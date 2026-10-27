"""Offline evidence conservation, provenance and archive boundaries; no network."""
from copy import deepcopy
import hashlib
import json

import pytest

from src.skill_evolution.v23 import memory, replay as legacy
from src.skill_evolution.v23_3.memory_view import compact_memory, project_messages
from src.skill_evolution.v23_4 import replay
from tests.skill_evolution.v23.test_replay_memory import case, commit, entry, output
from .test_diagnosis_replay import chain
from .helpers import Fake, read


def history(tmp_path, bundle, refs=('diff', 'P1:1', 'Q1:2')):
    root = tmp_path / 'memory'
    commit(root, bundle, output(entry(evidence=refs)))
    full = memory.load_memory(root)
    current = deepcopy(bundle); current['payload']['memory'] = full
    return root, current, replay.history_pair_sources(root, full)


def test_pairs_drive_order_without_changing_facts(case):
    b = deepcopy(case[3]); original = deepcopy(b)
    # Identical task descriptions must not substitute for immutable task identity.
    b['payload']['runs'].reverse()
    b['pair_audit'].reverse()
    view = replay.model_input(b)
    assert [r['ref'] for r in view['runs']] == ['P1', 'Q1', 'P2', 'Q2']
    assert {r['ref']: r for r in view['runs']} == {r['ref']: r for r in original['payload']['runs']}
    for key in ('parent', 'diff', 'plan', 'command_sets'):
        assert view[key] == original['payload'][key]
    assert [p['task_id'] for p in view['pairs']] == ['train:0001', 'train:0002']
    assert view['pairs'][0]['parent_result'] == {'status': 'success', 'success': True, 'steps': 2}
    assert b['payload']['runs'] == original['payload']['runs'][::-1]
    assert set(view) == set(original['payload'])


@pytest.mark.parametrize('defect', ['coverage', 'identity', 'verified', 'duplicate', 'swapped_pairs'])
def test_current_pair_metadata_cannot_be_guessed(case, defect):
    b = deepcopy(case[3])
    if defect == 'coverage': b['pair_audit'].pop()
    elif defect == 'identity': b['pair_audit'][0]['candidate']['task_id'] = 'different'
    elif defect == 'verified': b['pair_audit'][0]['verified'] = False
    elif defect == 'duplicate': b['pair_audit'][1] = deepcopy(b['pair_audit'][0])
    else:
        b['payload']['pairs'][0]['candidate'] = 'Q2'
        b['payload']['pairs'][1]['candidate'] = 'Q1'
    with pytest.raises(ValueError): replay.model_input(b)


def test_invalid_action_counts_but_pending_request_and_http_retries_do_not(case):
    p, q, _, _ = case
    q = deepcopy(q)
    q[0]['status'] = 'step_limit'; q[0]['won'] = False
    q[0]['steps'][-1].update(action='', action_in_admissible_commands=False,
                             observation='Nothing happens.', won=False, done=False)
    q[0]['steps'][-1]['transport_attempts'] = [{'attempt': i} for i in (1, 2, 3)]
    q[1]['status'] = 'error'; q[1]['won'] = False
    q[1]['steps'][-1]['phase'] = 'requesting'
    b = legacy.build_replay('offline', p, q)
    view = replay.model_input(b)
    assert view['pairs'][0]['candidate_result'] == {'status': 'step_limit', 'success': False, 'steps': 2}
    assert view['pairs'][1]['candidate_result'] == {'status': 'error', 'success': None, 'steps': 1}
    assert view['runs'][1]['steps'][-1]['action'] == ''


