"""Evaluate the completed V23.5 Parent using the training/Gate Actor protocol."""
from copy import deepcopy
import fcntl
from pathlib import Path

from . import evolution as ev
from .benchmark import current as benchmark_current

def prepare(experiment, campaign):
    return benchmark_current().prepare_evaluation(experiment, campaign)


def check_record(path, task, bundle):
    return benchmark_current().check_evaluation_record(path, task, bundle)


def run(root, *, experiment=None, campaign=None, resume=False,
        runner=None, bundle=None):
    root = Path(root).resolve(); root.mkdir(parents=True, exist_ok=True)
    with (root/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        bundle = prepare(experiment, campaign) if bundle is None else deepcopy(bundle)
        ev.require(not root.is_relative_to(Path(bundle['campaign'])), 'Evaluation must be outside training directory')
        if (root/'input.json').exists():
            ev.require(resume and ev.read(root/'input.json') == bundle, 'Evaluation exists or inputs changed')
            ev._check_contract(root)
        else:
            ev.require(not resume and not any(p.name != '.lock' for p in root.iterdir()), 'Nonempty evaluation output')
            ev.save(root/'input.json', bundle); ev.save(root/'contract.json', ev.frozen_contract())
        if runner is None:
            ev.check_live_environment(bundle['actor_config'])
        skill = root/'final_skill.md'
        if skill.exists():
            ev.require(skill.read_bytes().decode('utf-8') == bundle['skill_text'], 'Evaluation Skill snapshot changed')
        else:
            skill.write_bytes(bundle['skill_text'].encode('utf-8'))
        def invoke(task, skill_file, dest, cfg):
            if runner is not None:
                return runner(task, skill_file, dest, cfg)
            path = ev.actor_task(task, skill_file, dest, cfg, final=True)
            check_record(path, task, bundle)
            return path
        ev.save(root/'progress.json', {'status': 'running', 'at': ev.now()})
        try:
            paths, _ = ev._actors(root, root, 'episodes', [t['id'] for t in bundle['tasks']],
                                  skill, bundle['actor_config'], invoke, resume)
            rows = []
            for task, path in zip(bundle['tasks'], paths):
                r = check_record(path, task['id'], bundle)
                rows.append({'task_id': task['id'], 'success': r['won'], 'steps': len(r['steps']),
                             'termination': r['status'], 'trajectory': path})
            successes = sum(r['success'] for r in rows)
            result = {'status': 'complete', 'completed': len(rows), 'success': successes,
                      'success_rate': successes/len(rows), 'tasks': rows, 'cost': ev.cost_summary(root),
                      'initial_reference': bundle['initial_reference'], 'at': ev.now()}
            ev.save(root/'summary.json', result)
            ev.save(root/'progress.json', {'status': 'complete', 'at': ev.now()})
            return result
        except BaseException as exc:
            ev.save(root/'progress.json', {'status': 'stopped', 'error_type': type(exc).__name__, 'at': ev.now()})
            raise


def main():
    from .cli import evaluation_main
    evaluation_main()


if __name__ == '__main__':
    main()
