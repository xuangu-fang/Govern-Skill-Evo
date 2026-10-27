"""Offline validation-feedback, fault injection, request roles and recovery tests."""
from copy import deepcopy
import json

import pytest
import requests

from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23_5 import evolution as ev, preconditioner as pc, editor, diagnosis, replay
from src.skill_evolution.v23_5 import output_feedback as feedback
from src.skill_evolution.v23_5.config import method_config, validate_method, MEMORY_V3
from .helpers import read
from .test_baseline import Harness, config


class Scripted(Harness):
    def __init__(self, stage, actions):
        super().__init__()
        self.stage, self.actions, self.requests = stage, list(actions), []

    def generate(self, messages, dest):
        response = super().generate(messages, dest)
        if self.stage not in dest.parts:
            return response
        self.requests.append(deepcopy(messages))
        action = self.actions.pop(0) if self.actions else 'valid'
        value = json.loads(response['content'])
        if action in ('json', 'length'):
            response['content'] = 'PRIVATE_BODY not JSON'
            response['finish_reason'] = 'length' if action == 'length' else 'stop'
        elif action == 'schema': response['content'] = '{}'
        elif action == 'missing_to':
            for adjustment in value['adjustments']:
                del adjustment['to']
            response['content'] = json.dumps(value)
        elif action == 'reference':
            value['adjustments'][0]['reason'] = 'Use P1:1.'
            response['content'] = json.dumps(value)
        elif action == 'patch':
            patch = '--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-absent source\n+new text\n'
            if self.stage == 'editor':
                # A null Parent uses the /dev/null header.
                patch = patch.replace('--- a/SKILL.md', '--- /dev/null')
                value['patch'] = patch
            else:
                value['adjustments'][0].update(focus=['S'], change='Clarify the condition.', to={'patch': patch})
            response['content'] = json.dumps(value)
        elif action == 'timeout': raise requests.Timeout('offline')
        elif action == 'interrupt': raise KeyboardInterrupt('offline during request')
        elif action == '429':
            ev.save(dest/'http_status.json', {'status_code': 429})
            (dest/'http_response.txt').write_text('rate limited')
            raise ValueError('HTTP 429')
        response['reasoning_content'] = 'DO_NOT_FORWARD_INDEPENDENT_REASONING'
        return response


def run(root, harness, **kwargs):
    return ev.run_campaign(root, generate=harness.generate, actor_runner=harness.actor, **kwargs)


@pytest.mark.parametrize('stage', ['diagnosis', 'preconditioner', 'editor', 'replay'])
@pytest.mark.parametrize('error', ['json', 'schema'])
def test_output_feedback_and_complete_reload(tmp_path, stage, error):
    h = Scripted(stage, [error, 'valid'])
    result = run(tmp_path, h, config=config(1))
    assert result['state']['next_round'] == 2 and len(h.requests) == 2
    first, second = h.requests
    assert second[:2] == first
    assert [m['role'] for m in second] == ['system', 'user', 'assistant', 'user']
    attempts = tmp_path/f'rounds/R01/{stage}/attempts'
    assert second[2]['content'] == read(attempts/'001/response.json')['content']
    assert second[3]['content'].startswith('# Previous Output Validation Error')
    assert 'DO_NOT_FORWARD_INDEPENDENT_REASONING' not in json.dumps(second)
    err = read(attempts/'001/error.json')
    assert err['kind'] == 'output_validation' and len(err['diagnostic']['error']) <= 600
    if error == 'json':
        assert 'line 1, column 1' in err['diagnostic']['error']
        assert 'PRIVATE_BODY' not in json.dumps(err)
    module = {'diagnosis': diagnosis, 'preconditioner': pc, 'editor': editor, 'replay': replay}[stage]
    getattr(module, f'load_{stage}')(attempts/'002')
    before = len(h.calls), len(h.actor_calls)
    run(tmp_path, h, resume=True)
    assert before == (len(h.calls), len(h.actor_calls))


@pytest.mark.parametrize('technical', ['timeout', '429', 'length'])
def test_feedback_then_technical_retry_preserves_entire_request(tmp_path, technical):
    h = Scripted('preconditioner', ['reference', technical, 'valid'])
    cfg = config(1); cfg['call_config']['max_tokens'] = 32768
    run(tmp_path, h, config=cfg)
    assert len(h.requests) == 3 and h.requests[1] == h.requests[2]
    assert 'Update u1.reason' in h.requests[1][-1]['content']
    attempts = tmp_path/'rounds/R01/preconditioner/attempts'
    err = read(attempts/'002/error.json')
    assert err['kind'] == ('truncated' if technical == 'length' else 'technical')
    assert 'diagnostic' not in err
    assert all(read(attempts/f'{n:03}/run.json')['call_config']['max_tokens'] == 32768 for n in (1, 2, 3))


