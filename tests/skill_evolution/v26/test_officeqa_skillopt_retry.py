"""Offline regressions through native SkillOpt reflection and the OfficeQA launcher."""
import json
from pathlib import Path
import socket

import httpx
import pytest
from skillopt.gradient import reflect
from skillopt.model import openai_compatible_backend as backend, set_optimizer_backend

from src.adapters.officeqa import launchers, skillopt_optimizer
from src.adapters.officeqa.skillopt_budget import TrainingPaused
from .test_native_launchers import recipe


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail('Unexpected network connection')
    monkeypatch.setattr(socket.socket, 'connect', deny)


def setup_optimizer(monkeypatch):
    model = launchers.read(Path(launchers.ROOT) / 'experiments/configs/officeqa_skillopt_deepseek_flash.json')['optimizer']
    monkeypatch.setenv(model['api_key_env'], 'offline')
    launchers._optimizer({'config': {'optimizer': model}, 'method': 'skillopt'}, None, None)
    set_optimizer_backend('openai_compatible')


def reply(reason, text):
    return httpx.Response(200, json={'choices': [{'finish_reason': reason, 'message': {
        'role': 'assistant', 'content': text, 'reasoning_content': 'PRIVATE_REASONING'}}],
        'usage': {'prompt_tokens': 12, 'completion_tokens': 16384}})


def run_reflection(root):
    step = root / 'steps/step_0001'
    pred = step / 'rollout/predictions'
    for uid in ('a', 'b'):
        path = pred / uid / 'conversation.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('[{"role":"assistant","content":"offline trajectory"}]')
    return reflect.run_minibatch_reflect(results=[{'id': 'a', 'hard': 0}, {'id': 'b', 'hard': 1}],
        skill_content='initial', prediction_dir=str(pred), patches_dir=str(step / 'patches'), workers=2,
        failure_only=False, minibatch_size=8, random_seed=42)


def test_stop_repair_keeps_only_latest_full_response_and_saves_empty_patches(tmp_path, monkeypatch):
    setup_optimizer(monkeypatch)
    bodies = []
    malformed = '{"patch":{"edits": [}' + ' ' * 20000
    invalid = '{"patch":{"edits":[{"op":"replace","content":"retained"}]}}'
    empty = '{"patch":{"edits":[]}}'

    def send(request):
        body = json.loads(request.content)
        bodies.append(body)
        messages = body['messages']
        if '## Failed Trajectories' not in messages[1]['content']:
            return reply('stop', empty)
        if len(messages) == 2:
            return reply('stop', malformed)
        assert len(messages) == 4 and 'PRIVATE_REASONING' not in json.dumps(messages)
        if messages[2]['content'] == malformed:
            assert 'line 1 column' in messages[3]['content']
            return reply('stop', invalid)
        assert messages[2]['content'] == invalid and 'edits[0].target' in messages[3]['content']
        assert 'Preserve all unaffected content' in messages[3]['content']
        return reply('stop', empty)

    with skillopt_optimizer.configured_provider(tmp_path, http_transport=httpx.MockTransport(send)):
        patches = run_reflection(tmp_path)
    paths = sorted((tmp_path / 'steps/step_0001/patches').glob('*.json'))
    assert [p.name for p in paths] == ['minibatch_fail_000.json', 'minibatch_succ_000.json']
    assert all(launchers.read(p)['patch'] == {'edits': []} for p in paths)
    assert len(bodies) == 4 and all(b['max_tokens'] == 16384 for b in bodies)
    repaired = [b['messages'] for b in bodies if '## Failed Trajectories' in b['messages'][1]['content']]
    assert all(m[:2] == repaired[0] for m in repaired)
    with skillopt_optimizer.configured_provider(tmp_path, http_transport=httpx.MockTransport(send)):
        assert run_reflection(tmp_path) == patches
    assert len(bodies) == 4


@pytest.mark.parametrize('sixth', ['valid', 'length', 'interrupted'])
def test_three_length_then_double_with_interrupt_and_persistent_sixth(tmp_path, monkeypatch, sixth):
    setup_optimizer(monkeypatch)
    bodies = []

    class Interrupted(BaseException):
        pass

    def send(request):
        body = json.loads(request.content)
        bodies.append(body)
        if len(bodies) == 4 or (len(bodies) == 6 and sixth == 'interrupted'):
            raise Interrupted
        if len(bodies) == 6 and sixth == 'valid':
            return reply('stop', '{"slow_update_content":"guidance"}')
        return reply('length', '{"slow_update_content":"incomplete')

    def call(task):
        return backend.chat_optimizer('system', task, stage='slow_update', max_completion_tokens=8192)

    def provider():
        return skillopt_optimizer.configured_provider(tmp_path, http_transport=httpx.MockTransport(send))

    with pytest.raises(Interrupted), provider():
        call('original task')
    if sixth == 'valid':
        with provider():
            assert json.loads(call('regenerated task')[0])['slow_update_content'] == 'guidance'
        with provider():
            call('regenerated task')
    else:
        with pytest.raises(Interrupted if sixth == 'interrupted' else TrainingPaused), provider():
            call('regenerated task')
        with pytest.raises(TrainingPaused), provider():
            pytest.fail('Exhausted optimizer must pause before entering trainer')
        assert launchers.read(tmp_path / 'optimizer_paused.json')['attempts'] == 6
    assert [b['max_tokens'] for b in bodies] == [8192] * 3 + [16384] * 3
    assert all(b['messages'] == bodies[0]['messages'] for b in bodies)


