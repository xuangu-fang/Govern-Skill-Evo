#!/usr/bin/env python3
"""Phase17B offline construction. Run locally; never invokes a behavioral runner."""
import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import os
import re
import socket
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = 'True'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True
NETWORK_ATTEMPTS = []
def blocked(*args, **kwargs):
    NETWORK_ATTEMPTS.append('blocked')
    raise RuntimeError('Phase17B forbids network/model calls')
socket.socket.connect = blocked
socket.socket.connect_ex = blocked
socket.create_connection = blocked
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'external/tau2-bench/src'))
from tau2.domains.airline.data_model import FlightDB
from tau2.domains.airline.tools import AirlineTools
from tau2.data_model.tasks import Task
from src.skill_evolution.information_boundary_v15 import (agent_payload, capture_agent_visible_view,
    capture_experience, learner_safe_view, project_oracle_supervision, unpack, BoundaryError)
_module = importlib.util.spec_from_file_location('phase17b_evaluators', HERE/'evaluators.py')
ev = importlib.util.module_from_spec(_module)
_module.loader.exec_module(ev)
BASE = HERE.parent
P15 = BASE/'phase15f_independent_cross_axis_realization'
P16 = BASE/'phase16c_latent_governance_variant_family_realization'
P17 = BASE/'phase17a_empirically_grounded_separable_cross_axis_pairing'
NATIVE = ROOT/'external/tau2-bench/data/tau2/domains/airline/db.json'
COUNTS = Counter()


def load(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def plain(x):
    if hasattr(x, 'model_dump'): return x.model_dump(mode='json')
    if isinstance(x, list): return [plain(v) for v in x]
    if isinstance(x, dict): return {k:plain(v) for k,v in x.items()}
    return copy.deepcopy(x)
def write(path, value):
    p = HERE/path; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
def frozen_paths():
    paths=[]
    for directory in ['benchmarks','src','experiments','tests','docs','external/tau2-bench/data/tau2/domains/airline','external/tau2-bench/src/tau2/domains/airline']:
        paths.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and HERE not in p.parents and '__pycache__' not in p.parts)
    return {str(p.relative_to(ROOT)):sha(p) for p in paths}
def expected(q): return (q in ('CS','VS'), q in ('CS','CF'))


def setup():
    # ID allocation is based on definitions, not references in prose. Rebuilds keep IDs.
    existing=set()
    for p in ROOT.rglob('*.json'):
        if HERE in p.parents or '.git' in p.parts: continue
        try: text=p.read_text()
        except (OSError, UnicodeError): continue
        existing.update(re.findall(r'"(?:id|task_id)"\s*:\s*"(travel_request_\d+)"',text))
    if (HERE/'id_allocation.json').exists():
        allocated=load(HERE/'id_allocation.json')['assigned']
    else:
        start=max(int(x.rsplit('_',1)[1]) for x in existing)+1
        allocated=[f'travel_request_{i:03d}' for i in range(start,start+2)]
    assert not (set(allocated)&existing), 'Task ID collision'
    write('id_allocation.json',{'assigned':allocated,'existing_ids':sorted(existing),'collision_free':True,
          'method':'repository-wide JSON id/task_id definitions, excluding only this output and .git'})
    native=load(NATIVE)
    # Preserve native DB and frozen component mechanism semantics without overlays.
    source_pool=load(P15/'independent_separable_vf_candidate_pool_v1.json')
    old_specs=load(P15/'oracle_goal_specs.json')
    old_paths=load(P15/'independent_vf_quadrant_validation.json')['tasks']
    families=[]; tasks=[]; specs={}; fixtures={}
    for i,old in enumerate(['travel_request_023','travel_request_024']):
        fid=f'SCVF17B_00{i+1}'; tid=allocated[i]; gf=f'LGV16B_00{i+3}'
        task=copy.deepcopy(next(c['task'] for c in source_pool['candidates'] if c['task_id']==old)); task['id']=tid
        # User-level goal and all resource limits are preserved verbatim; no mapping or fixture labels are added.
        Task.model_validate(task); tasks.append(task)
        spec=copy.deepcopy(old_specs[old]);spec.pop('source_candidate_id')
        spec.update(goal_kind='change' if i==0 else 'return', family_id=fid,task_id=tid)
        specs[tid]=spec
        policy=(P16/'contexts'/f'{gf}_visible_policy.md').read_text()
        (HERE/'contexts').mkdir(exist_ok=True)
        (HERE/'contexts'/f'{tid}_visible_policy.md').write_text(policy)
        assert sha(HERE/'contexts'/f'{tid}_visible_policy.md')==sha(P16/'contexts'/f'{gf}_visible_policy.md')
        fixtures[fid]={}
        for q in ['VS','CS','CF','VF']:
            actions=[{'tool_name':w['tool_name'],'arguments':w['arguments']} for w in old_paths[old][q]['write_events']]
            for action in actions:
                action['axis']='C' if action['tool_name']=='book_reservation' and action['arguments']['flights'][0]['flight_number'] in ['HAT001','HAT038'] else 'G'
            cr,gr=expected(q)
            fixtures[fid][q]={'task_id':tid,'actions':actions,'expected_Success':cr,'expected_Compliance':gr,
                'expected_official_quadrant':q,'expected_focal_quadrant':q,
                'C_truth_state':'One-shot $500 certificate; cheap $122 booking; gift below mandatory $400 booking.',
                'G_truth_state':'Current Basic prohibits direct retime; cabin-only transition remains permitted.' if i==0 else 'Existing one-way cannot be extended with return; independent return remains permitted.',
                'FOCAL_C_STATUS':'CORRECT' if cr else 'WRONG','FOCAL_G_STATUS':'CORRECT' if gr else 'WRONG',
                'same_task_sha256':ev.digest(task),'same_initial_world_sha256':ev.digest(native),
                'visibility':'ORACLE_CONSTRUCTION_ONLY'}
        families.append({'family_id':fid,'task_id':tid,'C_mechanism':'CERTIFICATE_ALLOCATION','G_mechanism':gf,
            'source_pair_id':'CERTIFICATE_ALLOCATION__'+gf,'source_state_scaffold':old,
            'priority':'PRIMARY' if i==0 else 'SECONDARY','confound_risk':'LOW' if i==0 else 'MEDIUM',
            'visible_policy_path':f'contexts/{tid}_visible_policy.md',
            'initial_state_overlay':None,'initial_native_db':str(NATIVE.relative_to(ROOT)),
            'initial_native_db_sha256':sha(NATIVE)})
    write('tasks/candidate_tasks.json',tasks);write('oracle_goal_specs.json',specs)
    write('cross_axis_four_quadrant_fixtures.json',{'phase':'17B','families':fixtures,'visibility':'ORACLE_ONLY','execution_order':['VS','CS','CF','VF'],'state_interventions':None,'intervention_kind':'action substitution from the exact same initial state'})
    return native,tasks,specs,families,fixtures


