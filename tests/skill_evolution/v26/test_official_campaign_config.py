"""Offline coverage of the formal task budget and disabled online review policy."""
from copy import deepcopy
import json
from threading import Barrier, Lock

import pytest

from scripts.runs import run_v26_campaign
from src.adapters.officeqa.transport import ChatTransport
from src.adapters.officeqa.data import Dataset
from src.adapters.officeqa import execution
from src.skill_evolution.v26 import cli, evolution as ev, stages, transport
from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26.config import method_config, REVIEW_DISABLED, validate_config
from src.skill_evolution.v26.benchmarks.officeqa.task_budget import TaskOutputBudgetAdapter
from src.skill_evolution.v26.benchmarks.officeqa import protocol as p, evidence
from .conftest import Provider, response
from .test_campaign import campaign, FixedModules


@pytest.mark.parametrize('interrupted', [False, True])
def test_task_budget_both_roles_replay_publication_and_resume(office, campaign, monkeypatch, interrupted):
    root, dataset, runtime, _ = office
    provider = Provider({'a': [response('0'), response('1000')], 'b': [response('0'), response('1000')]})
    default = ChatTransport(offline_create=provider, model='offline-fixture', max_completion_tokens=32768)
    high = ChatTransport(offline_create=provider, model='offline-fixture', max_completion_tokens=65536)
    adapter = TaskOutputBudgetAdapter(dataset, runtime, default, gate_metric=p.EM_GATE, task_transports={'a': high})
    target, _, _, config, _ = campaign(batches=[['a', 'b']])
    config.update(actor=default.metadata(), actor_task_output_limits={'a': 65536},
                  method=method_config(REVIEW_DISABLED))
    generate = FixedModules(conflict=True)
    def forbidden(*a, **kw): raise AssertionError('Online review must not run')
    for name in ('review_input', 'verifier_call', 'repair_call'):
        monkeypatch.setattr(ev.modules, name, forbidden)
    with using_benchmark(adapter):
        if interrupted:
            def stop(stage):
                if stage == 'before_publish': raise KeyboardInterrupt()
            with pytest.raises(KeyboardInterrupt):
                ev.run_campaign(target, config=config, generate=generate, hook=stop)
            # Recover unfinished publication from completed shared-pool journals.
            for side in ('parent_runs', 'candidate_runs'):
                (target / 'rounds/R01' / side / 'records.json').unlink()
            result = ev.run_campaign(target, config=config, resume=True)
        else:
            result = ev.run_campaign(target, config=config, generate=generate)
        assert result['status'] == 'complete'
        assert [c[0] for c in generate.calls] == ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay']
        assert len(provider.requests) == 4
        for request in provider.requests:
            task = 'a' if 'Question for a?' in json.dumps(request['messages']) else 'b'
            assert request['max_completion_tokens'] == (65536 if task == 'a' else 32768)
        bundle = stages.read(target / 'rounds/R01/pairs/input.json')
        assert bundle['background']['task_max_completion_tokens'] == {'a': 65536}
        parents = {r['task_id']: r for r in bundle['audit']['parent_records']}
        candidates = {r['task_id']: r for r in bundle['audit']['candidate_records']}
        for task in parents:
            evidence.verify_pair(parents[task], candidates[task])
            assert parents[task]['execution']['actor'] == candidates[task]['execution']['actor']
        review = stages.read(target / 'rounds/R01/knowledge_review/result.json')
        assert review['status'] == 'disabled' and review['conflicts'] is None and not review['repair_applied']
        assert not (target / 'rounds/R01/verifier').exists()
        assert not (target / 'rounds/R01/repair').exists()
        assert 'paired answer difference' in json.dumps(stages.read(target / 'rounds/R01/memory/view.json'))
        assert stages.read(target / 'runtime.json')['actor_task_output_limits'] == {'a': 65536}
        ev.run_campaign(target, config=config, resume=True)
        ev.final_parent(target)
        assert len(provider.requests) == 4 and len(generate.calls) == 5
        bad = deepcopy(candidates['a']); bad['execution']['actor']['max_completion_tokens'] = 32768
        bad['provenance']['record_sha256'] = p.digest(bad['execution'])
        with pytest.raises(ValueError, match='Task Actor budget differs'):
            adapter.build_facts([bad], role='candidate')
        with pytest.raises(ValueError, match='Pair Actor conditions differ'):
            evidence.verify_pair(parents['a'], bad)
        drift = deepcopy(config); drift['actor_task_output_limits']['a'] = 32768
        with pytest.raises(ValueError, match='Task output limits differ'):
            validate_config(drift)


