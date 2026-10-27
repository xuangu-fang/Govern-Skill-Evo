"""All seven stages share feedback, technical retry and persistent request budgets."""
from copy import deepcopy
import json

import pytest
import requests

from src.skill_evolution.v23_5 import evolution as ev, knowledge_review as review
from src.skill_evolution.v23_5 import output_feedback as feedback, knowledge_repair as repair
from .test_knowledge_review import ReviewedHarness, cfg

STAGES = ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay', 'verifier', 'repair']


class Scripted(ReviewedHarness):
    def __init__(self, stage, actions):
        super().__init__()
        self.stage, self.actions, self.requests = stage, list(actions), []

    def generate(self, messages, dest):
        response = super().generate(messages, dest)
        if self.stage not in dest.parts:
            return response
        self.requests.append(deepcopy(messages))
        action = self.actions.pop(0) if self.actions else 'valid'
        if action == 'json': response['content'] = 'not JSON'
        elif action == 'schema': response['content'] = '{}'
        elif action == 'length': response.update(content='truncated', finish_reason='length')
        elif action == 'timeout': raise requests.Timeout('offline')
        elif action == 'chunked': raise requests.exceptions.ChunkedEncodingError('offline')
        elif action == 'interrupt': raise KeyboardInterrupt('offline')
        elif action == 'internal': raise ValueError('unknown generator bug')
        response['reasoning_content'] = 'NOT_FEEDBACK_EVIDENCE'
        return response


def config():
    value = cfg()
    value['max_attempts'] = 6
    value['retry_delay_seconds'] = 0
    return value


def run(root, h, *, resume=False):
    return ev.run_campaign(root, config=None if resume else config(), resume=resume,
                           generate=h.generate, actor_runner=h.actor)


@pytest.mark.parametrize('stage', STAGES)
def test_mixed_failures_share_six_attempt_budget_and_frozen_requests(tmp_path, stage):
    h = Scripted(stage, ['json', 'timeout', 'length', 'schema', 'chunked', 'valid'])
    assert run(tmp_path, h)['status'] == 'complete'
    assert len(h.requests) == 6
    first, feedback1, timeout_retry, length_retry, feedback2, chunked_retry = h.requests
    assert len(first) == 2
    assert feedback1 == timeout_retry == length_retry
    assert feedback2 == chunked_retry
    assert feedback1[:2] == feedback2[:2] == first
    assert feedback1[2]['content'] == 'not JSON'
    assert feedback2[2]['content'] == '{}'
    assert 'Previous Output Validation Error' in feedback2[3]['content']
    assert 'NOT_FEEDBACK_EVIDENCE' not in json.dumps(h.requests)
    attempts = tmp_path/'rounds/R01'/stage/'attempts'
    assert len(list(attempts.iterdir())) == 6
    for path in attempts.iterdir():
        assert ev.read(path/'run.json')['call_config'] == ev.stage_call_config(config(), stage)
    before = deepcopy(h.calls), deepcopy(h.actor_calls)
    run(tmp_path, h, resume=True)
    assert before == (h.calls, h.actor_calls)
    # Legal CONFLICT routes to Repair, without a second semantic Verifier call.
    assert h.calls.count('verifier') == (6 if stage == 'verifier' else 1)
    assert h.calls.count('repair') == (6 if stage == 'repair' else 1)


@pytest.mark.parametrize('stage', STAGES)
def test_interruption_consumes_slot_and_exhaustion_survives_resume(tmp_path, stage):
    h = Scripted(stage, ['schema', 'timeout', 'interrupt', 'json', 'length', 'schema', 'valid'])
    with pytest.raises(KeyboardInterrupt): run(tmp_path, h)
    assert len(h.requests) == 3
    with pytest.raises(ev.Stopped, match='exhausted'): run(tmp_path, h, resume=True)
    assert len(h.requests) == 6
    with pytest.raises(ValueError, match='fixed shared request budget'):
        ev.editor_retry.enable(tmp_path, round_number=1, reason='offline test')
    assert h.requests[1] == h.requests[2] == h.requests[3]
    with pytest.raises(ev.Stopped, match='exhausted'): run(tmp_path, h, resume=True)
    assert len(h.requests) == 6 and h.actions == ['valid']
    assert not (tmp_path/'rounds/R01/memory').exists()


@pytest.mark.parametrize('stage', STAGES)
def test_unknown_generator_exception_stops_without_retry(tmp_path, stage):
    h = Scripted(stage, ['internal', 'valid'])
    with pytest.raises(ev.Stopped, match='unknown generator bug'): run(tmp_path, h)
    with pytest.raises(ev.Stopped): run(tmp_path, h, resume=True)
    assert len(h.requests) == 1


def test_review_campaign_does_not_inherit_old_editor_budget_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(ev.editor_retry, 'request_limit', lambda *args: 12)
    h = Scripted('editor', ['schema'] * 6 + ['valid'])
    with pytest.raises(ev.Stopped, match='exhausted'): run(tmp_path, h)
    with pytest.raises(ev.Stopped, match='exhausted'): run(tmp_path, h, resume=True)
    assert len(h.requests) == 6


