"""Problem-scoped originals and one-pass review, independent of v19 review state.

Archive inputs must be learner-side projections, never raw benchmark artifacts.
The campaign owns artifact authentication; this boundary checks typed references,
loads complete selected trajectories and never treats a summary as an event.
"""
from dataclasses import dataclass
from copy import deepcopy

from ..v19.edit_tracking_v19 import encode, parse, digest
from ..v19.memory_store_v19 import require
from .issue_memory_v20 import validate_memory, IssueMemorySnapshot
from .issue_fusion_v20 import build_issue_fusion_input, validate_issue_fusion_result
from ..v19.current_diagnosis_v19 import validate_current_batch
from ..v18.diagnosis_references_v18 import build_reference_catalogs
from ..v19.evidence_review_v19 import FINAL_SCHEMA, GAP_SCHEMA, _validate_final_references
from ..v18.diagnosis_contract_v18 import _object, _validate
from ..v19.evidence_review_prompt_v19 import ONCE_SYSTEM
from ..v15.information_boundary_v15 import _public_schema


@dataclass(frozen=True)
class EvidenceArchive:
    payload_json: str

    @property
    def payload(self):
        return parse(self.payload_json)

    @property
    def archive_ref(self):
        return 'EVIDENCE_ARCHIVE_V20/' + digest(self.payload_json)


def _insert(catalog, ref, value):
    require(ref not in catalog or catalog[ref] == value, 'conflicting archive reference: ' + ref)
    catalog[ref] = value


def build_evidence_archive(*, run_id, experiences=(), contexts=(), records=(), edits=()):
    """Index already-projected learning evidence; no Memory state or Gate data.

    Records resolve Findings, reviews or attribution IDs into exact event refs.
    source_refs express explicit dependencies, edit_refs preserve joint identity.
    All records for an involved edit are loaded, including non-selected attempts.
    """
    require(isinstance(run_id, str) and run_id.strip(), 'archive run_id required')
    ctx, trajectories, events, sources, edit_map = {}, {}, {}, {}, {}
    for c in contexts:
        # Never copy arbitrary context metadata (private task/evaluator state).
        require(type(c['visible_policy']) is str, 'visible policy text required')
        for tool in c['public_tools']:
            _public_schema(tool)
        _insert(ctx, c['context_ref'], {k: c[k] for k in ('context_ref', 'visible_policy', 'public_tools')})
    for exp in experiences:
        require(exp['context_ref'] in ctx, 'missing visible context')
        metadata = {k: exp[k] for k in ('task_ref', 'trajectory_ref', 'rollout_index', 'context_ref',
                                       'origin', 'source_round_id', 'skill_ref', 'role', 'supervision')}
        label = exp['supervision']
        require(label.get('level') == 0 and type(label['success']) is bool and
                type(label['compliant']) is bool, 'only Level-0 supervision allowed')
        metadata['supervision'] = {k: label[k] for k in ('supervision_ref', 'level', 'success', 'compliant')}
        require(set(exp['skill_ref']) == {'skill_id', 'sha256', 'text_ref'}, 'invalid Skill identity')
        require(exp['role'] in ('PARENT', 'CANDIDATE') and exp['origin'] in
                ('CURRENT_PARENT', 'COMMITTED_HISTORICAL_OBSERVATION'), 'learner trajectory origin required')
        if 'pair_id' in exp:
            metadata['pair_id'] = exp['pair_id']
        if 'execution_ref' in exp:
            require(isinstance(exp['execution_ref'], str) and
                    exp['execution_ref'].startswith('EXECUTION/'), 'invalid execution identity')
            metadata['execution_ref'] = exp['execution_ref']
        tid = 'TRAJECTORY_V20/' + digest(encode(metadata))
        _insert(trajectories, tid, metadata)
        for event in exp['events']:
            base = {'evidence_ref', 'step', 'actor', 'event_type'}
            fields = {'message': {'content'}, 'tool_call': {'tool_name', 'arguments'},
                      'tool_result': {'tool_name', 'content'}}
            require(event['event_type'] in fields and set(event) == base | fields[event['event_type']],
                    'only observed event fields allowed')
            _insert(events, event['evidence_ref'], {'trajectory_ref': tid,
                'event': {k: v for k, v in event.items() if k != 'evidence_ref'}})
    for edit in edits:
        require(edit['operation'] in ('ADD', 'REPLACE', 'DELETE'), 'invalid archived edit operation')
        _insert(edit_map, edit['edit_id'], {k: edit[k] for k in ('edit_id', 'operation', 'target_blocks', 'after_text')})
    fields = {'ref', 'kind', 'statement', 'evidence_refs', 'counterevidence_refs', 'edit_refs', 'source_refs'}
    for record in records:
        require(set(record) == fields, 'exact archive record fields required')
        require(record['kind'] in ('FINDING', 'REVIEW', 'ATTRIBUTION'), 'learning-side record kind required')
        require(isinstance(record['statement'], str) and record['statement'].strip(), 'source statement required')
        for field in ('evidence_refs', 'counterevidence_refs', 'edit_refs', 'source_refs'):
            refs = record[field]
            require(type(refs) is list and all(type(r) is str and r for r in refs)
                    and len(refs) == len(set(refs)), 'invalid archive ' + field)
        require(set(record['evidence_refs'] + record['counterevidence_refs']) <= events.keys(), 'unresolved original event')
        require(set(record['edit_refs']) <= edit_map.keys(), 'unresolved joint edit')
        _insert(sources, record['ref'], record)
    require(all(set(r['source_refs']) <= sources.keys() for r in sources.values()), 'unresolved source dependency')
    return EvidenceArchive(encode({'schema_version': 'evidence_archive_v20.1', 'run_id': run_id,
        'contexts': ctx, 'trajectories': trajectories, 'events': events, 'records': sources, 'edits': edit_map}))


