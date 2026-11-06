"""Truth worker cooperation. Parent independently enforces the same limits."""
import os
from pathlib import Path
import time
from support import write,rss,save_npz


class ResourceLimit(RuntimeError):pass


class Budget:
    def __init__(self,out,wall_s,rss_bytes,parent_pid):
        self.out=Path(out);self.wall_s=wall_s;self.rss_bytes=rss_bytes;self.parent_pid=parent_pid
        self.started=time.monotonic();self.stage_started=self.started;self.name='initializing'
        self.last=0;self.found=0;self.partial={};self.stages={}
    def stage(self,name):
        now=time.monotonic()
        self.stages[self.name]=self.stages.get(self.name,0)+now-self.stage_started
        self.name=name;self.stage_started=now;self.check(force=True)
    def check(self,force=False):
        now=time.monotonic()
        if not force and now-self.last<.1:return
        if os.getppid()!=self.parent_pid:raise ResourceLimit('parent process ended')
        if now-self.started>self.wall_s:raise ResourceLimit('truth worker wall limit')
        if rss()>self.rss_bytes:raise ResourceLimit('truth worker RSS limit')
        if force or now-self.last>=1:
            write(self.out/'heartbeat.json',{'stage':self.name,'elapsed_s':now-self.started,'found':self.found,'rss_hwm_bytes':rss()})
            self.last=now
    def finish(self):
        now=time.monotonic();self.stages[self.name]=self.stages.get(self.name,0)+now-self.stage_started
        return {'elapsed_s':now-self.started,'stages_wall_s':self.stages,'worker_peak_rss_bytes':rss()}
    def save_partial(self):
        if self.partial:save_npz(self.out/'partial_graph.npz',self.partial)
