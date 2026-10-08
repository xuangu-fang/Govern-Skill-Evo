"""Repair a completed v20 Pilot's Memory without replaying model calls.

The repair is an explicit artifact migration. It rewrites only stale Memory
source bindings and explanatory fields, then rebinds the campaign head to the
new Memory revision. Candidate Skills, Gate receipts, edits, and benchmark
outputs are copied byte-for-byte and checked.
"""
from copy import deepcopy
from datetime import datetime, timezone
import argparse
from pathlib import Path
import shutil
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/tau2-bench/src')]

from src.skill_evolution.edit_tracking_v19 import encode, digest
from src.skill_evolution.evolution_replay_v19 import _file_digest, _load, _save
from src.skill_evolution.campaign_v20 import _binding, _head_ref, campaign_config_v20
from src.skill_evolution.benchmark_adapter_v20 import BenchmarkAdapterV20, DEFAULT_CONFIG
from src.skill_evolution.issue_memory_v20 import (_head, _write, load_issue_memory,
                                                   validate_memory)
from src.skill_evolution.runtime_v20 import _saved_round_archive
from src.skill_evolution.evidence_review_v20 import merge_evidence_archives


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


def _rounds(root):
    rows = []
    for path in sorted(root.glob('round-*')):
        if not path.is_dir():
            continue
        try:
            number = int(path.name.rsplit('-', 1)[1])
        except (ValueError, IndexError):
            continue
        rows.append((number, path))
    return rows


def _repair_index(root):
    """Index saved edits, Fusion proposals, reviews and replay observations."""
    edits = {}
    for number, round_root in _rounds(root):
        audit_path = round_root / 'generation' / 'generation-audit.json'
        if not audit_path.exists():
            continue
        audit = _load(audit_path)
        result = audit.get('result', {})
        fusion = _load(round_root / 'issue-fusion-result.json')
        proposals = [p for p in fusion.get('issues', []) if p.get('decision') == 'PROPOSE']
        reviews = {r['proposal_id']: r for r in audit.get('reviews', [])
                   if isinstance(r, dict) and r.get('proposal_id')}
        candidate = _load(round_root / 'candidate_evolution' / 'candidate-summary.json')
        gate = _load(round_root / 'monitor_private' / 'receipt.json')
        for edit in result.get('edits', []):
            matching = [p for p in proposals
                        if set(edit.get('memory_issue_refs', [])) & set(p.get('memory_issue_refs', []))
                        or set(edit.get('current_finding_refs', [])) & set(p.get('current_finding_refs', []))]
            edits[edit['edit_id']] = {
                'round_id': f'round-{number:02d}', 'edit': edit,
                'proposals': matching, 'reviews': [reviews[p['proposal_issue_id']]
                                                   for p in matching if p['proposal_issue_id'] in reviews],
                'candidate': candidate, 'gate': gate,
            }
    require(edits, 'no saved edits found for Memory repair')
    return edits


def _compact(value, limit):
    text = ' '.join(str(value or '').split())
    return text if len(text) <= limit else text[:limit - 1] + '…'


def _repair_memory(memory, index):
    repaired = deepcopy(memory)
    changes = []
    for issue in repaired['issues']:
        for attempt in issue['attempts']:
            metadata = [index[ref] for ref in attempt['edit_refs'] if ref in index]
            require(metadata, 'Memory attempt has no saved edit: ' + attempt['attempt_id'])
            source_refs = []
            for item in metadata:
                edit = item['edit']
                refs = list(edit.get('current_finding_refs', []))
                if not refs:
                    refs = [p['proposal_issue_id'] for p in item['proposals']]
                if not refs:
                    refs = [issue['issue_id']]
                for ref in refs:
                    if ref not in source_refs:
                        source_refs.append(ref)
            old_sources = list(attempt['source_refs'])
            if any(ref.startswith('GENERATION/') for ref in old_sources):
                attempt['source_refs'] = source_refs
                changes.append({'issue_id': issue['issue_id'], 'attempt_id': attempt['attempt_id'],
                                'old_source_refs': old_sources, 'new_source_refs': source_refs})

            # Backfill the existing fields from already-saved artifacts. This
            # changes no experiment result; it makes the durable Memory useful
            # to the next Fusion request.
            first = metadata[0]
            edit = first['edit']
            approach = _compact(edit.get('after_text'), 700)
            if approach:
                approach = edit['operation'] + ' Parent guidance: ' + approach
            else:
                approach = edit['operation'] + ' selected Parent rule'
            candidate = first['candidate']
            replay = ''
            if candidate.get('task_count'):
                replay = (f"Candidate replay observed success {candidate.get('success_count')}/"
                          f"{candidate.get('task_count')}, compliance {candidate.get('compliance_count')}/"
                          f"{candidate.get('task_count')}; ")
            review = first['reviews'][0] if first['reviews'] else None
            review_note = ''
            if review:
                review_note = ('Evidence Review ' + review['verdict'] + ': ' +
                               _compact(review['reason'], 420) + '; ')
                if isinstance(review.get('gap'), dict) and review['gap'].get('statement'):
                    review_note += 'reviewed gap: ' + _compact(review['gap']['statement'], 300) + '; '
            assessment = _compact(replay + review_note +
                                  'private Gate decision was ' + first['gate']['decision'] +
                                  '; edit-specific effect remains unresolved.', 1000)
            if attempt['approach'] != approach or attempt['assessment'] != assessment:
                changes.append({'issue_id': issue['issue_id'], 'attempt_id': attempt['attempt_id'],
                                'fields': ['approach', 'assessment']})
                attempt['approach'] = approach
                attempt['assessment'] = assessment
    validate_memory(repaired, run_id=memory['run_id'])
    return repaired, changes


