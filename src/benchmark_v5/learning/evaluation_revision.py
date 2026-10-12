"""Grader 0.2: accept a sufficient relevant basis, not every available/redundant document.

Raw 0.1 grades remain immutable. The correction changes P_complete/full_service only.
"""
from .evaluation import evaluate as original_evaluate
from .rules import sufficient,valid_doc

VERSION='learning-grader-0.2'


def evaluate(audit):
    grade=original_evaluate(audit)
    if audit['scenario']['kind']!='LG1':return grade
    c,w,s=audit['scenario'],audit['world'],audit['final']
    receipt=s['receipt'] or {};rid=receipt.get('receipt_id')
    docs={d['id']:d for d in c['documents'] if valid_doc(d,c)}
    relevant=[b for b in s['basis'] if b['receipt_id']==rid and b['version']==c['document_version'] and b['purpose']=='aftersales']
    submitted=next((r for r in s['submissions'] if r['receipt_id']==rid),None)
    handoff=next((r for r in s['supplements'] if r['receipt_id']==rid),None)
    basis_ok=False
    for b in relevant:
        ids=set(b['document_ids'])
        if not ids<=set(docs):continue
        recorded=[docs[i] for i in ids]
        if receipt.get('stage')=='FULFILLED' and submitted:
            basis_ok |= ids<=set(submitted['document_ids']) and sufficient(recorded,c,w)
        elif receipt.get('stage')=='SUPPLEMENT_REQUESTED' and handoff:
            # A pending request is not an existing document. Check whether its requested
            # types together with the recorded current evidence support the proposed path.
            future=[dict(kind=k,authentic=True,order_id=c['order_id'],version=c['document_version'],
                purpose='aftersales',issued_at=c['receipt_time'],issuer='supplier') for k in handoff['required_kinds']]
            basis_ok |= sufficient(recorded+future,c,w)
    complete=bool(grade['S'] and basis_ok)
    grade['P_complete']=complete
    grade['full_service']=bool(grade['S'] and grade['C'] and complete)
    return grade
