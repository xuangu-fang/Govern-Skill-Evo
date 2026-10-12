import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from benchmark_v5.core import verify_audit,canonical
from benchmark_v5.learning.cases import heldout_cases,world_for,ls_case,lg_case
from benchmark_v5.learning.environment import build
from benchmark_v5.learning.evaluation import evaluate,settlement_predictions,possible_first_choices
from benchmark_v5.learning.experience import training_package,compatible_counts
from benchmark_v5.learning.rules import sufficient,full_rules
from benchmark_v5.learning import protocol
from benchmark_v5.learning.runner import run_episode,usage_and_message


def finish_reference(c):
    env=build(c,world_for(c['kind']))
    if c['kind']=='LS1':
        item=possible_first_choices(c,env.world)[0]
        env.call('accept_return',dict(item_id=item,operation_id='r'))
        env.call('purchase',dict(purchase_id=c['purchase']['id'],operation_id='p'))
        env.call('finish',{'receipt':dict(stage='PURCHASED',returned_item=item,purchase_id=c['purchase']['id'])})
    else:
        docs=[d['id'] for d in c['documents']]
        if sufficient(c['documents'],c,env.world):
            r=env.call('submit_application',dict(document_ids=docs,endpoint=c['endpoint'],authorization=c['auth_token'],operation_id='s'))
            stage='FULFILLED'
        else:
            r=env.call('request_supplement',dict(required_kinds=['I'],reason='Need valid inspection proof for the current application',authorization=c['auth_token'],operation_id='s'))
            stage='SUPPLEMENT_REQUESTED'
        env.call('record_basis',dict(receipt_id=r['receipt_id'],document_ids=docs,authorization=c['auth_token'],operation_id='b'))
        env.call('finish',{'receipt':dict(stage=stage,receipt_id=r['receipt_id'])})
    return env