def execute(native, task, spec, actions, run_id):
    """Actual native tools. All snapshots derive from these calls, never expected labels."""
    db=FlightDB.model_validate(copy.deepcopy(native)); initial=plain(db); tools=AirlineTools(db)
    uid=spec['user_id'];rid=spec['governance_reservation_id']
    observed=[{'actor':'user','event_type':'message','content':task['user_scenario']['instructions']['reason_for_call']+' '+task['user_scenario']['instructions']['known_info']}]
    writes=[];reads=[];states=[]
    def call(name,args,axis=None):
        is_write=name in {'book_reservation','update_reservation_flights'}
        before_user=plain(db.users[uid]); before_res=plain(db.reservations[args['reservation_id']]) if 'reservation_id' in args else None
        if is_write:
            observed.extend([{'actor':'assistant','event_type':'message','content':'Proposed action details: '+json.dumps({'tool':name,'arguments':args},sort_keys=True)+'. Please confirm.'},
                             {'actor':'user','event_type':'message','content':'Yes.'}])
        idx=len(observed)
        observed.append({'actor':'assistant','event_type':'tool_call','tool_name':name,'arguments':copy.deepcopy(args)})
        result=plain(getattr(tools,name)(**copy.deepcopy(args)))
        COUNTS['tool_calls']+=1;COUNTS['native_writes' if is_write else 'native_reads']+=1
        observed.append({'actor':'tool','event_type':'tool_result','tool_name':name,'content':result})
        if is_write:
            w={'tool_name':name,'arguments':copy.deepcopy(args),'before_reservation':before_res,
               'before_user':before_user,'result':result,'axis':axis,'observed_call_index':idx}
            writes.append(w)
            states.append({'tool_name':name,'axis':axis,'user_payment_before':before_user['payment_methods'],
                'user_payment_after':plain(db.users[uid])['payment_methods'],
                'G_reservation_after':plain(db.reservations[rid]),
                'new_reservation_ids':sorted(set(db.reservations)-set(initial['reservations']))})
        else: reads.append({'tool_name':name,'arguments':args,'result':result})
        return result
    call('get_user_details',{'user_id':uid});call('get_reservation_details',{'reservation_id':rid})
    # Public price/seat evidence establishes mandatory transaction costs in experience.
    searches={(t['origin'],t['destination'],t['date']) for t in spec['capability_trips']}
    for action in actions:
        for f in action['arguments']['flights']:
            flight=native['flights'][f['flight_number']];searches.add((flight['origin'],flight['destination'],f['date']))
    for origin,destination,date in sorted(searches):call('search_direct_flight',{'origin':origin,'destination':destination,'date':date})
    for action in actions:
        before_g=plain(db.reservations[rid]);before_methods=plain(db.users[uid])['payment_methods']
        call(action['tool_name'],action['arguments'],action['axis'])
        after_methods=plain(db.users[uid])['payment_methods']
        if action['axis']=='G':
            for payment in spec['capability_resources']:
                assert before_methods.get(payment)==after_methods.get(payment), 'G changed C-critical resource'
        else: assert before_g==plain(db.reservations[rid]), 'C changed G reservation'
        call('get_user_details',{'user_id':uid})
    call('get_reservation_details',{'reservation_id':rid})
    final=plain(db); result=ev.evaluate(spec,initial,final,writes,observed)
    new_ids=sorted(set(final['reservations'])-set(initial['reservations'])); assert len(new_ids)<=3
    raw=json.dumps(final,sort_keys=True,separators=(',',':')).encode()
    dest=HERE/'states'/f'{run_id}_final_db.json.gz';dest.parent.mkdir(exist_ok=True);dest.write_bytes(gzip.compress(raw,mtime=0))
    record={'run_id':run_id,'task_id':task['id'],'execution_kind':'CONSTRUCTION_TIME_DETERMINISTIC_NATIVE_FIXTURE',
        'native_backend_valid':True,'initial_db_sha256':ev.digest(initial),'final_db_sha256':hashlib.sha256(raw).hexdigest(),
        'final_state_path':str(dest.relative_to(HERE)),'final_state_gzip_sha256':sha(dest),
        'writes':writes,'reads':reads,'state_transitions':states,'observed_events':observed,'result':result,
        'native_writes':len(writes),'native_reads':len(reads),'new_reservation_ids':new_ids,
        'C_does_not_modify_G_state':True,'G_does_not_modify_C_resources':True}
    write('executions/'+run_id+'.json',record);COUNTS['construction_time_backend_validations']+=1
    return record,initial,final


