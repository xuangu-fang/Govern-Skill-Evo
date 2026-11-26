"""Exercise the production bindings with a denied network and synthetic responses."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from scripts.runs import run_v26_3_campaign as cli
from src.adapters.officeqa.runtime import Runtime
from src.adapters.officeqa.transport import ChatTransport
from src.skill_evolution.v26_3 import config, evolution, memory, protocol, reporting
from tests.skill_evolution.v26_1.conftest import offline_only
from tests.skill_evolution.v26_1.support import MethodProvider, make, response

CONFIG = protocol.ROOT / 'experiments/configs/v26_3_officeqa_train74.json'
PROMPT_HASHES = {
    'diagnosis': '9cb9da17164a3769104b16cf8df49d0869502a5e5c600efe631a8c3fd30cde70',
    'preconditioner': 'cb59b127b989017d3c1c7fc399d3f171c67bb519dfb729bccf07c136d1e9e115',
    'editor': '6b72d0a88a099785caffb61ed6877308b59bdd6196d855fd711f123829593c9e',
    'replay': '2fa9178d80ea13e85aa57e974f53cbe1b067ea6d52fb3dbfb5df21dac428ce05',
}


def test_production_profile_and_readonly_cli(tmp_path, monkeypatch, capsys):
    cfg = evolution.read(CONFIG)
    previous = deepcopy(cfg)
    previous['method']['version'] = 'v26_2_campaign_v1'
    previous['method']['prompts']['preconditioner'] = 'v26_2_officeqa_preconditioner_v1'
    # Canonical JSON digest of the v26.2 production campaign config, including its ordered batches.
    assert protocol.digest(previous) == '2559a1d1beb47397ecbe64b1cebee2fc3035b444ce0d3bdebd4fd96cb427877b'
    assert {k: sha256(s.encode()).hexdigest() for k, s in config.render_prompts().items()} == PROMPT_HASHES
    with cli.bind(cfg).using():
        for wrong in (previous, {**cfg, 'batches': list(reversed(cfg['batches']))}):
            with pytest.raises(ValueError):
                config.validate_config(wrong)
        wrong = deepcopy(cfg)
        wrong['module_calls']['editor']['endpoint'] = 'https://api.deepseek.com/chat/completions'
        with pytest.raises(ValueError):
            config.validate_config(wrong)
    wrong = deepcopy(cfg)
    wrong['actor']['model'] = 'deepseek-flash'
    with pytest.raises(ValueError):
        cli.bind(wrong)

    def forbidden(*args, **kwargs):
        pytest.fail('Read-only preflight entered execution')
    for name in ('ChatTransport', 'HTTPGenerator', 'run_training', 'run_test'):
        monkeypatch.setattr(cli, name, forbidden)
    campaign = tmp_path / 'absent'
    cli.main(['train', str(campaign), '--config', str(CONFIG), '--validate-only'])
    assert json.loads(capsys.readouterr().out) == {
        'status': 'valid', 'method': 'v26_3_campaign_v1', 'optimization_count': 74, 'test_count': 172,
        'batch_sizes': [11, 11, 11, 11, 10, 10, 10], 'model_requests': 0,
        'training_started': False, 'test_started': False,
    }
    assert not campaign.exists()


def test_seven_mock_rounds_handoff_resume_and_final_test(tmp_path):
    fixture, actor, _ = make(tmp_path / 'fixture', full=True)
    dataset = fixture.dataset
    dataset.batches = deepcopy(protocol.PLAN['schedule']['batches'])

    def transport(limit):
        return ChatTransport(model=protocol.ACTOR['model'], max_completion_tokens=limit,
                             reasoning_effort='medium', reasoning_mode='deepseek_thinking',
                             token_limit_field='max_tokens', offline_create=actor)

    method = cli.CampaignAdapter(dataset, Runtime(fixture.runtime.parsed_root), transport(32768),
                                 task_transports={'UID0007': transport(65536)})
    cfg = config.campaign_config(method)
    provider = MethodProvider('candidate')
    actor.scripts = {uid: [response('0'), response('1000')] for uid in dataset.splits['train']}
    replacement = 'Apply the requested rounding to the numeric value.'

    def generate(name, messages, directory, call_config):
        assert call_config == cfg['module_calls'][name]
        assert sha256(messages[0]['content'].encode()).hexdigest() == PROMPT_HASHES[name]
        result = provider(name, messages, directory, call_config)
        if name == 'preconditioner':
            value = json.loads(result['content'])
            value['adjustments'][0].update(action='REPLACE', text=replacement)
            result['content'] = json.dumps(value)
        if name == 'editor':
            payload = json.loads(messages[1]['content'])
            assert payload['plan']['updates'] == [{'id': 'u1', 'text': replacement}]
            if replacement not in payload['parent']:
                value = json.loads(result['content'])
                value['edits'][0]['patch'] += '+' + replacement + '\n'
                result['content'] = json.dumps(value)
        return result

    campaign, output = tmp_path / 'campaign', tmp_path / 'test'
    with method.using():
        def interrupt(point):
            if point == 'after_memory_commit':
                raise KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            evolution.run_round(campaign, config=cfg, generate=generate, hook=interrupt)
        before = len(actor.requests), len(provider.calls)
        evolution.resume_round(campaign)
        assert before == (len(actor.requests), len(provider.calls)) == (22, 4)
        with pytest.raises(ValueError, match='not complete'):
            cli.prepare_test(campaign, output)
        summary = cli.run_training(campaign, cfg, generate=generate, resume=True)
        assert summary['rounds_completed'] == 7 and summary['optimization_count'] == 74
        assert not summary['test_started'] and not output.exists()
        assert len(actor.requests) == 148 and len(provider.calls) == 28
        for request in actor.requests:
            is_override = 'Question for UID0007?' in json.dumps(request['messages'])
            assert request['max_tokens'] == (65536 if is_override else 32768)
            assert request['model'] == 'deepseek-v4.1-flash'
        for n in range(1, 8):
            rd = campaign / 'rounds' / f'R{n:02}'
            assert evolution.read(rd / 'preconditioner/identity.json')['prompt'] == protocol.PRECONDITIONER_VERSION
            assert evolution.read(rd / 'gate/result.json')['decisions'][0]['gate_decision'] == 'Retain'
        prior = memory.load_memory(campaign / 'memory')
        assert len(prior['memory']['rounds']) == 7
        actor.scripts[dataset.splits['test'][-1]] = [KeyboardInterrupt()]
        with pytest.raises(KeyboardInterrupt):
            cli.run_test(campaign, output)
        incomplete = evolution.read(output / 'incomplete.json')
        assert incomplete['em'] is None and incomplete['f1'] is None
        assert 0 < incomplete['correct'] == incomplete['completed'] < 172
        assert dataset.splits['test'][-1] in incomplete['pending']
        report = cli.run_test(campaign, output, resume=True)
        assert report['method'] == protocol.METHOD_VERSION
        assert report['completed'] == report['correct'] == 172
        assert report['em'] == report['f1'] == 1
        assert all(req['max_tokens'] == 32768 for req in actor.requests[148:])
        assert (campaign / 'final_skill.md').read_bytes() == (output / 'skill.md').read_bytes()
        assert replacement in (output / 'skill.md').read_text()
        assert memory.load_memory(campaign / 'memory') == prior


def test_same_budget_comparison(tmp_path):
    def evaluation(label, values):
        root = tmp_path / label
        (root / 'runs/actor').mkdir(parents=True)
        (root / 'evaluation.json').write_text(json.dumps({
            'tasks': ['a', 'b', 'c', 'd'], 'revision': 'r', 'scorer_profile': 's'}))
        with (root / 'runs/actor/results.jsonl').open('w') as journal:
            for uid, em, budget in values:
                record = {'task_id': uid, 'metrics': {'em': em}, 'actor': {'max_completion_tokens': budget}}
                journal.write(json.dumps({'id': uid, 'record': record}) + '\n')
            journal.write('{"id":')  # Uncommitted bytes from an interrupted run.
        return root
    old = evaluation('old', [('b', 1, 32768), ('a', 0, 32768), ('c', 1, 65536)])
    new = evaluation('new', [('a', 1, 32768), ('b', 0, 32768), ('c', 0, 32768), ('d', 0, 32768)])
    report = reporting.compare_tests(new, old)
    assert report['common'] == 2 and report['baseline_correct'] == report['evaluation_correct'] == 1
    assert report['gain_ids'] == ['a'] and report['loss_ids'] == ['b']


def test_previous_checkpoint_rejected_before_requests(tmp_path):
    from src.skill_evolution.v26_2 import evolution as previous
    from tests.skill_evolution.v26_2.test_campaign import synthetic_method

    old, actor, cfg = synthetic_method(tmp_path)
    campaign = tmp_path / 'campaign'
    with old.using():
        previous.initialize(campaign, cfg)
    before = {path: path.read_bytes() for path in campaign.rglob('*') if path.is_file()}
    provider = MethodProvider()
    with cli.bind(evolution.read(CONFIG)).using(), pytest.raises(ValueError):
        evolution.run_campaign(campaign, resume=True, generate=provider)
    assert not actor.requests and not provider.calls
    assert {path: path.read_bytes() for path in before} == before
