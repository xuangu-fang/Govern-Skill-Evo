"""Immutable v19 round archives and one atomic Memory/retained-Skill head.

Private audit storage. Only memory_retrieval_v19 builds learner-facing context.
A Gate receipt is supplied by the trusted Monitor caller, never by a learner.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import uuid

from .edit_tracking_v19 import (DecidedEdits, EditLedger, digest, encode, parse,
                                skill_ref, validate_edit_ledger, trace_edit_history)
from .evolution_replay_v19 import RAW_FILES, _load, _file_digest, _lock, load_candidate_replay
from .attribution_v19 import build_attribution_input
from .attribution_dispatch_v19 import archive_files, load_attribution, load_complete


class MemoryRejected(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise MemoryRejected(message)


def _durable_save(path, value):
    """Same-directory replace is the single publication point; fsync for durability."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('wb') as handle:
        handle.write((encode(value) + '\n').encode('utf-8'))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)
    _sync_directory(path.parent)


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sync_tree(directory):
    for path in directory.rglob('*'):
        if path.is_file():
            with path.open('rb') as handle:
                os.fsync(handle.fileno())
    for path in sorted((p for p in directory.rglob('*') if p.is_dir()), reverse=True):
        _sync_directory(path)
    _sync_directory(directory)


def artifact_ref(identity, payload):
    return {'artifact_id': identity, 'sha256': digest(encode(payload))}


def _round_ref(record):
    return artifact_ref(record['memory_record_id'], record)


