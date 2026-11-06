"""D028 physical model only; no completion oracle or source-pool cache."""
import hashlib
import random


def seed64(*parts):
    return int.from_bytes(hashlib.sha256('|'.join(map(str,parts)).encode()).digest()[:8],'big')


def seed32(*parts):
    return int.from_bytes(hashlib.sha256('|'.join(map(str,parts)).encode()).digest()[:4],'big')


def instance(n,seed):
    rng=random.Random(seed64('D028-instance-v1',n,seed))
    return {'n':n,'seed':seed,'m':2,'buffer_capacity_MB':[40,40],
            'applications':[{'data_sizes_MB':[rng.randint(10,35) for _ in range(3)],'access_satellite_zero_based':rng.randrange(2)} for _ in range(n)]}


class Model:
    def __init__(self,inst):
        self.instance=inst;self.n=inst['n'];self.sizes=tuple(tuple(a['data_sizes_MB']) for a in inst['applications']);self.access=tuple(a['access_satellite_zero_based'] for a in inst['applications'])
        self.universe=2*8**self.n;self.initial=1;self.done_pos=7
        assert self.n in (3,6) and all(len(s)==3 and all(10<=v<=35 for v in s) for s in self.sizes)
    def decode(self,code):
        return tuple((code>>(1+3*i))&7 for i in range(self.n))+(code&1,)
    def encode(self,state):
        return sum(p<<(1+3*i) for i,p in enumerate(state[:-1]))|state[-1]
    def free(self,state):
        f=[40,40]
        for i,p in enumerate(state[:-1]):
            if 0<p<7:
                sat,phase=divmod(p-1,3);f[sat]-=self.sizes[i][phase]
        return tuple(f)
    def app(self,state,i):
        p=state[i]
        if p==7:return
        if p==0:dest=[1+3*self.access[i]]
        else:
            sat,phase=divmod(p-1,3);dest=[7 if phase==2 else p+1]
            if phase<2 and state[-1]:dest.append(1+3*(1-sat)+phase)
        for q in dest:
            t=state[:i]+(q,)+state[i+1:]
            if min(self.free(t))>=0:yield t,(i<<6)|(p<<3)|q
    def successors(self,code):
        state=self.decode(code)
        for i in range(self.n):
            for t,action in self.app(state,i):yield self.encode(t),action
        yield code^1,-1
    def is_end(self,code):return (code>>1)==8**self.n-1
    def is_initial_safe(self,code):return all(p in (0,7) for p in self.decode(code)[:-1])