def merge_evidence_archives(*archives):
    """Merge round archives while preserving exact historical references.

    A v20 Memory source reference can point at a Finding from an earlier round.
    The archive supplied to local review therefore needs a durable, learner-side
    union of prior round records.  This merge only unions authenticated archive
    maps; it does not add new evidence or copy private benchmark artifacts.
    """
    require(archives, 'at least one evidence archive required')
    checked = [validate_evidence_archive(a) for a in archives]
    run_id = checked[0].payload['run_id']
    merged = {'schema_version': 'evidence_archive_v20.1', 'run_id': run_id,
              'contexts': {}, 'trajectories': {}, 'events': {}, 'records': {}, 'edits': {}}
    for archive in checked:
        data = archive.payload
        require(data['run_id'] == run_id, 'archive run mismatch')
        for key in ('contexts', 'trajectories', 'events', 'records', 'edits'):
            for ref, value in data[key].items():
                _insert(merged[key], ref, value)
    return validate_evidence_archive(EvidenceArchive(encode(merged)))


def validate_evidence_archive(archive):
    p = archive.payload
    experiences = [{**metadata, 'events': [
        {'evidence_ref': ref, **value['event']} for ref, value in p['events'].items()
        if value['trajectory_ref'] == tid]} for tid, metadata in p['trajectories'].items()]
    rebuilt = build_evidence_archive(run_id=p['run_id'], experiences=experiences,
        contexts=p['contexts'].values(), records=p['records'].values(), edits=p['edits'].values())
    require(rebuilt == archive, 'archive changed or malformed')
    return archive


@dataclass(frozen=True)
class EvidenceReviewInput:
    payload_json: str

    @property
    def payload(self):
        return parse(self.payload_json)

    @property
    def input_ref(self):
        return 'EVIDENCE_REVIEW_INPUT_V20/' + digest(self.payload_json)

    def build_request(self):
        return _v20_review_request(self)

    def normalize_response(self, raw):
        return raw


@dataclass(frozen=True)
class EvidenceReviewResult:
    payload_json: str

    @property
    def payload(self):
        return parse(self.payload_json)


