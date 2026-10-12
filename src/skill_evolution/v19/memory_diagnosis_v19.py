"""Memory-aware Diagnosis inputs and reauthorization, using v18 pure contracts.

Historical observations retain original pair/role/Skill identities. Hypotheses,
Gate decisions and binding hints never enter the citable observation catalog.
"""
from dataclasses import replace

from .edit_tracking_v19 import digest, encode, parse, skill_ref
from .memory_store_v19 import load_memory, require
from .memory_retrieval_v19 import retrieve_memory
from .memory_allocation_v19 import allocate_memory, validate_allocation
from .evolution_replay_v19 import load_parent_experiences
from ..v17.group_diagnosis_input_v17 import GroupDiagnosisInput, build_group_diagnosis_inputs
from ..v18.diagnosis_references_v18 import build_reference_catalogs
from ..v18.diagnosis_validation_v18 import validate_diagnosis_response, DiagnosisRejected
from ..v18.compiler_contract_v18 import CompilerDiagnosisSource
from ..v15.information_boundary_v15 import _seal


def build_memory_diagnosis_inputs(*, store_dir, backend, parent_dir, round_id,
                                  grouping_result, query='', edit_ids=(), max_rounds=None,
                                  max_memory_chars=None, max_input_chars=None):
    """Join a validated current grouping with committed Memory before any NOOP.

    The caller supplies the existing Grouper result. Every current group,
    including success-only groups, is retained; historical edits have unique owners.
    No new grouping algorithm or hidden failure-only selection is introduced.
    """
    require(type(round_id) is str and bool(round_id.strip()), 'round ID required')
    snapshot = load_memory(store_dir)
    require(round_id not in {r['record']['round_id'] for r in snapshot.rounds}, 'round already committed')
    head = snapshot.head
    if head['replay_manifest_sha256'] is not None:
        require(digest(encode(backend.manifest())) == head['replay_manifest_sha256'],
                'Evolution manifest differs from committed Memory')
    parent = head['retained_skill']
    sources, scope = load_parent_experiences(run_id=head['run_id'], round_id=round_id,
        parent_skill=parent, backend=backend, artifact_dir=parent_dir)
    requests = build_group_diagnosis_inputs(sources, scope=scope,
                                            grouping_result=grouping_result, parent_skill=parent)
    memory = retrieve_memory(store_dir=store_dir, current_parent=parent, query=query, edit_ids=edit_ids,
                             max_rounds=max_rounds, max_chars=max_memory_chars).payload
    require(memory['committed_memory_ref'] == head['memory_ref'], 'memory head changed while building Diagnosis')
    if max_input_chars is not None:
        require(type(max_input_chars) is int and max_input_chars > 0, 'positive input budget required')
    result = []
    for request, allocated_memory in allocate_memory(memory, requests):
        payload = request.learner_payload
        # Round-scoped current refs avoid collisions with earlier rounds/roles.
        namespace = 'CURRENT/' + digest(encode({'run_id': head['run_id'], 'round_id': round_id})) + '/'
        refs = {}
        for experience in payload['experiences']:
            experience.update(origin='CURRENT_PARENT', source_round_id=round_id,
                              skill_ref=skill_ref(parent), role='PARENT')
            for event in experience['events']:
                old = event['evidence_ref']; event['evidence_ref'] = namespace + old; refs[old] = event['evidence_ref']
            old = experience['supervision']['supervision_ref']
            experience['supervision']['supervision_ref'] = namespace + old; refs[old] = namespace + old
        for key in ('available_evidence_refs', 'available_supervision_refs'):
            payload[key] = {refs[ref]: {**value, 'origin': 'CURRENT_PARENT', 'source_round_id': round_id,
                                       'skill_ref': skill_ref(parent), 'role': 'PARENT'}
                            for ref, value in payload[key].items()}
        contexts = {c['context_ref']: c for c in payload['contexts']}
        for row in allocated_memory['rounds']:
            source_round = row['memory_record']['round_id']
            for context in row['replay']['contexts']:
                name = context['context_ref']
                require(name not in contexts or contexts[name] == context, 'context identity collision')
                contexts[name] = context
            for pair in row['replay']['pairs']:
                for role in ('parent', 'candidate'):
                    observation = pair[role]
                    identity = {'task_ref': pair['task_ref'], 'trajectory_ref': observation['trajectory_ref'],
                                'rollout_index': pair['rollout_index']}
                    origin = {'origin': 'COMMITTED_HISTORICAL_OBSERVATION', 'source_round_id': source_round,
                              'pair_id': pair['pair_id'], 'role': observation['role'],
                              'skill_ref': observation['skill_ref']}
                    payload['experiences'].append({**identity, **origin, 'context_ref': observation['context_ref'],
                        'events': observation['events'], 'supervision': observation['supervision']})
                    for event in observation['events']:
                        ref = event['evidence_ref']
                        require(ref not in payload['available_evidence_refs'], 'duplicate observation reference')
                        payload['available_evidence_refs'][ref] = {**identity, **origin, 'step': event['step']}
                    ref = observation['supervision']['supervision_ref']
                    require(ref not in payload['available_supervision_refs'], 'duplicate label reference')
                    payload['available_supervision_refs'][ref] = {**identity, **origin, 'level': 0}
        payload['contexts'] = list(contexts.values())
        payload['memory_context'] = allocated_memory
        payload['consumer_version'] = 'memory_diagnosis_v19.1'
        payload.update(build_reference_catalogs(payload))
        require(max_input_chars is None or len(encode(payload)) <= max_input_chars,
                'combined Diagnosis input exceeds budget; no truncation permitted')
        provenance = {**request.provenance, 'run_id': head['run_id'],
                      'memory_head_ref': head['memory_ref'], 'memory_context_sha256': digest(encode(allocated_memory)),
                      'memory_consumer_version': 'memory_diagnosis_v19.1'}
        result.append(GroupDiagnosisInput(_seal('V17_GROUP_DIAGNOSIS_INPUT', payload), encode(provenance)))
    validate_allocation(result)
    return tuple(result)


