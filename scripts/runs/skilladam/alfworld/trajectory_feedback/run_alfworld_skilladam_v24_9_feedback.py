"""Dual-official DeepSeek ALFWorld SkillAdam with v24.9 training evidence."""
import argparse
import fcntl
from importlib.metadata import version
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from scripts.runs.alfworld.alfworld_aligned_common import read, require, run_batch, sha, write
from src.skill_evolution.shared.experiment_paths import resolve_experiment_path
from src.skill_evolution.skilladam.alfworld.shared_actor.paths import historical_input
from src.skill_evolution.skilladam.alfworld.trajectory_feedback.backend import (
    BASELINE, NATIVE, ROOT, FeedbackBackend, bridge,
)

ARTIFACTS = ROOT / 'artifacts/methods/skilladam/alfworld/trajectory_feedback'


def prepare():
    manifest = read(BASELINE / 'manifest.json')
    require(sys.version == manifest['python_version'], 'Use the recorded SkillAdam Python version')
    for name, expected in manifest['packages'].items():
        require(version(name) == expected, f'Frozen package changed: {name}')
    # The original manifest recorded absolute paths, including an entire upstream checkout.
    upstream_license, = (Path(name) for name in manifest['files']
                         if Path(name).parts[-3:] == ('external', 'SkillAdam', 'LICENSE'))
    recorded_root = upstream_license.parents[2]
    for filename, expected in manifest['files'].items():
        relative = Path(filename).relative_to(recorded_root)
        if relative.is_relative_to('external/SkillAdam'):
            upstream = relative.relative_to('external/SkillAdam')
            if upstream.parts[0] not in ('skilladam', 'LICENSE', 'NOTICE'):
                continue
            path = NATIVE / upstream
        else:
            path = historical_input(relative)
        require(sha(path) == expected, f'Frozen input changed: {path}')
    return read(BASELINE / 'actor.json'), read(BASELINE / 'skilladam.json')


def run(output, resume):
    actor, cfg = prepare()
    output = resolve_experiment_path(output.resolve())
    require(not output.is_relative_to(BASELINE.parent)
            and not output.is_relative_to(resolve_experiment_path(cfg['output_root'])), 'Use a new output outside the historical run')
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.parent == ARTIFACTS:
        # Native RunStore requires the output directory to be empty on first start.
        controls = output / 'launch'
        if not (controls / 'campaign.launch.json').exists():
            controls = ARTIFACTS / 'launch' / output.name
        controls.mkdir(parents=True, exist_ok=True)
        lock_path, receipt = controls / 'campaign.lock', controls / 'campaign.launch.json'
    else:
        lock_path = output.with_name(output.name + '.lock')
        receipt = output.with_name(output.name + '.launch.json')
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        signature = {'source_manifest': sha(BASELINE / 'manifest.json'), 'feedback_driver': sha(__file__)}
        require(not (output / 'completion.json').exists(), 'Training already complete')
        if resume:
            require(read(receipt) == signature and (output / 'checkpoint.json').is_file(), 'Checkpoint differs')
        else:
            require(not output.exists() and not receipt.exists(), 'Expected fresh training output')
        bridge.configure_runtime(actor)
        if not resume:
            write(receipt, signature)
        backend = FeedbackBackend(actor, cfg, output)
        runner = bridge.AlignedRunner(config=bridge.native_config(cfg), adapter=bridge.ALFWorldAdapter(BASELINE / 'splits'),
                                      backend=backend, context=official.context_for(bridge, actor, cfg), output_dir=output)
        result = runner.run(cases=bridge.cases_for(cfg), initial_skill=(BASELINE / 'initial_skill.md').read_text(),
                            resume=resume)
        write(output / 'completion.json', {'status': 'complete', 'automatic_test': False,
              'iterations': [r.to_dict() for r in result.feedback_loop.iterations],
              'resumed_from_iteration': result.feedback_loop.resumed_from_iteration,
              'new_optimizer_logical_calls': backend.new_generations})


def test_final(training):
    actor, cfg = prepare()
    training = resolve_experiment_path(training.resolve())
    state = read(training / 'checkpoint.json')
    completion = read(training / 'completion.json')
    rounds = cfg['native']['feedback_loop']['max_iterations']
    require(completion['status'] == 'complete' and len(completion['iterations']) == rounds
            and state['next_iteration'] == rounds and state['pending_post_decision'] is None,
            'Training or Momentum is incomplete')
    skill = (training / 'final_skill.md').read_text()
    require(skill.strip() and skill == state['current_skill'], 'Final skill differs from checkpoint')
    tasks = read(BASELINE / 'splits/test/items.json')
    ids = [item['id'] for item in tasks]
    require(len(ids) == len(set(ids)) == 134 and all(uid.startswith('test:') for uid in ids),
            'Unexpected test split')
    if training.name == 'training_snapshot' and training.parent.parent == ARTIFACTS:
        output = training.parent
    else:
        output = training.with_name(training.name + '_test134')
    output.mkdir(exist_ok=True)
    with (output / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        signature = {'skill': skill, 'actor': actor, 'tasks': tasks}
        if (output / 'inputs.json').exists():
            require(read(output / 'inputs.json') == signature, 'Test inputs changed')
        else:
            require(all(p.name == '.lock' for p in output.iterdir()), 'Unexpected existing test files')
            write(output / 'inputs.json', signature)
        if (output / 'summary.json').exists():
            summary = read(output / 'summary.json')
            require(summary['status'] == 'complete' and [r['id'] for r in summary['tasks']] == ids
                    and summary['skill_sha256'] == sha(training / 'final_skill.md'), 'Test result differs')
            return summary
        bridge.configure_runtime(actor)
        rows = run_batch(actor, tasks, skill, output)
        require([r['id'] for r in rows] == ids and (output / 'actor_skill.md').read_text() == skill,
                'Final test coverage or skill differs')
        success = sum(r['hard'] for r in rows)
        summary = {'status': 'complete', 'completed': len(rows), 'success': success,
                   'success_rate': success / len(rows), 'skill_sha256': sha(output / 'actor_skill.md'),
                   'tasks': rows, 'training_updated': False}
        write(output / 'summary.json', summary)
        return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--start', metavar='OUTPUT', type=Path)
    action.add_argument('--test-only', metavar='TRAINING_OUTPUT', type=Path)
    parser.add_argument('--test-after', action='store_true', help='Test the frozen final skill after training')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if (args.test_after or args.resume) and not args.start:
        parser.error('--test-after and --resume require --start OUTPUT')
    if args.start:
        run(args.start, args.resume)
        if args.test_after:
            test_final(args.start)
    elif args.test_only:
        test_final(args.test_only)
    else:
        prepare()
        print('Dual-official ALFWorld configuration verified offline')
