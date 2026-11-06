"""Exact accepted single-task worker API; no default batch launcher."""
import gzip, hashlib, json, os, platform, resource, subprocess, sys, time, traceback
from pathlib import Path
from core import Controller, METHODS, Model, SCENARIOS, Selector, derived_seed, events, make_instance
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def read(path):
    return json.loads(Path(path).read_text())

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    temporary.replace(path)

def rss_bytes():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(rss if sys.platform == 'darwin' else rss*1024)

def code_hashes():
    return {p.name: digest(p) for p in sorted(HERE.glob('*.py'))}

def worker(task_path):
    started = time.perf_counter()
    task = read(task_path)
    out = Path(task_path).parent
    instance = task['instance']
    m, n, seed = instance['m'], instance['n'], instance['seed']
    model = Model(instance)
    controller = Controller(model, task['method'], task['config']['cache_limit'])
    selector = Selector(n, task['selection_seed'])
    state = model.initial
    schedule = events(n, task['scenario'])
    limit = task['config']['slots_per_app']*n
    completed_slots = [None]*n
    timings = {k: 0.0 for k in ['decision_s', 'enumeration_successors_s',
                               'certification_and_set_s', 'permission_list_s', 'selector_s', 'simulation_s', 'write_s']}
    totals = {'physical_candidates': 0, 'rejected_candidates': 0, 'operations': 0,
              'transfers': 0, 'transfer_MB': 0, 'idle_slots': 0, 'no_physical_slots': 0,
              'repeated_state_slots': 0, 'no_progress_slots': 0,
              'down_slots': 0, 'down_idle_slots': 0, 'down_completed_stages': 0,
              'down_completed_apps': 0, 'max_candidates': 0, 'max_no_progress_streak': 0, 'max_idle_streak': 0}
    peaks, sums = [0]*m, [0]*m
    visits, stage_history, event_records = set(), [], []
    status, error, slot = 'slot_budget', None, 0
    idle_streak, no_progress_streak = 0, 0
    trace_path = out/'trace.jsonl.gz'
    try:
        with gzip.open(trace_path, 'wt', encoding='utf8') as trace:
            for slot in range(1, limit+1):
                if time.perf_counter()-started > task['config']['worker_wall_seconds']:
                    status = 'host_wall_limit'
                    slot -= 1
                    break
                if rss_bytes() > task['config']['rss_limit_bytes']:
                    status = 'host_rss_limit'
                    slot -= 1
                    break
                sim_start = time.perf_counter()
                before = state
                event = None
                if slot in schedule:
                    state = state[:-1]+(schedule[slot],)
                    event = 'recovery' if schedule[slot] else 'failure'
                    event_records.append({'slot': slot, 'event': event,
                                          'completed_apps_before': sum(p == model.done for p in state[:-1]),
                                          'completed_stages_before': model.stages(state)})
                model.valid(state)
                stages_before = model.stages(state)
                completed_before = sum(p == model.done for p in state[:-1])
                totals['repeated_state_slots'] += state in selector.memory
                visits.update((before, state))
                timings['simulation_s'] += time.perf_counter()-sim_start
                candidates, decision_timing = controller.decide(state)
                permission_start = time.perf_counter()
                allowed = [a for a in candidates if a['allowed']]
                permission_list_s = time.perf_counter()-permission_start
                decision_timing['permission_list_s'] = permission_list_s
                decision_timing['certification_and_set_s'] += permission_list_s
                decision_timing['decision_s'] += permission_list_s
                for key, value in decision_timing.items():
                    timings[key] += value
                selection_start = time.perf_counter()
                selected, selection = selector.select(state, allowed)
                selection_s = time.perf_counter()-selection_start
                timings['selector_s'] += selection_s
                sim_start = time.perf_counter()
                after = selected['successor'] if selected else state
                model.valid(after)
                free, after_free = model.free(state), model.free(after)
                occupied = [40-x for x in after_free]
                for j in range(m):
                    peaks[j] = max(peaks[j], occupied[j])
                    sums[j] += occupied[j]
                visits.add(after)
                totals['max_candidates'] = max(totals['max_candidates'], len(candidates))
                totals['physical_candidates'] += len(candidates)
                totals['rejected_candidates'] += len(candidates)-len(allowed)
                totals['idle_slots'] += not bool(allowed)
                totals['no_physical_slots'] += not bool(candidates)
                totals['operations'] += bool(selected)
                if selected and selected['kind'] == 'transfer':
                    totals['transfers'] += 1
                    totals['transfer_MB'] += model.sizes[selected['app']][(selected['from']-1) % 3]
                for i, p in enumerate(after[:-1]):
                    if p == model.done and completed_slots[i] is None:
                        completed_slots[i] = slot
                stages_after = model.stages(after)
                completed_after = sum(p == model.done for p in after[:-1])
                no_progress = stages_after == stages_before and completed_after == completed_before
                totals['no_progress_slots'] += no_progress
                no_progress_streak = no_progress_streak+1 if no_progress else 0
                idle_streak = idle_streak+1 if not allowed else 0
                totals['max_no_progress_streak'] = max(totals['max_no_progress_streak'], no_progress_streak)
                totals['max_idle_streak'] = max(totals['max_idle_streak'], idle_streak)
                if state[-1] == 0:
                    totals['down_slots'] += 1
                    totals['down_idle_slots'] += not bool(allowed)
                    totals['down_completed_stages'] += stages_after-stages_before
                    totals['down_completed_apps'] += completed_after-completed_before
                simulation_s = time.perf_counter()-sim_start
                timings['simulation_s'] += simulation_s
                row = {'slot': slot, 'before_event': before, 'event': event, 'state': state,
                       'free_MB': free, 'physical': candidates, 'allowed_ids': [a['id'] for a in allowed],
                       'selector': selection, 'selected': selected['id'] if selected else None,
                       'after': after, 'after_free_MB': after_free,
                       'completed_stages': stages_after, 'completed_apps': completed_after,
                       'timings': dict(decision_timing, selector_s=selection_s, simulation_s=simulation_s)}
                writing = time.perf_counter()
                trace.write(json.dumps(row, separators=(',', ':'))+'\n')
                timings['write_s'] += time.perf_counter()-writing
                stage_history.append(stages_after)
                state = after
                if all(p == model.done for p in state[:-1]):
                    status = 'all_complete'
                    break
    except KeyboardInterrupt:
        status, error = 'interrupted', 'KeyboardInterrupt'
    except BaseException:
        status, error = 'implementation_error', traceback.format_exc()
    finished = time.perf_counter()
    valid_observation = status in ('all_complete', 'slot_budget')
    result = {'m': m, 'n': n, 'seed': seed, 'method': task['method'], 'scenario': task['scenario'],
              'selection_seed': task['selection_seed'], 'status': status, 'error': error,
              'slots_executed': slot, 'slot_budget': limit, 'completed_app_slots': completed_slots,
              'completed_apps': sum(p == model.done for p in state[:-1]), 'completed_fraction': sum(p == model.done for p in state[:-1])/n,
              'completed_stages': model.stages(state), 'last_state': state,
              'all_complete_slot': slot if status == 'all_complete' else None,
              'events_seen': event_records,
              'events_not_reached': [{'slot': s, 'link': x} for s, x in schedule.items() if s > slot],
              'totals': totals, 'timings': timings, 'worker_wall_s': finished-started,
              'cpu_s': time.process_time(), 'peak_rss_bytes': rss_bytes(),
              'visited_physical_states': len(visits), 'selector_states': len(selector.memory),
              'selector_stored_action_ids': selector.max_actions,
              'controller_cache_entries_final': len(controller.cache), 'controller_stats': dict(controller.stats),
              'buffer_peak_MB': peaks,
              'buffer_utilization_fixed_window': [x/(40*limit) for x in sums] if valid_observation else None,
              'buffer_utilization_observed_slots': [x/(40*slot) for x in sums] if slot else None,
              'utilization_definition': 'post-task occupied_MB / capacity; common 64n window; after all-complete 0; resource/error unknown',
              'max_candidates': totals['max_candidates'], 'task_path': str(task_path), 'task_sha256': digest(task_path),
              'code_hashes': task['code_hashes'], 'cache_scope': 'cold per instance/method/scenario subprocess',
              'classification': 'budget noncompletion/observed inactivity only; no global impossibility inferred'}
    write(out/'result.json', result)
    return 0 if valid_observation else 2
