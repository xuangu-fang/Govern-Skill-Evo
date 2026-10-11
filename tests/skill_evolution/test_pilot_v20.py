import json
from pathlib import Path

import pytest

from skill_evolution.pilot_v20 import (
    PilotRejected,
    pilot_config_v20,
    run_v20_pilot,
    validate_pilot_result,
)
from skill_evolution.comparison_v20 import (
    comparison_config_v20,
    run_v20_comparison,
    validate_comparison,
)


TASKS = [
    {'task_id': 'task-b', 'family': 'checkout'},
    {'task_id': 'task-a', 'family': 'search'},
]


def test_pilot_isolated_binding_and_numeric_metrics(tmp_path):
    seen = {}

    def fake_campaign_runner(**kwargs):
        seen['output'] = Path(kwargs['output'])
        seen['config'] = kwargs['config']
        Path(kwargs['output']).mkdir(parents=True)
        return {'schema_version': 'campaign_report_v20.1', 'status': 'COMPLETE',
                'committed_rounds': 1, 'rounds': []}

    result = run_v20_pilot(
        output=tmp_path / 'pilot', run_id='pilot-1', initial_skill='skill-v20',
        task_manifest=TASKS, round_factory=lambda _ctx: None,
        post_generation=lambda _ctx: None,
        measurement=lambda report: {'success_rate': 0.75, 'rounds': report['committed_rounds']},
        config=pilot_config_v20(round_limit=1, seed=17),
        campaign_runner=fake_campaign_runner,
    )
    payload = validate_pilot_result(result, task_manifest=TASKS, run_id='pilot-1')
    assert payload['config']['seed'] == 17
    assert payload['metrics'] == {'success_rate': 0.75, 'rounds': 1}
    assert seen['output'] == tmp_path / 'pilot' / 'campaign'
    assert seen['config']['round_limit'] == 1
    assert (tmp_path / 'pilot' / 'pilot-binding.json').exists()

    with pytest.raises(PilotRejected, match='Pilot binding changed'):
        run_v20_pilot(
            output=tmp_path / 'pilot', run_id='pilot-1', initial_skill='changed',
            task_manifest=TASKS, round_factory=lambda _ctx: None,
            post_generation=lambda _ctx: None,
            config=pilot_config_v20(round_limit=1, seed=17),
            campaign_runner=fake_campaign_runner, resume=True,
        )


def test_pilot_does_not_accept_private_or_non_numeric_measurements(tmp_path):
    def fake_campaign_runner(**kwargs):
        Path(kwargs['output']).mkdir(parents=True)
        return {'committed_rounds': 0}

    with pytest.raises(PilotRejected, match='metrics must be numeric'):
        run_v20_pilot(
            output=tmp_path / 'pilot', run_id='pilot-2', initial_skill='skill',
            task_manifest=TASKS, round_factory=lambda _ctx: None,
            post_generation=lambda _ctx: None,
            measurement=lambda _report: {'private_gate': {'accepted': True}},
            campaign_runner=fake_campaign_runner,
        )


def test_comparison_pairs_same_manifest_and_keeps_public_surface(tmp_path):
    seen = {}
    families = {}

    def public_runner(condition, output, tasks, seed):
        seen[condition] = Path(output)
        Path(output).mkdir(parents=True, exist_ok=True)
        families[condition] = [task['family'] for task in tasks]
        tasks[0]['family'] = 'runner-local-mutation'
        base = 0.8 if condition == 'v20_memory' else 0.6
        return {
            'status': 'COMPLETE', 'seed': seed,
            'task_metrics': {task['task_id']: {'success': base + (0.1 if task['task_id'] == 'task-a' else 0)}
                             for task in tasks},
            'private_monitor_trace': {'secret': True},
        }

    report = run_v20_comparison(
        output=tmp_path / 'comparison', task_manifest=TASKS,
        condition_runner=public_runner,
        config=comparison_config_v20(seed=23), run_id='cmp-1',
    )
    validate_comparison(report, task_manifest=TASKS)
    assert seen['v20_memory'] != seen['no_memory']
    assert families['v20_memory'] == families['no_memory'] == ['search', 'checkout']
    paired = report['paired_metrics']['success']
    assert paired['mean_delta'] == pytest.approx(0.2)
    assert paired['wins'] == 2 and paired['ties'] == 0 and paired['losses'] == 0
    persisted = json.loads((tmp_path / 'comparison' / 'v20_memory' / 'condition-result.json').read_text())
    assert 'private_monitor_trace' not in persisted


def test_comparison_rejects_manifest_mismatch_and_non_numeric_metric(tmp_path):
    def bad_runner(_condition, output, _tasks, _seed):
        Path(output).mkdir(parents=True, exist_ok=True)
        return {'task_metrics': {'task-a': {'success': 'high'}, 'task-b': {'success': 0.2}}}

    with pytest.raises(PilotRejected, match='task metric must be finite numeric'):
        run_v20_comparison(output=tmp_path / 'bad', task_manifest=TASKS,
                           condition_runner=bad_runner)
