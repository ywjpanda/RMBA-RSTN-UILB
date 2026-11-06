"""Release input/domain helpers. No scientific search or timing on import."""
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import sys

HERE = Path(__file__).resolve().parent
FAMILIES = {'control','scale','het60','calibration','paired2','tristar_truth'}
CONTROL = {(2,4),(2,8),(2,12),(4,8),(4,12)}
SCALE = {'S4','S8','K4','K6','B35','B60','IO_LOW','IO_HIGH','L16','L48','K8','B50','L64','S16'}

def read(p): return json.loads(Path(p).read_text())
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def identity(x): return hashlib.sha256(canonical(x)).hexdigest()
def rss_bytes():
    x=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(x if sys.platform=='darwin' else x*1024)
def environment():
    import numpy as np
    import psutil
    return {'python_executable':sys.executable,'python_version':sys.version,'platform':platform.platform(),
            'machine':platform.machine(),'cpu_count':os.cpu_count(),'physical_memory_bytes':psutil.virtual_memory().total,
            'numpy_version':np.__version__,'psutil_version':psutil.__version__}
def inside(root,path):
    root=Path(root).resolve();p=(root/path).resolve()
    if root not in p.parents:raise ValueError('path outside declared input root')
    return p
def check_instance(inst):
    n=inst['n'];m=inst.get('m',len(inst['buffer_capacity_MB']));K=inst.get('K',2)
    if type(n) is not int or type(m) is not int or type(K) is not int or not 1<=n<=64 or not 2<=m<=16 or not 1<=K<=8:raise ValueError('instance dimension')
    caps=inst['buffer_capacity_MB'];apps=inst['applications']
    if len(caps)!=m or any(type(x) is not int or x<=0 for x in caps) or len(apps)!=n:raise ValueError('instance shape/capacity')
    for a in apps:
        sizes=a['data_sizes_MB'];access=a['access_satellite_zero_based']
        if len(sizes)!=K+1 or any(type(x) is not int or x<=0 for x in sizes) or type(access) is not int or not 0<=access<m:raise ValueError('application content/domain')
    if inst.get('split','formal')!='formal':raise ValueError('development cohort excluded')
    edges=inst.get('edges_zero_based',[[0,1]]);bad=inst.get('unreliable_edge_zero_based',[0,1])
    if edges!=[[j,j+1] for j in range(m-1)] or len(bad)!=2 or any(type(v) is not int for v in bad) or bad not in edges:raise ValueError('linear topology/unreliable edge domain')
    return inst