@pytest.mark.parametrize('stage', ['grouping', 'verifier', 'repair'])
def test_saved_response_resume_and_feedback_provenance(tmp_path, monkeypatch, stage):
    module = ev.grouping if stage == 'grouping' else review
    write = module.write_record
    fired = False

    def interrupt(path, value):
        nonlocal fired
        write(path, value)
        if stage in path.parts and '002' in path.parts and path.name == 'response.json' and not fired:
            fired = True
            raise KeyboardInterrupt('saved complete response')

    monkeypatch.setattr(module, 'write_record', interrupt)
    h = Scripted(stage, ['schema', 'valid'])
    with pytest.raises(KeyboardInterrupt): run(tmp_path, h)
    run(tmp_path, h, resume=True)
    assert len(h.requests) == 2
    folder = tmp_path/'rounds/R01'/stage
    selected = folder/ev.read(folder/'result.json')['path']
    assert ev.read(selected/'recovered_from.json')['additional_requests'] == 0
    assert ev.read(selected/'messages.json') == h.requests[1]
    error = ev.read(folder/'attempts/001/error.json')
    error['diagnostic']['error'] = 'tampered feedback'
    ev.save(folder/'attempts/001/error.json', error)
    with pytest.raises((ValueError, ev.Stopped)): ev.final_parent(tmp_path)
    assert len(h.requests) == 2


@pytest.mark.parametrize('stage', ['verifier', 'repair'])
def test_review_validator_internal_error_is_not_feedback(tmp_path, monkeypatch, stage):
    def broken(*args, **kwargs):
        raise ValueError('internal review validator defect')
    monkeypatch.setattr(review.verifier if stage == 'verifier' else repair, 'validate_result', broken)
    h = Scripted(stage, ['valid'])
    with pytest.raises(ev.Stopped, match='internal review validator defect'): run(tmp_path, h)
    assert len(h.requests) == 1
    error = ev.read(tmp_path/'rounds/R01'/stage/'attempts/001/error.json')
    assert not error['retryable'] and 'diagnostic' not in error


def test_invalid_repair_input_is_not_output_feedback():
    with pytest.raises(ValueError) as caught:
        feedback.output_call('repair output', repair.merge, {}, {}, {}, {})
    assert not isinstance(caught.value, feedback.OutputValidationError)


def test_invalid_verifier_input_is_not_output_feedback():
    target = {'target': {'entry_index': 0, 'knowledge_index': 0},
              'knowledge': {'text': 'original', 'evidence': ['Q1:1']}}
    value = {'targets': [target, deepcopy(target)], 'source_records': {'Q1:1': {}}}
    with pytest.raises(ValueError) as caught:
        feedback.output_call('verifier output', review.verifier.validate_result, {'results': []}, value)
    assert not isinstance(caught.value, feedback.OutputValidationError)


@pytest.mark.parametrize('fault', ['json', 'envelope', 'content', 'quota', 'forbidden', 'disk'])
def test_api_failures_are_distinct_from_local_faults(tmp_path, fault):
    h = Scripted('grouping', ['valid', 'valid'])
    generate = h.generate

    def bad_once(messages, dest):
        response = generate(messages, dest)
        if 'grouping' not in dest.parts or len(h.requests) != 1:
            return response
        ev.save(dest/'http_status.json', {'status_code': 403 if fault == 'forbidden' else
                                        429 if fault in ('quota', 'disk') else 200})
        (dest/'http_response.txt').write_text('insufficient_quota' if fault == 'quota' else 'broken')
        if fault == 'json':
            raw = requests.Response(); raw._content = b'not JSON'
            return raw.json()
        if fault == 'envelope': return ev.grouping.response_value({})
        if fault == 'content': return {**response, 'content': []}
        if fault == 'disk': raise OSError('disk failed after recording HTTP status')
        raise ValueError('HTTP failure')

    h.generate = bad_once
    if fault in ('json', 'envelope', 'content'):
        run(tmp_path, h)
        assert len(h.requests) == 2 and h.requests[0] == h.requests[1]
    else:
        with pytest.raises(ev.Stopped): run(tmp_path, h)
        with pytest.raises(ev.Stopped): run(tmp_path, h, resume=True)
        assert len(h.requests) == 1


@pytest.mark.parametrize('mutation', ['evidence', 'delete_last_evidence'])
def test_repair_permissions_and_merge_errors_get_feedback(tmp_path, mutation):
    h = Scripted('repair', ['valid', 'valid'])
    generate = h.generate

    def bad_once(messages, dest):
        response = generate(messages, dest)
        if 'repair' in dest.parts and len(h.requests) == 1:
            result = json.loads(response['content'])
            if mutation == 'evidence':
                result['changes'][0]['knowledge']['evidence'] = ['Q999:999']
            else:
                result['changes'][0]['knowledge'] = None
            response['content'] = json.dumps(result)
        return response

    h.generate = bad_once
    run(tmp_path, h)
    assert len(h.requests) == 2
    assert 'repair output' in h.requests[1][-1]['content']
    assert h.calls.count('verifier') == 1
