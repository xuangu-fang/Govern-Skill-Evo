"""Migrate an interrupted v20 Grouping checkpoint to the 24K budget."""
from datetime import datetime, timezone
import argparse
from pathlib import Path
import shutil
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/tau2-bench/src')]

from src.skill_evolution.benchmark_adapter_v20 import BenchmarkAdapterV20, DEFAULT_CONFIG
from src.skill_evolution.campaign_v20 import _binding
from src.skill_evolution.edit_tracking_v19 import encode, digest
from src.skill_evolution.evolution_replay_v19 import _file_digest, _load, _save
from src.skill_evolution.grouping_campaign_v20 import (
    GROUPING_MAX_COMPLETION_TOKENS, GROUPING_REASONING_EFFORT,
)


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


def migrate(source, output, *, config_path=DEFAULT_CONFIG):
    source, output = Path(source).resolve(), Path(output).resolve()
    require(source.is_dir() and not output.exists(), 'source must exist and output must be new')
    require(not output.is_relative_to(source), 'output cannot be inside source')
    original = inventory(source)
    binding = _load(source / 'binding.json')
    adapter = BenchmarkAdapterV20.from_config(config_path)
    grouping = source / 'round-03' / 'grouping'
    input_path = grouping / 'input.json'
    validation_path = grouping / 'validation.json'
    require(input_path.exists() and validation_path.exists(), 'round-03 Grouping checkpoint is missing')
    old_input = _load(input_path)
    old_validation = _load(validation_path)
    require(old_validation.get('status') == 'INCOMPLETE', 'Grouping is not an interrupted checkpoint')
    old_request = old_input['request']
    require(old_request.get('model') == 'deepseek-v4-pro', 'unexpected Grouping model')
    require(old_request.get('reasoning_effort') == 'high' and
            old_request.get('max_completion_tokens') == 16_000,
            'checkpoint is not the original 16K high-reasoning request')

    with tempfile.TemporaryDirectory(prefix='.v20-grouping-budget-', dir=output.parent) as work:
        copy = Path(work) / 'pilot'
        shutil.copytree(source, copy)
        current_input = _load(copy / 'round-03/grouping/input.json')
        new_request = dict(current_input['request'])
        new_request['reasoning_effort'] = GROUPING_REASONING_EFFORT
        new_request['max_completion_tokens'] = GROUPING_MAX_COMPLETION_TOKENS
        current_input['request'] = new_request
        _save(copy / 'round-03/grouping/input.json', current_input)

        archived = []
        for path in sorted((copy / 'round-03/grouping').glob('attempt-1*')):
            if not path.is_dir():
                continue
            target = path.with_name('archived-' + path.name)
            if target.exists():
                target = path.with_name('archived-' + path.name + '-' + digest(str(path))[:8])
            path.rename(target)
            archived.append({'from': path.name, 'to': target.name})
        require(archived, 'no failed Grouping attempts found to archive')
        _save(copy / 'round-03/grouping/validation.json', {
            'status': 'INCOMPLETE', 'error_type': 'GroupingBudgetMigrated',
            'previous_status': old_validation,
        })

        # Runtime source binding changes are explicit; campaign identity and
        # configuration remain unchanged.
        new_binding = _binding(binding['config'], binding['run_id'], adapter.initial_skill)
        _save(copy / 'binding.json', new_binding)
        receipt = {
            'schema_version': 'v20_grouping_budget_migration.1',
            'status': 'VERIFIED', 'created_at': datetime.now(timezone.utc).isoformat(),
            'source': str(source), 'output': str(output), 'run_id': binding['run_id'],
            'reason': 'Increase v20 Grouping completion ceiling after repeated high-reasoning truncation',
            'claim_boundary': 'NO_MODEL_CALLS; PRIOR_PARENT_AND_MEMORY_ARTIFACTS_UNCHANGED',
            'old_request_sha256': digest(encode(old_request)),
            'new_request_sha256': digest(encode(new_request)),
            'old_reasoning_effort': old_request['reasoning_effort'],
            'new_reasoning_effort': new_request['reasoning_effort'],
            'old_max_completion_tokens': old_request['max_completion_tokens'],
            'new_max_completion_tokens': new_request['max_completion_tokens'],
            'archived_attempts': archived, 'next_model_call': 'round-03/grouping/attempt-1',
            'old_binding': binding, 'new_binding': new_binding,
            'source_inventory_sha256': digest(encode(original)),
            'original_unchanged': inventory(source) == original,
        }
        _save(copy / 'migration/grouping-budget-receipt.json', receipt)
        after = inventory(copy)
        allowed_prefixes = (
            'round-03/grouping/input.json', 'round-03/grouping/validation.json',
            'round-03/grouping/attempt-1',
            'round-03/grouping/attempt-1.',
            'migration/grouping-budget-receipt.json', 'binding.json',
        )
        changed = [p for p, sha in original.items()
                   if not any(p == prefix or p.startswith(prefix + '/') or
                              p.startswith(prefix + '.')
                              for prefix in allowed_prefixes)
                   and after.get(p) != sha]
        require(not changed, 'non-Grouping artifacts changed: ' + ', '.join(changed[:10]))
        require(inventory(source) == original, 'original Pilot changed during migration')
        copy.rename(output)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(encode(migrate(args.source, args.output, config_path=args.config)))


if __name__ == '__main__':
    main()
