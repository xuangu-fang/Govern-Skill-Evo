"""Fixed-Test acceptance with synthetic sources and blocked network access."""
from copy import deepcopy
import hashlib
import json

import pytest

from src.adapters.officeqa.data import Dataset
from src.adapters.officeqa.transport import ChatTransport, RequestFailure
from src.adapters.officeqa.retry import GenerationExhausted
from src.skill_evolution.v26 import evaluation as ev, modules
from src.skill_evolution.v26.benchmarks.officeqa.adapter import OfficeQAEvidenceAdapter, SkillAdamEvidenceAdapter
from src.skill_evolution.v26.stages import read
from .conftest import Provider, response


@pytest.fixture
def evaluation(office, monkeypatch):
    root, dataset, runtime, _ = office
    template = dataset.rows['t']
    rows = []
    for uid in ev.TEST_IDS:
        rows.append({**deepcopy(template), 'id': uid, 'uid': uid, 'question': f'Question for {uid}?'})
    (dataset.root / 'test/items.json').write_text(json.dumps(rows))
    manifest = read(dataset.root / 'manifest.json'); manifest['splits']['test'] = list(ev.TEST_IDS)
    (dataset.root / 'manifest.json').write_text(json.dumps(manifest))
    dataset = Dataset(dataset.root)
    skill = root / 'selected.md'; skill.write_text('Use the document evidence.\n')

    def deny(*a, **k): raise AssertionError('Test must not enter any optimization module')
    for name in ('grouping', 'diagnosis', 'preconditioner', 'editor', 'replay', 'verifier', 'repair'):
        monkeypatch.setattr(modules, name + '_call', deny)

    def create(overrides=None):
        scripts = {uid: [response('0')] for uid in ev.TEST_IDS}
        scripts.update(overrides or {})
        provider = Provider(scripts)
        actor = ChatTransport(offline_create=provider, model='offline-fixture', max_completion_tokens=1234)
        adapter = OfficeQAEvidenceAdapter(dataset, runtime, actor)
        return root / 'evaluation', adapter, provider, skill
    return create


def test_full_172_scoring_archive_recovery_and_report_cli(evaluation, monkeypatch, capsys):
    first, second = ev.TEST_IDS[:2]
    root, adapter, provider, skill = evaluation({first: [response('1000')], second: [response('1000 extra')]})
    adapter = SkillAdamEvidenceAdapter(adapter.dataset, adapter.runtime, adapter.transport, workers=20)
    result = ev.run_evaluation(root, adapter=adapter, skill_file=skill)
    assert read(root / 'batch/actor/run.json')['identity']['execution']['workers'] == 20
    assert read(root / 'plan.json')['execution']['workers'] == 20
    assert result['status'] == 'complete' and result['completed'] == 172
    assert result['em'] == 1/172 and result['f1'] == pytest.approx((1+2/3)/172)
    assert len(provider.requests) == 172 and result['optimization_updates'] is False
    assert set(r['task_id'] for r in result['cases']) == set(ev.TEST_IDS)
    assert not (root / 'rounds').exists() and not (root / 'state.json').exists()
    assert (root / 'report.md').exists()
    with pytest.raises(ValueError, match='explicit resume'):
        ev.run_evaluation(root, adapter=adapter, skill_file=skill)
    archive = SkillAdamEvidenceAdapter(adapter.dataset, adapter.runtime, ev.ArchiveTransport(adapter.transport.metadata()), workers=20)
    assert ev.run_evaluation(root, adapter=archive, skill_file=skill, resume=True) == result
    # A crash after the common batch commits, before V26 records/report commit.
    (root / 'records.json').unlink(); (root / 'report.json').unlink()
    partial = ev.report_evaluation(root, adapter=archive)
    assert partial['awaiting_record_recovery'] and partial['em'] is None
    assert ev.run_evaluation(root, adapter=archive, skill_file=skill, resume=True) == result
    assert len(provider.requests) == 172
    from src.skill_evolution.v26.cli import main
    def deny(*a, **k): raise AssertionError('Report cannot create a provider client')
    monkeypatch.setattr(ChatTransport, '__init__', deny)
    main(['report', str(root)])
    assert json.loads(capsys.readouterr().out)['em'] == 1/172


