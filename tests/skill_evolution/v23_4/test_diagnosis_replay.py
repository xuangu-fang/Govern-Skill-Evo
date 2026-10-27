"""Offline version boundaries and actual-Diff → Memory → next-Plan handoff."""
from copy import deepcopy
import json

import pytest

from src.skill_evolution.v23 import grouping, memory, replay as legacy_replay
from src.skill_evolution.v23.editor import actual_diff
from src.skill_evolution.v23.facts import build_facts
from src.skill_evolution.v23.preconditioner import preconditioner_input
from src.skill_evolution.v23_3 import diagnosis as diagnosis_v23_3
from src.skill_evolution.v23_4 import diagnosis, editor, preconditioner as pc, replay
from tests.skill_evolution.v23.test_grouping import result as groups
from tests.skill_evolution.v23.test_preconditioner import proposal
from tests.skill_evolution.v23.test_replay_memory import records
from .helpers import Fake, keep, read


@pytest.fixture
def chain(tmp_path):
    parents = records()
    gd, dd, pd, ed = [tmp_path / n for n in ('groups', 'diagnosis', 'pc', 'editor')]
    grouping.run_grouping(parents, gd, round_id='offline', generate=Fake(groups(build_facts(parents)['facts'])))
    saved = diagnosis.run_diagnosis(gd, dd, generate=Fake(proposal()))
    payload = preconditioner_input(saved)
    pc.run_preconditioner(gd, dd, pd, generate=Fake(keep(payload)))
    skill = 'Inspect visible relevant containers while preserving target identity.\n'
    editor.run_editor(pd, ed, generate=Fake({'patch': actual_diff(None, skill), 'reason': 'Synthetic interface fixture.'}))
    candidates = records(skill)
    bundle = replay.build_replay(ed, parents, candidates[::-1])
    return gd, dd, pd, ed, parents, candidates, bundle


def test_replay_memory_commit_and_next_preconditioner(chain, tmp_path):
    gd, dd, pd, ed, parents, candidates, bundle = chain
    # This fixture's records only show look actions: do not claim actual inspection.
    value = {'entries': [{'revises': [], 'knowledge':
        'Inspection guidance was added, but both synthetic traces only used look. '
        'These observations do not establish that the intended inspection was performed or improved behavior.',
        'evidence': ['diff', 'P1:1', 'Q1:1']}]}
    fake = Fake(value)
    rd = tmp_path / 'replay'
    saved = replay.run_replay(bundle, rd, generate=fake)
    assert read(rd / 'run.json')['prompt_version'] == replay.PROMPT_VERSION
    assert replay.load_replay(rd) == saved
    assert replay.run_replay(bundle, rd, generate=fake) == saved and fake.calls == 1
    assert bundle == legacy_replay.build_replay_from_editor(editor.load_editor(ed), ed, parents, candidates)
    assert set(json.loads(fake.messages[1]['content'])) == {'parent', 'diff', 'plan', 'command_sets', 'runs', 'pairs', 'memory'}
    assert 'raw_preconditioner' not in json.loads(fake.messages[1]['content'])
    root = tmp_path / 'memory'
    memory.commit_memory(root, context_id='synthetic_R1', context=bundle, result=saved['replay'])
    active = memory.load_memory(root)
    assert active['entries'][0]['evidence'] == ['synthetic_R1/diff', 'synthetic_R1/P1:1', 'synthetic_R1/Q1:1']
    output = keep(preconditioner_input(diagnosis.load_diagnosis(dd)))
    output['adjustments'][0]['reason'] = 'The non-adherence observation in `M1` and `synthetic_R1/Q1:1` does not establish that the proposal is harmful; retain it pending validation.'
    next_saved = pc.run_preconditioner(gd, dd, tmp_path / 'next_pc', generate=Fake(output), memory=active)
    visible = pc.model_input(next_saved)['memory']
    assert visible['entries'] == active['entries']
    assert visible['sources']['synthetic_R1/diff']['diff'] == bundle['payload']['diff']
    # Revising knowledge preserves the historical evidence needed for retained claims.
    revised_bundle = deepcopy(bundle)
    revised_bundle['payload']['memory'] = active
    revised = {'entries': [{'revises': ['M1'], 'knowledge':
        'The earlier inspection guidance was not followed in the cited look-only traces. '
        'The additional supplied traces likewise do not establish an inspection response; causation remains unresolved.',
        'evidence': [*active['entries'][0]['evidence'], 'diff', 'P2:1', 'Q2:1']}]}
    memory.commit_memory(root, context_id='synthetic_R2', context=revised_bundle, result=revised)
    updated = memory.load_memory(root)
    assert [e['id'] for e in updated['entries']] == ['M2']
    assert set(updated['sources']) >= {'synthetic_R1/diff', 'synthetic_R1/P1', 'synthetic_R1/Q1',
                                      'synthetic_R2/diff', 'synthetic_R2/P2', 'synthetic_R2/Q2'}


