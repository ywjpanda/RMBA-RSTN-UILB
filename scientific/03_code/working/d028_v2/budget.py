from release_support import rss_bytes
"""Sampled RSS/phase monitoring; limits are not OS hard memory isolation."""
import json
from pathlib import Path
import resource
import threading
import time
import psutil


class Limit(RuntimeError):pass


class Budget:
    def __init__(self,out,config):
        self.out=Path(out);self.config=config;self.start=time.monotonic();self.phase='startup';self.phase_start=self.start;self.stages={};self.current_peak=0;self.calls=0;self.found=0;self.error=None;self.closed=False;self.last_disk_check=0
        self.process=psutil.Process();self.thread=threading.Thread(target=self.monitor,daemon=True);self.thread.start()
    def monitor(self):
        while not self.closed:
            try:
                rss=self.process.memory_info().rss;self.current_peak=max(self.current_peak,rss)
                if time.monotonic()-self.last_disk_check>=1:
                    size=0
                    for f in self.out.rglob('*'):
                        try:
                            if f.is_file():size+=f.stat().st_size
                        except FileNotFoundError:pass
                    if size>self.config['instance_disk_bytes']:self.error='instance disk threshold'
                    self.last_disk_check=time.monotonic()
                data={'phase':self.phase,'phase_started_monotonic':self.phase_start,'heartbeat_monotonic':time.monotonic(),'worker_elapsed':time.monotonic()-self.start,'rss_bytes':rss,'found':self.found}
                p=self.out/'heartbeat.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(data));tmp.replace(p)
            except Exception as e:self.error=str(e)
            time.sleep(.1)
    def stage(self,name):
        self.finish();self.phase=name;self.phase_start=time.monotonic();self.current_peak=self.process.memory_info().rss;self.check(force=True)
    def finish(self):
        if self.phase!='startup':self.stages[self.phase]={'wall_s':time.monotonic()-self.phase_start,'rss_sample_peak_bytes':self.current_peak,'ru_maxrss_cumulative_bytes':rss_bytes()}
    def check(self,force=False):
        self.calls+=1
        if not force and self.calls%128:return
        now=time.monotonic();limit=self.config['phase_seconds'].get(self.phase,900)
        if now-self.phase_start>limit or now-self.start>self.config['worker_seconds']:raise Limit('time threshold '+self.phase)
        if self.error:raise Limit('monitor failure '+self.error)
        if self.process.memory_info().rss>self.config['worker_rss_bytes']:raise Limit('worker RSS threshold')
    def stop(self):self.finish();self.closed=True;self.thread.join(timeout=1)
