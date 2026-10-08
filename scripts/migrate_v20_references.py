"""Copy a v20 Pilot and verify its cross-round reference repair without model calls."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import shutil
import socket
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/tau2-bench/src')]

from src.skill_evolution.edit_tracking_v19 import encode, digest
from src.skill_evolution.evolution_replay_v19 import _load, _save, _file_digest
from src.skill_evolution.campaign_v20 import _binding, _load_head, run_campaign_v20
from src.skill_evolution.issue_memory_v20 import load_issue_memory
from src.skill_evolution.local_generation_v20 import GenerationInput, review_inputs, restore_generation
from src.skill_evolution.evidence_review_v20 import build_evidence_review_request

REPAIR_FILES = {'src/skill_evolution/runtime_v20.py',
                'src/skill_evolution/evidence_review_v20.py'}
DERIVED_FILES = {'round-02/evidence-archive.json', 'round-02/generation-input.json'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'symlink in Pilot: ' + str(path))
        if path.is_file():
            result[str(path.relative_to(root))] = _file_digest(path)
    return result


def check_binding_change(old, new):
    require({k: v for k, v in old.items() if k != 'source_files'} ==
            {k: v for k, v in new.items() if k != 'source_files'},
            'migration cannot change run identity, initial Skill or config')
    require(old['source_files'].keys() == new['source_files'].keys(),
            'unexpected source file addition/removal')
    changes = {p: {'before': old['source_files'][p], 'after': new['source_files'][p]}
               for p in old['source_files'] if old['source_files'][p] != new['source_files'][p]}
    require(changes and changes.keys() <= REPAIR_FILES, 'source changes exceed reference repair scope')
    return changes


def check_preserved(before, after, allowed=()):
    changed = [p for p, sha in before.items() if p not in allowed and after.get(p) != sha]
    require(not changed, 'preserved artifacts changed: ' + ', '.join(changed[:10]))


def validate_committed_round(root):
    head = _load_head(root)
    memory = load_issue_memory(root / 'memory')
    require(head['revision'] == 1 and head['round_id'] == 'round-01',
            'this migration requires exactly one committed round')
    require(head['memory_ref'] == memory.memory_ref, 'Memory/head mismatch')
    require(not (root / 'pending-commit.json').exists(), 'pending commit must be recovered first')
    receipt = _load(root / 'round-01/round-result.json')
    require(receipt['status'] == 'COMMITTED' and receipt['memory_ref'] == memory.memory_ref and
            receipt['retained_skill_ref'] == head['retained_skill_ref'], 'committed receipt mismatch')
    audit = _load(root / 'round-01/generation/generation-audit.json')
    _, result = restore_generation(audit)
    expected = result['candidate_skill'] if receipt['decision'] == 'ACCEPT' else audit['source']['parent_skill']
    require(expected == head['retained_skill'], 'committed Skill differs from generation')
    gate = _load(root / 'round-01/monitor_private/receipt.json')
    require(gate['status'] == 'COMPLETE' and gate['decision'] == receipt['decision'] and
            gate['run_id'] == head['run_id'] and gate['round_id'] == head['round_id'] and
            gate['parent_skill_sha256'] == digest(audit['source']['parent_skill']) and
            gate['candidate_skill_sha256'] == digest(result['candidate_skill']), 'Gate receipt mismatch')
    return head, memory


class OfflineBackend:
    """Allow manifest/checkpoint reads but never create a new rollout."""
    def __init__(self, backend):
        self.backend = backend

    def manifest(self):
        return self.backend.manifest()

    def prepare(self, *args, **kwargs):
        raise RuntimeError('offline preflight forbids a new rollout')


def preflight(root, adapter):
    from dataclasses import replace
    from src.skill_evolution.runtime_v20 import build_v20_round_factory, V20RuntimeTransports
    head, memory = validate_committed_round(root)
    require(not (root / 'round-02/generation').exists(), 'Evidence Review has already started')
    require(not (root / 'round-02/round-result.json').exists(), 'second round already has a result')
    binding = _load(root / 'binding.json')
    denied = []

    def deny(*args, **kwargs):
        denied.append(True)
        raise RuntimeError('offline preflight forbids model/network calls')

    class ReadyForReview(Exception):
        pass

    report = {}
    def stop(stage, round_id):
        require(stage == 'GENERATION' and round_id == 'round-02', 'unexpected recovery position')
        source = GenerationInput(encode(_load(root / round_id / 'generation-input.json')))
        packets = review_inputs(source)
        require(packets, 'no Evidence Review requests to resume')
        require(source.payload['memory'] == memory.memory and
                source.payload['parent_skill'] == head['retained_skill'], 'recovery source mismatch')
        archive = source.payload['archive']
        sources = {r for i in memory.memory['issues'] for r in i['source_refs']}
        edits = set()
        for issue in memory.memory['issues']:
            for attempt in issue['attempts']:
                sources.update(attempt['source_refs'])
                edits.update(attempt['edit_refs'])
        require(sources <= archive['records'].keys(), 'unresolved Memory source')
        require(edits <= archive['edits'].keys(), 'unresolved Memory edit')
        require(all(set(r['evidence_refs'] + r['counterevidence_refs']) <= archive['events'].keys()
                    for r in archive['records'].values()), 'unresolved original event')
        prompts = [build_evidence_review_request(packet) for packet in packets]
        report.update(status='PASS', model_calls=0, rollout_calls=0,
                      next_model_call='round-02/generation/review-0-request.json',
                      reused_stages=['Parent Evolution', 'Grouping', 'Current Diagnosis', 'Issue Fusion'],
                      generation_input_ref=source.input_ref,
                      memory_source_refs_resolved=len(sources), memory_edit_refs_resolved=len(edits),
                      archive_records=len(archive['records']), archive_events=len(archive['events']),
                      review_packet_count=len(packets),
                      review_packets=[{'input_ref': p.input_ref,
                                       'source_records': len(p.payload['source_records']),
                                       'historical_edits': len(p.payload['historical_edits']),
                                       'events': len(p.payload['events']),
                                       'request_sha256': digest(encode(prompt))}
                                      for p, prompt in zip(packets, prompts)])
        raise ReadyForReview()

    campaign_bytes = (root / 'campaign.json').read_bytes()
    offline = replace(adapter, evolution=OfflineBackend(adapter.evolution))
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(socket.socket, 'connect', deny))
            stack.enter_context(patch.object(socket.socket, 'connect_ex', deny))
            stack.enter_context(patch.object(socket, 'create_connection', deny))
            transports = V20RuntimeTransports(**{k: deny for k in V20RuntimeTransports.__dataclass_fields__})
            try:
                run_campaign_v20(output=root, run_id=binding['run_id'], initial_skill=adapter.initial_skill,
                    round_factory=build_v20_round_factory(benchmark=offline, transports=transports),
                    post_generation=deny, config=binding['config'], resume=True, event_hook=stop)
            except ReadyForReview:
                pass
            else:
                raise ValueError('preflight did not stop before Evidence Review')
    finally:
        (root / 'campaign.json').write_bytes(campaign_bytes)
    require(report.get('status') == 'PASS' and not denied, 'offline preflight failed')
    require(not (root / 'round-02/generation').exists(), 'preflight created generation directory')
    return report


def migrate(source, output, config):
    from src.skill_evolution.benchmark_adapter_v20 import BenchmarkAdapterV20
    source, output, config = source.resolve(), output.resolve(), config.resolve()
    require(source.is_dir() and not output.exists(), 'source must exist and output must be new')
    require(not output.is_relative_to(source), 'output cannot be inside source')
    original = inventory(source)
    adapter = BenchmarkAdapterV20.from_config(config)
    old = _load(source / 'binding.json')
    new = _binding(old['config'], old['run_id'], adapter.initial_skill)
    from src.skill_evolution.campaign_v20 import campaign_config_v20
    require(old['config'] == campaign_config_v20(round_limit=adapter.config['round_limit'],
            model=adapter.config['model']), 'frozen configuration differs')
    changes = check_binding_change(old, new)
    validate_committed_round(source)
    require(not (source / 'round-02/generation').exists(), 'Evidence Review already started')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.v20-reference-migration-', dir=output.parent) as work:
        copy = Path(work) / 'pilot'
        shutil.copytree(source, copy)
        require(inventory(copy) == original, 'Pilot copy is not identical')
        audit = copy / 'migration'
        require(not audit.exists(), 'source already has a migration')
        audit.mkdir()
        shutil.copy2(copy / 'binding.json', audit / 'original-binding.json')
        _save(audit / 'source-artifacts.json', original)
        for name, sha in new['source_files'].items():
            require(_file_digest(ROOT / name) == sha, 'source changed during migration')
            destination = audit / 'implementation' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, destination)
        _save(copy / 'binding.json', new)
        report = preflight(copy, adapter)
        after = inventory(copy)
        check_preserved(original, after, {'binding.json'} | DERIVED_FILES)
        require(inventory(source) == original, 'original Pilot changed during migration')
        _save(audit / 'preflight.json', report)
        _save(audit / 'receipt.json', {
            'schema_version': 'v20_reference_migration.1', 'status': 'VERIFIED',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'source': str(source), 'output': str(output), 'run_id': old['run_id'],
            'reason': 'Restore historical Finding records and edit references for round-02 Evidence Review',
            'claim_boundary': 'ENGINEERING_PILOT_WITH_EXPLICIT_CODE_REPAIR',
            'resume_round': 'round-02', 'resume_stage': 'EVIDENCE_REVIEW',
            'original_binding': old, 'resume_binding': new, 'source_changes': changes,
            'config_path': str(config), 'config_sha256': _file_digest(config),
            'migration_script_sha256': _file_digest(Path(__file__)),
            'source_inventory_sha256': digest(encode(original)),
            'preserved_file_count': len(original.keys() - ({'binding.json'} | DERIVED_FILES)),
            'original_unchanged': True, 'committed_round_unchanged': True,
            'derived_files': sorted(DERIVED_FILES), 'preflight_sha256': digest(encode(report)),
        })
        require(_binding(old['config'], old['run_id'], adapter.initial_skill) == new,
                'source code changed during preflight')
        copy.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=ROOT / 'experiments/configs/v20_pilot_001/config.json')
    args = parser.parse_args()
    print(encode(migrate(args.source, args.output, args.config)))


if __name__ == '__main__':
    main()
