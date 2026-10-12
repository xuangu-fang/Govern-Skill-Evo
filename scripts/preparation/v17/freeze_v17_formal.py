"""Create a new reviewed freeze; never overwrite an existing manifest, no models."""
import builtins
import importlib.metadata
import sys
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/tau2-bench/src')]
from src.skill_evolution.v17.formal_v17 import FREEZE, clean_policy, digest, frozen_policies, runtime, save


def main():
    if (FREEZE / 'manifest.json').exists():
        raise ValueError('Freeze already exists')
    FREEZE.mkdir(parents=True, exist_ok=True)
    reads = set(); original = builtins.open; path_open = Path.open
    def record(file, mode):
        if isinstance(file, (str, Path)) and 'r' in mode:
            p = Path(file).resolve()
            if p.is_relative_to(ROOT) and p.is_file() and p.suffix not in ('.pyc',):
                reads.add(p)
    def opened(file, mode='r', *args, **kwargs):
        record(file, mode); return original(file, mode, *args, **kwargs)
    def path_opened(file, mode='r', *args, **kwargs):
        record(file, mode); return path_open(file, mode, *args, **kwargs)
    with patch('builtins.open', opened), patch.object(Path, 'open', path_opened):
        r = runtime(); registry = r.BenchmarkRegistry(); adapter = r.UnifiedEnvironmentAdapter(registry)
        from src.skill_evolution.v15.information_boundary_v15 import unpack
        old = r.load(r.CONFIG)
        config = {'version': 'v17-formal-1', 'rounds': 3, 'seed': 200,
            'evolution_rollouts_per_task': 1, 'monitor_rollouts_per_task_per_role': 1,
            'tasks': {split: registry.task_ids(split) for split in ('train', 'monitor')},
            'base_config': r.load(ROOT / old['base_run_config']), 'policies': {},
            'stop': '3 rounds, or NO_UPDATE/UNABLE; errors halt without promotion',
            'gate': 'Four-Delta, integer counts; ACCEPT or RETAIN',
            'grouping': {'model': 'openai/deepseek-v4-pro', 'alias_seed': 200, 'temperature': 0, 'prompt': 'v17-grouping-2'},
            'diagnosis': {'model': 'deepseek-v4-pro', 'temperature': 0, 'prompt': 'v17-group-diagnosis-7'},
            'editor': {'model': 'deepseek-v4-pro', 'temperature': 0, 'prompt': 'v17-bounded-editor-1'}}
        (FREEZE / 'S0.md').write_bytes((ROOT / old['initial_skill']).read_bytes())
        tasks = config['tasks']['train'] + config['tasks']['monitor']
        snapshots = {}
        for task_id in tasks:
            entry = registry.get(task_id)
            view = unpack(adapter.visible_view_without_models(task_id), 'AGENT_VISIBLE_VIEW')
            policy = view['visible_policy']; key = digest(policy.encode())
            if key not in config['policies']:
                name = f'policies/{entry.logical_domain}.md'
                path = FREEZE / name; path.parent.mkdir(exist_ok=True)
                path.write_text(clean_policy(policy)); config['policies'][key] = name
            snapshots[task_id] = {'payload': entry.payload, 'spec': entry.spec, 'split': entry.split}
        save(FREEZE / 'tasks.json', snapshots)
        with frozen_policies(config):
            save(FREEZE / 'contexts.json', {t: unpack(adapter.visible_view_without_models(t), 'AGENT_VISIBLE_VIEW') for t in tasks})
        save(FREEZE / 'config.json', config)
    # Freeze source code plus the data actually opened while constructing all environments.
    for directory in ('src', 'benchmarks', 'external/tau2-bench/src'):
        reads.update((ROOT / directory).rglob('*.py'))
    reads.update(FREEZE.rglob('*'))
    reads.add(ROOT / 'experiments/methods/canonical-paths.json')
    reads.update(ROOT / 'scripts' / name for name in ('run_v17_formal.py', 'freeze_v17_formal.py'))
    reads.update(p for p in ROOT.glob('*') if p.name in ('pyproject.toml', 'uv.lock', 'requirements.txt'))
    files = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in sorted(reads)
             if p.is_file() and p.name != 'manifest.json' and p.name != '.env'}
    save(FREEZE / 'manifest.json', {'files': files,
        'packages': {n: importlib.metadata.version(n) for n in ('openai', 'litellm', 'pydantic')},
        'python': sys.version.split()[0]})
    print(f'Frozen {len(files)} files; no model calls')


if __name__ == '__main__': main()
