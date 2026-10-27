"""Raw model responses must survive persistence without newline conversion."""
import json

import pytest

from src.skill_evolution.v23_5 import evolution, replay
from src.skill_evolution.v23_5.config import KNOWLEDGE_ONLY, MEMORY_V3, baseline_config
from .helpers import Fake, read
from .test_baseline import Harness, config


@pytest.fixture(scope='module')
def bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp('replay_newlines')
    h = Harness()
    evolution.run_campaign(root, config=config(1), generate=h.generate, actor_runner=h.actor)
    return read(root/'rounds/R01/replay/attempts/001/input.json')


@pytest.mark.parametrize('view', [replay.INPUT_VIEW, replay.KNOWLEDGE_INPUT_VIEW])
@pytest.mark.parametrize('newlines', ['lf', 'crlf', 'mixed'])
def test_response_round_trip_preserves_exact_bytes(bundle, tmp_path, view, newlines):
    value = {'entries': [{'revises': [], 'knowledge': [{
        'text': '条件性认识。\r\n第二行；不确定性保留。', 'evidence': ['diff', 'P1:1', 'Q1:1']}]}]}
    content = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if newlines == 'crlf':
        content = content.replace('\n', '\r\n')
    elif newlines == 'mixed':
        content = content.replace('\n', '\r\n', 2)
    fake = Fake(value, content=content)
    dest = tmp_path/'replay'
    saved = replay.run_replay(bundle, dest, generate=fake, input_view=view)
    assert saved['replay'] == value
    assert (dest/'raw_output.txt').read_bytes() == content.encode('utf-8')
    assert read(dest/'response.json')['content'] == content
    assert read(dest/'run.json')['status'] == 'valid'
    assert replay.load_replay(dest) == saved
    assert replay.run_replay(bundle, dest, generate=fake, input_view=view) == saved
    assert fake.calls == 1


@pytest.mark.parametrize('view', [MEMORY_V3, KNOWLEDGE_ONLY])
@pytest.mark.parametrize('outcome', ['ACCEPT', 'RETAIN'])
def test_campaign_crlf_replay_does_not_retry(tmp_path, view, outcome):
    class CRLFHarness(Harness):
        def generate(self, messages, dest):
            response = super().generate(messages, dest)
            if messages[0]['content'].startswith('# Replay'):
                response['content'] = json.dumps(json.loads(response['content']), indent=2).replace('\n', '\r\n')
            return response

    h = CRLFHarness(outcome)
    result = evolution.run_campaign(tmp_path, config=baseline_config(config(1), memory_view=view),
                                    generate=h.generate, actor_runner=h.actor)
    assert result['state']['next_round'] == 2 and h.calls.count('replay') == 1
    attempts = tmp_path/'rounds/R01/replay/attempts'
    assert [p.name for p in attempts.iterdir()] == ['001']
    response = read(attempts/'001/response.json')['content']
    assert '\r\n' in response
    assert (attempts/'001/raw_output.txt').read_bytes() == response.encode()
    assert replay.load_replay(attempts/'001')['replay'] == read(attempts/'001/replay.json')
    calls = len(h.calls), len(h.actor_calls)
    evolution.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    assert (len(h.calls), len(h.actor_calls)) == calls
