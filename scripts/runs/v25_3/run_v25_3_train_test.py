"""Prepare or manually run the v25.3 SpreadsheetBench training and final test."""
import argparse
import fcntl
import getpass
import hashlib
import os
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.skill_evolution.v25_2.cli import read_config
from src.skill_evolution.v25_3 import campaign
from src.skill_evolution.v25_3.baseline import evaluation
from src.skill_evolution.v25_3.baseline.benchmark import using_benchmark
from src.skill_evolution.v25_3.baseline.benchmarks.spreadsheetbench import actor, scoring
from src.skill_evolution.v25_3.baseline.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from src.skill_evolution.v25_3.baseline.contracts.model_routing import route_call_config
from src.skill_evolution.v25_3.stages import freeze, read
from src.skill_evolution.v27.transport import HTTPGenerator

EXPERIMENT = ROOT / 'artifacts/methods/v25_3/v25_3_spreadsheetbench_proxy'
BASE_URL = 'http://llm-proxy.intra.xiaojukeji.com'
MODEL = 'deepseek-v4.1-flash'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recorded_contract_path(name):
    """Resolve paths stored in the v25.3 and v25.4 design baselines before the move."""
    path = Path(name)
    old_inputs = Path('experiments/comparisons/v25_2_prompt_only_20261101_001')
    if path.is_relative_to(old_inputs):
        return campaign.BASELINE / path.relative_to(old_inputs)
    sources = ROOT / 'experiments/methods/v25_3/v25_3_spreadsheetbench_proxy/config/recorded_sources'
    shared = ROOT / 'src/skill_evolution/v25_3'
    original = (ROOT / path).resolve()
    if original.is_relative_to(shared):
        saved = sources / original.relative_to(shared)
        if saved.is_file():
            return saved
    return ROOT / path


def prepare(root):
    train = campaign.configuration()
    baseline = campaign.BASELINE
    hashes = read(baseline / 'frozen_manifest.json')
    for rel in ('evaluation/config.json', 'evaluation/scoring.py'):
        if sha(baseline / rel) != hashes[rel]:
            raise ValueError(f'Frozen evaluation asset changed: {rel}')
    if sha(Path(scoring.__file__)) != hashes['evaluation/scoring.py']:
        raise ValueError('Final test scorer differs from v25.2')
    test = read_config(baseline / 'evaluation/config.json')
    test.update(candidate=train['candidate'], method=train['method'], module_max_tokens=train['module_max_tokens'])
    adapter = SpreadsheetBenchAdapter()
    for config in (train, test):
        config.update(actor_model=MODEL, actor_base_url=BASE_URL,
                      call_config=route_call_config(config['call_config'], BASE_URL))
        adapter.validate_config(config)
    if test['test_tasks'] != train['test_tasks'] or test['dataset']['metadata_issues']:
        raise ValueError('Final test cohort or metadata mismatch')
    if Path(sys.prefix).name != 'spreadsheetbench':
        raise ValueError('Use the spreadsheetbench conda environment')
    runtime = adapter.runtime_snapshot(train)
    if runtime != read(baseline / 'campaign/runtime.json'):
        raise ValueError('Docker runtime differs from v25.2')
    campaign.prepare(root / 'campaign', train)
    freeze(root / 'evaluation/config.json', test)
    freeze(root / 'runtime.json', {'python': sys.executable, 'docker': runtime,
                                   'evaluation_scorer_sha256': sha(Path(scoring.__file__))})
    return train, test


def proxy_session():
    session = requests.Session()
    session.trust_env = False
    return session


def credentials():
    key = os.environ.get('V25_3_PROXY_API_KEY')
    if not key and os.environ.get('OPENAI_BASE_URL', '').rstrip('/') == BASE_URL:
        key = os.environ.get('OPENAI_API_KEY')
    if not key:
        key = getpass.getpass('Internal proxy API key: ')
    if not key.strip():
        raise ValueError('Missing internal proxy API key')
    os.environ.update(OPENAI_BASE_URL=BASE_URL, OPENAI_API_KEY=key, PYTHONPATH=str(ROOT))
    return HTTPGenerator(key, session_factory=proxy_session)


def train_test(root, train, test, generate, *, run_campaign=campaign.run):
    train_dir = root / 'campaign'
    state = run_campaign(train_dir, generate, expected_config=train)
    skill_path = train_dir / 'final_skill.md'
    if state['next_round'] != len(train['batches']) + 1:
        raise ValueError('Training incomplete')
    skill = skill_path.read_bytes().decode('utf-8')
    if not skill.strip() or skill != state['selected']:
        raise ValueError('Final Skill differs from published training state')
    freeze(root / 'training_complete.json', {'rounds': len(train['batches']), 'skill_sha256': sha(skill_path)})
    bundle = dict(campaign=str(train_dir), skill_text=skill, actor_config=test,
                  tasks=[test['task_items'][t] for t in test['test_tasks']], initial_reference=None,
                  evaluation_policy='Frozen final Skill on v25.2 final test cohort')

    def invoke(task, snapshot, dest, config):
        if Path(snapshot).read_bytes().decode('utf-8') != skill:
            raise ValueError('Test Skill snapshot differs')
        return actor.run(config['task_items'][task], skill, dest, config, score=scoring.score)

    test_dir = root / 'test'
    with using_benchmark(SpreadsheetBenchAdapter()):
        result = evaluation.run(test_dir, runner=invoke, bundle=bundle, resume=(test_dir / 'input.json').exists())
    if result['status'] != 'complete' or [r['task_id'] for r in result['tasks']] != test['test_tasks']:
        raise ValueError('Final test incomplete')
    print(f"Test complete: {result['success']}/{result['completed']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run'])
    parser.add_argument('--output', type=Path, default=EXPERIMENT, help='campaign and test output directory')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (output / '.pipeline.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        train, test = prepare(output)
        if args.action == 'run':
            train_test(output, train, test, credentials())
        else:
            print(f"Prepared {len(train['batches'])} training batches and {len(test['test_tasks'])} test tasks.")


if __name__ == '__main__':
    main()
