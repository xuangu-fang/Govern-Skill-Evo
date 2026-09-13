"""No-model boundary tests and synthetic complete v15 proposal dry run."""
import ast
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from src.skill_evolution import information_boundary_v15 as b
from src.skill_evolution.diagnosis_v15 import build_diagnosis_prompts, call_diagnosis
from src.skill_evolution.diagnosis_schema_v15 import SEMANTIC_DIAGNOSIS_TEMPLATE
from src.skill_evolution.autonomous_gse_v15_benchmark_runtime import (
    prepare_diagnosis, prepare_diagnosis_from_stored, normalize_stored_simulation,
    bind_visible_context, propose_from_experience,
)
from src.skill_evolution.autonomous_gse_v15_proposal import (
    build_editor_request, DiagnosisEditorRequest,
)
from src.learners.stwebagentbench.generate_governed_skill_v15 import build_editor_prompts, call_governed_editor
from src.skill_evolution.skill_text_v15 import SECTIONS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'benchmarks/tau2_governed_evolution/information_boundary/phase12t_v15_experience_grounded_learner'
HIDDEN = 'SECRET cancellation must precede compensation 829104'
PRIVATE = 'PRIVATE expected payment history cardinality 839283'
ANSWER = 'GOLDEN refund amount 172938 and reference action'
SKILL = '# Operational Skill\n\n' + '\n\n'.join('## '+s for s in SECTIONS) + '\n'


class Tool:
    def __init__(self, name='mutate'):
        self.name = name
        self.short_desc = 'Public action.'
        self.long_desc = ''
    @property
    def openai_schema(self):
        return {'type':'function','function':{'name':self.name,'description':self.short_desc + self.long_desc,'parameters':{'type':'object','properties':{'item':{'type':'string'}},'additionalProperties':False}}}


def fixture():
    agent = SimpleNamespace(domain_policy='Consequential actions need confirmation. Identity and workflow constraints apply.', tools=[Tool()])
    view = b.capture_agent_visible_view(agent, 'retail')
    events = [
        {'actor':'user','event_type':'message','content':'Please change my item.'},
        {'actor':'assistant','event_type':'tool_call','tool_name':'mutate','arguments':{'item':'observed item'}},
        {'actor':'tool','event_type':'tool_result','tool_name':'mutate','content':{'status':'changed','observed_balance':3}},
    ]
    oracle = b.OracleView(HIDDEN, {'source':PRIVATE}, {'expected_action':ANSWER,'expected_final_state':ANSWER,'reference_response':ANSWER}, {'policy_id':'canonical_LGA01'})
    successes = [{'success':value,'expected_action':ANSWER,'expected_final_state':ANSWER,'reference_response':ANSWER} for value in (False,True,False)]
    judges = [{'compliant':value,'policy_clause':HIDDEN,'reason':HIDDEN,'repair_policy_ids':['canonical_LGA01']} for value in (False,True,False)]
    request = prepare_diagnosis(view, SKILL, [events]*3, successes, judges)
    return agent, view, request, oracle, events


def diagnosis_transport(system, user, schema):
    payload = json.loads(user)
    assert 'visible_policy' in payload and 'original_domain_policy' not in payload
    s = copy.deepcopy(SEMANTIC_DIAGNOSIS_TEMPLATE)
    s['behavioral_mechanism'].update(description='A proposed missing confirmation check.',evidence_status='contrastive_support',support_evidence_refs=['E002','E005'],counterevidence_refs=['E008'],counterevidence='Third rollout might contradict the hypothesis.')
    s['feasibility'] = {'status':'feasible','explanation':'An observed alternative is available.'}
    s['skill_coverage'] = {'status':'missing','related_rule_ids':[],'explanation':'No Parent rules.'}
    s['outcome_relation'] = {'task_success':'supports','compliance':'supports'}
    s['supervision_refs'] = ['S001']
    s['target_behavior'] = {k:'A learner hypothesis based on observed confirmation.' for k in s['target_behavior']}
    return json.dumps(s)


def editor_transport(system, user, schema):
    p=json.loads(user)
    return json.dumps({'canonical_edits':[{
        'derived_from_patch_ids':[p['eligible_hypotheses'][0]['patch_id']],
        'operation':'add','section':SECTIONS[0],'target_rule_id':'',
        'text':'For retail requests, obtain confirmation before the consequential action.',
        'reason':'Preserves the learner hypothesis.',
        'verification_hypothesis':{'problem':'Missing check','trigger_condition':'Consequential action','expected_behavior':'Obtain confirmation'},
    }]})


