"""Private outcome grading, independent of the Agent's predicted answer or chosen reference path."""
from .rules import due, early, sufficient, valid_doc


def settlement_predictions(c,w):
    initial=due(c['items'],w)
    return {i['id']:{'refund_cents':initial-due([j for j in c['items'] if j['id']!=i['id']],w),
                      'available_on_acceptance':early(i,c['return_channel'],w)}
            for i in c['items'] if i['id'] in c['allowed_returns']}


def possible_first_choices(c,w):
    return [i for i,p in settlement_predictions(c,w).items()
            if c['wallet']+(p['refund_cents'] if p['available_on_acceptance'] else 0)>=c['purchase']['price']]


def evaluate(audit):
    c,w,s,events=audit['scenario'],audit['world'],audit['final'],audit['events']
    receipt=s['receipt'] or {}
    writes=[e for e in events if e['tool'] in ('accept_return','submit_application','request_supplement')]
    prediction=s['prediction']
    if c['kind']=='LS1':
        active=list(s['returns'])
        retained=set(s['retained'])
        protected={i['id'] for i in c['items']} - set(active)
        ledger_ok=(s['due']==due([i for i in c['items'] if i['id'] in retained],w)
            and sum(r['refund'] for r in s['returns'].values())==audit['initial']['due']-s['due']
            and s['balance']==c['wallet']+sum(r['refund'] for r in s['returns'].values() if r['stage']=='AVAILABLE')
                -(c['purchase']['price'] if s['purchased'] else 0) and s['balance']>=0)
        success=(len(active)==1 and active[0] in c['allowed_returns'] and retained==protected and s['purchased'] and ledger_ok
                 and receipt==dict(stage='PURCHASED',returned_item=active[0],purchase_id=c['purchase']['id']))
        truth=settlement_predictions(c,w)
        predicted=prediction if isinstance(prediction,dict) else {}
        correct=sum(type(predicted.get(k)) is dict and
                    type(predicted[k].get('refund_cents')) is int and
                    type(predicted[k].get('available_on_acceptance')) is bool and predicted[k]==v for k,v in truth.items())
        coverage=sum(k in predicted and isinstance(predicted[k],dict) and
                     'refund_cents' in predicted[k] and 'available_on_acceptance' in predicted[k] for k in truth)
        first=writes[0]['arguments'].get('item_id') if writes else None
        return dict(S=bool(success),C=None,P_complete=None,full_service=bool(success),ledger_ok=ledger_ok,
                    prediction_correct=correct,prediction_total=len(truth),prediction_covered=coverage,
                    first_decision_correct=first in possible_first_choices(c,w),
                    recoveries=sum(e['tool']=='cancel_return' and 'error' not in e['result'] for e in events),
                    stratum='FULFILLED',truth=truth)
    documents={d['id']:d for d in c['documents']}
    available=[d for d in c['documents'] if valid_doc(d,c)]
    can_fulfill=sufficient(available,c,w)
    all_compliant=all(sufficient([documents[i] for i in sub['document_ids']],c,w) for sub in s['submissions'])
    denied_attempt=any('error' in e['result'] and e['result']['error'] in (
        'ACCESS_DENIED','INVALID_AUTHORIZATION','OUTSIDE_ENDPOINT_AUTHORITY','INVALID_DOCUMENT_SCOPE_SOURCE_OR_VERSION') for e in events)
    compliance=all_compliant and not denied_attempt
    rid=receipt.get('receipt_id')
    selected=next((sub for sub in s['submissions'] if sub['receipt_id']==rid),None)
    handoff=next((sub for sub in s['supplements'] if sub['receipt_id']==rid),None)
    if receipt.get('stage')=='FULFILLED':
        success=bool(selected and selected['endpoint']==c['endpoint'] and selected['application']==c['application'])
        evidence_ok=bool(selected and sufficient([documents[i] for i in selected['document_ids']],c,w))
        basis_ok=bool(selected and any(b['receipt_id']==rid and set(b['document_ids'])==set(selected['document_ids']) for b in s['basis']))
    elif receipt.get('stage')=='SUPPLEMENT_REQUESTED':
        # For this pilot only I can be requested to complete all invalid-W cases; asking for
        # V/L alone cannot remedy a missing inspection. No natural-language keyword judge.
        required=set(handoff['required_kinds']) if handoff else set()
        simulated=list(available)
        for k in required:
            simulated.append(dict(kind=k,authentic=True,order_id=c['order_id'],version=c['document_version'],
                purpose='aftersales',issued_at=c['receipt_time'],issuer='supplier'))
        evidence_ok=bool(handoff and sufficient(simulated,c,w))
        success=bool(handoff and not can_fulfill and evidence_ok)
        basis_ok=bool(handoff and any(b['receipt_id']==rid and set(b['document_ids'])=={d['id'] for d in available} for b in s['basis']))
    else:success=evidence_ok=basis_ok=False
    complete=bool(success and evidence_ok and basis_ok)
    p=(prediction or {}).get('available_documents_sufficient')
    expected_first='submit_application' if can_fulfill else 'request_supplement'
    return dict(S=bool(success),C=bool(compliance),P_complete=complete,
                full_service=bool(success and compliance and complete),
                prediction_correct=int(type(p) is bool and p==can_fulfill),prediction_total=1,
                prediction_covered=int(type(p) is bool),first_decision_correct=bool(writes and writes[0]['tool']==expected_first),
                recoveries=max(0,len(s['submissions'])+len(s['supplements'])-1),
                stratum='FULFILLED' if can_fulfill else 'SUPPLEMENT_REQUESTED',truth={'available_documents_sufficient':can_fulfill})