def _memory_catalog(request):
    payload = request.learner_payload
    require(payload.get('consumer_version') == 'memory_diagnosis_v19.1', 'v19 memory Diagnosis input required')
    memory = payload['memory_context']
    require(memory['current_parent'] == payload['current_skill']
            and memory['committed_memory_ref'] == request.provenance['memory_head_ref']
            and digest(encode(memory)) == request.provenance['memory_context_sha256'], 'memory input binding mismatch')
    return {e['edit_id']: (e, binding, row)
            for row in memory['rounds'] for e, binding in zip(row['edits'], row['current_bindings'])}


def gap_closure_issues(diagnosis, event_refs):
    """Structured closure diagnostics after schema/reference validation."""
    issues = []
    dimensions = {'SUCCESS':'success_analysis', 'COMPLIANCE':'compliance_analysis'}
    for index, gap in enumerate(diagnosis['parent_skill_gaps']):
        analyses = [dimensions[d] for d in gap['source_dimensions']]
        refs = set(gap['evidence_refs'])
        union = set().union(*(set(diagnosis[a]['evidence_refs']) for a in analyses))
        events = refs & set(event_refs)
        missing = sorted(refs - union)
        unshared = [a for a in analyses if not events.intersection(
            diagnosis[a]['evidence_refs'])]
        if missing or unshared:
            issues.append({'gap_index':index,'source_dimensions':gap['source_dimensions'],
                'missing_from_declared_analyses':missing,'analyses_without_shared_event':unshared})
    return issues


