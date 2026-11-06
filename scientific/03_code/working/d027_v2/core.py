"""D027 m-satellite Linear model; position0 ground, 1+3*sat+phase resident,
done=1+3*m. Single specified unreliable edge only; remaining edges reliable.
FS/MBA/RMBA and state-memory selector preserve D026 V3 rules.
"""
import hashlib
import random
import time
from collections import Counter

METHODS = ('uncontrolled', 'mba_current', 'peak_remaining', 'rmba')
SCENARIOS = ('S0', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6')


def derived_seed(*parts):
    return int.from_bytes(hashlib.sha256('|'.join(map(str, parts)).encode()).digest()[:8], 'big')


def make_instance(m, n, seed):
    # Different n use explicitly independent hash-derived generation streams.
    rng = random.Random(derived_seed('D027-instance-v1', m, n, seed))
    return {'m': m, 'n': n, 'seed': seed, 'generation_seed': derived_seed('D027-instance-v1', m, n, seed),
            'buffer_capacity_MB': [40]*m, 'edges_zero_based': [[j,j+1] for j in range(m-1)],
            'unreliable_edge_zero_based': [0, 1] if m==2 else [1, 2],
            'applications': [{'data_sizes_MB': [rng.randint(10, 35) for _ in range(3)],
                              'access_satellite_zero_based': rng.randrange(m)} for _ in range(n)]}


def events(n, scenario):
    return {'S0': {}, 'S1': {n: 0}, 'S2': {2*n: 0}, 'S3': {3*n: 0},
            'S4': {2*n: 0, 3*n: 1}, 'S5': {2*n: 0, 4*n: 1},
            'S6': {2*n: 0, 6*n: 1}}[scenario]


class Model:

    def __init__(self, instance):
        self.instance = instance
        self.n = instance['n']
        self.m = instance.get('m',len(instance['buffer_capacity_MB']))
        self.done = 1+3*self.m
        self.edges = {frozenset(e) for e in instance['edges_zero_based']}
        self.unreliable = frozenset(instance['unreliable_edge_zero_based'])
        self.sizes = tuple(tuple(a['data_sizes_MB']) for a in instance['applications'])
        self.access = tuple(a['access_satellite_zero_based'] for a in instance['applications'])
        self.caps = (40,)*self.m
        assert all(len(s) == 3 and all(10 <= x <= 35 for x in s) for s in self.sizes)
        assert all(max(s) <= 40 for s in self.sizes)
        self.initial = (0,) * self.n + (1,)

    def free(self, state):
        free = [40]*self.m
        for i, p in enumerate(state[:-1]):
            if 0 < p < self.done:
                sat, phase = divmod(p-1, 3)
                free[sat] -= self.sizes[i][phase]
        return tuple(free)

    def valid(self, state):
        assert len(state) == self.n+1 and state[-1] in (0, 1)
        assert all(0 <= p <= self.done for p in state[:-1])
        assert all(0 <= x <= 40 for x in self.free(state))

    def app_successors(self, state, i):
        p = state[i]
        if p == self.done:
            return
        if p == 0:
            destinations = [(1+3*self.access[i], 'upload')]
        else:
            sat, phase = divmod(p-1, 3)
            destinations = [(self.done if phase == 2 else p+1, 'download' if phase == 2 else 'execute')]
            if phase < 2:
                for target in range(self.m):
                    edge = frozenset((sat,target))
                    if edge in self.edges and (state[-1] or edge != self.unreliable):
                        destinations.append((1+3*target+phase, 'transfer'))
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
                sat, phase = divmod(p-1, 3)
                virtual[sat] += max(self.sizes[i][phase:])
        return virtual

    def stages(self, state):
        return sum(2 if p == self.done else (p-1) % 3 if p else 0 for p in state[:-1])


class Controller:
    """Caches belong to exactly one instance/method/scenario worker process.

    Only complete boolean MBA answers are cached; local FS searches run to
    exhaustion, never map a host limit/exception to rejection. Cache cap clears
    the whole cache (performance only); keys contain complete physical state.
    """
    def __init__(self, model, method, cache_limit=100000):
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
        start = time.perf_counter()
        candidates = self.model.candidates(state)
        enumerated = time.perf_counter()
        for a in candidates:
            nxt = a['successor']
            if self.method == 'uncontrolled':
                allowed, checks = True, {}
            elif self.method == 'mba_current':
                current = self.mba(nxt)
                allowed, checks = current, {'current': current}
            elif self.method == 'peak_remaining':
                peak = self.model.remaining_peak(nxt)
                allowed, checks = max(peak) <= 40, {'virtual_MB': peak}
            elif self.method == 'rmba':
                current = self.mba(nxt)
                if not current:
                    # Algorithm 3 rejects immediately; skipped is not False/UNKNOWN.
                    allowed = False
                    checks = {'current': False, 'down': None, 'down_status': 'skipped_current_false'}
                else:
                    down = self.mba(nxt[:-1]+(0,)) if nxt[-1] else current
                    allowed, checks = down, {'current': current, 'down': down}
            else:
                raise ValueError(self.method)
            a.update(allowed=allowed, checks=checks)
        finish = time.perf_counter()
        return candidates, {'enumeration_successors_s': enumerated-start,
                            'certification_and_set_s': finish-enumerated,
                            'decision_s': finish-start}


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