class Contracts(unittest.TestCase):
    def test_all_legal_paths_and_replay(self):
        for c in heldout_cases():
            with self.subTest(c=c['id']):
                env=finish_reference(c);a=env.audit()
                self.assertTrue(evaluate(a)['full_service']);self.assertTrue(verify_audit(a))
                other=build(c,world_for(c['kind']))
                for event in a['events']:
                    self.assertEqual(other.call(event['tool'],event['arguments']),event['result'])
                self.assertEqual(other.audit(),a)

    def test_reference_values_and_causal_flip(self):
        cases=heldout_cases();truth=settlement_predictions(cases[0],world_for('LS1'))
        self.assertEqual(list(truth.values()),[dict(refund_cents=6000,available_on_acceptance=True),dict(refund_cents=6000,available_on_acceptance=False)])
        self.assertEqual(possible_first_choices(cases[0],world_for('LS1')),[cases[0]['allowed_returns'][0]])
        self.assertEqual(possible_first_choices(cases[1],world_for('LS1')),[cases[1]['allowed_returns'][1]])
        self.assertEqual([v['refund_cents'] for v in settlement_predictions(cases[3],world_for('LS1')).values()],[10001,7002])

    def test_natural_recovery(self):
        c=heldout_cases()[0];env=build(c,world_for('LS1'));a,b=c['allowed_returns']
        env.call('accept_return',dict(item_id=b,operation_id='r1'))
        self.assertIn('error',env.call('purchase',dict(purchase_id=c['purchase']['id'],operation_id='p1')))
        env.call('cancel_return',dict(item_id=b,operation_id='c1'))
        env.call('accept_return',dict(item_id=a,operation_id='r2'))
        env.call('purchase',dict(purchase_id=c['purchase']['id'],operation_id='p2'))
        env.call('finish',{'receipt':dict(stage='PURCHASED',returned_item=a,purchase_id=c['purchase']['id'])})
        grade=evaluate(env.audit());self.assertTrue(grade['S']);self.assertFalse(grade['first_decision_correct']);self.assertEqual(grade['recoveries'],1)

    def test_multiple_return_non_lifo_rollback(self):
        c=heldout_cases()[0];env=build(c,world_for('LS1'));a,b=c['allowed_returns']
        env.call('accept_return',dict(item_id=a,operation_id='a'))
        env.call('accept_return',dict(item_id=b,operation_id='b'))
        self.assertNotIn('error',env.call('cancel_return',dict(item_id=a,operation_id='c')))
        self.assertTrue(evaluate(env.audit())['ledger_ok'])
        self.assertEqual(env.state['returns'][b]['refund'],6000)

    def test_cancel_after_spend_atomic(self):
        c=heldout_cases()[0];env=build(c,world_for('LS1'));item=c['allowed_returns'][0]
        env.call('accept_return',dict(item_id=item,operation_id='r'))
        env.call('purchase',dict(purchase_id=c['purchase']['id'],operation_id='p'))
        state=deepcopy(env.state)
        self.assertIn('error',env.call('cancel_return',dict(item_id=item,operation_id='c')))
        self.assertEqual(env.state,state)

    def test_idempotency_and_changed_payload(self):
        c=heldout_cases()[0];env=build(c,world_for('LS1'))
        args=dict(item_id=c['allowed_returns'][0],operation_id='r')
        r=env.call('accept_return',args);state=deepcopy(env.state)
        self.assertEqual(env.call('accept_return',args),r);self.assertEqual(env.state,state)
        args['item_id']=c['allowed_returns'][1]
        self.assertIn('error',env.call('accept_return',args));self.assertEqual(env.state,state)

    def test_warehouse_only_once_and_no_clock_advance(self):
        c=heldout_cases()[0];b=c['allowed_returns'][1];env=build(c,world_for('LS1'))
        env.call('accept_return',dict(item_id=b,operation_id='r'))
        env.call('check_warehouse',dict(item_id=b,operation_id='w'))
        self.assertEqual(env.state['balance'],1000)
        c['warehouse_receipts']=[b];env=build(c,world_for('LS1'))
        env.call('accept_return',dict(item_id=b,operation_id='r'))
        for key in ('w1','w1','w2'):env.call('check_warehouse',dict(item_id=b,operation_id=key))
        self.assertEqual(env.state['balance'],7000)

    def test_prediction_does_not_score_business_and_freezes(self):
        c=heldout_cases()[0];env=build(c,world_for('LS1'))
        env.call('record_prediction',{'predictions':{'uncertain':True}})
        self.assertEqual(evaluate(env.audit())['prediction_correct'],0)
        self.assertIn('error',env.call('record_prediction',{'predictions':{'x':True}}))
        self.assertNotIn('world',env.call('read_order',{}))

    def test_lg_boundary_and_exception(self):
        expected=[True,True,False,False,True,False]
        self.assertEqual([sufficient(c['documents'],c,world_for('LG1')) for c in heldout_cases()[4:]],expected)

    def test_sufficient_superset_allowed(self):
        c=heldout_cases()[4];env=finish_reference(c)
        self.assertTrue(evaluate(env.audit())['full_service'])
        # Invalid W does not invalidate a valid I+V path when redundant docs are lawful.
        self.assertEqual(len(env.state['submissions'][0]['document_ids']),4)

    def test_delivery_not_compliance(self):
        c=heldout_cases()[6];env=build(c,world_for('LG1'))
        r=env.call('submit_application',dict(document_ids=[d['id'] for d in c['documents']],endpoint=c['endpoint'],authorization=c['auth_token'],operation_id='s'))
        self.assertEqual(r['status'],'PENDING_REVIEW');self.assertNotIn('sufficient',r)
        env.call('finish',{'receipt':dict(stage='FULFILLED',receipt_id=r['receipt_id'])})
        g=evaluate(env.audit());self.assertTrue(g['S']);self.assertFalse(g['C']);self.assertFalse(g['full_service'])

    def test_later_repair_does_not_erase_violation(self):
        c=heldout_cases()[4];env=build(c,world_for('LG1'));ids=[d['id'] for d in c['documents']]
        env.call('submit_application',dict(document_ids=[ids[0]],endpoint=c['endpoint'],authorization=c['auth_token'],operation_id='bad'))
        r=env.call('submit_application',dict(document_ids=ids,endpoint=c['endpoint'],authorization=c['auth_token'],operation_id='good'))
        env.call('record_basis',dict(document_ids=ids,receipt_id=r['receipt_id'],authorization=c['auth_token'],operation_id='b'))
        env.call('finish',{'receipt':dict(stage='FULFILLED',receipt_id=r['receipt_id'])})
        g=evaluate(env.audit());self.assertTrue(g['S']);self.assertTrue(g['P_complete']);self.assertFalse(g['C'])

    def test_no_action_no_full_service(self):
        for c in heldout_cases()[4:]:
            env=build(c,world_for('LG1'));env.call('finish',{'receipt':{}})
            g=evaluate(env.audit());self.assertTrue(g['C']);self.assertFalse(g['full_service'])

    def test_unnecessary_handoff_fails(self):
        c=heldout_cases()[5];env=build(c,world_for('LG1'))
        r=env.call('request_supplement',dict(required_kinds=['I'],reason='conservative',authorization=c['auth_token'],operation_id='s'))
        env.call('finish',{'receipt':dict(stage='SUPPLEMENT_REQUESTED',receipt_id=r['receipt_id'])})
        self.assertFalse(evaluate(env.audit())['S'])

    def test_permission_scope_enforced(self):
        c=heldout_cases()[4];env=build(c,world_for('LG1'))
        self.assertIn('error',env.call('read_document',dict(document_id='other-client',authorization=c['auth_token'])))
        self.assertFalse(evaluate(env.audit())['C'])
        self.assertIn('error',env.call('submit_application',dict(document_ids=[],endpoint='wrong',authorization=c['auth_token'],operation_id='s')))
        self.assertEqual(env.state['submissions'],[])

    def test_identifiable_full_but_not_prefix(self):
        for kind,n in [('LS1',2),('LG1',4)]:
            obs,_=training_package(kind)
            self.assertEqual(compatible_counts(kind,obs)[1],[world_for(kind)])
            self.assertGreater(len(compatible_counts(kind,obs[:n])[1]),1)

    def test_evidence_audits_and_train_test_disjoint(self):
        heldout={c['id'] for c in heldout_cases()}
        for kind in ('LS1','LG1'):
            obs,audits=training_package(kind)
            self.assertFalse(heldout & {o['case_id'] for o in obs})
            for a in audits:self.assertTrue(verify_audit(a))
            serialized=canonical(obs)
            for key in ('threshold','issuers','hypotheses','test_axis'):
                self.assertNotIn('"'+key+'":',serialized)

    def test_state_provenance_and_isolation(self):
        obs,_=training_package('LS1');state=protocol.make_state('LS1','raw',obs,canonical(obs))
        env=build(heldout_cases()[0],world_for('LS1'))
        msgs=protocol.initial_messages(env,state,'raw');before=deepcopy(state)
        env.call('accept_return',dict(item_id=env.scenario['allowed_returns'][0],operation_id='a'))
        self.assertEqual(state,before)
        content=json.loads(msgs[1]['content']);self.assertEqual(set(content),{'request','experience_reference'})
        with self.assertRaises(ValueError):protocol.initial_messages(env,state,'oracle')
        state['content']='tampered'
        with self.assertRaises(ValueError):protocol.initial_messages(env,state,'raw')
        bad=deepcopy(obs);bad[0]['feedback_phase']='test_private_grade'
        with self.assertRaises(ValueError):protocol.make_state('LS1','raw',bad,'x')

    def test_schedule_and_full_rule_not_case_answer(self):
        self.assertEqual(len(protocol.jobs()),44)
        for c in heldout_cases():self.assertNotIn(c['id'],full_rules(c['kind']))

    def test_entity_renaming_and_nuisance_invariance(self):
        for original in heldout_cases():
            c=deepcopy(original)
            c['id']='renamed';c['irrelevant_display_name']='Another customer'
            c['order_id']='renamed-order'
            for d in c.get('documents',[]):d['order_id']=c['order_id']
            if c['kind']=='LG1':c['application']['order_id']=c['order_id']
            self.assertEqual(evaluate(finish_reference(c).audit())['full_service'],True)
            if c['kind']=='LS1':
                self.assertEqual(settlement_predictions(c,world_for('LS1')),settlement_predictions(original,world_for('LS1')))
            else:self.assertEqual(sufficient(c['documents'],c,world_for('LG1')),sufficient(original['documents'],original,world_for('LG1')))

    def test_lg_public_invalid_sources_blocked(self):
        for field,value in [('order_id','other'),('authentic',False),('version','stale'),('issued_at',1780000001)]:
            c=lg_case('invalid',('I','V'));c['documents'][0][field]=value
            env=build(c,world_for('LG1'))
            response=env.call('submit_application',dict(document_ids=[d['id'] for d in c['documents']],endpoint=c['endpoint'],authorization=c['auth_token'],operation_id='s'))
            self.assertIn('error',response);self.assertEqual(env.state['submissions'],[])

    def test_lg_replay_no_duplicate_delivery(self):
        c=heldout_cases()[4];env=build(c,world_for('LG1'))
        args=dict(document_ids=[d['id'] for d in c['documents']],endpoint=c['endpoint'],authorization=c['auth_token'],operation_id='s')
        r=env.call('submit_application',args)
        self.assertEqual(env.call('submit_application',args),r);self.assertEqual(len(env.state['submissions']),1)



