"""Raw integer ns, nearest-rank p95; undefined summaries are None."""
import math
import statistics


def summary(values):
    x=sorted(values)
    if not x:
        return {'count':0,'mean':None,'median':None,'p95':None,'max':None}
    return {'count':len(x),'mean':statistics.mean(x),'median':statistics.median(x),
            'p95':x[math.ceil(.95*len(x))-1],'max':x[-1]}
