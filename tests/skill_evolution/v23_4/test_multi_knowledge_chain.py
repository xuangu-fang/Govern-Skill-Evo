"""P3 versioned dataflow and evidence conservation; injected responses only."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from src.skill_evolution.v23 import memory, preconditioner as compiler, editor as base_editor
from src.skill_evolution.v23_3 import memory_view as view
from src.skill_evolution.v23_4 import preconditioner as pc, replay, editor, diagnosis, update_patch
from .test_diagnosis_replay import chain
from .helpers import Fake, keep, revise, read, memory as synthetic_memory
from .test_multi_knowledge_memory import knowledge, proposal, output
from tests.skill_evolution.v23.test_replay_memory import records

OLD = memory.LEGACY_CONTRACT
NEW = memory.MULTI_KNOWLEDGE_CONTRACT


def seed(root, bundle):
    memory.commit_memory(root, context_id='R1', context=bundle, result={'entries': [{
        'revises': [], 'knowledge': 'Synthetic earlier joint response; not a learned claim.',
        'evidence': ['diff', 'P1:1', 'Q1:1']}]})
    return memory.load_memory(root, memory_contract=NEW)


@pytest.mark.parametrize('mode', [view.FORMAT, view.LEGACY])
def test_entire_contract_chain_and_editor_handoff(chain, tmp_path, monkeypatch, mode):
    gd, dd, _, ed, parents, candidates, original = chain
    root = tmp_path / 'memory'
    active = seed(root, original)
    old_bytes = (root / 'archive/R1.json').read_bytes()
    bundle = replay.build_replay(ed, parents, candidates, memory=active, memory_contract=NEW)
    sources = replay.history_pair_sources(root, active, memory_contract=NEW)
    result = output(proposal(
        knowledge('Updated response under first conditions.', ['diff', 'P1:1', 'Q1:1']),
        knowledge('Independent second conditions.', ['P2:2', 'Q2:2']),
        deepcopy(active['entries'][0]['knowledge'][0]), revises=['M1']))
    rd = tmp_path / 'replay'
    generated = Fake(result)
    saved = replay.run_replay(bundle, rd, generate=generated, memory_contract=NEW, history_sources=sources)
    assert replay.load_replay(rd, expected_memory_contract=NEW) == saved
    assert replay.run_replay(bundle, rd, generate=generated, memory_contract=NEW, history_sources=sources) == saved
    assert generated.calls == 1
    assert read(rd / 'run.json')['memory_contract'] == NEW
    assert read(rd / 'run.json')['prompt_version'] == replay.MULTI_PROMPT_VERSION
    assert read(rd / 'input.json') == bundle
    assert read(rd / 'model_input.json')['memory']['entries'] == active['entries']
    assert read(rd / 'input.json')['payload']['runs'] != read(rd / 'model_input.json')['runs']
    assert set(read(rd / 'model_input.json')) == set(bundle['payload'])
    assert not (root / 'archive/R2.json').exists()  # Replay never publishes Memory.
    memory.commit_memory(root, context_id='R2', context=bundle, result=saved['replay'], memory_contract=NEW)
    newer = memory.load_memory(root, memory_contract=NEW)
    assert (root / 'archive/R1.json').read_bytes() == old_bytes
    assert newer['entries'][0]['id'] == 'M2'
    sources2 = replay.history_pair_sources(root, newer, memory_contract=NEW)
    b2 = deepcopy(bundle); b2['payload']['memory'] = newer
    projected = replay.model_input(b2, history_sources=sources2, memory_contract=NEW)
    assert {p['context'] for p in projected['memory']['pairs']} == {'R1', 'R2'}
    assert {'R2/P2', 'R2/Q2'} <= projected['memory']['sources'].keys()
    pc_saved = {**diagnosis.load_diagnosis(dd), 'memory': newer}
    payload = compiler.preconditioner_input(pc_saved, memory_contract=NEW)
    raw = keep(payload)
    replacement = 'Inspect relevant visible containers while preserving target identity.\n'
    raw['adjustments'][0] = revise(payload, replacement=replacement)
    raw['adjustments'][0]['reason'] = 'The conditions in `M2` and `R2/Q2:2` motivate this unverified change.'
    # Guard the important internal boundary, including archive reconstruction.
    actual_compile = update_patch.compile_effective_plan
    contracts = []
    def checked_compile(result, payload, *, memory_contract=OLD):
        contracts.append(memory_contract)
        assert memory_contract == NEW
        return actual_compile(result, payload, memory_contract=memory_contract)
    monkeypatch.setattr(update_patch, 'compile_effective_plan', checked_compile)
    pd = tmp_path / 'next_pc'
    pc_fake = Fake(raw)
    effective = pc.run_preconditioner(gd, dd, pd, generate=pc_fake, memory=newer,
                                      memory_contract=NEW, memory_view=mode)
    assert contracts and all(c == NEW for c in contracts)
    assert effective['effective_plan']['updates'][0]['text'] == replacement
    assert read(pd / 'run.json')['memory_contract'] == NEW
    assert pc.load_preconditioner(pd, expected_memory_contract=NEW) == effective
    assert pc.model_input(effective, memory_contract=NEW, memory_view=mode) == read(pd / 'model_input.json')
    assert pc.run_preconditioner(gd, dd, pd, generate=pc_fake, memory=newer,
                                 memory_contract=NEW, memory_view=mode) == effective
    assert pc_fake.calls == 1
    assert 'memory_contract' not in effective['effective_plan'] and 'memory_contract' not in raw
    new_ed = tmp_path / 'next_editor'
    fake_ed = Fake({'patch': base_editor.actual_diff(None, 'Synthetic candidate.\n'), 'reason': 'Offline handoff.'})
    edited = editor.run_editor(pd, new_ed, generate=fake_ed)
    assert json.loads(fake_ed.messages[1]['content']) == {'parent': None, 'plan': effective['effective_plan']}
    assert editor.load_editor(new_ed) == edited
    next_bundle = replay.build_replay(new_ed, parents, records('Synthetic candidate.\n'),
                                     memory=newer, memory_contract=NEW)
    replay.validate_bundle(next_bundle, memory_contract=NEW)
    assert next_bundle['payload']['diff'] == edited['actual_diff']
    # Tampering the Preconditioner contract invalidates Editor's upstream reload.
    meta = read(pd / 'run.json'); meta['memory_contract'] = OLD
    (pd / 'run.json').write_text(json.dumps(meta))
    with pytest.raises(ValueError): editor.load_editor(new_ed)


def multi_fixture(payload):
    full = memory.normalize_memory(synthetic_memory(payload), source_contract=OLD)
    run = full['sources']['R1/P1']['run']
    template = deepcopy(run['steps'][0]); previous = deepcopy(run['initial'])
    steps = []
    for n in range(1, 19):
        step = deepcopy(template)
        step.update(step=f'P1:{n}', before=deepcopy(previous), action=f'synthetic action {n}')
        step['feedback'].update(done=n == 18, won=n == 18)
        previous = step['after']
        steps.append(step)
    run['steps'] = steps
    full['entries'][0]['knowledge'] = [knowledge('First condition.', ['R1/diff', 'R1/P1:1']),
                                      knowledge('Second condition.', ['R1/P1:14'])]
    return full


def test_every_knowledge_contributes_windows_without_merging_claims(payload):
    full = multi_fixture(payload); before = deepcopy(full)
    projected = view.compact_memory(full, memory_contract=NEW)
    source = projected['sources']['R1/P1']
    assert source['windows'] == [{'start': 1, 'end': 3}, {'start': 12, 'end': 16}]
    assert len(source['run']['trace']) == 18
    assert source['run']['trace'] == [{'step': f"R1/{s['step']}", 'action': s['action'], 'feedback': s['feedback']}
                                     for s in full['sources']['R1/P1']['run']['steps']]
    assert projected['entries'] == full['entries'] and full == before
    assert 'evidence' not in projected['entries'][0]
    # Repeating a fact across Knowledge changes neither sources nor windows/menus.
    full['entries'][0]['knowledge'].append(knowledge('Another interpretation.', ['R1/P1:14']))
    again = view.compact_memory(full, memory_contract=NEW)
    assert again['sources'] == projected['sources'] and again['command_pool'] == projected['command_pool']


@pytest.mark.parametrize('mode', [view.FORMAT, view.LEGACY])
@pytest.mark.parametrize('layer', ['input', 'projection', 'messages', 'adjustment', 'compiler'])
def test_each_boundary_rejects_wrong_contract(upstream, payload, mode, layer):
    full = multi_fixture(payload)
    saved = {**upstream[2], 'memory': full}
    new_payload = compiler.preconditioner_input(saved, memory_contract=NEW)
    raw = keep(new_payload); raw['adjustments'][0] = revise(new_payload)
    legacy_result, _ = update_patch.normalize_update_patches(raw, new_payload, memory_view=mode, memory_contract=NEW)
    calls = {
        'input': lambda: compiler.preconditioner_input(saved),
        'projection': lambda: pc.model_input(saved, memory_view=mode),
        'messages': lambda: pc.messages_for(saved, memory_view=mode),
        'adjustment': lambda: update_patch.normalize_update_patches(raw, new_payload, memory_view=mode),
        'compiler': lambda: compiler.compile_effective_plan(legacy_result, new_payload),
    }
    with pytest.raises(ValueError): calls[layer]()


@pytest.mark.parametrize('stage', ['pc', 'replay'])
@pytest.mark.parametrize('wrong', [OLD, 'unknown', None, 'missing'])
def test_empty_memory_cannot_bypass_archive_contract(chain, tmp_path, stage, wrong):
    gd, dd, _, _, _, _, bundle = chain
    out = tmp_path / 'new_run'
    if stage == 'pc':
        fake = Fake(keep(compiler.preconditioner_input(diagnosis.load_diagnosis(dd))))
        pc.run_preconditioner(gd, dd, out, generate=fake, memory_contract=NEW)
        loader = pc.load_preconditioner
        with pytest.raises(ValueError): pc.run_preconditioner(gd, dd, out, generate=fake)
    else:
        fake = Fake({'entries': []})
        replay.run_replay(bundle, out, generate=fake, memory_contract=NEW)
        loader = replay.load_replay
        with pytest.raises(ValueError): replay.run_replay(bundle, out, generate=fake)
    assert fake.calls == 1
    with pytest.raises(ValueError): loader(out, expected_memory_contract=OLD)
    meta = read(out / 'run.json')
    if wrong == 'missing': del meta['memory_contract']
    else: meta['memory_contract'] = wrong
    (out / 'run.json').write_text(json.dumps(meta))
    with pytest.raises(ValueError): loader(out)


@pytest.mark.parametrize('mode', ['keep', 'withdraw', 'late_bad_patch', 'bad_reference'])
def test_new_memory_adjustment_semantics_and_atomic_failure(upstream, payload, mode):
    gd, dd, _, pd = upstream
    full = multi_fixture(payload)
    raw = keep(payload)
    if mode == 'withdraw':
        for item in raw['adjustments']:
            item.update(focus=['C'], change='Withdraw this proposal.', to=[])
        raw['checks'] = []
    elif mode == 'late_bad_patch':
        raw['adjustments'][0] = revise(payload)
        raw['adjustments'][-1] = revise(payload, len(raw['adjustments']) - 1)
        raw['adjustments'][-1]['to']['patch'] = 'broken'
    elif mode == 'bad_reference':
        raw['adjustments'][0]['reason'] = 'Unknown historical state in `R1/P1:999`.'
    fake = Fake(raw)
    if mode in ('late_bad_patch', 'bad_reference'):
        with pytest.raises(ValueError): pc.run_preconditioner(gd, dd, pd, generate=fake, memory=full, memory_contract=NEW)
        assert not (pd / 'effective_plan.json').exists()
        assert read(pd / 'run.json')['status'] == 'invalid'
    else:
        result = pc.run_preconditioner(gd, dd, pd, generate=fake, memory=full, memory_contract=NEW)
        assert result['effective_plan'] == (None if mode == 'withdraw' else result['diagnosis']['plan'])


@pytest.mark.parametrize('input_view', [replay.INPUT_VIEW, replay.LEGACY_INPUT_VIEW])
def test_new_replay_format_and_budget(chain, tmp_path, input_view):
    bundle = chain[-1]
    messages = replay.messages_for(bundle, memory_contract=NEW, input_view=input_view)
    system = messages[0]['content']
    assert 'Each entry contains exactly two fields:' in system
    assert 'Each entry contains exactly three fields:' not in system
    assert 'Multi-Knowledge Memory representation v1' in system
    assert '{{execution_context}}' not in system
    fake = Fake(output(proposal()))
    saved = replay.run_replay(bundle, tmp_path / 'valid', generate=fake, memory_contract=NEW, input_view=input_view)
    assert saved['replay']['entries'][0]['knowledge'][0]['evidence'] == ['diff', 'P1:1', 'Q1:2']
    budget = Fake(output())
    with pytest.raises(ValueError, match='budget'):
        replay.run_replay(bundle, tmp_path / 'budget', generate=budget, memory_contract=NEW, input_view=input_view, max_input_chars=1)
    assert budget.calls == 0


@pytest.mark.parametrize('kind', ['legacy_output', 'bad_second_evidence', 'length', 'duplicate_key'])
def test_replay_errors_do_not_publish_or_fall_back(chain, tmp_path, kind):
    value = output(proposal())
    if kind == 'legacy_output': value = {'entries': [{'revises': [], 'knowledge': 'Old shape.', 'evidence': ['diff', 'P1:1']}]}
    if kind == 'bad_second_evidence': value['entries'][0]['knowledge'].append(knowledge(evidence=['P2:999']))
    fake = Fake(value, finish='length' if kind == 'length' else 'stop',
                content='{"entries":[],"entries":[]}' if kind == 'duplicate_key' else None)
    out = tmp_path / 'invalid'
    with pytest.raises(ValueError): replay.run_replay(chain[-1], out, generate=fake, memory_contract=NEW)
    assert read(out / 'run.json')['status'] == 'invalid' and not (out / 'replay.json').exists()
    with pytest.raises(ValueError): replay.run_replay(chain[-1], out, generate=fake, memory_contract=NEW)
    assert fake.calls == 1


@pytest.mark.parametrize('round_id', ['R04', 'R05'])
def test_real_old_memory_has_identical_projection_and_pairs(round_id):
    root = Path('artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds') / round_id / 'memory'
    old = memory.load_memory(root)
    new = memory.load_memory(root, memory_contract=NEW)
    a, b = view.compact_memory(old), view.compact_memory(new, memory_contract=NEW)
    for key in ('format', 'policy', 'sources', 'command_pool'): assert a[key] == b[key]
    assert b['entries'] == new['entries']
    assert replay.history_pair_sources(root, old) == replay.history_pair_sources(root, new, memory_contract=NEW)


@pytest.mark.parametrize('defect', ['unknown_version', 'wrong_shape_version', 'hash', 'task_identity'])
def test_mixed_pair_sources_are_versioned_and_verified(chain, tmp_path, defect):
    bundle = deepcopy(chain[-1]); root = tmp_path / 'memory'
    bundle['payload']['memory'] = seed(root, bundle)
    result = output(proposal(knowledge(evidence=['diff', 'P2:1', 'Q2:1']),
                             deepcopy(bundle['payload']['memory']['entries'][0]['knowledge'][0]), revises=['M1']))
    memory.commit_memory(root, context_id='R2', context=bundle, result=result, memory_contract=NEW)
    full = memory.load_memory(root, memory_contract=NEW)
    sources = replay.history_pair_sources(root, full, memory_contract=NEW)
    bundle['payload']['memory'] = full
    path = root / 'archive/R2.json'; archived = read(path)
    if defect == 'hash': path.write_text(path.read_text() + ' ')
    else:
        if defect == 'unknown_version': archived['memory_contract'] = 'unknown'
        elif defect == 'wrong_shape_version': archived['memory_contract'] = OLD
        else: archived['context']['pair_audit'][1]['candidate']['task_id'] = 'different'
        path.write_text(json.dumps(archived))
        sources['R2']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError): replay.model_input(bundle, history_sources=sources, memory_contract=NEW)


@pytest.mark.parametrize('case', ['R05', 'R06'])
def test_frozen_real_inputs_change_only_entry_representation(case):
    root = Path('experiments/methods/v23_4/replay_input_view_live_001/config') / case
    bundle = read(root / 'replay_bundle.json')
    before = deepcopy(bundle)
    sources = read(root / 'history_pair_sources.json')
    assert replay.messages_for(bundle, history_sources=sources) == read(root / 'messages.json')
    old = replay.model_input(bundle, history_sources=sources)
    assert old == read(root / 'model_input.json')
    new_bundle = deepcopy(bundle)
    new_bundle['payload']['memory'] = memory.normalize_memory(bundle['payload']['memory'], source_contract=OLD)
    new = replay.model_input(new_bundle, history_sources=sources, memory_contract=NEW)
    expected = deepcopy(old)
    expected['memory']['entries'] = new_bundle['payload']['memory']['entries']
    assert new == expected and bundle == before
    assert new['runs'] == old['runs'] and new['pairs'] == old['pairs']


@pytest.mark.parametrize('stage', ['pc', 'replay'])
def test_unknown_contract_stops_before_generation_with_empty_memory(chain, tmp_path, stage):
    gd, dd, _, _, _, _, bundle = chain
    fake = Fake({'entries': []})
    out = tmp_path / 'unknown'
    with pytest.raises(ValueError, match='Unsupported Memory contract'):
        if stage == 'pc': pc.run_preconditioner(gd, dd, out, generate=fake, memory_contract='unknown')
        else: replay.run_replay(bundle, out, generate=fake, memory_contract='unknown')
    assert fake.calls == 0 and not out.exists()


@pytest.mark.parametrize('defect', ['missing', 'old'])
def test_editor_archive_contract_checked_even_without_memory(chain, tmp_path, defect):
    gd, dd = chain[:2]
    pd, ed = tmp_path / 'new_pc', tmp_path / 'new_editor'
    raw = keep(compiler.preconditioner_input(diagnosis.load_diagnosis(dd)))
    pc.run_preconditioner(gd, dd, pd, generate=Fake(raw), memory_contract=NEW)
    fake = Fake({'patch': base_editor.actual_diff(None, 'Synthetic candidate.\n'), 'reason': 'Offline fixture.'})
    editor.run_editor(pd, ed, generate=fake)
    meta = read(ed / 'run.json')
    assert meta['memory_contract'] == NEW
    if defect == 'missing': del meta['memory_contract']
    else: meta['memory_contract'] = OLD
    (ed / 'run.json').write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='Editor Memory contract differs'): editor.load_editor(ed)