def test_disabled_review_still_rejects_invalid_replay_references(campaign):
    target, adapter, provider, config, generate = campaign()
    config['method'] = method_config(REVIEW_DISABLED)
    def invalid(name, messages, directory, cfg):
        result = generate(name, messages, directory, cfg)
        if name == 'replay':
            result['content'] = result['content'].replace('Q1:outcome', 'Q999:outcome')
        return result
    with using_benchmark(adapter), pytest.raises(stages.Stopped, match='budget exhausted'):
        ev.run_campaign(target, config=config, generate=invalid)
    assert len(provider.requests) == 2
    assert not (target / 'rounds/R01/knowledge_review').exists()
    assert not any(c[0] in ('verifier', 'repair') for c in generate.calls)


def test_formal_launcher_validate_only_without_credentials_or_clients(campaign, monkeypatch, capsys):
    target, adapter, provider, config, _ = campaign()
    config['actor'].update(transport='direct_http', endpoint='https://offline.invalid/chat/completions')
    config.update(method=method_config(REVIEW_DISABLED), actor_task_output_limits={'a': 65536})
    path = target.parent / 'config.json'; path.write_text(json.dumps(config))
    def forbidden(*a, **kw): raise AssertionError('Validation must not construct clients or start a campaign')
    monkeypatch.setattr(ChatTransport, '__init__', forbidden)
    monkeypatch.setattr(transport.HTTPGenerator, '__init__', forbidden)
    monkeypatch.setattr(ev, 'run_campaign', forbidden)
    monkeypatch.setattr(run_v26_campaign, 'read_credentials', forbidden)
    run_v26_campaign.main([str(target), '--config', str(path), '--validate-only',
        '--env-file', str(target.parent / 'missing.env'), '--prepared-root', str(adapter.dataset.root),
        '--parsed-root', str(adapter.runtime.parsed_root)])
    result = json.loads(capsys.readouterr().out)
    assert result['status'] == 'configuration_validated'
    assert result['model_requests'] == 0 and not result['training_started'] and not result['online_review_enabled']
    assert result['task_actors']['a']['max_completion_tokens'] == 65536
    assert not target.exists() and not provider.requests


def test_validate_only_rejects_resume_or_credentials(campaign):
    target, adapter, _, config, _ = campaign()
    path = target.parent / 'config.json'; path.write_text(json.dumps(config))
    for options in (['--resume'], ['--actor-key-env', 'UNUSED'], ['--archive-only']):
        with pytest.raises(ValueError, match='--validate-only cannot'):
            cli.main(['run', str(target), '--config', str(path), '--validate-only',
                '--prepared-root', str(adapter.dataset.root), '--parsed-root', str(adapter.runtime.parsed_root), *options])
    assert not target.exists()


def test_formal_cli_dispatches_both_budgets_without_online_review(campaign, monkeypatch, capsys):
    target, adapter, _, config, _ = campaign(batches=[['a', 'b']])
    config['actor'].update(max_completion_tokens=32768, transport='direct_http',
                           endpoint='https://offline.invalid/chat/completions')
    config.update(method=method_config(REVIEW_DISABLED), actor_task_output_limits={'a': 65536})
    path = target.parent / 'config.json'; path.write_text(json.dumps(config))
    provider = Provider({'a': [response('0'), response('1000')], 'b': [response('0'), response('1000')]})
    made = []
    def make_actor(**kwargs):
        limit = kwargs['max_completion_tokens']; made.append(limit)
        actor = ChatTransport(offline_create=provider, model='offline-fixture', max_completion_tokens=limit)
        metadata = {**config['actor'], 'max_completion_tokens': limit}
        monkeypatch.setattr(actor, 'metadata', lambda: dict(metadata))
        return actor
    generate = FixedModules(conflict=True)
    monkeypatch.setattr('src.adapters.officeqa.transport.ChatTransport', make_actor)
    monkeypatch.setattr(transport, 'HTTPGenerator', lambda key: generate)
    monkeypatch.setenv('FIXTURE_KEY', 'offline-fixture')
    cli.main(['run', str(target), '--config', str(path), '--prepared-root', str(adapter.dataset.root),
        '--parsed-root', str(adapter.runtime.parsed_root), '--actor-key-env', 'FIXTURE_KEY',
        '--method-key-env', 'FIXTURE_KEY'])
    assert json.loads(capsys.readouterr().out)['status'] == 'complete'
    assert made == [32768, 65536] and len(provider.requests) == 4
    assert [c[0] for c in generate.calls] == ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay']
    for side in ('parent_runs', 'candidate_runs'):
        records = stages.read(target / 'rounds/R01' / side / 'records.json')
        assert {r['task_id']: r['execution']['actor']['max_completion_tokens'] for r in records} == {
            'a': 65536, 'b': 32768}


