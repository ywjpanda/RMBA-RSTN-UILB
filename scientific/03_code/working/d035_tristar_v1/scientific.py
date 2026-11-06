"""D035 tristar online certifiers only. No saved graph, labels, I/O or RNG imports."""
from time import perf_counter_ns
from rmba import Certification

VERSION = 'D035_TRISTAR_SCIENCE_V1'


class ExactCertification:
    """Finite deterministic task-only DFS, current then necessary down check."""
    def __init__(self, model):
        self.model = model
        self.cache = {}
        self.visited_count = 0
        self.edge_count = 0

    def completable(self, state):
        if state in self.cache:
            return self.cache[state]
        stack = [state]
        visited = {state}
        while stack:
            current = stack.pop()
            self.visited_count += 1
            if all(p == self.model.done_pos for p in current[:-1]):
                self.cache[state] = True
                return True
            # APP ascending, then original app() yield order; LIFO reversed.
            successors = []
            for i in range(self.model.n):
                for nxt, action in self.model.app(current, i):
                    self.edge_count += 1
                    successors.append(nxt)
            for nxt in reversed(successors):
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        self.cache[state] = False
        return False

    def accept(self, code):
        state = self.model.decode(code)
        if not self.completable(state):
            return False
        return self.completable(state[:-1] + (0,)) if state[-1] else True


def timed_call(model, code, method, clock=perf_counter_ns, factories=None):
    """Clock encloses fresh object/cache, decode, search and Boolean return."""
    factories = factories or {'RMBA': Certification, 'Exact': ExactCertification}
    factory = factories[method]
    start = clock()
    certifier = factory(model)
    answer = certifier.accept(code)
    end = clock()
    if type(answer) is not bool:
        raise TypeError('certification did not return bool')
    elapsed = end - start
    if elapsed < 0:
        raise ValueError('negative timing observation ns=' + str(elapsed))
    return answer, elapsed
