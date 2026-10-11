"""Historical claims reviewed against all current findings and raw evidence.

No routing to current groups, mutation decisions, model transport or memory writes.
"""
from .edit_tracking_v19 import encode, digest
from .attribution_semantics_v19 import judgment
from .memory_store_v19 import load_memory, require
from .memory_retrieval_v19 import retrieve_memory
from .current_diagnosis_v19 import validate_current_batch
from .review_contract_v19 import MemoryReviewInput, HistoricalReviews, REVIEW_SCHEMA, checked_response


def build_memory_review_input(*, store_dir, current_requests, current_findings):
    batch = validate_current_batch(current_requests, current_findings)
    snapshot = load_memory(store_dir)
    parent = current_requests[0].payload['current_skill']
    require(snapshot.head['run_id'] == batch['run_id'] and snapshot.head['retained_skill'] == parent,
            'Memory/current run or Parent mismatch')
    require(batch['round_id'] not in {r['record']['round_id'] for r in snapshot.rounds},
            'current round already committed')
    require(snapshot.head['replay_manifest_sha256'] in (None, batch['evolution_manifest_sha256']),
            'Memory/current Evolution manifest mismatch')
    memory = retrieve_memory(store_dir=store_dir, current_parent=parent).payload
    require(memory['committed_memory_ref'] == snapshot.head['memory_ref'], 'Memory head changed')
    return assemble_memory_review_input(memory=memory,current_requests=current_requests,current_findings=current_findings, memory_protocol="issue_memory_v19.2")


def assemble_memory_review_input(*, memory, current_requests, current_findings, memory_protocol=None):
    """Pure assembly for offline audit restoration; caller verifies committed Memory."""
    require(memory_protocol in (None, "issue_memory_v19.1", "issue_memory_v19.2"), "unknown Memory protocol")
    batch=validate_current_batch(current_requests,current_findings)
    parent=current_requests[0].payload['current_skill']
    require(memory['current_parent']==parent and memory['run_id']==batch['run_id'], 'review Memory binding mismatch')
    events, supervision, contexts, findings = {}, {}, {}, []
    for request in current_requests:
        for context in request.payload['contexts']:
            ref = context['context_ref']
            require(ref not in contexts or contexts[ref] == context, 'current context collision')
            contexts[ref] = context
        for exp in request.payload['experiences']:
            identity = {k: exp[k] for k in ('task_ref','trajectory_ref','rollout_index','context_ref',
                                           'origin','source_round_id','skill_ref','role')}
            for event in exp['events']:
                ref = event['evidence_ref']
                require(ref not in events, 'duplicate current event')
                events[ref] = {**identity, 'event': event}
            label = exp['supervision']
            supervision[label['supervision_ref']] = {**identity, 'supervision': label}
    for result in current_findings:
        findings.extend(result.payload['findings'])
    if memory_protocol == "issue_memory_v19.2":
        from copy import deepcopy
        from .attribution_semantics_v19 import record_facts
        memory = deepcopy(memory)
        for row in memory['rounds']:
            batch_attribution = row['attribution']
            batch_attribution['records'] = [record_facts(r, batch_attribution) for r in batch_attribution['records']]
    objects, historical_events = [], {}
    for row in memory['rounds']:
        for pair in row['replay']['pairs']:
            for role in ('parent', 'candidate'):
                for event in pair[role]['events']:
                    historical_events[event['evidence_ref']] = {'pair_id': pair['pair_id'], 'role': role.upper()}
        for edit, binding in zip(row['edits'], row['current_bindings']):
            records = [r for r in row['attribution']['records'] if edit['edit_id'] in r['edit_ids']]
            require(bool(records), 'historical edit has no attribution review object')
            for record in records:
                identity = {'edit_id': edit['edit_id'], 'attribution_id': record['attribution_id']}
                # Attribution is a historical hypothesis, not a new factual claim.
                pair_ids = {o['pair_id'] for o in record['observations']}
                objects.append({'historical_object_id': 'HO/' + digest(encode(identity)), **identity,
                    'historical_judgment': ({k: record[k] for k in
                        ('effect','interpretation','applicability','uncertainty','alternative_explanations')}
                        if 'effect' in record else judgment(record)),
                    'current_binding': binding, 'joint_edit_ids': record['edit_ids'],
                    'historical_event_refs': sorted({e['evidence_ref'] for p in row['replay']['pairs']
                        if not pair_ids or p['pair_id'] in pair_ids
                        for role in ('parent','candidate') for e in p[role]['events']})})
    from .memory_experience_v19 import project_attempts
    extension = {} if memory_protocol is None else {
        'memory_protocol': memory_protocol, 'edit_attempts': project_attempts(memory)}
    return MemoryReviewInput(encode({**extension, 'schema_version': 'memory_review_input_v19.1', 'batch': batch,
        'current_skill': parent, 'memory_context': memory, 'historical_objects': objects,
        'current_findings': findings,
        'current_findings_refs': sorted(digest(f.payload_json) for f in current_findings),
        'current_evidence': events, 'current_supervision': supervision, 'current_contexts': contexts,
        'historical_event_catalog': historical_events,
        'authority': 'HISTORICAL_HYPOTHESES_NOT_POLICY_OR_EDIT_AUTHORIZATION'}))


