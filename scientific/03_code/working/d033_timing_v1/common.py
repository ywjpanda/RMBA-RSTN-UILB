from pathlib import Path
import hashlib,json,random,sys
from release_support import HERE as RELEASE,inside,check_instance
HERE=Path(__file__).resolve().parent
ROOT=RELEASE
SCIENCE_FILES=('model.py','rmba.py','scientific.py')
def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda : f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    tmp.replace(path)

def science_hashes():
    return {name: digest(HERE / name) for name in SCIENCE_FILES}

def query_seed(split, n, seed):
    stream = f'R1_06_TIMING_022_v1|{split}|{n}|{seed}|query'
    return int.from_bytes(hashlib.sha256(stream.encode('utf8')).digest()[:8], 'big')

def queries(codes, rstar, split, n, seed):
    population = sorted((int(c) for (c, yes) in zip(codes, rstar) if yes))
    return random.Random(query_seed(split, n, seed)).sample(population, min(1000, len(population)))
def verify_binding(item):
    attempt=inside(ROOT,item['attempt'])
    task={'instance':json.loads((attempt/'instance.json').read_text())}
    inst=check_instance(task['instance'])
    if (inst['n'],inst['seed'])!=(item['n'],item['seed']):raise ValueError('truth/input instance mismatch')
    from model import Model
    from validate_truth import validate
    checked=validate(attempt,Model(inst))
    saved=json.loads((attempt/'result.json').read_text())
    for k in ('Rstar','R_RMBA','eta_reach'):
        if saved[k]!=checked[k]:raise ValueError('saved truth cardinality mismatch')
    return attempt,task
