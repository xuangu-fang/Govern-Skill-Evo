"""P4 candidate dispatch, assembly, archive compatibility and offline dataflow."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.skill_evolution.v23 import memory, preconditioner as compiler, editor as base_editor
from src.skill_evolution.v23.prompts import execution_context
from src.skill_evolution.v23_4 import replay, preconditioner as pc, editor, diagnosis
from .test_diagnosis_replay import chain
from .test_multi_knowledge_chain import seed
from .test_multi_knowledge_memory import knowledge, proposal, output
from .helpers import Fake, keep, revise, read

OLD, NEW = memory.LEGACY_CONTRACT, memory.MULTI_KNOWLEDGE_CONTRACT
P4 = replay.LEARNING_PROMPT_VERSION
EXPERIMENT = Path('experiments/methods/v23_4/multi_knowledge_p4_001')


def test_candidate_matches_frozen_original_with_only_two_edits():
    original = (EXPERIMENT / 'original_prompt.md').read_text()
    candidate = (EXPERIMENT / 'candidate_prompt.md').read_text()
    expected = original.replace('Choose one of:',
        'For each relevant theme, choose whether to create a new entry, revise existing entries, or leave them unchanged. '
        'A response may contain both new and revised entries. Return `{"entries":[]}` only when no theme warrants an update.')
    anchor = 'Do not claim a historical statement was false solely because compact evidence does not display a relevant state or menu.'
    expected = expected.replace(anchor, anchor + '\n\nWhen historical detail is insufficient to reassess a prior claim, '
        'distinguish lack of verification from contradiction. Preserve the supported comparison and state what remains unresolved.')
    assert candidate == expected == replay.LEARNING_PROMPT_PATH.read_text()
    assert '{{execution_context}}' not in candidate


def test_assembly_changes_system_only_and_appends_each_context_once(chain):
    bundle = chain[-1]
    p3 = replay.messages_for(bundle, memory_contract=NEW)
    p4 = replay.messages_for(bundle, memory_contract=NEW, prompt_version=P4)
    system = p4[0]['content']
    assert p4[1] == p3[1]
    assert system == '\n\n'.join([
        replay.LEARNING_PROMPT_PATH.read_text().rstrip(), execution_context(bundle['background']),
        replay.MEMORY_FORMAT_PATH.read_text(), replay.MULTI_VIEW_PATH.read_text(), replay.MULTI_FORMAT_PATH.read_text()])
    for heading in ['## Execution Context', '## Historical Memory evidence view v3',
                    '## Replay paired-input view v1', '## Multi-Knowledge Memory representation v1']:
        assert system.count(heading) == 1
    assert set(json.loads(p4[1]['content'])) == {'parent', 'diff', 'plan', 'command_sets', 'runs', 'pairs', 'memory'}


@pytest.mark.parametrize('contract,version', [(OLD, replay.PROMPT_VERSION), (NEW, replay.MULTI_PROMPT_VERSION), (NEW, P4)])
def test_all_registered_versions_reload_without_silent_default_switch(chain, tmp_path, contract, version):
    bundle = chain[-1]; out = tmp_path / 'replay'; fake = Fake(output())
    saved = replay.run_replay(bundle, out, generate=fake, memory_contract=contract, prompt_version=version)
    assert read(out / 'run.json')['prompt_version'] == version
    assert replay.load_replay(out, expected_memory_contract=contract, expected_prompt_version=version) == saved
    assert replay.run_replay(bundle, out, generate=fake, memory_contract=contract, prompt_version=version) == saved
    assert fake.calls == 1
    if version != P4:
        assert replay.messages_for(bundle, memory_contract=contract) == replay.messages_for(bundle, memory_contract=contract, prompt_version=version)
    else:
        with pytest.raises(ValueError, match='prompt version differs'):
            replay.run_replay(bundle, out, generate=fake, memory_contract=NEW)
    assert fake.calls == 1


@pytest.mark.parametrize('contract,version', [(OLD, P4), (OLD, replay.MULTI_PROMPT_VERSION),
    (NEW, replay.PROMPT_VERSION), (NEW, 'unknown'), (NEW, 12), (NEW, [])])
def test_invalid_versions_fail_before_call_even_for_empty_memory(chain, tmp_path, contract, version):
    fake = Fake(output()); out = tmp_path / 'invalid'
    with pytest.raises(ValueError):
        replay.run_replay(chain[-1], out, generate=fake, memory_contract=contract, prompt_version=version)
    assert fake.calls == 0 and not out.exists()


def test_p4_requires_paired_input_view(chain, tmp_path):
    fake = Fake(output()); out = tmp_path / 'old_view'
    with pytest.raises(ValueError, match='paired Replay input view'):
        replay.run_replay(chain[-1], out, generate=fake, memory_contract=NEW, prompt_version=P4,
                          input_view=replay.LEGACY_INPUT_VIEW)
    assert fake.calls == 0 and not out.exists()


@pytest.mark.parametrize('defect', ['p3_version', 'missing_version', 'unknown_version', 'wrong_memory',
    'system', 'template', 'view', 'raw', 'output', 'config'])
def test_p4_archive_tampering_and_cross_version_reuse_refused(chain, tmp_path, monkeypatch, defect):
    out = tmp_path / 'replay'
    fake = Fake(output(proposal()))
    replay.run_replay(chain[-1], out, generate=fake, memory_contract=NEW, prompt_version=P4)
    if defect in ('p3_version', 'missing_version', 'unknown_version', 'wrong_memory'):
        meta = read(out / 'run.json')
        if defect == 'missing_version': del meta['prompt_version']
        elif defect == 'wrong_memory': meta['memory_contract'] = OLD
        else: meta['prompt_version'] = replay.MULTI_PROMPT_VERSION if defect == 'p3_version' else 'unknown'
        (out / 'run.json').write_text(json.dumps(meta))
    elif defect == 'system': (out / 'prompt.md').write_text('changed')
    elif defect == 'template':
        template = tmp_path / 'changed.md'; template.write_text(replay.LEARNING_PROMPT_PATH.read_text() + '\nChanged')
        monkeypatch.setattr(replay, 'LEARNING_PROMPT_PATH', template)
    elif defect == 'view':
        model = read(out / 'model_input.json'); model['pairs'][0]['parent_result']['steps'] += 1
        (out / 'model_input.json').write_text(json.dumps(model))
    elif defect == 'raw': (out / 'raw_output.txt').write_text('{}')
    elif defect == 'output': (out / 'replay.json').write_text('{"entries":[]}')
    if defect == 'config':
        with pytest.raises(ValueError): replay.load_replay(out, expected_call_config={})
    else:
        with pytest.raises(ValueError): replay.load_replay(out)


def test_p4_new_and_revised_entries_commit_and_feed_next_patch(chain, tmp_path):
    gd, dd, _, _, _, _, original = chain
    root = tmp_path / 'memory'; active = seed(root, original)
    bundle = deepcopy(original); bundle['payload']['memory'] = active
    sources = replay.history_pair_sources(root, active, memory_contract=NEW)
    # Artificial observations exercise complete replacement, not semantic quality.
    result = output(proposal(deepcopy(active['entries'][0]['knowledge'][0]),
                              knowledge('Synthetic updated response.', ['diff', 'P1:1', 'Q1:1']), revises=['M1']),
                    proposal(knowledge('Synthetic separate theme.', ['diff', 'P2:2', 'Q2:2'])))
    rd = tmp_path / 'replay'
    saved = replay.run_replay(bundle, rd, generate=Fake(result), memory_contract=NEW,
                              prompt_version=P4, history_sources=sources)
    assert memory.load_memory(root, memory_contract=NEW) == active
    memory.commit_memory(root, context_id='R2', context=bundle, result=saved['replay'], memory_contract=NEW)
    new = memory.load_memory(root, memory_contract=NEW)
    assert [e['id'] for e in new['entries']] == ['M2', 'M3']
    assert new['entries'][0]['knowledge'][0] == active['entries'][0]['knowledge'][0]
    payload = compiler.preconditioner_input(diagnosis.load_diagnosis(dd), memory=new, memory_contract=NEW)
    value = keep(payload); value['adjustments'][0] = revise(payload)
    value['adjustments'][0]['reason'] = 'The conditional observations in `M2`, `M3` and `R2/Q2:2` motivate this unverified change.'
    pd = tmp_path / 'next_pc'
    effective = pc.run_preconditioner(gd, dd, pd, generate=Fake(value), memory=new, memory_contract=NEW)
    assert pc.load_preconditioner(pd, expected_memory_contract=NEW) == effective
    candidate = 'Synthetic revised Skill.\n'
    ed = tmp_path / 'next_editor'
    updated = editor.run_editor(pd, ed, generate=Fake({'patch': base_editor.actual_diff(None, candidate), 'reason': 'Offline fixture.'}))
    assert editor.load_editor(ed)['actual_diff'] == updated['actual_diff']


@pytest.mark.parametrize('case', ['R05', 'R06'])
def test_frozen_real_p4_messages_rebuild_without_fact_changes(case):
    root = EXPERIMENT / 'cases' / case
    b = read(root / 'replay_bundle.json'); sources = read(root / 'history_pair_sources.json')
    actual = replay.messages_for(b, memory_contract=NEW, prompt_version=P4, history_sources=sources)
    assert actual == read(root / 'messages.json')
    p3 = replay.messages_for(b, memory_contract=NEW, history_sources=sources)
    assert p3[1] == actual[1]
    baseline = Path('experiments/methods/v23_4/replay_prompt_candidate_001/config') / case
    old = read(baseline / 'replay_bundle.json')
    assert b['payload']['memory'] == memory.normalize_memory(old['payload']['memory'], source_contract=OLD)
    recovered = deepcopy(b); recovered['payload']['memory'] = old['payload']['memory']
    assert recovered == old
    expected = read(baseline / 'model_input.json'); expected['memory']['entries'] = b['payload']['memory']['entries']
    assert json.loads(actual[1]['content']) == expected