def resolve_current_evidence(request, refs):
    """Read-only exact events with their current context and trajectory identity."""
    payload = request.payload
    require(len(refs) == len(set(refs)) and set(refs) <= set(payload['current_evidence']),
            'unknown or duplicate current event references')
    return [{'ref': ref, **payload['current_evidence'][ref],
             'context': payload['current_contexts'][payload['current_evidence'][ref]['context_ref']]}
            for ref in refs]


def validate_historical_reviews(raw, *, request):
    require(isinstance(request, MemoryReviewInput), 'MemoryReviewInput required')
    output = checked_response(raw, REVIEW_SCHEMA)
    payload = request.payload
    objects = {o['historical_object_id']: o for o in payload['historical_objects']}
    findings = {f['finding_id']: f for f in payload['current_findings']}
    seen, reviews = set(), []
    for index, review in enumerate(output['reviews']):
        oid = review['historical_object_id']
        require(oid in objects and oid not in seen, f'review {index}: unknown or duplicate historical object')
        seen.add(oid)
        supporting = set(review['supporting_current_refs'])
        contradicting = set(review['contradicting_current_refs'])
        context = set(review['context_current_refs'])
        refs = supporting | contradicting | context
        require(refs <= set(payload['current_evidence']), f'review {index}: non-current or unknown event refs')
        require(set(review['historical_evidence_refs']) <= set(objects[oid]['historical_event_refs']),
                f'review {index}: historical evidence outside reviewed judgment')
        require(set(review['current_finding_refs']) <= set(findings), f'review {index}: unknown finding')
        missing = [f for f in review['current_finding_refs'] if not refs & set(findings[f]['evidence_refs'])]
        require(not missing, f'review {index}: finding link without shared current evidence: ' + encode({
            'historical_object_id':oid, 'unlinked_findings':{f:findings[f]['evidence_refs'] for f in missing},
            'cited_current_refs':sorted(refs)}))
        status = review['evidence_status']
        expected = 'MIXED' if supporting and contradicting else 'SUPPORTED' if supporting else \
                   'CONTRADICTED' if contradicting else 'NOT_COVERED'
        require(status == expected, f'review {index}: status/evidence polarity mismatch')
        if status == 'NOT_COVERED':
            require(review['coverage_reason'] in ('NO_RELEVANT_OBSERVATION', 'INSUFFICIENT_EVIDENCE'),
                    f'review {index}: uncovered reason required')
            require((review['coverage_reason'] == 'INSUFFICIENT_EVIDENCE') == bool(context),
                    f'review {index}: insufficient evidence needs observed context; absent coverage has none')
        else:
            require(review['coverage_reason'] == 'ASSESSED', f'review {index}: assessed coverage required')
        reviews.append({'review_id': 'HR/' + digest(encode({'input_ref': request.input_ref, 'review': review})),
                        **review})
    require(seen == set(objects), 'historical review coverage incomplete: ' + encode(sorted(set(objects)-seen)))
    return HistoricalReviews(encode({'schema_version': 'historical_reviews_v19.1',
        'input_ref': request.input_ref, 'raw_response': raw, 'reviews': reviews,
        'validation_scope': 'STRUCTURE_REFERENCES_AND_BINDINGS_NOT_SEMANTIC_TRUTH'}))
