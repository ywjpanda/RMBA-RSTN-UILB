"""Independent complete saved truth validation, outside online timing.
No historical verification receipt is trusted or required. User-invoked full
validation checks every physical successor, autonomous closure, exact sets,
independent FIFO FS labels, controlled reachability and completion certificates.
"""
from collections import deque
import json
from pathlib import Path
import numpy as np
def load_npz(path):
    with np.load(path,allow_pickle=False) as f:return {k:f[k].copy() for k in f.files}
def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def reverse_coaccess(reverse, ends, within=None):
    found = set((u for u in ends if within is None or within[u]))
    queue = deque(found)
    while queue:
        for u in reverse[queue.popleft()]:
            if u not in found and (within is None or within[u]):
                found.add(u)
                queue.append(u)
    return found

def controlled(adj, accepted):
    require(bool(accepted[0]), 'initial rejected')
    seen = {0}
    queue = deque([0])
    while queue:
        for (v, a) in adj[queue.popleft()]:
            if a < 0:
                require(bool(accepted[v]), 'autonomous closure')
            elif not accepted[v]:
                continue
            if v not in seen:
                seen.add(v)
                queue.append(v)
    return seen

def reference_mba(model, state):
    """FIFO full FS, complete the first certifiable app; no production cache."""
    current = state
    while True:
        todo = [i for (i, p) in enumerate(current[:-1]) if p != model.done_pos]
        if not todo:
            return True
        accepted = None
        for i in todo:
            seen = {current}
            queue = deque([current])
            done = False
            while queue:
                value = queue.popleft()
                if value[i] == model.done_pos:
                    done = True
                    break
                for (nxt, _) in model.app(value, i):
                    if nxt not in seen:
                        seen.add(nxt)
                        queue.append(nxt)
            if done:
                accepted = i
                break
        if accepted is None:
            return False
        current = current[:accepted] + (model.done_pos,) + current[accepted + 1:]

def reference_rmba(model, code):
    state = model.decode(code)
    if not reference_mba(model, state):
        return False
    return reference_mba(model, state[:-1] + (0,)) if state[-1] else True

def validate_parents(adj, selected, parents, actions, name):
    require(int(parents[0]) == -1 and int(actions[0]) == -2, name + ' initial parent')
    for v in range(len(adj)):
        if v not in selected:
            require(int(parents[v]) == -1 and int(actions[v]) == -2, name + ' unreachable parent')
            continue
        if v == 0:
            continue
        u = int(parents[v])
        a = int(actions[v])
        require(u in selected and (v, a) in adj[u], name + ' invalid parent edge')
    known = {0}
    for start in selected:
        path = []
        local = set()
        u = start
        while u not in known:
            require(u not in local and u in selected, name + ' parent cycle')
            local.add(u)
            path.append(u)
            u = int(parents[u])
        known.update(path)