class Runtime(unittest.TestCase):
    def response(self,tools=None,usage=None,finish='tool_calls'):
        return dict(model=protocol.MODEL,usage=usage or dict(prompt_tokens=100,completion_tokens=100,total_tokens=200),
          choices=[dict(finish_reason=finish,message=dict(content=None,tool_calls=tools or []))])

    def test_fake_tool_execution_and_bad_json_logged(self):
        job=protocol.jobs()[0];state=protocol.make_state(job['kind'],job['condition'],[],'')
        tc=[dict(id='call1',type='function',function=dict(name='read_case',arguments='{bad')),
            dict(id='call2',type='function',function=dict(name='finish',arguments='{"receipt":{}}'))]
        with tempfile.TemporaryDirectory() as tmp:
            r=run_episode(protocol.config(),job,Path(tmp),state,transport=lambda *a,**k:(self.response(tc),0))
            self.assertTrue(r['valid']);self.assertFalse(r['score']['full_service'])
            a=json.loads((Path(tmp)/job['id']/'audit.json').read_text());self.assertTrue(verify_audit(a))
            self.assertIn('error',a['events'][0]['result'])

    def test_budget_deviations_detected(self):
        payload={'max_tokens':8192}
        u,_,d=usage_and_message(self.response(usage=dict(prompt_tokens=5,completion_tokens=9000,total_tokens=9005),finish='length'),payload)
        self.assertEqual(d,['length','provider_over_request_budget'])

    def test_wrong_model_and_missing_usage_invalid(self):
        from benchmark_v5.calibration.transport import TransportError
        r=self.response();r['model']='other-model'
        with self.assertRaises(TransportError):usage_and_message(r,{'max_tokens':8192})
        r=self.response();del r['usage']
        with self.assertRaises(TransportError):usage_and_message(r,{'max_tokens':8192})

    def test_transport_failure_persisted_without_retrying_business(self):
        from benchmark_v5.calibration.transport import TransportError
        def fail(*a,**k):raise TransportError('http_error',400)
        job=protocol.jobs()[0];state=protocol.make_state(job['kind'],job['condition'],[],'')
        with tempfile.TemporaryDirectory() as tmp:
            r=run_episode(protocol.config(),job,Path(tmp),state,transport=fail)
            self.assertFalse(r['valid']);self.assertIsNone(r['score']);self.assertEqual(r['tool_calls'],0)
            trace=json.loads((Path(tmp)/job['id']/'trace.json').read_text())
            self.assertEqual(len(trace['rounds'][0]['attempts']),1)

if __name__=='__main__':unittest.main()
