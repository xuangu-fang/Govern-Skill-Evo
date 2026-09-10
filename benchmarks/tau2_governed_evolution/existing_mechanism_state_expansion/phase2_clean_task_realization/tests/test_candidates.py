"""Synthetic outcome fixtures only; never executes environment/backend actions."""
import copy
import json
import unittest
from pathlib import Path
from tau2.data_model.tasks import Task
from benchmarks.tau2_governed_evolution.existing_mechanism_state_expansion.phase2_clean_task_realization import benchmark_adapter as adapter
from benchmarks.tau2_governed_evolution.existing_mechanism_state_expansion.phase2_clean_task_realization.build_candidates import leakage, digest, preservation_snapshot
from benchmarks.tau2_governed_evolution.existing_mechanism_state_expansion.phase2_clean_task_realization.evaluators.success import evaluate
HERE=Path(__file__).resolve().parents[1]
REPO=HERE.parents[3]

def load(path):return json.loads(path.read_text())

class Candidates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db=load(REPO/'external/tau2-bench/data/tau2/domains/airline/db.json')
        cls.tasks=load(HERE/'tasks/candidate_tasks.json')
        cls.specs=load(HERE/'evaluators/goal_specs.json')

    def fixture(self,spec,mixed=False):
        # Construct a detached outcome document. No backend or native mutation.
        final=copy.deepcopy(self.db)
        uid=spec['user_id']
        if spec['kind']=='bookings':
            certificate,gift=spec['allowed_resources']
            remainder=self.db['users'][uid]['payment_methods'][gift]['amount']-100
            for i,trip in enumerate(spec['trips']):
                rid=f'UNPREDICTED_{i}_ID'
                r={k:copy.deepcopy(v) for k,v in trip.items() if k!='total'}
                payments=[{'payment_id':gift if i==0 else certificate,'amount':trip['total']}]
                if mixed and i==1:
                    payments=[{'payment_id':gift,'amount':remainder},{'payment_id':certificate,'amount':trip['total']-remainder}]
                r.update(reservation_id=rid,user_id=uid,payment_history=payments)
                final['reservations'][rid]=r
                final['users'][uid]['reservations'].append(rid)
            final['users'][uid]['payment_methods'].pop(certificate)
            final['users'][uid]['payment_methods'][gift]['amount']=0 if mixed else remainder
        else:
            r=final['reservations'][spec['reservation_id']]
            if spec['kind']=='cancel':
                r['status']='cancelled'
                r['payment_history'] += [{'payment_id':p['payment_id'],'amount':-p['amount']} for p in copy.deepcopy(r['payment_history'])]
            else:
                r['flights']=copy.deepcopy(spec['flights'])
                r['payment_history'].append({'payment_id':spec['payment_id'],'amount':spec['fare_difference']})
        return final

    def test_all_native_schemas_and_ids(self):
        self.assertEqual(len(self.tasks),14)
        self.assertEqual(len({t['id'] for t in self.tasks}),14)
        for task in self.tasks:
            with self.subTest(task=task['id']):
                parsed=Task.model_validate(task)
                spec=self.specs[parsed.id]
                self.assertIn(spec['user_id'],self.db['users'])
                self.assertIsNone(parsed.initial_state)
                self.assertIsNone(parsed.evaluation_criteria)
                instructions=task['user_scenario']['instructions']
                for k in ('reason_for_call','known_info','task_instructions'):self.assertTrue(instructions[k])
                if spec['kind']!='bookings':self.assertIn(spec['reservation_id'],self.db['reservations'])
                else:
                    for r in spec['allowed_resources']:self.assertIn(r,self.db['users'][spec['user_id']]['payment_methods'])

    def test_request_whitelist_and_full_context(self):
        manifest=load(REPO/'benchmarks/tau2_governed_evolution/phase_a_final_context/final_context_manifest.json')['contexts']['airline']
        self.assertEqual(digest(REPO/manifest['policy_path']),manifest['policy_sha256'])
        for i,task in enumerate(self.tasks,1):
            with self.subTest(task=task['id']):
                request=load(HERE/f"requests/{task['id']}.json")
                self.assertEqual(request['domain_policy'],(REPO/manifest['policy_path']).read_text())
                self.assertEqual(leakage(request),[])
                self.assertEqual(len(request['tools']),14)
                poison=copy.deepcopy(task)
                poison['description']={'purpose':'LGA03 ACTIVE dev state'}
                poison['source_native_state']='secret';poison['user_scenario']['instructions']['mechanism']='LGA01'
                self.assertEqual(adapter.build_task_request(poison,f'T{i:03d}',request['tools']),request)
                self.assertTrue(leakage({'text':'ACTIVE LGA03 state expansion'}))

    def test_every_positive_endpoint_and_unchanged_negative(self):
        for task in self.tasks:
            with self.subTest(task=task['id']):
                spec=self.specs[task['id']]
                self.assertTrue(adapter.evaluate_success(Task.model_validate(task),self.db,self.fixture(spec))['success'])
                self.assertFalse(adapter.evaluate_success(task,self.db,self.db)['success'])
                self.assertFalse(evaluate(spec,self.db,{})['success'])
                self.assertFalse(evaluate(spec,self.db,self.fixture(spec))['compliance_evaluated'])

    def test_p4_mixed_payments_and_arbitrary_booking_ids(self):
        for spec in self.specs.values():
            if spec['kind']!='bookings':continue
            with self.subTest(user=spec['user_id']):
                self.assertTrue(evaluate(spec,self.db,self.fixture(spec,True))['success'])
                for variant in ('missing','wrong_date','wrong_passenger','wrong_cabin','unauthorized','underpaid','reversed','cancelled','extra'):
                    final=self.fixture(spec,True); r=final['reservations']['UNPREDICTED_1_ID']
                    if variant=='missing':del final['reservations']['UNPREDICTED_1_ID']
                    if variant=='wrong_date':r['flights'][0]['date']='2024-05-30'
                    if variant=='wrong_passenger':r['passengers'][0]['first_name']='SomeoneElse'
                    if variant=='wrong_cabin':r['cabin']='business'
                    if variant=='unauthorized':r['payment_history'][0]['payment_id']='credit_card_other'
                    if variant=='underpaid':r['payment_history'][0]['amount']-=1
                    if variant=='reversed':final['users'][spec['user_id']]['reservations'][-2:]=['UNPREDICTED_1_ID','UNPREDICTED_0_ID']
                    if variant=='cancelled':r['status']='cancelled'
                    if variant=='extra':
                        final['reservations']['EXTRA']=copy.deepcopy(r)
                        final['users'][spec['user_id']]['reservations'].append('EXTRA')
                    self.assertFalse(evaluate(spec,self.db,final)['success'],variant)

    def test_cancellation_refund_and_roster_properties(self):
        for spec in self.specs.values():
            if spec['kind']!='cancel':continue
            with self.subTest(state=spec['reservation_id']):
                final=self.fixture(spec)
                r=final['reservations'][spec['reservation_id']]
                # Two refund entries instead of one remain outcome equivalent.
                refund=r['payment_history'].pop()
                r['payment_history'] += [{**refund,'amount':refund['amount']/2}]*2
                self.assertTrue(evaluate(spec,self.db,final)['success'])
                r['payment_history'].pop()
                self.assertFalse(evaluate(spec,self.db,final)['success'])
                final=self.fixture(spec);final['reservations'][spec['reservation_id']]['passengers']=[]
                self.assertFalse(evaluate(spec,self.db,final)['success'])

    def test_scope_uses_segments_not_stale_header(self):
        for spec in self.specs.values():
            if spec['kind']!='change':continue
            final=self.fixture(spec)
            rid=spec['reservation_id']
            self.assertEqual(final['reservations'][rid]['destination'],self.db['reservations'][rid]['destination'])
            self.assertTrue(evaluate(spec,self.db,final)['success'])
            final['reservations'][rid]['flights']=copy.deepcopy(self.db['reservations'][rid]['flights'])
            final['reservations'][rid]['destination']=spec['flights'][-1]['destination']
            self.assertFalse(evaluate(spec,self.db,final)['success'])
            final=self.fixture(spec);final['reservations'][rid]['payment_history'][-1]['amount']+=1
            self.assertFalse(evaluate(spec,self.db,final)['success'])

    def test_policy_separation_and_unknown_dispatch(self):
        # Both an ineligible cancellation and eligible cancellation achieve the
        # same user goal in a synthetic endpoint; policy eligibility is separate.
        for tid in ('travel_request_004','travel_request_008','travel_request_010'):
            spec=self.specs[tid]
            self.assertTrue(evaluate(spec,self.db,self.fixture(spec))['success'])
        self.assertIn('health or weather',adapter.canonical_judge_policy('airline'))
        with self.assertRaises(ValueError):adapter.evaluate_success({'id':'unknown'},self.db,self.db)

    def test_preexisting_sources_unchanged(self):
        before=load(HERE/'audits/source_preservation.json')['before'];now=preservation_snapshot()
        self.assertEqual([p for p,h in before.items() if now.get(p)!=h],[])

if __name__=='__main__':unittest.main(verbosity=2)
