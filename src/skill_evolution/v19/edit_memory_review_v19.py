"""One deterministic evidence packet and checkpoint per historical edit.

The full MemoryReviewInput remains an audit archive, never a model prompt here.
No semantic routing, keyword matching, retrieval requests or silent truncation.
"""
from collections import defaultdict
from pathlib import Path
from copy import deepcopy

from .edit_tracking_v19 import encode, parse, digest
from .memory_store_v19 import require
from .review_contract_v19 import MemoryReviewInput, REVIEW_SCHEMA
from .historical_review_v19 import validate_historical_reviews
from .review_context_v19 import paired_events
from .evolution_replay_v19 import _load, _save, _lock

PROTOCOL = 'edit_memory_review_v19.5'
MAX_INPUT_TOKENS = 64000
INPUT_OBSERVATION_TOKENS = 32000


def build_edit_packets(request):
    data = request.payload
    issue_memory = data.get('memory_protocol') in ('issue_memory_v19.1','issue_memory_v19.2')
    groups = defaultdict(list)
    for obj in data['historical_objects']:
        groups[obj['edit_id']].append(obj)
    from ..v18.diagnosis_references_v18 import build_reference_catalogs
    rule_catalog = build_reference_catalogs({'current_skill':data['current_skill'],'contexts':[]})['available_rule_refs']
    packets = []
    for edit_id, objects in sorted(groups.items()):
        row = next(r for r in data['memory_context']['rounds'] if any(e['edit_id'] == edit_id for e in r['edits']))
        edit = next(e for e in row['edits'] if e['edit_id'] == edit_id)
        rules = set()
        for obj in objects:
            binding = obj['current_binding']
            rules.update(binding['current_rule_refs'])
            rules.update(binding['descendant_rule_refs'])
        findings = [f for f in data['current_findings'] if rules & set(f['related_rule_refs'])]
        seeds = {ref for f in findings for ref in f['evidence_refs']}
        by_trajectory = defaultdict(list)
        for ref, item in data['current_evidence'].items():
            by_trajectory[item['trajectory_ref']].append(item['event'])
        selected = set(seeds)
        for events in by_trajectory.values():
            selected.update(paired_events(sorted(events, key=lambda e:e['step']), seeds))
        events = {ref:{k:data['current_evidence'][ref][k] for k in ('trajectory_ref','context_ref','event')} for ref in sorted(selected)}
        trajectories = {}
        for ref in sorted(selected):
            item = data['current_evidence'][ref]
            trajectories[item['trajectory_ref']] = {k:v for k,v in item.items() if k!='event'}
        # Only attribution-cited observations, including both polarities and context.
        attrs = [a for a in row['attribution']['records'] if edit_id in a['edit_ids']]
        historical_seeds = {ref for a in attrs for o in a['observations'] + a.get('unattributed_context', [])
                            for field in ('parent_evidence_refs','candidate_evidence_refs') for ref in o[field]}
        # Resolve references against the archive without copying historical bodies.
        # Attribution observations retain every local comparison and its limitations.
        historical_refs = {}
        outcomes = {}
        cited_pairs = {o['pair_id'] for attr in attrs for o in attr['observations']}
        for pair in row['replay']['pairs']:
            if pair['pair_id'] in cited_pairs:
                outcomes[pair['pair_id']] = {
                    'outcome_transition': pair['outcome_transition'],
                    'supervision': {role: pair[role]['supervision'] for role in ('parent','candidate')}}
            for role in ('parent','candidate'):
                for event in pair[role]['events']:
                    if event['evidence_ref'] in historical_seeds:
                        historical_refs[event['evidence_ref']] = {'pair_id':pair['pair_id'], 'role':role.upper()}
        require(historical_seeds <= set(historical_refs), 'missing attribution evidence')
        require(cited_pairs == set(outcomes), 'missing attribution pair outcomes')
        local_objects = deepcopy(objects)
        for obj in local_objects:
            attr = next(a for a in attrs if a['attribution_id']==obj['attribution_id'])
            allowed = {ref for o in attr['observations'] + attr.get('unattributed_context', []) for field in ('parent_evidence_refs','candidate_evidence_refs') for ref in o[field]}
            # Keep the per-judgment provenance boundary; these IDs do not load event bodies.
            obj['historical_event_refs'] = sorted(allowed)
        contexts = {}
        for ref in sorted({v['context_ref'] for v in events.values()}):
            original = data['current_contexts'][ref]
            names = {v['event'].get('tool_name') for v in events.values() if v['context_ref']==ref}
            contexts[ref] = {**original, 'public_tools':[t for t in original['public_tools']
                                if t.get('function',{}).get('name') in names]}
        supervision_refs = {ref for f in findings for ref in f['supervision_refs']}
        payload = {'schema_version':PROTOCOL, 'source_input_ref':request.input_ref,
            'batch':data['batch'], 'edit_id':edit_id,
            'edit':{k:edit[k] for k in ('edit_id','operation','target_blocks','after_text')},
            'gate_decision':row['memory_record']['gate_decision'],
            'current_rules':{ref:rule_catalog[ref] for ref in sorted(rules)},
            'historical_objects':local_objects, 'attribution':attrs,
            'historical_evidence':{}, 'historical_evidence_refs':historical_refs,
            'historical_pair_outcomes':outcomes,
            'historical_representation':'ATTRIBUTION_SUMMARIES_WITH_ARCHIVE_REFERENCES_NOT_EVENT_BODIES',
            'current_findings':findings, 'current_evidence':events, 'current_trajectories':trajectories,
            'current_supervision':{ref:{k:data['current_supervision'][ref][k] for k in ('trajectory_ref','supervision')} for ref in sorted(supervision_refs)},
            'current_contexts':contexts,
            'association':{'method':'EXACT_CURRENT_OR_DESCENDANT_RULE_REFERENCE',
                'finding_links':{f['finding_id']:sorted(rules & set(f['related_rule_refs'])) for f in findings},
                'limitation':'No matched finding means no evidence in this packet, not absence of relevant behavior in the full round.'}}
        if issue_memory:
            # Association reads validated findings, never a broadcast of raw replay.
            # Rule presence is a useful hint, not an eligibility condition.
            findings = [{k:f[k] for k in ('finding_id','kind','statement','applicability',
                         'evidence_refs','related_rule_refs','uncertainty')} for f in data['current_findings']]
            refs = {ref for f in findings for ref in f['evidence_refs']}
            payload.update({
                'edit_attempt': {k:v for k,v in data['edit_attempts'][edit_id].items()
                                 if k not in ('attempt','results')},
                'current_findings': findings,
                'current_evidence': {ref: {
                    'trajectory_ref': data['current_evidence'][ref]['trajectory_ref'],
                    'context_ref': data['current_evidence'][ref]['context_ref']}
                    for ref in sorted(refs)},
                'current_trajectories': {}, 'current_contexts': {}, 'current_supervision': {},
                'current_representation': 'VALIDATED_FINDING_SUMMARIES_AND_REFERENCE_INDEX_NOT_EVENT_BODIES',
                'association': {
                    'method': 'REVIEW_PROBLEM_AND_ATTEMPT_AGAINST_CURRENT_FINDINGS',
                    'finding_links': payload['association']['finding_links'],
                    'limitation': 'Rule links are hints only. Review selects relevant findings; no match is not resolution.'}})
        from .memory_consumption_v19 import state_view
        # One shared summary boundary for both consumers. The full request stays
        # the source archive; no accumulated raw replay enters this view.
        if 'edit_attempt' in payload:
            attempt=payload['edit_attempt']
            attempt['source_finding_refs']=[f['finding_id'] for f in attempt.pop('source_findings',[])]
        fields=('historical_objects','attribution','historical_evidence_refs',
                'historical_pair_outcomes','edit_attempt')
        history,receipt=state_view({k:payload[k] for k in fields if k in payload})
        payload.update(history)
        payload['memory_consumption']=receipt
        packets.append(MemoryReviewInput(encode(payload)))
    return tuple(packets)


