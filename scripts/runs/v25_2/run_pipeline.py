"""Run the authorized frozen V25.2 training, final test and three-way comparison."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.v25_2.cli import prepare, read_config
from scripts.runs.v25_2.verify_bundle import verify

def read(path):
    return json.loads(path.read_text())


def save(path, value):
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def now():
    return datetime.now(timezone.utc).isoformat()


def status(phase, state='running', **extra):
    save(HERE / 'pipeline_status.json', dict(phase=phase, status=state,
         pid=os.getpid(), at=now(), **extra))


def setup():
    from scripts.runs.spreadsheetbench.schedules.v25_1_skilladam_run_20261030_001.launcher.common import load_settings
    settings = load_settings()
    os.environ['PYTHONPATH'] = os.pathsep.join(filter(None, (str(ROOT), os.environ.get('PYTHONPATH'))))
    from dotenv import dotenv_values
    env = dotenv_values(settings['official_env'])
    require(env.get('OPENAI_BASE_URL', '').rstrip('/') == 'https://api.deepseek.com'
            and bool(env.get('OPENAI_API_KEY')), 'Official credentials or endpoint unavailable')
    os.environ['OPENAI_API_KEY'] = env['OPENAI_API_KEY']
    os.environ['OPENAI_BASE_URL'] = env['OPENAI_BASE_URL']
    from src.skill_evolution.v25_2 import evolution as ev, evaluation
    from src.skill_evolution.v25_2.benchmark import using_benchmark
    from src.skill_evolution.v25_2.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
    from src.skill_evolution.v25_2.benchmarks.spreadsheetbench import actor
    cfg = read_config(CONFIG / 'config.json')
    context = using_benchmark(SpreadsheetBenchAdapter())
    return settings, cfg, ev, evaluation, actor, context


def reference_files(settings):
    files = {}
    for name, info in settings['arms'].items():
        folder = Path(info.get('record', info['folder']))
        summary = read(folder / 'test/summary.json')
        receipt = read(folder / 'test_complete.json')
        require(summary['status'] == 'complete' and summary['completed'] == 280
                and len(summary['tasks']) == 280, 'Incomplete baseline: ' + name)
        require(sha(folder / 'test/summary.json') == receipt['summary_sha256'], 'Baseline hash differs')
        for rel in ['final_skill.md', 'test/summary.json', 'test_complete.json',
                    'evaluation/config.json', 'evaluation/scoring.py']:
            files[str(folder / rel)] = sha(folder / rel)
    return files


def preflight():
    audit = verify()
    settings, cfg, ev, _, _, context = setup()
    with context:
        ev.validate_config(cfg)
        ev.check_live_environment(cfg)
        runtime = ev.runtime_snapshot(cfg)
        require(runtime == settings['runtime'], 'Docker runtime differs from baseline')
    references = reference_files(settings)
    save(HERE / 'launch_preflight.json', {'status': 'passed', 'at': now(),
         'published_run': audit, 'runtime': runtime,
         'reference_files': references, 'real_model_requests': 0})
    return {'status': 'passed', 'published_run': audit, 'runtime': runtime}


def comparison(settings, output):
    folders = {'v25_2': HERE, **{n: Path(i.get('record', i['folder'])) for n, i in settings['arms'].items()}}
    results, task_rows = {}, {}
    order = read_config(CONFIG / 'evaluation/config.json')['test_tasks']
    for name, folder in folders.items():
        summary = read(folder / 'test/summary.json')
        require(summary['status'] == 'complete' and summary['completed'] == 280
                and [r['task_id'] for r in summary['tasks']] == order, 'Test coverage differs')
        require(summary['success'] == sum(r['hard'] for r in summary['tasks']), 'Invalid success total')
        results[name] = {k: summary[k] for k in ['completed', 'success', 'hard', 'per_cell_pass_rate', 'cost']}
        results[name]['skill_words'] = len((folder / 'final_skill.md').read_text().split())
        results[name]['summary_sha256'] = sha(folder / 'test/summary.json')
        task_rows[name] = {r['task_id']: r for r in summary['tasks']}
    paired = {}
    for baseline in settings['arms']:
        improved = [t for t in order if task_rows['v25_2'][t]['hard'] > task_rows[baseline][t]['hard']]
        regressed = [t for t in order if task_rows['v25_2'][t]['hard'] < task_rows[baseline][t]['hard']]
        paired[baseline] = {'improved_tasks': improved, 'regressed_tasks': regressed,
                            'net_success_change': len(improved) - len(regressed),
                            'percentage_point_change': 100 * (len(improved) - len(regressed)) / len(order)}
    value = {'status': 'complete', 'at': now(), 'results': results, 'paired_vs_v25_2': paired,
             'limitations': ['Single runs; baseline results reused.',
                            'Some test cases previously informed development; not an untouched holdout.']}
    save(output / 'comparison_results.json', value)
    lines = ['# V25.2 / V25.1 / SkillAdam comparison', '',
             '| Method | Passed | Accuracy | Cell pass rate | Skill words | Test tokens (known) |',
             '| --- | --- | --- | --- | --- | --- |']
    for name, r in results.items():
        lines.append(f"| {name} | {r['success']}/280 | {r['hard']:.2%} | {r['per_cell_pass_rate']:.2%} | {r['skill_words']} | {r['cost']['total_tokens_known']} |")
    for name, p in paired.items():
        lines += ['', f"V25.2 vs {name}: {len(p['improved_tasks'])} improved, {len(p['regressed_tasks'])} regressed; net {p['net_success_change']:+d} tasks ({p['percentage_point_change']:+.2f} percentage points)."]
    lines += ['', 'V25.1 and SkillAdam reuse completed actor-aligned runs. These are single-run comparisons.',
              'Some test cases previously informed development; this is not an untouched holdout.']
    (output / 'comparison.md').write_text('\n'.join(lines) + '\n')
    return value


def run():
    with (HERE / '.pipeline.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        phase = 'preflight'
        try:
            require(not (HERE / 'pipeline_status.json').exists(), 'Pipeline already started; no implicit retry')
            receipt = read(HERE / 'launch_authorization.json')
            require(receipt['script_sha256'] == sha(Path(__file__)), 'Launcher changed')
            preflight()
            settings, cfg, ev, evaluation, actor, context = setup()
            references = read(HERE / 'launch_preflight.json')['reference_files']
            with context:
                phase = 'training'
                status(phase)
                result = ev.run_campaign(HERE / 'campaign', config=cfg)
                require(result['status'] == 'complete', 'Training incomplete')
                final = ev.final_parent(HERE / 'campaign')
                require(final is not None and bool(final.read_text().strip()), 'Missing final Skill')
                (HERE / 'final_skill.md').write_bytes(final.read_bytes())
                final_hash = sha(HERE / 'final_skill.md')
                save(HERE / 'training_complete.json', {'status': 'complete', 'rounds': 8,
                     'skill_sha256': final_hash, 'at': now(), 'cost': ev.cost_summary(HERE / 'campaign')})
                phase = 'test'
                status(phase)
                evaluation_cfg = read_config(CONFIG / 'evaluation/config.json')
                scorer = load('v252_frozen_scoring', CONFIG / 'evaluation/scoring.py')
                bundle = {'campaign': str(HERE / 'campaign'), 'skill_text': final.read_text(),
                          'actor_config': evaluation_cfg,
                          'tasks': [evaluation_cfg['task_items'][t] for t in evaluation_cfg['test_tasks']],
                          'initial_reference': None,
                          'evaluation_policy': 'Frozen final Skill, 280 tasks, no optimization or Skill update'}
                def invoke(task, skill, directory, config):
                    return actor.run(config['task_items'][task], Path(skill).read_text(), directory,
                                     config, score=scorer.score)
                result = evaluation.run(HERE / 'test', bundle=bundle, runner=invoke)
                require(result['status'] == 'complete' and result['completed'] == 280, 'Incomplete final test')
                require(sha(HERE / 'final_skill.md') == final_hash and final.read_bytes()
                        == (HERE / 'final_skill.md').read_bytes(), 'Final Skill changed')
                save(HERE / 'test_complete.json', {**{k: result[k] for k in
                     ['status', 'completed', 'success', 'hard', 'per_cell_pass_rate']},
                     'summary_sha256': sha(HERE / 'test/summary.json'), 'at': now()})
                phase = 'comparison'
                status(phase)
                require(all(sha(Path(p)) == digest for p, digest in references.items()), 'Baseline artifacts changed')
                comparison(settings, HERE)
                status('complete', 'complete')
        except BaseException as exc:
            status(phase, 'stopped', error_type=type(exc).__name__)
            traceback.print_exc()
            raise SystemExit(1)


def start():
    with (HERE / '.launch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not (HERE / 'launch_authorization.json').exists(), 'Launch already reserved')
        preflight()
        save(HERE / 'launch_authorization.json', {'at': now(),
             'authorization': 'User requested V25.2 training and test, then comparison with V25.1 and SkillAdam.',
             'script_sha256': sha(Path(__file__)), 'automatic_failure_resume': False})
        with (HERE / 'pipeline.log').open('ab', buffering=0) as log:
            proc = subprocess.Popen([sys.executable, '-B', '-u', str(Path(__file__)), 'run', '--output', str(HERE)],
                 cwd=HERE, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                 start_new_session=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        save(HERE / 'pipeline_launch.json', {'pid': proc.pid, 'at': now()})
        return {'status': 'launched', 'pid': proc.pid}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['check', 'start', 'run'])
    parser.add_argument('--output', type=Path, help='new experiment directory for start, or its directory for run')
    args = parser.parse_args()
    if args.action == 'check':
        print(json.dumps(verify(), indent=2))
        sys.exit(0)
    if args.output is None:
        parser.error('--output is required for start and run')
    HERE = args.output.resolve()
    CONFIG = HERE / 'config'
    if args.action == 'start':
        prepare(HERE)
    if args.action == 'run':
        run()
    else:
        print(json.dumps(start(), ensure_ascii=False))
