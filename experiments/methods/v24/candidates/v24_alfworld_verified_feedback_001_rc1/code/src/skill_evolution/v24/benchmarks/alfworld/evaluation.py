from src.skill_evolution.v24.benchmarks.alfworld.actor.skill_runtime import protocol_settings
from src.skill_evolution.v24.benchmarks.alfworld.actor.skill_runtime import execution_protocol, LEGACY_INJECTION, LEGACY_OUTPUT
from .facts import COMPLETE
from copy import deepcopy


from pathlib import Path

from src.skill_evolution.v24 import evolution as ev

from src.skill_evolution.v24.benchmarks.alfworld.actor.run_task import SPLIT_ROOT


from src.skill_evolution.v24.benchmarks.alfworld.actor.response_archive import verify_response_archive

from src.skill_evolution.v24.benchmarks.alfworld.actor.verify_skill_run import verify_action_feedback

EXPERIMENT = ev.ROOT/'experiments/methods/v24/alfworld_verified_feedback_001'


CAMPAIGN = ev.ROOT/'artifacts/methods/v24/alfworld_verified_feedback_001/S1'


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
    files = {}
    for task in tasks:
        game = Path(cfg['environment_root'])/task['gamefile']
        for path in (game, game.parent/'initial_state.pddl'):
            data = path.read_bytes()
            files[str(path)] = data.decode('utf-8')
    actor = deepcopy(cfg)
    actor.update(task_items={t['id']: t for t in tasks}, environment_files=files)
    reference = ev.read(experiment/'config/initial_baseline_reference.json')
    return {'campaign': str(campaign), 'campaign_config': cfg, 'actor_config': actor,
            'campaign_state': ev.read(campaign/'state.json'), 'tasks': tasks,
            'skill_path': str(skill), 'skill_text': skill.read_bytes().decode('utf-8'),
            'initial_reference': reference, 'runtime': ev.runtime_snapshot(cfg)}


def check_record(path, task, bundle):
    record = ev.read(path); cfg = bundle['actor_config']
    ev.require(record['task'] == cfg['task_items'][task] and record['split'] == 'test'
               and record['purpose'] == 'final', 'Wrong final Test task/purpose')
    ev.require(record['skill']['text'] == bundle['skill_text'], 'Wrong final Skill')
    ev.require(record['model'] == cfg['actor_model'] and protocol_settings(record['protocol']) == protocol_settings(execution_protocol(
        cfg['max_steps'], cfg.get('actor_skill_injection', LEGACY_INJECTION),
        output_format=cfg.get('actor_output_format', LEGACY_OUTPUT),
        retry_invalid_actions=cfg.get('actor_retry_invalid_actions', False),
        action_feedback=cfg.get('actor_action_feedback', False))), 'Actor protocol differs')
    ev.require(record['request_policy'] == {'max_attempts': cfg['actor_request_attempts'],
               'strict_response': True}, 'Actor request policy differs')
    expected_backend = cfg['call_config']['endpoint']
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
            ev.require(attempt['request_parameters'] == params, 'Actual Actor request differs')
            verify_response_archive(path, attempt)
    ev.build_facts([record])  # Reconstruct and verify every observation/history/Skill prompt.
    ev.require(record['status'] in COMPLETE and type(record['won']) is bool
               and not record.get('error_type'), 'Incomplete/technical Test outcome')
    return record

