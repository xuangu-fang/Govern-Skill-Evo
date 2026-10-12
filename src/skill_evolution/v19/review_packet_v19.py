"""One deterministic local packet; no model-directed retrieval or budget pruning."""
import re
from copy import deepcopy
from .edit_tracking_v19 import encode


def policy_paragraph_refs(policies,seeds):
    """Expand cited nonblank lines to their contiguous Markdown paragraph.

    Catalog line-number gaps preserve blank-line boundaries. A heading starts a
    new block. No semantic search or policy-specific keywords are used.
    """
    groups={}
    for ref,line in policies.items():
        groups.setdefault((line['context_ref'],line['policy_digest']),[]).append((ref,line))
    selected=set(seeds)
    for lines in groups.values():
        blocks=[];block=[];previous=None
        for ref,line in sorted(lines,key=lambda item:item[1]['line']):
            heading=bool(re.match(r'^\s*#{1,6}\s',line['text']))
            if block and (line['line']!=previous+1 or heading):blocks.append(block);block=[]
            block.append(ref);previous=line['line']
        if block:blocks.append(block)
        for block in blocks:
            if set(block)&seeds:selected.update(block)
    return selected


def scoped_case(case):
    """Keep historical observations as context, not automatic raw-event seeds.

    The canonical case remains the full archive. Direct finding/review citations
    and every known counterexample are mandatory; selection never depends on size.
    """
    from .evidence_review_v19 import EvidenceReviewCase
    p=deepcopy(case.payload)
    seeds={ref for f in p['findings'] for ref in f['evidence_refs']}
    for review in p['historical_reviews']:
        for field in ('supporting_current_refs','contradicting_current_refs',
                      'context_current_refs'):
            seeds.update(review[field])
    from .memory_consumption_v19 import select_originals, state_view
    current_refs={e['evidence_ref'] for exp in p['experiences'] if exp.get('origin')=='CURRENT_PARENT'
                  for e in exp['events']}
    counter=set(p['known_counterevidence_refs'])
    historical={ref for r in p['historical_reviews'] for ref in r['historical_evidence_refs']}
    selected,receipt=select_originals(p['experiences'],historical,counter-current_refs)
    seeds.update(counter & current_refs)
    seeds.update(selected)
    p['known_counterevidence_refs']=sorted(counter & seeds)
    p['memory_consumption']=receipt
    p['seed_refs']=sorted(seeds)
    p['experiences']=[exp for exp in p['experiences']
        if seeds & {e['evidence_ref'] for e in exp['events']}]
    # Review conclusions already appear in historical_reviews. Old discovery
    # findings are provenance, not a second full Diagnosis input.
    from .memory_consumption_v19 import historical_object_view
    p['historical_objects']=[historical_object_view(obj) for obj in p['historical_objects']]
    history,summary=state_view({k:p[k] for k in ('historical_objects','historical_reviews','historical_observations')})
    p.update(history)
    p['memory_consumption'].update(summary)
    return EvidenceReviewCase(encode(p))


def build_once_input(case, *, legacy=False):
    from .evidence_review_v19 import build_evidence_review_input, EvidenceReviewInput
    archive=case
    if not legacy:case=scoped_case(case)
    p=case.payload
    seeds={r for f in p['findings'] for r in f['policy_refs']}
    policies=policy_paragraph_refs(p['policies'],seeds)
    text_by_context={}
    for ref in policies:
        line=p['policies'][ref]
        text_by_context.setdefault(line['context_ref'],[]).append(line['text'])
    mentioned=set();tools=[]
    for ref,tool in p['tools'].items():
        name=tool['definition'].get('function',{}).get('name','')
        if name and re.search(r'(?<![\w])'+re.escape(name)+r'(?![\w])',
                              '\n'.join(text_by_context.get(tool['context_ref'],[]))):
            mentioned.add((tool['context_ref'],name));tools.append(ref)
    events=sorted({e['evidence_ref'] for exp in p['experiences'] for e in exp['events']
        if (legacy or exp.get('origin')=='CURRENT_PARENT') and (exp['context_ref'],e.get('tool_name')) in mentioned})
    # Reuse the pure historical packet resolver; the selection above is entirely
    # program-owned, and this intermediate object is never sent to a model.
    packet=build_evidence_review_input(case,input_version='v19.2',context_round=1,
        additional_evidence_refs=events,additional_tool_refs=tools,additional_policy_refs=sorted(policies)).payload
    for field in ('event_directory','policy_directory','tool_directory','rule_directory','context_requests_remaining'):
        packet.pop(field)
    packet['schema_version']='evidence_review_input_v19.3'
    if legacy:
        packet['input_scope']={'selection':'DIRECT_EVIDENCE_PAIRED_CALL_RESULTS_CITED_POLICY_PARAGRAPHS_AND_REFERENCED_TOOLS',
            'archived_events':sum(len(e['events']) for e in p['experiences']), 'loaded_events':len(packet['events']),
            'archived_policy_lines':len(p['policies']),'loaded_policy_lines':len(packet['policies'])}
    else:
        packet['packet_version']='evidence_packet_v19.5'
        packet['memory_consumption']=p['memory_consumption']
        packet['case_ref']=archive.case_ref
        packet['input_scope']={'selection':'DIRECT_EVIDENCE_PAIRED_CALL_RESULTS_CITED_POLICY_PARAGRAPHS_AND_REFERENCED_TOOLS',
            'history_selection':'REVIEW_CITATIONS_AND_KNOWN_COUNTEREVIDENCE_NOT_ALL_ATTRIBUTION_EVENTS',
            'required_event_count':len(p['seed_refs']),
            'archived_events':sum(len(e['events']) for e in archive.payload['experiences']), 'loaded_events':len(packet['events']),
            'archived_policy_lines':len(p['policies']),'loaded_policy_lines':len(packet['policies'])}
    return EvidenceReviewInput(encode(packet))