def validate_memory_diagnosis_response(raw, *, request):
    """Validate explicit review coverage and current-Parent reauthorization.

    Reuses the existing semantic Diagnosis validator; relevance/causality remain
    model hypotheses. Historical non-successes remain historical, not current flags.
    """
    output = parse(raw)
    require(type(output) is dict and set(output) == {'schema_version', 'diagnosis', 'memory_review'}
            and output['schema_version'] == 'memory_diagnosis_response_v19.1', 'invalid v19 Diagnosis response')
    catalog = _memory_catalog(request)
    try:
        validated = validate_diagnosis_response(encode(output['diagnosis']), request=request)
    except DiagnosisRejected as exc:
        if exc.stage == 'LINKAGE':
            issues = gap_closure_issues(output['diagnosis'], request.learner_payload['available_evidence_refs'])
            if issues:
                raise DiagnosisRejected('LINKAGE', 'gap evidence closure violations: ' + encode(issues)) from exc
        raise
    reviews = output['memory_review']
    require(type(reviews) is list, 'memory_review list required')
    seen = set()
    gaps = output['diagnosis']['parent_skill_gaps']
    for review_index, review in enumerate(reviews):
        require(type(review) is dict and set(review) == {
            'edit_id', 'decision', 'relation', 'gap_indices', 'evidence_refs', 'reason'}, 'invalid memory review fields')
        edit_id = review['edit_id']
        require(type(edit_id) is str and edit_id in catalog and edit_id not in seen, 'unknown or duplicate reviewed edit')
        seen.add(edit_id)
        require(type(review['reason']) is str and bool(review['reason'].strip()), 'review reason required')
        indices, refs = review['gap_indices'], review['evidence_refs']
        require(type(indices) is list and all(type(i) is int and 0 <= i < len(gaps) for i in indices)
                and len(indices) == len(set(indices)), 'invalid review gap indices')
        location = f'memory_review[{review_index}] edit_id={edit_id}'
        require(type(refs) is list and all(type(r) is str for r in refs),
                f'{location}: evidence_refs must be a list of event-reference strings')
        require(len(refs) == len(set(refs)), f'{location}: duplicate review event refs')
        invalid = [ref for ref in refs if ref not in request.learner_payload['available_evidence_refs']]
        require(not invalid, f'{location}: invalid review event refs {encode(invalid)}; '
                'only experiences[*].events[*].evidence_ref is allowed; '
                'policy support belongs in Diagnosis analysis/gap evidence_refs')
        require(review['decision'] in ('USE', 'DEFER'), 'invalid memory decision')
        if review['decision'] == 'DEFER':
            require(review['relation'] == 'NONE' and not indices, 'deferred memory cannot authorize a gap')
            continue
        require(review['relation'] in ('REVISES', 'RETRIES', 'REVERTS') and bool(indices), 'used memory needs linked gaps')
        edit, binding, row = catalog[edit_id]
        relevant_pairs = row['replay']['pairs']
        require(any(all(set(refs).intersection(e['evidence_ref'] for e in pair[role]['events'])
                            for role in ('parent', 'candidate')) for pair in relevant_pairs),
                'used memory requires both sides of a historical pair from that edit round')
        for index in indices:
            gap = gaps[index]
            require(set(refs) <= set(gap['evidence_refs']), 'review evidence must ground each linked gap')
            targets = set(gap['related_rule_refs'])
            current_refs = set(binding['current_rule_refs']) | set(binding['descendant_rule_refs'])
            if review['relation'] == 'RETRIES':
                original_texts = {b['text'] for b in edit['target_blocks']}
                original_targets = {ref for ref, block in request.learner_payload['available_rule_refs'].items()
                                    if block['text'] in original_texts}
                if edit['operation'] == 'DELETE':
                    require(gap['kind'] == 'SHOULD_REMOVE' and bool(targets & current_refs),
                            'retry deletion requires newly authorized existing targets')
                else:
                    require(binding['binding_status'] == 'ABSENT' and (
                        gap['kind'] == 'MISSING' or (edit['operation'] == 'REPLACE'
                            and gap['kind'] == 'NEEDS_REVISION' and bool(targets & original_targets))),
                        'retry requires absent proposed text and a newly authorized missing/revision gap')
            elif review['relation'] == 'REVISES':
                require(edit['operation'] != 'DELETE' and gap['kind'] == 'NEEDS_REVISION'
                        and bool(targets & current_refs), 'revision must target bound current content')
            elif edit['operation'] == 'DELETE':
                require(binding['binding_status'] == 'ABSENT' and gap['kind'] == 'MISSING',
                        'revert deletion requires missing guidance in current Parent')
            else:
                require(gap['kind'] in ('NEEDS_REVISION', 'SHOULD_REMOVE') and bool(targets & current_refs),
                        'revert must reauthorize a bound current target')
    require(seen == set(catalog), 'every selected historical edit requires review, including on NO_UPDATE')
    # Any gap citing old observations must explicitly acknowledge its memory source.
    historical = {r for r,v in request.learner_payload['available_evidence_refs'].items()
                  if v['origin'] == 'COMMITTED_HISTORICAL_OBSERVATION'}
    for index, gap in enumerate(gaps):
        if set(gap['evidence_refs']) & historical:
            require(any(r['decision'] == 'USE' and index in r['gap_indices'] for r in reviews),
                    'historical gap missing explicit memory review')
    return validated, output


def memory_diagnosis_source(raw, *, request):
    validated, _ = validate_memory_diagnosis_response(raw, request=request)
    provenance = {**request.provenance, 'memory_response': raw, 'memory_response_sha256': digest(raw)}
    bound_request = replace(request, provenance_json=encode(provenance))
    return CompilerDiagnosisSource('DIAGNOSIS/' + digest(validated.payload), bound_request, validated)


def validate_memory_source(source):
    """Called again by v19 ledger construction/restoration; no disk or model reads."""
    request = source.request
    provenance = request.provenance
    require(digest(provenance['memory_response']) == provenance['memory_response_sha256'], 'memory review digest mismatch')
    envelope, output = validate_memory_diagnosis_response(provenance['memory_response'], request=request)
    require(envelope == source.validated, 'memory response differs from compiled Diagnosis')
    return output


def memory_links_for_plan(value, *, run_id):
    """Map reauthorized gaps to original edit unit indices and exact source refs."""
    sources = {s.diagnosis_ref: s for s in value.compiler_input.diagnoses}
    reviews = {ref: validate_memory_source(s)['memory_review'] for ref, s in sources.items()
               if s.request.learner_payload.get('consumer_version') == 'memory_diagnosis_v19.1'}
    links = {}
    for index, unit in enumerate(value.plan.edit_units):
        for gap in unit.supporting_gap_refs:
            for review in reviews.get(gap.diagnosis_ref, []):
                if review['decision'] != 'USE' or gap.gap_index not in review['gap_indices']:
                    continue
                key = (index, review['edit_id'])
                if key not in links:
                    links[key] = {'edit_unit_index': index, 'prior_edit_id': review['edit_id'],
                                  'relation': review['relation'], 'basis_refs': []}
                require(links[key]['relation'] == review['relation'], 'conflicting memory relation in merged edit')
                for ref in review['evidence_refs']:
                    evidence = 'EVIDENCE/' + digest(encode({'run_id': run_id, 'round_id': value.compiler_input.round_id,
                        'diagnosis_ref': gap.diagnosis_ref, 'reference_type': 'TRAJECTORY', 'ref': ref}))
                    if evidence not in links[key]['basis_refs']:
                        links[key]['basis_refs'].append(evidence)
    for item in links.values():
        item['basis_refs'].sort()
    return [links[key] for key in sorted(links)]
