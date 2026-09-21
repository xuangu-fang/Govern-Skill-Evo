"""Create the benchmark-v4 v18 freeze; never overwrite it, no models."""
import builtins
import importlib.metadata
import sys
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/tau2-bench/src')]
from src.skill_evolution.formal_v18_v4 import FREEZE, clean_policy, digest, frozen_policies, runtime, save


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
        from src.skill_evolution.information_boundary_v15 import unpack
        old = r.shared.load(r.shared.CONFIG)
        config = {'version': 'v18-formal-3-benchmark-v4', 'benchmark_edition': 'phase_v4_day36', 'rounds': 4, 'seed': 200,
            'evolution_rollouts_per_task': 1, 'monitor_rollouts_per_task_per_role': 1,
            'tasks': {split: registry.task_ids(split) for split in ('train', 'monitor')},
            'base_config': r.shared.load(ROOT / old['base_run_config']), 'policies': {},
            'stop': '4 rounds, or NO_UPDATE/UNABLE; errors halt without promotion',
            'gate': 'Four-Delta, integer counts; ACCEPT or RETAIN',
            'grouping': {'model': 'openai/deepseek-v4-pro', 'alias_seed': 200, 'temperature': 0, 'prompt': 'v17-grouping-2'},
            'diagnosis': {'model': 'deepseek-v4-pro', 'temperature': 0, 'prompt': 'v18-group-diagnosis-3.2.1'},
            'editor': {'model': 'deepseek-v4-pro', 'temperature': 0, 'prompt': 'v18-bounded-editor-1'}}
        save(FREEZE / 'protocol.json', {
            'version': 'v18-v4-formal-protocol-1', 'initial_skill': 'S0.md',
            'round_limit': 4, 'seed': 200, 'prompt_changes_during_campaign': False,
            'candidate_states': ['VALID', 'APPLIED_DETERMINISTIC'],
            'promotion': 'COMPLETE Monitor and ACCEPT only; RETAIN keeps Parent',
            'stop': ['ROUND_LIMIT', 'NO_UPDATE', 'UNABLE'],
            'errors': 'INCOMPLETE; explicit resume only, preserve attempts; no outcome-based reruns',
            'metrics': ['S', 'C', 'CS', 'VF', 'quadrant_counts', 'transition_counts'],
            'report_slices': ['all_monitor', 'core_monitor', 'regression_guards', 'each_family', 'joint_families'],
            'gate': 'all Monitor tasks; delta S/C/CS >= 0, delta VF <= 0, at least one strict improvement',
            'analysis': 'Compare each Candidate with matched Parent; report task counts and denominators; no causal claim from unmatched rounds',
            'semantic_audit': 'Report condition/scope/epistemic preservation and unsupported duties without changing learner mid-run',
            'limitations': ['single seed', 'Monitor used during benchmark development', 'JRA-01 original contract remains HOLD_REPLICATION'],
        })
        config['protocol_sha256'] = digest((FREEZE / 'protocol.json').read_bytes())
        config['protocol_file'] = 'protocol.json'
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
        user_prompts = {}
        with frozen_policies(config):
            for task_id in tasks:
                orchestrator, _ = adapter.build_orchestrator(task_id, base_config=config['base_config'],
                    seed=config['seed'], skill_path=FREEZE / 'S0.md', initial_skill_path=FREEZE / 'S0.md')
                user_prompts[task_id] = orchestrator.user.prompt_record()
        save(FREEZE / 'user_prompts.json', user_prompts)
        config['user_prompts_sha256'] = digest((FREEZE / 'user_prompts.json').read_bytes())
        save(FREEZE / 'config.json', config)
    # Freeze source code plus the data actually opened while constructing all environments.
    for directory in ('src', 'benchmarks', 'external/tau2-bench/src'):
        reads.update((ROOT / directory).rglob('*.py'))
    reads.update(FREEZE.rglob('*'))
    reads.update(ROOT / 'scripts' / name for name in ('run_v18_formal_v4.py', 'freeze_v18_formal_v4.py'))
    reads.update(p for p in ROOT.glob('*') if p.name in ('pyproject.toml', 'uv.lock', 'requirements.txt'))
    files = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in sorted(reads)
             if p.is_file() and p.name != 'manifest.json' and p.name != '.env'}
    save(FREEZE / 'manifest.json', {'files': files,
        'packages': {n: importlib.metadata.version(n) for n in ('openai', 'litellm', 'pydantic')},
        'python': sys.version.split()[0]})
    print(f'Frozen {len(files)} files; no model calls')


if __name__ == '__main__': main()
