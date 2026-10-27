"""Exercise the previously bypassed final-evaluation bundle construction."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.skill_evolution.v24 import evolution as ev, evaluation
from src.skill_evolution.v24.benchmark import current
from src.skill_evolution.v24.benchmarks.alfworld import evaluation as adapter_eval
from .test_review_paths import migrated


@pytest.fixture
def preparation(tmp_path, monkeypatch):
    experiment, campaign = tmp_path/'experiment', tmp_path/'S1'
    value = migrated()
    pool = {tid: {'id': tid, 'gamefile': tid.replace(':', '_')+'.pddl'} for tid in value['batches'][0]}
    value.update(task_items=pool, environment_root=str(tmp_path/'environment'))
    tasks = [{'id': f'test:{i:04}', 'gamefile': f'{i}/game.tw-pddl', 'task_type': 'fixture'} for i in range(134)]
    files = {}
    for task in tasks:
        for name in ('game.tw-pddl', 'initial_state.pddl'):
            path = Path(value['environment_root'])/Path(task['gamefile']).parent/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f'offline environment fixture {task["id"]} {name}')
            files[str(path)] = str(path)
    ev.initialize(campaign, value)
    ev.save(experiment/'config/campaign.json', value)
    ev.save(experiment/'data/test.json', tasks)
    ev.save(tmp_path/'splits/test/items.json', tasks)
    historical = tmp_path/'historical_reference.json'
    historical.write_text('{"success": 1}')
    reference = {'source': str(historical),
                 'remeasure': False, 'comparable_to_current_protocol': False}
    ev.save(experiment/'config/initial_baseline_reference.json', reference)
    skill = campaign/'final_skill.md'; skill.write_text('Frozen test fixture Skill.\n')
    # Publication is independently checked by campaign tests. Only its result and
    # runtime metadata are substituted here; all manifest/environment checks run.
    monkeypatch.setattr(ev, 'final_parent', lambda root: skill)
    runtime = {'packages': {'alfworld': 'fixture', 'textworld': 'fixture', 'requests': 'fixture'}}
    monkeypatch.setattr(ev, 'runtime_snapshot', lambda cfg: runtime)
    monkeypatch.setattr(adapter_eval, 'SPLIT_ROOT', tmp_path/'splits')
    return experiment, campaign, value, tasks, runtime


def test_prepare_checks_frozen_inputs_and_matches_legacy(preparation, monkeypatch):
    from src.skill_evolution.v23_5 import evaluation as legacy
    experiment, campaign, value, tasks, runtime = preparation
    actual = evaluation.prepare(experiment, campaign)
    monkeypatch.setattr(legacy, 'SPLIT_ROOT', adapter_eval.SPLIT_ROOT)
    monkeypatch.setattr(legacy.ev, '_config', lambda _: value)
    monkeypatch.setattr(legacy.ev, 'final_parent', ev.final_parent)
    monkeypatch.setattr(legacy.ev, 'runtime_snapshot', lambda _: runtime)
    assert actual['skill_text'] == ev.final_parent(campaign).read_text()
    assert actual['tasks'] == tasks and len(actual['actor_config']['environment_files']) == 268
    assert actual['actor_config']['task_items'] == {t['id']: t for t in tasks}
    assert actual['campaign_config'] == value and set(value['task_items']).isdisjoint(actual['actor_config']['task_items'])


@pytest.mark.parametrize('mutation', ['config', 'manifest', 'duplicate', 'overlap', 'incomplete'])
def test_prepare_rejects_changed_inputs_before_actor(preparation, monkeypatch, mutation):
    experiment, campaign, value, tasks, runtime = preparation
    if mutation == 'config':
        changed = deepcopy(value); changed['max_steps'] = 49
        ev.save(experiment/'config/campaign.json', changed)
    elif mutation in ('manifest', 'duplicate', 'overlap'):
        changed = deepcopy(tasks)
        if mutation == 'manifest': changed[0]['task_type'] = 'changed'
        elif mutation == 'duplicate': changed[1] = changed[0]
        else: changed[0]['gamefile'] = next(iter(value['task_items'].values()))['gamefile']
        ev.save(experiment/'data/test.json', changed)
        if mutation != 'manifest': ev.save(adapter_eval.SPLIT_ROOT/'test/items.json', changed)
    elif mutation == 'environment':
        (Path(value['environment_root'])/tasks[0]['gamefile']).write_text('changed')
    elif mutation == 'reference':
        (experiment.parent/'historical_reference.json').write_text('changed')
    else:
        def incomplete(_): raise ValueError('Campaign is not complete')
        monkeypatch.setattr(ev, 'final_parent', incomplete)
    with pytest.raises(ValueError):
        evaluation.prepare(experiment, campaign)
