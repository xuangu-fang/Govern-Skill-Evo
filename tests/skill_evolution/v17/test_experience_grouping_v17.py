import json
from dataclasses import replace

import pytest

from src.skill_evolution.v17.experience_cards_v17 import ExperienceCardBatch
from src.skill_evolution.v17.experience_grouping_contract_v17 import EvolutionExperienceRef, GroupingScope
from src.skill_evolution.v17.experience_grouping_v17 import ALIAS_SEED, MODEL, SYSTEM_PROMPT, GroupingRunError, prepare_grouping_request, run_experience_grouping


@pytest.fixture
def case():
    refs = tuple(EvolutionExperienceRef(f'local-{i}', 'public-context', f'trace-{i}') for i in range(12))
    scope = GroupingScope('r1', 'parent', refs)
    payload = {'contexts': [{'context_ref': 'public-context', 'visible_policy': 'Ask first.',
                             'public_tools': []}],
               'cards': [{'task_ref': r.task_ref, 'context_ref': r.context_ref,
                          'trajectory_ref': r.trajectory_ref,
                          'events': [{'step': 1, 'actor': 'user', 'event_type': 'message',
                                      'content': f'Observed request {i}'}]}
                         for i, r in enumerate(refs)]}
    return ExperienceCardBatch(json.dumps(payload), {}), scope


def answer(request):
    members = list(request['alias_to_source']['task_ref'])
    return {'groups': [{'group_id': 'G1', 'members': members,
                        'decision_problem': 'When to act?', 'shared_basis': 'Similar decisions.',
                        'important_differences': []}]}


def test_aliases_are_fixed_order_independent_and_lossless(case):
    batch, scope = case
    request = prepare_grouping_request(batch, scope=scope)
    payload = batch.payload
    payload['cards'].reverse()
    other = prepare_grouping_request(ExperienceCardBatch(json.dumps(payload), {}),
                                     scope=replace(scope, experiences=tuple(reversed(scope.experiences))))
    assert request == other
    assert request == prepare_grouping_request(batch, scope=replace(scope, round_id='r2', parent_skill_digest='new'))
    assert request['alias_seed'] == ALIAS_SEED == 200
    assert 'local-' not in request['user_prompt']
    assert 'trace-' not in request['user_prompt']
    assert 'public-context' not in request['user_prompt']
    cards = json.loads(request['user_prompt'])['cards']
    original = {c['task_ref']: c for c in batch.payload['cards']}
    order = [request['alias_to_source']['task_ref'][c['task_ref']] for c in cards]
    assert order != sorted(original)
    for c in cards:
        assert c['events'] == original[request['alias_to_source']['task_ref'][c['task_ref']]]['events']


def test_single_call_and_audit(case, tmp_path):
    batch, scope = case
    request = prepare_grouping_request(batch, scope=scope)
    calls = []
    def transport(model, system, user, **kwargs):
        calls.append(user)
        assert model == MODEL and system == SYSTEM_PROMPT
        assert kwargs['temperature'] == 0
        assert kwargs['response_format']['json_schema']['strict'] is True
        assert (tmp_path / 'run/grouping_request.json').exists()
        return json.dumps(answer(request)), MODEL.removeprefix('openai/'), {'prompt_tokens': 100}
    result = run_experience_grouping(batch, scope=scope, artifact_dir=tmp_path / 'run', learner_call=transport)
    assert len(calls) == 1
    assert set(result['groups'][0]['members']) == {r.task_ref for r in scope.experiences}
    assert result['round_id'] == 'r1'
    assert json.loads((tmp_path / 'run/grouping_attempts.json').read_text())[0]['status'] == 'valid'
    with pytest.raises(FileExistsError):
        run_experience_grouping(batch, scope=scope, artifact_dir=tmp_path / 'run', learner_call=transport)
    assert len(calls) == 1


@pytest.mark.parametrize('bad', ['not JSON', '{"groups":[],"groups":[]}', '{"groups":[]}',
                                  '{"groups":NaN}'])
def test_one_repair_reuses_input(case, tmp_path, bad):
    batch, scope = case
    request = prepare_grouping_request(batch, scope=scope)
    users = []
    def transport(model, system, user, **kwargs):
        users.append(user)
        return (bad if len(users) == 1 else json.dumps(answer(request))), 'deepseek-v4-pro', None
    run_experience_grouping(batch, scope=scope, artifact_dir=tmp_path / 'run', learner_call=transport)
    assert len(users) == 2
    assert json.loads(users[1])['original_input'] == json.loads(users[0])


def test_failure_is_recorded_without_fallback(case, tmp_path):
    batch, scope = case
    calls = []
    def transport(*args, **kwargs):
        calls.append(1)
        return '{"groups":[]}', 'deepseek-v4-pro', {}
    with pytest.raises(GroupingRunError, match='one repair'):
        run_experience_grouping(batch, scope=scope, artifact_dir=tmp_path / 'run', learner_call=transport)
    assert len(calls) == 2
    assert not (tmp_path / 'run/validated_groups.json').exists()
    assert len(json.loads((tmp_path / 'run/grouping_attempts.json').read_text())) == 2


@pytest.mark.parametrize('wrong_model', [False, True])
def test_transport_failure_or_model_drift(case, tmp_path, wrong_model):
    batch, scope = case
    def transport(*args, **kwargs):
        if wrong_model:
            return '{}', 'other-model', None
        raise RuntimeError('provider failure')
    with pytest.raises(GroupingRunError, match='transport failed'):
        run_experience_grouping(batch, scope=scope, artifact_dir=tmp_path / 'run', learner_call=transport)
    records = json.loads((tmp_path / 'run/grouping_attempts.json').read_text())
    assert len(records) == 1 and records[0]['status'] == 'transport_failed'
