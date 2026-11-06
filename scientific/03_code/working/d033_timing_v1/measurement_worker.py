from release_support import rss_bytes
"""One isolated paired instance; saved labels remain outside scientific.py."""
import csv
import json
import mmap
import os
import resource
from pathlib import Path
import struct
import sys
import time
import traceback
import threading
import numpy as np
from common import ROOT, read, write, digest, queries, verify_binding, science_hashes
from model import Model
from scientific import timed_call


def run(task_path):
    task = read(task_path)
    out = Path(task_path).parent
    start = time.monotonic()
    def parent_guard():
        while True:
            time.sleep(0.5)
            if os.getppid() != task['parent_pid']:
                os._exit(143)
    threading.Thread(target=parent_guard, daemon=True).start()
    with (out / 'watch.bin').open('r+b') as wf:
        watch = mmap.mmap(wf.fileno(), 24)
        try:
            attempt, old_task = verify_binding(task['input'])
            model = Model(old_task['instance'])
            with np.load(attempt / 'graph.npz', allow_pickle=False) as graph:
                codes = graph['codes'].copy()
            with np.load(attempt / 'sets.npz', allow_pickle=False) as sets:
                rstar, K, A = (sets[key].copy() for key in ('Rstar', 'K', 'A'))
            q = queries(codes, rstar, task['split'], model.n, task['input']['seed'])
            query_hash = __import__('hashlib').sha256(json.dumps(q, separators=(',', ':')).encode()).hexdigest()
            lookup = {int(c): i for i, c in enumerate(codes)}
            counts = {'up': 0, 'down': 0, 'has_ready': 0, 'has_done': 0, 'all_done': 0, 'initial_safe': 0}
            for code in q:
                state = model.decode(code)
                counts['up' if code & 1 else 'down'] += 1
                counts['has_ready'] += int(0 in state[:-1])
                counts['has_done'] += int(7 in state[:-1])
                counts['all_done'] += int(all(p == 7 for p in state[:-1]))
                counts['initial_safe'] += int(all(p in (0, 7) for p in state[:-1]))
            write(out / 'queries.json', {'codes': q, 'sha256': query_hash, 'counts': counts, 'domain_size': int(rstar.sum()), 'input': task['input']})
            total = 0
            sums = {'RMBA': 0, 'Exact': 0}
            with (out / 'raw.csv').open('w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['round', 'position', 'code', 'method_order', 'method', 'answer', 'ns'])
                for rnd in range(4):
                    order = ('RMBA', 'Exact') if rnd in (0, 3) else ('Exact', 'RMBA')
                    sequence = q if rnd in (0, 3) else q[::-1]
                    for position, code in enumerate(sequence):
                        for ordinal, method in enumerate(order):
                            watch[:] = struct.pack('dQQ', time.monotonic(), total, 1 if method == 'RMBA' else 2)
                            answer, ns = timed_call(model, code, method)
                            watch[:] = struct.pack('dQQ', 0.0, total + 1, 0)
                            writer.writerow([rnd, position, code, ordinal, method, int(answer), ns])
                            expected = bool(A[lookup[code]]) if method == 'RMBA' else bool(K[lookup[code]])
                            if answer != expected:
                                f.flush()
                                raise RuntimeError(f'LABEL_MISMATCH {method} code={code} got={answer} expected={expected}')
                            sums[method] += ns
                            total += 1
            result = read(attempt / 'result.json')
            each = 4 * len(q)
            if each == 0 or sums['Exact'] <= 0:
                raise RuntimeError('invalid empty workload or nonpositive Exact mean')
            write(out / 'measurement.json', {'status': 'PASS', 'input': task['input'], 'science_hashes': science_hashes(), 'split': task['split'], 'n': model.n, 'seed': task['input']['seed'], 'query_sha256': query_hash, 'query_count': len(q), 'observations': total, 'eta_reach': result['eta_reach'], 'Rstar': result['Rstar'], 'R_RMBA': result['R_RMBA'], 'mean_ns': {m: sums[m] / each for m in sums}, 'ratio': sums['RMBA'] / sums['Exact'], 'worker_elapsed_s': time.monotonic() - start, 'worker_ru_maxrss_bytes': rss_bytes(), 'ru_maxrss_units': 'bytes; Linux KiB converted by adapter', 'query_counts': counts})
            write(out / 'worker_complete.json', {'files': {name: digest(out / name) for name in ('task.json', 'queries.json', 'raw.csv', 'measurement.json')}, 'science_hashes': science_hashes()})
            return 0
        except BaseException:
            write(out / 'worker_failure.json', {'status': 'EXCEPTION', 'elapsed_s': time.monotonic() - start, 'traceback': traceback.format_exc()})
            traceback.print_exc()
            return 2
        finally:
            watch.close()


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    sys.exit(run(sys.argv[1]))