def _valid_ref(ref):
    require(type(ref) is dict and set(ref) == {'artifact_id', 'sha256'}
            and type(ref['sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', ref['sha256'])
            and type(ref['artifact_id']) is str and re.fullmatch(r'MEMORY/[0-9a-f]{64}', ref['artifact_id']),
            'invalid memory reference')


@dataclass(frozen=True)
class MemorySnapshot:
    """Private verified snapshot. Do not serialize history/source to a learner."""
    head_json: str
    rounds_json: str
    history: tuple

    @property
    def head(self):
        return parse(self.head_json)

    @property
    def rounds(self):
        return parse(self.rounds_json)


@dataclass(frozen=True)
class _ArchivedBackend:
    manifest_json: str

    def manifest(self):
        return parse(self.manifest_json)


def _archive_files(manifest, attribution_dir):
    names = ['backend.json', 'gate.json', 'ledger_input.json', 'ledger.json']
    for role in ('parent', 'candidate'):
        names.extend(role + '/' + name for name in ('input.json', 'state.json'))
        for i in range(len(manifest['task_ids'])):
            names.extend(f'{role}/tasks/T{i+1:03d}/' + name for name in
                         (*RAW_FILES, 'raw_complete.json', 'evaluation.json', 'checkpoint.json'))
    names.extend('candidate/learner/' + name for name in ('pairs.json', 'validation.json'))
    names.extend('attribution/' + name for name in archive_files(attribution_dir))
    return names


def _gate(ledger, gate):
    payload = ledger.payload
    require(type(gate) is dict and set(gate) == {
        'status', 'decision', 'run_id', 'round_id', 'parent_skill_sha256', 'candidate_skill_sha256'},
        'Gate requires an exact completed, version-bound receipt without scores')
    require(gate['status'] == 'COMPLETE' and gate['decision'] in ('ACCEPT', 'RETAIN')
            and gate['run_id'] == payload['run_id'] and gate['round_id'] == payload['round_id']
            and gate['parent_skill_sha256'] == payload['parent_skill_ref']['sha256']
            and gate['candidate_skill_sha256'] == payload['candidate_skill_ref']['sha256'],
            'Gate receipt incomplete or bound to a different candidate')


def _record(ledger, replay, attribution, gate, previous, audit):
    _gate(ledger, gate)
    data = ledger.payload
    body = {'schema_version': 'round_memory_v19.1', 'run_id': data['run_id'], 'round_id': data['round_id'],
            'previous_memory_ref': previous, 'parent_skill_ref': data['parent_skill_ref'],
            'candidate_skill_ref': data['candidate_skill_ref'],
            'edit_refs': [artifact_ref(e['edit_id'], e) for e in data['edits']],
            'replay_pair_refs': [artifact_ref(p['pair_id'], p) for p in replay['pairs']],
            'attribution_refs': [artifact_ref(a['attribution_id'], a) for a in attribution['records']],
            'gate_decision': gate['decision'],
            'retained_skill_ref': data['candidate_skill_ref' if gate['decision'] == 'ACCEPT' else 'parent_skill_ref'],
            'audit_sha256': digest(encode(audit))}
    return {**body, 'memory_record_id': 'MEMORY/' + digest(encode(body))}


def _read_archive(directory, record, history):
    audit = _load(directory / 'audit.json')
    require(type(audit) is dict and digest(encode(audit)) == record['audit_sha256'], 'audit manifest mismatch')
    manifest = _load(directory / 'backend.json')
    require(set(audit) == set(_archive_files(manifest, directory / 'attribution')), 'incomplete audit coverage')
    for name, sha in audit.items():
        require(_file_digest(directory / name) == sha, 'archived artifact changed: ' + name)
    ledger = EditLedger(encode(_load(directory / 'ledger_input.json')), encode(_load(directory / 'ledger.json')))
    validate_edit_ledger(ledger, history=history)
    backend = _ArchivedBackend(encode(manifest))
    replay = load_candidate_replay(ledger, backend=backend, parent_dir=directory / 'parent',
                                   artifact_dir=directory / 'candidate', history=history).payload
    learner_input = build_attribution_input(ledger, backend=backend, parent_dir=directory / 'parent',
                                            replay_dir=directory / 'candidate', history=history)
    # Preserve the historical Prompt/config. A code update cannot rewrite old
    # provenance or force historical model calls. Revalidate response semantics
    # supported by the current deterministic structural/reference validator.
    attribution = load_complete(directory / 'attribution', learner_input).payload
    gate = _load(directory / 'gate.json')
    expected = _record(ledger, replay, attribution, gate, record['previous_memory_ref'], audit)
    require(record == expected, 'memory record differs from revalidated evidence')
    return ledger, replay, attribution, manifest


def _head(genesis, records, current, manifest):
    return {'schema_version': 'memory_head_v19.1', 'run_id': genesis['run_id'],
            'genesis_sha256': digest(encode(genesis)), 'revision': len(records),
            'memory_ref': _round_ref(records[-1]) if records else None,
            'retained_skill': current, 'retained_skill_ref': skill_ref(current),
            'replay_manifest_sha256': digest(encode(manifest)) if manifest is not None else None}


def load_memory(store_dir):
    """Read only the committed head chain; pending/orphan archives are invisible."""
    root = Path(store_dir)
    try:
        genesis, head = _load(root / 'genesis.json'), _load(root / 'head.json')
        require(type(genesis) is dict and set(genesis) == {'schema_version', 'run_id', 'initial_skill'}
                and genesis['schema_version'] == 'memory_genesis_v19.1'
                and type(genesis['run_id']) is str and bool(genesis['run_id'].strip())
                and type(genesis['initial_skill']) is str, 'invalid memory genesis')
        records, seen, cursor = [], set(), head['memory_ref']
        while cursor is not None:
            _valid_ref(cursor)
            require(cursor['sha256'] not in seen, 'cyclic memory chain')
            seen.add(cursor['sha256'])
            record = _load(root / 'rounds' / cursor['sha256'] / 'record.json')
            require(_round_ref(record) == cursor, 'memory record digest mismatch')
            records.append(record)
            cursor = record['previous_memory_ref']
        records.reverse()
        history, loaded, rounds_seen = (), [], set()
        current, manifest = genesis['initial_skill'], None
        for record in records:
            require(record['run_id'] == genesis['run_id'] and record['round_id'] not in rounds_seen,
                    'wrong run or repeated round')
            rounds_seen.add(record['round_id'])
            ledger, replay, attribution, active_manifest = _read_archive(
                root / 'rounds' / _round_ref(record)['sha256'], record, history)
            require(ledger.source['editor']['parent_skill'] == current, 'retained Parent chain mismatch')
            if manifest is not None:
                require(active_manifest == manifest, 'Evolution manifest drift across memory rounds')
            manifest = active_manifest
            history += (DecidedEdits(ledger, record['gate_decision']),)
            if record['gate_decision'] == 'ACCEPT':
                current = ledger.source['candidate_skill']
            loaded.append({'record': record, 'edits': ledger.payload['edits'],
                           'source_evidence': ledger.payload['evidence'],
                           'parent_skill': ledger.source['editor']['parent_skill'],
                           'candidate_skill': ledger.source['candidate_skill'],
                           'replay': replay, 'attribution': attribution})
            if 'generation_audit' in ledger.source:
                audit = ledger.source['generation_audit']
                loaded[-1]['generation_reviews'] = {
                    'generation_audit_sha256': ledger.payload['generation_audit_sha256'],
                    'historical_reviews': audit['historical_reviews']['reviews'],
                    **({'issues':audit['issue_fusion']['issues'],
                        'evidence_reviews':[r['result'] for r in audit['evidence_reviews']]}
                       if audit['schema_version']=='local_generation_v19.1' else {'decisions': audit['reconciliation']['decisions']}),
                    'current_findings': [{k:v for k,v in f.items() if k != 'raw_response'} for f in audit['current_findings']]}
        require(head == _head(genesis, records, current, manifest), 'atomic head/Skill binding mismatch')
        return MemorySnapshot(encode(head), encode(loaded), history)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, MemoryRejected):
            raise
        raise MemoryRejected('cannot verify memory: ' + type(exc).__name__) from exc


