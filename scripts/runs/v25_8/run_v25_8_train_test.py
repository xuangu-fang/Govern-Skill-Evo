"""Prepare SpreadsheetBench v25.8, then train and evaluate the final published Skill."""
import argparse
import fcntl
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.runs.v25_3 import run_v25_3_train_test as pipeline
from src.skill_evolution.v25_8 import PACKAGE, engine
from src.skill_evolution.v25_8.stages import freeze, read
from src.skill_evolution.v27.facts import require
from src.skill_evolution.v27.storage import write_record

OFFICIAL = ROOT / 'experiments/methods/v25_5/v25_5_spreadsheetbench_deepseek/config'
EXPERIMENT = ROOT / 'artifacts/methods/v25_8/v25_8_spreadsheetbench_deepseek'
BASE_URL = 'https://api.deepseek.com'
INTERNAL_BASE_URL = 'http://llm-proxy.intra.xiaojukeji.com'
INTERNAL_MODEL = 'deepseek-v4.1-flash'


def configurations(api_profile='public'):
    require(api_profile in ('public', 'internal'), 'Unknown API profile')
    train, test = (pipeline.read_config(OFFICIAL / name)
                   for name in ('config.json', 'evaluation/config.json'))
    train['actor_max_workers'] = 15
    test['actor_max_workers'] = 40
    for config in (train, test):
        require(config['actor_base_url'] == BASE_URL and config['actor_model'] == 'deepseek-flash',
                'Expected the public v25.5 DeepSeek profile')
        config['candidate'] = 'v25_8_spreadsheetbench'
        config['method']['version'] = 'v25_8_selective_updates_prompt_v1'
        if api_profile == 'internal':
            config.update(actor_base_url=INTERNAL_BASE_URL, actor_model=INTERNAL_MODEL,
                          call_config=pipeline.route_call_config(
                              {**config['call_config'], 'model': INTERNAL_MODEL}, INTERNAL_BASE_URL))
        pipeline.SpreadsheetBenchAdapter().validate_config(config)
    # The official evaluation config supplies the corrected answer region for test:60-7.
    require(train['test_tasks'] == test['test_tasks'] and not test['dataset']['metadata_issues'],
            'Test cohort differs or evaluation metadata is unresolved')
    return train, test


def save_snapshot(root, state):
    number = state['next_round'] - 1
    folder = root / 'snapshots'
    folder.mkdir(exist_ok=True)
    path = folder / f'R{number:02}.md'
    tmp = path.with_suffix('.tmp')
    tmp.write_bytes(state['selected'].encode('utf-8'))
    tmp.replace(path)


def prepare(root, api_profile='public'):
    train, test = configurations(api_profile)
    engine.check_assets(train)
    engine.check_assets(test)
    runtime = pipeline.SpreadsheetBenchAdapter().runtime_snapshot(train)
    require(runtime == read(OFFICIAL / 'runtime.json')['docker'], 'Official Docker runtime differs')
    write_record(root / 'runtime.json', dict(python=sys.executable, docker=runtime))
    state = engine.prepare(root / 'campaign', train)
    freeze(root / 'evaluation/config.json', test)
    save_snapshot(root, state)
    return train, test


def configured_generator(base_url):
    from dotenv import dotenv_values
    env = dict(dotenv_values(ROOT / '.env', interpolate=False))
    # Prefer the explicitly configured process pair, otherwise use the .env pair.
    if os.environ.get('OPENAI_API_KEY'):
        env = os.environ
    require((env.get('OPENAI_BASE_URL') or '').rstrip('/') in (base_url, base_url + '/v1')
            and env.get('OPENAI_API_KEY'), 'Credentials must match the configured API endpoint')
    os.environ.update(OPENAI_BASE_URL=base_url, OPENAI_API_KEY=env['OPENAI_API_KEY'], PYTHONPATH=str(ROOT))
    if base_url == INTERNAL_BASE_URL:
        return pipeline.HTTPGenerator(env['OPENAI_API_KEY'], session_factory=pipeline.proxy_session)
    return pipeline.HTTPGenerator(env['OPENAI_API_KEY'])


def evaluate_final(root, test):
    campaign = root / 'campaign'
    skill = (campaign / 'final_skill.md').read_bytes().decode('utf-8')
    folder = root / 'test'
    bundle = dict(campaign=str(campaign), skill_text=skill, actor_config=test,
                  tasks=[test['task_items'][t] for t in test['test_tasks']], initial_reference=None,
                  evaluation_policy='Final v25.8 Skill on the official test cohort')

    def invoke(task, snapshot, dest, config):
        return pipeline.actor.run(config['task_items'][task], skill, dest, config, score=pipeline.scoring.score)

    with pipeline.using_benchmark(pipeline.SpreadsheetBenchAdapter()):
        return pipeline.evaluation.run(folder, runner=invoke, bundle=bundle,
                                       resume=(folder / 'input.json').exists())


def train_only(root, train, generate):
    campaign = root / 'campaign'
    _, state = engine.current(campaign)
    while state['next_round'] <= len(train['batches']):
        state = engine.run(campaign, generate, limit=1, expected_config=train)
        save_snapshot(root, state)
    if not (campaign / 'final_skill.md').exists():
        # Resume after the last HEAD commit but before the engine exported the final file.
        engine.run(campaign, generate, limit=0, expected_config=train)


def train_and_test(root, train, test, generate):
    train_only(root, train, generate)
    return evaluate_final(root, test)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'verify', 'train', 'run'))
    parser.add_argument('--api-profile', choices=('public', 'internal'), default='public')
    parser.add_argument('--output', type=Path, default=EXPERIMENT)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.pipeline.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        train, test = prepare(root, args.api_profile)
        if args.action == 'verify':
            from scripts.verification.v25_8.verify_offline import verify
            report = verify(train, test, api_profile=args.api_profile)
            write_record(root / 'offline_acceptance.json', report)
            print('Offline checks passed:', root / 'offline_acceptance.json')
        elif args.action == 'train':
            train_only(root, train, configured_generator(train['actor_base_url']))
            print('Training complete:', root / 'campaign/final_skill.md')
        elif args.action == 'run':
            train_and_test(root, train, test, configured_generator(train['actor_base_url']))
            print('Final test results:', root / 'test/summary.json')
        else:
            print('Prepared:', root)


if __name__ == '__main__':
    main()