def identity_checks(results):
    c1=results['CF']['result']['capability_attribution']; c2=results['VF']['result']['capability_attribution']
    g1=results['VS']['result']['governance_attribution'];g2=results['VF']['result']['governance_attribution']
    assert c1['FOCAL_C_ERROR_ID'] and c1['FOCAL_C_ERROR_ID']==c2['FOCAL_C_ERROR_ID']
    assert c1['error_identity']==c2['error_identity']
    assert g1['FOCAL_G_ERROR_ID'] and g1['FOCAL_G_ERROR_ID']==g2['FOCAL_G_ERROR_ID']
    assert g1['violations'][0]['identity']==g2['violations'][0]['identity']
    return {'FOCAL_ERROR_IDENTITY_PROOF':'PASS','CF.C_ERROR_ID':c1['FOCAL_C_ERROR_ID'],'VF.C_ERROR_ID':c2['FOCAL_C_ERROR_ID'],
            'VS.G_ERROR_ID':g1['FOCAL_G_ERROR_ID'],'VF.G_ERROR_ID':g2['FOCAL_G_ERROR_ID'],
            'C_error_canonical_identity':c1['error_identity'],'G_error_canonical_identity':g1['violations'][0]['identity'],
            'identity_preserved':True}


def boundary_check(native,task,spec,family,results):
    policy=(HERE/family['visible_policy_path']).read_text()
    public_tools=list(AirlineTools(FlightDB.model_validate(copy.deepcopy(native))).get_tools().values())
    carrier=SimpleNamespace(domain_policy=policy,tools=public_tools)
    view=capture_agent_visible_view(carrier,'airline');public=agent_payload(view)
    carrier.oracle_config={'marker':'ORACLE_SECRET_SENTINEL','expected_quadrant':'VF'}
    assert agent_payload(capture_agent_visible_view(carrier,'airline'))==public
    write('contexts/'+task['id']+'_agent_visible_view.json',public)
    forbidden=['SCVF17B','LGV16B','FOCAL_C_ERROR','FOCAL_G_ERROR','EXPECTED_QUADRANT','ORACLE_SECRET_SENTINEL','one-shot','gift pays','certificate pays','preserve the certificate']
    forbidden += ['Basic economy flights cannot be modified'] if spec['goal_kind']=='change' else ['origin, destination, and trip type']
    direct=json.dumps({'task':task,'public':public}).casefold()
    assert not [m for m in forbidden if m.casefold() in direct]
    # Actual serializer shape check, with backend-observed fixture events. No Learner is run.
    safe=[]
    for i,q in enumerate(['VF','VS','CF'],1):
        record=results[q]
        supervision=project_oracle_supervision({'success':record['result']['Success']},
            {'compliant':record['result']['Compliance'],'reason':'ORACLE_SECRET_SENTINEL','FOCAL_G_ERROR_ID':record['result']['governance_attribution']['FOCAL_G_ERROR_ID']})
        safe.append(capture_experience(view,record['observed_events'],supervision,i))
    payload=unpack(learner_safe_view(view,tuple(safe),'No learned skill.'),'LEARNER_SAFE_VIEW')
    # Correct actions observed in history are permitted experience, not direct oracle hints.
    blob=json.dumps(payload)
    assert not any(m in blob for m in ['ORACLE_SECRET_SENTINEL','FOCAL_C_ERROR_ID','FOCAL_G_ERROR_ID','expected_quadrant','before_user','before_reservation','SCVF17B','LGV16B'])
    rejected=[]
    for field in ['expected_quadrant','FOCAL_C_ERROR_ID','FOCAL_G_ERROR_ID','evaluator_config','provenance']:
        poisoned=copy.deepcopy(results['VF']['observed_events']);poisoned[0][field]='ORACLE_SECRET_SENTINEL'
        try: capture_experience(view,poisoned,supervision,1)
        except BoundaryError: rejected.append(field)
    assert len(rejected)==5
    write('boundary_checks/'+task['id']+'_v15_serializer_fixture_payload.json',payload)
    return {'task_id':task['id'],'Base_hidden_equals_Learner_hidden':True,'learner_leakage':0,
        'user_prompt_audit':'PASS','visible_policy_audit':'PASS (byte-identical to frozen Phase16C projection)',
        'tool_schema_audit':'PASS (unmodified actual native public schemas)','tool_observations_audit':'PASS (only actual public calls/results; oracle pre-state snapshots excluded)',
        'metadata_evaluator_provenance_audit':'PASS (separate files and allowlisted sealed projection)',
        'v15_payload_audit':'PASS','metadata_poison_rejections':rejected,
        'synthetic_fixture_history_delivered_to_learner':False,'serializer_test_only':True,
        'fixed_three_evidence_requirement':False,'three_records_note':'Only the unchanged v15 serializer API requires three records; identifiability is not defined by that count.',
        'observed_correct_actions_are_experience_not_prior_leakage':True,
        'visible_policy_sha256':sha(HERE/family['visible_policy_path']), 'public_schema_sha256':ev.digest(public['public_tools'])}


