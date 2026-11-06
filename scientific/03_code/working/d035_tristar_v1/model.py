"""D035 generalization of D028's physical tuple/app interface.
Dense base=(3*m+2), dynamic done position, single unreliable edge.
No oracle, graph labels, certification cache or query RNG is stored in Model.
"""


class Model:
    def __init__(self,inst):
        self.instance=inst;self.n=inst['n'];self.m=inst['m'];self.K=inst.get('K',2)
        assert self.K==2 and self.m in (2,3) and self.n>=1
        self.done_pos=1+3*self.m;self.base=self.done_pos+1
        self.powers=tuple(self.base**i for i in range(self.n))
        self.universe=2*self.base**self.n;self.initial=1
        self.sizes=tuple(tuple(a['data_sizes_MB']) for a in inst['applications'])
        self.access=tuple(a['access_satellite_zero_based'] for a in inst['applications'])
        self.caps=tuple(inst['buffer_capacity_MB'])
        self.edges={frozenset(e) for e in inst.get('edges_zero_based',[[j,j+1] for j in range(self.m-1)])}
        self.unreliable=frozenset(inst.get('unreliable_edge_zero_based',[0,1]))
        assert len(self.sizes)==self.n and len(self.caps)==self.m and all(c==40 for c in self.caps)
        assert all(len(s)==3 and all(type(v) is int and 10<=v<=35 for v in s) for s in self.sizes)
        assert all(0<=j<self.m for j in self.access) and self.unreliable in self.edges

    def decode(self,code):
        code=int(code)
        if not 0<=code<self.universe:raise ValueError('state code out of dense domain')
        value=code//2;positions=[]
        for _ in range(self.n):value,p=divmod(value,self.base);positions.append(p)
        return tuple(positions)+(code&1,)

    def encode(self,state):
        if len(state)!=self.n+1 or state[-1] not in (0,1) or any(not 0<=p<=self.done_pos for p in state[:-1]):
            raise ValueError('invalid physical tuple')
        return 2*sum(p*w for p,w in zip(state[:-1],self.powers))+state[-1]

    def free(self,state):
        free=list(self.caps)
        for i,p in enumerate(state[:-1]):
            if 0<p<self.done_pos:
                sat,phase=divmod(p-1,3);free[sat]-=self.sizes[i][phase]
        return tuple(free)

    def valid(self,state):
        self.encode(state)
        if any(not 0<=f<=c for f,c in zip(self.free(state),self.caps)):raise ValueError('buffer invariant')

    def action(self,i,p,q):
        return i*self.base*self.base+p*self.base+q

    def decode_action(self,action):
        if not 0<=action<self.n*self.base*self.base:raise ValueError('not a task action')
        i,rest=divmod(action,self.base*self.base);p,q=divmod(rest,self.base)
        return i,p,q

    def app(self,state,i):
        p=state[i]
        if p==self.done_pos:return
        if p==0:destinations=[1+3*self.access[i]]
        else:
            sat,phase=divmod(p-1,3)
            destinations=[self.done_pos if phase==2 else p+1]
            if phase<2:
                for target in range(self.m):
                    edge=frozenset((sat,target))
                    if edge in self.edges and (state[-1] or edge!=self.unreliable):
                        destinations.append(1+3*target+phase)
        for q in destinations:
            nxt=state[:i]+(q,)+state[i+1:]
            if min(self.free(nxt))>=0:yield nxt,self.action(i,p,q)

    def successors(self,code):
        state=self.decode(code)
        for i in range(self.n):
            for nxt,action in self.app(state,i):yield self.encode(nxt),action
        yield int(code)^1,-1

    def is_end(self,code):
        return (int(code)//2)==self.base**self.n-1

    def is_initial_safe(self,code):
        return all(p in (0,self.done_pos) for p in self.decode(code)[:-1])