def packet_wire(payload):
    """Extend the existing lossless notation to paired historical references."""
    from .review_context_v19 import compact_projection
    wire = compact_projection(payload)
    prefixes = dict(wire.pop('reference_prefixes'))
    pairs = set()
    def visit(v):
        if isinstance(v,str) and v.startswith('PAIR/'):
            pairs.add(v.split('/')[1])
        elif isinstance(v,list):
            for x in v:visit(x)
        elif isinstance(v,dict):
            for k,x in v.items():visit(k);visit(x)
    visit(wire)
    reverse = {'PAIR/'+pid+'/':f'@PAIR{i}/' for i,pid in enumerate(sorted(pairs))}
    def walk(v):
        if isinstance(v,str):
            for prefix,alias in reverse.items():
                if v.startswith(prefix):return alias+v[len(prefix):]
            return v
        if isinstance(v,list):return [walk(x) for x in v]
        if isinstance(v,dict):return {walk(k):walk(x) for k,x in v.items()}
        return v
    result = {**walk(wire),'reference_prefixes':{**prefixes,**{a:p for p,a in reverse.items()}}}
    ids=set()
    def collect(v):
        if isinstance(v,str) and v.startswith(('CF/','HO/','EDIT/','ATTRIBUTION/')) and len(v.split('/'))==2:
            ids.add(v)
        elif isinstance(v,dict):
            for k,x in v.items():collect(k);collect(x)
        elif isinstance(v,list):
            for x in v:collect(x)
    collect(result)
    aliases={value:'@ID'+str(i)+'/' for i,value in enumerate(sorted(ids))}
    def shorten(v):
        if isinstance(v,str):return aliases.get(v,v)
        if isinstance(v,dict):return {shorten(k):shorten(x) for k,x in v.items()}
        if isinstance(v,list):return [shorten(x) for x in v]
        return v
    result=shorten(result)
    result['reference_prefixes'].update({alias:value for value,alias in aliases.items()})
    return result


