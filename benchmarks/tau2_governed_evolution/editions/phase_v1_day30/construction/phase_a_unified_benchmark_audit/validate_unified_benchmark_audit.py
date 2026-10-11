"""Read-only JSON, source-integrity and arithmetic validation; no model calls."""
import hashlib
import json
from pathlib import Path
P = Path(__file__).resolve().parent
ROOT = P.parents[2]
def load(name):
    return json.loads((P / name).read_text())
def validate():
    roles = load('success_task_role_audit.json')['tasks']
    assert len(roles) == len({r['task_id'] for r in roles}) == 27
    assert sum(r['role']=='CAPABILITY_ANCHOR' for r in roles)==11
    assert sum(r['role']=='PROTECTED_CONTROL' for r in roles)==16
    audit=load('cross_axis_candidate_audit.json')
    assert len(audit['candidates'])==9 and audit['accepted_count']==1
    accepted=[c for c in audit['candidates'] if c['static_verdict']=='ACCEPT_CLEAN_COMPOSITION']
    assert len(accepted)==1 and accepted[0]['CO_SATISFIABLE']
    replay=load('native_backend_replay.json')['results']
    assert [r['actual_delta'] for r in replay]==[44,132,96]
    assert [r['reservation']['flights'][0]['destination'] for r in replay]==['EWR','EWR','LGA']
    assert 2*137-230==44 and 2*181-230==132 and 2*163-230==96
    for name,h in load('audit_provenance.json')['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
    final=P.parent/'phase_a_final_context'
    for name,h in json.loads((final/'freeze_manifest.json').read_text())['sha256'].items():
        assert hashlib.sha256((final/name).read_bytes()).hexdigest()==h,name
    blueprint=load('unified_benchmark_blueprint.json')
    assert sum(blueprint['counts'].values())==34
    assert all(v==0 for v in blueprint['model_calls'].values())
    assert blueprint['outcome_admission_used'] is False
    return {'valid':True,'tasks_audited':27,'cross_axis_proposals':9,'accepted':1,'context_freeze_unchanged':True,'model_calls':0}
if __name__=='__main__':
    print(json.dumps(validate(),indent=2))