@pytest.mark.parametrize('role', ['parent', 'candidate'])
def test_uid0007_enters_same_four_worker_pool_with_per_task_limits(office, monkeypatch, role):
    root, original, runtime, _ = office
    ids = ['UID0002', 'UID0007', 'UID0014', 'UID0017', 'UID0018', 'UID0019']
    rows = [{**deepcopy(original.rows['a']), 'id': uid, 'uid': uid, 'question': f'Question for {uid}?'}
            for uid in ids]
    stages.save(original.root / 'train/items.json', rows)
    manifest = stages.read(original.root / 'manifest.json'); manifest['splits']['train'] = ids
    stages.save(original.root / 'manifest.json', manifest)
    dataset = Dataset(original.root)
    provider = Provider({uid: [response('1000')] for uid in ids})
    default = ChatTransport(offline_create=provider, model='offline-fixture', max_completion_tokens=32768)
    high = ChatTransport(offline_create=provider, model='offline-fixture', max_completion_tokens=65536)
    adapter = TaskOutputBudgetAdapter(dataset, runtime, default, gate_metric=p.EM_GATE,
                                     task_transports={'UID0007': high})
    barrier, lock = Barrier(4), Lock()
    started, counts, pools = [], {'active': 0, 'peak': 0}, []
    run = runtime.run
    def observed(case, skill, transport, *, owner, directory):
        with lock:
            started.append((case.case_id, transport.metadata()['max_completion_tokens']))
            first_wave = len(started) <= 4
            counts['active'] += 1
            counts['peak'] = max(counts['peak'], counts['active'])
        try:
            if first_wave: barrier.wait(timeout=5)
            return run(case, skill, transport, owner=owner, directory=directory)
        finally:
            with lock: counts['active'] -= 1
    monkeypatch.setattr(runtime, 'run', observed)
    executor = execution.ThreadPoolExecutor
    def pool(*args, **kwargs):
        pools.append(kwargs['max_workers'])
        return executor(*args, **kwargs)
    monkeypatch.setattr(execution, 'ThreadPoolExecutor', pool)
    directory = root / role
    config = {'role': role, 'split': 'train'}
    records = adapter.actor_batch(ids, None, directory, config)
    assert pools == [4] and counts['peak'] == 4
    assert {uid for uid, _ in started[:4]} == set(ids[:4])
    expected = {uid: 65536 if uid == 'UID0007' else 32768 for uid in ids}
    assert dict(started) == expected
    assert {r['task_id']: r['execution']['actor']['max_completion_tokens'] for r in records} == expected
    assert default.metadata()['max_completion_tokens'] == 32768 and high.metadata()['max_completion_tokens'] == 65536
    assert stages.read(directory / 'actor/run.json')['ids'] == ids
    assert len((directory / 'actor/results.jsonl').read_text().splitlines()) == len(ids)
    assert not (directory / 'default_budget').exists() and not (directory / 'task_budget').exists()
    adapter.actor_batch(ids, None, directory, config)
    assert len(provider.requests) == len(ids) and len(started) == len(ids)
    changed = TaskOutputBudgetAdapter(dataset, runtime, default, gate_metric=p.EM_GATE,
                                     task_transports={'UID0007': default})
    with pytest.raises(ValueError, match='Evidence batch identity differs'):
        changed.actor_batch(ids, None, directory, config)
    assert len(provider.requests) == len(ids)