@pytest.mark.parametrize('stage', ['preconditioner', 'editor'])
def test_patch_error_reports_hunk_and_replaces_last_feedback(tmp_path, stage):
    h = Scripted(stage, ['json', 'patch', 'valid'])
    run(tmp_path, h, config=config(1))
    assert len(h.requests[2]) == 4
    assert 'Hunk 1' in h.requests[2][-1]['content']
    assert 'PRIVATE_BODY' not in h.requests[2][-1]['content']
    attempts = tmp_path/f'rounds/R01/{stage}/attempts'
    assert h.requests[2][2]['content'] == read(attempts/'002/response.json')['content']


def test_length_checked_before_parser_and_never_resets_budget(tmp_path, monkeypatch):
    parse = pc.parse_json_response
    def guarded(content):
        assert content != 'PRIVATE_BODY not JSON', 'Truncated body reached parser'
        return parse(content)
    monkeypatch.setattr(pc, 'parse_json_response', guarded)
    h = Scripted('preconditioner', ['length'] * 3)
    with pytest.raises(ev.Stopped, match='budget exhausted'): run(tmp_path, h, config=config(1))
    assert h.requests[0] == h.requests[1] == h.requests[2]
    with pytest.raises(ev.Stopped, match='budget exhausted'): run(tmp_path, h, resume=True)
    assert len(h.requests) == 3


@pytest.mark.parametrize('saved_response', [False, True])
def test_feedback_request_survives_interrupt_and_resume(tmp_path, monkeypatch, saved_response):
    h = Scripted('preconditioner', ['reference', 'valid' if saved_response else 'interrupt', 'valid'])
    write = pc.write_record
    interrupted = False
    def crash(path, value):
        nonlocal interrupted
        write(path, value)
        if saved_response and '002' in path.parts and path.name == 'response.json' and not interrupted:
            interrupted = True
            raise KeyboardInterrupt('after response save')
    monkeypatch.setattr(pc, 'write_record', crash)
    with pytest.raises(KeyboardInterrupt): run(tmp_path, h, config=config(1))
    run(tmp_path, h, resume=True)
    assert len(h.requests) == (2 if saved_response else 3)
    folder = tmp_path/'rounds/R01/preconditioner'
    selected = folder/read(folder/'result.json')['path']
    assert read(selected/'messages.json') == h.requests[1]
    if saved_response:
        assert read(selected/'recovered_from.json')['additional_requests'] == 0
    else:
        assert h.requests[2] == h.requests[1]
    pc.load_preconditioner(selected)


@pytest.mark.parametrize('where', ['input', 'save', 'reload', 'scanner', 'unknown_validator'])
def test_program_errors_never_become_content_feedback(tmp_path, monkeypatch, where):
    fired = False
    if where == 'input':
        def failure(*args, **kwargs):
            require(False, 'same ValueError from input assembly')
        monkeypatch.setattr(pc, 'preconditioner_input', failure)
    elif where in ('scanner', 'unknown_validator'):
        original = pc.normalize_update_patches
        def failure(*args, **kwargs):
            nonlocal fired
            if not fired:
                fired = True
                if where == 'scanner': raise feedback.TechnicalValidationError('identified scanner defect')
                raise ValueError('unknown internal validator defect')
            return original(*args, **kwargs)
        monkeypatch.setattr(pc, 'normalize_update_patches', failure)
    elif where == 'save':
        original = pc.write_record
        def failure(path, value):
            nonlocal fired
            if path.name == 'parsed.json' and not fired:
                fired = True
                require(False, 'same ValueError from persistence')
            return original(path, value)
        monkeypatch.setattr(pc, 'write_record', failure)
    else:
        original = pc.load_preconditioner
        def failure(*args, **kwargs):
            nonlocal fired
            if not fired:
                fired = True
                require(False, 'same ValueError from reload')
            return original(*args, **kwargs)
        monkeypatch.setattr(pc, 'load_preconditioner', failure)
    h = Scripted('preconditioner', [])
    if where == 'input':
        with pytest.raises(ev.Stopped): run(tmp_path, h, config=config(1))
        assert h.requests == []
    else:
        with pytest.raises(ev.Stopped): run(tmp_path, h, config=config(1))
        assert all(m == h.requests[0] and len(m) == 2 for m in h.requests)
        assert len(h.requests) == 1
    err = read(tmp_path/'rounds/R01/preconditioner/attempts/001/error.json')
    assert err['kind'] == 'technical' and 'diagnostic' not in err
    assert err['retryable'] is False
    with pytest.raises(ev.Stopped): run(tmp_path, h, resume=True)


