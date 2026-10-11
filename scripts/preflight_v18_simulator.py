"""Freeze/check all v18 User prompts without running Agent or User models."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/tau2-bench/src')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path,
                        default=ROOT / 'experiments/configs/v17_formal_001/config.json')
    parser.add_argument('--initial-skill', type=Path,
                        default=ROOT / 'experiments/configs/v17_formal_001/S0.md')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('New output directory required')
    from src.skill_evolution.benchmark_runtime_v18 import BenchmarkRegistry, UnifiedEnvironmentAdapter
    from src.skill_evolution.user_simulator_v18 import PROMPT_VERSION, PROMPT_SHA256
    config_bytes = args.config.read_bytes()
    config = json.loads(config_bytes)
    registry = BenchmarkRegistry()
    for split in ('train', 'monitor'):
        if registry.task_ids(split) != config['tasks'][split]:
            raise ValueError('Task split mismatch')
    adapter = UnifiedEnvironmentAdapter(registry)
    prompts = {}
    for task_id in registry.task_ids():
        orchestrator, _ = adapter.build_orchestrator(
            task_id, base_config=config['base_config'], seed=config['seed'],
            skill_path=args.initial_skill, initial_skill_path=args.initial_skill)
        record = orchestrator.user.prompt_record()
        actual = orchestrator.user.get_init_state().system_messages[0].content
        if actual != record['system_prompt']:
            raise ValueError(f'Actual user state differs from frozen prompt: {task_id}')
        prompts[task_id] = record
    payload = (json.dumps(prompts, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    summary = {
        'status': 'PREFLIGHT', 'scope': 'SIMULATOR_ONLY', 'model_calls': 0,
        'prompt_version': PROMPT_VERSION, 'shared_guidelines_sha256': PROMPT_SHA256,
        'source_config_sha256': hashlib.sha256(config_bytes).hexdigest(),
        'user_prompts_sha256': hashlib.sha256(payload).hexdigest(),
        'evolution_tasks': len(registry.task_ids('train')),
        'monitor_tasks': len(registry.task_ids('monitor')),
    }
    args.output.mkdir(parents=True, exist_ok=False)
    # These contain private scenarios. Never supply this file to the learner.
    (args.output / 'user_prompts.json').write_bytes(payload)
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
