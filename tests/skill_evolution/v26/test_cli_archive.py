"""Campaign CLI archive recovery with provider construction forbidden."""
import json

import pytest

from src.adapters.officeqa.transport import ChatTransport
from src.skill_evolution.v26 import cli, evolution as ev, stages, transport
from src.skill_evolution.v26.benchmark import using_benchmark
from .test_campaign import campaign


@pytest.fixture
def cli_campaign(campaign, monkeypatch):
    root, adapter, provider, config, generate = campaign()
    # Only the public metadata mimics production; all requests still use the
    # existing predetermined fixture, under the autouse network prohibition.
    metadata = {**adapter.transport.metadata(), 'transport': 'direct_http',
                'endpoint': 'https://offline.invalid/chat/completions'}
    monkeypatch.setattr(adapter.transport, 'metadata', lambda: dict(metadata))
    config['actor'] = metadata
    args = ['run', str(root), '--config', str(root / 'config.json'),
            '--prepared-root', str(adapter.dataset.root), '--parsed-root', str(adapter.runtime.parsed_root)]
    return root, adapter, provider, config, generate, args


def prohibit_clients(monkeypatch):
    def deny(*a, **k): raise AssertionError('Archive recovery must not construct request clients')
    monkeypatch.setattr(ChatTransport, '__init__', deny)
    monkeypatch.setattr(transport.HTTPGenerator, '__init__', deny)


@pytest.mark.parametrize('point', ['complete', 'before_publish', 'saved_verifier'])
def test_archive_cli_recovers_without_keys_or_clients(cli_campaign, monkeypatch, capsys, point):
    root, adapter, provider, config, generate, args = cli_campaign
    def hook(stage):
        if point == 'before_publish' and stage == 'before_publish': raise KeyboardInterrupt()
    def generator(name, messages, path, cfg):
        result = generate(name, messages, path, cfg)
        if point == 'saved_verifier' and name == 'verifier':
            stages.save(path / 'response.json', result)
            raise KeyboardInterrupt()
        return result
    with using_benchmark(adapter):
        if point == 'complete': ev.run_campaign(root, config=config, generate=generator)
        else:
            with pytest.raises(KeyboardInterrupt):
                ev.run_campaign(root, config=config, generate=generator, hook=hook)
    if point == 'before_publish':
        for side in ('parent_runs', 'candidate_runs'):
            (root / 'rounds/R01' / side / 'records.json').unlink()
    counts = len(provider.requests), len(generate.calls)
    journals = {p: p.read_bytes() for p in root.glob('rounds/**/results.jsonl')}
    prohibit_clients(monkeypatch)
    cli.main([*args, '--resume', '--archive-only'])
    assert json.loads(capsys.readouterr().out)['status'] == 'complete'
    assert (len(provider.requests), len(generate.calls)) == counts
    assert all(p.read_bytes() == value for p, value in journals.items())
    assert stages.read(root / 'state.json')['next_round'] == 2
    with using_benchmark(adapter): assert ev.final_parent(root).read_text() == 'Candidate 1\n'
    if point == 'saved_verifier':
        assert stages.read(root / 'rounds/R01/verifier/attempts/001/recovery.json')['additional_requests'] == 0


@pytest.mark.parametrize('phase', ['parent_runs', 'candidate_runs', 'grouping'])
def test_archive_cli_stops_before_new_actor_or_method_request(cli_campaign, monkeypatch, phase):
    root, adapter, provider, config, generate, args = cli_campaign
    def hook(stage):
        if stage == phase: raise KeyboardInterrupt()
    with using_benchmark(adapter), pytest.raises(KeyboardInterrupt):
        ev.run_campaign(root, config=config, generate=generate, hook=hook)
    requests = list(root.glob('rounds/**/request_started.json'))
    counts = len(provider.requests), len(generate.calls)
    prohibit_clients(monkeypatch)
    message = 'before new Actor' if phase.endswith('_runs') else 'generator required for a new request'
    with pytest.raises(ValueError, match=message): cli.main([*args, '--resume', '--archive-only'])
    assert list(root.glob('rounds/**/request_started.json')) == requests
    assert (len(provider.requests), len(generate.calls)) == counts
    if phase.endswith('_runs'): assert not (root / 'rounds/R01' / phase).exists()
    assert stages.read(root / 'state.json')['next_round'] == 1