def test_partial_batch_drain_and_resume_only_pending(evaluation, monkeypatch):
    root, adapter, provider, skill = evaluation()
    original = adapter.runtime.run; failed = ev.TEST_IDS[0]
    def interrupted(case, *a, **k):
        if case.case_id == failed: raise RuntimeError('injected pre-request interruption')
        return original(case, *a, **k)
    monkeypatch.setattr(adapter.runtime, 'run', interrupted)
    with pytest.raises(RuntimeError, match='injected'):
        ev.run_evaluation(root, adapter=adapter, skill_file=skill)
    report = read(root / 'report.json')
    assert report['completed'] == 171 and report['pending_ids'] == [failed]
    assert report['em'] is None and report['f1'] is None
    archive = OfficeQAEvidenceAdapter(adapter.dataset, adapter.runtime, ev.ArchiveTransport(adapter.transport.metadata()))
    with pytest.raises(ValueError, match='Pending Test'):
        ev.run_evaluation(root, adapter=archive, skill_file=skill, resume=True)
    assert len(provider.requests) == 171
    monkeypatch.setattr(adapter.runtime, 'run', original)
    # An interrupted append is ignored by reports, then repaired by the common scheduler.
    journal = root / 'batch/actor/results.jsonl'
    with journal.open('ab') as handle: handle.write(b'{"id":')
    before = journal.read_bytes()
    assert ev.report_evaluation(root, adapter=archive)['completed'] == 171
    assert journal.read_bytes() == before
    result = ev.run_evaluation(root, adapter=adapter, skill_file=skill, resume=True)
    assert result['completed'] == 172 and len(provider.requests) == 172
    assert result['cases'][-1]['task_id'] == failed


def test_six_attempt_exhaustion_is_not_reset_by_test_resume(evaluation):
    uid = ev.TEST_IDS[0]
    root, adapter, provider, skill = evaluation({uid: [RequestFailure('injected')] * 6})
    with pytest.raises(GenerationExhausted):
        ev.run_evaluation(root, adapter=adapter, skill_file=skill)
    count = len(provider.requests)
    assert count == 171 + 6
    with pytest.raises(GenerationExhausted):
        ev.run_evaluation(root, adapter=adapter, skill_file=skill, resume=True)
    assert len(provider.requests) == count
    state = read(root / 'batch/actor/cases' / hashlib.sha256(uid.encode()).hexdigest() / 'actor_state.json')
    assert len(state['rounds'][0]['attempts']) == 6
    assert read(root / 'report.json')['status'] == 'incomplete'


def test_plan_preparation_crash_resume(evaluation, monkeypatch):
    root, adapter, provider, skill = evaluation()
    original = ev.freeze_text
    def interrupted(*a, **k): raise KeyboardInterrupt()
    monkeypatch.setattr(ev, 'freeze_text', interrupted)
    with pytest.raises(KeyboardInterrupt): ev.run_evaluation(root, adapter=adapter, skill_file=skill)
    assert (root / 'plan.json').exists() and not provider.requests
    monkeypatch.setattr(ev, 'freeze_text', original)
    assert ev.run_evaluation(root, adapter=adapter, skill_file=skill, resume=True)['completed'] == 172


@pytest.mark.parametrize('change', ['skill', 'actor', 'gold', 'document', 'implementation'])
def test_frozen_identity_rejects_drift_before_actor(evaluation, monkeypatch, change):
    root, adapter, provider, skill = evaluation()
    original = ev.freeze_text
    monkeypatch.setattr(ev, 'freeze_text', lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt): ev.run_evaluation(root, adapter=adapter, skill_file=skill)
    monkeypatch.setattr(ev, 'freeze_text', original)
    if change == 'skill': skill.write_text('Different Skill')
    elif change == 'actor': adapter.transport.context = type(adapter.transport.context)(
        'officeqa', 'baseline', 'changed-model', 'none', 1, 42)
    elif change == 'gold':
        path = adapter.dataset.root / 'test/items.json'; rows = read(path)
        rows[0]['answers'] = ['changed']; path.write_text(json.dumps(rows))
    elif change == 'document':
        next(adapter.runtime.text_root.glob('*.txt')).write_text('changed source')
    else: monkeypatch.setattr(ev, '_contract', lambda _: {'changed': 'source'})
    with pytest.raises(ValueError): ev.run_evaluation(root, adapter=adapter, skill_file=skill, resume=True)
    assert not provider.requests


@pytest.mark.parametrize('change', ['subset', 'train_id', 'order', 'gate'])
def test_no_subsets_wrong_splits_or_gate(evaluation, change):
    root, adapter, provider, skill = evaluation()
    if change == 'subset': adapter.dataset.splits['test'].pop()
    elif change == 'train_id': adapter.dataset.splits['test'][0] = 'a'
    elif change == 'order': adapter.dataset.splits['test'].reverse()
    else: adapter.gate_metric = 'officeqa_em_exact_v1'
    with pytest.raises(ValueError): ev.run_evaluation(root, adapter=adapter, skill_file=skill)
    assert not provider.requests and not root.exists()


def test_report_rejects_score_corruption(evaluation):
    root, adapter, _, skill = evaluation()
    ev.run_evaluation(root, adapter=adapter, skill_file=skill)
    rows = read(root / 'records.json'); rows[0]['execution']['metrics']['em'] = 1
    (root / 'records.json').write_text(json.dumps(rows))
    with pytest.raises(ValueError, match='journal'):
        ev.report_evaluation(root, adapter=adapter)


