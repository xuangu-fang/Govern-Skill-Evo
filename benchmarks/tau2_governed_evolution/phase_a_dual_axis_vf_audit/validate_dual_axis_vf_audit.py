"""Read-only consistency validation; no models, simulation or evaluators."""
import hashlib
import json
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
def read(name):return json.loads((P/name).read_text())
def validate():
    inv=read('historical_vf_inventory.json')
    assert len(inv['natural_records'])==7 and len(inv['latent_records'])==2
    assert sum(x['current_category']=='TRUE_DUAL_AXIS_HEADROOM' for x in inv['natural_records'])==6
    direct=read('direct_vf_candidate_audit.json')
    assert len(direct['candidates'])==4 and direct['new_tasks_to_add']==0
    for c in direct['candidates']:
        assert c['CO_SATISFIABLE'] and c['overlap_with_existing_benchmark']['TASK_OVERLAP']
        assert c['disposition']=='REUSE_EXISTING_TASK_DO_NOT_DUPLICATE'
    assert read('staged_vf_candidate_audit.json')['accepted_states']==0
    probes=read('native_backend_probes.json')
    assert probes['tool_calls']==12
    for r in probes['records']:
        if r['branch']=='correct_allocation':assert all(x['accepted'] for x in r['steps'])
        elif r['branch']=='consumed_reuse':assert not r['steps'][1]['accepted'] and not r['steps'][1]['certificate_present']
        else:assert r['payment_change_accepted']
    for f,h in read('source_provenance.json')['sha256'].items():
        assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,f
    f=P.parent/'phase_a_final_context'
    for name,h in json.loads((f/'freeze_manifest.json').read_text())['sha256'].items():
        assert hashlib.sha256((f/name).read_bytes()).hexdigest()==h,name
    b=read('dual_axis_vf_blueprint.json')
    assert all(v==0 for k,v in b['calls'].items() if k!='STATIC_NATIVE_BACKEND_PROBES')
    return {'valid':True,'historical_VF':9,'structural_reviews':8,'direct_supported_existing_states':4,'staged':0,'new_duplicate_tasks':0,'static_tool_probes':12,'model_calls':0,'Final_Context_unchanged':True}
if __name__=='__main__':print(json.dumps(validate(),indent=2))