@pytest.mark.parametrize('stage', ['diagnosis', 'preconditioner', 'editor', 'replay'])
@pytest.mark.parametrize('prior_failures', [0, 2])
def test_save_failure_stops_without_model_or_local_retry(tmp_path, monkeypatch, stage, prior_failures):
    module = {'diagnosis': diagnosis, 'preconditioner': pc, 'editor': editor, 'replay': replay}[stage]
    write = module.write_record
    failed = False
    def failure(path, value):
        nonlocal failed
        if path.name == 'parsed.json' and not failed:
            failed = True
            raise OSError('offline transient save failure before output validation')
        return write(path, value)
    monkeypatch.setattr(module, 'write_record', failure)
    h = Scripted(stage, ['json'] * prior_failures + ['valid'])
    generate = h.generate
    def with_http_status(messages, dest):
        response = generate(messages, dest)
        ev.save(dest/'http_status.json', {'status_code': 200})
        return response
    h.generate = with_http_status
    with pytest.raises(ev.Stopped, match='OSError'):
        run(tmp_path, h, config=config(1))
    assert len(h.requests) == prior_failures + 1
    folder = tmp_path/f'rounds/R01/{stage}'
    original = folder/f'attempts/{prior_failures + 1:03}'
    assert not read(original/'run.json').get('output_validated', False)
    assert not (original/'recovered').exists()
    assert not (folder/'result.json').exists()
    assert not read(original/'error.json')['retryable']
    with pytest.raises(ev.Stopped): run(tmp_path, h, resume=True)
    assert len(h.requests) == prior_failures + 1


def test_local_failure_remains_stopped_on_resume(tmp_path, monkeypatch):
    write = pc.write_record
    unavailable = True
    def failure(path, value):
        if unavailable and path.name == 'parsed.json' and '003' in path.parts:
            raise OSError('offline storage temporarily unavailable')
        return write(path, value)
    monkeypatch.setattr(pc, 'write_record', failure)
    h = Scripted('preconditioner', ['reference', 'reference', 'valid'])
    with pytest.raises(ev.Stopped):
        run(tmp_path, h, config=config(1))
    with pytest.raises(ev.Stopped):
        run(tmp_path, h, resume=True)
    assert len(h.requests) == 3
    unavailable = False
    with pytest.raises(ev.Stopped): run(tmp_path, h, resume=True)
    assert len(h.requests) == 3
    assert len(list((tmp_path/'rounds/R01/preconditioner/attempts').iterdir())) == 3


@pytest.mark.parametrize('stage', ['diagnosis', 'preconditioner', 'editor', 'replay'])
def test_third_response_recovers_after_two_interruptions(tmp_path, monkeypatch, stage):
    module = {'diagnosis': diagnosis, 'preconditioner': pc, 'editor': editor, 'replay': replay}[stage]
    write = module.write_record
    crashes = 0
    def crash(path, value):
        nonlocal crashes
        write(path, value)
        if '003' in path.parts and (
                (crashes == 0 and path.name == 'response.json') or
                (crashes == 1 and 'recovered' in path.parts and path.name == 'parsed.json')):
            crashes += 1
            raise KeyboardInterrupt('offline interruption during saved-response processing')
    monkeypatch.setattr(module, 'write_record', crash)
    h = Scripted(stage, ['json', 'json', 'valid'])
    with pytest.raises(KeyboardInterrupt): run(tmp_path, h, config=config(1))
    with pytest.raises(KeyboardInterrupt): run(tmp_path, h, resume=True)
    run(tmp_path, h, resume=True)
    assert len(h.requests) == 3 and crashes == 2
    folder = tmp_path/f'rounds/R01/{stage}'
    selected = folder/read(folder/'result.json')['path']
    assert selected.name == 'recovered_002'
    assert read(selected.parent/'recovered/run.json')['status'] == 'invalid'
    assert read(selected/'messages.json') == h.requests[-1]
    getattr(module, f'load_{stage}')(selected)
    before = len(h.calls), len(h.actor_calls)
    run(tmp_path, h, resume=True)
    assert before == (len(h.calls), len(h.actor_calls))