def _write_memory_migration(root, repaired):
    current = load_issue_memory(root / 'memory')
    require(current.memory_ref != 'MEMORY_V20/' + digest(encode(repaired)),
            'Memory already repaired or unchanged')
    new_ref = 'MEMORY_V20/' + digest(encode(repaired))
    _write(root / 'memory' / 'revisions' / new_ref.split('/', 1)[1] / 'memory.json', repaired)
    _write(root / 'memory' / 'head.json', _head(current.head['run_id'], current.head['revision'] + 1,
                                                repaired, current.memory_ref))
    return current.memory_ref, new_ref


def migrate(source, output, *, round_limit=4, config_path=DEFAULT_CONFIG):
    source, output = Path(source).resolve(), Path(output).resolve()
    require(source.is_dir() and not output.exists(), 'source must exist and output must be new')
    require(not output.is_relative_to(source), 'output cannot be inside source')
    original = inventory(source)
    binding = _load(source / 'binding.json')
    adapter = BenchmarkAdapterV20.from_config(config_path)
    old_head = _load(source / 'campaign-head.json')
    require(old_head['revision'] >= 2, 'completed two-round Pilot required')
    source_memory = load_issue_memory(source / 'memory').memory
    index = _repair_index(source)
    with tempfile.TemporaryDirectory(prefix='.v20-completed-memory-repair-', dir=output.parent) as work:
        copy = Path(work) / 'pilot'
        shutil.copytree(source, copy)
        repaired, changes = _repair_memory(source_memory, index)
        old_memory_ref, new_memory_ref = _write_memory_migration(copy, repaired)

        # Rebind the campaign for continuation. The frozen benchmark remains
        # unchanged; only the campaign's allowed future round limit changes.
        new_config = campaign_config_v20(round_limit=round_limit, model=binding['config']['model'])
        new_binding = _binding(new_config, binding['run_id'], adapter.initial_skill)
        _save(copy / 'binding.json', new_binding)
        head = _load(copy / 'campaign-head.json')
        head['memory_ref'] = new_memory_ref
        _save(copy / 'campaign-head.json', head)
        receipt = _load(copy / 'round-02/round-result.json')
        receipt['memory_ref'] = new_memory_ref
        _save(copy / 'round-02/round-result.json', receipt)
        report = _load(copy / 'campaign.json')
        report.update(status='RUNNING', stop_reason=None, memory_ref=new_memory_ref,
                      head_ref=_head_ref(head))
        _save(copy / 'campaign.json', report)

        # Structural preflight: every Memory source and edit must resolve in
        # the merged historical archive, without running a model or rollout.
        archives = [_saved_round_archive(path) for _, path in _rounds(copy)]
        archive = merge_evidence_archives(*[a for a in archives if a is not None])
        sources = {r for issue in repaired['issues'] for r in issue['source_refs']}
        edits = {r for issue in repaired['issues'] for attempt in issue['attempts'] for r in attempt['edit_refs']}
        for issue in repaired['issues']:
            for attempt in issue['attempts']:
                sources.update(attempt['source_refs'])
        require(sources <= archive.payload['records'].keys(), 'unresolved migrated Memory source')
        require(edits <= archive.payload['edits'].keys(), 'unresolved migrated Memory edit')
        preflight = {'schema_version': 'v20_completed_memory_preflight.1', 'status': 'PASS',
                     'model_calls': 0, 'rollout_calls': 0, 'next_model_call': 'round-03/current-000',
                     'memory_source_refs_resolved': len(sources), 'memory_edit_refs_resolved': len(edits),
                     'archive_records': len(archive.payload['records']),
                     'archive_events': len(archive.payload['events']),
                     'repaired_attempt_count': len(changes), 'new_memory_ref': new_memory_ref,
                     'next_round_limit': round_limit}
        migration_dir = copy / 'migration'
        _save(migration_dir / 'continuation-preflight.json', preflight)
        _save(migration_dir / 'continuation-receipt.json', {
            'schema_version': 'v20_completed_memory_migration.1', 'status': 'VERIFIED',
            'created_at': datetime.now(timezone.utc).isoformat(), 'source': str(source),
            'output': str(output), 'run_id': binding['run_id'],
            'reason': 'Repair stale Memory source bindings after completed two-round Pilot',
            'claim_boundary': 'NO_MODEL_CALLS; COMMITTED_SKILL_AND_GATE_RESULTS_UNCHANGED',
            'old_memory_ref': old_memory_ref, 'new_memory_ref': new_memory_ref,
            'old_campaign_config': binding['config'], 'new_campaign_config': new_config,
            'changed_attempts': changes, 'preflight': preflight,
            'source_inventory_sha256': digest(encode(original)),
            'original_unchanged': inventory(source) == original,
        })
        after = inventory(copy)
        allowed = {'binding.json', 'campaign-head.json', 'campaign.json', 'round-02/round-result.json',
                   'memory/head.json', 'memory/revisions/' + new_memory_ref.split('/', 1)[1] + '/memory.json',
                   'migration/continuation-preflight.json', 'migration/continuation-receipt.json'}
        changed = [p for p, sha in original.items() if p not in allowed and after.get(p) != sha]
        require(not changed, 'committed artifacts changed: ' + ', '.join(changed[:10]))
        require(inventory(source) == original, 'original Pilot changed during migration')
        copy.rename(output)
    return preflight


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--round-limit', type=int, default=4)
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(encode(migrate(args.source, args.output, round_limit=args.round_limit,
                         config_path=args.config)))


if __name__ == '__main__':
    main()
