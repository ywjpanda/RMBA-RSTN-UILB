"""Public paired mean60 declarations; exact supplied B60 backgrounds, no RNG."""
import copy,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CONFIGS=('B60','H10','H20','H25')
SCENARIOS=('N','F','R')
DELTA={'B60':0,'H10':10,'H20':20,'H25':25}
PATTERNS=((0,1,1,0),(1,0,0,1),(0,1,0,1),(1,0,1,0))
ORDER_ROWS=(('B60','H10','H25','H20'),('H10','H20','B60','H25'),('H20','H25','H10','B60'),('H25','B60','H20','H10'))
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf8')
def identity(value):return hashlib.sha256(canonical(value)).hexdigest()
def labels(split):
    if split!='formal':raise ValueError('only formal backgrounds are distributed')
    return list(range(1702001,1702101))
def index(split,label):return labels(split).index(label)
def position(split,label):return 'ABCD'[index(split,label)%4]
def capacity(config,split,label):
    d=DELTA[config];return [60+d if high else 60-d for high in PATTERNS[index(split,label)%4]]
def order(split,label,scenario):return ORDER_ROWS[(index(split,label)+SCENARIOS.index(scenario))%4]
def events(instance,scenario):
    W=instance['n']*(instance['K']+2)
    return {'N':{},'F':{W//2:0},'R':{W//2:0,W:1}}[scenario]
def load_base(split,label):
    index(split,label)
    path=ROOT/'inputs/scale'/f'B60_{label}.json'
    base=json.loads(path.read_text())['instance']
    if (base['config_id'],base['split'],base['seed_label'],base['m'],base['n'],base['K'],base['buffer_capacity_MB'])!=('B60','formal',label,4,16,2,[60]*4):raise ValueError('paired base content/domain')
    return base,path
def make_instance(config,label,split='formal'):
    if config not in CONFIGS:raise ValueError('unregistered capacity condition')
    base,path=load_base(split,label);inst=copy.deepcopy(base)
    spec=HERE/'EXPERIMENT_SPEC.json';declaration=json.loads(spec.read_text())
    if declaration['model']['m']!=4 or declaration['model']['n']!=16 or declaration['model']['K']!=2 or {c['id'] for c in declaration['configs']}!=set(CONFIGS):raise ValueError('scientific declaration drift')
    model=declaration['model']
    if model['edges_zero_based']!=[[0,1],[1,2],[2,3]] or model['unreliable_edge_zero_based']!=[1,2] or model['data_sizes_integer_uniform_inclusive']!=[10,35] or model['data_items_per_application']!=3:raise ValueError('scientific model declaration mismatch')
    if declaration['W']!=64 or declaration['slot_budget']!=1024:raise ValueError('declared operation budget mismatch')
    if [(s['internal'],s['events']) for s in declaration['scenarios']]!=[('N',[]),('F',[{'slot':32,'link_up':False}]),('R',[{'slot':32,'link_up':False},{'slot':64,'link_up':True}])]:raise ValueError('declared event schedule mismatch')
    for c in declaration['configs']:
        d=DELTA[c['id']];pair=[60-d,60+d]
        if c['mean_MB']!=60 or c['population_SD_MB']!=d or c['total_MB']!=240 or c['component_total_MB']!=120 or c['CV']!=d/60 or c['component_capacity_multisets_MB']!=[pair,pair] or sorted(c['illustrative_capacity_vector_MB'])!=sorted(pair*2):raise ValueError('declared capacity content mismatch')
    inst.update(schema='D039_PAIRED_HET60_INSTANCE_V1',namespace='D039_HET60_PAIRED_B60_V1',config_id=config,
                buffer_capacity_MB=capacity(config,split,label),
                scientific_config_hash=identity({'m':4,'n':16,'K':2,'condition':config,'mean_MB':60,'SD_MB':DELTA[config]}),
                declaration_sha256=hashlib.sha256(spec.read_bytes()).hexdigest(),
                paired_provenance={'base_config_id':'B60','position_pattern':position(split,label),'derived_seeds':'exact copied B60 data/access/capacity/selector; no new seed derivation','capacity_scope':'only capacity and necessary identity/provenance metadata vary'})
    changed={k for k in set(base)|set(inst) if base.get(k)!=inst.get(k)}
    if not changed<={'schema','namespace','config_id','buffer_capacity_MB','scientific_config_hash','declaration_sha256','paired_provenance'}:raise ValueError('unpaired mutation')
    if inst['derived_seeds']!=base['derived_seeds'] or inst['applications']!=base['applications']:raise ValueError('paired background drift')
    if sum(inst['buffer_capacity_MB'])!=240 or sum(inst['buffer_capacity_MB'][:2])!=120 or sum(inst['buffer_capacity_MB'][2:])!=120:raise ValueError('component capacity drift')
    return inst
