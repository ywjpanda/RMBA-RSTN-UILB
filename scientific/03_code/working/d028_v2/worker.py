from release_support import rss_bytes
"""One isolated D028 instance; saves every complete stage and honest failures."""
from pathlib import Path
import hashlib
import json
import resource
import sys
import time
import traceback
import numpy as np
from model import Model
from exact import build,analyze
from legacy_pool import Pool
from sampling import calibrate
from budget import Budget


def write(path,value):
    path=Path(path);temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def science_hashes():
    here=Path(__file__).resolve().parent
    return {name:digest(here/name) for name in ('model.py','exact.py','rmba.py','legacy_pool.py','sampling.py','budget.py','worker.py')}


def run(task_path):
    task_path=Path(task_path);task=json.loads(task_path.read_text());out=task_path.parent;model=Model(task['instance']);budget=Budget(out,task['limits']);start=time.monotonic();g=None;sets=None;pools=[]
    try:
        g=build(model,budget);np.savez_compressed(out/'graph.npz',**g);budget.check(force=True)
        sets=analyze(model,g,budget);np.savez_compressed(out/'sets.npz',**sets);budget.check(force=True)
        F=int(sets['F'].sum())
        for q in (10,30,60):
            budget.stage('pool_q%d'%q);threshold=(q*F+99)//100
            pool=Pool(model,q,threshold,out,budget);meta=pool.run();index=g['index']
            bad=[c for c in meta['P_codes'] if index[c]<0 or not sets['Rstar'][index[c]]]
            meta['P_outside_Rstar_codes']=bad;meta['threshold_counted_positive_overshoot']=meta['positive_count']-threshold
            meta['P_equals_previous_q']=[p['q_percent'] for p in pools if p['P_codes']==meta['P_codes']]
            write(out/('pool_q%d.json'%q),meta)
            if bad:raise RuntimeError('SCIENTIFIC_POOL_OUTSIDE_RSTAR '+str(bad[:10]))
            if meta['B']!=0 or set(meta['I_codes'])!={int(c) for c in g['codes'][sets['I']]}:raise RuntimeError('source B/I mismatch')
            pools.append(meta);budget.check(force=True)
        result=calibrate(model,g,sets,pools,out,budget);write(out/'result.json',result);budget.check(force=True);budget.stop()
        metadata={'status':'science_complete','elapsed_s':time.monotonic()-start,'stage_measurements':budget.stages,'worker_ru_maxrss_cumulative_bytes':rss_bytes(),'science_hashes':science_hashes(),'task_sha256':digest(task_path)}
        write(out/'metrics.json',metadata)
        files=['task.json','graph.npz','sets.npz','result.json','metrics.json','samples.jsonl.gz']+[f'pool_q{q}.json' for q in (10,30,60)]+[f'pool_q{q}_trace.jsonl.gz' for q in (10,30,60)]
        write(out/'science_complete.json',{'science_hashes':science_hashes(),'files':{name:digest(out/name) for name in files}})
        return 0
    except BaseException:
        budget.stop()
        if g is not None and not (out/'graph.npz').exists():np.savez_compressed(out/'graph_partial.npz',**g)
        write(out/'failure.json',{'status':'interrupted' if isinstance(sys.exc_info()[1],KeyboardInterrupt) else 'failed','phase':budget.phase,'elapsed_s':time.monotonic()-start,'traceback':traceback.format_exc(),'stage_measurements':budget.stages,'science_hashes':science_hashes()})
        traceback.print_exc();return 2


if __name__=='__main__':
    sys.dont_write_bytecode=True
    sys.exit(run(sys.argv[1]))
