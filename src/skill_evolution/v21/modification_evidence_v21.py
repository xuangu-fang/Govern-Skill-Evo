"""Read-only post-modification evidence for the v21 Memory updater.

Revalidate completed train checkpoints and generation before projecting public
observations. No rollout, evaluator, Gate, attribution or Memory write runs here.
The archive is complete; open_memory_evidence builds a bounded consumer view.
"""
from dataclasses import dataclass
from pathlib import Path

from ..v19.edit_tracking_v19 import encode, parse, digest, skill_ref
from ..v19.evolution_replay_v19 import _input, _manifest, _load_set, _project, _file_digest, _load, _save, _execution_ref
from ..v20.evidence_review_v20 import EvidenceArchive, build_evidence_archive, merge_evidence_archives, validate_evidence_archive
from ..v20.local_generation_v20 import restore_generation
from ..v20.issue_memory_v20 import validate_memory
from ..v20.runtime_v20 import _finding_records, _fusion_records
from ..v20.issue_fusion_v20 import IssueFusionResult
from ..v19.memory_store_v19 import require


@dataclass(frozen=True)
class ModificationEvidence:
    payload_json: str

    @property
    def payload(self):
        return parse(self.payload_json)

    @property
    def evidence_ref(self):
        return 'MODIFICATION_EVIDENCE_V21/' + digest(self.payload_json)


def _merge(target, incoming):
    for ref, value in incoming.items():
        require(ref not in target or target[ref] == value, 'conflicting evidence: ' + ref)
        target[ref] = value


def _bodies(events):
    return [{k: v for k, v in event.items() if k != 'evidence_ref'} for event in events]


