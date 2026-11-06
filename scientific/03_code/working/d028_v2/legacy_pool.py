"""AST-only bridge to the EXACT specified code_with_sample_all pool source.
No notebook top-level cells, random constructor or formal loop is executed.
The source algorithm bodies are retained; record return-line instrumentation
and wrappers only record provenance/budget, not decisions or traversal order.
"""
import ast
import copy
from collections import deque,Counter
from collections.abc import Mapping,Set
import gzip
import hashlib
import io
import json
from itertools import product
from pathlib import Path
import random
import time
from types import SimpleNamespace
import numpy as np
import pandas as pd
from bidict import bidict
from model import seed64,seed32

SOURCE=Path(__file__).with_name('pool_definitions.py')
CONFIG=Path(__file__).with_name('pool_config_definitions.py')
SOURCE_SHA=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
CONFIG_SHA=hashlib.sha256(CONFIG.read_bytes()).hexdigest()

class CopyMonitor:
    def __init__(self,budget):self.budget=budget
    def deepcopy(self,*args,**kwargs):self.budget.check();return copy.deepcopy(*args,**kwargs)
    def __getattr__(self,name):return getattr(copy,name)


class NumpyPrivate:
    def __init__(self,seed):self.random=np.random.RandomState(seed)
    def __getattr__(self,name):return getattr(np,name)


class PythonPrivate:
    def __init__(self,seed):self.rng=random.Random(seed)
    def __getattr__(self,name):return getattr(self.rng,name) if hasattr(self.rng,name) else getattr(random,name)


def definitions(code,ns,filename,instrument_return=False):
    tree=ast.parse(code,filename=filename)
    tree.body=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))]
    if instrument_return:
        for cls in tree.body:
            if isinstance(cls,ast.ClassDef) and cls.name=='App_Collection':
                method=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='record_1000_rob_comp_mk')
                class TraceReturns(ast.NodeTransformer):
                    def visit_Return(self,node):
                        marker=ast.Assign(targets=[ast.Attribute(value=ast.Name(id='self',ctx=ast.Load()),attr='_d028_return_line',ctx=ast.Store())],value=ast.Constant(node.lineno))
                        return [ast.copy_location(marker,node),node]
                TraceReturns().visit(method)
    ast.fix_missing_locations(tree);exec(compile(tree,filename,'exec'),ns)