def test_no_skill_arm_and_campaign_path_protection(evaluation):
    root, adapter, provider, _ = evaluation()
    campaign = root.parent / 'campaign'; campaign.mkdir()
    (campaign / 'state.json').write_text('{}'); (campaign / 'config.json').write_text('{}')
    with pytest.raises(ValueError, match='Campaign'):
        ev.run_evaluation(campaign / 'test', adapter=adapter, skill_file=None)
    assert not provider.requests
    result = ev.run_evaluation(root, adapter=adapter, skill_file=None)
    assert result['completed'] == 172 and not (root / 'skill.md').exists()


def test_real_prepared_inventory_matches_both_upstreams():
    from pathlib import Path
    root = Path(__file__).resolve().parents[3]
    adam = read(root / 'external/SkillAdam/skilladam/data/profiles/officeqa_main_results.json')
    opt = read(root / 'external/SkillOpt/data/officeqa_id_split/test/items.json')
    release = read(root / 'data/officeqa/releases/763a8366abf2a3605c381d53586d844dc60fa756/dataset_config.json')
    data = Dataset(release['prepared_root'])
    assert list(ev.TEST_IDS) == adam['splits']['test'] == [r['id'] for r in opt] == data.splits['test']
    assert not set(ev.TEST_IDS) & (set(data.splits['train']) | set(data.splits['validation']))


def test_interrupted_request_consumes_slot_on_resume(evaluation):
    uid = ev.TEST_IDS[0]
    root, adapter, provider, skill = evaluation({uid: [KeyboardInterrupt(), response('1000')]})
    with pytest.raises(KeyboardInterrupt):
        ev.run_evaluation(root, adapter=adapter, skill_file=skill)
    result = ev.run_evaluation(root, adapter=adapter, skill_file=skill, resume=True)
    assert result['completed'] == 172 and len(provider.requests) == 173
    state = read(root / 'batch/actor/cases' / hashlib.sha256(uid.encode()).hexdigest() / 'actor_state.json')
    assert [a['status'] for a in state['rounds'][0]['attempts']] == ['interrupted', 'accepted']
    assert result['actor_requests'] == 173


def test_report_write_crash_recovers_without_actor(evaluation, monkeypatch):
    root, adapter, provider, skill = evaluation()
    original = ev._write_report
    monkeypatch.setattr(ev, '_write_report', lambda *a: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt): ev.run_evaluation(root, adapter=adapter, skill_file=skill)
    assert (root / 'records.json').exists()
    monkeypatch.setattr(ev, '_write_report', original)
    archive = OfficeQAEvidenceAdapter(adapter.dataset, adapter.runtime, ev.ArchiveTransport(adapter.transport.metadata()))
    assert ev.report_evaluation(root, adapter=archive)['status'] == 'complete'
    assert len(provider.requests) == 172


def test_native_rescoring_rejects_consistent_archive_score_tampering(evaluation):
    root, adapter, _, skill = evaluation()
    ev.run_evaluation(root, adapter=adapter, skill_file=skill)
    records = read(root / 'records.json')
    records[0]['execution']['metrics']['em'] = 1
    records[0]['provenance']['record_sha256'] = ev.p.digest(records[0]['execution'])
    (root / 'records.json').write_text(json.dumps(records))
    journal = root / 'batch/actor/results.jsonl'
    rows = [json.loads(line) for line in journal.read_text().splitlines()]
    rows[0]['record'] = records[0]['execution']
    journal.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    with pytest.raises(ValueError, match='Native score'):
        ev.report_evaluation(root, adapter=adapter)


def test_evaluate_cli_and_archive_resume_without_credentials(evaluation, monkeypatch, capsys):
    from src.skill_evolution.v26.cli import main
    root, adapter, _, skill = evaluation()
    actor = ChatTransport(endpoint='https://offline.invalid/chat/completions', api_key='synthetic',
                          model='offline-cli-fixture', max_completion_tokens=1234)
    config = root.parent / 'actor.json'; config.write_text(json.dumps(actor.metadata()))
    calls = []
    def fake_request(self, **body):
        calls.append(body); return response('1000')
    monkeypatch.setattr(ChatTransport, '__call__', fake_request)
    monkeypatch.setenv('OFFICEQA_OFFLINE_TEST_KEY', 'synthetic')
    args = ['evaluate', str(root), '--actor-config', str(config), '--prepared-root', str(adapter.dataset.root),
            '--parsed-root', str(adapter.runtime.parsed_root), '--skill', str(skill)]
    main([*args, '--actor-key-env', 'OFFICEQA_OFFLINE_TEST_KEY'])
    assert json.loads(capsys.readouterr().out)['em'] == 1
    assert len(calls) == 172
    (root / 'records.json').unlink()
    monkeypatch.delenv('OFFICEQA_OFFLINE_TEST_KEY')
    main([*args, '--resume'])
    assert json.loads(capsys.readouterr().out)['completed'] == 172
    assert len(calls) == 172
