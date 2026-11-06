import hashlib,json
def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf8')

def identity(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def events(instance,scenario):
    W=instance['n']*(instance['K']+2)
    assert W%2 == 0
    return {'N':{},'F':{W//2:0},'R':{W//2:0,W:1}}[scenario]
