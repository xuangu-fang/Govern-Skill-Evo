"""Independent v20 multi-round campaign and atomic publication.

The campaign owns orchestration and publication. Benchmark Evolution,
Attribution and Monitor are injected as trusted callbacks; their private outputs
are archived outside the learner-facing Memory update.
"""
from dataclasses import dataclass
from pathlib import Path
import uuid

from ..v19.edit_tracking_v19 import encode, digest
from ..v19.evolution_replay_v19 import _load, _save, _file_digest, _lock
from .issue_memory_v20 import initialize_issue_memory, load_issue_memory, commit_issue_memory_update, merge_update, validate_memory, IssueMemorySnapshot, IssueMemoryRejected
from .local_generation_v20 import GenerationInput, run_local_generation, restore_generation


class CampaignRejected(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise CampaignRejected(message)


@dataclass(frozen=True)
class CampaignTransports:
    review: object = None
    editor: object = None


def campaign_config_v20(*, round_limit=4, model='deepseek-v4-pro'):
    require(type(round_limit) is int and 1 <= round_limit <= 32, 'invalid v20 round_limit')
    require(type(model) is str and model.strip(), 'model required')
    return {'schema_version': 'campaign_config_v20.1', 'round_limit': round_limit,
            'model': model, 'publication': 'ATOMIC_MEMORY_AND_RETAINED_SKILL_V20.1',
            'private_monitor_boundary': 'CALLER_SUPPLIED_GATE_RECEIPT'}


def _skill_ref(text):
    return 'SKILL_V20/' + digest(text)


def _source_manifest():
    root = Path(__file__).resolve().parents[3]
    return {str(p.relative_to(root)): _file_digest(p) for p in sorted((root / 'src/skill_evolution/v20').glob('*v20.py'))}


def _binding(config, run_id, initial_skill):
    require(type(run_id) is str and run_id.strip(), 'run_id required')
    require(type(initial_skill) is str, 'initial Skill required')
    return {'schema_version': 'campaign_binding_v20.1', 'run_id': run_id,
            'initial_skill_sha256': digest(initial_skill), 'config': config,
            'source_files': _source_manifest()}


def _empty_head(run_id, initial_skill, memory_ref):
    return {'schema_version': 'campaign_head_v20.1', 'run_id': run_id, 'revision': 0,
            'round_id': None, 'retained_skill': initial_skill,
            'retained_skill_ref': _skill_ref(initial_skill), 'memory_ref': memory_ref,
            'previous_head_ref': None}


def _head_ref(head):
    return 'CAMPAIGN_HEAD_V20/' + digest(encode(head))


def _write_skill(root, skill):
    ref = _skill_ref(skill)
    path = root / 'skills' / (ref.split('/', 1)[1] + '.md')
    if path.exists():
        require(path.read_text(encoding='utf-8') == skill, 'Skill digest collision')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(skill, encoding='utf-8')
    return ref


def _load_head(root):
    head = _load(root / 'campaign-head.json')
    require(set(head) == {'schema_version', 'run_id', 'revision', 'round_id', 'retained_skill',
        'retained_skill_ref', 'memory_ref', 'previous_head_ref'} and
        head['schema_version'] == 'campaign_head_v20.1', 'invalid v20 campaign head')
    require(head['retained_skill_ref'] == _skill_ref(head['retained_skill']), 'retained Skill digest mismatch')
    return head


def initialize_campaign(*, output, run_id, initial_skill, config=None):
    output = Path(output); config = config or campaign_config_v20()
    require(not output.exists(), 'campaign output already exists')
    pending = output.with_name('.' + output.name + '.initialize-' + uuid.uuid4().hex)
    pending.mkdir(parents=True)
    try:
        _save(pending / 'binding.json', _binding(config, run_id, initial_skill))
        snapshot = initialize_issue_memory(store_dir=pending / 'memory', run_id=run_id)
        _write_skill(pending, initial_skill)
        _save(pending / 'campaign-head.json', _empty_head(run_id, initial_skill, snapshot.memory_ref))
        _save(pending / 'campaign.json', {'schema_version': 'campaign_report_v20.1', 'status': 'READY',
            'committed_rounds': 0, 'rounds': [], 'head_ref': _head_ref(_load_head(pending))})
        pending.rename(output)
    finally:
        if pending.exists():
            import shutil
            shutil.rmtree(pending, ignore_errors=True)
    return _load_head(output)


def _validate_gate(gate, *, run_id, round_id, parent_skill, candidate_skill):
    require(type(gate) is dict and set(gate) >= {'status', 'decision', 'run_id', 'round_id',
        'parent_skill_sha256', 'candidate_skill_sha256'}, 'complete Gate receipt required')
    require(gate['status'] == 'COMPLETE' and gate['decision'] in ('ACCEPT', 'RETAIN'), 'Gate must be ACCEPT or RETAIN')
    require(gate['run_id'] == run_id and gate['round_id'] == round_id, 'Gate round binding mismatch')
    require(gate['parent_skill_sha256'] == digest(parent_skill) and gate['candidate_skill_sha256'] == digest(candidate_skill),
            'Gate Skill binding mismatch')


def commit_v20_round(*, output, round_id, candidate_skill, gate, memory_update, expected_head_ref):
    """Publish Memory and retained Skill with a recoverable two-phase marker.

    A completed Memory revision without a campaign head is an orphan, never a
    visible campaign round. Recovery sees the marker and finishes publication
    only when the new Memory ref and exact Skill match.
    """
    root = Path(output)
    with _lock(root):
        head = _load_head(root); require(_head_ref(head) == expected_head_ref, 'stale campaign head')
        snapshot = load_issue_memory(root / 'memory')
        require(snapshot.memory_ref == head['memory_ref'], 'campaign/Memory head mismatch')
        require(memory_update['run_id'] == head['run_id'] and memory_update['round_id'] == round_id,
                'Memory update round mismatch')
        merged = merge_update(snapshot.memory, memory_update)
        new_memory_ref = 'MEMORY_V20/' + digest(encode(merged))
        retained = candidate_skill if gate['decision'] == 'ACCEPT' else head['retained_skill']
        marker = {'schema_version': 'v20_commit_marker_v20.1', 'round_id': round_id,
            'expected_head_ref': expected_head_ref, 'parent_skill': head['retained_skill'],
            'candidate_skill': candidate_skill, 'retained_skill': retained,
            'gate': gate, 'memory_update': memory_update, 'memory_ref': new_memory_ref}
        pending = root / 'pending-commit.json'
        if pending.exists():
            require(_load(pending) == marker, 'pending commit differs from requested commit')
        else:
            _save(pending, marker)
        # CAS protects ordinary concurrent writers. If the marker was left by a
        # crash after publication, recovery below accepts the already-bound ref.
        if snapshot.memory_ref != new_memory_ref:
            commit_issue_memory_update(store_dir=root / 'memory', update=memory_update,
                                       expected_head_ref=snapshot.memory_ref)
        now = load_issue_memory(root / 'memory')
        require(now.memory_ref == new_memory_ref, 'Memory commit did not publish expected ref')
        skill_ref = _write_skill(root, retained)
        new_head = {'schema_version': 'campaign_head_v20.1', 'run_id': head['run_id'],
            'revision': head['revision'] + 1, 'round_id': round_id, 'retained_skill': retained,
            'retained_skill_ref': skill_ref, 'memory_ref': new_memory_ref,
            'previous_head_ref': _head_ref(head)}
        _save(root / 'campaign-head.json', new_head)
        # Publish a minimal round receipt with the head.  The outer runner may
        # enrich it with generation metadata, but recovery never depends on a
        # post-commit Python frame having survived.
        _save(root / f'round-{head["revision"] + 1:02d}' / 'round-result.json',
              {'round_id': round_id, 'status': 'COMMITTED', 'decision': gate['decision'],
               'memory_ref': new_head['memory_ref'], 'retained_skill_ref': new_head['retained_skill_ref']})
        pending.unlink(missing_ok=True)
        return new_head


def _recover_pending(root):
    pending = root / 'pending-commit.json'
    if not pending.exists():
        return _load_head(root)
    marker = _load(pending); head = _load_head(root)
    if (_head_ref(head) != marker['expected_head_ref'] and head['round_id'] == marker['round_id']
            and head['memory_ref'] == marker['memory_ref'] and head['retained_skill'] == marker['retained_skill']):
        pending.unlink(missing_ok=True)
        return head
    require(_head_ref(head) == marker['expected_head_ref'], 'pending commit expected head is stale')
    now = load_issue_memory(root / 'memory')
    require(now.memory_ref == marker['memory_ref'], 'pending commit Memory is incomplete')
    gate = marker['gate']; retained = marker['retained_skill']
    require(retained == (marker['candidate_skill'] if gate['decision'] == 'ACCEPT' else head['retained_skill']),
            'pending retained Skill mismatch')
    new_head = {'schema_version': 'campaign_head_v20.1', 'run_id': head['run_id'],
        'revision': head['revision'] + 1, 'round_id': marker['round_id'], 'retained_skill': retained,
        'retained_skill_ref': _write_skill(root, retained), 'memory_ref': now.memory_ref,
        'previous_head_ref': _head_ref(head)}
    _save(root / 'campaign-head.json', new_head); pending.unlink()
    return new_head


def campaign_report(root, status='RUNNING', stop_reason=None):
    head = _load_head(root)
    report = {'schema_version': 'campaign_report_v20.1', 'status': status,
        'stop_reason': stop_reason, 'committed_rounds': head['revision'],
        'head_ref': _head_ref(head), 'memory_ref': head['memory_ref'],
        'retained_skill_ref': head['retained_skill_ref'], 'rounds': []}
    for index in range(1, head['revision'] + 1):
        row = _load(root / f'round-{index:02d}' / 'round-result.json')
        report['rounds'].append(row)
    return report


def run_campaign_v20(*, output, run_id, initial_skill, round_factory, post_generation,
                     config=None, transports=None, resume=False, event_hook=None):
    """Run independent v20 rounds.

    ``round_factory(context)`` returns ``{'source': GenerationInput,
    'archive': ..., ...}`` for the current Parent. ``post_generation`` receives
    the verified generation audit and context and returns a trusted Gate receipt
    plus ``memory_update``. Candidate Evolution/Attribution/Monitor stay behind
    this callback and their private artifacts must not be copied into the update.
    """
    config = config or campaign_config_v20(); transports = transports or CampaignTransports()
    root = Path(output)
    with _lock(root.parent):
        if root.exists():
            require(resume, 'existing v20 campaign requires resume')
            require(_load(root / 'binding.json') == _binding(config, run_id, initial_skill), 'campaign binding changed')
            _recover_pending(root)
        else:
            require(not resume, 'resume requires existing v20 campaign')
            initialize_campaign(output=root, run_id=run_id, initial_skill=initial_skill, config=config)
    for _ in range(config['round_limit']):
        with _lock(root):
            _recover_pending(root)
            head = _load_head(root)
            if head['revision'] >= config['round_limit']:
                report = campaign_report(root, 'COMPLETE', 'ROUND_LIMIT'); _save(root / 'campaign.json', report); return report
            index = head['revision'] + 1; round_id = f'round-{index:02d}'
            parent = head['retained_skill']; snapshot = load_issue_memory(root / 'memory')
            root_round = root / round_id
            root_round.mkdir(parents=True, exist_ok=True)
        def event(stage):
            if event_hook: event_hook(stage, round_id)
            _save(root / round_id / 'status.json', {'status': 'RUNNING', 'stage': stage})
        try:
            spec = round_factory({'run_id': run_id, 'round_id': round_id, 'parent_skill': parent,
                'memory': snapshot, 'head': head, 'root': root_round})
            require(type(spec) is dict and isinstance(spec.get('source'), GenerationInput), 'round factory must return GenerationInput')
            source = spec['source']; require(source.payload['parent_skill'] == parent, 'generation Parent differs from campaign head')
            require(source.payload['fusion_input']['memory_ref'] == snapshot.memory_ref, 'generation Memory differs from campaign head')
            event('GENERATION')
            audit = spec.get('generation_audit')
            if audit is None:
                audit = run_local_generation(source=source, output=root_round / 'generation',
                    review_transport=spec.get('review_transport', transports.review),
                    editor_transport=spec.get('editor_transport', transports.editor), model=config['model'])
            require(audit.get('source') == source.payload, 'generation audit source mismatch')
            _, checked_result = restore_generation(audit)
            candidate = checked_result.get('candidate_skill')
            if candidate is None:
                _save(root_round / 'round-result.json', {'round_id': round_id, 'status': audit['result']['status']})
                report = campaign_report(root, 'COMPLETE', audit['result']['status']); _save(root / 'campaign.json', report); return report
            event('POST_GENERATION')
            outcome = post_generation({'run_id': run_id, 'round_id': round_id, 'parent_skill': parent,
                'candidate_skill': candidate, 'audit': audit, 'root': root_round, 'memory': snapshot})
            require(type(outcome) is dict and 'gate' in outcome and 'memory_update' in outcome, 'post_generation result incomplete')
            _validate_gate(outcome['gate'], run_id=run_id, round_id=round_id, parent_skill=parent, candidate_skill=candidate)
            validate_memory(merge_update(snapshot.memory, outcome['memory_update']), run_id=run_id)
            event('COMMIT')
            new_head = commit_v20_round(output=root, round_id=round_id, candidate_skill=candidate,
                gate=outcome['gate'], memory_update=outcome['memory_update'], expected_head_ref=_head_ref(head))
            row = {'round_id': round_id, 'status': 'COMMITTED', 'decision': outcome['gate']['decision'],
                'memory_ref': new_head['memory_ref'], 'retained_skill_ref': new_head['retained_skill_ref'],
                'generation_status': audit['result']['status']}
            _save(root_round / 'round-result.json', row)
            _save(root / 'campaign.json', campaign_report(root, 'RUNNING'))
        except BaseException as exc:
            _save(root / 'campaign.json', {**campaign_report(root, 'INCOMPLETE'),
                'failed_round': round_id, 'error_type': type(exc).__name__, 'message': str(exc)})
            raise
    report = campaign_report(root, 'COMPLETE', 'ROUND_LIMIT'); _save(root / 'campaign.json', report); return report
