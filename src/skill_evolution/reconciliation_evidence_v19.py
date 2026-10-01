"""Reference-selected Reconciliation view; full evidence stays in the audit input.

No ranking, summarization, truncation or outcome-based evidence selection. The
wire view is reproducible from the bound upstream artifacts and explicit extra
refs. Local validators use the same visibility set as the model.
"""
from .edit_tracking_v19 import encode, digest
from .memory_store_v19 import require

REVIEW_FIELDS = ('supporting_current_refs','contradicting_current_refs',
                 'context_current_refs','historical_evidence_refs')


def selected_evidence_refs(request):
    data=request.payload; review=data['review_input']
    selected={ref for finding in review['current_findings'] for ref in finding['evidence_refs']}
    selected.update(ref for item in data['historical_reviews']['reviews']
                    for field in REVIEW_FIELDS for ref in item[field])
    # Original attribution evidence remains available even when a review reports
    # NOT_COVERED. Preserve both Parent and Candidate observations, not whole pairs.
    object_ids={o['attribution_id'] for o in review['historical_objects']}
    for row in review['memory_context']['rounds']:
        for record in row['attribution']['records']:
            if record['attribution_id'] in object_ids:
                selected.update(ref for obs in record['observations']
                                for field in ('parent_evidence_refs','candidate_evidence_refs') for ref in obs[field])
    selected.update(data.get('additional_evidence_refs',[]))
    return selected


def evidence_view(request, *, catalog=None):
    from .reconciliation_v19 import _catalog
    catalog=_catalog(request) if catalog is None else catalog
    payload=request.payload; data=payload['review_input']; selected=selected_evidence_refs(request)
    require(selected<=set(catalog['available_evidence_refs']),
            'selected evidence contains unknown refs: '+encode(sorted(selected-set(catalog['available_evidence_refs']))))
    if payload['schema_version']=='reconciliation_input_v19.4':
        # Domain-independent context closure: all events of a referenced source
        # trajectory, including earlier tool results and subsequent counterexamples.
        selected=set(selected)
        for exp in catalog['experiences']:
            if selected & {e['evidence_ref'] for e in exp['events']}:
                selected.update(e['evidence_ref'] for e in exp['events'])
    records={r['attribution_id']:r for row in data['memory_context']['rounds'] for r in row['attribution']['records']}
    labels={ref for finding in data['current_findings'] for ref in finding['supervision_refs']}
    labels.update(ref for obj in data['historical_objects']
                  for obs in records[obj['attribution_id']]['observations'] for ref in obs['supervision_refs'])
    events={}; trajectories={}; contexts=set()
    for exp in catalog['experiences']:
        observed=[e for e in exp['events'] if e['evidence_ref'] in selected]
        if not observed and exp['supervision']['supervision_ref'] not in labels:continue
        tid=f'TRAJECTORY/{len(trajectories):04d}'
        trajectories[tid]={k:v for k,v in exp.items() if k not in ('events','supervision')}
        trajectories[tid]['supervision']=exp['supervision']
        trajectories[tid]['available_event_count']=len(exp['events'])
        trajectories[tid]['loaded_event_count']=len(observed)
        contexts.add(exp['context_ref'])
        for event in observed:
            events[event['evidence_ref']]={'trajectory_id':tid,
                'event':{k:v for k,v in event.items() if k!='evidence_ref'}}
    # Policy lines appear exactly once. Catalog keys retain original full typed
    # refs; context identity is explicit rather than inferred from short aliases.
    policies={r:{'context_ref':v['context_ref'],'text':v['text']}
              for r,v in catalog['available_policy_refs'].items() if v['context_ref'] in contexts}
    visible_contexts={c['context_ref']:{k:v for k,v in c.items() if k not in ('visible_policy','context_ref')}
                      for c in catalog['contexts'] if c['context_ref'] in contexts}
    edits={e['edit_id']:e for row in data['memory_context']['rounds'] for e in row['edits']}
    objects=[]
    for obj in data['historical_objects']:
        # Large per-object whole-pair reference catalogs are local audit data,
        # not a second representation of evidence sent to the model.
        item={k:v for k,v in obj.items() if k!='historical_event_refs'}
        item['loaded_historical_event_refs']=sorted(selected & set(obj['historical_event_refs']))
        item['observations']=records[obj['attribution_id']]['observations']
        item['edit']=edits[obj['edit_id']]
        objects.append(item)
    tools={}
    if payload['schema_version']=='reconciliation_input_v19.4':
        for ref,context in visible_contexts.items():
            for index,tool in enumerate(context.get('public_tools',[])):
                tools[f'TOOL/{ref}/{index}/{digest(encode(tool))}']={'context_ref':ref,'definition':tool}
            context.pop('public_tools',None)
    return {**({'available_tool_refs':tools} if payload['schema_version']=='reconciliation_input_v19.4' else {}), 'schema_version':'reconciliation_evidence_view_v19.1',
        'reconciliation_input_ref':request.input_ref,
        'coverage':payload['coverage'], 'evidence_counting':payload['evidence_counting'],
        'review_input':{'batch':data['batch'],'current_skill':data['current_skill'],
            'current_findings':data['current_findings'],'historical_objects':objects},
        'historical_reviews':{'input_ref':payload['historical_reviews']['input_ref'],
                              'reviews':payload['historical_reviews']['reviews']},
        'events':events,'trajectories':trajectories,'contexts':visible_contexts,
        'available_policy_refs':policies,'available_rule_refs':catalog['available_rule_refs'],
        'evidence_selection':{
            'policy':'COMPLETE_REFERENCED_TRAJECTORIES' if payload['schema_version']=='reconciliation_input_v19.4' else 'ALL_FINDING_REVIEW_AND_ATTRIBUTION_EVENT_REFS_PLUS_EXPLICIT_CONTEXT',
            'additional_evidence_refs':payload.get('additional_evidence_refs',[]),
            'loaded_event_count':len(events),'archived_event_count':len(catalog['available_evidence_refs']),
            'full_evidence_sha256':digest(encode(data)),
            'not_loaded_means':'NOT_INSPECTED_NOT_ABSENT',
            'insufficient_context_action':'DEFER_WITH_REQUIRED_EVENT_OR_TRAJECTORY_REFERENCES',
        }}
