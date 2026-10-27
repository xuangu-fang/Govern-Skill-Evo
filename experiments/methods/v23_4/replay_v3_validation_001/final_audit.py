"""Aggregate saved receipts; no API invocation and no guessed missing usage."""
import hashlib
import json
from pathlib import Path

from experiments.methods.v23_4.archive_io import archive_glob, resolve, source_path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def read(p):return json.loads(resolve(p).read_text())
def sha(p):return hashlib.sha256(resolve(p).read_bytes()).hexdigest()

def main():
    rows=[]
    for root in (HERE,HERE/'round2'):
        for p in archive_glob(root/'runs', '*_replay/attempt_*'):
            a=read(p/'attempt.json')
            response=read(p/'response.json') if resolve(p/'response.json').exists() else {}
            rows.append({'path':str(source_path(p).relative_to(ROOT)),**a,'finish_reason':response.get('finish_reason'),
                         'usage':response.get('usage'),'request_sha256':sha(p/'http/request.json')})
    reported={k:sum((r['usage'] or {}).get(k,0) for r in rows) for k in ('prompt_tokens','completion_tokens','total_tokens')}
    missing=[r['path'] for r in rows if r['usage'] is None]
    protected=read(HERE/'protected_before.json')
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    for root in (HERE,HERE/'round2'):
        frozen=read(root/'config/freeze.json')
        assert all(sha(ROOT/p)==h for p,h in frozen['sha256'].items())
    assert (HERE/'v23_4_replay.md').read_bytes()==Path('/Users/didi/Downloads/v23_4_replay.md').read_bytes()
    result={'calls':rows,'http_attempts':len(rows),'logical_calls':3,
       'reported_usage_subtotal':reported,'attempts_without_usage':missing,
       'total_billed_tokens_known':not missing,
       'usage_note':'Missing usage is unknown, not zero; subtotal includes failed responses that returned usage.',
       'protected_files_unchanged':len(protected),'candidate_prompt_unchanged':True,
       'production_or_active_memory_modified':False,'semantic_retries':0,
       'second_round_type':'offline_controlled_sibling_edit_revision_NOT_natural_continuous_evolution',
       'first_legal_selection':{c:read(root/f'runs/{c}_replay/selected.json')['attempt']
          for c,root in [('R05',HERE),('R06',HERE),('ROUND2',HERE/'round2')]}}
    (HERE/'RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='calls'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