class V15BoundaryTests(unittest.TestCase):
    def test_A_v14_frozen(self):
        diff=json.loads((OUT/'v14_v15_behavioral_boundary_diff.json').read_text())
        self.assertTrue(diff['frozen_v14_sha256'])
        for path, expected in diff['frozen_v14_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),expected,path)

    def test_B_hidden_policy_isolation(self):
        _,view,request,oracle,_=fixture()
        self.assertIn(HIDDEN,oracle.canonical_policy)
        self.assertNotIn(HIDDEN,json.dumps(b.agent_payload(view)))
        self.assertNotIn(HIDDEN,build_diagnosis_prompts(request)[1])
        self.assertEqual(b.agent_payload(view)['visible_policy'],json.loads(build_diagnosis_prompts(request)[1])['visible_policy'])

    def test_C_evaluator_truth_isolation(self):
        _,_,request,oracle,_=fixture()
        self.assertIn(ANSWER,json.dumps(oracle.evaluator_truth))
        hypothesis=call_diagnosis(request,learner_call=diagnosis_transport)
        editor,_=build_editor_request((hypothesis,))
        for payload in [build_diagnosis_prompts(request)[1],build_editor_prompts(editor)[1]]:
            self.assertNotIn(ANSWER,payload)
            self.assertNotIn('reference_response',payload)
            self.assertNotIn('expected_final_state',payload)

    def test_D_backend_truth_isolation(self):
        _,view,request,oracle,_=fixture()
        self.assertIn(PRIVATE,json.dumps(oracle.private_backend))
        self.assertNotIn(PRIVATE,json.dumps(b.agent_payload(view)))
        payload=json.loads(build_diagnosis_prompts(request)[1])
        self.assertEqual(payload['public_tools'],b.agent_payload(view)['public_tools'])
        self.assertNotIn('raises',json.dumps(payload))
        self.assertNotIn(PRIVATE,json.dumps(payload))

    def test_E_judge_level3_blocked(self):
        signal=b.project_oracle_supervision({'success':False},{'compliant':False,'reason':HIDDEN,'policy_clause':HIDDEN,'evidence_steps':[2]})
        safe=b.unpack(signal,'LEARNER_SAFE_SUPERVISION')
        self.assertEqual(safe['level'],0)
        self.assertLessEqual(safe['level'],2)
        self.assertNotIn(HIDDEN,json.dumps(safe))
        self.assertEqual(set(safe),{'success','compliant','level','provenance'})

    def test_F_editor_rejects_oracle_provenance(self):
        _,_,request,_,_=fixture()
        h=call_diagnosis(request,learner_call=diagnosis_transport)
        data=b.unpack(h,'LEARNER_INFERRED');data['semantic_origin']='ORACLE_DERIVED'
        with self.assertRaises(b.BoundaryError):build_editor_request((b._seal('LEARNER_INFERRED',data),))
        with self.assertRaises(b.BoundaryError):build_editor_request(({'semantic_origin':'LEARNER_INFERRED','target_behavior':HIDDEN},))
        editor,_=build_editor_request((h,));wrong=replace(editor.hypotheses,payload=editor.hypotheses.payload.replace('LEARNER_INFERRED','ORACLE_DERIVED'))
        with self.assertRaises(b.BoundaryError):build_editor_prompts(DiagnosisEditorRequest(wrong))

    def test_G_experience_retained(self):
        _,_,request,_,_=fixture();p=json.loads(build_diagnosis_prompts(request)[1])
        self.assertEqual(len(p['rollouts']),3)
        self.assertEqual([r['supervision']['success'] for r in p['rollouts']],[False,True,False])
        self.assertEqual([r['supervision']['compliant'] for r in p['rollouts']],[False,True,False])
        self.assertIn('observed_balance',json.dumps(p))
        self.assertEqual(p['current_skill'],SKILL)
        h=call_diagnosis(request,learner_call=diagnosis_transport)
        self.assertTrue(b.unpack(h,'LEARNER_INFERRED')['provenance']['counterevidence_refs'])

    def test_H_no_oracle_pointer(self):
        _,_,request,_,_=fixture();h=call_diagnosis(request,learner_call=diagnosis_transport);editor,_=build_editor_request((h,))
        for p in [build_diagnosis_prompts(request)[1],build_editor_prompts(editor)[1]]:
            self.assertNotIn('canonical_LGA01',p)
            self.assertNotIn('repair_policy_ids',p)
            self.assertNotIn('policy_aliases',p)
        p=json.loads(build_diagnosis_prompts(request)[1])
        self.assertEqual(set(p['available_supervision_refs']),{'S001','S002','S003'})
        self.assertEqual(set(p['available_supervision_refs']['S001']),{'source_id','level'})

    def test_complete_no_model_dry_run(self):
        _,_,request,_,_=fixture()
        result=propose_from_experience((request,),diagnosis_transport=diagnosis_transport,editor_transport=editor_transport)
        self.assertEqual(result['status'],'CANDIDATE_CREATED')
        self.assertEqual(result['information_boundary_version'],'v15_learner_safe')
        self.assertIn('For retail requests,',b.unpack(result['candidate'],'LEARNER_INFERRED_SKILL')['candidate_skill'])

    def test_context_snapshot_and_override(self):
        agent=SimpleNamespace(domain_policy=HIDDEN,tools=[Tool('cancel_pending_order')])
        view=bind_visible_context(agent,'retail')
        manifest=json.loads((ROOT/'benchmarks/tau2_governed_evolution/formal_manifestation_admission/contexts/context_manifest.json').read_text())
        spec=manifest['contexts']['retail'];expected=(ROOT/spec['policy_path']).read_text()
        self.assertEqual(b.agent_payload(view)['visible_policy'],expected)
        self.assertEqual(agent.domain_policy,expected)
        self.assertNotIn('refund will be added',b.agent_payload(view)['public_tools'][0]['function']['description'].lower())

    def test_stored_simulation_adapter_retains_observations_only(self):
        simulation = {
            'policy': HIDDEN, 'reward_info': {'expected_action': ANSWER},
            'messages': [
                {'role':'user','content':'Observed request.','raw_data':{'reasoning':HIDDEN}},
                {'role':'assistant','content':'','tool_calls':[{'id':'c1','name':'mutate','arguments':{'item':'observed item'}}],'raw_data':{'reasoning':HIDDEN}},
                {'role':'tool','id':'c1','content':{'status':'changed'},'error':False},
            ],
        }
        events = normalize_stored_simulation(simulation)
        self.assertEqual([event['event_type'] for event in events], ['message','tool_call','tool_result'])
        self.assertIn('changed',json.dumps(events))
        self.assertNotIn(HIDDEN,json.dumps(events))
        self.assertNotIn(ANSWER,json.dumps(events))
        self.assertNotIn('raw_data',json.dumps(events))

    def test_stored_simulation_adapter_routes_through_diagnosis(self):
        _,view,_,_,_=fixture()
        simulation = {'messages':[
            {'role':'user','content':'Observed request.'},
            {'role':'assistant','content':'','tool_calls':[{'id':'c1','name':'mutate','arguments':{'item':'observed item'}}]},
            {'role':'tool','id':'c1','content':{'status':'changed'}},
        ]}
        request = prepare_diagnosis_from_stored(
            view, SKILL, [simulation]*3,
            [{'success':False,'expected_action':ANSWER}]*3,
            [{'compliant':False,'raw_oracle_reasoning':HIDDEN}]*3,
        )
        payload = json.loads(build_diagnosis_prompts(request)[1])
        self.assertEqual(len(payload['rollouts']),3)
        self.assertNotIn(ANSWER,json.dumps(payload))
        self.assertNotIn(HIDDEN,json.dumps(payload))

    def test_stored_simulation_adapter_rejects_unmatched_tool_result(self):
        with self.assertRaises(b.BoundaryError):
            normalize_stored_simulation({'messages':[{'role':'tool','id':'unknown','content':'result'}]})

    def test_no_canonical_or_v14_runtime_imports(self):
        files=list((ROOT/'src/skill_evolution').glob('*v15*.py'))+[ROOT/'src/learners/stwebagentbench/generate_governed_skill_v15.py']
        for f in files:
            tree=ast.parse(f.read_text())
            for n in ast.walk(tree):
                if isinstance(n,ast.ImportFrom):self.assertNotIn('v14',n.module or '',str(f))
            self.assertNotIn('load_authoritative_domain_contexts',f.read_text())

    def test_missing_projection_and_labels_fail_closed(self):
        with self.assertRaises(b.BoundaryError):b.project_oracle_supervision({'success':None},{'compliant':True})
        with self.assertRaises(b.BoundaryError):b.project_oracle_supervision({'success':1},{'compliant':True})
        with self.assertRaises(b.BoundaryError):b.capture_agent_visible_view(SimpleNamespace(),'retail')
        _,_,request,_,_=fixture()
        with self.assertRaises(b.BoundaryError):build_diagnosis_prompts(replace(request,learner_view=None))

    def test_oracle_fields_in_events_rejected(self):
        _,view,_,_,events=fixture();events=copy.deepcopy(events);events[0]['task_instructions']=HIDDEN
        supervision=b.project_oracle_supervision({'success':True},{'compliant':True})
        with self.assertRaises(b.BoundaryError):b.capture_experience(view,events,supervision,1)

    def test_context_mismatch_and_duplicate_rollouts_rejected(self):
        agent,view,_,_,events=fixture();s=b.project_oracle_supervision({'success':True},{'compliant':True})
        experiences=tuple(b.capture_experience(view,events,s,i) for i in (1,2,3))
        agent.domain_policy='Different visible context';other=b.capture_agent_visible_view(agent,'retail')
        with self.assertRaises(b.BoundaryError):b.learner_safe_view(other,experiences,SKILL)
        with self.assertRaises(b.BoundaryError):b.learner_safe_view(view,(experiences[0],)*3,SKILL)

    def test_unsupported_diagnosis_metadata_rejected(self):
        _,_,request,_,_=fixture()
        def bad(system,user,schema):
            v=json.loads(diagnosis_transport(system,user,schema));v['oracle_expected_behavior']=HIDDEN;return json.dumps(v)
        with self.assertRaises(b.BoundaryError):call_diagnosis(request,learner_call=bad)

    def test_compiler_is_algorithmic_v14_snapshot(self):
        old=(ROOT/'src/skill_evolution/diagnosis_compiler_v14.py').read_text().replace('v0.14','v0.15')
        new=(ROOT/'src/skill_evolution/diagnosis_compiler_v15.py').read_text()
        self.assertEqual(old,new)

    def test_field_level_oracle_origin_rejected(self):
        _,_,request,_,_=fixture()
        h=call_diagnosis(request,learner_call=diagnosis_transport)
        data=b.unpack(h,'LEARNER_INFERRED')
        data['field_provenance']['target_behavior.expected_behavior']='ORACLE_DERIVED'
        with self.assertRaises(b.BoundaryError):build_editor_request((b._seal('LEARNER_INFERRED',data),))
        del data['field_provenance']
        with self.assertRaises(b.BoundaryError):build_editor_request((b._seal('LEARNER_INFERRED',data),))

    def test_no_update_does_not_call_editor(self):
        _,_,request,_,_=fixture()
        def insufficient(system,user,schema):return json.dumps(SEMANTIC_DIAGNOSIS_TEMPLATE)
        def forbidden(*args):self.fail('Editor called without eligible update')
        result=propose_from_experience((request,),diagnosis_transport=insufficient,editor_transport=forbidden)
        self.assertIsNone(result['candidate'])

    def test_editor_cannot_override_compiled_operation(self):
        _,_,request,_,_=fixture();h=call_diagnosis(request,learner_call=diagnosis_transport);e,_=build_editor_request((h,))
        def bad(system,user,schema):
            result=json.loads(editor_transport(system,user,schema))
            result['canonical_edits'][0]['operation']='delete'
            return json.dumps(result)
        with self.assertRaises(b.BoundaryError):call_governed_editor(e,learner_call=bad)

    def test_new_experiment_default_is_v15(self):
        from src.skill_evolution import experience_grounded_runtime as default
        self.assertEqual(default.INFORMATION_BOUNDARY_VERSION,'v15_learner_safe')
        self.assertEqual(default.LEARNER_SETTING,'EXPERIENCE_GROUNDED_LEARNER')
        self.assertIs(default.propose_from_experience,propose_from_experience)


if __name__=='__main__':unittest.main()