@pytest.mark.parametrize('version', ['v23_3', 'v23_4'])
def test_explicit_diagnosis_version_and_step3_archive(upstream, payload, tmp_path, version):
    gd, dd, saved, pd = upstream
    if version == 'v23_3':
        dd = tmp_path / 'old_diagnosis'
        diagnosis_v23_3.run_diagnosis(gd, dd, generate=Fake(saved['diagnosis']))
        with pytest.raises(ValueError): diagnosis.load_diagnosis(dd)
    else:
        with pytest.raises(ValueError): diagnosis_v23_3.load_diagnosis(dd)
    result = pc.run_preconditioner(gd, dd, pd, generate=Fake(keep(payload)), diagnosis_version=version)
    assert read(pd / 'run.json')['diagnosis_version'] == version
    if version == 'v23_3':
        meta = read(pd / 'run.json')
        del meta['diagnosis_version']  # Exact third-step metadata convention.
        (pd / 'run.json').write_text(json.dumps(meta))
        assert pc.load_preconditioner(pd) == result
        with pytest.raises(ValueError): pc.run_preconditioner(gd, dd, pd, generate=Fake(keep(payload)))
        # Equal parsed Plans do not make different Diagnosis prompt versions identical.
        with pytest.raises(ValueError, match='Diagnosis version differs'):
            pc.run_preconditioner(gd, upstream[1], pd, generate=Fake(keep(payload)))
    else:
        meta = read(dd / 'run.json'); meta['prompt_version'] = 'unknown'
        (dd / 'run.json').write_text(json.dumps(meta))
        with pytest.raises(ValueError): pc.load_preconditioner(pd)


def test_diagnosis_boundary_evidence_selects_preservation_run(upstream):
    saved = deepcopy(upstream[2])
    value = saved['diagnosis']['plan']
    value['updates'] = [{'id': 'u1', 'text': 'Inspect relevant containers; retain exact target information.\n',
                         'basis': ['G1', 'P1:1']}]
    value['checks'] = []
    assert [r['ref'] for r in preconditioner_input(saved)['runs']] == ['P1']
    value['updates'][0]['basis'].append('P2:1')
    assert [r['ref'] for r in preconditioner_input(saved)['runs']] == ['P1', 'P2']
    messages = diagnosis.messages_for(saved)
    assert 'memory' not in json.loads(messages[1]['content'])


@pytest.mark.parametrize('decision', ['no_change', 'need_evidence'])
def test_diagnosis_semantic_stops_do_not_invent_originals(upstream, tmp_path, decision):
    gd = upstream[0]
    dd = tmp_path / 'stop'
    result = {'decision': decision, 'reason': 'Synthetic upstream stop.', 'plan': None}
    diagnosis.run_diagnosis(gd, dd, generate=Fake(result))
    pc_path = tmp_path / 'stopped_pc'
    fake = Fake({})
    with pytest.raises(ValueError): pc.run_preconditioner(gd, dd, pc_path, generate=fake)
    assert fake.calls == 0 and not pc_path.exists()


@pytest.mark.parametrize('stage', ['diagnosis', 'replay'])
@pytest.mark.parametrize('kind', ['truncated', 'schema', 'exception', 'reference'])
def test_failures_never_become_success_or_retry(chain, tmp_path, stage, kind):
    gd, _, _, _, _, _, bundle = chain
    module = diagnosis if stage == 'diagnosis' else replay
    value = proposal() if stage == 'diagnosis' else {'entries': []}
    if kind == 'schema': value['extra'] = True
    if kind == 'reference':
        if stage == 'diagnosis': value['plan']['updates'][0]['basis'] = ['P99:1']
        else: value['entries'] = [{'revises': [], 'knowledge': 'Unknown evidence.', 'evidence': ['diff', 'Q99:1']}]
    fake = Fake(value, finish='length' if kind == 'truncated' else 'stop')
    if kind == 'exception':
        def fake(*args): raise RuntimeError('Synthetic failure')
    path = tmp_path / 'failed'
    invoke = lambda gen: (module.run_diagnosis(gd, path, generate=gen) if stage == 'diagnosis'
                          else module.run_replay(bundle, path, generate=gen))
    with pytest.raises((ValueError, RuntimeError)): invoke(fake)
    assert read(path / 'run.json')['status'] == 'invalid'
    assert not (path / f'{stage}.json').exists()
    retry = Fake(proposal() if stage == 'diagnosis' else {'entries': []})
    with pytest.raises(ValueError): invoke(retry)
    assert retry.calls == 0


@pytest.mark.parametrize('kind', ['prompt', 'version', 'raw', 'upstream', 'candidate', 'plan', 'config'])
def test_replay_rechecks_archive_and_lineage(chain, tmp_path, kind):
    _, _, _, ed, _, _, bundle = chain
    rd = tmp_path / 'replay'
    replay.run_replay(bundle, rd, generate=Fake({'entries': []}))
    if kind == 'prompt': (rd / 'prompt.md').write_text('changed')
    elif kind == 'raw': (rd / 'raw_output.txt').write_text('{}')
    elif kind == 'version':
        meta = read(rd / 'run.json'); meta['prompt_version'] = 'other'
        (rd / 'run.json').write_text(json.dumps(meta))
    elif kind == 'upstream': (ed / 'actual.diff').write_text('tampered')
    elif kind in ('candidate', 'plan'):
        value = read(rd / 'input.json')
        if kind == 'candidate': value['candidate'] += 'changed'
        else: value['payload']['plan']['updates'][0]['text'] = 'changed'
        (rd / 'input.json').write_text(json.dumps(value))
    if kind == 'config':
        with pytest.raises(ValueError): replay.load_replay(rd, expected_call_config={})
    else:
        with pytest.raises(ValueError): replay.load_replay(rd)
