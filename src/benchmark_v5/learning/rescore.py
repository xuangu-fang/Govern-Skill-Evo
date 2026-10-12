"""Write separately versioned obligation corrections; raw experimental files stay untouched."""
import argparse
from collections import defaultdict
from pathlib import Path
from benchmark_v5.core import ROOT,verify_audit,canonical
from benchmark_v5.calibration.runner import read,write,sha,now
from .evaluation import evaluate as original
from .evaluation_revision import evaluate,VERSION


def rescore(directory):
    freeze=read(directory/'freeze.json');rows=[];groups=defaultdict(list)
    source=ROOT/'src/benchmark_v5/learning/evaluation_revision.py'
    for job in freeze['jobs']:
        folder=directory/job['id'];result=read(folder/'result.json')
        if not result['valid']:continue
        audit=read(folder/'audit.json');verify_audit(audit)
        assert original(audit)==result['score']
        score=evaluate(audit)
        assert all(score[k]==result['score'][k] for k in score if k not in ('P_complete','full_service'))
        row=dict(id=job['id'],kind=job['kind'],condition=job['condition'],budget_clean=result['budget_clean'],
            audit_sha256=sha(folder/'audit.json'),original_result_sha256=sha(folder/'result.json'),
            original_score=result['score'],corrected_score=score,
            changed_fields=[k for k in score if score[k]!=result['score'][k]])
        rows.append(row);groups[(job['kind'],job['condition'])].append(row)
    summary=[]
    for key,rr in sorted(groups.items()):
        clean=[r for r in rr if r['budget_clean']]
        summary.append(dict(kind=key[0],condition=key[1],n=len(rr),
            S=sum(r['corrected_score']['S'] for r in rr),
            C=None if key[0]=='LS1' else sum(r['corrected_score']['C'] for r in rr),
            SC=sum(r['corrected_score']['S'] and r['corrected_score']['C'] is not False for r in rr),
            original_full=sum(r['original_score']['full_service'] for r in rr),
            corrected_full=sum(r['corrected_score']['full_service'] for r in rr),
            budget_clean_n=len(clean),budget_clean_full=sum(r['corrected_score']['full_service'] for r in clean)))
    artifact=dict(grader_version=VERSION,created_at_utc=now(),grader_source_sha256=sha(source),
        results=rows,groups=summary,changed=[r['id'] for r in rows if r['changed_fields']])
    write(directory/'corrected_scores_v02.json',artifact)
    print(canonical({'grader':VERSION,'changed':artifact['changed'],'groups':summary}))
    return artifact

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path)
    rescore(parser.parse_args().directory)