def build_modification_evidence(*, audit, backend, parent_dir, candidate_dir, history=()):
    """Build from authenticated completed checkpoints, never candidate-summary.

    backend must supply the trusted train manifest. history contains only bundles
    selected by the caller from committed rounds (or explicitly imported history);
    filesystem adjacency alone never makes a previous round committed.
    """
    is_v21 = audit['source']['schema_version'] == 'generation_input_v21.1'
    if is_v21:
        from .memory_consumption_v21 import restore_generation as restore_v21
        _, result = restore_v21(audit)
    else:
        _, result = restore_generation(audit)
    require(result['status'] in ('EDITED', 'APPLIED_DETERMINISTIC') and result['edits'],
            'completed Candidate generation required')
    source = audit['source']
    batch = source['current_requests'][0]['provenance']['batch']
    run_id, round_id = batch['run_id'], batch['round_id']
    parent, candidate = source['parent_skill'], result['candidate_skill']
    manifest = _manifest(backend)  # rejects a Monitor manifest
    require(batch['evolution_manifest_sha256'] == digest(encode(manifest)),
            'generation and replay train manifests differ')
    parents = _load_set(Path(parent_dir), _input(run_id, round_id, 'PARENT', parent, manifest))
    candidate_input = _input(run_id, round_id, 'CANDIDATE', candidate, manifest,
                             parent_set=_file_digest(Path(parent_dir) / 'state.json'))
    candidates = _load_set(Path(candidate_dir), candidate_input)
    replay = _project(candidate_input, parents, candidates).payload

    # Reuse v20's validated source archive; augment missing current records even
    # when the generation source predates v20's durable Finding archive wiring.
    experiences = [e for r in source['current_requests'] for e in r['payload']['experiences']]
    contexts = [c for r in source['current_requests'] for c in r['payload']['contexts']]
    bases = [] if is_v21 else [validate_evidence_archive(EvidenceArchive(encode(source['archive'])))]
    base = merge_evidence_archives(*bases,
        build_evidence_archive(run_id=run_id, experiences=experiences, contexts=contexts,
            records=_finding_records(source['current_findings']) +
                    _fusion_records(IssueFusionResult(encode(source['fusion_result'])))),
        build_evidence_archive(run_id=run_id, edits=result['edits'])).payload
    archive = {key: base[key] for key in ('contexts', 'trajectories', 'events', 'records', 'edits')}
    archive.update(pairs={}, parent_pairs={})
    inherited = [ModificationEvidence(encode(source['memory_evidence']))] if is_v21 else []
    prior = inherited + list(history)
    for previous in prior:
        require(isinstance(previous, ModificationEvidence), 'validated history bundle required')
        old = previous.payload
        require(old['run_id'] == run_id and old['round_id'] != round_id,
                'history run/round mismatch')
        for key in archive:
            _merge(archive[key], old['archive'][key])

    for context in replay['contexts']:
        ref = context['context_ref']
        _merge(archive['contexts'], {ref: {k: context[k] for k in
            ('context_ref', 'visible_policy', 'public_tools')}})
    current_pairs = []
    for index, pair in enumerate(replay['pairs']):
        pid = pair['pair_id']
        current_pairs.append(pid)
        row = {k: pair[k] for k in ('pair_id', 'run_id', 'round_id', 'task_ref', 'rollout_index')}
        event_refs = []
        for role in ('parent', 'candidate'):
            observation = pair[role]
            tid = observation['trajectory_ref']
            row[role] = tid
            # This is a current replay, not a claimed committed historical run.
            metadata = {k: observation[k] for k in
                        ('trajectory_ref', 'role', 'skill_ref', 'context_ref', 'supervision')}
            metadata.update(pair_id=pid, source_round_id=round_id,
                            task_ref=pair['task_ref'], rollout_index=pair['rollout_index'])
            execution = _execution_ref((parents if role == 'parent' else candidates)[index])
            if execution is not None:
                metadata['execution_ref'] = execution
            _merge(archive['trajectories'], {tid: metadata})
            for event in observation['events']:
                ref = event['evidence_ref']
                _merge(archive['events'], {ref: {'trajectory_ref': tid,
                    'event': {k: v for k, v in event.items() if k != 'evidence_ref'}}})
                event_refs.append(ref)
        _merge(archive['pairs'], {pid: row})
        # A pair is an observation source, not per-edit attribution. No edit_refs
        # are attached: that would pull the entire round into every local view.
        _merge(archive['records'], {pid: {'ref': pid, 'kind': 'REPLAY',
            'statement': 'Paired observations; edit-specific effects are not inferred.',
            'evidence_refs': event_refs, 'counterevidence_refs': [],
            'edit_refs': [], 'source_refs': []}})

    # Authenticate the Parent evidence actually used for generation against the
    # replay Parent, then link its original IDs without copying/relabeling them.
    pairs_by_task = {p['task_ref']: p for p in replay['pairs']}
    source_contexts = {c['context_ref']: c for c in contexts}
    # Grouper uses anonymized/reordered task aliases. Resolve its explicit
    # provenance instead of equating the displayed T001 with replay's T001.
    bindings = {}
    for request in source['current_requests']:
        lineage = request['provenance']['experience_bindings']
        require(len(lineage) == len(request['payload']['experiences']), 'incomplete Parent lineage')
        for item in lineage:
            _merge(bindings, {item['presented']['task_ref']: item})
    require(set(bindings) == {e['task_ref'] for e in experiences}
            and {b['source']['task_ref'] for b in bindings.values()} == set(pairs_by_task)
            and len(experiences) == len(bindings) == len(pairs_by_task),
            'incomplete generation Parent coverage')
    for exp in experiences:
        binding = bindings[exp['task_ref']]
        require(all(exp[k] == v for k, v in binding['presented'].items())
                and exp['rollout_index'] == binding['rollout_index'], 'Parent alias lineage mismatch')
        pair = pairs_by_task[binding['source']['task_ref']]
        obs = pair['parent']
        expected_context = archive['contexts'][obs['context_ref']]
        context = source_contexts[exp['context_ref']]
        if 'execution_ref' in exp:
            require(exp['execution_ref'] == archive['trajectories'][obs['trajectory_ref']].get('execution_ref'),
                    'generation Parent execution identity differs from replay')
        require(exp['role'] == 'PARENT' and exp['source_round_id'] == round_id
                and exp['skill_ref'] == obs['skill_ref']
                and exp['rollout_index'] == pair['rollout_index']
                and _bodies(exp['events']) == _bodies(obs['events'])
                and all(exp['supervision'][k] == obs['supervision'][k]
                        for k in ('success', 'compliant', 'level'))
                and all(context[k] == expected_context[k] for k in ('visible_policy', 'public_tools')),
                'generation Parent evidence differs from replay')
        for event in exp['events']:
            tid = archive['events'][event['evidence_ref']]['trajectory_ref']
            _merge(archive['parent_pairs'], {tid: pair['pair_id']})

    reviews = []
    for original in audit['reviews']:
        review = {k: original[k] for k in ('proposal_id', 'verdict', 'evidence_refs',
                                          'counterevidence_refs', 'reason', 'gap')}
        rid = 'REVIEW_V21/' + digest(encode({'input_ref': result['input_ref'], 'review': review}))
        reviews.append({'review_ref': rid, **review})
        _merge(archive['records'], {rid: {'ref': rid, 'kind': 'REVIEW',
            'statement': review['reason'], 'evidence_refs': review['evidence_refs'],
            'counterevidence_refs': review['counterevidence_refs'],
            'edit_refs': [e['edit_id'] for e in result['edits'] if review['proposal_id'] in e['proposal_refs']],
            'source_refs': []}})
    memory = validate_memory(source['memory'], run_id=run_id)
    return ModificationEvidence(encode({
        'schema_version': 'modification_evidence_v21.1', 'run_id': run_id, 'round_id': round_id,
        'parent_skill': parent, 'candidate_skill': candidate,
        'parent_skill_ref': skill_ref(parent), 'candidate_skill_ref': skill_ref(candidate),
        'generation_ref': result['input_ref'], 'generation_sha256': digest(encode(audit)),
        'train_manifest_sha256': digest(encode(manifest)),
        'parent_checkpoint_sha256': _file_digest(Path(parent_dir) / 'state.json'),
        'candidate_checkpoint_sha256': _file_digest(Path(candidate_dir) / 'state.json'),
        'history_refs': sorted({h.evidence_ref for h in prior}),
        'memory': memory, 'proposals': source['fusion_result']['issues'],
        'reviews': reviews, 'edits': result['edits'], 'current_pair_refs': current_pairs,
        'archive': archive}))


