"""Merged optimization uses synthetic sources; real checks read inventory only."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from src.adapters.officeqa.data import Dataset
from src.adapters.officeqa.transport import ChatTransport
from src.skill_evolution.v26.training import load_dataset, MERGED_POOL, POOL_IDS
from src.skill_evolution.v26.benchmarks.officeqa.adapter import OfficeQAEvidenceAdapter
from src.skill_evolution.v26.benchmarks.officeqa import protocol as p
from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26.config import validate_config, method_config
from src.skill_evolution.v26 import evolution, cli
from src.skill_evolution.v26.stages import read
from .conftest import Provider, response
from .test_campaign import FixedModules, campaign


@pytest.fixture
def merged(office, campaign, monkeypatch):
    root, original, runtime, _ = office
    _, _, _, config, _ = campaign()
    manifest = read(original.root / 'manifest.json')
    for public, disk in (('train', 'train'), ('validation', 'val')):
        manifest['splits'][disk] = list(POOL_IDS[public])
        rows = [{**deepcopy(original.rows['a']), 'id': uid, 'uid': uid,
                 'question': f'Question for {uid}?', 'split': disk} for uid in POOL_IDS[public]]
        (original.root / disk / 'items.json').write_text(json.dumps(rows))
    (original.root / 'manifest.json').write_text(json.dumps(manifest))
    base = Dataset(original.root); dataset = load_dataset(original.root, MERGED_POOL)
    scripts = {uid: [response('0')] for uid in dataset.splits['train']}
    provider = Provider(scripts)
    transport = ChatTransport(offline_create=provider, model='offline-fixture', max_completion_tokens=1234)
    metadata = {**transport.metadata(), 'transport': 'direct_http', 'endpoint': 'https://offline.invalid/chat/completions'}
    monkeypatch.setattr(transport, 'metadata', lambda: dict(metadata))
    adapter = OfficeQAEvidenceAdapter(dataset, runtime, transport, gate_metric=p.EM_GATE)
    ids = dataset.splits['train']
    # Deliberately cross the original split boundary in one batch.
    batches = [[ids[0], ids[50]], [uid for uid in ids if uid not in (ids[0], ids[50])]]
    config.update(optimization_pool=MERGED_POOL, optimization_splits=['train'], batches=batches,
                  actor=metadata, method=method_config())
    selection = read(Path(__file__).resolve().parents[3] / 'experiments/configs/v26_officeqa_training_selection.json')
    config['initial_skill'] = deepcopy(selection['campaign_fields']['initial_skill'])
    return root / 'merged_campaign', base, adapter, provider, config, FixedModules(branch='diagnosis_no_change')


def test_merge_preserves_source_rows_messages_answers_and_test(merged):
    _, base, adapter, _, _, _ = merged
    dataset = adapter.dataset
    assert dataset.splits['train'] == base.splits['train'] + base.splits['validation']
    assert len(dataset.splits['train']) == 74 and dataset.splits['validation'] == []
    for uid in dataset.splits['train']:
        prior, current = base.case(uid), dataset.case(uid)
        assert current.metadata['split'] == 'train'
        assert current.metadata['source_split'] == prior.metadata['split']
        assert current.payload == prior.payload and current.reference == prior.reference
        assert adapter.runtime.prepare(current, 'Skill') == adapter.runtime.prepare(prior, 'Skill')
    assert dataset.splits['test'] == base.splits['test']
    assert dataset.rows['t'] == base.rows['t']
    assert Dataset(base.root).rows == base.rows  # No rewritten prepared data.


def test_merged_campaign_cross_split_batch_and_archive_cli(merged, monkeypatch, capsys):
    root, base, adapter, provider, config, generate = merged
    def crash(stage):
        if stage == 'before_publish': raise KeyboardInterrupt()
    with using_benchmark(adapter), pytest.raises(KeyboardInterrupt):
        evolution.run_campaign(root, config=config, generate=generate, hook=crash)
    from src.skill_evolution.v26 import transport as method_transport
    def deny(*a, **k): raise AssertionError('Archive mode must not create clients')
    monkeypatch.setattr(ChatTransport, '__init__', deny)
    monkeypatch.setattr(method_transport.HTTPGenerator, '__init__', deny)
    args = ['run', str(root), '--config', str(root / 'config.json'), '--prepared-root', str(base.root),
            '--parsed-root', str(adapter.runtime.parsed_root), '--resume', '--archive-only']
    # R01 publishes from its saved responses, then the unchanged generator
    # guard stops before the next batch's new Actor work.
    with pytest.raises(ValueError, match='before new Actor'): cli.main(args)
    assert read(root / 'state.json')['next_round'] == 2 and len(provider.requests) == 2
    with using_benchmark(adapter):
        assert evolution.run_campaign(root, resume=True, generate=generate)['status'] == 'complete'
        assert evolution.final_parent(root).read_text() == config['initial_skill']['text']
    cli.main(args)
    assert json.loads(capsys.readouterr().out)['status'] == 'complete'
    assert len(provider.requests) == 74
    assert Dataset(base.root).rows == base.rows


@pytest.mark.parametrize('change', ['subset', 'test', 'validation', 'missing_mode', 'unknown_mode'])
def test_merged_config_guards(merged, change):
    _, _, adapter, provider, config, _ = merged
    if change == 'subset': config['batches'][1].pop()
    elif change == 'test': config['batches'][1][-1] = 't'
    elif change == 'validation': config['optimization_splits'] = ['train', 'validation']
    elif change == 'missing_mode': config.pop('optimization_pool')
    else: config['optimization_pool'] = 'unknown'
    with using_benchmark(adapter), pytest.raises(ValueError): validate_config(config)
    assert not provider.requests


def test_merged_epoch_pool_covers_all_74_each_epoch(merged):
    _, _, adapter, _, config, _ = merged
    config['batches'] = config['batches'] * 2
    config['epoch_schedule'] = {'epochs': 2, 'round_epochs': [1, 1, 2, 2], 'batch_size': 72}
    with using_benchmark(adapter):
        validate_config(config)
        config['batches'][-1] = config['batches'][-1][:-1]
        with pytest.raises(ValueError, match='Each epoch'): validate_config(config)


def test_merged_snapshot_detects_underlying_validation_drift(merged):
    _, base, adapter, _, config, _ = merged
    adapter.runtime_snapshot(config)
    path = base.root / 'val/items.json'; rows = read(path)
    rows[0]['answers'] = ['changed']; path.write_text(json.dumps(rows))
    with pytest.raises(ValueError, match='Dataset changed'): adapter.runtime_snapshot(config)


def test_real_selection_matches_upstream_initial_skill_and_inventory():
    root = Path(__file__).resolve().parents[3]
    selection = read(root / 'experiments/configs/v26_officeqa_training_selection.json')
    release = read(root / 'data/officeqa/releases/763a8366abf2a3605c381d53586d844dc60fa756/dataset_config.json')
    original = Dataset(release['prepared_root'])
    merged = load_dataset(original.root, selection['campaign_fields']['optimization_pool'])
    upstream = read(root / 'external/SkillAdam/skilladam/data/profiles/officeqa_main_results.json')
    assert selection['optimization_pool']['task_ids'] == merged.splits['train'] == upstream['splits']['train'] + upstream['splits']['val']
    assert len(merged.splits['test']) == 172 and not set(merged.splits['train']) & set(merged.splits['test'])
    provenance = selection['initial_skill_provenance']
    content = (root / provenance['path']).read_bytes()
    assert (root / provenance['snapshot']).read_bytes() == content
    assert hashlib.sha256(content).hexdigest() == provenance['sha256']
    assert selection['campaign_fields']['initial_skill']['text'] == content.decode()
    assert selection['campaign_fields']['gate_metric'] == p.EM_GATE and selection['stage0'] is False
    assert selection['status'] == 'resolved_in_formal_campaign_configuration'


def test_wrong_original_pool_inventory_rejected_before_requests(merged):
    _, base, _, _, _, _ = merged
    manifest = read(base.root / 'manifest.json')
    manifest['splits']['val'].reverse()
    path = base.root / 'val/items.json'; path.write_text(json.dumps(list(reversed(read(path)))))
    (base.root / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='fixed 50 Train'): load_dataset(base.root, MERGED_POOL)


@pytest.mark.parametrize('answer,decision', [('1000 extra', 'RETAIN'), ('1000', 'ACCEPT')])
def test_original_validation_case_uses_unchanged_strict_em_gate(merged, answer, decision):
    root, _, adapter, provider, config, _ = merged
    uid = POOL_IDS['validation'][0]
    provider.scripts[uid] = iter([response('0'), response(answer)])
    skill = root.parent / 'gate_skill.md'; skill.write_text(config['initial_skill']['text'])
    parents = adapter.actor_batch([uid], skill, root.parent / 'parent', {'split': 'train', 'role': 'parent'})
    candidates = adapter.actor_batch([uid], skill, root.parent / 'candidate', {'split': 'train', 'role': 'candidate'})
    result = adapter.build_gate(parents, candidates, [uid], parent_skill=skill.read_text(), candidate_skill=skill.read_text())
    assert result['result']['decision'] == decision