def test_existing_v3_projection_and_history_pair_index(case, tmp_path):
    root, b, sources = history(tmp_path, case[3])
    before = deepcopy(b)
    view = replay.model_input(b, history_sources=sources)
    projected = deepcopy(view['memory'])
    assert projected.pop('pairs') == [{'context': 'test_R1', 'parent': 'test_R1/P1', 'candidate': 'test_R1/Q1'}]
    assert projected.pop('unpaired_runs') == []
    assert projected == compact_memory(b['payload']['memory'])
    assert b == before and memory.load_memory(root) == b['payload']['memory']
    messages = replay.messages_for(b, history_sources=sources)
    assert json.loads(messages[1]['content']) == view
    assert 'Historical Memory evidence view v3' in messages[0]['content']
    assert 'Replay paired-input view v1' in messages[0]['content']
    assert 'sha256' not in view['memory'] and 'path' not in view['memory']


def test_single_side_and_unavailable_provenance_never_invent_counterpart(case, tmp_path):
    _, b, sources = history(tmp_path, case[3], refs=('diff', 'P1:1'))
    view = replay.model_input(b, history_sources=sources)
    assert view['memory']['pairs'] == []
    assert view['memory']['unpaired_runs'] == ['test_R1/P1']
    assert 'test_R1/Q1' not in view['memory']['sources']
    unknown = replay.model_input(b, history_sources={'test_R1': None})
    assert unknown == view
    with pytest.raises(ValueError, match='explicit pairing provenance'): replay.model_input(b)


def test_missing_provenance_does_not_erase_visible_pair_uncertainty(case, tmp_path):
    _, b, _ = history(tmp_path, case[3])
    view = replay.model_input(b, history_sources={'test_R1': None})
    assert view['memory']['pairs'] == []
    assert view['memory']['unpaired_runs'] == ['test_R1/P1', 'test_R1/Q1']


@pytest.mark.parametrize('defect', ['hash', 'edit', 'run', 'menu', 'context', 'pairs'])
def test_historical_provenance_must_match_supplied_facts(case, tmp_path, defect):
    root, b, sources = history(tmp_path, case[3])
    path = root / 'archive/test_R1.json'
    if defect == 'hash': path.write_text(path.read_text() + ' ')
    elif defect == 'edit': b['payload']['memory']['sources']['test_R1/diff']['parent'] = 'different'
    elif defect == 'run': b['payload']['memory']['sources']['test_R1/P1']['run']['task'] = 'different'
    elif defect == 'menu':
        menus = b['payload']['memory']['sources']['test_R1/P1']['command_sets']
        next(iter(menus.values())).append('different')
    else:
        a = read(path)
        if defect == 'context': a['context_id'] = 'other'
        else:
            # Same task wording, valid reference coverage, but conflicts with actual pair audit.
            a['context']['payload']['pairs'][0]['candidate'] = 'Q2'
            a['context']['payload']['pairs'][1]['candidate'] = 'Q1'
        path.write_text(json.dumps(a))
        sources['test_R1']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError): replay.model_input(b, history_sources=sources)


def test_snapshot_mismatch_and_context_collisions(case, tmp_path):
    root, b, sources = history(tmp_path, case[3])
    with pytest.raises(ValueError, match='snapshot differs'):
        replay.history_pair_sources(root, memory.empty_memory())
    commit(root, b, output(entry()), cid='test_R2')
    b['payload']['memory'] = memory.load_memory(root)
    view = replay.model_input(b, history_sources=replay.history_pair_sources(root, b['payload']['memory']))
    assert [p['context'] for p in view['memory']['pairs']] == ['test_R1', 'test_R2']
    assert view['memory']['sources']['test_R1/P1']['run']['trace'][0]['step'] == 'test_R1/P1:1'
    assert view['memory']['sources']['test_R2/P1']['run']['trace'][0]['step'] == 'test_R2/P1:1'


