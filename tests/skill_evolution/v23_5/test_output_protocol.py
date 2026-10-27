"""Offline regressions for diagnostics; malformed output is never repaired."""
from copy import deepcopy
import json

import pytest

from src.skill_evolution.v22.diagnosis_editor import parse_json_response as original_parse
from src.skill_evolution.v23 import grouping
from src.skill_evolution.v23.editor import _read_text
from src.skill_evolution.v23_5 import comparison, preconditioner as pc
from src.skill_evolution.v23_5.memory_view import KNOWLEDGE_ONLY, MEMORY_V3
from src.skill_evolution.v23_5.update_patch import normalize_update_patches as normalize
from .helpers import Fake, keep, memory, read, revise


@pytest.mark.parametrize('view', [MEMORY_V3, KNOWLEDGE_ONLY])
@pytest.mark.parametrize('fragment,diagnostic', [
    ('P1:1', 'requires single-backtick citation format'),
    ('R1/P1:1', 'requires single-backtick citation format'),
    ('`heat apple 1 with microwave 1`', 'backtick content'),
    ('`ordinary words`', 'not in the allowed reference set'),
    ('`M99`', 'not in the allowed reference set'),
    ('`R1/P1:999`', 'not in the allowed reference set'),
    ('`P1:1 P2:1`', 'not in the allowed reference set'),
    ('`P1:1', 'malformed single-backtick citation'),
    ('``P1:1``', 'malformed single-backtick citation'),
])
def test_reference_error_locates_update_field_and_fragment(payload, view, fragment, diagnostic):
    payload['memory'] = memory(payload)
    raw = keep(payload)
    raw['adjustments'][1]['reason'] = 'Decision based on ' + fragment
    before = deepcopy((raw, payload))
    with pytest.raises(ValueError) as error:
        normalize(raw, payload, memory_view=view)
    message = str(error.value)
    assert 'Update u2.reason' in message and diagnostic in message
    assert fragment.strip('`') in message
    assert 'ordinary text' not in message
    assert (raw, payload) == before


def test_reference_diagnostic_is_bounded(payload):
    raw = keep(payload)
    raw['adjustments'][0]['reason'] = 'Based on `' + 'x' * 10000 + 'DO_NOT_LOG_TAIL`.'
    with pytest.raises(ValueError) as error:
        normalize(raw, payload)
    assert len(str(error.value)) < 300
    assert 'DO_NOT_LOG_TAIL' not in str(error.value)


def test_view_permissions_and_non_reason_locations_are_unchanged(payload):
    payload['memory'] = memory(payload)
    raw = keep(payload)
    # A full-view run reference is not automatically granted by Knowledge evidence.
    raw['adjustments'][0]['reason'] = 'Historical run `R1/P1` motivates exploration.'
    assert normalize(raw, payload, memory_view=MEMORY_V3)[1] == payload['plan']
    with pytest.raises(ValueError, match='Update u1.reason.*not in the allowed reference set'):
        normalize(raw, payload, memory_view=KNOWLEDGE_ONLY)
    raw['adjustments'][0]['reason'] = 'Reported by `M1`, with provenance `R1/P1:1`.'
    assert normalize(raw, payload, memory_view=KNOWLEDGE_ONLY)[1] == payload['plan']
    raw['adjustments'][0]['change'] = 'Explore based on R1/P1:999.'
    with pytest.raises(ValueError, match='Update u1.change.*R1/P1:999'):
        normalize(raw, payload, memory_view=KNOWLEDGE_ONLY)


@pytest.mark.parametrize('body,diagnostic', [
    ('@@\n-missing\n+New\n', 'Hunk 1:.*found 0'),
    ('@@\n-same\n+New\n', 'Hunk 1:.*found 2'),
    ('@@\n-A\n+X\n@@\n-missing\n+Y\n', 'Hunk 2:.*found 0'),
    ('@@\n-A\n+X\n@@\nB\n+Y\n', 'Hunk 2:.*invalid body line'),
    ('@@\n-A\n+X\n@@ -4 +4 @@\n-B\n+Y\n', 'Hunk 2:.*bare @@ header'),
    ('@@\n-B\n+Y\n@@\n-A\n+X\n', 'Hunk 2:.*source order'),
    ('@@\n-A\n+X\n same\n@@\n same\n-same\n+Y\n', 'Hunk 2:.*overlaps'),
    ('@@\n-A\n+X\n\\ No newline at end of file\n', 'Hunk 1:.*before result EOF'),
])
def test_patch_error_locates_update_and_hunk_without_partial_application(payload, body, diagnostic):
    payload['plan']['updates'][2]['text'] = 'A\nsame\nsame\nB\n'
    raw = keep(payload)
    raw['adjustments'][0] = revise(payload)
    raw['adjustments'][2] = revise(payload, 2)
    raw['adjustments'][2]['to']['patch'] = '--- a/SKILL.md\n+++ b/SKILL.md\n' + body
    before = deepcopy((raw, payload))
    with pytest.raises(ValueError, match='Update u3.to.patch: ' + diagnostic):
        normalize(raw, payload)
    assert (raw, payload) == before