class Pool:
    def __init__(self,model,q,threshold,out,budget):
        self.model,self.q,self.threshold,self.budget=model,q,threshold,budget
        self.out=Path(out);self.trace=gzip.open(self.out/('pool_q%d_trace.jsonl.gz'%q),'wt',encoding='utf8')
        self.query=None;self.fill=None;self.sequence=0;self.status_map=None
        self.py_seed=seed64('D028-pool-python-v1',model.n,model.instance['seed']);self.np_seed=seed32('D028-pool-numpy-v1',model.n,model.instance['seed'])
        private_np=NumpyPrivate(self.np_seed);private_py=PythonPrivate(self.py_seed)
        ns={'np':private_np,'random':private_py,'copy':CopyMonitor(budget),'time':time,'deque':deque,'Counter':Counter,'product':product,'bidict':bidict,'pd':pd,'Mapping':Mapping,'Set':Set}
        definitions(CONFIG.read_text(),ns,str(CONFIG))
        cfg=SimpleNamespace(Zm_LEO=2,Zn_App=model.n,Which_Connect=0,UnRliable_Link=(0,1),ENV_Trans_Max_Num=10,Sample_MK_Num=1000,Cunchu_Max_MK_Num=threshold)
        ns['cfg']=cfg;leo=ns['LEO_env_config'](cfg);ns['LEOconfig']=leo;cfg.DISCONNECT_TRANS=ns['find_all_disconnect_trans'](leo,cfg)
        definitions(SOURCE.read_text(),ns,str(SOURCE),False)
        apc=ns['App_Collection'].__new__(ns['App_Collection']);apc.app_number=model.n;apc.LEO_number=2;apc.p_LEO=np.array([40,40],int);apc.LEO_buffer_exe=apc.p_LEO.copy();apc.app_complete=np.zeros(model.n,int)
        apc.app_for_tasks=[]
        for sizes,access in zip(model.sizes,model.access):
            app=ns['App_straight'].__new__(ns['App_straight']);app.task_1=ns['Task'](sizes[0],sizes[1]);app.task_2=ns['Task'](sizes[1],sizes[2]);app.access_satellite=access;app.app_num=1;apc.app_for_tasks.append(app)
        apc.app_pn_for_qianzhi_matrix=[];apc.app_pn_for_pn_matrix=[];apc.generate_spc_apps_markings();apc.generate_pn();apc.generate_app_task_size_numpy()
        apc.app_start_marking_with_buffer=self.marking(model.initial);apc.one_marking_length_record=apc.marking_length_jilu(apc.app_start_marking_with_buffer)
        apc.all_safe_marking_set=set();apc.all_safe_marking_list=[];apc.initial_safe_marking_set=apc.Initial_safe_markings();apc.all_safe_marking_set=set(apc.initial_safe_marking_set)
        apc.correct_end_marking_list=[];apc.correct_end_marking_set=set();apc.generate_end_marking();apc.Cunchu_Max_MK_Num=threshold;apc.Sample_MK_Num=1000
        apc.ENV_Trans_Max_Num=10;self.apc=apc;self.ns=ns;self.np=private_np;self.py=private_py
        original_dict=ns['ValueCountingDict'];owner=self
        class TracedDict(original_dict):
            def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);owner.status_map=self;owner.log('cache_init',positive=self.counted_value_num,length=len(self))
            def __setitem__(self,key,value):
                super().__setitem__(key,value);owner.log('cache_write',code=owner.key_code(key),status=int(value),positive=self.counted_value_num,length=len(self),query=owner.query,fill=owner.fill)
        ns['ValueCountingDict']=TracedDict
        self.wrap('find_next_marking_list','outer_next')
        self.wrap('get_enabled_transitions','dfs_enabled')
        self.wrap('robust_nbba_pandaun','query')
        self.wrap('add_lujing_safe_marking_in_dict','fill')
        mapping=[]
        for i,(pre,inc) in enumerate(zip(apc.app_pn_for_qianzhi_matrix,apc.app_pn_for_pn_matrix)):
            for col in range(pre.shape[1]):
                src=np.flatnonzero(inc[:8,col]<0);dst=np.flatnonzero(inc[:8,col]>0)
                if len(src)!=1 or len(dst)!=1:raise RuntimeError('PN column not a one-token task action')
                mapping.append({'app':i,'column':col,'from':int(src[0]),'to':int(dst[0]),'pre_free':pre[-2:,col].tolist(),'delta_free':inc[-2:,col].tolist()})
        self.mapping=mapping
        # Construction is deterministic; explicitly reset both streams for each q.
        private_py.rng.seed(self.py_seed);private_np.random.seed(self.np_seed)
    def marking(self,code):
        state=self.model.decode(code);proc=[]
        for p in state[:-1]:
            row=np.zeros(8,int);row[p]=1;proc.append(row)
        return proc+[np.array(self.model.free(state),int),np.array([state[-1],1-state[-1]],int)]
    def key_code(self,key):
        positions=[]
        for row in key[:-2]:
            if sum(row)!=1 or any(x not in (0,1) for x in row):raise RuntimeError('non-single-token source key')
            positions.append(row.index(1))
        if tuple(key[-1]) not in ((1,0),(0,1)):raise RuntimeError('invalid source link')
        state=tuple(positions)+(int(key[-1][0]),)
        if tuple(key[-2])!=self.model.free(state):raise RuntimeError('source buffer violates conservation')
        return self.model.encode(state)
    def code(self,marking):return self.key_code(self.apc.decompose_marking_to_tuple(marking))
    def log(self,event,**fields):
        self.sequence+=1;self.trace.write(json.dumps(dict(seq=self.sequence,event=event,**fields),separators=(',',':'))+'\n');self.budget.check()
    def wrap(self,name,kind):
        original=getattr(self.apc,name)
        def wrapper(*args,**kwargs):
            code=self.code(args[0]);old_query=self.query;old_fill=self.fill
            if kind=='query':self.query=code;self.log('query_begin',code=code)
            if kind=='fill':self.fill=self.sequence+1;self.log('path_fill_begin',code=code,actions=[[int(v) for v in a] for a in args[1]])
            answer=original(*args,**kwargs)
            if kind=='outer_next':self.log(kind,code=code,successors=[self.code(m) for m in answer])
            elif kind=='dfs_enabled':self.log(kind,code=code,actions=[[int(v) for v in a] for a in answer])
            elif kind=='query':self.log('query_end',code=code,status=int(answer),positive=self.status_map.counted_value_num);self.query=old_query
            elif kind=='fill':self.log('path_fill_end',code=code);self.fill=old_fill
            return answer
        setattr(self.apc,name,wrapper)
    def run(self):
        result=self.apc.record_1000_rob_comp_mk(0);cache=result[-1]
        positives=sorted(self.key_code(k) for k,v in cache.items() if v==1)
        excluded=sorted(self.key_code(k) for k in self.apc.initial_safe_marking_set)
        P=sorted(set(positives)-set(excluded))
        meta={'q_percent':self.q,'B':0,'T':self.threshold,'positive_count':cache.counted_value_num,'cache_length':len(cache),'filtered_positive_count':len(set(positives)&set(excluded)),'P_codes':P,'positive_codes':positives,'statuses':[[self.key_code(k),int(v)] for k,v in cache.items()],'I_codes':excluded,'transition_fire_count':int(result[1]),'cache_write_count':int(result[2]),'popped_count':int(result[3]),'source_reported_seconds':float(result[4]),'source_return_line':int(self.apc._d028_return_line),'threshold_reached':bool(cache.counted_value_num>=self.threshold),'pool_python_seed':self.py_seed,'pool_numpy_seed':self.np_seed,'PN_column_mapping':self.mapping,'trace_events':self.sequence,'source_sha256':SOURCE_SHA,'config_sha256':CONFIG_SHA,'algorithm':'original AST bodies; record Return line assignment and observational wrappers only'}
        self.trace.close();return meta
