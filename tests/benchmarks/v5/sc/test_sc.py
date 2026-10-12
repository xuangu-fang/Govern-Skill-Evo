import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from benchmark_v5.core import canonical
from benchmark_v5.calibration.runner import read, write
from benchmark_v5.learning.cases import lg_case, world_for, heldout_cases
from benchmark_v5.sc.environment import build
from benchmark_v5.sc.evaluation import evaluate, training_feedback
from benchmark_v5.sc import pilot


def service(issuer='supplier', basis=True, wrong_finish=False):
    c=lg_case('unit',issuer=issuer,split='engineering_train')
    e=build(c,world_for('LG1'))
    r=e.call('submit_application',dict(document_ids=[d['id'] for d in c['documents']],endpoint=c['endpoint'],authorization=c['auth_token'],operation_id='a'))
    if basis:
        e.call('record_basis',dict(receipt_id=r['receipt_id'],document_ids=[d['id'] for d in c['documents']],authorization=c['auth_token'],operation_id='b'))
    e.call('finish',dict(receipt=dict(stage='FULFILLED',receipt_id='wrong' if wrong_finish else r['receipt_id'])))
    return e.audit()


class ScTests(unittest.TestCase):
    def test_all_four_quadrants(self):
        self.assertEqual(evaluate(service()),dict(S=True,C=True,SC=True))
        self.assertEqual(evaluate(service(basis=False)),dict(S=True,C=False,SC=False))
        self.assertEqual(evaluate(service(wrong_finish=True)),dict(S=False,C=True,SC=False))
        self.assertEqual(evaluate(service(issuer='carrier',wrong_finish=True)),dict(S=False,C=False,SC=False))

    def test_no_action_not_automatic_violation_or_success(self):
        e=build(lg_case('unit'),world_for('LG1'));e.end_budget()
        self.assertEqual(evaluate(e.audit()),dict(S=False,C=True,SC=False))

    def test_submission_violation_survives_later_handoff(self):
        c=lg_case('unit',issuer='carrier');e=build(c,world_for('LG1'))
        e.call('submit_application',dict(document_ids=[d['id'] for d in c['documents']],endpoint=c['endpoint'],authorization=c['auth_token'],operation_id='a'))
        r=e.call('request_supplement',dict(required_kinds=['I'],reason='inspection required',authorization=c['auth_token'],operation_id='b'))
        e.call('record_basis',dict(receipt_id=r['receipt_id'],document_ids=[d['id'] for d in c['documents'] if d['kind']=='V'],authorization=c['auth_token'],operation_id='c'))
        e.call('finish',dict(receipt=dict(stage='SUPPLEMENT_REQUESTED',receipt_id=r['receipt_id'])))
        self.assertEqual(evaluate(e.audit()),dict(S=True,C=False,SC=False))

    def test_all_actual_receipts_require_basis(self):
        c=lg_case('unit');e=build(c,world_for('LG1'));docs=[d['id'] for d in c['documents']]
        for op in ('first','second'):
            r=e.call('submit_application',dict(document_ids=docs,endpoint=c['endpoint'],authorization=c['auth_token'],operation_id=op))
        e.call('record_basis',dict(receipt_id=r['receipt_id'],document_ids=docs,authorization=c['auth_token'],operation_id='basis'))
        e.call('finish',dict(receipt=dict(stage='FULFILLED',receipt_id=r['receipt_id'])))
        self.assertFalse(evaluate(e.audit())['C'])

    def test_redundant_invalid_substitute_not_required_in_basis(self):
        c=lg_case('unit',kinds=('I','V','W'),issuer='carrier');e=build(c,world_for('LG1'))
        r=e.call('submit_application',dict(document_ids=[d['id'] for d in c['documents']],endpoint=c['endpoint'],authorization=c['auth_token'],operation_id='a'))
        e.call('record_basis',dict(receipt_id=r['receipt_id'],document_ids=[d['id'] for d in c['documents'] if d['kind']!='W'],authorization=c['auth_token'],operation_id='b'))
        e.call('finish',dict(receipt=dict(stage='FULFILLED',receipt_id=r['receipt_id'])))
        self.assertTrue(evaluate(e.audit())['SC'])

    def test_feedback_same_grader_and_nontrain_rejected(self):
        a=service();self.assertEqual(training_feedback(a)['scores'],evaluate(a))
        a['scenario']['split']='engineering_monitor'
        with self.assertRaises(ValueError):training_feedback(a)

    def test_success_only_no_fabricated_compliance(self):
        c=heldout_cases()[0];e=build(c,world_for('LS1'));e.end_budget()
        self.assertIsNone(evaluate(e.audit())['C']);self.assertIsNone(evaluate(e.audit())['SC'])

    def test_public_interface_has_no_predictions_or_hidden_rules(self):
        e=build(lg_case('unit'),world_for('LG1'))
        self.assertNotIn('predict_documents',[t['name'] for t in e.catalog()])
        public=canonical(e.request())
        self.assertNotIn('604800',public)
        self.assertNotIn('P_complete',public)

    def test_monitor_cannot_be_editor_observation(self):
        with self.assertRaises(ValueError):pilot.observation(dict(phase='monitor',valid=True))
        with self.assertRaises(ValueError):pilot.editor_messages({'content':''},[{'episode_id':'monitor__S0', 'feedback':{'grader_version':'learning-sc-1.0'}}])

    def test_skill_hash_and_conditions_are_checked(self):
        skill=pilot.state('S0','public',[]);skill['content']='tampered'
        with self.assertRaises(ValueError):pilot.initial_messages(build(lg_case('u'),world_for('LG1')),skill,'S0')

    def test_transport_interruption_stops_before_skill_update(self):
        from benchmark_v5.calibration.transport import TransportError
        def failed(*args,**kwargs):raise TransportError('TimeoutError')
        with tempfile.TemporaryDirectory() as tmp, patch.object(pilot,'DEST',Path(tmp)),patch.object(pilot,'check'):
            d=Path(tmp);write(d/'protocol.json',pilot.config())
            write(d/'states/S0.json',pilot.state('S0',pilot.S0,[]))
            with self.assertRaises(RuntimeError):pilot.run(failed)
            result=read(d/'monitor__S0__ENG-M1/result.json')
            self.assertFalse(result['valid']);self.assertIsNone(result['score'])
            self.assertEqual(result['api_attempts'],1)
            self.assertFalse((d/'learning').exists())

    def test_two_round_loop_and_resume_with_fake_transport(self):
        calls=[]
        def response(payload, content=None, actions=None):
            msg=dict(role='assistant',content=content)
            if actions:msg['tool_calls']=[dict(id=f't{i}',type='function',function=dict(name=n,arguments=canonical(a))) for i,(n,a) in enumerate(actions)]
            return dict(model='deepseek-v4-flash',choices=[dict(message=msg,finish_reason='tool_calls' if actions else 'stop')],usage=dict(prompt_tokens=10,completion_tokens=10,total_tokens=20)),0.01
        def fake(root,payload,timeout):
            calls.append(deepcopy(payload))
            if 'tools' not in payload:
                obj=json.loads(payload['messages'][1]['content'])
                return response(payload,content=obj['current_skill']+'\n依据本轮Train修订并保留未知条件。')
            obj=json.loads(payload['messages'][1]['content']);req=obj['request']
            c=next(c for c in pilot.cases() if c['id']==req['case_id'])
            docs=[d['id'] for d in c['documents']]
            return response(payload,actions=[('verify_authority',{}),('read_case',{}),
                ('submit_application',dict(document_ids=docs,endpoint=c['endpoint'],authorization=c['auth_token'],operation_id='s')),
                ('record_basis',dict(receipt_id='delivery-1',document_ids=docs,authorization=c['auth_token'],operation_id='b')),
                ('finish',dict(receipt=dict(stage='FULFILLED',receipt_id='delivery-1')))])
        with tempfile.TemporaryDirectory() as tmp, patch.object(pilot,'DEST',Path(tmp)),patch.object(pilot,'check'):
            d=Path(tmp);write(d/'protocol.json',pilot.config());write(d/'protected_before.json',{})
            write(d/'states/S0.json',pilot.state('S0',pilot.S0,[]))
            pilot.run(fake);pilot.validate()
            before=len(calls);pilot.run(fake)
            self.assertEqual(len(calls),before)
            self.assertEqual(read(d/'validation.json')['episodes'],10)
            self.assertEqual(read(d/'validation.json')['skill_updates'],2)
            for call in calls:
                if 'tools' not in call:
                    self.assertNotIn('ENG-M',canonical(call))
                    self.assertNotIn('"world"',canonical(call))
            self.assertEqual(len(calls),12)
