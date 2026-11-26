"""Explicit citations retain permissions without interpreting spreadsheet syntax."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from src.skill_evolution.v25 import editor, preconditioner, output_feedback
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from src.skill_evolution.v25.contracts.preconditioner import preconditioner_input
from src.skill_evolution.v25.contracts.memory import MULTI_KNOWLEDGE_CONTRACT
from src.skill_evolution.v25.explicit_references import permissions, parse
from src.skill_evolution.v25.update_patch import (
    CONTRACT_VERSION, LEGACY_CONTRACT_VERSION, normalize_update_patches, compile_effective_plan,
)
from .test_preconditioner_context import fixture, with_history, keep
from .test_pipeline import campaign
from .support import MethodResponses, response


@pytest.fixture
def payload():
    with using_benchmark(SpreadsheetBenchAdapter()):
        yield with_history(fixture())


def allowed(payload):
    return permissions(payload, [], memory_contract=MULTI_KNOWLEDGE_CONTRACT)


@pytest.mark.parametrize('value', [
    'A2:M70', '=G2*H2', '=$M$70', "'Sheet 1'!$P$3:$Q$4", 'M12 P3 Q4 C12',
    '`A2:M70`', '`=G2*H2`', '`delete_rows`', '```python\nx = "M70"\n```',
])
def test_spreadsheet_and_code_text_are_not_citations(payload, value):
    assert parse(value, allowed(payload), location='reason') == []
    _, plan = normalize_update_patches(keep(value), payload)
    assert plan == payload['plan']


@pytest.mark.parametrize('namespace,ref', [
    ('Memory', 'M1'), ('Group', 'G1'), ('Evidence', 'P1:0'), ('Evidence', 'P1:1'),
    ('Evidence', 'P1:outcome'), ('Evidence', 'R_demo/diff'), ('Evidence', 'R_demo/P1:1'),
    ('Update', 'u1'), ('Check', 'c1'),
])
def test_all_types_and_mixed_formula_text(payload, namespace, ref):
    value = f'Use =G2*H2 in A2:M70; `{namespace}:{ref}` supplies context; `delete_rows` is code.'
    assert parse(value, allowed(payload), location='reason') == [(namespace, ref)]
    normalize_update_patches(keep(value), payload)


@pytest.mark.parametrize('value', [
    '`Memory:M999`', '`Group:G999`', '`Group:M1`', '`Memory:G1`', '`Evidence:M1`',
    '`Group:G2`',  # Group exists in the archive but is not visible provenance.
    '`Evidence:R_demo/P1`', '`Evidence:R_demo/P1:outcome`', '`Evidence:R_demo/P1:2`',
    '`Evidence:P99:1`', '`Update:u999`', '`Check:c999`',
    'Memory:M1', '`Memory:M1', 'Memory:M1`', '``Memory:M1``',
    '`Memory: M1`', '`Memory:M1 M2`', '`Memory :M1`', '`Evidence:R_demo/P1:1-2`',
])
def test_invalid_or_unavailable_explicit_citations_fail(payload, value):
    with pytest.raises(ValueError, match='explicit reference|single-backtick'):
        normalize_update_patches(keep(value), payload)


def modified(payload, reason):
    original = payload['plan']['updates'][0]['text']
    replacement = original.rstrip('\n') + '\n- Inspect A2:M70 and =G2*H2 without changing unrelated cells.\n'
    removed = ''.join('-'+x+'\n' for x in original.splitlines())
    if not original.endswith('\n'):
        removed += '\\ No newline at end of file\n'
    patch = '--- a/SKILL.md\n+++ b/SKILL.md\n@@\n' + removed + ''.join('+'+x for x in replacement.splitlines(True))
    return {'adjustments': [{'target': 'u1', 'focus': ['S'], 'change': 'Inspect A2:M70 and `=G2*H2`.',
                            'reason': reason, 'to': {'patch': patch}}],
            'checks': [{'id': 'c2', 'update_ids': ['u1'],
                        'question': 'Does A2:M70 preserve values, following `Update:u1` and `Check:c2`?'}]}


def test_full_normalization_compilation_and_editor_handoff(payload):
    before = deepcopy(payload)
    raw = modified(payload, '`Memory:M1` and `Evidence:R_demo/P1:1` motivate `Update:u1`; '
                            '`Group:G1` is inherited provenance and `Evidence:P1:1` is current.')
    normalized, effective = normalize_update_patches(raw, payload)
    assert 'M1' in normalized['adjustments'][0]['basis']
    assert 'P1:1' in normalized['adjustments'][0]['basis']
    assert 'Memory:M1' not in normalized['adjustments'][0]['basis']
    assert 'R_demo/P1:1' not in normalized['adjustments'][0]['basis']  # legacy basis scope unchanged
    assert compile_effective_plan(normalized, payload) == effective
    saved = {'facts': {k: payload[k] for k in ('parent', 'runs')},
             'grouping': payload['grouping'], 'memory': payload['memory'],
             'diagnosis': {'decision': 'revise', 'reason': 'Review P1:1.', 'plan': payload['plan']},
             'preconditioner': normalized, 'effective_plan': effective,
             'preconditioner_contract': CONTRACT_VERSION}
    assert editor.editor_input(saved)['plan'] == effective
    assert payload == before
    # Rechecking cannot silently accept a changed citation.
    tampered = deepcopy(normalized)
    tampered['adjustments'][0]['reason'] += ' `Memory:M999`'
    with pytest.raises(ValueError, match='M999'):
        compile_effective_plan(tampered, payload)


@pytest.mark.parametrize('field', ['change', 'text', 'check'])
def test_explicit_checks_apply_to_all_output_prose(payload, field):
    raw = modified(payload, '`Evidence:P1:1` supports the change.')
    if field == 'change': raw['adjustments'][0]['change'] += ' `Group:G2`'
    elif field == 'text': raw['adjustments'][0]['to']['patch'] += '+Do what `Group:G2` says.\n'
    else: raw['checks'][0]['question'] += ' `Group:G2`'
    with pytest.raises(ValueError, match='G2'):
        normalize_update_patches(raw, payload)


def test_bad_citation_uses_existing_output_retry_classification(payload):
    with pytest.raises(output_feedback.OutputValidationError, match='M999'):
        output_feedback.output_call('Preconditioner output', normalize_update_patches,
                                    keep('`Memory:M999` supports this.'), payload)


def test_legacy_contract_keeps_its_original_rules(payload):
    _, plan = normalize_update_patches(keep('`M1` and `P1:1` support `u1`.'), payload,
                                      contract_version=LEGACY_CONTRACT_VERSION)
    assert plan == payload['plan']
    with pytest.raises(ValueError, match='M70'):
        normalize_update_patches(keep('Inspect A2:M70.'), payload,
                                 contract_version=LEGACY_CONTRACT_VERSION)


class ExplicitMethods(MethodResponses):
    def __call__(self, messages, directory):
        result = super().__call__(messages, directory)
        if 'preconditioner' in Path(directory).parts:
            p = json.loads(messages[1]['content'])
            result = response(json.dumps(modified(p, '`Evidence:P1:1` supports `Update:u1`; use `delete_rows` in A2:M70.')))
        return result


def test_new_and_legacy_archives_reload_without_reinterpreting_versions(tmp_path):
    root, _, adapter, _, _, _ = campaign(tmp_path, method=ExplicitMethods())
    new = root/'rounds/R01/preconditioner/attempts/001'
    ed = root/'rounds/R01/editor/attempts/001'
    with using_benchmark(adapter):
        saved = preconditioner.load_preconditioner(new)
        assert saved['preconditioner_contract'] == CONTRACT_VERSION
        assert editor.load_editor(ed)['effective_plan'] == saved['effective_plan']
        # Build a synthetic v3 archive in tmp_path; never mutate real experiments.
        old = tmp_path/'legacy_preconditioner'
        shutil.copytree(new, old)
        read = lambda name: json.loads((old/name).read_text())
        write = lambda name, value: (old/name).write_text(json.dumps(value))
        meta = read('run.json')
        meta.update(contract_version=LEGACY_CONTRACT_VERSION, prompt_version=preconditioner.LEGACY_PROMPT_VERSION)
        write('run.json', meta)
        upstream = read('input.json')
        raw = keep('`P1:1` supports `u1`.')
        normalized, plan = normalize_update_patches(raw, preconditioner_input(upstream),
                                                  contract_version=LEGACY_CONTRACT_VERSION)
        messages = preconditioner.messages_for(upstream, contract_version=LEGACY_CONTRACT_VERSION,
                    retry_policy=output_feedback.policy(output_feedback.saved_context(old)))
        messages = output_feedback.request_messages(messages, output_feedback.saved_context(old))
        write('messages.json', messages); (old/'prompt.md').write_text(messages[0]['content'])
        write('response.json', response(json.dumps(raw))); (old/'raw_output.txt').write_text(json.dumps(raw))
        write('parsed.json', raw); write('preconditioner.json', normalized); write('effective_plan.json', plan)
        write('actual_diffs.json', {})
        before = {f.name: f.read_bytes() for f in old.iterdir() if f.is_file()}
        loaded = preconditioner.load_preconditioner(old)
        assert 'preconditioner_contract' not in loaded
        assert editor.editor_input(loaded)['plan'] == plan
        old_editor = tmp_path/'legacy'/'editor'
        editor.run_editor(old, old_editor, generate=MethodResponses(), max_input_chars=4000000)
        assert editor.load_editor(old_editor)['effective_plan'] == plan
        assert before == {f.name: f.read_bytes() for f in old.iterdir() if f.is_file()}
        meta['prompt_version'] = preconditioner.KNOWLEDGE_PROMPT_VERSION
        write('run.json', meta)
        with pytest.raises(ValueError, match='version mismatch'):
            preconditioner.load_preconditioner(old)
