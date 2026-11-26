"""Train SkillOpt with the v25.8 SpreadsheetBench actor, then test its selection-best skill."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
UPSTREAM = ROOT / 'external/SkillOpt'
sys.path[:0] = [str(ROOT), str(UPSTREAM)]
from scripts.runs import run_skillopt_spreadsheetbench_aligned as legacy
from scripts.runs.v25_8 import run_v25_8_train_test as v258
from src.skill_evolution.shared.offline_records import offline_records
from src.skill_evolution.v25_2 import cli as spreadsheet_inputs
from src.skill_evolution.v25_3.stages import freeze, read
from src.skill_evolution.v27.facts import require
from skillopt.engine.trainer import ReflACTTrainer
from skillopt.utils.scoring import compute_score, skill_hash

DEFAULT = ROOT / 'artifacts/methods/skillopt/spreadsheetbench_v25_8'
V25 = ROOT / 'artifacts/methods/v25_8/v25_8_spreadsheetbench_official_20261118_232447'
ADAM = (ROOT / 'artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback'
        / 'skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006')
WORKER = Path(__file__).with_name('worker.py')
PIN = '7da46ae693ee0329b80225c0128a37d65db10e9e'
# The local checkout already has a DeepSeek transport and an optional final-test switch.
LOCAL_PATCHES = {
    'skillopt/config.py': '9fc7302c8b130684d323fc848c6c908faee1a4929a732d79e9d7f2510fc82813',
    'skillopt/engine/trainer.py': '0df9d435f43cf6e5e7b773e81e5dbfdbb06c81d25e6edf5816d3278177a852b2',
    'skillopt/model/openai_compatible_backend.py': '758836d5131672be8cdb988b518e81401cc1ea41812031459d4cce54d23869de',
}


def upstream_check():
    cmd = ['git', '-C', str(UPSTREAM)]
    paths = subprocess.check_output(cmd + ['diff', '--name-only', PIN, '--', 'configs', 'skillopt'],
                                    text=True).splitlines()
    require('skillopt/model/openai_compatible_backend.py' in paths and set(paths) <= LOCAL_PATCHES.keys() and
            all(legacy.sha(UPSTREAM / p) == LOCAL_PATCHES[p] for p in paths),
            'SkillOpt sources differ from the verified upstream revision and transport adaptations')
    require(not subprocess.check_output(cmd + ['ls-files', '--others', '--exclude-standard',
                                               '--', 'configs', 'skillopt']), 'Unexpected SkillOpt sources')


def prepare(root):
    train, test = v258.configurations()
    upstream_check()
    actor_fields = ('actor_profile', 'actor_model', 'actor_base_url', 'call_config', 'executor',
                    'task_items', 'initial_skill', 'test_tasks', 'actor_request_attempts', 'retry_delay_seconds')
    launch = read(ADAM / 'launch.json')
    with offline_records('spreadsheetbench', spreadsheet_inputs):
        for cfg, vfile, afile, stage in [(train, 'campaign/config.json', 'shared_config.json', 'train'),
                                         (test, 'evaluation/config.json', 'evaluation/config.json', 'test')]:
            original = v258.pipeline.read_config(V25 / vfile)
            other = v258.pipeline.read_config(ADAM / 'config' / afile)
            for field in actor_fields:
                require(cfg[field] == original[field] == other[field], f'{stage} {field} differs')
            require(cfg['actor_max_workers'] == original['actor_max_workers'] == launch[stage + '_workers'],
                    f'{stage} concurrency differs')
            freeze(root / f'{stage}_actor.json', cfg)
    cfg = legacy.native_defaults()
    initial = UPSTREAM / cfg['skill_init']
    require(initial.read_bytes() == train['initial_skill']['text'].encode(), 'Initial skill differs')
    cfg.update(model_backend='openai_compatible', optimizer_backend='openai_compatible',
               target_backend='openai_compatible', optimizer_model=train['actor_model'],
               target_model=train['actor_model'], skill_init=str(initial), out_root=str(root / 'campaign'),
               split_dir=str(UPSTREAM / 'data/spreadsheetbench_id_split'),
               data_root=str(Path(next(iter(train['task_items'].values()))['input_path']).parents[2]),
               workers=train['actor_max_workers'], max_completion_tokens=train['actor_profile']['actor_max_output_tokens'],
               slow_update_gate_with_selection=True, eval_test=False)  # Final Selection and Test are separately resumable below.
    freeze(root / 'skillopt.json', cfg)
    adapter = SharedActor(root, cfg, train)
    for split, expected in [('train', 80), ('val', 40), ('test', 280)]:
        ids = [r['id'] for r in adapter.dataloader.get_split_items(split)]
        keys = [f'{split}:{uid}' for uid in ids]
        expected_keys = [k for k, task in train['task_items'].items() if task['split'] == split]
        require(keys == expected_keys and len(set(keys)) == expected, f'{split} cohort differs')
        if split == 'test':
            require(keys == test['test_tasks'], 'Test order differs')
    return cfg, adapter


def worker(action, root, *args):
    python = read(V25 / 'runtime.json')['python']
    env = {**os.environ, 'PYTHONPATH': str(ROOT)}
    subprocess.run([python, str(WORKER), action, str(root), *map(str, args)], check=True, cwd=ROOT, env=env)


class SharedActor(legacy.SpreadsheetBenchAdapter):
    @property
    def _env_name(self):
        return 'spreadsheetbench'

    def __init__(self, root, cfg, actor):
        super().__init__(**{k: cfg[k] for k in (
            'split_dir', 'split_mode', 'data_root', 'mode', 'max_turns', 'exec_timeout', 'workers',
            'analyst_workers', 'failure_only', 'minibatch_size', 'edit_budget', 'seed', 'max_completion_tokens')})
        self.root = root
        self.keys = {task['dataset_id']: k for k, task in actor['task_items'].items()}
        self.setup(cfg)

    def rollout(self, env_manager, skill_content, out_dir, **kwargs):
        require(not kwargs.get('diagnostic_mode'), 'Actor diagnostic intervention is disabled')
        ids = [str(item['id']) for item in env_manager]
        keys = [self.keys[uid] for uid in ids]
        splits = {key.split(':', 1)[0] for key in keys}
        require(splits in ({'train'}, {'val'}) and len(set(keys)) == len(keys),
                'Training rollout requires one non-Test split with distinct tasks')
        directory = Path(out_dir)
        freeze(directory / 'binding.json', {'tasks': keys, 'skill': skill_content})
        if not (directory / 'results.jsonl').exists():
            worker('batch', self.root, directory)
        rows = [json.loads(line) for line in (directory / 'results.jsonl').read_text().splitlines()]
        require([str(r['id']) for r in rows] == ids, 'Incomplete or reordered rollout')
        return rows


def select_best(root, cfg, adapter):
    """Reproduce upstream end-of-training promotion before exposing a separately runnable Test."""
    campaign = root / 'campaign'
    summary = read(campaign / 'summary.json')
    history = read(campaign / 'history.json')
    state = read(campaign / 'runtime_state.json')
    steps = [row['step'] for row in history]
    require(steps == list(range(1, 9)) and state['last_completed_step'] == summary['total_steps'] == 8,
            'Selection requires eight completed steps')
    current = Path(state['current_skill_path']).read_text()
    best = Path(state['best_skill_path']).read_text()
    score, step, origin = state['best_score'], state['best_step'], state['best_origin']
    final_hard = score
    if skill_hash(current) != skill_hash(best):
        env = adapter.build_eval_env(cfg['sel_env_num'], 'valid_seen', cfg['seed'])
        rows = adapter.rollout(env, current, campaign / 'final_selection_eval')
        final_hard, _ = compute_score(rows)
        if final_hard > score:
            best, score, step, origin = current, final_hard, steps[-1], state['current_origin']
    result = dict(best_step=step, best_origin=origin, best_selection_hard=score,
                  final_selection_hard=final_hard, sha256=hashlib.sha256(best.encode()).hexdigest())
    tmp = root / 'best_skill.tmp'
    tmp.write_text(best)
    tmp.replace(root / 'best_skill.md')
    freeze(root / 'selection.json', result)
    return result


def train(root, cfg, adapter):
    if (root / 'selection.json').exists():
        result = read(root / 'selection.json')
        require(legacy.sha(root / 'best_skill.md') == result['sha256'], 'Selected Skill changed')
        return result
    if not (root / 'campaign/summary.json').exists():
        ReflACTTrainer(dict(cfg), adapter).train()
    return select_best(root, cfg, adapter)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['verify', 'train', 'test', 'train-test'], default='verify', nargs='?')
    parser.add_argument('--output', type=Path, default=DEFAULT)
    args = parser.parse_args()
    root = args.output.resolve()
    if args.action == 'test':
        require((root / 'selection.json').is_file(), 'Run training and final Selection before Test')
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        cfg, adapter = prepare(root)
        if args.action == 'verify':
            from scripts.runs.skillopt.spreadsheetbench.verify import verify
            verify(root, cfg, adapter)
            return
        v258.engine.check_assets(read(root / 'test_actor.json'))
        shared = read(root / 'train_actor.json')
        require(v258.pipeline.SpreadsheetBenchAdapter().runtime_snapshot(shared) == read(V25 / 'runtime.json')['docker'],
                'Actor Docker runtime differs from the v25.8 run')
        legacy.configure_model(shared)
        if args.action in ('train', 'train-test'):
            train(root, cfg, adapter)
        if args.action in ('test', 'train-test'):
            worker('test', root)


if __name__ == '__main__':
    main()