def build_packet_request(packet):
    from .review_prompt_v19 import REVIEW_INSTRUCTIONS
    from .memory_consumption_v19 import INSTRUCTIONS as MEMORY_INSTRUCTIONS
    instructions = REVIEW_INSTRUCTIONS + MEMORY_INSTRUCTIONS + '''\nThis is one edit's deterministically selected evidence packet, not the full round.
Use only loaded references. Unmatched findings remain available to Issue Fusion.
No association is not evidence of effectiveness, resolution or irrelevance.
No MORE_CONTEXT requests are supported. Insufficient material means NOT_COVERED.
Historical attribution is a hypothesis; preserve counterevidence and uncertainty.
Historical input is the existing attribution summaries and their provenance, not
raw historical trajectories. historical_evidence is empty by design. Read the
attribution observations for local behavior comparisons/reasons and the
historical_pair_outcomes for program-recorded labels/deltas. Joint edit evidence
remains joint. historical_evidence_refs and each object's historical_event_refs
are archive pointers only, not event bodies you have inspected. You may cite
these supplied IDs in historical_evidence_refs to trace a summarized judgment,
but must not claim to have read their raw content, invent additional historical
facts, or strengthen the attribution. Do not redo historical Attribution.
Assess evidence status from the loaded CURRENT evidence; a historical summary or
outcome alone cannot establish current support or contradiction. No current
association is not a finding that the historical issue disappeared.
'''
    if packet.payload.get('edit_attempt') is not None:
        instructions += """
Evidence status concerns a specific historical behavior observation or applicability
claim, never whether the edit is good or bad. In reason identify the claim supported
or contradicted. Outcome counts describe associated PAIRS, not edit effects. Preserve
unattributed_context as alternative behavioral context without assigning it to this
edit. Zero deltas do not establish no behavioral effect; an unchanged behavior does
not demonstrate a new benefit. Gate is not individual edit quality.
For this protocol CURRENT evidence is supplied as validated finding summaries and
an event reference index, NOT raw event bodies. Assess the historical judgment
against what the findings report; do not claim direct inspection of indexed events.
Compare the historical problem, attempted behavior and applicability to ALL supplied
finding summaries. Parent binding/related_rule_refs are hints, never prerequisites:
an ABSENT edit rejected with its Candidate may still address a current problem.
Select relevant current_finding_refs and their event references. Every current event
citation must belong to a selected finding. Similar words or the same tool alone do
not establish relevance. Insufficient or absent coverage remains NOT_COVERED.
Gate RETAIN is not evidence that an individual edit failed; ACCEPT is not proof that
it helped. Preserve contrary and joint evidence. Final modification feasibility and
raw evidence verification belong to the downstream local Evidence Review.
"""
    from .memory_consumption_v19 import REVIEW_COMPARISON
    instructions += REVIEW_COMPARISON
    from .evidence_projection_v19 import INSTRUCTIONS
    import tiktoken
    system = instructions + INSTRUCTIONS + '\nreference_prefixes are lossless aliases. Full or compact reference IDs are accepted in output reference fields.\n'
    from .memory_review_repair_v19 import compact_text, TEXT_INSTRUCTIONS
    system += TEXT_INSTRUCTIONS
    user = encode(compact_text(packet_wire(packet.payload)))
    schema = {'type':'json_schema','json_schema':{'name':'edit_memory_review','strict':True,'schema':deepcopy(REVIEW_SCHEMA)}}
    text = encode({'messages':[{'role':'system','content':system},{'role':'user','content':user}], 'response_format':schema})
    tokens = len(tiktoken.get_encoding('cl100k_base').encode(text,disallowed_special=()))
    return {'prompt_version':PROTOCOL+'-claim-comparison-1','system_prompt':system,'user_prompt':user,'response_format':schema,
        'prompt_sha256':digest(system),'input_sha256':digest(user),'max_completion_tokens':24000,
        'input_budget':{'method':'cl100k_base_PROXY_NOT_GATEWAY_TOKENIZER','proxy_input_tokens':tokens,
                        'max_input_tokens':MAX_INPUT_TOKENS,
                        'observation_threshold':INPUT_OBSERVATION_TOKENS,
                        'above_observation_threshold':tokens>INPUT_OBSERVATION_TOKENS}}



