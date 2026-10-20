"""Shared prompts, explicit legacy reads, configuration-safe reuse; no network."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.skill_evolution.v23 import diagnosis, grouping, prompts
from src.skill_evolution.v23.facts import build_facts
from tests.skill_evolution.v23.test_grouping import record, response
from tests.skill_evolution.v23.test_diagnosis import answer, make_grouping, proposal


BEFORE = Path('experiments/methods/v23/v23_prompt_alignment_001/config/before')
LEGACY = {name: (BEFORE / f'{name}_prompt.md').read_text() for name in ('grouping', 'diagnosis')}


def write(path, obj):
    path.write_text(json.dumps(obj))


def snapshot(path):
    return {p.name: p.read_bytes() for p in path.iterdir() if p.is_file()}


def legacy_diagnosis(tmp_path, decision='revise'):
    group = make_grouping(tmp_path)
    saved = grouping.load_grouping(group)
    out = tmp_path / 'diagnosis'
    value = proposal() if decision == 'revise' else {'decision': decision, 'reason': 'Current evidence reason.', 'plan': None}
    diagnosis.run_diagnosis(group, out, generate=lambda *args: answer(value))
    if value['plan'] is not None:
        for check in value['plan']['checks']:
            check['about'] = check.pop('update_ids')
    write(out / 'response.json', answer(value))
    write(out / 'parsed.json', value)
    write(out / 'diagnosis.json', value)
    (out / 'raw_output.txt').write_text(json.dumps(value))
    messages = diagnosis.messages_for(saved)
    messages[0]['content'] = prompts.legacy_diagnosis_system(saved['background'], LEGACY)
    write(out / 'messages.json', messages)
    (out / 'prompt.md').write_text(messages[0]['content'])
    return out, saved


def test_shared_context_preserves_protocol_and_is_not_extracted_from_grouping(tmp_path, monkeypatch):
    saved = grouping.load_grouping(make_grouping(tmp_path))
    for field in ('system_prompt', 'initial_template', 'history_template'):
        saved['background'][field] += '\nLiteral {{max_steps}} and {current_step} stay unchanged.'
    context = prompts.execution_context(saved['background'])
    before = diagnosis.messages_for(saved)
    for fn in (diagnosis.messages_for, grouping.messages_for):
        system = fn(saved)[0]['content']
        assert system.count(context) == 1
        assert system.count('## Execution Context') == 1
        assert '{{execution_context}}' not in system
        for field in ('system_prompt', 'initial_template', 'history_template'):
            assert saved['background'][field] in system
    custom = tmp_path / 'different_grouping.md'
    custom.write_text('# Unrelated headings\n{{execution_context}}\n## Different task')
    monkeypatch.setattr(grouping, 'PROMPT_PATH', custom)
    assert diagnosis.messages_for(saved) == before


@pytest.mark.parametrize('template', ['No context', '{{execution_context}}{{execution_context}}', '{{execution_context}} {{unknown}}'])
def test_invalid_module_placeholders_rejected(template):
    with pytest.raises(ValueError): prompts.render_prompt(template, {})


def test_rendering_does_not_mutate_shared_facts():
    bundle = build_facts([record()]); before = deepcopy(bundle)
    g = grouping.messages_for(bundle)
    saved = {**bundle, 'grouping': json.loads(response(bundle['facts'])['content'])}
    d = diagnosis.messages_for(saved)
    assert json.loads(g[1]['content']) == bundle['facts']
    assert {k: json.loads(d[1]['content'])[k] for k in bundle['facts']} == bundle['facts']
    assert bundle == before
    assert '{{' not in g[0]['content'] and '{{' not in d[0]['content']


@pytest.mark.parametrize('kind', ['old_only', 'both'])
def test_new_model_output_rejects_about_and_preserves_failure(tmp_path, kind):
    group = make_grouping(tmp_path); out = tmp_path / 'diagnosis'
    value = proposal(); check = value['plan']['checks'][0]
    check['about'] = check['update_ids']
    if kind == 'old_only': del check['update_ids']
    with pytest.raises(ValueError): diagnosis.run_diagnosis(group, out, generate=lambda *args: answer(value))
    assert json.loads((out / 'parsed.json').read_text()) == value
    assert not (out / 'diagnosis.json').exists()


@pytest.mark.parametrize('decision', ['revise', 'no_change', 'need_evidence'])
def test_legacy_validate_then_readonly_convert(tmp_path, decision):
    out, saved = legacy_diagnosis(tmp_path, decision); before = snapshot(out)
    with pytest.raises(ValueError): diagnosis.load_diagnosis(out)
    loaded = diagnosis.load_diagnosis(out, expected_grouping=saved, legacy_templates=LEGACY)
    diagnosis.validate_diagnosis(loaded['diagnosis'], diagnosis.diagnosis_input(saved))
    if decision == 'revise':
        assert 'about' not in loaded['diagnosis']['plan']['checks'][0]
        assert loaded['diagnosis']['plan']['checks'][0]['update_ids'] == ['u1']
    assert snapshot(out) == before


@pytest.mark.parametrize('kind', ['bad_reference', 'extra_field', 'new_field', 'changed_prompt', 'changed_input', 'changed_result'])
def test_legacy_errors_not_hidden_by_conversion(tmp_path, kind):
    out, _ = legacy_diagnosis(tmp_path)
    value = json.loads((out / 'diagnosis.json').read_text())
    check = value['plan']['checks'][0]
    if kind == 'bad_reference': check['about'] = ['u99']
    elif kind == 'extra_field': check['extra'] = 1
    elif kind == 'new_field': check['update_ids'] = check.pop('about')
    elif kind == 'changed_prompt': (out / 'prompt.md').write_text('Changed')
    elif kind == 'changed_input':
        data = json.loads((out / 'input.json').read_text()); data['facts']['parent'] = 'Different Skill'
        write(out / 'input.json', data)
    elif kind == 'changed_result': value['reason'] += 'Changed'
    if kind in ('bad_reference', 'extra_field', 'new_field'):
        write(out / 'response.json', answer(value)); write(out / 'parsed.json', value)
    write(out / 'diagnosis.json', value)
    with pytest.raises(ValueError): diagnosis.load_diagnosis(out, legacy_templates=LEGACY)


@pytest.mark.parametrize('module', ['grouping', 'diagnosis'])
@pytest.mark.parametrize('changed', ['model', 'max_tokens', 'timeout_seconds', 'endpoint', 'temperature', 'reasoning_effort', 'thinking'])
def test_configuration_changes_do_not_reuse_or_recall(tmp_path, module, changed):
    config = grouping.call_configuration(base_url='https://example.test', model='model', max_tokens=100, timeout=30)
    calls = []
    if module == 'grouping':
        records = [record()]; out = tmp_path / 'grouping'
        def generate(*args): calls.append(1); return response(build_facts(records)['facts'])
        run = lambda cfg: grouping.run_grouping(records, out, round_id='r1', generate=generate, call_config=cfg)
    else:
        group = make_grouping(tmp_path); out = tmp_path / 'diagnosis'
        def generate(*args): calls.append(1); return answer()
        run = lambda cfg: diagnosis.run_diagnosis(group, out, generate=generate, call_config=cfg)
    first = run(config); before = snapshot(out)
    assert run(config) == first
    other = deepcopy(config); other[changed] = 'changed'
    with pytest.raises(ValueError): run(other)
    assert calls == [1] and snapshot(out) == before


def test_generator_configuration_must_match_declared(tmp_path):
    def generate(*args): raise AssertionError('Must not be invoked')
    generate.call_config = {'model': 'a'}
    with pytest.raises(ValueError): grouping.run_grouping([record()], tmp_path/'g', round_id='r', generate=generate, call_config={'model':'b'})
    group = make_grouping(tmp_path)
    with pytest.raises(ValueError): diagnosis.run_diagnosis(group, tmp_path/'d', generate=generate, call_config={'model':'b'})


def test_real_historical_archives_remain_readable_but_not_current_reusable():
    g = Path('artifacts/methods/v23/v23_grouping_001/live')
    d = Path('artifacts/methods/v23/v23_diagnosis_001/live')
    if not g.exists() or not d.exists(): pytest.skip('Local historical archives unavailable')
    before = snapshot(g), snapshot(d)
    with pytest.raises(ValueError): grouping.load_grouping(g)
    with pytest.raises(ValueError): diagnosis.load_diagnosis(d)
    saved = grouping.load_grouping(g, legacy_template=LEGACY['grouping'])
    result = diagnosis.load_diagnosis(d, expected_grouping=saved, legacy_templates=LEGACY)
    raw = json.loads((d/'diagnosis.json').read_text())
    for check in raw['plan']['checks']: check['update_ids'] = check.pop('about')
    assert result['diagnosis'] == raw
    assert (snapshot(g), snapshot(d)) == before
    assert len(result['facts']['runs']) == 4
    assert sum(len(r['steps']) for r in result['facts']['runs']) == 93


@pytest.mark.parametrize('module', ['grouping', 'diagnosis'])
def test_changed_current_prompt_rejects_reuse(tmp_path, monkeypatch, module):
    calls = []
    if module == 'grouping':
        mod = grouping; records = [record()]; out = tmp_path/'g'
        def generate(*args): calls.append(1); return response(build_facts(records)['facts'])
        run = lambda: grouping.run_grouping(records, out, round_id='r', generate=generate)
    else:
        mod = diagnosis; group = make_grouping(tmp_path); out = tmp_path/'d'
        def generate(*args): calls.append(1); return answer()
        run = lambda: diagnosis.run_diagnosis(group, out, generate=generate)
    run(); before = snapshot(out)
    changed = tmp_path/'changed.md'; changed.write_text(mod.PROMPT_PATH.read_text()+'\nChanged instruction.\n')
    monkeypatch.setattr(mod, 'PROMPT_PATH', changed)
    with pytest.raises(ValueError): run()
    assert calls == [1] and snapshot(out) == before


def test_real_fact_reassembly_and_actor_prompt_verification_unchanged():
    summary = Path('experiments/methods/v23/v23_grouping_001/results/summary.json')
    paths = [Path(p) for p in json.loads(summary.read_text())['selected_sources']]
    original = Path('artifacts/methods/v23/v23_grouping_001/live/input.json')
    if not original.exists() or not all(p.exists() for p in paths):
        pytest.skip('Local historical trajectories unavailable')
    raw = [p.read_bytes() for p in paths]
    rebuilt = build_facts([json.loads(data) for data in raw])
    assert rebuilt == json.loads(original.read_text())
    assert sum(len(r['steps']) for r in rebuilt['facts']['runs']) == 93
    assert all(e['prompt_verified'] for s in rebuilt['sources'] for e in s['events'])
    assert [p.read_bytes() for p in paths] == raw
