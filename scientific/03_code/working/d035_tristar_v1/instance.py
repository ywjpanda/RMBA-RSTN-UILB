"""D035 independent tristar declarations. Importing does not generate instances."""
import hashlib
import random

NAMESPACE='TRADEOFF_MULTI_013_v1'
CONFIG_ID='TRADEOFF_3_4_013'
FORMAL_LABELS=tuple(range(5342001,5342101))


def seed64(split,label,stream):
    if split not in ('formal',) or stream not in ('data','access','query'):
        raise ValueError('invalid declared stream')
    text=f'{NAMESPACE}|{split}|{CONFIG_ID}|{label}|{stream}'
    return int.from_bytes(hashlib.sha256(text.encode('utf8')).digest()[:8],'big')


def instance(label,split='formal'):
    if split not in ('formal',):raise ValueError('invalid instance split')
    if label not in FORMAL_LABELS:raise ValueError('label outside fixed split')
    seeds={s:seed64(split,label,s) for s in ('data','access','query')}
    data=random.Random(seeds['data']);access=random.Random(seeds['access'])
    return {'schema':'D035_TRISTAR_INSTANCE_V1','namespace':NAMESPACE,'config_id':CONFIG_ID,
            'split':split,'seed':label,'seed_label':label,'derived_seeds':seeds,'m':3,'n':4,'K':2,
            'buffer_capacity_MB':[40,40,40],'edges_zero_based':[[0,1],[1,2]],
            'unreliable_edge_zero_based':[0,1],
            'applications':[{'data_sizes_MB':[data.randint(10,35) for _ in range(3)],
                             'access_satellite_zero_based':access.randrange(3)} for _ in range(4)]}
