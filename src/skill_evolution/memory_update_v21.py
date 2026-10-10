"""Evidence-backed v21 Memory deltas, auditable and replayable without a head write.

Persistent Memory retains the v20 schema. The caller/campaign owns atomic Skill
and Memory publication; this stage saves a complete proposed revision and its
derived evidence archive, never a standalone deployment or active Memory head.
"""
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import json

from .edit_tracking_v19 import encode, parse, digest
from .diagnosis_contract_v18 import _validate
from .issue_memory_v20 import merge_update, validate_memory
from .memory_store_v19 import require
from .modification_evidence_v21 import ModificationEvidence, open_memory_evidence
from .current_understanding_v21 import (
    current_understanding, open_current_memory_evidence, PREFIX, MAX_CHARACTERS,
)
from .memory_update_prompt_v21 import SYSTEM, SCHEMA
from .evidence_wire_v21 import pack, pack_memory, restore_response, INSTRUCTIONS
from .memory_generation_prompt_v19 import diagnosis_budget
from .memory_generation_v19 import _read_call
from .attribution_v19 import _transport
from .evolution_replay_v19 import _load, _save, _file_digest, _lock


@dataclass(frozen=True)
class MemoryUpdateInput:
    evidence: ModificationEvidence
    payload_json: str

    @property
    def payload(self):
        return parse(self.payload_json)

    @property
    def input_ref(self):
        return 'MEMORY_UPDATE_INPUT_V21/' + digest(self.payload_json)


def _check_input(request):
    require(isinstance(request, MemoryUpdateInput), 'MemoryUpdateInput required')
    packet, data = request.payload, request.evidence.payload
    require(packet['evidence_ref'] == request.evidence.evidence_ref
            and all(packet[k] == data[k] for k in ('run_id', 'round_id', 'parent_skill', 'candidate_skill'))
            and packet['current_edits'] == data['edits'], 'Memory input/evidence binding mismatch')
    expected = build_memory_update_input(request.evidence,
        issue_refs=[i['issue_id'] for i in packet['memory_issues']],
        proposal_refs=[p['proposal_issue_id'] for p in packet['proposals']], pair_refs=list(packet['pairs']))
    require(expected == request, 'Memory input view differs from original evidence')


def regression_pair_refs(evidence):
    """Find current paired Level-0 label declines, not edit-specific causes.

    Scan the complete current replay index, independent of pre-edit citations.
    Missing/invalid labels fail closed rather than silently dropping a case.
    """
    require(isinstance(evidence, ModificationEvidence), 'ModificationEvidence required')
    data = evidence.payload
    archive = data['archive']
    current = data['current_pair_refs']
    indexed = {ref for ref, pair in archive['pairs'].items()
               if pair['run_id'] == data['run_id'] and pair['round_id'] == data['round_id']}
    require(len(current) == len(set(current)) and set(current) == indexed,
            'incomplete or duplicate current replay pair index')
    regressions = []
    for ref in current:
        pair = archive['pairs'][ref]
        require(pair['pair_id'] == ref and pair['parent'] != pair['candidate'], 'invalid replay pair identity')
        labels = {}
        for role in ('parent', 'candidate'):
            require(pair[role] in archive['trajectories'], 'missing replay trajectory')
            trajectory = archive['trajectories'][pair[role]]
            require(trajectory['role'] == role.upper() and trajectory['pair_id'] == ref
                    and trajectory['source_round_id'] == data['round_id']
                    and trajectory['skill_ref'] == data[role + '_skill_ref'], 'replay trajectory binding mismatch')
            label = trajectory['supervision']
            require(label.get('level') == 0 and all(type(label.get(k)) is bool
                    for k in ('success', 'compliant')), 'paired Level-0 boolean labels required')
            labels[role] = label
        if any(labels['parent'][k] and not labels['candidate'][k] for k in ('success', 'compliant')):
            regressions.append(ref)
    return tuple(regressions)


def build_memory_update_input(evidence, *, issue_refs=(), proposal_refs=None, pair_refs=()):
    regressions = regression_pair_refs(evidence)
    data = evidence.payload
    proposals = ([p['proposal_issue_id'] for p in data['proposals']]
                 if proposal_refs is None else list(proposal_refs))
    view = open_memory_evidence(evidence, issue_refs=issue_refs, proposal_refs=proposals,
                                pair_refs=sorted(set(pair_refs) | set(regressions)))
    for issue in view['memory_issues']:
        summary = current_understanding(issue, data['archive'])
        if summary:
            issue['current_understanding'] = summary['statement']
    # All short issue summaries remain visible to avoid duplicating an unloaded
    # historical issue. Only explicitly loaded issues may be revised in this call.
    loaded = {i['issue_id'] for i in view['memory_issues']}
    view['memory_catalog'] = [{'issue_id': i['issue_id'], 'problem': i['problem']}
                              for i in data['memory']['issues'] if i['issue_id'] not in loaded]
    view['current_pair_refs'] = [p for p in data['current_pair_refs'] if p in view['pairs']]
    view['regression_pair_refs'] = list(regressions)
    require(view['current_pair_refs'], 'load relevant current replay pairs before Memory update')
    view['schema_version'] = 'memory_update_input_v21.4'
    return MemoryUpdateInput(evidence, encode(view))