def build_evidence_review_inputs(*, memory, fusion_input, fusion_result, parent_skill,
                                archive, current_requests=(), current_findings=(), history=()):
    """Rebuild Fusion from its sources, then open only selected problem evidence.

    Entire trajectories containing relevant events are included with their
    policy/tool context. This avoids loss of prerequisites and call/results
    without pulling unrelated pairs or whole-round history into every request.
    """
    require(isinstance(archive, EvidenceArchive), 'EvidenceArchive required')
    fp = fusion_input.payload
    mem = validate_memory(memory.memory if isinstance(memory, IssueMemorySnapshot) else memory,
                          run_id=fp['run_id'])
    if isinstance(memory, IssueMemorySnapshot):
        require(memory.memory_ref == 'MEMORY_V20/' + digest(encode(mem)), 'memory digest mismatch')
    if current_requests or current_findings:
        batch = validate_current_batch(current_requests, current_findings)
        require(batch['run_id'] == fp['run_id'] and batch['round_id'] == fp['round_id'], 'current batch mismatch')
        require(all(r.payload['current_skill'] == parent_skill for r in current_requests), 'current Parent mismatch')
    require(build_issue_fusion_input(memory=memory, current_requests=current_requests,
        current_findings=current_findings, parent_skill=parent_skill, run_id=fp['run_id'],
        round_id=fp['round_id'], history=history) == fusion_input, 'Fusion source binding mismatch')
    validate_issue_fusion_result(fusion_result, request=fusion_input)
    data = validate_evidence_archive(archive).payload
    require(data['schema_version'] == 'evidence_archive_v20.1' and data['run_id'] == fp['run_id'], 'archive run mismatch')
    # Current originals come from the validated Diagnosis inputs, never a second
    # caller-authored catalog that could disagree with those findings.
    current_archive = build_evidence_archive(run_id=fp['run_id'],
        experiences=[e for r in current_requests for e in r.payload['experiences']],
        contexts=[c for r in current_requests for c in r.payload['contexts']]).payload
    for key in ('contexts', 'trajectories', 'events'):
        for ref, value in current_archive[key].items():
            _insert(data[key], ref, value)
    findings = {f['finding_id']: f for fs in current_findings for f in fs.payload['findings']}
    memories = {i['issue_id']: i for i in mem['issues']}
    rules = build_reference_catalogs({'current_skill': parent_skill, 'contexts': []})['available_rule_refs']
    requests = []
    for issue in fusion_result.payload['issues']:
        if issue['decision'] != 'PROPOSE':
            continue
        selected = [memories[r] for r in issue['memory_issue_refs']]
        selected_findings = [findings[r] for r in issue['current_finding_refs']]
        sources = {r for i in selected for r in i['source_refs']}
        edits = {r for i in selected for a in i['attempts'] for r in a['edit_refs']}
        sources.update(r for i in selected for a in i['attempts'] for r in a['source_refs'])
        # Current finding IDs are also legitimate Memory sources.
        for f in findings.values():
            _insert(data['records'], f['finding_id'], {'ref': f['finding_id'], 'kind': 'FINDING',
                'statement': f['statement'], 'evidence_refs': f['evidence_refs'],
                'counterevidence_refs': f['evidence_refs'] if f['kind'] == 'COUNTEREVIDENCE' else [],
                'edit_refs': [], 'source_refs': []})
        while True:
            require(sources <= data['records'].keys(), 'unresolved Memory source')
            require(edits <= data['edits'].keys(), 'unresolved Memory edit')
            before = (len(sources), len(edits))
            # Explicit joint edit/source closure, never whole-round closure.
            sources.update(ref for ref, r in data['records'].items() if edits & set(r['edit_refs']))
            for ref in list(sources):
                edits.update(data['records'][ref]['edit_refs'])
                sources.update(data['records'][ref]['source_refs'])
            if before == (len(sources), len(edits)):
                break
        records = {r: data['records'][r] for r in sorted(sources)}
        seeds = {r for f in selected_findings for r in f['evidence_refs']}
        counter = {r for f in selected_findings if f['kind'] == 'COUNTEREVIDENCE' for r in f['evidence_refs']}
        for record in records.values():
            seeds.update(record['evidence_refs']); counter.update(record['counterevidence_refs'])
        seeds.update(counter)
        require(seeds <= data['events'].keys(), 'unresolved selected original')
        tids = {data['events'][r]['trajectory_ref'] for r in seeds}
        trajectories = {t: data['trajectories'][t] for t in sorted(tids)}
        events = {r: e for r, e in data['events'].items() if e['trajectory_ref'] in tids}
        contexts = {t['context_ref'] for t in trajectories.values()}
        policies = build_reference_catalogs({'current_skill': parent_skill,
            'contexts': [data['contexts'][r] for r in sorted(contexts)]})['available_policy_refs']
        tools = {f'TOOL/{c}/{n}/{digest(encode(t))}': {'context_ref': c, 'definition': t}
                 for c in sorted(contexts) for n, t in enumerate(data['contexts'][c]['public_tools'])}
        requests.append(EvidenceReviewInput(encode({'schema_version': 'evidence_review_input_v20.1',
            'fusion_input_ref': fusion_input.input_ref, 'fusion_result_sha256': digest(fusion_result.payload_json),
            'archive_ref': archive.archive_ref, 'proposal_id': issue['proposal_issue_id'], 'issue': issue,
            'parent_skill_sha256': digest(parent_skill), 'findings': selected_findings,
            'memory_issues': selected, 'source_records': records,
            'historical_edits': {r: data['edits'][r] for r in sorted(edits)},
            'events': events, 'trajectories': trajectories, 'rules': rules, 'policies': policies, 'tools': tools,
            'known_counterevidence_refs': sorted(counter),
            'selection': 'SELECTED_PROBLEMS_ALL_ATTEMPTS_EXPLICIT_DEPENDENCIES_AND_RELEVANT_TRAJECTORIES'})))
    return tuple(requests)


