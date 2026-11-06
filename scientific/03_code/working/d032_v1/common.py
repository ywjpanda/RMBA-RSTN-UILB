import hashlib
import json
import os
import platform
import resource
import sys
from pathlib import Path
import psutil


def read(p):
    return json.loads(Path(p).read_text())


def write(p,x):
    p=Path(p)
    t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
    t.replace(p)


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rss():
    x=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(x if sys.platform=='darwin' else x*1024)


def environment():
    return {'python_executable':sys.executable,'python_version':sys.version,'platform':platform.platform(),
            'machine':platform.machine(),'cpu_count':os.cpu_count(),'physical_memory_bytes':psutil.virtual_memory().total,
            'psutil_version':psutil.__version__}
