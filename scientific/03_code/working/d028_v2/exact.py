"""Independent finite physical graph, task-only coaccessibility and controlled BFS."""
from array import array
from collections import deque
import numpy as np
from rmba import Certification


def build(model,budget):
    budget.stage('graph');U=model.universe
    index=np.full(U,-1,np.int32);index[model.initial]=0;codes=array('I',[model.initial]);parent=array('i',[-1]);parent_action=array('h',[-2]);rowptr=array('I',[0]);targets=array('I');actions=array('h')
    u=0
    while u<len(codes):
        code=codes[u]
        for nxt,action in model.successors(code):
            if index[nxt]<0:
                index[nxt]=len(codes);codes.append(nxt);parent.append(u);parent_action.append(action)
                if len(codes)>U:raise RuntimeError('physical state bound exceeded')
            targets.append(int(index[nxt]));actions.append(action)
            if len(targets)>(2*model.n+1)*U:raise RuntimeError('physical edge bound exceeded')
        rowptr.append(len(targets));u+=1;budget.found=u
        if u%256==0:budget.check(force=True)
    return {'codes':np.array(codes,dtype=np.uint32),'index':index,'rowptr':np.array(rowptr,dtype=np.uint32),'targets':np.array(targets,dtype=np.uint32),'actions':np.array(actions,dtype=np.int16),'raw_parent':np.array(parent,dtype=np.int32),'raw_parent_action':np.array(parent_action,dtype=np.int16)}


def reverse_tasks(g,budget):
    N=len(g['codes']);counts=np.zeros(N,np.uint32)
    for v,a in zip(g['targets'],g['actions']):
        if a>=0:counts[v]+=1
    ptr=np.empty(N+1,np.uint32);ptr[0]=0;np.cumsum(counts,out=ptr[1:]);cursor=ptr[:-1].copy();src=np.empty(int(ptr[-1]),np.uint32);edge=np.empty(int(ptr[-1]),np.uint32)
    for u in range(N):
        for e in range(g['rowptr'][u],g['rowptr'][u+1]):
            if g['actions'][e]>=0:
                v=g['targets'][e];k=cursor[v];src[k]=u;edge[k]=e;cursor[v]+=1
        if u%256==0:budget.check(force=True)
    return ptr,src,edge


def coaccess(g,reverse,ends,budget,within=None):
    ptr,src,edge=reverse;found=np.zeros(len(g['codes']),bool);nxt=np.full(len(found),-1,np.int32);queue=deque()
    for u in ends:
        if within is None or within[u]:found[u]=True;queue.append(int(u))
    while queue:
        v=queue.popleft()
        for k in range(ptr[v],ptr[v+1]):
            u=int(src[k])
            if not found[u] and (within is None or within[u]):found[u]=True;nxt[u]=v;queue.append(u)
        budget.check()
    return found,nxt


def reachable(g,accepted,budget):
    N=len(g['codes']);found=np.zeros(N,bool);parent=np.full(N,-1,np.int32);parent_action=np.full(N,-2,np.int16)
    if not accepted[0]:raise RuntimeError('initial state not accepted')
    found[0]=True;queue=deque([0])
    while queue:
        u=queue.popleft()
        for e in range(g['rowptr'][u],g['rowptr'][u+1]):
            v=int(g['targets'][e]);a=int(g['actions'][e])
            if a<0:
                if not accepted[v]:raise RuntimeError('autonomous failure/recovery closure violation')
            elif not accepted[v]:continue
            if not found[v]:found[v]=True;parent[v]=u;parent_action[v]=a;queue.append(v)
        budget.check()
    return found,parent,parent_action


def analyze(model,g,budget):
    budget.stage('exact_certification');codes=g['codes'];ends=np.array([u for u,c in enumerate(codes) if model.is_end(int(c))],np.int32)
    reverse=reverse_tasks(g,budget);C,complete_next=coaccess(g,reverse,ends,budget)
    down=g['index'][codes&np.uint32(~1&0xffffffff)];K=C[down]
    if np.any(K & ~C):raise RuntimeError('down completion does not replay in up')
    flip=g['index'][codes^1]
    if not np.array_equal(K,K[flip]):raise RuntimeError('K not autonomous closed')
    R,opt_parent,opt_actions=reachable(g,K,budget)
    completion_R,_=coaccess(g,reverse,ends,budget,R)
    if not np.array_equal(completion_R,R):raise RuntimeError('R* not task-only nonblocking')
    cert=Certification(model);A=np.empty(len(codes),bool)
    for u,code in enumerate(codes):
        A[u]=cert.accept(int(code))
        if u%128==0:budget.check(force=True)
    if not A[0] or np.any(A & ~K) or not np.array_equal(A,A[flip]):raise RuntimeError('RMBA invariant/closure invalid')
    RR,rmba_parent,rmba_actions=reachable(g,A,budget)
    if np.any(RR&~(A&R)):raise RuntimeError('RMBA reachable not subset A and R*')
    completion_RR,_=coaccess(g,reverse,ends,budget,RR)
    if not np.array_equal(completion_RR,RR):raise RuntimeError('RMBA controlled task completion invalid')
    I=np.array([model.is_initial_safe(int(c)) for c in codes],bool);F=R&~I
    if not R.any():raise RuntimeError('empty R*')
    return {'C':C,'K':K,'Rstar':R,'A':A,'R_RMBA':RR,'I':I,'F':F,'task_completion_next':complete_next,'optimal_parent':opt_parent,'optimal_parent_action':opt_actions,'rmba_parent':rmba_parent,'rmba_parent_action':rmba_actions,'certification_queries':np.array([cert.queries,cert.hits],np.uint64)}