def test_new_archive_memory_roundtrip_and_reload_after_active_changes(chain, tmp_path):
    _, _, _, _, _, _, bundle = chain
    root, b, sources = history(tmp_path, bundle)
    rd = tmp_path / 'replay'
    result = output(entry(revises=['M1'], evidence=('test_R1/diff', 'test_R1/P1:1', 'diff', 'Q2:1')))
    fake = Fake(result)
    saved = replay.run_replay(b, rd, generate=fake, history_sources=sources)
    assert read(rd / 'input.json') == b
    assert read(rd / 'history_pair_sources.json') == sources
    assert read(rd / 'run.json')['input_view'] == replay.INPUT_VIEW
    assert read(rd / 'model_input.json')['memory']['format'] == 'memory_evidence_view_v3'
    commit(root, b, result, cid='test_R2')
    loaded = memory.load_memory(root)
    assert [e['id'] for e in loaded['entries']] == ['M2']
    snapshot = {str(p): p.read_bytes() for p in root.rglob('*.json')}
    commit(root, b, result, cid='test_R2')
    assert {str(p): p.read_bytes() for p in root.rglob('*.json')} == snapshot
    # Immutable context hashes suffice; changing Active must not invalidate past runs.
    assert replay.load_replay(rd) == saved
    assert replay.run_replay(b, rd, generate=fake, history_sources=sources) == saved and fake.calls == 1
    projected = project_messages([{'role': 'system', 'content': 'Offline next PC projection'},
        {'role': 'user', 'content': json.dumps({'memory': loaded})}])
    assert json.loads(projected[1]['content'])['memory'] == compact_memory(loaded)


@pytest.mark.parametrize('defect', ['model_input', 'messages', 'view_version', 'sources', 'archive'])
def test_saved_view_and_provenance_tampering_rejected(chain, tmp_path, defect):
    root, b, sources = history(tmp_path, chain[-1])
    rd = tmp_path / 'replay'
    replay.run_replay(b, rd, generate=Fake({'entries': []}), history_sources=sources)
    if defect == 'model_input':
        data = read(rd / 'model_input.json'); data['pairs'][0]['parent_result']['steps'] += 1
        (rd / 'model_input.json').write_text(json.dumps(data))
    elif defect == 'messages': (rd / 'messages.json').write_text('[]')
    elif defect == 'view_version':
        data = read(rd / 'run.json'); data['input_view'] = 'unknown'
        (rd / 'run.json').write_text(json.dumps(data))
    elif defect == 'sources': (rd / 'history_pair_sources.json').write_text('{}')
    else:
        path = root / 'archive/test_R1.json'; path.write_text(path.read_text() + ' ')
    with pytest.raises(ValueError): replay.load_replay(rd)


def test_legacy_archive_stays_readable_and_cannot_be_silently_reused(chain, tmp_path):
    b = chain[-1]; rd = tmp_path / 'legacy'
    saved = replay.run_replay(b, rd, generate=Fake({'entries': []}), input_view=replay.LEGACY_INPUT_VIEW)
    assert read(rd / 'model_input.json') == b['payload']
    # Exactly the pre-view archive convention, with no new metadata or files.
    meta = read(rd / 'run.json'); del meta['input_view']
    (rd / 'run.json').write_text(json.dumps(meta))
    (rd / 'model_input.json').unlink(); (rd / 'history_pair_sources.json').unlink()
    assert replay.load_replay(rd) == saved
    fake = Fake({'entries': []})
    with pytest.raises(ValueError, match='input view differs'): replay.run_replay(b, rd, generate=fake)
    assert fake.calls == 0
    assert replay.run_replay(b, rd, generate=fake, input_view=replay.LEGACY_INPUT_VIEW) == saved
    assert fake.calls == 0


def test_budget_failure_never_truncates_or_calls_generator(chain, tmp_path):
    b = chain[-1]; rd = tmp_path / 'budget'; fake = Fake({'entries': []})
    with pytest.raises(ValueError, match='budget'):
        replay.run_replay(b, rd, generate=fake, max_input_chars=1)
    assert fake.calls == 0 and read(rd / 'run.json')['status'] == 'invalid'
    assert read(rd / 'model_input.json') == replay.model_input(b)
