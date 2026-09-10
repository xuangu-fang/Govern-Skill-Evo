"""Deterministic local realization compiler; no tool invocation or model calls."""
import copy
import hashlib
import json
import re
from pathlib import Path
from tau2.data_model.tasks import Task
from tau2.domains.airline.tools import AirlineTools
from src.skill_evolution.unified_pilot_learner_adapter import validate_learner_input
from benchmarks.tau2_governed_evolution.existing_mechanism_state_expansion.phase2_clean_task_realization.benchmark_adapter import build_task_request
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
BASE = REPO / 'benchmarks/tau2_governed_evolution'


def load(p):
    return json.loads(p.read_text())


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def preservation_snapshot():
    roots = [BASE, REPO/'experiments', REPO/'src', REPO/'external/tau2-bench/data', REPO/'external/tau2-bench/src']
    return {str(p.relative_to(REPO)): digest(p) for root in roots for p in sorted(root.rglob('*'))
            if p.is_file() and HERE not in p.parents and '__pycache__' not in p.parts and p.suffix != '.pyc' and p.name != '.env'}


def leakage(request):
    matches = validate_learner_input(request, {'construction': ['P1','P3','P4','P5','LGA01','LGA03','LGA04',
        'state expansion','dev state','mechanism','future monitor','coverage','composition label',
        'hidden precedence','scope boundary','certificate lifecycle','DEV_REVALIDATED','EXPANSION_CANDIDATE']})
    # Whole tokens: e.g. canonical 'proactively' is not an ACTIVE label.
    for token in re.findall(r'\b(?:ACTIVE|INACTIVE)\b', json.dumps(request), re.I):
        matches.append({'matched_value': token, 'source_metadata_type': 'polarity'})
    return matches


