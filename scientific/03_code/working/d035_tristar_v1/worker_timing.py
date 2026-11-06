"""Tristar ABBA timing; graph/labels are used only outside measured functions."""
import csv
import hashlib
import json
import mmap
import os
from pathlib import Path
import random
import signal
import struct
import sys
import threading
import time
import traceback
import numpy as np
from support import read,write,digest,identity,science_hashes,verify_task,verify_truth_binding,rss
from budget import ResourceLimit
from model import Model
from scientific import timed_call


def queries(model,codes,rstar,query_seed):
    population=sorted(int(code) for code,yes in zip(codes,rstar) if yes)
    if not population:raise RuntimeError('empty complete Rstar')
    return random.Random(query_seed).sample(population,min(1000,len(population)))


def strata(model,query_codes):
    counts={k:0 for k in ('up','down','has_ready','has_done','all_done','initial_safe')}
    for code in query_codes:
        state=model.decode(code);done=model.done_pos
        counts['up' if code&1 else 'down']+=1;counts['has_ready']+=int(0 in state[:-1])
        counts['has_done']+=int(done in state[:-1]);counts['all_done']+=int(all(p==done for p in state[:-1]))
        counts['initial_safe']+=int(all(p in (0,done) for p in state[:-1]))
    return counts


def run(task_path):
    task_path=Path(task_path);task=read(task_path);out=task_path.parent
    start=time.monotonic();inst=verify_task(task,'timing');model=Model(inst)
    def parent_guard():
        while True:
            time.sleep(.5)
            if os.getppid()!=task['parent_pid']:os._exit(143)
    threading.Thread(target=parent_guard,daemon=True).start()
    def terminate(signum,frame):raise ResourceLimit('parent requested termination; consult process record')
    signal.signal(signal.SIGTERM,terminate)
    with (out/'watch.bin').open('r+b') as wf:
        watch=mmap.mmap(wf.fileno(),24)
        try:
            truth,truth_task=verify_truth_binding(task['truth_input'])
            if truth_task['instance']!=inst:raise RuntimeError('truth/timing instance mismatch')
            with np.load(truth/'graph.npz',allow_pickle=False) as g:codes=g['codes'].copy()
            with np.load(truth/'sets.npz',allow_pickle=False) as s:R,K,A=(s[k].copy() for k in ('Rstar','K','A'))
            q=queries(model,codes,R,inst['derived_seeds']['query'])
            qhash=hashlib.sha256(json.dumps(q,separators=(',',':')).encode()).hexdigest()
            counts=strata(model,q);lookup={int(c):i for i,c in enumerate(codes)}
            write(out/'queries.json',{'codes':q,'sha256':qhash,'query_seed':inst['derived_seeds']['query'],
                                      'domain_size':int(R.sum()),'counts':counts,'truth_input':task['truth_input']})
            total=0;sums={'RMBA':0,'Exact':0};zero=0
            with (out/'raw.csv').open('w',newline='') as f:
                writer=csv.writer(f);writer.writerow(['round','position','code','method_order','method','answer','ns'])
                for rnd in range(4):
                    methods=('RMBA','Exact') if rnd in (0,3) else ('Exact','RMBA')
                    for pos,code in enumerate(q if rnd in (0,3) else q[::-1]):
                        for ordinal,method in enumerate(methods):
                            call_start=time.monotonic()
                            watch[:]=struct.pack('dQQ',time.monotonic(),total,1 if method=='RMBA' else 2)
                            answer,ns=timed_call(model,code,method)
                            watch[:]=struct.pack('dQQ',0.0,total+1,0)
                            call_wall=time.monotonic()-call_start
                            if call_wall>task['limits']['single_method_call_wall_s']:
                                write(out/'call_limit_failure.json',{'method':method,'code':code,'answer':answer,'ns':ns,'call_wall_s':call_wall})
                                raise ResourceLimit('single method call wall limit')
                            writer.writerow([rnd,pos,code,ordinal,method,int(answer),ns])
                            expected=bool(A[lookup[code]]) if method=='RMBA' else bool(K[lookup[code]])
                            if answer!=expected:
                                f.flush();raise RuntimeError(f'LABEL_MISMATCH {method} {code} got={answer} expected={expected}')
                            sums[method]+=ns;zero+=int(ns==0);total+=1
            each=4*len(q)
            if not each or sums['Exact']<=0:raise RuntimeError('nonpositive Exact mean or empty workload')
            truth_result=read(truth/'result.json')
            result={'schema':'D035_TRISTAR_TIMING_V1','status':'PASS','m':3,'n':4,'seed':inst['seed_label'],'split':inst['split'],
                    'instance_hash':identity(inst),'task_identity':identity(task),'truth_input':task['truth_input'],
                    'science_hashes':science_hashes(),'query_count':len(q),'query_sha256':qhash,'query_counts':counts,
                    'observations':total,'observations_per_method':each,'zero_ns':zero,'sum_ns':sums,'mean_ns':{m:sums[m]/each for m in sums},
                    'ratio':(sums['RMBA']/each)/(sums['Exact']/each),'Rstar':truth_result['Rstar'],'R_RMBA':truth_result['R_RMBA'],
                    'eta_reach':truth_result['eta_reach'],'worker_elapsed_s':time.monotonic()-start,'worker_peak_rss_bytes':rss()}
            write(out/'measurement.json',result)
            if time.monotonic()-start>task['limits']['worker_wall_s'] or rss()>task['limits']['worker_rss_bytes']:raise ResourceLimit('timing exit wall/RSS limit')
            files=('task.json','queries.json','raw.csv','measurement.json')
            write(out/'worker_complete.json',{'PASS':True,'task_identity':identity(task),'science_hashes':science_hashes(),'files':{n:digest(out/n) for n in files}})
            if time.monotonic()-start>task['limits']['worker_wall_s'] or rss()>task['limits']['worker_rss_bytes']:raise ResourceLimit('timing final wall/RSS limit')
            return 0
        except BaseException as error:
            if (out/'worker_complete.json').exists():(out/'worker_complete.json').replace(out/'rejected_worker_complete.json')
            write(out/'worker_failure.json',{'status':'RESOURCE_LIMIT' if isinstance(error,ResourceLimit) else 'IMPLEMENTATION_ERROR',
                                             'reason':str(error),'elapsed_s':time.monotonic()-start,'traceback':traceback.format_exc()})
            traceback.print_exc();return 2
        finally:watch.close()


if __name__=='__main__':sys.exit(run(sys.argv[1]))
