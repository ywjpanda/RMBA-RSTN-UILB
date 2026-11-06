"""One fresh process/controller/Selector per instance/scenario; no search cap."""
import gzip
import json
import sys
import time
import traceback
from pathlib import Path
from core import Model,Controller,Selector
from instance import events,identity
from stats import summary
from common import read,write,rss


def run(task_path):
    started=time.perf_counter_ns()
    task=read(task_path)
    out=Path(task_path).parent
    inst=task['instance']
    model=Model(inst)
    cold=time.perf_counter_ns()
    initial=Controller(model)
    current=initial.mba(model.initial)
    down=initial.mba(model.initial[:-1]+(0,)) if current else None
    initial_ns=time.perf_counter_ns()-cold
    assert current is True and down is True, 'initial actual RMBA acceptance failed'
    initial_stats=dict(initial.stats)
    del initial
    controller=Controller(model)
    selector=Selector(model.n,inst['derived_seeds']['selector'])
    assert not controller.cache and not selector.memory
    state=model.initial
    W=model.n*(model.K+2)
    budget=16*W
    schedule=events(inst,task['scenario'])
    totals={'physical_candidates':0,'allowed_candidates':0,'rejected_candidates':0,'operations':0,
            'transfers':0,'transfer_MB':0,'idle':0,'empty_candidates':0,'nonempty_candidates':0}
    event_records=[]
    times=[]
    candidate_counts=[]
    buffer_peak=[0]*model.m
    buffer_sum=[0]*model.m
    completions=[None]*model.n
    status='slot_budget'
    slot=0
    trace_io=0
    timing_io=0
    event_total=0
    simulation_total=0
    with gzip.open(out/'trace.jsonl.gz','wt',encoding='utf8') as trace, (out/'timings.jsonl').open('w') as timing:
        for slot in range(1,budget+1):
            t=time.perf_counter_ns()
            before=state
            event=None
            if slot in schedule:
                state=state[:-1]+(schedule[slot],)
                event='recovery' if schedule[slot] else 'failure'
                event_records.append({'slot':slot,'event':event})
            event_ns=time.perf_counter_ns()-t
            event_total+=event_ns
            t=time.perf_counter_ns()
            model.valid(state)
            simulation_ns=time.perf_counter_ns()-t
            candidates,allowed,tm=controller.decide(state)
            t=time.perf_counter_ns()
            selected,selection=selector.select(state,allowed)
            selector_ns=time.perf_counter_ns()-t
            tm.update(selector_ns=selector_ns,decision_plus_selector_ns=tm['decision_ns']+selector_ns)
            t=time.perf_counter_ns()
            after=selected['successor'] if selected else state
            model.valid(after)
            free,after_free=model.free(state),model.free(after)
            occupied=[c-f for c,f in zip(model.caps,after_free)]
            for j,x in enumerate(occupied):
                buffer_peak[j]=max(buffer_peak[j],x)
                buffer_sum[j]+=x
            totals['physical_candidates']+=len(candidates)
            totals['allowed_candidates']+=len(allowed)
            totals['rejected_candidates']+=len(candidates)-len(allowed)
            totals['operations']+=int(selected is not None)
            totals['idle']+=int(selected is None)
            totals['empty_candidates']+=int(not candidates)
            totals['nonempty_candidates']+=int(bool(candidates))
            if selected and selected['kind']=='transfer':
                totals['transfers']+=1
                totals['transfer_MB']+=model.sizes[selected['app']][(selected['from']-1)%model.stride]
            for i,p in enumerate(after[:-1]):
                if p==model.done and completions[i] is None:
                    completions[i]=slot
            completed=sum(p==model.done for p in after[:-1])
            stages=model.stages(after)
            simulation_ns+=time.perf_counter_ns()-t
            simulation_total+=simulation_ns
            row={'slot':slot,'before_event':before,'event':event,'state':state,'free_MB':free,
                 'physical':candidates,'allowed_ids':[a['id'] for a in allowed],'selector':selection,
                 'selected':selected['id'] if selected else None,'after':after,'after_free_MB':after_free,
                 'completed_stages':stages,'completed_apps':completed,'controller_stats':dict(controller.stats),
                 'timings':dict(tm,event_ns=event_ns,simulation_ns=simulation_ns)}
            t=time.perf_counter_ns()
            trace.write(json.dumps(row,separators=(',',':'))+'\n')
            serialization_ns=time.perf_counter_ns()-t
            trace_io+=serialization_ns
            tm.update(slot=slot,event_ns=event_ns,simulation_ns=simulation_ns,serialization_io_ns=serialization_ns,
                      candidate_count=len(candidates),allowed_count=len(allowed),link=state[-1])
            t=time.perf_counter_ns()
            timing.write(json.dumps(tm,separators=(',',':'))+'\n')
            timing_io+=time.perf_counter_ns()-t
            times.append(tm)
            candidate_counts.append(len(candidates))
            state=after
            if completed==model.n:
                status='all_complete'
                break
    finish=time.perf_counter_ns()
    if status=='all_complete':
        assert slot==W+totals['transfers']+totals['idle']
    metrics=('decision_ns','selector_ns','decision_plus_selector_ns')
    summaries={k:summary([t[k] for t in times]) for k in metrics}
    subsets={name:{k:summary([t[k] for t in times if pred(t)]) for k in metrics} for name,pred in [
        ('empty',lambda t:t['candidate_count']==0),('nonempty',lambda t:t['candidate_count']>0),
        ('up',lambda t:t['link']==1),('down',lambda t:t['link']==0)]}
    by_count={str(c):{k:summary([t[k] for t in times if t['candidate_count']==c]) for k in metrics} for c in sorted(set(candidate_counts))}
    result={'schema':'D032_RESULT_V1','task_identity':identity(task),'config_id':inst['config_id'],
            'seed_label':inst['seed_label'],'scenario':task['scenario'],'instance_hash':identity(inst),
            'science_lock_hash':task['science_lock_hash'],'environment':task['environment'],
            'status':status,'valid_observation':True,'error':None,'W':W,'slot_budget':budget,
            'slots_executed':slot,'completed_apps':sum(p==model.done for p in state[:-1]),
            'completed_stages':model.stages(state),'completed_app_slots':completions,'last_state':state,
            'all_complete_slot':slot if status=='all_complete' else None,'events_seen':event_records,
            'events_not_reached':[{'slot':s,'link':x} for s,x in schedule.items() if s>slot],
            'initial_certification':{'current':current,'down':down,'time_ns':initial_ns,'stats':initial_stats},
            'online_initial_cache_entries':0,'first_decision_ns':times[0]['decision_ns'] if times else None,
            'timing_summaries':summaries,'timing_subsets':subsets,'timing_by_candidate_count':by_count,
            'candidate_count_summary':summary(candidate_counts),'totals':totals,
            'controller_stats':dict(controller.stats),'controller_cache_entries_final':len(controller.cache),
            'selector_states':len(selector.memory),'selector_stored_actions':selector.max_actions,
            'buffer_peak_MB':buffer_peak,'buffer_utilization_observed':[s/(c*slot) for s,c in zip(buffer_sum,model.caps)],
            'worker_wall_s':(finish-started)/1e9,'worker_cpu_s':time.process_time(),'worker_peak_rss_bytes':rss(),
            'time_components_ns':{'initial_certification':initial_ns,'event':event_total,'simulation':simulation_total,
                                  'trace_serialization_io':trace_io,'timing_sidecar_io':timing_io,
                                  **{k:sum(t[k] for t in times) for k in metrics}}}
    write(out/'result.json',result)
    return result


if __name__=='__main__':
    try:
        run(Path(sys.argv[1]))
    except BaseException:
        traceback.print_exc()
        sys.exit(2)