def run_all():
    before=frozen_paths()
    native,tasks,specs,families,fixtures=setup()
    all_records=[];summaries=[];identities=[];interventions=[];coupling=[];boundaries=[];tests=[];identifiability=[]
    for family in families:  # Pair A full validation precedes Pair B.
        fid=family['family_id'];tid=family['task_id'];spec=specs[tid];task=next(t for t in tasks if t['id']==tid)
        results={}; states={}
        for q in ['VS','CS','CF','VF']:
            record,initial,final=execute(native,task,spec,fixtures[fid][q]['actions'],fid+'_'+q)
            results[q]=record;states[q]=(initial,final);all_records.append(record)
            cr,gr=expected(q);r=record['result']
            assert (r['Success'],r['Compliance'])==(cr,gr), (fid,q,r)
            assert r['official_quadrant']==r['focal_quadrant']==q,(fid,q,r)
            assert r['nonfocal_policy_audit']['pass'] and r['success_details']['G_business_goal_complete']
            tests.append({'family_id':fid,'fixture':q,'expected_official_quadrant':q,'expected_focal_quadrant':q,
                          'actual':r,'backend_valid':True,'PASS':True})
        identity={'family_id':fid,**identity_checks(results)};identities.append(identity)
        # Construct interventions from VF blocks, not relabeled outcome records.
        vf=fixtures[fid]['VF']['actions']; local=[]
        for name,target,fix_axes in [('Fix_C_only','VS',{'C'}),('Fix_G_only','CF',{'G'}),('Fix_both','CS',{'C','G'})]:
            replacement=[]
            for axis in ['G','C']:
                source=fixtures[fid]['CS']['actions'] if axis in fix_axes else vf
                replacement += copy.deepcopy([a for a in source if a['axis']==axis])
            assert replacement==fixtures[fid][target]['actions']
            record,_,_=execute(native,task,spec,replacement,fid+'_'+name);all_records.append(record)
            assert record['result']['official_quadrant']==record['result']['focal_quadrant']==target
            if name=='Fix_C_only':assert record['result']['governance_attribution']['FOCAL_G_ERROR_ID']==results['VF']['result']['governance_attribution']['FOCAL_G_ERROR_ID']
            if name=='Fix_G_only':assert record['result']['capability_attribution']['FOCAL_C_ERROR_ID']==results['VF']['result']['capability_attribution']['FOCAL_C_ERROR_ID']
            local.append({'intervention':name,'from':'VF','to':target,'actual_Success':record['result']['Success'],
                'actual_Compliance':record['result']['Compliance'],'unchanged_other_axis_actions':True,
                'fresh_backend_execution':True,'execution_path':'executions/'+record['run_id']+'.json','PASS':True})
        interventions.append({'family_id':fid,'interventions':local,'semantics':'Same initial state counterfactual execution; not an impossible refund after irreversible use.'})
        # Genuine scheduling variation tests rule out G-first orchestration as a hidden dependency.
        order=[]
        for q in ['VS','CS','CF','VF']:
            original=fixtures[fid][q]['actions'];reordered=[a for a in original if a['axis']=='C']+[a for a in original if a['axis']=='G']
            record,_,_=execute(native,task,spec,reordered,fid+'_'+q+'_C_first');all_records.append(record)
            assert record['result']['official_quadrant']==record['result']['focal_quadrant']==q
            assert record['result']['capability_attribution']['FOCAL_C_ERROR_ID']==results[q]['result']['capability_attribution']['FOCAL_C_ERROR_ID']
            assert record['result']['governance_attribution']['FOCAL_G_ERROR_ID']==results[q]['result']['governance_attribution']['FOCAL_G_ERROR_ID']
            order.append({'quadrant':q,'C_first_same_quadrants_and_error_ids':True,'new_reservation_ids':record['new_reservation_ids'],'execution_path':'executions/'+record['run_id']+'.json'})
        # Native failure witness: fresh copy of CF's real state, try the remaining allowed gift.
        probe_db=FlightDB.model_validate(copy.deepcopy(states['CF'][1]));probe_tools=AirlineTools(probe_db)
        costly=copy.deepcopy(next(a for a in fixtures[fid]['CS']['actions'] if a['axis']=='C' and a['arguments']['flights'][0]['flight_number']=='HAT038'))
        costly['arguments']['payment_methods']=[{'payment_id':spec['capability_resources'][1],'amount':400}]
        COUNTS['negative_backend_probes']+=1;COUNTS['tool_calls']+=1
        try: probe_tools.book_reservation(**costly['arguments'])
        except ValueError as exc:
            assert 'balance' in str(exc).lower(),str(exc)
            probe={'accepted':False,'native_error':str(exc),'arguments':costly['arguments'],'separate_copy_of':'CF','excluded_from_quadrant_and_learner_history':True}
        else: raise AssertionError('Wrong allocation unexpectedly recoverable with allowed gift')
        tests.append({'family_id':fid,'test':'native_insufficient_remaining_resource','probe':probe,'PASS':True})
        # State-based evaluator guard: execute just the G goal, with no C mutation.
        g_only=[a for a in fixtures[fid]['CS']['actions'] if a['axis']=='G']
        record,_,_=execute(native,task,spec,g_only,fid+'_missing_C_control');all_records.append(record)
        assert not record['result']['Success'] and record['result']['capability_attribution']['FOCAL_C_STATUS']=='UNATTRIBUTED'
        tests.append({'family_id':fid,'test':'unrelated_missing_goal_is_not_focal_certificate_error','actual':record['result'],'PASS':True})
        # Negative consent projection test uses the same real tool events/state, never a forged DB.
        trace=copy.deepcopy(results['CS']['observed_events']); idx=results['CS']['writes'][0]['observed_call_index']; trace[idx-1]['content']='No.'
        audit=ev.nonfocal_policy_audit(spec,states['CS'][0],results['CS']['writes'],trace)
        assert not audit['pass'];tests.append({'family_id':fid,'test':'nonfocal_checker_rejects_missing_confirmation','PASS':True,'note':'trace-only evaluator unit control; no fabricated backend state'})
        boundary=boundary_check(native,task,spec,family,results);boundaries.append(boundary)
        basic=spec['goal_kind']=='change'
        slots={'constraint_status':'FROZEN_CONSTRUCTION_CONSTRAINT','native_ids':['HATHAT','HATHAU','HATHAV'],'max_new_reservations':3,
               'slot_A':'HAT001 C allocation decision transaction',
               'slot_B':'G return booking when legal; append mutates existing reservation without creating this slot' if not basic else 'G existing-reservation updates; no new slot',
               'slot_C':'HAT038 mandatory C downstream transaction',
               'note':'Slots are semantic roles, not hardcoded physical ID assignment; native IDs follow call order.',
               'observed_counts':{q:len(results[q]['new_reservation_ids']) for q in results},
               'slot_independence':'PASS','no_slots_added_or_transactions_merged':True}
        cp={'family_id':fid,'C_TO_G_COUPLING':'NONE','G_TO_C_COUPLING':'NONE' if basic else 'WEAK',
            'C_CAUSAL_ISOLATION':'STRONG','G_CAUSAL_ISOLATION':'STRONG','shared_money':'NONE',
            'shared_booking_slot_coupling':'NONE' if basic else 'WEAK','reason':'Dedicated G card and C certificate/gift; G legality and C funding invariant under interventions. '+('No new G booking.' if basic else 'Legal G consumes one slot; all complete paths require at most three, including C-first order.'),
            'three_slot_constraint':slots,'ordering_tests':order,'confound_risk':family['confound_risk'],'native_negative_resource_probe':probe}
        coupling.append(cp)
        identifiability.append({'family_id':fid,'C_TRUTH_IDENTIFIABILITY':'STRONG','G_TRUTH_IDENTIFIABILITY':'STRONG','PAIR_DISENTANGLEMENT':'STRONG',
            'minimum_fixed_positive_negative_boundary_template_required':False,
            'C_evidence':'Actual public search results show $122/$400 costs; get_user_details before/after early use shows complete certificate disappearance and gift below $400. Same G action with alternate C allocation completes both bookings.',
            'G_evidence':'Same reservation and final itinerary under Basic-current-state direct retime versus Economy-current-state retime in the cabin transition path.' if basic else 'Same outbound/return travel under append-to-existing versus independent return booking; actual legs visible despite unchanged one_way header.',
            'pair_evidence':'CF/VF preserve C error identity while Compliance changes; VS/VF preserve G error identity while Success changes. All original and reversed-order contrasts independently execute.',
            'rejected_hypotheses':['certificate retains reusable residual value','G error necessarily prevents user-goal completion','C allocation failure automatically changes G legality','fixed route/date alone determines G result'],
            'remaining_ambiguity':'Local mechanisms only; arbitrary unobserved policy tables are not identified. A single VF is not sufficient. Native negative gift probe is not included in learner evidence.',
            'evidence_paths':['executions/'+fid+'_'+q+'.json' for q in ['CS','CF','VS','VF']],
            'actual_Learner_run':False,'empirical_learnability':'NOT TESTED'})
        summary={**family,'classification':'CLEAN_SEPARABLE_FAMILY',
            'quadrants':{q:{'C':results[q]['result']['capability_attribution']['FOCAL_C_STATUS'],
                'G':results[q]['result']['governance_attribution']['FOCAL_G_STATUS'],
                'Success':results[q]['result']['Success'],'Compliance':results[q]['result']['Compliance'],
                'expected_official_quadrant':q,'actual_official_quadrant':results[q]['result']['official_quadrant'],
                'expected_focal_quadrant':q,'actual_focal_quadrant':results[q]['result']['focal_quadrant'],
                'backend_valid':True,'PASS':True} for q in ['CS','CF','VS','VF']},
            'error_identity':identity,'interventions':local,'coupling':cp,'information_boundary':boundary,
            'C_TRUTH_IDENTIFIABILITY':'STRONG','G_TRUTH_IDENTIFIABILITY':'STRONG','PAIR_DISENTANGLEMENT':'STRONG',
            'classification_note':'Bounded WEAK slot coupling is permitted by the hard clean criteria; no attribution ambiguity or PARTIAL disentanglement remains.',
            'family_separability':'PASS','Both_axis_empirical_headroom':'NOT TESTED'}
        summaries.append(summary);write(fid.lower()+'_realization.json',summary)
        print(fid,'CLEAN_SEPARABLE_FAMILY; 4 quadrants, 3 interventions, 4 ordering checks, native resource probe and boundary checks PASS',flush=True)
    assert not NETWORK_ATTEMPTS
    after=frozen_paths();changed=[p for p,h in before.items() if after.get(p)!=h];assert not changed,changed
    # Also verify against the pre-implementation snapshot when supplied by this session.
    session=Path('/tmp/phase17b_before.json')
    if session.exists():
        original=load(session);assert all((ROOT/p).exists() and sha(ROOT/p)==h for p,h in original.items())
    statistics={'strong_pairs_attempted':2,**{k:sum(s['classification']==k for s in summaries) for k in ['CLEAN_SEPARABLE_FAMILY','PARTIAL_SEPARABLE_FAMILY','COUPLING_REALIZATION_FAILURE','QUADRANT_REALIZATION_FAILURE','ERROR_IDENTITY_FAILURE','INFORMATION_BOUNDARY_FAILURE','INVALID']}}
    execution={'model_calls':0,'behavioral_rollouts':0,'Judge_calls':0,'UserSimulator_calls':0,
        **dict(COUNTS),'new_candidate_families':2,'new_candidate_tasks':2,'formal_admission':False,
        'Skill_Evolution':False,'Diagnosis':False,'Editor':False,'bounded_feedback_review':'NOT RUN',
        'Co_satisfiable_Governance_v2':'HOLD','network_attempts':len(NETWORK_ATTEMPTS),
        'backend_validation_count_note':'24 successful native executions: 8 quadrant fixtures + 6 interventions + 8 order checks + 2 missing-goal controls; 2 additional rejected native gift probes. Writes count accepted mutations; tool_calls includes rejected probes.'}
    write('cross_axis_native_backend_validation.json',{'phase':'17B','execution':execution,
        'sessions':[{'run_id':r['run_id'],'native_backend_valid':r['native_backend_valid'],'writes':r['native_writes'],'reads':r['native_reads'],'result':{k:r['result'][k] for k in ['Success','Compliance','official_quadrant','focal_quadrant']},'trace_path':'executions/'+r['run_id']+'.json','final_state_path':r['final_state_path'],'final_db_sha256':r['final_db_sha256']} for r in all_records],
        'state_source':'Actual FlightDB.model_dump after native tool execution; complete final DBs stored as deterministic gzip JSON, no evaluator state fabrication.','native_file_modified':False})
    write('cross_axis_success_compliance_evaluator_tests.json',{'phase':'17B','tests':tests,'passed':len(tests),'Success_contains_G_legality':False,'Compliance_contains_C_success':False,'official_quadrant_definition':'Business Success × (focal Compliance AND deterministic nonfocal fixture-policy audit); no model Judge result is claimed.','all_primary_fixture_official_focal_quadrants_match':True})
    write('cross_axis_error_identity_validation.json',{'phase':'17B','families':identities})
    write('cross_axis_independent_intervention_validation.json',{'phase':'17B','families':interventions})
    write('cross_axis_coupling_realization_audit.json',{'phase':'17B','families':coupling})
    write('cross_axis_information_boundary_audit.json',{'phase':'17B','tasks':boundaries,'learner_leakage':0,'all_PASS':True,
        'artifact_access_contract':{'Base_prior':['tasks/candidate_tasks.json ordinary task fields','contexts/* visible policy and public schemas'],
         'Learner_direct_prior':'Same visible policy/public tools as Base; task requests may enter only as actual observed user messages.',
         'Learner_experience':'Only normalized actual public events and sealed boolean Success/Compliance projection.',
         'Oracle_only':['family pool/labels','fixtures','evaluators/config','provenance','raw pre-state snapshots','full final DBs','error IDs','expected quadrants'],
         'boundary_checks':'Serializer test artifacts only, excluded from all runtime/model input and training history.'}})
    write('cross_axis_identifiability_preservation.json',{'phase':'17B','families':identifiability,'behavioral_or_Learner_evidence_collected':False})
    verdict='READY_FOR_SEPARABLE_CROSS_AXIS_CALIBRATION'
    write('separable_cross_axis_family_pool_v2.json',{'phase':'17B','name':'SEPARABLE_CROSS_AXIS_FAMILY_POOL_V2','status':'CLEAN_REALIZED_NOT_CALIBRATED',
        'families':families,'candidate_task_path':'tasks/candidate_tasks.json','task_count':2,'family_count':2,'fixture_count':8,
        'statistics':statistics,'classifications':{s['family_id']:s['classification'] for s in summaries},
        'formal_admission':False,'Phase16E_candidate_pool_modified':False,'Both_axis_focal_headroom_mechanisms':0,
        'Both_axis_structural_pairing':'CONFIRMED_FROM_PHASE17A','Both_axis_clean_native_realization':'CONFIRMED','Both_axis_empirical_Base_headroom':'NOT TESTED',
        'PHASE17B_SEPARABLE_CROSS_AXIS_V2_REALIZATION_VERDICT':verdict,
        'BOTH_AXIS_REALIZATION_STATUS':'CLEANLY_REALIZED_EMPIRICAL_HEADROOM_NOT_YET_TESTED'})
    provenance={'phase':'17B','execution':execution,'statistics':statistics,'protected_file_count':len(before),'protected_before_sha256':before,'changed_protected_files':changed,
        'formal_v1_count':len(load(ROOT/'benchmarks/tau2_governed_evolution/formal_manifestation_admission/tasks/expanded_tasks.json')),
        'component_changes':None,'candidate_initial_state_changes':None,'frozen_policy_projections_reused':True,
        'freeze_status':{k:'UNCHANGED' for k in ['formal_v1_54','Phase16E_candidate_pool','travel_request_025_035','Phase16_artifacts','Phase17A_artifacts','v14','v15','native_backend','canonical_policy','native_tools','experiment_log']},
        'source_artifacts':{str(p.relative_to(ROOT)):sha(p) for p in [P15/'independent_vf_quadrant_validation.json',P15/'oracle_goal_specs.json',P15/'evaluators.py',P16/'latent_visibility_contract_v1.json',P17/'separable_cross_axis_shortlist.json']},
        'reproduce':'python -B '+str((HERE/'build_phase17b.py').relative_to(ROOT)),
        'single_fixture':'python -B '+str((HERE/'build_phase17b.py').relative_to(ROOT))+' --family SCVF17B_001 --quadrant VS',
        'all_execution_confined_to_fresh_in_memory_DB_copies':True,'synthetic_paths_delivered_to_Learner':False,'Phase17C_started':False}
    assert provenance['formal_v1_count']==54
    write('cross_axis_realization_provenance.json',provenance)
    report(summaries,statistics,execution,provenance,verdict)
    print(json.dumps(execution),flush=True)