def validate_packet(raw, packet):
    from .review_context_v19 import expand_reference
    prefixes = packet_wire(packet.payload)['reference_prefixes']
    from .review_contract_v19 import checked_response
    response = checked_response(raw, REVIEW_SCHEMA)
    for item in response.get('reviews', []):
        if not isinstance(item, dict):continue
        if isinstance(item.get('historical_object_id'),str):
            item['historical_object_id']=expand_reference(item['historical_object_id'],prefixes)
        for field in ('supporting_current_refs','contradicting_current_refs','context_current_refs','current_finding_refs','historical_evidence_refs'):
            if isinstance(item.get(field), list):
                item[field] = [expand_reference(ref,prefixes) if isinstance(ref,str) else ref for ref in item[field]]
    if packet.payload.get('edit_attempt') is not None:
        findings = {f['finding_id']: f for f in packet.payload['current_findings']}
        for review in response['reviews']:
            require(set(review['current_finding_refs']) <= set(findings), 'unknown finding')
            allowed = {ref for fid in review['current_finding_refs'] for ref in findings[fid]['evidence_refs']}
            cited = {ref for field in ('supporting_current_refs','contradicting_current_refs','context_current_refs')
                     for ref in review[field]}
            require(cited <= allowed, 'current evidence must belong to selected findings')
    return validate_historical_reviews(encode(response), request=packet)


