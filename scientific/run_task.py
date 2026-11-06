"""Guarded fresh single-task execution. Run only when a scientific rerun is intended."""
import argparse
import importlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import sys
import time
from release_support import HERE,check_cohort,environment,prepare,read,rss_bytes,identity

MODULES={'calibration':('d028_v2','worker','run'),'paired2':('d033_timing_v1','measurement_worker','run'),
         'scale':('d032_v1','worker','run'),'het60':('d039_het60_v3','worker','run'),
         'tristar_truth':('d035_tristar_v1','worker_truth','run')}
def module_for(task):
    if task['family']=='control':
        inst=task['instance'];m=inst.get('m',len(inst['buffer_capacity_MB']))
        return ('d026_2leo_v3' if m==2 and inst['n'] in (4,8) else 'd027_v2','worker_api','worker')
    if task['family']=='tristar_truth' and task['phase']=='timing':return 'd035_tristar_v1','worker_timing','run'
    return MODULES[task['family']]
def _worker(path):
    task=read(path);folder,name,func=module_for(task)
    sys.path.insert(0,str(HERE/'03_code/working'/folder));module=importlib.import_module(name)
    if task['family']=='tristar_truth':
        from support import science_hashes
        task['science_hashes']=science_hashes()
    if task['family'] in {'scale','het60'}:
        import hashlib
        folder_path=HERE/'03_code/working'/folder
        task['science_lock_hash']=identity({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder_path.glob('*.py'))})
    if task['family']=='control':task['code_hashes']=module.code_hashes()
    task['environment']=environment();Path(path).write_text(json.dumps(task,indent=2)+'\n')
    value=getattr(module,func)(path)
    return value if isinstance(value,int) else 0
def limits(task):
    lim=task.get('limits',{});cfg=task.get('config',{})
    return {'wall':lim.get('worker_wall_s',lim.get('instance_worker_wall_s',lim.get('worker_seconds',cfg.get('worker_wall_seconds',120)))),
            'worker_rss':lim.get('worker_rss_bytes',cfg.get('rss_limit_bytes',2*1024**3)),
            'parent_rss':lim.get('parent_rss_bytes',4*1024**3),
            'disk':lim.get('trajectory_disk_bytes',lim.get('instance_disk_bytes',512*1024**2)),
            'free':lim.get('runtime_min_free_bytes',2*1024**3),
            'preflight':lim.get('preflight_min_free_bytes',lim.get('preflight_free_bytes',2*1024**3)),
            'call':lim.get('single_method_call_wall_s',30),'grace':lim.get('term_grace_s',3)}
def watch_failure(out,lim,now):
    path=out/'watch.bin'
    if not path.exists():return None
    raw=path.read_bytes()
    if len(raw)!=24:raise ValueError('watch record shape')
    started,count,method=struct.unpack('dQQ',raw)
    if not math.isfinite(started) or started<0 or started>now or method not in (0,1,2) or bool(started)!=bool(method):raise ValueError('watch record domain')
    if started and now-started>lim['call']:return 'single method call wall limit'
    return None
def terminate_group(proc,grace):
    """Each worker owns a fresh process group; clean its entire group on failure."""
    try:os.killpg(proc.pid,signal.SIGTERM)
    except ProcessLookupError:return
    try:proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:pass
    # The group may still contain descendants after the direct worker exits.
    try:os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError:pass
def result_complete(task,out,result):
    if not result.is_file():return False
    data=read(result);family=task['family']
    if family=='calibration':
        return (out/'metrics.json').is_file() and read(out/'metrics.json').get('status')=='science_complete' and (out/'science_complete.json').is_file()
    if family in {'paired2','tristar_truth'}:return data.get('status')=='PASS'
    if family in {'scale','het60'}:return data.get('status') in {'all_complete','slot_budget'} and data.get('valid_observation') is True and data.get('error') is None
    return data.get('status') in {'all_complete','slot_budget'} and data.get('error') is None
