"""D032 V1, parameterization of D027 core; complete FS and unchanged Selector.
Physical state=(application positions, link); free buffers reconstruct uniquely.
"""
import hashlib
import random
import time
from collections import Counter


def derived_seed(*parts):
    return int.from_bytes(hashlib.sha256('|'.join(map(str, parts)).encode('utf8')).digest()[:8], 'big')


class Model:

    def __init__(self, instance):
        self.instance = instance
        self.n = instance['n']
        self.m = instance.get('m',len(instance['buffer_capacity_MB']))
        self.K = instance['K']
        self.stride = self.K+1
        self.done = 1+self.stride*self.m
        self.edges = {frozenset(e) for e in instance['edges_zero_based']}
        self.unreliable = frozenset(instance['unreliable_edge_zero_based'])
        self.sizes = tuple(tuple(a['data_sizes_MB']) for a in instance['applications'])
        self.access = tuple(a['access_satellite_zero_based'] for a in instance['applications'])
        self.caps = tuple(instance['buffer_capacity_MB'])
        assert len(self.sizes) == self.n and len(self.caps) == self.m
        assert all(len(s) == self.stride and all(isinstance(x, int) and x > 0 for x in s) for s in self.sizes)
        assert all(0 <= x < self.m for x in self.access)
        self.initial = (0,) * self.n + (1,)

    def free(self, state):
        free = list(self.caps)
        for i, p in enumerate(state[:-1]):
            if 0 < p < self.done:
                sat, phase = divmod(p-1, self.stride)
                free[sat] -= self.sizes[i][phase]
        return tuple(free)

    def valid(self, state):
        assert len(state) == self.n+1 and state[-1] in (0, 1)
        assert all(0 <= p <= self.done for p in state[:-1])
        assert all(0 <= x <= c for x,c in zip(self.free(state),self.caps))

    def app_successors(self, state, i):
        p = state[i]
        if p == self.done:
            return
        if p == 0:
            destinations = [(1+self.stride*self.access[i], 'upload')]
        else:
            sat, phase = divmod(p-1, self.stride)
            destinations = [(self.done if phase == self.K else p+1, 'download' if phase == self.K else 'execute')]
            if phase < self.K:
                for target in range(self.m):
                    edge = frozenset((sat,target))
                    if edge in self.edges and (state[-1] or edge != self.unreliable):
                        destinations.append((1+self.stride*target+phase, 'transfer'))
        for q, kind in destinations:
            successor = state[:i]+(q,)+state[i+1:]
            if min(self.free(successor)) >= 0:
                yield {'id': '%d:%d>%d' % (i, p, q), 'app': i, 'from': p, 'to': q,
                       'kind': kind, 'successor': successor}

    def candidates(self, state):
        return [a for i in range(self.n) for a in self.app_successors(state, i)]

    def remaining_peak(self, state):
        virtual = [0]*self.m
        for i, p in enumerate(state[:-1]):
            if 0 < p < self.done:
                sat, phase = divmod(p-1, self.stride)
                virtual[sat] += max(self.sizes[i][phase:])
        return virtual

    def stages(self, state):
        return sum(self.K if p == self.done else (p-1) % self.stride if p else 0 for p in state[:-1])


class Controller:
    """Caches belong to exactly one instance/method/scenario worker process.

    Only complete boolean MBA answers are cached; local FS searches run to
    exhaustion, never map a host limit/exception to rejection. Cache cap clears
    the whole cache (performance only); keys contain complete physical state.
    """
    def __init__(self, model, method="rmba", cache_limit=100000):
        self.model, self.method = model, method
        self.cache, self.stats = {}, Counter()
        self.cache_limit = cache_limit

    def fs(self, state, i):
        self.stats['fs_calls'] += 1
        stack, seen = [state], {state}
        while stack:
            current = stack.pop()
            self.stats['fs_expanded'] += 1
            if current[i] == self.model.done:
                return True
            for a in self.model.app_successors(current, i):
                nxt = a['successor']
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return False

    def mba(self, state):
        self.stats['mba_queries'] += 1
        if state in self.cache:
            self.stats['mba_hits'] += 1
            return self.cache[state]
        current = state
        while True:
            unfinished = [i for i, p in enumerate(current[:-1]) if p != self.model.done]
            if not unfinished:
                accepted = True
                break
            for i in unfinished:
                if self.fs(current, i):
                    current = current[:i]+(self.model.done,)+current[i+1:]
                    break
            else:
                accepted = False
                break
        if len(self.cache) >= self.cache_limit:
            self.cache.clear()
            self.stats['cache_clears'] += 1
        self.cache[state] = accepted
        self.stats['cache_peak_entries'] = max(self.stats['cache_peak_entries'], len(self.cache))
        return accepted

    def decide(self, state):
        start = time.perf_counter_ns()
        candidates = self.model.candidates(state)
        enumerated = time.perf_counter_ns()
        for a in candidates:
            nxt = a['successor']
            current = self.mba(nxt)
            if not current:
                allowed = False
                self.stats['rmba_current_false_short_circuit'] += 1
                checks = {'current': False, 'down': None, 'down_status': 'skipped_current_false'}
            elif nxt[-1]:
                self.stats['rmba_up_down_checks'] += 1
                down = self.mba(nxt[:-1]+(0,))
                allowed, checks = down, {'current': True, 'down': down, 'down_status': 'checked'}
            else:
                self.stats['rmba_already_down'] += 1
                allowed, checks = True, {'current': True, 'down': True, 'down_status': 'already_down'}
            a.update(allowed=allowed, checks=checks)
        allowed = [a for a in candidates if a['allowed']]
        finish = time.perf_counter_ns()
        return candidates, allowed, {'enumeration_successors_ns': enumerated-start,
                            'certification_and_set_ns': finish-enumerated,
                            'decision_ns': finish-start}


class Selector:
    def __init__(self, n, seed):
        self.n, self.seed = n, seed
        self.global_cursor = random.Random(seed).randrange(n)
        self.memory = {}
        self.max_actions = 0

    def select(self, state, allowed):
        first = state not in self.memory
        global_before = self.global_cursor
        if first:
            byapp = {}
            for a in allowed:
                byapp.setdefault(a['app'], []).append(a['id'])
            orders = {}
            for i, ids in sorted(byapp.items()):
                ids = sorted(ids)
                random.Random(derived_seed('D026-action-v1', self.seed, state, i)).shuffle(ids)
                orders[i] = ids
            self.memory[state] = {'cursor': self.global_cursor, 'orders': orders,
                                  'indices': {i: 0 for i in orders}, 'visits': 0}
            self.max_actions += len(allowed)
        record = self.memory[state]
        # Controller is a pure function: permitted IDs must remain identical.
        assert sorted(a['id'] for a in allowed) == sorted(x for ids in record['orders'].values() for x in ids)
        before = record['cursor']
        info = {'first_visit': first, 'global_before': global_before,
                'state_cursor_before': before, 'visits_before': record['visits']}
        record['visits'] += 1
        chosen = None
        for step in range(self.n):
            app = (before+step) % self.n
            order = record['orders'].get(app, [])
            if order:
                index = record['indices'][app]
                chosen = next(a for a in allowed if a['id'] == order[index])
                record['indices'][app] = (index+1) % len(order)
                record['cursor'] = self.global_cursor = (app+1) % self.n
                info.update(selected_app=app, action_order=order, action_cursor_before=index,
                            action_cursor_after=record['indices'][app])
                break
        info.update(state_cursor_after=record['cursor'], global_after=self.global_cursor)
        return chosen, info
