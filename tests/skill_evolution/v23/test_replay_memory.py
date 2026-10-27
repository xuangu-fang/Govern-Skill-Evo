"""Paired facts, immutable Memory transitions and one-shot calls; no network."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from src.adapters.alfworld.skill_runtime import digest, load_skill
from src.skill_evolution.v23 import replay, memory, editor, preconditioner as pc
from src.skill_evolution.v23.facts import build_facts
from tests.skill_evolution.v23.test_grouping import record
from tests.skill_evolution.v23.test_preconditioner import answer, keep, proposal
from tests.skill_evolution.v23.test_diagnosis import make_grouping
from src.skill_evolution.v23 import diagnosis


def records(skill=None):
    result = []
    for n in (1, 2):
        r = record(n, parent=skill)
        r.update(split='train', model='offline', backend_id='test', versions={'environment': '1'},
                 environment={'game_sha256': str(n), 'manifest_sha256': 'manifest'},
                 implementation={'files': {'runner': 'same'}})
        r['skill'] = load_skill() if skill is None else {'mode': 'fixed', 'text': skill,
            'skill_id': 'sha256:' + digest(skill.encode()), 'sha256': digest(skill.encode()), 'source': 'offline'}
        if skill is not None: r['run_id'] = 'candidate-' + r['run_id']
        result.append(r)
    return result


@pytest.fixture
def case(monkeypatch):
    parent, candidate = records(), records('Inspect the visible cabinet.\n')
    frozen = build_facts(parent)
    saved = {**frozen, 'effective_plan': proposal()['plan'], 'editor_status': 'candidate',
             'candidate_text': candidate[0]['skill']['text'], 'actual_diff': editor.actual_diff(None, candidate[0]['skill']['text'])}
    monkeypatch.setattr(replay, 'load_editor', lambda _: deepcopy(saved))
    bundle = replay.build_replay('offline', parent, candidate)
    return parent, candidate, saved, bundle


def entry(revises=(), evidence=('diff', 'P1:1', 'Q1:2')):
    return {'revises': list(revises), 'knowledge': 'Synthetic conditional response; not real learned Memory.', 'evidence': list(evidence)}


def output(*entries): return {'entries': list(entries)}


def commit(root, bundle, result, cid='test_R1'):
    return memory.commit_memory(root, context_id=cid, context=bundle, result=result)


def test_pairing_full_facts_and_order_independence(case):
    p, q, saved, b = case
    assert len(b['payload']) == 7
    assert b['payload']['runs'][:2] == saved['facts']['runs']
    reversed_q = replay.build_replay('offline', p, q[::-1])
    assert b['payload'] == reversed_q['payload']
    assert [r['ref'] for r in b['payload']['runs']] == ['P1', 'P2', 'Q1', 'Q2']
    assert b['payload']['runs'][0]['steps'][0]['before'] == b['payload']['runs'][2]['steps'][0]['before']
    assert b['payload']['runs'][0]['steps'][0]['step'] != b['payload']['runs'][2]['steps'][0]['step']
    assert b['payload']['command_sets'] == saved['facts']['command_sets']
    assert 'basis' not in b['payload']['plan']['updates'][0]
    assert b['pair_audit'][0]['candidate']['events'][0]['step'] == 'Q1:1'


@pytest.mark.parametrize('key', ['task', 'split', 'model', 'backend_id', 'protocol', 'versions', 'environment', 'initial_observation', 'implementation', 'skill', 'run_id'])
def test_bad_pair_rejected(case, key):
    p, q, saved, _ = case
    q = deepcopy(q)
    if key == 'task': q[0][key]['id'] = 'missing'
    elif key == 'protocol': q[0][key]['environment_seed'] = 99
    elif key == 'environment': q[0][key]['game_sha256'] = 'other'
    elif key == 'versions': q[0][key]['environment'] = '2'
    elif key == 'implementation': q[0][key]['files']['runner'] = 'other'
    elif key == 'skill': q[0][key]['sha256'] = 'invalid'
    elif key == 'run_id': q[0][key] = p[0]['run_id']
    else: q[0][key] = 'other'
    with pytest.raises(ValueError): replay.build_replay('offline', p, q)


def test_explicit_implementation_review(case):
    p, q, _, _ = case
    q = deepcopy(q)
    for r in q: r['implementation']['files'] = {'runner': 'new'}
    review = {'parent_files': p[0]['implementation']['files'], 'candidate_files': q[0]['implementation']['files'],
              'reason': 'Offline reviewed bookkeeping-only difference.', 'diff': 'Recorded source diff'}
    assert replay.build_replay('offline', p, q, implementation_review=review)['pair_audit'][0]['verified']
    review['candidate_files'] = {'runner': 'unrelated'}
    with pytest.raises(ValueError): replay.build_replay('offline', p, q, implementation_review=review)


def test_interruption_keeps_only_real_events(case):
    p, q, _, _ = case
    q = deepcopy(q)
    q[0]['status'] = 'error'; q[0]['won'] = False
    q[0]['steps'][-1]['phase'] = 'requesting'; q[0]['error_stage'] = 'model_request'
    b = replay.build_replay('offline', p, q)
    r = b['payload']['runs'][2]
    assert len(r['steps']) == 1 and r['outcome']['success'] is None
    assert r['outcome']['end_reason'] == 'error'
    assert b['pair_audit'][0]['candidate']['pending_step']['step'] == 'Q1:2'


def test_add_revision_merge_and_sources(case, tmp_path):
    b = case[3]
    first = commit(tmp_path, b, output(entry(), entry(evidence=('diff', 'P2:1', 'Q2:1'))))
    assert first['after_active_ids'] == ['M1', 'M2']
    archive = (tmp_path/'archive/test_R1.json').read_bytes()
    view = memory.load_memory(tmp_path)
    assert len(view['sources']) == 5 and len(view['sources']['test_R1/P1']['run']['steps']) == 2
    b2 = deepcopy(b); b2['payload']['memory'] = view
    newer = entry(['M1'], ['test_R1/diff', 'test_R1/P1:1', 'diff', 'Q1:1'])
    second = commit(tmp_path, b2, output(newer), 'test_R2')
    assert second['after_active_ids'] == ['M2', 'M3']
    assert 'test_R1/Q1:2' not in second['entries'][0]['evidence'] # no automatic inheritance
    assert (tmp_path/'archive/test_R1.json').read_bytes() == archive
    b3 = deepcopy(b); b3['payload']['memory'] = memory.load_memory(tmp_path)
    merged = commit(tmp_path, b3, output(entry(['M2', 'M3'])), 'test_R3')
    assert merged['after_active_ids'] == ['M4']
    assert set(memory.load_memory(tmp_path)['sources']) == {'test_R3/diff', 'test_R3/P1', 'test_R3/Q1'}
    assert len(list((tmp_path/'archive').glob('*.json'))) == 3


def test_empty_and_exact_idempotence(case, tmp_path):
    b = case[3]; r = output(entry())
    first = commit(tmp_path, b, r)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob('*.json')}
    assert commit(tmp_path, b, r) == first
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob('*.json')}
    b2 = deepcopy(b); b2['payload']['memory'] = memory.load_memory(tmp_path)
    commit(tmp_path, b2, output(), 'test_R2')
    assert memory.load_memory(tmp_path)['entries'][0]['id'] == 'M1'
    with pytest.raises(ValueError): commit(tmp_path, b, output(entry(), entry()))
    with pytest.raises(ValueError): commit(tmp_path, b, output(entry()), 'test_R3') # stale snapshot


@pytest.mark.parametrize('kind', ['extra', 'type', 'empty_text', 'missing_ref', 'group_ref', 'memory_ref', 'check_ref',
                                  'plan_ref', 'empty_evidence', 'no_edit', 'no_run', 'unknown_revision',
                                  'duplicate_revision', 'chain', 'duplicate_evidence', 'wrong_namespace'])
def test_invalid_proposals(case, kind):
    b = case[3]; v = output(entry()); e = v['entries'][0]
    if kind == 'extra': e['updates'] = []
    elif kind == 'type': v['entries'] = {}
    elif kind == 'empty_text': e['knowledge'] = ' '
    elif kind == 'missing_ref': e['evidence'] = ['diff', 'P1:999']
    elif kind == 'group_ref': e['evidence'] = ['diff', 'G1']
    elif kind == 'memory_ref': e['evidence'] = ['diff', 'M1']
    elif kind == 'check_ref': e['evidence'] = ['diff', 'c1']
    elif kind == 'plan_ref': e['evidence'] = ['diff', 'u1']
    elif kind == 'empty_evidence': e['evidence'] = []
    elif kind == 'no_edit': e['evidence'] = ['P1:1']
    elif kind == 'no_run': e['evidence'] = ['diff']
    elif kind == 'unknown_revision': e['revises'] = ['M1']
    elif kind == 'duplicate_revision': e['revises'] = ['M1', 'M1']
    elif kind == 'chain': v['entries'].append(entry(['M1']))
    elif kind == 'duplicate_evidence': e['evidence'] *= 2
    else: e['evidence'] = ['diff', 'other_R1/P1:1']
    with pytest.raises(ValueError): memory.validate_entries(v, b['payload'])


def test_repeated_active_target_and_atomic_rejection(case, tmp_path):
    b = case[3]; commit(tmp_path, b, output(entry()))
    b = deepcopy(b); b['payload']['memory'] = memory.load_memory(tmp_path)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob('*.json')}
    with pytest.raises(ValueError): commit(tmp_path, b, output(entry(['M1']), entry(['M1'])), 'test_R2')
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob('*.json')}


def test_crash_before_active_switch_recovers_once(case, tmp_path, monkeypatch):
    b = case[3]; original = memory.write_record
    def fail(path, value):
        if path.name == 'active.json': raise KeyboardInterrupt()
        original(path, value)
    monkeypatch.setattr(memory, 'write_record', fail)
    with pytest.raises(KeyboardInterrupt): commit(tmp_path, b, output(entry()))
    assert memory.load_memory(tmp_path) == memory.empty_memory()
    assert (tmp_path/'archive/test_R1.json').exists()
    monkeypatch.setattr(memory, 'write_record', original)
    with pytest.raises(ValueError): commit(tmp_path, b, output(entry()), 'other')
    assert commit(tmp_path, b, output(entry()))['after_active_ids'] == ['M1']
    assert commit(tmp_path, b, output(entry()))['after_active_ids'] == ['M1']


@pytest.mark.parametrize('kind', ['missing_source', 'missing_step', 'missing_menu', 'duplicate_id', 'missing_context'])
def test_missing_historical_facts_rejected(case, tmp_path, kind):
    commit(tmp_path, case[3], output(entry()))
    v = memory.load_memory(tmp_path)
    if kind == 'missing_source': del v['sources']['test_R1/P1']
    elif kind == 'missing_step': v['entries'][0]['evidence'].append('test_R1/P1:99')
    elif kind == 'missing_menu': v['sources']['test_R1/P1']['command_sets'] = {}
    elif kind == 'duplicate_id': v['entries'] *= 2
    else: del v['sources']['test_R1/diff']
    with pytest.raises(ValueError): memory.validate_memory(v)


def test_persistence_reuse_and_changed_inputs(case, tmp_path):
    b = case[3]; calls = []
    def gen(*_): calls.append(1); return answer(output(entry()))
    first = replay.run_replay(b, tmp_path/'call', generate=gen, call_config={'model':'offline'})
    assert first == replay.run_replay(b, tmp_path/'call', generate=gen, call_config={'model':'offline'})
    assert len(calls) == 1
    with pytest.raises(ValueError): replay.run_replay(b, tmp_path/'call', generate=gen, call_config={'model':'other'})
    b2 = deepcopy(b); b2['candidate'] += 'changed'
    with pytest.raises(ValueError): replay.run_replay(b2, tmp_path/'call', generate=gen, call_config={'model':'offline'})


@pytest.mark.parametrize('kind', ['json', 'length', 'contract', 'network', 'interrupt', 'budget'])
def test_failed_call_not_retried(case, tmp_path, kind):
    calls = []; response = answer(output(entry()))
    if kind == 'json': response['content'] = '{broken'
    if kind == 'length': response['finish_reason'] = 'length'
    if kind == 'contract': response = answer({'entries': [], 'summary': 'no'})
    def gen(*_):
        calls.append(1)
        if kind == 'network': raise ConnectionError()
        if kind == 'interrupt': raise KeyboardInterrupt()
        return response
    with pytest.raises((ValueError, ConnectionError, KeyboardInterrupt)):
        replay.run_replay(case[3], tmp_path/'call', generate=gen, max_input_chars=1 if kind == 'budget' else 400000)
    assert json.loads((tmp_path/'call/validation.json').read_text())['valid'] is False
    if kind not in ('network', 'interrupt', 'budget'):
        assert (tmp_path/'call/raw_output.txt').read_text() == response['content']
    with pytest.raises((ValueError, FileNotFoundError)):
        replay.run_replay(case[3], tmp_path/'call', generate=gen)
    assert len(calls) == (0 if kind == 'budget' else 1)


def test_nonempty_memory_preconditioner_handoff(case, tmp_path):
    commit(tmp_path/'memory', case[3], output(entry()))
    view = memory.load_memory(tmp_path/'memory')
    group = make_grouping(tmp_path)
    diagnosis.run_diagnosis(group, tmp_path/'diag', generate=lambda *_: answer(proposal()))
    value = {**keep(), 'adjustments': [{'from':['u1'], 'to':[{'id':'u1','text':'Inspect visible conditions.'}],
                                      'basis':['M1'], 'reason':'M1 records a conditional response.'}]}
    calls = []
    def gen(*_): calls.append(1); return answer(value)
    saved = pc.run_preconditioner(group, tmp_path/'diag', tmp_path/'pc', generate=gen, memory=view)
    assert saved['memory'] == view
    assert saved['effective_plan']['updates'][0]['basis'] == proposal()['plan']['updates'][0]['basis']
    assert pc.run_preconditioner(group, tmp_path/'diag', tmp_path/'pc', generate=gen, memory=view) == saved
    assert len(calls) == 1
    with pytest.raises(ValueError): pc.run_preconditioner(group, tmp_path/'diag', tmp_path/'pc', generate=gen)
    p = pc.preconditioner_input(saved); value['adjustments'][0]['basis'] = ['M99']
    with pytest.raises(ValueError): pc.compile_effective_plan(value, p)


def test_frozen_preconditioner_handoff_to_current_editor(tmp_path):
    paths = [Path('artifacts/methods/v23/v23_preconditioner_001/live'),
             Path('artifacts/methods/v23/v23_editor_recovery_001/live')]
    before = {str(p):p.read_bytes() for d in paths for p in d.rglob('*') if p.is_file()}
    saved = pc.load_preconditioner(paths[0])
    # Reuse only the historical response as an offline fixture. A fresh archive
    # must use today's Prompt; this does not re-evaluate the response's semantics.
    response = json.loads((paths[1] / 'editor.json').read_text())
    calls = []
    def generate(messages, directory):
        calls.append(messages)
        assert messages == editor.messages_for(saved)
        return answer(response)
    out = tmp_path / 'current_editor'
    ed = editor.run_editor(paths[0], out, generate=generate)
    assert ed['candidate_text'].count('\n') == 23 and ed['effective_plan'] == saved['effective_plan']
    assert (out / 'prompt.md').read_text() == editor.messages_for(saved)[0]['content']
    assert editor.load_editor(out, expected_preconditioner=saved) == ed
    assert editor.run_editor(paths[0], out, generate=generate) == ed
    assert len(calls) == 1
    assert before == {str(p):p.read_bytes() for d in paths for p in d.rglob('*') if p.is_file()}


def test_actual_replay_sources_and_readonly_reuse():
    root = Path('artifacts/methods/v23/v23_replay_memory_001')
    if not (root/'replay/replay.json').exists(): pytest.skip('Real Replay not available')
    before = {str(p):p.read_bytes() for p in (root/'memory').rglob('*.json')}
    saved = replay.load_replay(root/'replay')
    view = memory.load_memory(root/'memory')
    assert len(view['entries']) == len(saved['replay']['entries'])
    assert len(saved['payload']['runs']) == 8
    for key, source in view['sources'].items():
        if key.endswith('/diff'):
            assert source['parent'] == saved['payload']['parent'] and source['diff'] == saved['payload']['diff']
        else:
            run = next(r for r in saved['payload']['runs'] if r['ref'] == source['run']['ref'])
            assert source['run'] == run
            assert source['command_sets'] == memory.run_menus(run, saved['payload']['command_sets'])
    assert before == {str(p):p.read_bytes() for p in (root/'memory').rglob('*.json')}


def test_actual_memory_control_changes_only_memory():
    root = Path('artifacts/methods/v23/v23_preconditioner_with_memory_001')
    if not (root/'real/preconditioner.json').exists(): pytest.skip('Real comparison not available')
    a,b = [pc.load_preconditioner(root/name) for name in ('empty','real')]
    am,bm = [json.loads((root/name/'messages.json').read_text()) for name in ('empty','real')]
    assert am[0] == bm[0]
    ap,bp = json.loads(am[1]['content']),json.loads(bm[1]['content'])
    assert ap.pop('memory') == memory.empty_memory()
    assert bp.pop('memory') == memory.load_memory('artifacts/methods/v23/v23_replay_memory_001/memory')
    assert ap == bp
    for saved in (a,b):
        assert pc.compile_effective_plan(saved['preconditioner'],pc.preconditioner_input(saved)) == saved['effective_plan']
    assert json.loads((root/'empty/run.json').read_text())['call_config'] == json.loads((root/'real/run.json').read_text())['call_config']