def test_mixed_errors_share_six_slots(tmp_path, monkeypatch):
    setup_optimizer(monkeypatch)
    cases = [('stop', ''), ('length', '{}'), ('stop', '{"meta_skill_content":12}'),
             ('length', '{}'), ('length', '{}'), ('stop', '')]
    seen = []

    def send(request):
        seen.append(json.loads(request.content))
        return reply(*cases[len(seen) - 1])

    with pytest.raises(TrainingPaused), skillopt_optimizer.configured_provider(
            tmp_path, http_transport=httpx.MockTransport(send)):
        backend.chat_optimizer('system', 'task', stage='meta_skill')
    assert [b['max_tokens'] for b in seen] == [16384] * 5 + [32768]
    assert seen[1]['messages'] == seen[2]['messages']
    assert seen[1]['messages'][-2] == {'role': 'assistant', 'content': ''}
    assert seen[3]['messages'] == seen[4]['messages'] == seen[5]['messages']
    assert seen[-1]['messages'][-2]['content'] == cases[2][1]


def test_epoch_two_exhaustion_pauses_real_launcher_before_no_content(office, monkeypatch):
    cfg, actor, actor_calls = recipe(office, 'skillopt', monkeypatch)
    cfg['native'].update(num_epochs=3, batch_size=1, use_slow_update=True,
                         slow_update_samples=2, slow_update_gate_with_selection=True)
    cfg['optimizer']['max_tokens'] = 16384
    monkeypatch.setenv(cfg['optimizer']['api_key_env'], 'offline')
    root = office[0] / 'training-fixture'
    slow_requests = []
    recorded = []

    def send(request):
        body = json.loads(request.content)
        recorded.append(body)
        if "## Previous Slow Update Guidance" in body['messages'][1]['content']:
            slow_requests.append(body)
            return reply('length', '')
        return reply('stop', '{"patch":{"edits":[{"op":"append","content":"Synthetic edit"}]}}')

    original = skillopt_optimizer.configured_provider
    monkeypatch.setattr(skillopt_optimizer, 'configured_provider',
                        lambda path: original(path, http_transport=httpx.MockTransport(send)))
    with pytest.raises(TrainingPaused):
        launchers.train(cfg, root, transport=actor)
    native = root / 'native'
    assert launchers.read(native / 'runtime_state.json')['last_completed_step'] == 4
    assert not (native / 'slow_update/epoch_02/slow_result.json').exists()
    assert not (native / 'steps/step_0005').exists() and not (root / 'result.json').exists()
    assert [b['max_tokens'] for b in slow_requests] == [16384] * 3 + [32768] * 3
    paused = launchers.read(native / 'optimizer_paused.json')
    folder = native / 'model_calls' / paused['call']
    assert paused['stage'] == 'slow_update' and len(list(folder.glob('http_*_request.json'))) == 6
    assert json.loads((folder / 'http_006_response_body.bin').read_bytes())['choices'][0]['finish_reason'] == 'length'
    before = len(actor_calls), len(recorded)
    with pytest.raises(TrainingPaused):
        launchers.train(cfg, root, transport=actor, resume=True)
    assert (len(actor_calls), len(recorded)) == before


def test_invalid_ordinary_update_pauses_before_selection(office, monkeypatch):
    cfg, actor, actor_calls = recipe(office, 'skillopt', monkeypatch)
    monkeypatch.setenv(cfg['optimizer']['api_key_env'], 'offline')
    cfg['native'].update(minibatch_size=8, failure_only=False)
    requests = []

    def send(request):
        requests.append(json.loads(request.content))
        return reply('stop', '{"patch":{}}')

    original = skillopt_optimizer.configured_provider
    monkeypatch.setattr(skillopt_optimizer, 'configured_provider',
                        lambda path: original(path, http_transport=httpx.MockTransport(send)))
    root = office[0] / 'ordinary-fixture'
    with pytest.raises(TrainingPaused):
        launchers.train(cfg, root, transport=actor)
    step = root / 'native/steps/step_0001'
    assert len(requests) == 6 and len(list((step / 'patches').glob('*.json'))) == 0
    assert not (step / 'step_record.json').exists() and not (step / 'selection_eval').exists()
    assert launchers.read(root / 'native/optimizer_paused.json')['stage'] == 'analyst'
    previous = len(actor_calls)
    with pytest.raises(TrainingPaused):
        launchers.train(cfg, root, transport=actor, resume=True)
    assert len(requests) == 6 and len(actor_calls) == previous


def test_merge_and_ranking_validate_stage_output(tmp_path, monkeypatch):
    from skillopt.gradient import aggregate
    from skillopt.optimizer.clip import rank_and_select

    setup_optimizer(monkeypatch)
    edits = [{'op': 'append', 'content': letter} for letter in 'abc']
    answers = iter(['{"patch":{"edits":[]}}', '{"edits":[]}',
                    '{"selected_indices":[9,9]}', '{"selected_indices":[2,0]}'])
    calls = []

    def send(request):
        calls.append(json.loads(request.content)['messages'])
        return reply('stop', next(answers))

    with skillopt_optimizer.configured_provider(tmp_path, http_transport=httpx.MockTransport(send)):
        merged = aggregate._merge_batch('skill', [{'edits': edits}], 'system', 'patch')
        ranked = rank_and_select('skill', {'edits': edits}, 2)
    assert merged == {'edits': []} and ranked['edits'] == [edits[2], edits[0]]
    assert 'Expected edits array' in calls[1][-1]['content']
    assert 'indices' in calls[3][-1]['content']