def test_patch_preserves_list_indentation_and_whitespace(payload):
    payload['plan']['updates'][0]['text'] = '  - Old  \n'
    raw = keep(payload)
    raw['adjustments'][0] = revise(payload, replacement='  - New  \n')
    assert normalize(raw, payload)[1]['updates'][0]['text'] == '  - New  \n'
    raw['adjustments'][0]['to']['patch'] = raw['adjustments'][0]['to']['patch'].replace('-  - Old  ', '-Old')
    with pytest.raises(ValueError, match='Update u1.to.patch: Hunk 1:.*found 0'):
        normalize(raw, payload)


@pytest.mark.parametrize('content', [
    '{\n  "adjustments": ]\n}', 'prefix\n{"adjustments":[],"checks":null}',
    '{}\n{}', '{} trailing', '```json\n{\n  "checks": ]\n}\n```',
])
def test_json_errors_keep_parser_position_and_short_reason(content):
    with pytest.raises(ValueError) as original:
        original_parse(content)
    cause = original.value.__cause__
    assert isinstance(cause, json.JSONDecodeError)
    with pytest.raises(ValueError) as updated:
        pc.parse_json_response(content)
    message = str(updated.value)
    assert f'line {cause.lineno}, column {cause.colno} (char {cause.pos})' in message
    assert cause.msg in message
    assert len(message) < 200


@pytest.mark.parametrize('content', [
    '{}', ' \r\n{"a":1}\r\n', '```json\n{"a":1}\n```',
    '```\n{"a":1}\n```', '[]', '{"a":1,"a":2}', '{"a":NaN}',
    '', '```json\n{}', 'ordinary text' * 1000 + '\n{}',
])
def test_json_acceptance_is_identical(content):
    try:
        expected = original_parse(content)
    except ValueError:
        with pytest.raises(ValueError):
            pc.parse_json_response(content)
    else:
        assert pc.parse_json_response(content) == expected


@pytest.mark.parametrize('view', [MEMORY_V3, KNOWLEDGE_ONLY])
def test_json_error_saved_without_body_or_extra_calls(upstream, payload, view):
    gd, dd, _, pd = upstream
    content = 'UNLOGGED_RESPONSE_BODY' * 1000 + '\n' + json.dumps(keep(payload))
    fake = Fake(keep(payload), content=content)
    with pytest.raises(ValueError, match='JSON body line 1, column 1'):
        pc.run_preconditioner(gd, dd, pd, generate=fake, memory_view=view)
    assert fake.calls == 1
    assert _read_text(pd/'raw_output.txt') == content
    error = read(pd/'validation.json')['error']
    assert 'UNLOGGED_RESPONSE_BODY' not in error and len(error) < 200
    assert not (pd/'effective_plan.json').exists()


def test_comparison_preconditioner_uses_same_json_diagnostics(tmp_path):
    response = {'content': 'prefix\n{}', 'finish_reason': 'stop'}
    with pytest.raises(ValueError, match='JSON body line 1, column 1'):
        comparison.finish_response(tmp_path, {'stage': 'preconditioner'}, tmp_path, response)
    assert read(tmp_path/'response.json') == response
    assert _read_text(tmp_path/'raw_output.txt') == response['content']


@pytest.mark.parametrize('content', ['prefix\n{}', '{}', None, ''])
def test_http_extraction_does_not_join_reasoning_or_wrap_content(tmp_path, monkeypatch, content):
    message = {'role': 'assistant', 'content': content,
               'reasoning_content': 'SEPARATE_REASONING',
               'thinking_blocks': [{'type': 'thinking', 'thinking': 'SEPARATE_THINKING'}],
               'provider_specific_fields': {'thinking_blocks': ['PROVIDER_THINKING']}}
    payload = {'choices': [{'message': message, 'finish_reason': 'stop'}], 'model': 'offline'}
    encoded = json.dumps(payload).encode()

    class Response:
        status_code = 200
        content = encoded

        def json(self):
            return json.loads(self.content)

    class Session:
        calls = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *args, **kwargs):
            Session.calls += 1
            return Response()

    monkeypatch.setattr('requests.Session', Session)
    generate = grouping.live_generator(base_url='http://offline.invalid', key='offline', model='offline')
    result = generate([{'role': 'user', 'content': 'Offline fixture.'}], tmp_path)
    assert Session.calls == 1
    assert (tmp_path/'http_response.txt').read_bytes() == encoded
    assert result['content'] == (content or '')
    assert result == grouping.response_value(payload)
    if content == 'prefix\n{}':
        with pytest.raises(ValueError):
            pc.parse_json_response(result['content'])


def test_prompts_share_output_wording_and_keep_visibility_distinction():
    a, b = pc.PROMPT_PATH.read_text(), pc.KNOWLEDGE_PROMPT_PATH.read_text()
    for clause in (
        'Return only one JSON object with `adjustments` and `checks`; put decision grounds in\n`reason`.',
        'In `reason`, enclose each formal reference ID in single backticks.\n'
        'Do not use backticks for ordinary text or action commands.',
        'The first character of each body line is the patch marker:\n'
        'a space for context, `-` for deletion, or `+` for addition. The remaining text must\n'
        'preserve its own list markers, indentation and whitespace.',
    ):
        assert a.count(clause) == b.count(clause) == 1
    assert 'inspect the historical Parent and actual Diff' in a
    assert 'without inspecting unavailable historical sources' in b
    assert a.count('```json') == b.count('```json') == 2