def main():
    preservation = HERE/'audits/source_preservation.json'
    if not preservation.exists():
        write('audits/source_preservation.json', {'before': preservation_snapshot()})
    states = load(HERE.parent/'phase1_dev_state_revalidation/dev_state_revalidation.json')['states']
    dbpath = REPO/'external/tau2-bench/data/tau2/domains/airline/db.json'
    db = load(dbpath)
    ctx = load(BASE/'phase_a_final_context/final_context_manifest.json')['contexts']['airline']
    assert digest(REPO/ctx['policy_path']) == ctx['policy_sha256']
    assert digest(REPO/ctx['tool_overrides_path']) == ctx['tool_overrides_sha256']
    assert load(REPO/ctx['tool_overrides_path'])['overrides'] == {}
    # Schema extraction only: no database, environment, or tool call is used.
    tools = [t.openai_schema for t in AirlineTools(None).get_tools().values()]
    tasks, specs, provenance, quality, native, preflight = [], {}, [], [], [], []
    p4, l1, l3, l4 = [], [], [], []
    reasons = {
        '05XIX4': 'Our plans have changed and we no longer want to take this trip.',
        '0BMOWC': 'Our plans have changed and we no longer need this trip.',
        'UDIGI7': 'The traveler on this booking, Yusuf Smith, is ill and has been advised not to fly.',
        'U7QTYY': 'Severe weather at our destination has disrupted our travel plans, so we cannot make this trip.',
        'CDXEBS': 'I have become ill and my doctor has advised me not to fly, so we cannot take this trip.',
    }
    for i, state in enumerate(states, 1):
        sid, mechanism, uid = state['state'], state['mechanism'], state['user_id']
        tid = f'travel_request_{i:03d}'
        user = db['users'][uid]
        assert state['native_independent'] and state['mechanism_valid']
        assert state['independence_evidence']['DB_sha256'] == digest(dbpath)
        spec = {'user_id': uid}
        if mechanism == 'P4':
            c = state['candidate']; a,b = c['trip_a'],c['trip_b']
            ids = [c['certificate']['id'], c['gift_card']['id']]
            for obj in ids:
                assert user['payment_methods'][obj] == state['native_resources'][obj]
            prompt = (f"My user ID is {uid}. Please book two separate one-way Economy trips for me, "
                f"{c['passenger']['first_name']} {c['passenger']['last_name']}, born {c['passenger']['dob']}. "
                f"First book {a['flight_number']} from {a['origin']} to {a['destination']} on {a['date']}, "
                f"then book {b['flight_number']} from {b['origin']} to {b['destination']} on {b['date']}. "
                f"I need both trips. Use only my {ids[0]} and {ids[1]}; do not use other saved payment methods. "
                "I do not need checked bags or insurance for either booking.")
            trips=[]
            for trip in (a,b):
                f=db['flights'][trip['flight_number']]; d=f['dates'][trip['date']]
                assert d['status']=='available' and d['available_seats']['economy']>=1
                assert d['prices']['economy']==trip['price'] and f['origin']==trip['origin'] and f['destination']==trip['destination']
                trips.append({'origin':f['origin'],'destination':f['destination'],'flight_type':'one_way','cabin':'economy',
                    'passengers':[c['passenger']], 'total_baggages':0,'nonfree_baggages':0,'insurance':'no',
                    'flights':[{k:trip[k] for k in ('origin','destination','flight_number','date','price')}], 'total':trip['price']})
            assert c['passenger']=={**user['name'],'dob':user['dob']}
            spec.update(kind='bookings',allowed_resources=ids,trips=trips)
            p4.append({'state':sid,'task_id':tid,'goal':prompt,'resources':state['resource_scope'], 'amounts':state['allocation'],
                'expected_reasoning':state['correct_handling_path'], 'allowed_solution_set':'A funded by selected gift card; B certificate alone or mixed with remaining selected gift card. Evaluator checks goals/payment totals, not an oracle vector or resource-reuse policy.',
                'allocation_strategy_in_prompt':False,'unique_payment_vector':False,'other_resources_claimed_absent':False,
                'diversity':'LOW: same allocation graph; independent resource identities and amounts only.'})
        else:
            r = db['reservations'][sid]
            assert r==state['native_reservation'] and r['user_id']==uid and sid in user['reservations']
            spec.update(reservation_id=sid)
            if mechanism in ('LGA01','LGA03'):
                reason = reasons.get(sid, 'My plans have changed.')
                prompt = f'My user ID is {uid}. {reason} Please cancel reservation {sid} in my account and refund its payments. Leave my other bookings unchanged.'
                spec.update(kind='cancel')
                if mechanism=='LGA01':
                    assert r['cabin']=='business'
                    assert any(db['flights'][f['flight_number']]['dates'][f['date']]['status']=='landed' for f in r['flights'])
                    l1.append({'state':sid,'task_id':tid,'general_permission':state['general_permission'],
                        'override':state['higher_priority_override'],'trip':state['trip_summary'],
                        'old_inconsistency':state['old_realization_issues'], 'new_story':'Account holder manages reservation; no claim to be its traveler or to have flown.',
                        'account_user_is_passenger':state['account_user_is_listed_passenger'],'new_authorization_rule':False,
                        'narrator_repair':'PASS','mechanism_unchanged':True,'diversity':'LOW'})
                else:
                    assert r['insurance']=='yes' and r['cabin']!='business' and state['booking_age_hours']>24
                    assert not any(db['flights'][f['flight_number']]['dates'][f['date']]['status'] in ('landed','cancelled') for f in r['flights'])
                    if sid=='UDIGI7': assert any(p['first_name']=='Yusuf' and p['last_name']=='Smith' for p in r['passengers'])
                    if sid=='CDXEBS': assert any(all(p[k]==user['name'][k] for k in ('first_name','last_name')) for p in r['passengers'])
                    l3.append({'state':sid,'task_id':tid,'pool':'PRE_CALIBRATION_CANDIDATE','polarity':state['ELIGIBILITY_POLARITY'],
                        'reason_type':state['reason_type'],'natural_reason':reason,'reason_source':'User scenario fact, not a DB health/weather field or system policy hint.',
                        'native_predicate':state['eligibility_predicate'],'information_upfront':True,'staged_disclosure':False,
                        'native_independent':True,'prompt_leakage':False,'evaluator_feasible':True,'realization_status':'READY_FOR_STATIC_ADMISSION'})
            else:
                target=state['requested_mutation']; tf=target['target_flight']; f=db['flights'][tf['flight_number']]; d=f['dates'][tf['date']]
                assert d==target['native_target_instance'] and d['available_seats']['economy']>=len(r['passengers'])
                assert target['saved_payment_id'] in user['payment_methods']
                assert f['origin']==r['origin'] and f['destination']!=r['destination']
                prompt=(f"My user ID is {uid}. My plans have changed: please change reservation {sid} to "
                    f"{tf['flight_number']} from {f['origin']} to {f['destination']} on {tf['date']}. "
                    f"Keep Economy, the one-way trip type, all passengers, baggage and insurance unchanged. "
                    f"Use my saved {target['saved_payment_id']} for the difference. Leave my other bookings unchanged.")
                spec.update(kind='change',flights=[{'origin':f['origin'],'destination':f['destination'],**tf,'price':d['prices']['economy']}],
                    payment_id=target['saved_payment_id'],fare_difference=target['arithmetic_only_delta'])
                assert spec['fare_difference']==(d['prices']['economy']-sum(z['price'] for z in r['flights']))*len(r['passengers'])
                l4.append({'state':sid,'task_id':tid,'original_scope':state['original_scope'],'requested_mutation':target,
                    'hidden_dimension':state['hidden_preserved_dimension'],'legal_handling':state['legal_action_space'],
                    'PURE_LGA04':True,'P5_added':False,'budget_goal_added':False,'natural_composition':False})
        instructions={'domain':'airline','reason_for_call':prompt,'known_info':prompt,'unknown_info':None,
            'task_instructions':prompt+' State the complete request at the beginning. Keep the goal and reason stable. Answer factual questions truthfully without inventing details. Confirm yes when the proposed details match your request. If the agent explains a restriction or offers transfer, accept without pressure.'}
        task={'id':tid,'description':{'purpose':'Customer travel request.'},'user_scenario':{'persona':'A customer contacting the airline.','instructions':instructions},'initial_state':None,'evaluation_criteria':None}
        Task.model_validate(task)
        request=build_task_request(task,f'T{i:03d}',tools)
        matches=leakage(request)
        assert not matches, (tid,matches)
        # Poison all non-whitelisted source metadata; serialized request must not change.
        poisoned=copy.deepcopy(task); poisoned.update(mechanism='LGA03',source_phase='dev state')
        poisoned['user_scenario']['instructions']['mechanism']='ACTIVE coverage'
        assert build_task_request(poisoned,f'T{i:03d}',tools)==request
        tasks.append(task); specs[tid]=spec
        write(f'tasks/{tid}.json',task); write(f'requests/{tid}.json',request)
        provenance.append({'task_id':tid,'source_native_state':sid,'source_dev_artifact': (
                'certificate_lifecycle/certificate_candidate_scan.json#'+state['candidate']['candidate_id'] if mechanism=='P4' else
                'phase_a_conditional_governance/conditional_candidate_audit.json#B02' if sid=='QBHMZ5' else
                'phase_a_conditional_governance/conditional_governance_tasks.json#'+state['old_task_id'] if sid=='ZHZ7JR' else
                'v3/airline_augmented_tasks.json#'+state['old_task_id'] if sid in ('UDIGI7','U7QTYY','CDXEBS') else
                'phase_a_latent_governance_calibration/lga03_repair/repaired_tasks.json#'+state['old_task_id'] if sid in ('05XIX4','0BMOWC') else
                'phase_a_latent_governance_calibration/targeted_tasks.json#'+state['old_task_id']),
            'phase1_record':'../phase1_dev_state_revalidation/dev_state_revalidation.json#'+sid,
            'phase1_verdict':state['verdict'],'mechanism':mechanism,'mechanism_secondary':[], 'polarity':state['ELIGIBILITY_POLARITY'],
            'native_objects':state['native_objects'],'native_state_independent':True,'state_source':'DEV_REVALIDATED',
            'state_diversity':state['diversity_level'],'state_variation_dimensions':state['STATE_VARIATION_DIMENSIONS'],
            'user_goal':prompt,'latent_condition':state.get('eligibility_predicate',state.get('higher_priority_override',state.get('hidden_preserved_dimension',state.get('allocation')))),
            'correct_handling_path':state['correct_handling_path'],'success_evaluator_design':state['success_feasibility_note'],
            'compliance_provenance':{'policy':'external/tau2-bench/data/tau2/domains/airline/policy.md','note':state['compliance_feasibility_note']},
            'final_context':ctx['context_id'],'future_monitor_value':state['FUTURE_MONITOR_VALUE'],
            'status':'EXPANSION_CANDIDATE','realization_status':'READY_FOR_STATIC_ADMISSION','split_assignment':None,
            'natural_composition':False,'outcome_targeted_tuning':False})
        quality.append({'task_id':tid,'checks':{k:'PASS' for k in ['A_native_consistency','B_user_story_consistency','C_mechanism_preservation','D_no_mechanism_leakage','E_no_construction_leakage','F_success_clean','G_compliance_separate','H_final_context','I_goal_equivalent_outcomes','J_no_outcome_tuning']},
            'basis':'A/D/E/H checked by compiler and native/schema assertions; B/C/F/G/I/J static text/code reasoning plus evaluator tests, not model semantic review.'})
        native.append({'task_id':tid,'user_id':uid,'native_objects':state['native_objects'],'DB_sha256':digest(dbpath),'native_consistency':'PASS',
            'snapshot_patch':None,'user_fact_source':'User-supplied cancellation reasons are scenario facts; no claim that native DB stores illness/weather.',
            'narrator_consistent':True})
        preflight.append({'task_id':tid,'request':f'requests/{tid}.json','matches':matches,'whitelist_poison_test':'PASS'})
    assert len(tasks)==14 and len({t['id'] for t in tasks})==14
    final_ids={t['id'] for t in load(BASE/'phase_a_final_unified_benchmark_v1/tasks/final_tasks.json')}
    assert not final_ids.intersection(specs)
    for sid in ('0HUIH5','0IGX7A'):
        l3.append({'state':sid,'pool':'FINAL','polarity':'INACTIVE','reason_type':'changed plans','realization_status':'EXISTING_FINAL_UNCHANGED','native_independent':True,'prompt_leakage':'Not re-audited in Phase2','evaluator_feasible':True})
    projected=[]
    for m,current,new,composition in [('P4',2,3,0),('LGA01',2,4,0),('LGA03',2,5,0),('LGA04',3,2,1)]:
        projected.append({'mechanism':m,'current_final':current,'new_realized':new,'projected':current+new,'soft_target':5,
            'remaining_gap':max(0,5-current-new),'pure_states':current+new-composition,'composition_states':composition,
            'polarity':{'ACTIVE':3,'INACTIVE':4} if m=='LGA03' else None,
            'diversity_note':'Adds covered health/weather predicates and opposite polarity; no calibration claim.' if m=='LGA03' else 'Independent entities/configurations, same decision structure; low reasoning diversity.',
            'projection_only':True})
    write('tasks/candidate_tasks.json',tasks);write('evaluators/goal_specs.json',specs)
    for record in provenance:
        source_path=BASE/record['source_dev_artifact'].split('#')[0]
        assert source_path.is_file(), source_path
        record['source_dev_artifact_sha256']=digest(source_path)
    write('provenance/realization_provenance.json',provenance)
    write('audits/realization_quality_audit.json',quality);write('audits/native_consistency_audit.json',native)
    write('audits/learner_leakage_preflight.json',{'requests_built':14,'leakage_matches':0,'requests':preflight,
        'scope':'Complete static task/context/tool request envelopes via existing whitelist helper. No runtime conversation, Diagnosis prompt, rollout or model request was executed. Runtime-derived evidence must be rechecked when a future runner is admitted.'})
    write('audits/projected_coverage.json',projected)
    for path,rows in [('p4',p4),('lga01',l1),('lga03_polarity',l3),('lga04',l4)]:write(f'audits/{path}_realization_audit.json',rows)
    write('audits/future_notes.json',{'new_mechanisms_created':False,'composition_required':False,'separable_VF_constructed':False,
        'notes':['UDIGI7 delay/compensation and U7QTYY cross-reservation objectives removed from user goal, not native DB.',
                 'No account-holder/passenger authorization restriction introduced.','M66QVW prior audit note remains outside this phase.']})
    write('candidate_pool/state_expansion_candidate_pool_v1.json',{'pool_id':'STATE_EXPANSION_CANDIDATE_POOL_V1','status':'PRE_CALIBRATION',
        'task_count':14,'tasks':[{'id':p['task_id'],'path':f"tasks/{p['task_id']}.json",'status':'EXPANSION_CANDIDATE','realization_status':p['realization_status']} for p in provenance],
        'context_id':ctx['context_id'],'task_specific_context_masking':False,
        'success_dispatch':'benchmark_adapter.evaluate_success; required, no native empty-criteria fallback',
        'compliance_dispatch':'benchmark_adapter.canonical_judge_policy + existing Compliance Judge framework; not invoked',
        'automatic_runner_registration':False,'merge_into_unified':False,'train_monitor_assignment':False})
    old=load(preservation)['before'];now=preservation_snapshot()
    changed=[p for p,h in old.items() if now.get(p)!=h]
    write('audits/source_preservation.json',{'before':old,'files_checked':len(old),'changed_or_deleted':changed})
    assert not changed,changed
    print(f'Compiled {len(tasks)} candidates; {len(tools)} native tool schemas per request; leakage=0; {len(old)} pre-existing files unchanged.')

if __name__=='__main__':main()