def initialize_memory(*, store_dir, run_id, initial_skill):
    require(type(run_id) is str and bool(run_id.strip()) and type(initial_skill) is str,
            'run identity and exact initial Skill required')
    root = Path(store_dir)
    genesis = {'schema_version': 'memory_genesis_v19.1', 'run_id': run_id, 'initial_skill': initial_skill}
    with _lock(root):
        if root.exists():
            snapshot = load_memory(root)
            require(_load(root / 'genesis.json') == genesis, 'existing memory has different genesis')
            return snapshot
        pending = root.with_name('.' + root.name + '.initialize-' + uuid.uuid4().hex)
        pending.mkdir(parents=True)
        _durable_save(pending / 'genesis.json', genesis)
        _durable_save(pending / 'head.json', _head(genesis, [], initial_skill, None))
        pending.rename(root)
        _sync_directory(root.parent)
    return load_memory(root)


def commit_round_memory(ledger, *, store_dir, expected_head_ref, backend, parent_dir,
                        replay_dir, attribution_dir, gate_result):
    """Append all evidence for ACCEPT or RETAIN; atomically publish head + Skill.

    Repeating the same round/evidence/decision is idempotent even after later
    commits. Stale new writes fail CAS. The caller must supply a trusted, completed
    Monitor projection; this module cannot attest that an external Gate ran.
    """
    root = Path(store_dir)
    with _lock(root):
        snapshot = load_memory(root)
        payload = ledger.payload
        _gate(ledger, gate_result)
        prior = next((i for i, r in enumerate(snapshot.rounds)
                      if r['record']['round_id'] == payload['round_id']), None)
        prefix = snapshot.history if prior is None else snapshot.history[:prior]
        previous = snapshot.head['memory_ref'] if prior is None else snapshot.rounds[prior]['record']['previous_memory_ref']
        require(expected_head_ref == previous, 'stale expected memory head')
        validate_edit_ledger(ledger, history=prefix)
        current = (_load(root / 'genesis.json')['initial_skill'] if not prefix
                   else trace_edit_history(prefix)['current_skill'])
        require(payload['run_id'] == snapshot.head['run_id']
                and ledger.source['editor']['parent_skill'] == current, 'new round Parent/run mismatch')
        # Verify originals before snapshot, then independently verify the copy.
        verified_attribution = load_attribution(ledger, backend=backend, parent_dir=parent_dir, replay_dir=replay_dir,
                                                artifact_dir=attribution_dir, history=prefix)
        manifest = backend.manifest()
        if snapshot.head['replay_manifest_sha256'] is not None:
            require(digest(encode(manifest)) == snapshot.head['replay_manifest_sha256'], 'Evolution manifest drift')
        pending = root / 'pending' / uuid.uuid4().hex
        pending.mkdir(parents=True)
        _durable_save(pending / 'backend.json', manifest)
        _durable_save(pending / 'gate.json', gate_result)
        _durable_save(pending / 'ledger_input.json', ledger.source)
        _durable_save(pending / 'ledger.json', payload)
        sources = {'parent': Path(parent_dir), 'candidate': Path(replay_dir), 'attribution': Path(attribution_dir)}
        for name in _archive_files(manifest, attribution_dir):
            if '/' not in name:
                continue
            role, suffix = name.split('/', 1)
            target = pending / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(sources[role] / suffix, target)
        audit = {name: _file_digest(pending / name) for name in _archive_files(manifest, attribution_dir)}
        _durable_save(pending / 'audit.json', audit)
        replay = _load(pending / 'candidate/learner/pairs.json')
        attribution = _load(pending / 'attribution/attributions.json')
        record = _record(ledger, replay, attribution, gate_result, previous, audit)
        _read_archive(pending, record, prefix)
        copied_input = build_attribution_input(ledger, backend=_ArchivedBackend(encode(manifest)),
            parent_dir=pending / 'parent', replay_dir=pending / 'candidate', history=prefix)
        require(encode(attribution) == verified_attribution.payload_json
                and load_complete(pending / 'attribution', copied_input) == verified_attribution,
                'attribution changed during snapshot')
        if prior is not None:
            require(record == snapshot.rounds[prior]['record'], 'committed round conflicts with supplied evidence')
            shutil.rmtree(pending)
            return _round_ref(record)
        _durable_save(pending / 'record.json', record)
        _sync_tree(pending)
        ref = _round_ref(record)
        destination = root / 'rounds' / ref['sha256']
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            # Complete archive left behind by interruption before head publication.
            require(_load(destination / 'record.json') == record, 'orphan record conflict')
            _read_archive(destination, record, prefix)
            shutil.rmtree(pending)
        else:
            pending.rename(destination)
            _sync_directory(destination.parent)
        current = ledger.source['candidate_skill'] if gate_result['decision'] == 'ACCEPT' else current
        _durable_save(root / 'head.json', _head(_load(root / 'genesis.json'),
            [r['record'] for r in snapshot.rounds] + [record], current, manifest))
        return ref