def test_cached_response_still_runs_output_validation(tmp_path, monkeypatch):
    write = pc.write_record
    failed = False
    def failure(path, value):
        nonlocal failed
        if path.name == 'parsed.json' and not failed:
            failed = True
            raise KeyboardInterrupt('offline interruption before schema validation')
        return write(path, value)
    monkeypatch.setattr(pc, 'write_record', failure)
    h = Scripted('preconditioner', ['schema', 'valid'])
    with pytest.raises(KeyboardInterrupt): run(tmp_path, h, config=config(1))
    run(tmp_path, h, resume=True)
    assert len(h.requests) == 2
    assert h.requests[1][2]['content'] == '{}'
    assert h.requests[1][3]['content'].startswith('# Previous Output Validation Error')
    first = tmp_path/'rounds/R01/preconditioner/attempts/001'
    assert read(first/'error.json')['kind'] == 'output_validation'
    assert read(first/'recovered/run.json')['status'] == 'invalid'


def test_grouping_uses_validation_feedback(tmp_path):
    h = Scripted('grouping', ['schema', 'valid'])
    run(tmp_path, h, config=config(1))
    assert len(h.requests) == 2 and h.requests[0] == h.requests[1][:2]
    assert h.requests[1][2]['content'] == '{}'
    assert 'Grouping output' in h.requests[1][3]['content']


def test_resume_preserves_non_retryable_http_failure(tmp_path):
    h = Scripted('preconditioner', [])
    generate = h.generate
    def forbidden(messages, dest):
        response = generate(messages, dest)
        if 'preconditioner' in dest.parts:
            ev.save(dest/'http_status.json', {'status_code': 403})
            (dest/'http_response.txt').write_text('forbidden')
            raise ValueError('HTTP 403')
        return response
    h.generate = forbidden
    with pytest.raises(ev.Stopped, match='HTTP 403'):
        run(tmp_path, h, config=config(1))
    with pytest.raises(ev.Stopped, match='non-retryable technical failure'):
        run(tmp_path, h, resume=True)
    assert len(h.requests) == 1


def test_legacy_policy_keeps_old_prompt_and_retry_path(tmp_path):
    cfg = config(1)
    cfg['method'] = method_config(MEMORY_V3, retry_policy=feedback.LEGACY)
    assert 'retry_policy' not in cfg['method']
    validate_method(cfg['method'])
    h = Scripted('preconditioner', ['json', 'valid'])
    run(tmp_path, h, config=cfg)
    assert h.requests[0] == h.requests[1] and len(h.requests[1]) == 2
    assert feedback.INSTRUCTION not in h.requests[0][0]['content']


def test_feedback_provenance_rechecked_on_reload(tmp_path):
    h = Scripted('preconditioner', ['reference', 'valid'])
    run(tmp_path, h, config=config(1))
    folder = tmp_path/'rounds/R01/preconditioner/attempts'
    error = read(folder/'001/error.json'); error['diagnostic']['error'] = 'tampered diagnostic'
    ev.save(folder/'001/error.json', error)
    with pytest.raises(ValueError, match='prompt/input differs'): pc.load_preconditioner(folder/'002')


def test_unknown_require_and_wrapped_scanner_defect_are_not_feedback(monkeypatch, payload):
    from src.skill_evolution.v23_5 import update_patch
    from .helpers import keep, revise
    def unknown():
        require(False, 'an internal check, not a declared output check')
    with pytest.raises(ValueError) as caught:
        feedback.output_call('output', unknown)
    assert not isinstance(caught.value, feedback.OutputValidationError)
    with pytest.raises(ValueError) as caught:
        feedback.output_call('output', update_patch.normalize_update_patches, keep(payload), {})
    assert not isinstance(caught.value, feedback.OutputValidationError)
    def broken_patch(*args):
        raise feedback.TechnicalValidationError('identified patch scanner defect')
    monkeypatch.setattr(update_patch, 'apply_patch', broken_patch)
    raw = keep(payload); raw['adjustments'][0] = revise(payload)
    with pytest.raises(ValueError) as caught:
        feedback.output_call('output', update_patch.normalize_update_patches, raw, payload)
    assert not isinstance(caught.value, feedback.OutputValidationError)


def test_all_checks_rerun_after_fix_and_feedback_stays_recent(tmp_path):
    h = Scripted('preconditioner', ['reference', 'patch', 'valid'])
    run(tmp_path, h, config=config(1))
    assert 'single-backtick' in h.requests[1][-1]['content']
    assert 'Hunk 1' in h.requests[2][-1]['content']
    assert 'single-backtick' not in h.requests[2][-1]['content']