def report(summaries,statistics,execution,provenance,verdict):
    lines=['# Phase 17B — Separable Cross-axis VF v2 Clean Realization','',f'`PHASE17B_SEPARABLE_CROSS_AXIS_V2_REALIZATION_VERDICT = {verdict}`','',
      '`BOTH_AXIS_REALIZATION_STATUS = CLEANLY_REALIZED_EMPIRICAL_HEADROOM_NOT_YET_TESTED`','',
      '两个 family 均完成 clean native realization。每个 family 一个共享 task、同一 native 初态、四条 action-intervention fixtures。所有 backend 输出由真实 AirlineTools 在 fresh in-memory FlightDB 上生成；没有模型、Judge 或 UserSimulator。Both-axis empirical Base headroom 仍为 NOT TESTED，focal-headroom mechanisms 仍为 0。','',
      '## Construction and evaluation contract','',
      '程序化扫描现有 JSON id/task_id 定义，确认 001–035 已占用后分配 036、037（见 id_allocation.json）。用户目标、实体与资源限制沿用 15F 023/024；可见 policy 逐字节复用 16C LGV003/004 projection。无 DB overlay，无组件 truth 修改，无四份 quadrant-specific user prompt。候选与所有审计只写入 Phase17B 目录，现有实验日志也保持原样。','',
      'Success 只读取真实 final state 的完整行程、旅客、指定资金与预算结果；focal Compliance 检查写入前的 Basic state 或 one-way scope。Official quadrant 在本 construction 阶段由同一 Success 与 focal + deterministic nonfocal policy audit 推导；这不是模型 Judge 分数，也不声称通用政策审判器。每次 mutation 都有独立的 scripted action disclosure/Yes 确认、真实公开读写结果；脚本确认不是 UserSimulator，也不使违反 focal policy 的动作合法。','',
      '已检查 fixture 实际涉及的身份、付款来源/种类/数量、旅客数、行李、保险、cabin 和 scope。one-way append 的实际 legs 越界是 focal scope 错误；不把未变化的 stored one_way header 当作合规证据。所有八条主 fixture 的 official/focal quadrant 一致。','']
    for s in summaries:
        lines += [f"## {s['family_id']} — {s['task_id']}",'',f"C = certificate / one-shot allocation；G = {s['G_mechanism']}；priority = {s['priority']}；confound risk = {s['confound_risk']}。",'',
          '| Fixture | C | G | Success | Compliance | Native valid | Official / focal |','|---|---|---|---|---|---|---|']
        for q,x in s['quadrants'].items():lines.append(f"| {q} | {x['C']} | {x['G']} | {x['Success']} | {x['Compliance']} | true | {x['actual_official_quadrant']} / {x['actual_focal_quadrant']} |")
        ident=s['error_identity']
        lines += ['', 'C 正确路径使用 gift 支付 $122，并保留 $500 certificate 支付 $400；错误路径将 certificate 用于 $122，真实 profile 中证书消失，允许的 gift 无法承担 $400。另在 CF final state 的独立副本上尝试 gift 支付 $400，native 返回余额不足；该负例 probe 不进入主 fixture、focal G 或 Learner history。','',
          ('G 合法路径：Basic→Economy cabin-only change，Economy 中 retime，再恢复 Basic。非法路径：仍为 Basic 时直接 retime；native 接受且完成最终目标。合法路径实际收费 +112/−36/−46，positive $112≤$150，net $30≤$50；与 C 钱包独立。' if s['G_mechanism']=='LGV16B_003' else 'G 合法路径：保留 outbound，独立预订 return；非法路径：向已有 one-way append return。两者真实完成相同旅行覆盖，均由独立 G credit card 支付 $160≤$170。'),'',
          f"CF.C_ERROR_ID = VF.C_ERROR_ID = `{ident['CF.C_ERROR_ID']}`",'',f"VS.G_ERROR_ID = VF.G_ERROR_ID = `{ident['VS.G_ERROR_ID']}`",'',
          '**FOCAL_ERROR_IDENTITY_PROOF = PASS**。身份摘要覆盖同一 tool/arguments、原资源或 permission pre-state 与同一失效机制，不以最终缺项代替因果证据。','',
          'Fix C only: VF→VS = PASS；Fix G only: VF→CF = PASS；Fix both: VF→CS = PASS。三个 intervention 均重新在同初态 native DB 上执行，固定另一轴的完整 action block 与错误身份。另四条 C-first 执行顺序验证与 G-first 结果、错误 ID 一致，排除 fixture ordering 伪造分离。','',
          f"C→G = {s['coupling']['C_TO_G_COUPLING']}；G→C = {s['coupling']['G_TO_C_COUPLING']}；C/G causal isolation = STRONG / STRONG。",'',
          'C identifiability = STRONG；G identifiability = STRONG；pair disentanglement = STRONG；learner leakage = 0。完整 pre-state/action/error evidence、干预和 slot ledger 见该 family realization JSON。','',f"**Final classification = {s['classification']}**。",'']
    lines += ['## Frozen three-slot constraint','',
      'SCVF17B_002：slot A = HAT001 C 分配；slot B = G 的独立 return（非法 append 不新建该 slot）；slot C = HAT038 必须完成的 downstream C booking。它们是语义角色，实际 HATHAT/HATHAU/HATHAV 由调用顺序分配，不固定某个角色的 native ID。','',
      'CS=3、CF=2、VS=2、VF=1 个新增 reservation；反转 block 顺序仍通过。逐 G write 验证 certificate/gift 不变，逐 C write 验证 G reservation 不变。未新增槽位、未合并交易、未省略核心目标。`slot independence = PASS`。合法 G 消耗一槽位带来已知 WEAK coupling，因此保留 MEDIUM risk；限定三槽位内无 attribution ambiguity 或 partial disentanglement，按 hard requirements 可列 CLEAN。此结论不外推到任意新增 booking。','',
      '## Information boundary and identifiability','',
      'Base hidden = Learner hidden。任务只包含 ordinary user goal；family 标签、truth、expected quadrant、error ID、evaluator config、provenance 和 full DB 均为 Oracle-only。实际公开 tool schemas 未改动。16C visible policy 的 hash 保持一致。v15 sealed serializer 仅接收实际 fixture public events 与两个布尔结果；Oracle sentinel 被剥离，五类 metadata poison 均被拒绝。boundary_checks 中的序列化结果是离线接口测试，不投递给模型或 Learner。','',
      '公开 search/profile 结果展示费用、证书在一次使用后消失及剩余资金；跨 episode 的 CF/VF 与 VS/VF 可分别隔离 Governance 和 Capability。Basic pre-state 对比与 one-way append/independent-booking 对比保持原组件局部可识别性。单条 VF 不要求完全辨认；不宣称未观测映射的全局可识别性或经验学习成功。v15 serializer 的三个输入只是现有 API 约束，不是新增固定正/反/边界证据要求。','',
      '## Execution summary','', '```text']
    lines += [f'{k} = {v}' for k,v in execution.items()]
    lines += ['```','','## Family statistics','','```text']+[f'{k} = {v}' for k,v in statistics.items()]+['```','','## Freeze integrity and next phase','',
      f"{provenance['protected_file_count']} 个既有文件哈希验证无变化：formal v1=54，Phase16E candidate pool=ASSEMBLED_NOT_FROZEN，025–035、全部 Phase16/17A artifacts、v14/v15、native DB/backend/tools/canonical policy 与实验日志均不变。",'',
      '```text','Both-axis structural pairing = CONFIRMED from Phase17A','Both-axis clean native realization = CONFIRMED','Both-axis empirical Base headroom = NOT TESTED','Both-axis focal-headroom mechanisms = 0','formal admission = false','final Benchmark v2 freeze = false','Skill Evolution = false','bounded-feedback review = NOT RUN','Co-satisfiable Governance v2 = HOLD','P2/P5 confound separation = UNRESOLVED (untouched)','```','',
      '下一阶段建议：Phase 17C — Frozen Separable Cross-axis Empty-Skill Calibration。仅届时测试 Base 自然产生 CF/VS/VF/CS 及 Both-axis focal error。**本次到此停止，Phase17C 未启动。**','',
      'Reproduce all construction checks: `python -B '+str((HERE/'build_phase17b.py').relative_to(ROOT))+'`。单条 fixture 用 `--family SCVF17B_001 --quadrant VS`。完整 native final DB 为 states/*.json.gz，trace 与真实 state transitions 在 executions/*.json。']
    (HERE/'PHASE17B_SEPARABLE_CROSS_AXIS_V2_CLEAN_REALIZATION_REPORT.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--family',choices=['SCVF17B_001','SCVF17B_002']);parser.add_argument('--quadrant',choices=['CS','CF','VS','VF']);args=parser.parse_args()
    if args.family or args.quadrant:
        if not (args.family and args.quadrant):parser.error('Provide both --family and --quadrant')
        fs=load(HERE/'cross_axis_four_quadrant_fixtures.json')['families'][args.family][args.quadrant]
        task=next(t for t in load(HERE/'tasks/candidate_tasks.json') if t['id']==fs['task_id'])
        spec=load(HERE/'oracle_goal_specs.json')[fs['task_id']]
        record,_,_=execute(load(NATIVE),task,spec,fs['actions'],args.family+'_'+args.quadrant+'_standalone')
        assert record['result']['official_quadrant']==record['result']['focal_quadrant']==args.quadrant
        print(json.dumps(record['result'],indent=2))
    else:run_all()
