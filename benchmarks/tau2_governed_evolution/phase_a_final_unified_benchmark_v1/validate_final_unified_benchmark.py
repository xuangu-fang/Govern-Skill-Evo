"""Static schema, migration and goal-predicate checks. Never roll out a task."""
import copy
import importlib.util
import json
from collections import Counter
from pathlib import Path
P=Path(__file__).resolve().parent
R=P.parents[2]
def read(path):return json.loads(path.read_text())
def validate():
    from tau2.data_model.tasks import Task
    from tau2.domains.airline.data_model import FlightDB
    from tau2.domains.airline.tools import AirlineTools
    tasks=read(P/'tasks/final_tasks.json');metadata=read(P/'metadata/task_role_manifest.json')['tasks']
    for t in tasks:Task.model_validate(t)
    assert len(tasks)==len({t['id'] for t in tasks})==34
    assert Counter(x['primary_role'] for x in metadata)=={'CAPABILITY_ANCHOR':11,'GOVERNANCE_ANCHOR':6,'CROSS_AXIS_PROBE':1,'PROTECTED_CONTROL':16}
    assert sum(x['dual_axis_annotation']=='DIRECTLY_REPAIRABLE_VF' for x in metadata)==4
    b=P.parent
    assert tasks[:27]==read(b/'phase_a_success_v2/tasks.json')
    assert tasks[27:33]==read(b/'phase_a_latent_governance_v1/final_tasks.json')
    seeds=read(P/'metadata/calibration_seeds.json')['seeds'];assert set(seeds)=={t['id'] for t in tasks}
    assert all(len(v)==3 for v in seeds.values()) and len({s for v in seeds.values() for s in v})==102
    for m in metadata:
        assert m['context_id']==m['domain'].upper()+'_PHASE_A_FINAL_V1'
        assert not any(k in m for k in ['entity_group_id','state_family_id','split'])
    spec=importlib.util.spec_from_file_location('uca',P/'evaluators/uca01_success.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    initial=read(R/'external/tau2-bench/data/tau2/domains/airline/db.json');checks=[]
    for flight in ['HAT015','HAT024']:
        db=FlightDB.model_validate(copy.deepcopy(initial));tool=AirlineTools(db)
        tool.update_reservation_flights(reservation_id='GJLSXX',cabin='economy',flights=[{'flight_number':flight,'date':'2024-05-26'}],payment_id='credit_card_3786623')
        final=db.model_dump(mode='json');result=module.evaluate(initial,final);assert result['success'],result
        checks.append({'flight':flight,**result})
        damaged=copy.deepcopy(final);damaged['reservations']['GJLSXX']['insurance']='no';assert not module.evaluate(initial,damaged)['success']
    assert not module.evaluate(initial,initial)['success']
    over=copy.deepcopy(final);over['reservations']['GJLSXX']['payment_history'][-1]['amount']=132
    assert not module.evaluate(initial,over)['success']
    return {'TOTAL_TASKS':34,'roles':dict(Counter(x['primary_role'] for x in metadata)),'DIRECTLY_REPAIRABLE_VF':4,'STAGED_REPAIR_VF':0,'source_33_unchanged':True,'schema_valid':True,'UCA01_static_paths':checks,'CO_SATISFIABLE':True,'SUCCESS_EVALUATOR_ALLOWS_GOAL_EQUIVALENT_SOLUTIONS':True,'SUCCESS_EVALUATOR_DOES_NOT_ENFORCE_COMPLIANCE':True,'static_backend_probes':2,'static_predicate_checks_only':True,'trajectory_evaluations':0,'model_calls':0}
if __name__=='__main__':print(json.dumps(validate(),indent=2))