def validate(attempt,model):
    attempt=Path(attempt).resolve()
    if not hasattr(model,'base'):model.base=8
    g=load_npz(attempt/'graph.npz');s=load_npz(attempt/'sets.npz')
    require(set(g)=={'codes','index','rowptr','targets','actions','raw_parent','raw_parent_action'},'graph schema')
    require(set(s)=={'C','K','Rstar','A','R_RMBA','I','F','task_completion_next','optimal_parent','optimal_parent_action','rmba_parent','rmba_parent_action','certification_queries'},'set schema')
    codes=[int(c) for c in g['codes']];N=len(codes);E=len(g['targets'])
    for key,dtype in {'codes':'uint32','index':'int32','rowptr':'uint32','targets':'uint32','actions':'int16','raw_parent':'int32','raw_parent_action':'int16'}.items():
        require(g[key].ndim==1 and g[key].dtype==np.dtype(dtype),'graph dtype '+key)
    require(N>0 and N<=model.universe and len(set(codes))==N and codes[0]==model.initial,'physical codes')
    require(g['index'].shape==(model.universe,) and g['rowptr'].shape==(N+1,),'dense/CSR shape')
    require(g['rowptr'][0]==0 and int(g['rowptr'][-1])==E and len(g['actions'])==E,'CSR endpoints')
    require(np.all(g['rowptr'][1:]>=g['rowptr'][:-1]) and E<=(3*model.n+1)*model.universe,'CSR monotonic/bound')
    require(g['raw_parent'].shape==(N,) and g['raw_parent_action'].shape==(N,),'raw parents shape')
    index={c:i for i,c in enumerate(codes)}
    for c in range(model.universe):require(int(g['index'][c])==index.get(c,-1),'dense index mismatch')
    adj=[];reverse=[[] for _ in codes];ends=[]
    for u,c in enumerate(codes):
        state=model.decode(c)
        require(all(x>=0 for x in model.free(state)),'physical buffer domain')
        require(model.encode(model.decode(c))==c,'state encoding')
        edges=[]
        for e in range(int(g['rowptr'][u]),int(g['rowptr'][u+1])):
            v=int(g['targets'][e]);a=int(g['actions'][e])
            require(0<=v<N and (a==-1 or 0<=a<model.n*model.base**2),'edge domain')
            edges.append((v,a))
            if a>=0:reverse[v].append(u)
        expected=[(index[nxt],action) for nxt,action in model.successors(c)]
        require(edges==expected,'physical successor completeness/order')
        require(len(edges)==len(set(edges)),'duplicate physical edge')
        adj.append(edges)
        if model.is_end(c):ends.append(u)
    validate_parents(adj,set(range(N)),g['raw_parent'],g['raw_parent_action'],'raw')
    for key in ('C','K','Rstar','A','R_RMBA','I','F'):
        require(s[key].shape==(N,) and s[key].dtype==np.dtype(bool),'Boolean set shape '+key)
    for key in ('task_completion_next','optimal_parent','optimal_parent_action','rmba_parent','rmba_parent_action'):
        require(s[key].shape==(N,),'certificate shape '+key)
        require(s[key].dtype==np.dtype('int16' if key.endswith('_action') else 'int32'),'certificate dtype '+key)
    require(s['certification_queries'].shape==(2,) and s['certification_queries'].dtype==np.dtype('uint64'),'certification counters')
    C=reverse_coaccess(reverse,ends)
    require(C==set(np.flatnonzero(s['C'])),'task-only C')
    K={u for u,c in enumerate(codes) if index[c&~1] in C}
    require(K==set(np.flatnonzero(s['K'])) and K<=C,'K down projection/subset')
    for u,c in enumerate(codes):require(s['K'][u]==s['K'][index[c^1]],'K environment closure')
    R=controlled(adj,s['K']);require(R==set(np.flatnonzero(s['Rstar'])),'actual optimal reachability')
    A=set()
    for u,c in enumerate(codes):
        value=reference_rmba(model,c)
        require(value==bool(s['A'][u]),'full FS RMBA saved label')
        if value:A.add(u)
    require(0 in A and A<=K,'A initial/soundness')
    for u,c in enumerate(codes):require(s['A'][u]==s['A'][index[c^1]],'A environment closure')
    RR=controlled(adj,s['A']);require(RR==set(np.flatnonzero(s['R_RMBA'])) and RR<=A&R,'actual RMBA reachability/subset')
    for name,within in (('Rstar',s['Rstar']),('R_RMBA',s['R_RMBA'])):
        require(reverse_coaccess(reverse,ends,within)==set(np.flatnonzero(within)),name+' task-only nonblocking')
    I={u for u,c in enumerate(codes) if model.is_initial_safe(c)}
    require(I==set(np.flatnonzero(s['I'])) and R-I==set(np.flatnonzero(s['F'])),'I/F labels')
    validate_parents(adj,R,s['optimal_parent'],s['optimal_parent_action'],'optimal')
    validate_parents(adj,RR,s['rmba_parent'],s['rmba_parent_action'],'rmba')
    for u in range(N):
        v=int(s['task_completion_next'][u])
        if u not in C or u in ends:require(v==-1,'completion endpoint certificate')
        else:require(v in C and any(w==v and a>=0 for w,a in adj[u]),'completion task certificate')
    for start in C:
        u=start;seen=set()
        while u not in ends:
            require(u not in seen and u in C,'completion certificate cycle');seen.add(u);u=int(s['task_completion_next'][u])
    return {'states':N,'edges':E,'full_FS_labels':N,'Rstar':len(R),'R_RMBA':len(RR),'eta_reach':len(RR)/len(R)}