def packet_profile(request, packets=None):
    packets = build_edit_packets(request) if packets is None else packets
    rows = []
    for packet in packets:
        prompt = build_packet_request(packet)
        tokens = prompt['input_budget']['proxy_input_tokens']
        p = packet.payload
        rows.append({'edit_id':p['edit_id'], 'finding_refs':[f['finding_id'] for f in p['current_findings']],
            'historical_objects':len(p['historical_objects']),
            'current_events':sum('event' in e for e in p['current_evidence'].values()),
            'current_reference_count':len(p['current_evidence']),
            'association_method':p['association']['method'],
            'historical_events':len(p['historical_evidence']),
            'historical_reference_count':len(p['historical_evidence_refs']),
            'historical_pair_count':len(p['historical_pair_outcomes']),
            'historical_observation_count':sum(len(a['observations']) for a in p['attribution']),
            'input_tokens':tokens,
            'within_budget':tokens<=MAX_INPUT_TOKENS,
            'above_observation_threshold':tokens>INPUT_OBSERVATION_TOKENS})
    available = {ref for row in rows for ref in row['finding_refs']}
    linked = {fid for packet in packets for fid, refs in packet.payload['association']['finding_links'].items() if refs}
    return {'schema_version':PROTOCOL, 'max_input_tokens':MAX_INPUT_TOKENS, 'edits':rows,
        'edit_count':len(rows), 'edits_with_current_findings':sum(bool(r['finding_refs']) for r in rows),
        'finding_count':len(request.payload['current_findings']), 'linked_finding_count':len(linked),
        'available_finding_count':len(available),
        'association_note':'linked counts rule hints only; semantic association requires completed Review',
        'unmatched_finding_refs':sorted(f['finding_id'] for f in request.payload['current_findings'] if f['finding_id'] not in linked),
        'all_current_findings_retained_for_fusion':True}


def run_edit_reviews(request, *, artifact_dir, transport=None):
    from .separated_generation_v19 import _contract_call, _checkpoint
    from .evidence_review_prompt_v19 import check_review_budget
    from .attribution_v19 import _transport
    root = Path(artifact_dir)
    if (root/'repair-migration.json').exists():
        from .review_repair_migration_v19 import run_migrated_reviews
        return run_migrated_reviews(request,root,transport)
    packets = build_edit_packets(request)
    with _lock(root):
        root.mkdir(parents=True,exist_ok=True)
        _checkpoint(root/'binding.json', {'protocol':PROTOCOL,'source_input_ref':request.input_ref,
            'packet_digests':[digest(p.payload_json) for p in packets], 'max_input_tokens':MAX_INPUT_TOKENS})
        _checkpoint(root/'profile.json', packet_profile(request, packets))
        completed, failures = [], {}
        for packet in packets:
            p = packet.payload
            directory = root/digest(p['edit_id'])
            directory.mkdir(exist_ok=True)
            _checkpoint(directory/'input.json', p)
            try:
                prompt = build_packet_request(packet)
                def bounded(prepared):
                    check_review_budget(prepared, MAX_INPUT_TOKENS)
                    return (transport or _transport)(prepared)
                # Both the initial request and the one permitted repair use the same cap.
                check_review_budget(prompt, MAX_INPUT_TOKENS)
                from .memory_review_repair_v19 import build_repair
                result = _contract_call(directory/'review', prompt,
                    lambda raw:validate_packet(raw,packet), bounded, repair_builder=build_repair)
                _checkpoint(directory/'result.json', result.payload)
                _save(directory/'status.json', {'status':'COMPLETE'})
                completed.extend(parse(result.payload['raw_response'])['reviews'])
            except Exception as exc:
                failures[p['edit_id']] = {'error_type':type(exc).__name__,'error':str(exc)}
                _save(directory/'status.json', {'status':'INCOMPLETE',**failures[p['edit_id']]})
        _save(root/'status.json', {'status':'INCOMPLETE' if failures else 'AGGREGATING',
            'completed_edits':len(packets)-len(failures),'total_edits':len(packets),'failures':failures})
        require(not failures, 'edit Memory Review incomplete; completed edits preserved; inspect per-edit status')
        merged = validate_historical_reviews(encode({'schema_version':'historical_review_response_v19.1',
            'reviews':completed}),request=request)
        _checkpoint(root/'historical-reviews.json', merged.payload)
        _save(root/'status.json', {'status':'COMPLETE','completed_edits':len(packets),
            'total_edits':len(packets),'failures':{}})
        return merged