def test_new_prompt_variants_keep_contract_and_legacy_files():
    paths = [diagnosis.PROMPT_PATH, editor.PROMPT_PATH, pc.PROMPT_PATH, pc.KNOWLEDGE_PROMPT_PATH,
             replay.LEARNING_PROMPT_PATH, replay.KNOWLEDGE_PROMPT_PATH]
    for path in paths:
        old = feedback.prompt_text(path, feedback.LEGACY)
        new = feedback.prompt_text(path, feedback.POLICY)
        assert old == path.read_text() and feedback.INSTRUCTION not in old
        assert new.count(feedback.INSTRUCTION) == 1
    for path in (pc.PROMPT_PATH, pc.KNOWLEDGE_PROMPT_PATH):
        new = feedback.prompt_text(path, feedback.POLICY)
        assert 'enclose each formal reference ID in single backticks' in new
        assert 'first character of each body line' in new
        assert 'Keep' in new and 'withdrawal' in new


def test_schema_feedback_lists_all_missing_to_fields(payload):
    from .helpers import keep
    raw = keep(payload)
    for a in raw['adjustments']:
        del a['to']
    before = deepcopy(raw)
    with pytest.raises(feedback.OutputValidationError) as caught:
        feedback.output_call('Preconditioner output', pc.normalize_update_patches, raw, payload)
    diagnostic = caught.value.diagnostic
    assert diagnostic['location'] == 'adjustments'
    for i in range(3):
        assert f'adjustments[{i}] (Update u{i+1}): missing field(s) "to".' in diagnostic['error']
    assert raw == before and len(diagnostic['error']) <= 600


@pytest.mark.parametrize('path,value,expected', [
    (['adjustments'], {}, 'adjustments: expected array; got object'),
    (['adjustments', 0], None, 'adjustments[0]: expected object; got null'),
    (['adjustments', 0, 'target'], 7, 'adjustments[0].target: expected string; got number'),
    (['adjustments', 0, 'focus'], 'S', '.focus: expected array; got string'),
    (['adjustments', 0, 'focus'], [False], '.focus[0]: expected string; got boolean'),
    (['adjustments', 0, 'reason'], [], '.reason: expected string; got array'),
    (['adjustments', 0, 'to'], {'patch': 9}, '.to.patch: expected string; got number'),
    (['adjustments', 0, 'to'], 'text', '.to: expected null, empty array, or object'),
    (['adjustments', 0, 'to'], [1], 'got array (nonempty)'),
    (['adjustments', 0, 'to'], {}, '.to: missing field(s) "patch"'),
    (['checks'], 1, 'checks: expected array or null; got number'),
    (['checks', 0], 'text', 'checks[0]: expected object; got string'),
    (['checks', 0, 'update_ids'], 'u1', 'checks[0].update_ids: expected array; got string'),
    (['checks', 0, 'update_ids'], [3], 'checks[0].update_ids[0]: expected string; got number'),
    (['checks', 0, 'question'], None, 'checks[0].question: expected string; got null'),
])
def test_output_schema_locations_and_acceptance_unchanged(payload, monkeypatch, path, value, expected):
    from .helpers import keep
    from src.skill_evolution.v23_5 import update_patch
    raw = keep(payload); raw['checks'] = deepcopy(payload['plan']['checks'])
    target = raw
    for key in path[:-1]: target = target[key]
    target[path[-1]] = value
    with monkeypatch.context() as m:
        m.setattr(update_patch, '_validate_output_schema', lambda result: None)
        with pytest.raises((ValueError, TypeError, KeyError)):
            update_patch.normalize_update_patches(raw, payload)
    with pytest.raises(feedback.OutputValidationError) as caught:
        feedback.output_call('Preconditioner output', update_patch.normalize_update_patches, raw, payload)
    assert expected in caught.value.diagnostic['error']
    assert caught.value.diagnostic['location'] != 'Preconditioner output'


