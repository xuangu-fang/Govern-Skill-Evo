"""Default selection and saved-view recovery through the real offline pipeline."""
import json

import pytest

from src.skill_evolution.v23_5 import evolution, preconditioner as pc, replay
from src.skill_evolution.v23_5.config import (
    KNOWLEDGE_ONLY, MEMORY_V3, baseline_config, method_config, validate_method)
from src.skill_evolution.v23_5.update_patch import normalize_update_patches
from .helpers import Fake, keep, memory, read
from .test_baseline import Harness, config
from .test_replay_newlines import bundle


def test_default_versions_and_reference_permissions(upstream, payload, bundle, tmp_path):
    method = method_config()
    assert method == evolution.METHOD == method_config(KNOWLEDGE_ONLY)
    assert method['memory_view'] == KNOWLEDGE_ONLY
    assert method['preconditioner_prompt'] == pc.KNOWLEDGE_PROMPT_VERSION
    assert method['replay_input_view'] == replay.KNOWLEDGE_INPUT_VIEW
    assert method['replay_prompt_version'] == replay.KNOWLEDGE_PROMPT_VERSION
    validate_method(method_config(MEMORY_V3))
    source = memory(payload)
    raw = keep(payload)
    raw['adjustments'][0]['reason'] = 'History `R1/P1:outcome`.'
    with pytest.raises(ValueError, match='allowed reference set'):
        normalize_update_patches(raw, {**payload, 'memory': source})
    normalize_update_patches(raw, {**payload, 'memory': source}, memory_view=MEMORY_V3)
    result = pc.run_preconditioner(*upstream[:2], upstream[3], generate=Fake(keep(payload)), memory=source)
    assert pc.messages_for(result) == read(upstream[3]/'messages.json')
    assert pc.model_input(result)['memory']['format'] == KNOWLEDGE_ONLY
    assert read(upstream[3]/'run.json')['prompt_version'] == method['preconditioner_prompt']

    bundle['payload']['memory'] = source
    raw = {'entries': [{'revises': [], 'knowledge': [{
        'text': 'Current observation.', 'evidence': ['diff', 'R1/P1:outcome']}]}]}
    with pytest.raises(ValueError, match='Unavailable historical reference'):
        replay.validate_result(raw, bundle['payload'])
    replay.validate_result(raw, bundle['payload'], input_view=replay.INPUT_VIEW)
    dest = tmp_path/'replay'
    replay.run_replay(bundle, dest, generate=Fake({'entries': []}))
    assert replay.messages_for(bundle) == read(dest/'messages.json')
    assert read(dest/'model_input.json')['memory']['format'] == KNOWLEDGE_ONLY
    assert read(dest/'run.json')['prompt_version'] == method['replay_prompt_version']


@pytest.mark.parametrize('view', [KNOWLEDGE_ONLY, MEMORY_V3])
@pytest.mark.parametrize('stage', ['preconditioner', 'replay'])
@pytest.mark.parametrize('stop', ['response_saved', 'valid_saved', 'retry_exhausted'])
def test_resume_preserves_frozen_view(tmp_path, monkeypatch, view, stage, stop):
    class RecoveryHarness(Harness):
        failures = 0

        def generate(self, messages, dest):
            response = super().generate(messages, dest)
            if (stop == 'retry_exhausted' and 'R02' in dest.parts
                    and stage in dest.parts and self.failures < 3):
                self.failures += 1
                response['content'] = '{'
            return response

    module = pc if stage == 'preconditioner' else replay
    write = module.write_record
    interrupted = False

    def interrupt_after_save(path, value):
        nonlocal interrupted
        write(path, value)
        target = (stop == 'response_saved' and path.name == 'response.json') or (
            stop == 'valid_saved' and path.name == 'run.json' and value.get('status') == 'valid')
        if 'R02' in path.parts and target and not interrupted:
            interrupted = True
            raise KeyboardInterrupt('Offline interruption after persistence')

    monkeypatch.setattr(module, 'write_record', interrupt_after_save)
    h = RecoveryHarness()
    # Exercise omitted defaults for new runs, explicit saved selection for v3.
    cfg = baseline_config(config()) if view == KNOWLEDGE_ONLY else baseline_config(config(), memory_view=view)
    with pytest.raises(evolution.Stopped if stop == 'retry_exhausted' else KeyboardInterrupt):
        evolution.run_campaign(tmp_path, config=cfg, generate=h.generate, actor_runner=h.actor)
    assert read(tmp_path/'state.json')['next_round'] == 2
    attempts = tmp_path/f'rounds/R02/{stage}/attempts'
    frozen_messages = read(attempts/'001/messages.json')
    assert json.loads(frozen_messages[1]['content'])['memory']['entries']
    prior_calls = h.calls.count(stage)
    if stop == 'retry_exhausted':
        with pytest.raises(evolution.Stopped, match='budget exhausted'):
            evolution.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
        assert h.calls.count(stage) == prior_calls
        assert not (attempts/'004').exists()
        return
    result = evolution.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    assert result['state']['next_round'] == 3
    assert h.calls.count(stage) == prior_calls + (stop == 'retry_exhausted')
    assert len(h.actor_calls) == 8
    assert read(tmp_path/'config.json') == cfg == read(tmp_path/'initial_config.json')
    selected = tmp_path/f'rounds/R02/{stage}'/read(tmp_path/f'rounds/R02/{stage}/result.json')['path']
    if stop == 'response_saved':
        assert selected == attempts/'001/recovered'
        assert read(selected/'recovered_from.json')['additional_requests'] == 0
    if stop == 'retry_exhausted':
        assert selected == attempts/'004'
    for path in attempts.rglob('messages.json'):
        assert read(path) == frozen_messages
    for name, loader, view_key, prompt_key in (
        ('preconditioner', pc.load_preconditioner, 'memory_view', 'preconditioner_prompt'),
        ('replay', replay.load_replay, 'input_view', 'replay_prompt_version'),
    ):
        folder = tmp_path/f'rounds/R02/{name}'
        chosen = folder/read(folder/'result.json')['path']
        loader(chosen)
        meta = read(chosen/'run.json')
        assert meta[view_key] == cfg['method']['memory_view' if name == 'preconditioner' else 'replay_input_view']
        assert meta['prompt_version'] == cfg['method'][prompt_key]
        assert ('Knowledge Only input view' in read(chosen/'messages.json')[0]['content']) == (view == KNOWLEDGE_ONLY)
    calls = len(h.calls), len(h.actor_calls)
    evolution.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    assert calls == (len(h.calls), len(h.actor_calls))
