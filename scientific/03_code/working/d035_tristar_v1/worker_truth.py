"""One complete tristar truth instance; no pool construction or calibration."""
import os
from pathlib import Path
import signal
import sys
import time
import traceback
import numpy as np
from support import read,write,digest,identity,science_hashes,verify_task,save_npz,rss
from budget import Budget,ResourceLimit
from model import Model
from exact import build,analyze


def run(task_path):
    task_path=Path(task_path);task=read(task_path);out=task_path.parent
    inst=verify_task(task,'truth');model=Model(inst);lim=task['limits']
    budget=Budget(out,lim['worker_wall_s'],lim['worker_rss_bytes'],task['parent_pid'])
    def terminate(signum,frame):raise ResourceLimit('parent requested termination; consult parent process record')
    signal.signal(signal.SIGTERM,terminate)
    try:
        assert model.universe==29282 and model.done_pos==10 and model.base==11
        graph=build(model,budget)
        budget.partial={}
        budget.stage('graph_serialization');save_npz(out/'graph.npz',graph)
        sets=analyze(model,graph,budget)
        budget.stage('set_serialization');save_npz(out/'sets.npz',sets)
        initial=int(graph['index'][model.initial])
        result={'schema':'D035_TRISTAR_TRUTH_V1','status':'PASS','m':3,'n':4,'seed':inst['seed_label'],'split':inst['split'],
                'task_identity':identity(task),'instance_hash':identity(inst),'science_hashes':science_hashes(),
                'raw_states':len(graph['codes']),'physical_edges':len(graph['targets']),
                'C':int(sets['C'].sum()),'K':int(sets['K'].sum()),'Rstar':int(sets['Rstar'].sum()),
                'A_raw':int(sets['A'].sum()),'R_RMBA':int(sets['R_RMBA'].sum()),
                'eta_reach':int(sets['R_RMBA'].sum())/int(sets['Rstar'].sum()),
                'certified_Rstar':int((sets['A']&sets['Rstar']).sum()),
                'certified_but_unreachable_Rstar':int((sets['A']&sets['Rstar']&~sets['R_RMBA']).sum()),
                'initial_K':bool(sets['K'][initial]),'initial_A':bool(sets['A'][initial]),
                'dense_upper_bound':model.universe,'safe_edge_upper_bound':(3*model.n+1)*model.universe,
                'worker_peak_rss_bytes':rss(),'worker_cpu_s':time.process_time(),
                'pool_constructions':0,'calibration_samples':0}
        budget.check(force=True)
        write(out/'result.json',result);metrics=budget.finish();write(out/'metrics.json',metrics)
        budget.check(force=True)
        files=('task.json','graph.npz','sets.npz','result.json','metrics.json')
        write(out/'science_complete.json',{'PASS':True,'task_identity':identity(task),'science_hashes':science_hashes(),'files':{n:digest(out/n) for n in files}})
        budget.check(force=True)
        return 0
    except BaseException as error:
        if (out/'science_complete.json').exists():(out/'science_complete.json').replace(out/'rejected_science_complete.json')
        partial_error=None
        try:budget.save_partial()
        except BaseException:partial_error=traceback.format_exc()
        write(out/'worker_failure.json',{'status':'RESOURCE_LIMIT' if isinstance(error,ResourceLimit) else 'IMPLEMENTATION_ERROR',
                                         'reason':str(error),'traceback':traceback.format_exc(),'partial_save_error':partial_error,
                                         'metrics':budget.finish()})
        traceback.print_exc();return 2


if __name__=='__main__':sys.exit(run(sys.argv[1]))