def save_modification_evidence(evidence, path):
    """Immutable, idempotent save. A failed/mismatched rerun cannot replace it."""
    require(isinstance(evidence, ModificationEvidence), 'ModificationEvidence required')
    path = Path(path)
    if path.exists():
        require(encode(_load(path)) == evidence.payload_json, 'existing evidence differs')
    else:
        _save(path, evidence.payload)
    return evidence.evidence_ref


def load_modification_evidence(path, *, expected_ref):
    """expected_ref comes from the trusted caller/commit, not the file itself."""
    value = ModificationEvidence(encode(_load(path)))
    require(value.evidence_ref == expected_ref, 'evidence digest mismatch')
    require(value.payload['schema_version'] == 'modification_evidence_v21.1', 'evidence version mismatch')
    return value


def prepare_memory_evidence(*, round_dir, backend, output, history=()):
    """Offline/runtime seam immediately after completed Candidate replay.

    Does not call a semantic updater or write a Memory head. Future v21 wiring
    passes bounded views of the returned evidence to the Memory updater.
    """
    root = Path(round_dir)
    require(not Path(output).resolve().is_relative_to(root.resolve()),
            'derived evidence must be outside the source round directory')
    value = build_modification_evidence(
        audit=_load(root / 'generation' / 'generation-audit.json'), backend=backend,
        parent_dir=root / 'parent_evolution', candidate_dir=root / 'candidate_evolution', history=history)
    save_modification_evidence(value, output)
    return value


