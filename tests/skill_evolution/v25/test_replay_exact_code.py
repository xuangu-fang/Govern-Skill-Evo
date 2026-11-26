"""Lossless exact-only code sharing; adapted or differing programs stay explicit."""
from copy import deepcopy
import json

import pytest
import requests

from src.skill_evolution.v25 import replay, replay_view, output_feedback as feedback
from src.skill_evolution.v25.replay_shared_initial import restore_initial, exact
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench import timeline, protocol
from src.skill_evolution.v25.benchmarks.spreadsheetbench.replay_code_view import MARKER, share_code, restore_code
from .test_replay_input_views import saved
from .test_pipeline import campaign
from .support import MethodResponses


def example(response='```python\nx = 1\n```'):
    _, code = protocol.extract_code(response)
    return {'runs':[{'attempts':[{'executed':True, 'response':response, 'executed_code':code}]}]}


@pytest.mark.parametrize('body', ['x = 1\n', '# 中文\nx = "a  b"\n', '# preserve\r\nx = 1\r\n'])
def test_exact_body_round_trip_preserves_response_bytes(body):
    source = example(' \n```python\n'+body+'```\n\t')
    before = exact(source)
    shared = share_code(source)
    assert shared['runs'][0]['attempts'][0]['executed_code'] == MARKER
    assert shared['runs'][0]['attempts'][0]['response'] == source['runs'][0]['attempts'][0]['response']
    assert exact(source) == before and exact(restore_code(shared)) == before


@pytest.mark.parametrize('difference', ['path','space','newline','algorithm','unexecuted','null','invalid_response'])
def test_nonidentical_or_unexecuted_code_remains_explicit(difference):
    source = example()
    a = source['runs'][0]['attempts'][0]
    if difference == 'path':
        source = example('```python\nINPUT_PATH = "input.xlsx"\nOUTPUT_PATH = "output.xlsx"\nx = 1\n```')
    elif difference == 'space':
        a['executed_code'] = 'x  = 1\n'
    elif difference == 'newline':
        a['executed_code'] = 'x = 1'
    elif difference == 'algorithm':
        a['executed_code'] = 'x = 2\n'
    elif difference == 'unexecuted':
        a['executed'] = False
    elif difference == 'null':
        a['executed_code'] = None
    else:
        a['response'] = '```python\nnot valid python !!!\n```'
    assert exact(share_code(source)) == exact(source)


@pytest.mark.parametrize('damage', ['version','extra','path','unexecuted','response'])
def test_invalid_code_markers_fail_closed(damage):
    view = share_code(example())
    a = view['runs'][0]['attempts'][0]
    if damage == 'version':
        a['executed_code']['from_response'] = 'unknown'
    elif damage == 'extra':
        a['executed_code']['ref'] = 'P2:1'
    elif damage == 'path':
        a['response'] = '```python\nINPUT_PATH = "input.xlsx"\n```'
    elif damage == 'unexecuted':
        a['executed'] = False
    else:
        a['response'] = None
    with pytest.raises(ValueError):
        restore_code(view)


def test_v4_composes_with_shared_initial_and_both_timeline_directions(saved):
    _, adapter, path, bundle = saved
    before = exact(bundle)
    with using_benchmark(adapter):
        full_v2 = replay_view.model_input(bundle, input_view=replay_view.PAIRED_FORMAT)
        full_v3 = replay_view.model_input(bundle, input_view=replay_view.SHARED_INITIAL_FORMAT)
        full_v4 = replay_view.model_input(bundle)
        assert exact(restore_code(full_v4)) == exact(full_v3)
        compact = timeline.project(full_v4)
        assert exact(restore_code(compact)) == exact(timeline.project(full_v3))
        assert restore_initial(restore_code(timeline.restore(compact))) == full_v2
        assert exact(restore_code(share_code(full_v3))) == exact(full_v3)
        old = replay.messages_for(bundle, input_view=replay_view.SHARED_INITIAL_FORMAT)
        new = replay.messages_for(bundle)
        note = (protocol.PROMPTS/'replay_exact_code_view.md').read_text().rstrip()
        assert new[0]['content'] == old[0]['content']+'\n\n'+note
        context = feedback.saved_context(path)
        old, new = (feedback.request_messages(m, context) for m in (old,new))
        assert exact(restore_code(json.loads(new[1]['content']))) == old[1]['content']
    assert exact(bundle) == before
    assert any(a['executed_code'] == MARKER for r in full_v4['runs'] for a in r['attempts'])
    assert full_v4['shared_initial'] == full_v3['shared_initial']
    assert full_v4['memory'] == full_v3['memory'] and full_v4['pairs'] == full_v3['pairs']


def test_code_marker_does_not_become_an_evidence_id(saved):
    _, adapter, _, bundle = saved
    result = {'entries':[{'revises':[], 'knowledge':[{'text':'Encoding is not evidence',
              'evidence':['diff','python_fence_body_exact_v1']}]}]}
    with using_benchmark(adapter), pytest.raises(ValueError):
        replay.validate_result(result,bundle['payload'])


def test_technical_retry_keeps_v4_base_messages(tmp_path):
    class Responses(MethodResponses):
        def __init__(self):
            super().__init__()
            self.replay_messages=[]
        def __call__(self,messages,directory):
            if 'replay' in directory.parts:
                self.replay_messages.append(deepcopy(messages))
                if len(self.replay_messages)==1:
                    raise requests.ReadTimeout('offline simulated timeout')
            return super().__call__(messages,directory)
    method=Responses()
    campaign(tmp_path,method=method)
    assert len(method.replay_messages)==2
    assert method.replay_messages[0]==method.replay_messages[1]
    assert len(method.replay_messages[0])==2