def test_archive_cli_incomplete_journal_does_not_enter_actor(cli_campaign, monkeypatch):
    root, adapter, provider, config, generate, args = cli_campaign
    def hook(stage):
        if stage == 'before_publish': raise KeyboardInterrupt()
    with using_benchmark(adapter), pytest.raises(KeyboardInterrupt):
        ev.run_campaign(root, config=config, generate=generate, hook=hook)
    folder = root / 'rounds/R01/parent_runs'
    (folder / 'records.json').unlink()
    (folder / 'actor/results.jsonl').write_text('')
    counts = len(provider.requests), len(generate.calls)
    prohibit_clients(monkeypatch)
    with pytest.raises(ValueError, match='before new Actor'):
        cli.main([*args, '--resume', '--archive-only'])
    assert (len(provider.requests), len(generate.calls)) == counts
    assert not (folder / 'records.json').exists()


def test_archive_cli_preserves_exhausted_module_budget(cli_campaign, monkeypatch):
    root, adapter, provider, config, _, args = cli_campaign
    def invalid(*a): return {'content': '{}', 'finish_reason': 'stop'}
    with using_benchmark(adapter), pytest.raises(stages.Stopped, match='budget exhausted'):
        ev.run_campaign(root, config=config, generate=invalid)
    attempts = root / 'rounds/R01/grouping/attempts'
    assert len(list(attempts.iterdir())) == 6
    prohibit_clients(monkeypatch)
    with pytest.raises(stages.Stopped, match='budget exhausted'):
        cli.main([*args, '--resume', '--archive-only'])
    assert len(list(attempts.iterdir())) == 6 and len(provider.requests) == 1


@pytest.mark.parametrize('options', [[], ['--resume'], ['--actor-key-env', 'ACTOR_KEY'],
    ['--archive-only'], ['--archive-only', '--resume', '--actor-key-env', 'ACTOR_KEY'],
    ['--archive-only', '--resume', '--method-key-env', 'METHOD_KEY']])
def test_cli_requires_explicit_mode_before_client_initialization(cli_campaign, monkeypatch, options):
    root, _, _, _, _, args = cli_campaign
    prohibit_clients(monkeypatch)
    with pytest.raises(ValueError): cli.main([*args, *options])
    assert not root.exists()


def test_archive_cli_cannot_initialize_a_new_campaign(cli_campaign, monkeypatch):
    root, _, _, config, _, args = cli_campaign
    path = root.parent / 'input_config.json'; path.write_text(json.dumps(config))
    args[args.index('--config') + 1] = str(path)
    prohibit_clients(monkeypatch)
    with pytest.raises(ValueError, match='existing initialized Campaign'):
        cli.main([*args, '--resume', '--archive-only'])
    assert not root.exists()


def test_archive_cli_rejects_config_drift(cli_campaign, monkeypatch):
    root, adapter, provider, config, _, args = cli_campaign
    with using_benchmark(adapter): ev.initialize(root, config)
    changed = {**config, 'max_attempts': 5}
    path = root.parent / 'changed.json'; path.write_text(json.dumps(changed))
    args[args.index('--config') + 1] = str(path)
    prohibit_clients(monkeypatch)
    with pytest.raises(ValueError, match='configuration differs'):
        cli.main([*args, '--resume', '--archive-only'])
    assert not provider.requests and not (root / 'rounds').exists()


def test_explicit_live_cli_still_uses_both_supplied_clients(cli_campaign, monkeypatch, capsys):
    root, adapter, provider, config, generate, args = cli_campaign
    path = root.parent / 'input_config.json'; path.write_text(json.dumps(config))
    args[args.index('--config') + 1] = str(path)
    monkeypatch.setenv('ACTOR_FIXTURE_KEY', 'actor-fixture')
    monkeypatch.setenv('METHOD_FIXTURE_KEY', 'method-fixture')
    keys = []
    def actor_factory(**kwargs):
        keys.append(kwargs['api_key']); return adapter.transport
    def method_factory(key):
        keys.append(key); return generate
    monkeypatch.setattr('src.adapters.officeqa.transport.ChatTransport', actor_factory)
    monkeypatch.setattr(transport, 'HTTPGenerator', method_factory)
    cli.main([*args, '--actor-key-env', 'ACTOR_FIXTURE_KEY', '--method-key-env', 'METHOD_FIXTURE_KEY'])
    assert json.loads(capsys.readouterr().out)['status'] == 'complete'
    assert keys == ['actor-fixture', 'method-fixture']
    assert len(provider.requests) == 2 and len(generate.calls) == 6
