"""Authorized deterministic sandbox evidence and its strict observation projection."""
from copy import deepcopy
from .cases import training_ls, training_lg, world_for
from .environment import build
from .rules import sufficient, hypotheses, due, early


def observation(case,event_id,payload,phase='train_business'):
    return dict(case_id=case['id'],world_version=case['world_version'],event_id=event_id,
                feedback_phase=phase,payload=deepcopy(payload))


def training_package(kind):
    result=[];audits=[]
    cases=training_ls() if kind=='LS1' else training_lg()
    for c in cases:
        w=world_for(kind);env=build(c,w)
        if kind=='LS1':
            public=env.call('read_order',{})
            item=c['allowed_returns'][0]
            returned=env.call('accept_return',dict(item_id=item,operation_id='accept'))
            entry=dict(facts=public,accepted=returned)
            # Trusted external event is part of the training scenario from initialization.
            if c['id'] in ('S-D','S-E'):
                c=deepcopy(c);c['warehouse_receipts']=[item]
                env=build(c,w);public=env.call('read_order',{})
                returned=env.call('accept_return',dict(item_id=item,operation_id='accept'))
                entry=dict(facts=public,accepted=returned)
                entry['warehouse_once']=env.call('check_warehouse',dict(item_id=item,operation_id='warehouse1'))
                entry['ledger_once']=env.call('read_ledger',{})
                entry['warehouse_again']=env.call('check_warehouse',dict(item_id=item,operation_id='warehouse2'))
                entry['ledger_again']=env.call('read_ledger',{})
            entry['case_review']={'review_goal':'Process the authorized return and account for its debt/release; no purchase goal in this training subtask', 'S': 'error' not in returned, 'return_processing_completed':True}
        else:
            facts=env.call('read_case',{})
            # Safe offline case review; not an unsafe real submission followed by an exemption.
            entry=dict(facts=facts,reviewed_document_ids=[d['id'] for d in c['documents']],
                case_review={'evidence_sufficient':sufficient(c['documents'],c,w),
                    'public_source_binding_valid':all(d['authentic'] and d['order_id']==c['order_id'] for d in c['documents'])})
        result.append(observation(c,f'{c["id"]}:review',entry,'authorized_sandbox_case_review'))
        audits.append(env.audit())
    return result,audits


def compatible_counts(kind,observations):
    candidates=hypotheses(kind);counts=[len(candidates)]
    for obs in observations:
        p=obs['payload'];f=p['facts']
        if kind=='LS1':
            r=p['accepted'];items=f['items'];chosen=next(i for i in items if i['id']==r['item_id'])
            candidates=[w for w in candidates if due(items,w)==f['original_paid']
                and due([i for i in items if i['id']!=chosen['id']],w)==r['contract_due']
                and (early(chosen,f['return_channel'],w)==(r['stage']=='AVAILABLE'))]
        else:
            # Only visible facts needed to evaluate the hypothetical case review.
            case={**f,'document_version':'revision-1'}
            candidates=[w for w in candidates if sufficient(f['documents'],case,w)==p['case_review']['evidence_sufficient']]
        counts.append(len(candidates))
    return counts,candidates
