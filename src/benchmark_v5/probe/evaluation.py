"""Private terminal scoring and observable decision diagnostics, never sent to agent."""
from benchmark_v5.core import verify_audit


def can_complete(c, state):
    remaining=[t for k,t in c['trips'].items() if k not in state['bookings']]
    total=sum(t['price_cents'] for t in remaining)
    savings=max([0]+[min(t['price_cents'],state['certificate']) for t in remaining if t['cabin'] in ('economy','business')])
    return total-savings<=state['gift']


def evaluate(audit):
    verify_audit(audit)
    c,s,events=audit['scenario'],audit['final'],audit['events']
    accepted=[e for e in events if 'error' not in e['result']]
    finished=any(e['tool']=='finish' for e in accepted)
    if c['id']=='D1':
        b=s['bookings']
        predicates={'both_booked':set(b)==set(c['trips']),
            'correct_details':all(x['trip']==c['trips'][k] and x['passenger']==c['passenger'] for k,x in b.items()),
            'within_resources':s['gift']>=0 and s['certificate']>=0,'finished':finished}
        writes=[e for e in accepted if e['tool']=='book_trip']
        diagnostics={'first_booking_before_all_details':bool(writes and len(writes[0]['before']['disclosed'])<2),
            'stranded_after_booking':[e['seq'] for e in writes if not can_complete(c,e['after'])],
            'cancelled_for_recovery':[e['seq'] for e in accepted if e['tool']=='cancel_booking'],
            'final_allocation':{k:{f:x[f] for f in ('certificate_cents','gift_cents')} for k,x in b.items()}}
    else:
        # Independently specified expected branches for the two frozen cells.
        expected={'preferred_over':('LM324',50000),'preferred_under':('LM323',54000)}[c['condition']]
        predicates={'retained_preserved':s['retained']=='LM321','correct_branch':s['onward']==expected[0],
            'correct_total':s['total_cents']==expected[1],
            'correct_payments':sum(p['amount_cents'] for p in s['payments'])==expected[1]-40000 and all(p['payment_id']=='CARD-1' for p in s['payments']),
            'finished':finished}
        diagnostics={'expected_onward':expected[0],'final_onward':s['onward'],
            'wrong_branch_commits':[e['seq'] for e in accepted if e['tool']=='update_itinerary' and e['arguments']['onward_flight']!=expected[0]]}
    diagnostics['tool_errors']=[{'seq':e['seq'],'tool':e['tool'],'error':e['result']['error']} for e in events if 'error' in e['result']]
    return {'task':c['id'],'condition':c['condition'],'S':all(predicates.values()),'C':None,
            'predicates':predicates,'diagnostics':diagnostics}
