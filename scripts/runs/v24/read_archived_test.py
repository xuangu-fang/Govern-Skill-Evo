"""Read a completed v24 or v24.1 ALFWorld Test from its relocated evidence."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.skill_evolution.shared.experiment_paths import resolve_experiment_path


def archive_path(value):
    """Locate a v24 receipt by its repository-relative identity after a checkout moves."""
    path = Path(value)
    if path.is_absolute() and not path.is_relative_to(ROOT):
        for parent in path.parents:
            if parent.parts[-2:] in (('experiments', 'campaigns'), ('experiments', 'evaluations'),
                                     ('artifacts', 'methods')):
                target = resolve_experiment_path(path.relative_to(parent.parent.parent))
                if target.is_relative_to(ROOT / 'artifacts/methods'):
                    return target
    return resolve_experiment_path(path)


def read_test(directory):
    directory = resolve_experiment_path(directory)
    version, run_id = directory.relative_to(ROOT / 'artifacts/methods').parts
    if version == 'v24':
        from src.skill_evolution.v24.benchmark import using_benchmark
        from src.skill_evolution.v24.benchmarks.alfworld.adapter import ALFWorldAdapter
    elif version == 'v24_1':
        from src.skill_evolution.v24_1.benchmark import using_benchmark
        from src.skill_evolution.v24_1.benchmarks.alfworld.adapter import ALFWorldAdapter
    else:
        raise ValueError('Expected a v24 or v24.1 Test archive')

    adapter = ALFWorldAdapter()
    with using_benchmark(adapter):
        return read_records(directory, run_id, adapter)


def read_records(directory, run_id, adapter):
    def read(path):
        return json.loads(path.read_bytes())

    bundle = read(directory / 'input.json')
    report = read(directory / 'summary.json')
    tasks = read(ROOT / 'benchmarks/alfworld/editions/skillopt_39_18_134/test/items.json')
    if (report['status'] != 'complete' or read(directory / 'progress.json')['status'] != 'complete'
            or bundle['tasks'] != tasks or len(report['tasks']) != report['completed'] or len(tasks) != report['completed']):
        raise ValueError('Incomplete Test or different held-out split')

    training = archive_path(bundle['campaign'])
    state = read(training / 'state.json')
    skill = (training / state['parent']).read_bytes()
    if (state != bundle['campaign_state'] or skill != bundle['skill_text'].encode()
            or skill != (directory / 'final_skill.md').read_bytes()):
        raise ValueError('Test input differs from the final training state')

    successes = 0
    for task, row in zip(tasks, report['tasks']):
        uid = task['id']
        episode = directory / 'episodes' / uid.replace(':', '_')
        path = archive_path(read(episode / 'result.json')['trajectory'])
        if path != archive_path(row['trajectory']) or episode / 'attempts' not in path.parents:
            raise ValueError(f'Trajectory differs from the receipt for {uid}')
        record = adapter.check_evaluation_record(path, uid, bundle)
        if ((uid, record['won'], len(record['steps']), record['status'])
                != (row['task_id'], row['success'], row['steps'], row['termination'])):
            raise ValueError(f'Result differs for {uid}')
        successes += record['won']
    if successes != report['success']:
        raise ValueError('Aggregate differs from individual trajectories')
    return {'run_id': run_id, 'completed': len(tasks), 'success': successes}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    print(json.dumps(read_test(parser.parse_args().directory)))