def validate_evidence_review(raw, *, request):
    require(isinstance(request, EvidenceReviewInput), 'v20 EvidenceReviewInput required')
    p = request.payload
    require(p['schema_version'] == 'evidence_review_input_v20.1', 'review protocol mismatch')
    raw = request.normalize_response(raw)
    out = parse(raw)
    require(type(out) is dict and set(out) == set(FINAL_SCHEMA['properties']), 'exact final verdict fields required')
    fields = {k: v for k, v in FINAL_SCHEMA['properties'].items() if k != 'gap'}
    _validate({k: out[k] for k in fields}, _object(fields), 'response')
    require(out['proposal_id'] == p['proposal_id'], 'proposal identity changed')
    require(out['reason'].strip(), 'review reason required')
    for key in ('evidence_refs', 'counterevidence_refs'):
        require(len(out[key]) == len(set(out[key])), 'duplicate event citation')
    if out['verdict'] == 'VERIFIED':
        _validate(out['gap'], GAP_SCHEMA, 'response.gap')
        require(out['gap']['statement'].strip(), 'gap statement required')
        targets = out['gap']['related_rule_refs']
        require(len(targets) == len(set(targets)), 'duplicate target')
    else:
        require(out['gap'] is None, 'NO_EDIT cannot carry a gap')
    _validate_final_references(out, p)
    return EvidenceReviewResult(encode({'schema_version': 'evidence_review_result_v20.1',
        'input_ref': request.input_ref, 'raw_response': raw, **out,
        'validation_scope': 'REFERENCES_AND_CONTRACT_NOT_SEMANTIC_TRUTH_OR_CAUSAL_PROOF'}))


def validate_evidence_review_result(result, *, request):
    require(isinstance(result, EvidenceReviewResult) and
            validate_evidence_review(result.payload['raw_response'], request=request) == result,
            'review result changed or stale')
    return result


def build_evidence_review_request(request):
    return request.build_request()


def _v20_review_request(request):
    system = ONCE_SYSTEM + '''
This v20 packet includes all attempts of each selected problem and explicit joint
source dependencies. memory_issues and source_records are prior hypotheses, not
new observations. Only events contains original event bodies. An ACCEPT never
makes an approach permanently correct; RETAIN never invalidates every local edit.
Before retrying an approach, address its specific failed conditions in reason:
explain a changed behavior/scope or loaded evidence that changes the old concern.
A repeated problem alone does not justify repeating the same failed solution.
History-only proposals can be verified using loaded historical originals and the
actual current Parent. Check current rules before deciding MISSING. Keep joint
edit relationships and uncertainty; do not assign a joint outcome to one edit.
'''
    return {'prompt_version': 'evidence-review-v20.1', 'system_prompt': system,
        'user_prompt': request.payload_json, 'input_ref': request.input_ref,
        'response_format': {'type': 'json_schema', 'json_schema': {
            'name': 'evidence_review_v20', 'strict': True, 'schema': deepcopy(FINAL_SCHEMA)}}}
