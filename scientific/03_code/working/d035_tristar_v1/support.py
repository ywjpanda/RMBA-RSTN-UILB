import hashlib,json,os,platform,resource,sys
from pathlib import Path
import numpy as np
import psutil
from release_support import HERE as RELEASE,check_instance
HERE=Path(__file__).resolve().parent
ROOT=RELEASE
SCIENCE_FILES=('instance.py','model.py','rmba.py','exact.py','scientific.py')
def read(path):
    return json.loads(Path(path).read_text())

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
    tmp.replace(path)

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda : f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf8')).hexdigest()

def science_hashes():
    return {name: digest(HERE / name) for name in SCIENCE_FILES}

def environment():
    return {'python_executable': sys.executable, 'python_version': sys.version, 'platform': platform.platform(), 'machine': platform.machine(), 'cpu_count': os.cpu_count(), 'physical_memory_bytes': psutil.virtual_memory().total, 'numpy_version': np.__version__, 'psutil_version': psutil.__version__}

def rss():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == 'darwin' else value * 1024)

def save_npz(path, values):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('wb') as f:
        np.savez_compressed(f, **values)
    tmp.replace(path)
def verify_task(task,phase):
    if task['phase']!=phase or task['science_hashes']!=science_hashes():raise ValueError('phase/current source mismatch')
    from instance import instance
    inst=check_instance(task['instance'])
    if inst['split']!='formal' or task['split']!='formal' or inst!=instance(inst['seed_label'],'formal'):raise ValueError('tristar fixed seed/content mismatch')
    actual=environment()
    for k in ('python_executable','python_version','platform','machine','numpy_version','psutil_version'):
        if actual[k]!=task['environment'][k]:raise ValueError('live environment changed '+k)
    return inst
def verify_truth_binding(binding):
    attempt=Path(binding['attempt']).resolve()
    task=read(attempt/'task.json') if (attempt/'task.json').exists() else {'instance':read(attempt/'instance.json')}
    inst=check_instance(task['instance'])
    from instance import instance
    if inst!=instance(inst['seed_label'],'formal'):raise ValueError('truth instance content mismatch')
    from model import Model
    from validate_truth import validate
    checked=validate(attempt,Model(inst))
    saved=read(attempt/'result.json')
    for k in ('Rstar','R_RMBA','eta_reach'):
        if saved[k]!=checked[k]:raise ValueError('truth numerical/cardinality mismatch')
    if (attempt/'task.json').exists():
        process=read(attempt/'process.json')
        if process['status']!='completed' or process['exit_code']!=0 or process['resource_final_PASS'] is not True:raise ValueError('new truth parent/resource context missing')
    return attempt,task
