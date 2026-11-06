"""Stable uniform no-replacement samples and per-draw error decomposition."""
import gzip
import json
import math
import random
import statistics
from model import seed64


def variance(p,N,k):
    return 0.0 if N<=1 or k==N else p*(1-p)*(N-k)/(k*(N-1))


def calibrate(model,g,sets,pools,out,budget):
    budget.stage('sampling');index=g['index'];A=sets['A'];R=sets['Rstar'];RR=sets['R_RMBA'];F=sets['F'];codes=g['codes']
    full=sorted(int(c) for c in codes[R]);eta=int(RR.sum())/len(full);alpha_full=int((A&R).sum())/len(full);alpha_filtered=int((A&F).sum())/int(F.sum()) if F.any() else None
    labels=lambda c:bool(A[index[c]])
    draws={};grids=[];pool_counts=[]
    with gzip.open(out/'samples.jsonl.gz','wt') as stream:
        for pool in pools:
            q=pool['q_percent'];P=pool['P_codes'];p=sum(map(labels,P))/len(P) if P else None
            pool_counts.append({'q_percent':q,'N':len(P),'alpha_pool':p,'coverage_F':len(P)/int(F.sum()) if F.any() else None,'coverage_Rstar':len(P)/len(full),'alpha_pool_minus_filtered':p-alpha_filtered if p is not None and alpha_filtered is not None else None})
            settings=[('f10',10),('f30',30),('f60',60)]+([('k1000',None)] if model.n==6 else [])
            used={}
            for setting,f in settings:
                grid={'q_percent':q,'setting':setting,'repeats':10,'branches':['full','pool']}
                if not P or (f is None and len(P)<1000):
                    grid.update(status='NA',reason='empty_pool' if not P else 'pool_less_than_1000',k=None,branch_statistics=None);grids.append(grid);continue
                k=max(1,f*len(P)//100) if f is not None else 1000
                grid.update(status='valid',k=k,pool_sampling_kind='full_pool_count' if k==len(P) else 'finite_sample',alias_of=used.get(k))
                used.setdefault(k,setting);summaries={};references={}
                for branch,population,truth in [('full',full,alpha_full),('pool',P,p)]:
                    key=(branch,q if branch=='pool' else None,k)
                    if key not in draws:
                        rows=[]
                        for repeat in range(10):
                            parts=('D028-sample-full-v1',model.n,model.instance['seed'],k,repeat) if branch=='full' else ('D028-sample-pool-v1',model.n,model.instance['seed'],q,k,repeat)
                            seed=seed64(*parts);sample=random.Random(seed).sample(population,k);accepted=sum(map(labels,sample));rate=accepted/k
                            row={'sample_id':'%s-q%s-k%d-r%d'%(branch,key[1],k,repeat),'branch':branch,'q_percent':key[1],'k':k,'repeat':repeat,'seed':seed,'population_N':len(population),'population_alpha':truth,'codes':sample,'accepted':accepted,'estimate':rate,'sampling_error':rate-truth,'sampling_absolute_error':abs(rate-truth),'sampling_squared_error':(rate-truth)**2,'eta_error':rate-eta,'eta_absolute_error':abs(rate-eta),'eta_squared_error':(rate-eta)**2}
                            stream.write(json.dumps(row,separators=(',',':'))+'\n');rows.append(row);budget.check()
                        draws[key]=rows
                    rows=draws[key];references[branch]=[r['sample_id'] for r in rows];v=variance(truth,len(population),k)
                    summaries[branch]={'N':len(population),'p':truth,'mean_estimate':statistics.mean(r['estimate'] for r in rows),'mean_signed_sampling_error':statistics.mean(r['sampling_error'] for r in rows),'sampling_MAE':statistics.mean(r['sampling_absolute_error'] for r in rows),'sampling_RMSE':math.sqrt(statistics.mean(r['sampling_squared_error'] for r in rows)),'mean_signed_eta_error':statistics.mean(r['eta_error'] for r in rows),'eta_MAE':statistics.mean(r['eta_absolute_error'] for r in rows),'eta_RMSE':math.sqrt(statistics.mean(r['eta_squared_error'] for r in rows)),'actual_10_draw_sample_variance':statistics.variance(r['estimate'] for r in rows),'theoretical_single_draw_variance':v,'theoretical_MSE_to_eta':v+(truth-eta)**2}
                    if k==len(population) and any(r['sampling_error']!=0 for r in rows):raise RuntimeError('census sampling error nonzero')
                grid.update(sample_references=references,branch_statistics=summaries);grids.append(grid)
    return {'n':model.n,'seed':model.instance['seed'],'raw_states':len(codes),'Rstar':len(full),'R_RMBA':int(RR.sum()),'A_raw':int(A.sum()),'I':int(sets['I'].sum()),'F':int(F.sum()),'eta_reach':eta,'alpha_full':alpha_full,'alpha_filtered':alpha_filtered,'alpha_full_minus_eta':alpha_full-eta,'alpha_filtered_minus_full':alpha_filtered-alpha_full if alpha_filtered is not None else None,'certified_Rstar_but_unreachable_codes':sorted(int(c) for c in codes[A&R&~RR]),'raw_certified_unreachable_codes':sorted(int(c) for c in codes[A&~RR]),'pools':pool_counts,'comparison_grid':grids,'planned_grids':9 if model.n==3 else 12,'distinct_sample_records':sum(len(v) for v in draws.values()),'sampling_adapter':'sorted compact-code populations; Python Random.sample uniform without replacement; original source reservoir replaced only at sampling stage, not pool construction'}
