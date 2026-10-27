"""Per-module budgets reach HTTP bodies, retries, frozen metadata and resume."""
from copy import deepcopy
import json

import pytest
import requests

from src.skill_evolution.v23_5 import evolution as ev
from src.skill_evolution.v23_5.config import method_config
from src.skill_evolution.v23_5.output_feedback import POLICY, LEGACY
from .test_baseline import Harness, config


@pytest.mark.parametrize('policy', [POLICY, LEGACY])
def test_module_budgets_on_wire_and_reload(tmp_path, monkeypatch, policy):
    cfg = config(1); cfg['method'] = method_config(retry_policy=policy)
    cfg['module_max_tokens'] = {'preconditioner': 32768, 'replay': 32768}
    h = Harness(); wire = []; counts = {}
    scratch = tmp_path/'wire'; scratch.mkdir()
    def post(session, endpoint, **kwargs):
        body = kwargs['json']; messages = body['messages']
        stage = messages[0]['content'].splitlines()[0][2:].split()[0].lower()
        wire.append((stage, deepcopy(body)))
        counts[stage] = counts.get(stage, 0) + 1
        generated = h.generate(messages, scratch)
        # Retry a validation error and a truncation at the same frozen stage budget.
        if stage == 'preconditioner' and counts[stage] == 1: generated['content'] = '{}'
        if stage == 'replay' and counts[stage] == 1: generated['finish_reason'] = 'length'
        response = requests.Response(); response.status_code = 200
        response._content = json.dumps({'choices': [{'message': {'content': generated['content']},
            'finish_reason': generated['finish_reason']}], 'usage': generated['usage']}).encode()
        return response
    monkeypatch.setattr(requests.Session, 'post', post)
    monkeypatch.setattr(ev, 'check_live_environment', lambda config: None)
    monkeypatch.setenv('OPENAI_API_KEY', 'offline-unused')
    root = tmp_path/'campaign'
    ev.run_campaign(root, config=cfg, actor_runner=h.actor)
    assert counts == {'grouping': 1, 'diagnosis': 1, 'preconditioner': 2, 'editor': 1, 'replay': 2}
    for stage, body in wire:
        assert body['max_tokens'] == (32768 if stage in ('preconditioner', 'replay') else 16384)
    for stage in counts:
        expected = ev.stage_call_config(cfg, stage)
        for path in (root/'rounds/R01'/stage/'attempts').glob('*/run.json'):
            assert ev.read(path)['call_config'] == expected
        for path in (root/'rounds/R01'/stage/'attempts').glob('*/request.json'):
            assert ev.read(path)['body']['max_tokens'] == expected['max_tokens']
    assert cfg['call_config']['max_tokens'] == 16384
    assert ev.execution_protocol(50)['max_tokens'] == 16384
    before = len(wire), len(h.actor_calls)
    ev.run_campaign(root, resume=True, actor_runner=h.actor)
    assert before == (len(wire), len(h.actor_calls))
    changed = deepcopy(cfg); changed['module_max_tokens']['preconditioner'] = 16384
    with pytest.raises(ValueError, match='config changed'): ev.initialize(root, changed)


@pytest.mark.parametrize('value', [{'unknown': 32768}, {'preconditioner': True},
                                  {'replay': 0}, {'replay': '32768'}, None])
def test_invalid_module_budgets_fail_before_work(tmp_path, value):
    cfg = config(1); cfg['module_max_tokens'] = value
    with pytest.raises(ValueError): ev.initialize(tmp_path, cfg)
    assert not (tmp_path/'state.json').exists()