def test_schema_missing_target_extra_fields_and_bounded_summary(payload):
    from .helpers import keep
    raw = keep(payload)
    del raw['adjustments'][0]['target']
    raw['adjustments'][0]['unexpected'] = 'PRIVATE_BODY' * 1000
    raw['adjustments'][1]['to'] = {'patch': 'irrelevant', 'extra': True}
    with pytest.raises(feedback.OutputValidationError) as caught:
        feedback.output_call('output', pc.normalize_update_patches, raw, payload)
    detail = caught.value.diagnostic['error']
    assert 'adjustments[0]: missing field(s) "target"' in detail
    assert 'adjustments[0]: extra field(s) "unexpected"' in detail
    assert '(Update u2).to: extra field(s) "extra"' in detail
    assert 'PRIVATE_BODY' not in detail
    raw['adjustments'] = [{} for _ in range(100)]
    with pytest.raises(feedback.OutputValidationError) as caught:
        feedback.output_call('output', pc.normalize_update_patches, raw, payload)
    assert len(caught.value.diagnostic['error']) <= 600
    assert 'additional schema error(s) not shown' in caught.value.diagnostic['error']


@pytest.mark.parametrize('mode', ['keep', 'checks', 'withdraw', 'patch'])
def test_valid_schema_results_equal_existing_validator(payload, monkeypatch, mode):
    from .helpers import keep, revise, withdraw
    from src.skill_evolution.v23_5 import update_patch
    raw = keep(payload)
    if mode == 'checks': raw['checks'] = deepcopy(payload['plan']['checks'])
    if mode == 'withdraw':
        raw = {'adjustments': [withdraw(a['target']) for a in raw['adjustments']], 'checks': []}
    if mode == 'patch': raw['adjustments'][0] = revise(payload)
    actual = update_patch.normalize_update_patches(raw, payload)
    with monkeypatch.context() as m:
        m.setattr(update_patch, '_validate_output_schema', lambda result: None)
        assert actual == update_patch.normalize_update_patches(raw, payload)


def three_update_harness(actions):
    h = Scripted('preconditioner', actions)
    generate = h.generate
    def three_updates(messages, dest):
        response = generate(messages, dest)
        if 'diagnosis' in dest.parts:
            value = json.loads(response['content'])
            original = value['plan']['updates'][0]
            value['plan']['updates'] = [{**original, 'id': f'u{i}'} for i in range(1, 4)]
            response['content'] = json.dumps(value)
        return response
    h.generate = three_updates
    return h


def test_schema_fix_still_checks_references_and_replaces_feedback(tmp_path):
    h = three_update_harness(['missing_to', 'reference', 'valid'])
    run(tmp_path, h, config=config(1))
    assert len(h.requests) == 3
    for i in range(3):
        assert f'adjustments[{i}] (Update u{i+1})' in h.requests[1][-1]['content']
    assert 'single-backtick' in h.requests[2][-1]['content']
    assert 'missing field' not in h.requests[2][-1]['content']
    pc.load_preconditioner(tmp_path/'rounds/R01/preconditioner/attempts/003')


@pytest.mark.parametrize('saved_response', [False, True])
def test_schema_diagnostic_survives_save_reload_and_recovery(tmp_path, monkeypatch, saved_response):
    h = three_update_harness(['missing_to', 'valid' if saved_response else 'interrupt', 'valid'])
    write = pc.write_record
    fired = False
    def crash(path, value):
        nonlocal fired
        write(path, value)
        if saved_response and '002' in path.parts and path.name == 'response.json' and not fired:
            fired = True
            raise KeyboardInterrupt('offline after response save')
    monkeypatch.setattr(pc, 'write_record', crash)
    with pytest.raises(KeyboardInterrupt): run(tmp_path, h, config=config(1))
    folder = tmp_path/'rounds/R01/preconditioner'
    diagnostic = read(folder/'attempts/001/error.json')['diagnostic']
    assert diagnostic['location'] == 'adjustments'
    assert diagnostic['error'] in h.requests[1][-1]['content']
    run(tmp_path, h, resume=True)
    selected = folder/read(folder/'result.json')['path']
    assert read(selected/'messages.json') == h.requests[1]
    assert len(h.requests) == (2 if saved_response else 3)
    pc.load_preconditioner(selected)
    run(tmp_path, h, resume=True)
    assert len(h.requests) == (2 if saved_response else 3)


def test_schema_error_class_alone_does_not_enable_feedback(payload, monkeypatch):
    from src.skill_evolution.v23_5 import update_patch
    from .helpers import keep
    def unrelated(*args, **kwargs):
        raise update_patch.OutputSchemaError('unrelated', 'Not from the output schema helper')
    with pytest.raises(update_patch.OutputSchemaError):
        feedback.output_call('input', unrelated)
    monkeypatch.setattr(update_patch, 'validate_memory', unrelated)
    with pytest.raises(update_patch.OutputSchemaError):
        feedback.output_call('output', update_patch.normalize_update_patches, keep(payload), payload)