def open_memory_evidence(evidence, *, issue_refs=(), proposal_refs=(), source_refs=(), pair_refs=(), event_refs=()):
    """Load selected issues/sources, counterevidence and complete matched pairs.

    Explicit pair_refs also admit new evidence for an old/unselected issue. This
    is reference resolution, not a relevance classifier or effect assessment.
    """
    data = evidence.payload
    archive = data['archive']
    issues = {i['issue_id']: i for i in data['memory']['issues']}
    proposals = {p['proposal_issue_id']: p for p in data['proposals']}
    selected_issues, selected_proposals = set(issue_refs), set(proposal_refs)
    require(selected_proposals <= proposals.keys(), 'unknown proposal reference')
    for pid in selected_proposals:
        selected_issues.update(proposals[pid]['memory_issue_refs'])
    require(selected_issues <= issues.keys(), 'unknown issue reference')
    sources, edits, pairs = set(source_refs), set(), set(pair_refs)
    issue_sources = {}
    for iid in selected_issues:
        issue = issues[iid]
        local = set(issue['source_refs'])
        for attempt in issue['attempts']:
            local.update(attempt['source_refs'])
            edits.update(attempt['edit_refs'])
        # Explicit historical links belong to this issue's provenance. Reverse
        # links through a shared edit are context, not automatic issue ownership.
        pending = list(local)
        while pending:
            ref = pending.pop()
            require(ref in archive['records'], 'unresolved issue source reference')
            for dependency in archive['records'][ref]['source_refs']:
                if dependency not in local:
                    local.add(dependency)
                    pending.append(dependency)
        issue_sources[iid] = sorted(local)
        sources.update(local)
    for pid in selected_proposals:
        sources.update(proposals[pid]['current_finding_refs'])
        sources.update(r['review_ref'] for r in data['reviews'] if r['proposal_id'] == pid)
        edits.update(e['edit_id'] for e in data['edits'] if pid in e['proposal_refs'])
    require(pairs <= archive['pairs'].keys(), 'unknown pair reference')
    sources.update(pairs)
    # Follow explicit source/joint-edit links, preserving all known restrictions.
    while True:
        before = (len(sources), len(edits))
        require(sources <= archive['records'].keys(), 'unresolved source reference')
        require(edits <= archive['edits'].keys(), 'unresolved edit reference')
        sources.update(ref for ref, r in archive['records'].items() if edits & set(r['edit_refs']))
        for ref in list(sources):
            sources.update(archive['records'][ref]['source_refs'])
            edits.update(archive['records'][ref]['edit_refs'])
        if before == (len(sources), len(edits)):
            break
    event_refs = set(event_refs) | {ref for s in sources for key in ('evidence_refs', 'counterevidence_refs')
                                   for ref in archive['records'][s][key]}
    require(event_refs <= archive['events'].keys(), 'unresolved event reference')
    tids = {archive['events'][ref]['trajectory_ref'] for ref in event_refs}
    for tid in list(tids):
        pair = archive['trajectories'][tid].get('pair_id') or archive['parent_pairs'].get(tid)
        if pair:
            pairs.add(pair)
    for pid in pairs:
        tids.update(archive['pairs'][pid][role] for role in ('parent', 'candidate'))
    contexts = {archive['trajectories'][tid]['context_ref'] for tid in tids}
    return {'schema_version': 'memory_evidence_view_v21.2', 'evidence_ref': evidence.evidence_ref,
        'run_id': data['run_id'], 'round_id': data['round_id'],
        'parent_skill': data['parent_skill'], 'candidate_skill': data['candidate_skill'],
        'memory_issues': [issues[r] for r in sorted(selected_issues)],
        'issue_source_refs': {r: issue_sources[r] for r in sorted(selected_issues)},
        'proposals': [proposals[r] for r in sorted(selected_proposals)],
        'reviews': [r for r in data['reviews'] if r['review_ref'] in sources],
        'current_edits': data['edits'],
        'source_records': {r: archive['records'][r] for r in sorted(sources | pairs)},
        'edits': {r: archive['edits'][r] for r in sorted(edits)},
        'pairs': {r: archive['pairs'][r] for r in sorted(pairs)},
        'parent_pairs': {r: pair for r, pair in archive['parent_pairs'].items() if r in tids},
        'contexts': {r: archive['contexts'][r] for r in sorted(contexts)},
        'trajectories': {r: archive['trajectories'][r] for r in sorted(tids)},
        'events': {r: event for r, event in archive['events'].items() if event['trajectory_ref'] in tids}}
