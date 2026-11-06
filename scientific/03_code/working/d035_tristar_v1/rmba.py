"""D028 full FS/greedy MBA/RMBA with dynamic completion endpoint only.
No saved graph, labels, completion certificates or query sampling imports.
"""


class Certification:
    def __init__(self,model):self.model=model;self.cache={};self.queries=0;self.hits=0
    def fs(self,state,i):
        stack=[state];seen={state}
        while stack:
            current=stack.pop()
            if current[i]==self.model.done_pos:return True
            for nxt,action in self.model.app(current,i):
                if nxt not in seen:seen.add(nxt);stack.append(nxt)
        return False
    def mba(self,state):
        self.queries+=1
        if state in self.cache:self.hits+=1;return self.cache[state]
        current=state
        while True:
            todo=[i for i,p in enumerate(current[:-1]) if p!=self.model.done_pos]
            if not todo:answer=True;break
            for i in todo:
                if self.fs(current,i):
                    current=current[:i]+(self.model.done_pos,)+current[i+1:];break
            else:answer=False;break
        self.cache[state]=answer;return answer
    def accept(self,code):
        state=self.model.decode(code)
        if not self.mba(state):return False
        return self.mba(state[:-1]+(0,)) if state[-1] else True
