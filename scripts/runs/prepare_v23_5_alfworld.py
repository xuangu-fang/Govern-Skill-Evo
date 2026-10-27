"""Prepare the initial-Skill ALFWorld experiment without API or Actor calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.v23_5 import evolution as ev
from src.skill_evolution.v23_5.config import method_config
from src.adapters.alfworld.skill_runtime import SKILLOPT_INJECTION, ACTION_ONLY_OUTPUT, ACTION_ONLY_INSTRUCTION

EXPERIMENT = ROOT/'experiments/methods/v23_5/alfworld_action_feedback_001'
BASELINE = ROOT/'artifacts/baselines/skillopt/alfworld_deepseek_v23_4_formal_20261023'
V23_4_CONFIG = ROOT/'experiments/methods/v23_4/v23_4_alfworld_formal_001/config/campaign.json'
PYTHON = '/Users/didi/miniforge3/envs/alfworld/bin/python'
SPLITS = ROOT/'benchmarks/alfworld/editions/skillopt_39_18_134'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze(path, value):
    if path.exists():
        ev.require(ev.read(path) == value, f'Prepared file differs: {path}')
    else:
        ev.save(path, value)


def main(experiment=EXPERIMENT, *, knowledge_review=False):
    baseline = ev.read(BASELINE/'config.json')
    expected = {'max_steps': 50, 'workers': 8, 'max_api_workers': 8,
                'max_completion_tokens': 16384, 'optimizer_model': 'deepseek-v4.1-flash',
                'target_model': 'deepseek-v4.1-flash'}
    ev.require(all(baseline[k] == v for k, v in expected.items()), 'SkillOpt reference config differs')
    original_initial = BASELINE/'skills/skill_v0000.md'
    source = ROOT/'external/SkillOpt'/baseline['skill_init']
    ev.require(original_initial.read_bytes() == source.read_bytes(), 'SkillOpt initial snapshot differs')
    initial = ROOT/'src/skill_evolution/v23_5/alfworld_initial_skill.md'
    old_format = '**Output format**: Always output `<think>...</think>` for reasoning, then `<action>...</action>` for the chosen action.'
    original_text = original_initial.read_bytes().decode('utf-8')
    ev.require(original_text.count(old_format) == 1 and initial.read_bytes().decode('utf-8') ==
               original_text.replace(old_format, '**Output format**: ' + ACTION_ONLY_INSTRUCTION),
               'Initial Skill must differ only by the approved output-format instruction')
    manifests = {s: ev.read(SPLITS/s/'items.json') for s in ('train', 'val', 'test')}
    ev.require([len(manifests[s]) for s in manifests] == [39, 18, 134], 'Unexpected splits')
    all_items = sum(manifests.values(), [])
    ev.require(len({t['id'] for t in all_items}) == len({t['gamefile'] for t in all_items}) == 191,
               'Overlapping task identities')
    for split in manifests:
        ev.require((SPLITS/split/'items.json').read_bytes() ==
                   (ROOT/'external/SkillOpt/data/alfworld_path_split'/split/'items.json').read_bytes(),
                   'Benchmark manifest differs from SkillOpt')
    # User-selected V23.4 protocol: one ordered pass over Train + Selection.
    protocol = ev.read(V23_4_CONFIG)
    pool = manifests['train'] + manifests['val']
    batches = protocol['batches']
    ev.require([len(b) for b in batches] == [10, 10, 10, 10, 10, 7]
               and [t for b in batches for t in b] == [t['id'] for t in pool],
               'V23.4 optimization task order differs')
    ev.require(protocol['optimization_splits'] == ['train', 'val']
               and protocol['task_items'] == {t['id']: t for t in pool},
               'V23.4 optimization identities differ')
    env_root = Path('/Users/didi/.cache/alfworld')
    files, hashes = {}, {}
    for split, items in manifests.items():
        for item in items:
            game = env_root/item['gamefile']
            for path in (game, game.parent/'initial_state.pddl'):
                hashes[str(path)] = sha(path)
                if split in ('train', 'val'): files[str(path)] = path.read_bytes().decode('utf-8')
    cfg = {
        'method': method_config(knowledge_review=knowledge_review), 'batches': batches, 'optimization_splits': ['train', 'val'],
        'initial_skill': {'source': str(initial.relative_to(ROOT)),
                          'sha256': sha(initial), 'text': initial.read_bytes().decode('utf-8')},
        'task_items': {t['id']: t for t in pool},
        'environment_root': str(env_root), 'environment_files': files,
        'actor_python': PYTHON, 'actor_model': 'deepseek-v4.1-flash',
        'actor_skill_injection': SKILLOPT_INJECTION,
        'actor_output_format': ACTION_ONLY_OUTPUT,
        'actor_retry_invalid_actions': True,
        'actor_action_feedback': True,
        'actor_base_url': 'http://llm-proxy.intra.xiaojukeji.com', 'actor_max_workers': 8,
        'max_attempts': 6, 'actor_request_attempts': 6, 'max_steps': 50,
        'module_max_tokens': {'preconditioner': 32768, 'replay': 32768},
        'continue_no_change': True, 'retry_delay_seconds': 2,
        'max_input_chars': 4000000, 'max_message_utf8_bytes': 6000000,
        'call_config': ev.grouping.call_configuration(base_url='http://llm-proxy.intra.xiaojukeji.com',
            model='deepseek-v4.1-flash', max_tokens=16384, timeout=300),
    }
    if knowledge_review:
        cfg['module_max_tokens'].update(verifier=32768, repair=32768)
    ev.validate_config(cfg)
    ev.check_environment_route(cfg)
    subprocess.check_call([PYTHON, '-c', 'import dotenv'])
    freeze(experiment/'config/campaign.json', cfg)
    freeze(experiment/'config/provenance.json', {
        'reference_run': str(BASELINE.relative_to(ROOT)), 'reference_config': baseline,
        'training_protocol_reference': str(V23_4_CONFIG.relative_to(ROOT)),
        'reference_files_sha256': {str(p.relative_to(ROOT)): sha(p) for p in
            [BASELINE/'config.json', original_initial, initial, source, V23_4_CONFIG,
             ROOT/'external/SkillOpt/skillopt/envs/alfworld/rollout.py',
             *sorted((ROOT/'external/SkillOpt/skillopt/envs/alfworld/prompts').glob('rollout_*history.md')),
             ROOT/'scripts/runs/run_skillopt_alfworld_deepseek.sh',
             ROOT/'experiments/configs/skillopt_alfworld_deepseek_v23_4.yaml']},
        'environment_sha256': hashes, 'runtime': ev.runtime_snapshot(cfg),
        'protocol': 'V23.4 ordered 57-task optimization pool, six batches; SkillOpt-derived initial Skill and Actor templates with action_only_v1 output; original model settings; native V23.5 Gate',
        'actor_protocol': ev.execution_protocol(cfg['max_steps'], SKILLOPT_INJECTION, output_format=ACTION_ONLY_OUTPUT,
                                                retry_invalid_actions=True, action_feedback=True),
        'selection_usage': '18 original Selection tasks included in optimization, same-batch Gate and Replay; no independent Selection gate',
        'test_usage': '134 held-out tasks; evaluate final published Parent only; SkillOpt initial score is historical context, not a same-protocol baseline',
    })
    reference = ev.read(BASELINE/'summary.json')
    freeze(experiment/'config/initial_baseline_reference.json', {
        'source': str((BASELINE/'summary.json').relative_to(ROOT)),
        'source_sha256': sha(BASELINE/'summary.json'), 'initial_skill_sha256': sha(original_initial),
        'current_initial_skill_sha256': sha(initial), 'comparable_to_current_protocol': False,
        'test_tasks': 134, 'success_rate': reference['baseline_test_hard'],
        'label': 'Historical SkillOpt initial Test result under its original output protocol; not a measurement of the action-only Skill/Actor',
        'remaining_actor_differences': 'Initial Skill output instruction and both Actor templates use action_only_v1; runtime versions, HTTP/module retries and response handling also differ from SkillOpt',
        'remeasure': False,
    })
    for split, items in manifests.items(): freeze(experiment/'data'/f'{split}.json', items)
    freeze(experiment/'data/optimization_pool.json', pool)
    freeze(experiment/'data/batches.json', batches)
    freeze(experiment/'config/budget.json', {
        'unique_optimization_tasks': 57, 'train_tasks': 39, 'selection_tasks_in_optimization': 18,
        'epochs': 1, 'rounds': 6, 'batch_sizes': [10, 10, 10, 10, 10, 7], 'optimization_task_exposures': 57,
        'parent_episodes_max': 57, 'candidate_episodes_max': 57,
        'actor_http_requests_max': 114 * cfg['max_steps'] * cfg['actor_request_attempts'],
        'module_http_requests_max': len(batches) * len(ev.enabled_modules(cfg)) * cfg['max_attempts'],
        'max_total_attempts_per_call': 6, 'max_retries_per_call': 5,
        'default_max_output_tokens': 16384,
        'module_max_tokens': cfg['module_max_tokens'], 'test_episodes_per_skill': 134,
        'note': 'Upper bounds, not estimates; no automatic token escalation. Training protocol follows V23.4, not SkillOpt.',
    })
    print(json.dumps({'status': 'prepared_offline', 'config': str(experiment/'config/campaign.json'),
        'round_sizes': list(map(len, batches)), 'initial_sha256': sha(initial),
        'runtime': ev.runtime_snapshot(cfg), 'knowledge_review': knowledge_review, 'network_calls': 0}, indent=2))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment-dir', type=Path, default=EXPERIMENT)
    parser.add_argument('--knowledge-review', action='store_true')
    args = parser.parse_args()
    main(args.experiment_dir.resolve(), knowledge_review=args.knowledge_review)
