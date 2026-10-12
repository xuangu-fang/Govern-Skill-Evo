import unittest
from benchmark_v5.probe.environment import build, CELLS
from benchmark_v5.probe.evaluation import evaluate

class ProbeTests(unittest.TestCase):
    def call(self,e,name,**args):
        result=e.call(name,args)
        self.assertNotIn('error',result)
        return result

    def complete_d1(self,e,reverse=False):
        self.call(e,'ask_user',scope='all')
        for k in (['T2','T1'] if reverse else ['T1','T2']):
            t=e.scenario['trips'][k];cert=t['price_cents'] if t['cabin']=='economy' else 0
            self.call(e,'book_trip',trip_id=k,certificate_cents=cert,gift_cents=t['price_cents']-cert)
        self.call(e,'finish',receipt={})
        self.assertTrue(evaluate(e.audit())['S'])

    def test_feasible_all_d1_orders_and_information_conditions(self):
        for cond in ('staged','upfront','fare_flip'):
            for reverse in (False,True):
                with self.subTest(cond=cond,reverse=reverse):self.complete_d1(build('D1',cond),reverse)

    def test_local_split_strands_but_is_recoverable(self):
        e=build('D1','staged')
        self.call(e,'book_trip',trip_id='T1',certificate_cents=10000,gift_cents=8800)
        before=e.audit()['final']
        self.assertEqual(e.call('book_trip',dict(trip_id='T2',certificate_cents=0,gift_cents=22400)),{'error':'INSUFFICIENT_FUNDS'})
        self.assertEqual(e.audit()['final'],before)
        self.assertFalse(evaluate(e.audit())['S'])
        self.assertEqual(evaluate(e.audit())['diagnostics']['stranded_after_booking'],[1])
        self.call(e,'cancel_booking',trip_id='T1')
        self.assertEqual(e.call('read_wallet',{}),{'certificate':32000,'gift':27000})
        self.complete_d1(e)
        self.assertTrue(evaluate(e.audit())['diagnostics']['first_booking_before_all_details'])

    def test_repeated_cancel_cannot_duplicate_credit(self):
        e=build('D1','staged')
        self.call(e,'book_trip',trip_id='T1',certificate_cents=18800,gift_cents=0)
        self.call(e,'cancel_booking',trip_id='T1')
        self.assertIn('error',e.call('cancel_booking',{'trip_id':'T1'}))
        self.assertEqual(e.call('read_wallet',{}),{'certificate':32000,'gift':27000})

    def test_d2_correct_and_incorrect_branch_and_recovery(self):
        for cond,correct,wrong in [('preferred_over','LM324','LM323'),('preferred_under','LM323','LM324')]:
            e=build('D2',cond)
            self.call(e,'update_itinerary',retained_flight='LM321',onward_flight=wrong,payment_id='CARD-1')
            self.assertFalse(evaluate(e.audit())['predicates']['correct_branch'])
            self.call(e,'update_itinerary',retained_flight='LM321',onward_flight=correct,payment_id='CARD-1')
            self.call(e,'finish',receipt={})
            score=evaluate(e.audit());self.assertTrue(score['S']);self.assertEqual(score['diagnostics']['wrong_branch_commits'],[1])

    def test_finish_alone_never_succeeds(self):
        for task,cond in CELLS:
            e=build(task,cond);self.call(e,'finish',receipt={})
            self.assertFalse(evaluate(e.audit())['S'])

    def test_wrong_types_do_not_mutate_money(self):
        e=build('D1','staged');before=e.audit()['final']
        self.assertIn('error',e.call('book_trip',dict(trip_id='T1',certificate_cents=True,gift_cents=18799)))
        self.assertEqual(e.audit()['final'],before)

    def test_public_catalog_does_not_expose_grader_or_private_state(self):
        for task,cond in CELLS:
            e=build(task,cond);names={t['name'] for t in e.catalog()}
            self.assertFalse(names & {'audit','evaluate','scenario','can_complete'})
            self.assertNotIn('expected',str(e.request()))

if __name__=='__main__':unittest.main()