def build_memory_update_request(request, *, model='deepseek-v4-pro', max_input_tokens=800000):
    _check_input(request)
    require(type(max_input_tokens) is int and max_input_tokens > 0, 'positive input limit required')
    payload = request.payload
    wire, reference_map = pack_memory(payload)
    system = SYSTEM + INSTRUCTIONS
    # Read historical interpretations first, then revisit the paired originals.
    # Only presentation order changes; no evidence is selected or summarized.
    comparison = wire.pop('replay_comparison')
    wire['replay_comparison'] = comparison
    user = json.dumps(wire, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    response_format = {'type': 'json_schema', 'json_schema': {
        'name': 'memory_update_v21', 'strict': True, 'schema': deepcopy(SCHEMA)}}
    budget = diagnosis_budget(system, user, response_format)
    require(budget['proxy_input_tokens'] <= max_input_tokens,
            'Memory update input exceeds budget; no evidence truncated or request sent')
    return {'prompt_version': 'memory_update_v21.10', 'input_ref': request.input_ref,
        'model': model, 'temperature': 0.0, 'reasoning_effort': 'high',
        'max_completion_tokens': 24000, 'timeout_seconds': 600, 'max_retries': 0,
        'system_prompt': system, 'user_prompt': user, 'response_format': response_format,
        'input_budget': budget, 'max_input_tokens': max_input_tokens,
        'reference_map': reference_map}


@dataclass(frozen=True)
class MemoryUpdateResult:
    payload_json: str

    @property
    def payload(self):
        return parse(self.payload_json)

    @property
    def updated_evidence(self):
        return ModificationEvidence(encode(self.payload['updated_evidence']))


def validate_memory_update(raw, *, request, wire=False):
    """Check identity, coverage and original citations, not semantic truth."""
    _check_input(request)
    require(type(raw) is str, 'Memory update response must be JSON text')
    if wire:
        raw = restore_response(raw, pack(request.payload)[1])
    response = parse(raw)
    _validate(response, SCHEMA, 'memory_update')
    packet, data = request.payload, request.evidence.payload
    base = validate_memory(data['memory'], run_id=data['run_id'])
    issues = {i['issue_id']: i for i in packet['memory_issues']}
    current_edits = {e['edit_id'] for e in data['edits']}
    records, covered, seen_issues = {}, set(), set()
    update = {'schema_version': 'issue_memory_update_v20.1', 'run_id': data['run_id'],
              'round_id': data['round_id'], 'issues': []}

    def citations(refs, *, candidate=False):
        require(bool(refs) and set(refs) <= packet['events'].keys(),
                'source_refs must cite loaded original events')
        fresh = []
        for ref in refs:
            tid = packet['events'][ref]['trajectory_ref']
            trajectory = packet['trajectories'][tid]
            pair = trajectory.get('pair_id') or packet['parent_pairs'].get(tid)
            if pair in packet['current_pair_refs'] and (not candidate or trajectory['role'] == 'CANDIDATE'):
                fresh.append(ref)
        require(fresh, 'changed record needs current ' + ('Candidate ' if candidate else '') + 'replay evidence')

    def record(text, refs, edit_refs, prior_refs, counter_refs, *, prefix='ASSESSMENT_V21/', owner=None):
        # A derived judgment keeps its own citations and old source dependencies;
        # preserving them does not mark the old judgment as permanently correct.
        pair_refs = set()
        for ref in refs:
            tid = packet['events'][ref]['trajectory_ref']
            pair = packet['trajectories'][tid].get('pair_id') or packet['parent_pairs'].get(tid)
            if pair:
                pair_refs.add(pair)
        body = {'kind': 'ATTRIBUTION', 'statement': text, 'evidence_refs': refs,
                'counterevidence_refs': sorted(counter_refs), 'edit_refs': edit_refs,
                'source_refs': sorted(set(prior_refs) | pair_refs)}
        ref = prefix + digest(encode({'input_ref': request.input_ref, 'record': body, 'owner': owner}))
        records[ref] = {'ref': ref, **body}
        return ref

    for item in response['issues']:
        iid = item['issue_id']
        require(iid not in seen_issues, 'issue updated more than once')
        seen_issues.add(iid)
        new_issue = iid.startswith('NEW/') and len(iid) > 4
        require(new_issue or iid in issues, 'unknown or unloaded issue_id')
        previous = None if new_issue else issues[iid]
        require(previous is None or item['problem'] == previous['problem'],
                'existing issue problem is a fixed scope anchor; use a new issue for a different problem')
        row = ({'new_issue_key': request.input_ref + '/' + iid} if new_issue else {'issue_id': iid})
        row.update(problem=item['problem'], source_refs=[], attempts=[])
        prior = previous['source_refs'] if previous else []
        # Retain this issue's known restrictions, not every other issue's
        # interpretation reached by reverse traversal through a shared edit.
        # Shared context/counterevidence stays loaded and in the full archive.
        counters = {ref for source in packet['issue_source_refs'].get(iid, [])
                    for ref in packet['source_records'][source]['counterevidence_refs']}
        require(counters <= packet['events'].keys(), 'known counterevidence was not loaded')
        citations(item['source_refs'])
        require(item['current_understanding'].strip() and len(item['current_understanding']) <= MAX_CHARACTERS,
                'current understanding must be nonblank and within the character limit; no truncation')
        old_attempts = {a['attempt_id']: a for a in previous['attempts']} if previous else {}
        seen_attempts = set()
        for attempt in item['attempts']:
            aid = attempt['attempt_id']
            require(aid not in seen_attempts, 'attempt updated more than once')
            seen_attempts.add(aid)
            new_attempt = aid.startswith('NEW/') and len(aid) > 4
            require(new_attempt or aid in old_attempts, 'unknown attempt_id or wrong issue')
            old = None if new_attempt else old_attempts[aid]
            allowed = current_edits | (set(old['edit_refs']) if old else set())
            require(set(attempt['edit_refs']) <= allowed and (old is not None or attempt['edit_refs']),
                    'new attempts require actual current edits; old edit ownership must match')
            carries_current = bool(set(attempt['edit_refs']) & current_edits)
            citations(attempt['source_refs'], candidate=carries_current)
            inherited = list(prior) + (old['source_refs'] if old else [])
            ref = record(attempt['assessment'], attempt['source_refs'], attempt['edit_refs'], inherited, counters)
            entry = ({'new_attempt_key': request.input_ref + '/' + aid} if new_attempt else {'attempt_id': aid})
            entry.update(approach=attempt['approach'], assessment=attempt['assessment'],
                         edit_refs=attempt['edit_refs'], source_refs=[ref])
            row['attempts'].append(entry)
            covered.update(set(attempt['edit_refs']) & current_edits)
        refs = sorted(set(item['source_refs']) | {r for a in item['attempts'] for r in a['source_refs']})
        # A new synthesis cites observations directly. Linking every preceding
        # synthesis here would reopen the complete diary on every local review.
        # All prior sources/attempts still live in Memory and the full archive.
        row['source_refs'] = [record(item['current_understanding'], refs, [], [], counters,
                                    prefix=PREFIX, owner=iid)]
        update['issues'].append(row)
    require(covered == current_edits, 'every actual edit needs a recorded attempt; joint/unknown effects are allowed')
    memory = merge_update(base, update)
    augmented = deepcopy(data)
    augmented['memory'] = memory
    augmented['archive']['records'].update(records)
    augmented['prior_evidence_ref'] = request.evidence.evidence_ref
    augmented['memory_update_input_ref'] = request.input_ref
    augmented['memory_update_response_sha256'] = digest(raw)
    # Close every new source through the same reader the next stage will use.
    updated = ModificationEvidence(encode(augmented))
    touched_ids = {i['issue_id'] for i in memory['issues']} - {i['issue_id'] for i in base['issues']}
    touched_ids.update(i for i in seen_issues if i in issues)
    open_memory_evidence(updated, issue_refs=sorted(touched_ids))
    return MemoryUpdateResult(encode({'schema_version': 'memory_update_result_v21.1',
        'input_ref': request.input_ref, 'evidence_ref': request.evidence.evidence_ref,
        'base_memory_sha256': digest(encode(base)), 'raw_response': raw,
        'memory_update': update, 'memory': memory, 'updated_evidence': augmented,
        'updated_evidence_ref': updated.evidence_ref,
        'validation_scope': 'IDENTITY_COVERAGE_AND_ORIGINAL_SOURCES_NOT_SEMANTIC_TRUTH'}))


def regression_retention_report(request, result):
    """Audit citations and recoverability, never semantic relevance or edit merit.

    Missing links stay visible instead of assigning an issue or manufacturing a
    judgment. This report is local audit data, not Memory or a model response.
    """
    require(isinstance(result, MemoryUpdateResult), 'Memory update result required')
    require(validate_memory_update(result.payload['raw_response'], request=request) == result,
            'retention audit result differs from validated response')
    evidence = result.updated_evidence
    archive = evidence.payload['archive']
    summaries = [(i, current_understanding(i, archive)) for i in evidence.payload['memory']['issues']]
    views, rows = {}, []
    for pid in request.payload['regression_pair_refs']:
        pair = archive['pairs'][pid]
        row = {'pair_ref': pid, 'task_ref': pair['task_ref'], 'issues': []}
        for role in ('parent', 'candidate'):
            label = archive['trajectories'][pair[role]]['supervision']
            row[role] = {k: label[k] for k in ('success', 'compliant')}
        for issue, summary in summaries:
            if summary is None:
                continue
            refs = {'parent': [], 'candidate': []}
            for ref in summary['evidence_refs'] + summary['counterevidence_refs']:
                tid = archive['events'][ref]['trajectory_ref']
                if tid == pair['candidate']:
                    refs['candidate'].append(ref)
                elif tid == pair['parent'] or archive['parent_pairs'].get(tid) == pid:
                    refs['parent'].append(ref)
            if not any(refs.values()):
                continue
            iid = issue['issue_id']
            if iid not in views:
                views[iid] = open_current_memory_evidence(evidence, issue_refs=[iid])
            view = views[iid]
            originals = {r for r, e in archive['events'].items()
                         if e['trajectory_ref'] in (pair['parent'], pair['candidate'])}
            row['issues'].append({'issue_id': iid, 'understanding_ref': summary['ref'],
                'parent_event_refs': sorted(set(refs['parent'])),
                'candidate_event_refs': sorted(set(refs['candidate'])),
                'review_has_complete_pair': pid in view['pairs'] and bool(originals)
                    and originals <= view['events'].keys()})
        rows.append(row)
    return {'schema_version': 'regression_retention_audit_v21.1',
        'input_ref': request.input_ref, 'updated_evidence_ref': evidence.evidence_ref,
        'scope': 'LATEST_UNDERSTANDING_CITATIONS_AND_ISSUE_LOCAL_READABILITY_NOT_SEMANTIC_TRUTH',
        'pairs': rows,
        'uncited_pair_refs': [r['pair_ref'] for r in rows if not r['issues']],
        'one_sided_pair_refs': [r['pair_ref'] for r in rows if r['issues'] and not any(
            i['parent_event_refs'] and i['candidate_event_refs'] for i in r['issues'])],
        'unreadable_pair_refs': [r['pair_ref'] for r in rows if any(
            not i['review_has_complete_pair'] for i in r['issues'])]}


def _save_once(path, value):
    if path.exists():
        require(_load(path) == value, 'saved Memory update artifact changed: ' + path.name)
    else:
        _save(path, value)


def run_memory_update(request, *, output, transport=None, resume=False,
                      model='deepseek-v4-pro', max_input_tokens=800000):
    """One checkpointed semantic call. No repair loop, retries or live head write."""
    prompt = build_memory_update_request(request, model=model, max_input_tokens=max_input_tokens)
    root = Path(output)
    with _lock(root):
        if root.exists():
            require(resume, 'existing Memory update requires explicit resume')
            require(_load(root / 'input.json') == request.payload, 'Memory input changed on resume')
            require(_load(root / 'request.json') == prompt, 'Memory request changed on resume')
            require((root / 'response_complete.json').exists(),
                    'uncertain model call; explicit new attempt directory required')
        else:
            require(not resume, 'resume requires existing output')
            root.mkdir(parents=True)
            _save(root / 'input.json', request.payload)
            _save(root / 'request.json', prompt)
            try:
                response = (transport or _transport)(deepcopy(prompt))
            except Exception as exc:
                _save(root / 'failure.json', {'error_type': type(exc).__name__})
                raise
            _save(root / 'response.json', response)
            _save(root / 'response_complete.json', {'status': 'COMPLETE', 'files': {
                name: _file_digest(root / name) for name in ('request.json', 'response.json')}})
        raw = _read_call(root, prompt)
        result = validate_memory_update(raw, request=request, wire=True)
        payload = result.payload
        outputs = {'memory-update.json': payload['memory_update'], 'memory.json': payload['memory'],
                   'updated-evidence.json': payload['updated_evidence'], 'result.json': payload,
                   'regression-retention.json': regression_retention_report(request, result)}
        for name, value in outputs.items():
            _save_once(root / name, value)
        _save_once(root / 'complete.json', {'status': 'COMPLETE', 'input_ref': request.input_ref,
            'updated_evidence_ref': payload['updated_evidence_ref'],
            'files': {name: _file_digest(root / name) for name in outputs}})
        return result