def execute(task_path):
    import psutil
    task=read(task_path);out=Path(task_path).parent;lim=limits(task)
    if shutil.disk_usage(out).free<lim['preflight']:raise RuntimeError('preflight disk headroom')
    task['parent_pid']=os.getpid();task['environment']=environment()
    Path(task_path).write_text(json.dumps(task,indent=2)+'\n');(out/'watch.bin').write_bytes(bytes(24))
    started=time.monotonic();reason=None;peak=0;parent_peak=0;cpu_peak=0
    with (out/'worker.log').open('w') as log:
        proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'_worker',str(task_path)],stdout=log,stderr=log,cwd=out,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),start_new_session=True)
        parent=psutil.Process()
        try:
            worker=psutil.Process(proc.pid)
            while proc.poll() is None:
                now=time.monotonic()
                tree=[worker]+worker.children(recursive=True)
                mem=sum(p.memory_info().rss for p in tree if p.is_running());peak=max(peak,mem)
                parent_peak=max(parent_peak,parent.memory_info().rss)
                if now-started>lim['wall']:reason='worker wall limit'
                elif mem>lim['worker_rss']:reason='worker tree RSS limit'
                elif parent_peak>lim['parent_rss']:reason='parent RSS limit'
                elif sum(p.stat().st_size for p in out.rglob('*') if p.is_file())>lim['disk']:reason='single-task disk limit'
                elif shutil.disk_usage(out).free<lim['free']:reason='runtime disk headroom'
                else:reason=watch_failure(out,lim,now)
                if reason:break
                time.sleep(.1)
        except BaseException as error:
            if not isinstance(error,psutil.NoSuchProcess) or proc.poll() is None:
                reason='monitor failure: '+type(error).__name__+': '+str(error)
        finally:
            terminate_group(proc,lim['grace'])
        code=proc.wait();elapsed=time.monotonic()-started
    # A fast worker is still subject to final resource checks.
    parent_peak=max(parent_peak,parent.memory_info().rss)
    if elapsed>lim['wall'] or peak>lim['worker_rss'] or parent_peak>lim['parent_rss']:reason=reason or 'final resource limit'
    if sum(p.stat().st_size for p in out.rglob('*') if p.is_file())>lim['disk']:reason=reason or 'final disk limit'
    result=out/('measurement.json' if task['family']=='paired2' or task.get('phase')=='timing' else 'result.json')
    try:complete=result_complete(task,out,result)
    except BaseException as error:complete=False;reason=reason or 'invalid result: '+str(error)
    accepted=code==0 and reason is None and complete
    if code==0 and not complete:reason=reason or 'worker result missing, partial or unsuccessful'
    if accepted:
        data=read(result);reported=data.get('worker_peak_rss_bytes',data.get('worker_ru_maxrss_bytes',data.get('peak_rss_bytes',0)))
        if task['family']=='calibration' and (out/'metrics.json').exists():reported=max(reported,read(out/'metrics.json').get('worker_ru_maxrss_cumulative_bytes',0))
        peak=max(peak,reported)
        if peak>lim['worker_rss']:accepted=False;reason='worker reported final RSS limit'
        if peak<=0:accepted=False;reason='worker RSS measurement unavailable'
    record={'status':'completed' if accepted else 'failed','exit_code':code,'resource_final_PASS':accepted,
            'wall_s':elapsed,'monitored_worker_peak_rss_bytes':peak,'parent_peak_rss_bytes':parent_peak,'reason':reason,
            'resource_budget':{'scope':'formal_pipeline','used_after_s':elapsed,'limit_s':lim['wall']},'limits':lim,
            'environment':environment(),'context':'fresh guarded single task; no old registry/GO/receipt reused'}
    record['result_complete']=complete
    record['acceptance_scope']='single-task resource and completion checks; independent scientific correctness is not inferred from successful execution'
    (out/'process.json').write_text(json.dumps(record,indent=2)+'\n')
    return 0 if accepted else 2
def main():
    if len(sys.argv)>1 and sys.argv[1]=='_worker':return _worker(Path(sys.argv[2]))
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--family',required=True);p.add_argument('--id',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--phase',choices=('truth','timing'),default='truth');p.add_argument('--truth',type=Path);p.add_argument('--method',choices=('uncontrolled','mba_current','peak_remaining','rmba'));p.add_argument('--scenario')
    a=p.parse_args();task_path=prepare(a.family,a.id,a.output);task=read(task_path)
    if a.method:
        if a.family!='control':raise ValueError('method option belongs to control')
        task['method']=a.method
    if a.scenario:
        allowed={f'S{i}' for i in range(7)} if a.family=='control' else {'N','F','R'} if a.family in {'scale','het60'} else set()
        if a.scenario not in allowed:raise ValueError('scenario outside selected family')
        task['scenario']=a.scenario
    check_cohort(a.family,task)
    task_path.write_text(json.dumps(task,indent=2)+'\n')
    if a.family=='tristar_truth' and a.phase=='timing':
        if a.truth is None:raise ValueError('timing needs an explicit complete truth directory')
        task['phase']='timing';task['truth_input']={'attempt':str(a.truth.resolve())}
        task['limits'].update(worker_wall_s=600,worker_rss_bytes=2*1024**3,parent_rss_bytes=4*1024**3,single_method_call_wall_s=30)
        task_path.write_text(json.dumps(task,indent=2)+'\n')
    return execute(task_path)
if __name__=='__main__':sys.exit(main())
