"""Evaluate the completed V23.5 Parent using the training/Gate Actor protocol."""
from copy import deepcopy
import fcntl
import hashlib
from pathlib import Path

from . import evolution as ev
from src.adapters.alfworld.run_task import SPLIT_ROOT
from src.adapters.alfworld.skill_runtime import context_fingerprint, execution_fingerprint, object_digest
from src.adapters.alfworld.response_archive import verify_response_archive
from src.adapters.alfworld.verify_skill_run import verify_action_feedback

EXPERIMENT = ev.ROOT/'experiments/methods/v23_5/alfworld_action_feedback_001'
CAMPAIGN = ev.ROOT/'artifacts/methods/v23_5/alfworld_action_feedback_001/S1'
OUTPUT = CAMPAIGN.parent/'evaluation/final'


def prepare(experiment=EXPERIMENT, campaign=CAMPAIGN):
    experiment, campaign = Path(experiment).resolve(), Path(campaign).resolve()
    cfg = ev.read(experiment/'config/campaign.json')
    ev.require(ev._config(campaign) == cfg, 'Training/evaluation configuration differs')
    skill = ev.final_parent(campaign)  # Checks source, runtime and every published Gate.
    ev.require(skill is not None, 'This initial-Skill experiment requires a final Skill')
    tasks = ev.read(experiment/'data/test.json')
    ev.require(len(tasks) == 134 and tasks == ev.read(SPLIT_ROOT/'test/items.json'), 'Test manifest differs')
    ev.require(len({t['id'] for t in tasks}) == len({t['gamefile'] for t in tasks}) == 134, 'Duplicate Test task')
    pool = list(cfg['task_items'].values())
    ev.require(not {t['id'] for t in tasks} & {t['id'] for t in pool}
               and not {t['gamefile'] for t in tasks} & {t['gamefile'] for t in pool}, 'Test overlaps optimization')
    provenance = ev.read(experiment/'config/provenance.json')
    files = {}
    for task in tasks:
        game = Path(cfg['environment_root'])/task['gamefile']
        for path in (game, game.parent/'initial_state.pddl'):
            data = path.read_bytes()
            ev.require(hashlib.sha256(data).hexdigest() == provenance['environment_sha256'][str(path)],
                       'Frozen Test environment differs')
            files[str(path)] = data.decode('utf-8')
    actor = deepcopy(cfg)
    actor.update(task_items={t['id']: t for t in tasks}, environment_files=files)
    reference = ev.read(experiment/'config/initial_baseline_reference.json')
    source = ev.ROOT/reference['source']
    ev.require(hashlib.sha256(source.read_bytes()).hexdigest() == reference['source_sha256'],
               'SkillOpt reference result changed')
    return {'campaign': str(campaign), 'campaign_config': cfg, 'actor_config': actor,
            'campaign_state': ev.read(campaign/'state.json'), 'tasks': tasks,
            'skill_path': str(skill), 'skill_text': skill.read_bytes().decode('utf-8'),
            'initial_reference': reference, 'runtime': ev.runtime_snapshot(cfg)}


def check_record(path, task, bundle):
    record = ev.read(path); cfg = bundle['actor_config']
    ev.require(record['task'] == cfg['task_items'][task] and record['split'] == 'test'
               and record['purpose'] == 'final', 'Wrong final Test task/purpose')
    ev.require(record['skill']['text'] == bundle['skill_text'], 'Wrong final Skill')
    ev.require(record['model'] == cfg['actor_model'] and record['protocol'] == ev.execution_protocol(
        cfg['max_steps'], cfg.get('actor_skill_injection', ev.LEGACY_INJECTION),
        output_format=cfg.get('actor_output_format', ev.LEGACY_OUTPUT),
        retry_invalid_actions=cfg.get('actor_retry_invalid_actions', False),
        action_feedback=cfg.get('actor_action_feedback', False)), 'Actor protocol differs')
    ev.require(record['request_policy'] == {'max_attempts': cfg['actor_request_attempts'],
               'strict_response': True}, 'Actor request policy differs')
    ev.require(record['context_fingerprint'] == context_fingerprint(record)
               and record['execution_fingerprint'] == execution_fingerprint(record), 'Actor fingerprint differs')
    expected_backend = hashlib.sha256(cfg['call_config']['endpoint'].encode()).hexdigest()
    ev.require(record['backend_id'] == expected_backend, 'Actor endpoint differs')
    for name in ('alfworld', 'textworld', 'requests'):
        ev.require(record['versions'][name] == bundle['runtime']['packages'][name], 'Actor runtime differs')
    params = {k: v for k, v in cfg['call_config'].items() if k not in ('endpoint', 'timeout_seconds')}
    for step in record['steps']:
        if cfg.get('actor_action_feedback'):
            verify_action_feedback(step)
        attempts = step.get('transport_attempts', [])
        ev.require(1 <= len(attempts) <= cfg['actor_request_attempts'], 'Missing/excess Actor attempts')
        for attempt in attempts:
            ev.require(attempt['request_parameters'] == params and attempt['request_sha256'] ==
                       object_digest({**params, 'messages': attempt['messages'] if cfg.get('actor_action_feedback')
                                      else step['messages']}), 'Actual Actor request differs')
            verify_response_archive(path, attempt)
    ev.build_facts([record])  # Reconstruct and verify every observation/history/Skill prompt.
    ev.require(record['status'] in ev.COMPLETE and type(record['won']) is bool
               and not record.get('error_type'), 'Incomplete/technical Test outcome')
    return record


def run(root=OUTPUT, *, experiment=EXPERIMENT, campaign=CAMPAIGN, resume=False,
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
    import argparse, json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['run', 'resume', 'status'])
    parser.add_argument('--root', type=Path, default=OUTPUT)
    parser.add_argument('--experiment', type=Path, default=EXPERIMENT)
    parser.add_argument('--campaign', type=Path, default=CAMPAIGN)
    args = parser.parse_args()
    if args.action == 'status':
        result = {'completed': len(list((args.root/'episodes').glob('*/result.json'))),
                  'progress': ev.read(args.root/'progress.json') if (args.root/'progress.json').exists() else None}
    else:
        result = run(args.root, experiment=args.experiment, campaign=args.campaign, resume=args.action == 'resume')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
