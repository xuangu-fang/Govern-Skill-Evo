"""Aggregate all predeclared episodes, without dropping observed business failures."""
from collections import defaultdict
from benchmark_v5.calibration.runner import read,write
from benchmark_v5.core import canonical
from .runner import DEST,check


def analyze():
    f=check();results=[read(DEST/j['id']/'result.json') for j in f['jobs']]
    grouped=defaultdict(list)
    for r in results:grouped[(r['kind'],r['condition'])].append(r)
    rows=[]
    for (kind,condition),rr in sorted(grouped.items()):
        valid=[r for r in rr if r['valid']]
        row=dict(kind=kind,condition=condition,n=len(rr),valid=len(valid),budget_clean=sum(r['budget_clean'] for r in rr))
        for metric in ('S','C','P_complete','full_service','first_decision_correct'):
            applicable=[r['score'][metric] for r in valid if r['score'][metric] is not None]
            row[metric]={'passed':sum(applicable),'total':len(applicable)}
        for metric in ('prediction_correct','prediction_total','prediction_covered','recoveries'):
            row[metric]=sum(r['score'][metric] for r in valid)
        row['strata']={s:{'passed':sum(r['score']['full_service'] for r in valid if r['score']['stratum']==s),
                         'total':sum(r['score']['stratum']==s for r in valid)}
                       for s in sorted({r['score']['stratum'] for r in valid})}
        row['usage']={k:sum(r['usage'][k] for r in rr) for k in ('prompt_tokens','completion_tokens','total_tokens','reasoning_tokens')}
        row['api_attempts']=sum(r['api_attempts'] for r in rr)
        rows.append(row)
    learning=[read(DEST/f'learning/{k}.json') for k in ('LS1','LG1')]
    summary=dict(groups=rows,episodes=len(results),valid=sum(r['valid'] for r in results),
        deviations=[{'id':r['id'],'deviations':r['deviations']} for r in results if not r['budget_clean']],
        invalid=[{'id':r['id'],'reason':r['failure_kind']} for r in results if not r['valid']],
        execution_usage={k:sum(r['usage'][k] for r in results) for k in ('prompt_tokens','completion_tokens','total_tokens','reasoning_tokens')},
        learning_usage={k:sum(l['usage'][k] for l in learning) for k in ('prompt_tokens','completion_tokens','total_tokens','reasoning_tokens')},
        api_attempts=sum(r['api_attempts'] for r in results)+sum(len(l['attempts']) for l in learning),
        unknown_usage_attempts=sum(r['unknown_usage_attempts'] for r in results)+sum('error' in a for l in learning for a in l['attempts']),
        failures=[dict(id=r['id'],score=r['score'],stop=r['stop']) for r in results if r['valid'] and not r['score']['full_service']])
    write(DEST/'analysis.json',summary)
    print(canonical(summary))
    return summary

if __name__=='__main__':analyze()