def check_cohort(family,task):
    if family not in FAMILIES:raise ValueError('unknown family')
    inst=check_instance(task['instance']);n=inst['n'];m=inst.get('m',len(inst['buffer_capacity_MB']))
    seed=inst.get('seed_label',inst.get('seed'))
    lo,hi=(2632001,2632100) if family=='control' and n in (4,8) and m==2 else (2732001,2732100) if family=='control' else (1702001,1702100) if family in {'scale','het60'} else (5342001,5342100) if family=='tristar_truth' else (2832001,2832100)
    if type(seed) is not int or not lo<=seed<=hi:raise ValueError('seed outside formal cohort')
    if family=='control':
        if (m,n) not in CONTROL or task['method'] not in {'uncontrolled','mba_current','peak_remaining','rmba'} or task['scenario'] not in {f'S{x}' for x in range(7)}:raise ValueError('control cohort')
        if inst.get('K',2)!=2 or inst['buffer_capacity_MB']!=[40]*m or inst.get('unreliable_edge_zero_based')!=([0,1] if m==2 else [1,2]) or any(not 10<=x<=35 for a in inst['applications'] for x in a['data_sizes_MB']):raise ValueError('control physical/data configuration')
    elif family=='scale':
        if inst['config_id'] not in SCALE or task['scenario'] not in {'N','F','R'}:raise ValueError('scale cohort')
        configs=read(HERE/'configurations/scale_retained.json')['configurations']
        cfg=next(c for c in configs if c['id']==inst['config_id'])
        if (m,n,inst['K'],inst['buffer_capacity_MB'],inst['unreliable_edge_zero_based'])!=(cfg['m'],cfg['n'],cfg['K'],cfg['capacity_MB'],cfg['unreliable_edge_zero_based']):raise ValueError('scale scientific configuration mismatch')
        lo,hi=cfg['all_d0_through_dK_integer_uniform_inclusive']
        if any(not lo<=x<=hi for a in inst['applications'] for x in a['data_sizes_MB']):raise ValueError('scale configured data domain')
    elif family=='het60':
        if inst['config_id'] not in {'B60','H10','H20','H25'} or (m,n)!=(4,16) or sum(inst['buffer_capacity_MB'])!=240 or task['scenario'] not in {'N','F','R'}:raise ValueError('mean60 cohort')
    elif family in {'calibration','paired2'}:
        if (m,n) not in {(2,3),(2,6)} or inst.get('K',2)!=2 or inst['buffer_capacity_MB']!=[40,40] or any(not 10<=x<=35 for a in inst['applications'] for x in a['data_sizes_MB']):raise ValueError('two-star exact cohort')
        if family=='calibration':
            cfg=task['config']
            expected={'n_values':[3,6],'q_percent':[10,30,60],'f_percent':[10,30,60],'repeats':10,'extra_1000_only_n6':True}
            if any(cfg[k]!=v for k,v in expected.items()) or cfg['limits']!=task['limits']:raise ValueError('calibration scientific sampling configuration')
    elif (m,n)!=(3,4) or inst.get('K',2)!=2 or inst['buffer_capacity_MB']!=[40]*3 or inst.get('unreliable_edge_zero_based')!=[0,1] or task['phase']!='truth' or any(not 10<=x<=35 for a in inst['applications'] for x in a['data_sizes_MB']):raise ValueError('tristar cohort')
    return task
def select(family,key):
    if family not in FAMILIES or not key or Path(key).name!=key or '/' in key or '\\' in key:raise ValueError('unknown family/invalid identity')
    p=inside(HERE/'inputs'/family,key+'.json')
    if not p.is_file():raise ValueError('unknown supplied identity')
    task=check_cohort(family,read(p));task=copy.deepcopy(task)
    inst=task['instance'];seed=inst.get('seed_label',inst.get('seed'))
    expected_id=(f"{inst.get('m',len(inst['buffer_capacity_MB']))}x{inst['n']}_{seed}" if family=='control' else f"{inst['config_id']}_{seed}" if family in {'scale','het60'} else f"n{inst['n']}_{seed}" if family in {'paired2','calibration'} else str(seed))
    if key!=expected_id:raise ValueError('input filename/content identity mismatch')
    task['family']=family;task['release_id']=key
    if family=='het60':
        # Rebind the real derived declaration and validate every paired background field.
        import importlib.util
        spec=importlib.util.spec_from_file_location('release_het_instance',HERE/'03_code/working/d039_het60_v3/instance.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        expected=module.make_instance(task['instance']['config_id'],task['instance']['seed_label'],'formal')
        observed=task['instance']
        required={'schema','namespace','split','config_id','seed_label','derived_seeds','m','n','K','buffer_capacity_MB','edges_zero_based','unreliable_edge_zero_based','applications','paired_provenance'}
        if set(observed)!=required:raise ValueError('paired field set mismatch')
        for name,value in observed.items():
            if expected.get(name)!=value:raise ValueError('paired supplied task drift '+name)
        task['instance']=expected
    return task
def prepare(family,key,out):
    task=select(family,key);out=Path(out).resolve()
    if out.exists():raise ValueError('choose a fresh output directory')
    out.mkdir(parents=True);(out/'task.json').write_text(json.dumps(task,indent=2)+'\n')
    return out/'task.json'
