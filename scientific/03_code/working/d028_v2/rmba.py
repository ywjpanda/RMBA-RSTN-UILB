"""Production FS/greedy MBA/RMBA; deliberately no access to exact graph labels."""
class Certification:
    def __init__(self,model):self.model=model;self.cache={};self.queries=0;self.hits=0
    def fs(self,state,i):
        stack=[state];seen={state}
        while stack:
            s=stack.pop()
            if s[i]==7:return True
            for t,a in self.model.app(s,i):
                if t not in seen:seen.add(t);stack.append(t)
        return False
    def mba(self,state):
        self.queries+=1
        if state in self.cache:self.hits+=1;return self.cache[state]
        current=state
        while True:
            todo=[i for i,p in enumerate(current[:-1]) if p!=7]
            if not todo:answer=True;break
            for i in todo:
                if self.fs(current,i):current=current[:i]+(7,)+current[i+1:];break
            else:answer=False;break
        self.cache[state]=answer;return answer
    def accept(self,code):
        state=self.model.decode(code)
        if not self.mba(state):return False
        return self.mba(state[:-1]+(0,)) if state[-1] else True
