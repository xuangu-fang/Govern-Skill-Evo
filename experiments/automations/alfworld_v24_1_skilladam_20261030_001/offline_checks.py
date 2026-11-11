"""Offline scheduling and final-evaluation gate checks, with network prohibited."""
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import tempfile
from unittest.mock import patch

HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('scheduled_evaluation', HERE/'evaluate_skilladam.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
plan=module.load_plan(HERE/'plan.json')
checks=[]

def require_error(call):
    try: call()
    except (ValueError, FileNotFoundError): return
    raise AssertionError('Completion guard did not reject incomplete inputs')

with patch.object(socket.socket, 'connect', side_effect=AssertionError('Offline only')):
    for name, expected in plan['frozen_inputs_sha256'].items():
        assert hashlib.sha256(module.frozen_file(name).read_bytes()).hexdigest()==expected
    checks.append('authorized_inputs_match')
    assert plan['not_before_utc']=='2026-10-29T20:44:03Z'
    assert plan['monitor_interval_minutes']==30
    assert plan['recovery_policy']['extra_physical_requests_per_failed_call']==3
    assert plan['recovery_policy']['maximum_grants_per_call']==1
    for job in plan['jobs'].values():
        assert not (module.ROOT/job['training_output']).exists()
        assert not (module.ROOT/job['test_output']).exists()
    checks.append('both_training_and_test_outputs_absent')
    require_error(lambda: module.completed_skill(plan))
    checks.append('real_unstarted_training_rejects_test')
    from src.skill_evolution.v24_1 import evolution
    with tempfile.TemporaryDirectory() as tmp, patch.object(module,'ROOT',Path(tmp)), patch.object(evolution,'final_parent',return_value=Path(tmp)/'skill.md'):
        p={'jobs':{'v24_1':{'training_output':'v24','experiment':'vexp'},'skilladam':{'training_output':'sa'}}}
        def save(rel,data):
            q=Path(tmp)/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(data))
        cfg={'batches':[[]]*6}
        save('vexp/config/campaign.json',cfg);save('v24/config.json',cfg)
        save('v24/state.json',{'next_round':7})
        save('sa/completion.json',{'status':'complete','iterations':[{}]*6})
        checkpoint={'next_iteration':6,'pending_post_decision':None,'current_skill':'Frozen final skill'}
        save('sa/checkpoint.json',checkpoint);(Path(tmp)/'sa/final_skill.md').write_text('Frozen final skill')
        assert module.completed_skill(p)=='Frozen final skill'
        checks.append('both_complete_accepts_final_skill')
        save('v24/state.json',{'next_round':6});require_error(lambda:module.completed_skill(p))
        checks.append('incomplete_v24_rejects_test');save('v24/state.json',{'next_round':7})
        for edit in [{'pending_post_decision':{}},{'next_iteration':5},{'current_skill':'Wrong skill'}]:
            save('sa/checkpoint.json',{**checkpoint,**edit});require_error(lambda:module.completed_skill(p))
        checks.extend(['pending_momentum_rejects_test','incomplete_skilladam_rejects_test','wrong_final_skill_rejects_test'])
        save('sa/checkpoint.json',checkpoint);save('v24/config.json',{'batches':[[]]*5})
        require_error(lambda:module.completed_skill(p));checks.append('wrong_v24_configuration_rejects_test')
report={'passed':True,'checks':checks,'real_model_requests':0,'environment_episodes':0,'training_started':False,'test_started':False}
(HERE/'offline_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
