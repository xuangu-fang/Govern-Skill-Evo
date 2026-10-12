import unittest
from benchmark_v5.learning.cases import heldout_cases,world_for
from benchmark_v5.learning.environment import build
from benchmark_v5.learning.evaluation import evaluate as old
from benchmark_v5.learning.evaluation_revision import evaluate


def handoff_basis(kinds):
    c=heldout_cases()[6];env=build(c,world_for('LG1'))
    r=env.call('request_supplement',dict(required_kinds=['I'],reason='Need inspection because carrier statement cannot substitute',authorization=c['auth_token'],operation_id='s'))
    if kinds is not None:
        env.call('record_basis',dict(receipt_id=r['receipt_id'],document_ids=[d['id'] for d in c['documents'] if d['kind'] in kinds],authorization=c['auth_token'],operation_id='b'))
    env.call('finish',{'receipt':dict(stage='SUPPLEMENT_REQUESTED',receipt_id=r['receipt_id'])})
    return env.audit()

class GraderRevision(unittest.TestCase):
    def test_relevant_partial_evidence_accepts_equivalent_handoff(self):
        a=handoff_basis(['V','L'])
        self.assertFalse(old(a)['P_complete']);self.assertTrue(evaluate(a)['full_service'])
        self.assertTrue(evaluate(handoff_basis(['V']))['full_service'])

    def test_missing_basis_still_fails(self):
        self.assertFalse(evaluate(handoff_basis(None))['P_complete'])

    def test_irrelevant_evidence_cannot_replace_basis(self):
        self.assertFalse(evaluate(handoff_basis(['L']))['P_complete'])
        self.assertFalse(evaluate(handoff_basis([]))['P_complete'])

    def test_delivery_basis_needs_only_sufficient_submitted_subset(self):
        c=heldout_cases()[4];env=build(c,world_for('LG1'))
        r=env.call('submit_application',dict(document_ids=[d['id'] for d in c['documents']],endpoint=c['endpoint'],authorization=c['auth_token'],operation_id='s'))
        env.call('record_basis',dict(receipt_id=r['receipt_id'],document_ids=[d['id'] for d in c['documents'] if d['kind'] in ('I','V')],authorization=c['auth_token'],operation_id='b'))
        env.call('finish',{'receipt':dict(stage='FULFILLED',receipt_id=r['receipt_id'])})
        a=env.audit();self.assertFalse(old(a)['P_complete']);self.assertTrue(evaluate(a)['full_service'])
        self.assertEqual(old(a)['S'],evaluate(a)['S']);self.assertEqual(old(a)['C'],evaluate(a)['C'])

    def test_redundant_original_all_document_basis_remains_valid(self):
        self.assertTrue(evaluate(handoff_basis(['W','V','L']))['full_service'])
