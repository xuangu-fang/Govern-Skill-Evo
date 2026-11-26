"""Offline acceptance for the two changes to OfficeQA v26.1."""
from copy import deepcopy
import json

import pytest

from scripts.runs import run_v26_2_campaign as cli
from src.adapters.officeqa.runtime import Runtime
from src.skill_evolution.v26_1 import config as baseline
from src.skill_evolution.v26_2 import config, diagnosis, evolution, facts, memory, preconditioner, protocol
from src.skill_evolution.v26_2.campaign import CampaignAdapter
from src.skill_evolution.v26_2.execution_input_view import restore_model_input
from tests.skill_evolution.v26_1.conftest import offline_only
from tests.skill_evolution.v26_1.support import MethodProvider, batch, make, response

CONFIG = protocol.ROOT / 'experiments/configs/v26_2_officeqa_train74.json'
BASE_CONFIG = CONFIG.with_name('v26_1_officeqa_train74.json')
SIZES = [11, 11, 11, 11, 10, 10, 10]


def synthetic_method(tmp_path):
    old, actor, _ = make(tmp_path / 'fixture', full=True)
    old.dataset.batches = deepcopy(protocol.PLAN['schedule']['batches'])
    adapter = CampaignAdapter(
        old.dataset, Runtime(old.runtime.parsed_root), old.transport,
        task_transports={uid: item.transport for uid, item in old.task_adapters.items()},
    )
    return adapter, actor, config.campaign_config(adapter)


def test_release_config_prompts_and_readonly_cli(tmp_path, monkeypatch, capsys):
    old = evolution.read(BASE_CONFIG)
    cfg = evolution.read(CONFIG)
    expected = deepcopy(old)
    expected['method']['version'] = config.METHOD_VERSION
    expected['method']['prompts']['preconditioner'] = protocol.PRECONDITIONER_VERSION
    expected['batches'] = cfg['batches']
    assert cfg == expected
    assert list(map(len, cfg['batches'])) == SIZES
    assert sum(cfg['batches'], []) == sum(old['batches'], [])
    assert not set(sum(cfg['batches'], [])).intersection(protocol.PLAN['schedule']['test_ids'])
    prompts = baseline.render_prompts()
    prompts['preconditioner'] = (protocol.DESIGN / 'prompts/preconditioner.md').read_bytes().decode()
    assert config.render_prompts() == prompts

    method = cli.bind(cfg)
    with method.using():
        for wrong in (old, {**cfg, 'batches': old['batches']},
                      {**cfg, 'method': old['method']}):
            with pytest.raises(ValueError):
                config.validate_config(wrong)
        assert [method.dataset.case(uid).metadata['source_split']
                for uid in cfg['batches'][4]] == ['train'] * 6 + ['validation'] * 4
    with cli.bind(cfg).using(), pytest.raises(ValueError):
        baseline.validate_config(cfg)

    def forbidden(*args, **kwargs):
        pytest.fail('Read-only preflight attempted execution or live transport')
    for name in ('ChatTransport', 'HTTPGenerator', 'run_training', 'run_test'):
        monkeypatch.setattr(cli, name, forbidden)
    location = tmp_path / 'absent'
    cli.main(['train', str(location), '--config', str(CONFIG), '--validate-only'])
    status = json.loads(capsys.readouterr().out)
    assert status == dict(status='valid', method=config.METHOD_VERSION,
                          optimization_count=74, test_count=172, batch_sizes=SIZES,
                          model_requests=0, training_started=False, test_started=False)
    assert not location.exists()


def test_seven_rounds_resume_and_separate_synthetic_test(tmp_path):
    method, actor, cfg = synthetic_method(tmp_path)
    root, output = tmp_path / 'campaign', tmp_path / 'evaluation'
    provider = MethodProvider('candidate')
    actor.scripts = {uid: [response('0'), response('1000')] for uid in method.dataset.splits['train']}
    with method.using():
        def interrupt(point):
            if point == 'after_memory_commit':
                raise KeyboardInterrupt('synthetic publication interruption')

        with pytest.raises(KeyboardInterrupt):
            evolution.run_round(root, config=cfg, generate=provider, hook=interrupt)
        before = len(actor.requests), len(provider.calls)
        evolution.resume_round(root)
        assert before == (len(actor.requests), len(provider.calls)) == (22, 4)
        with pytest.raises(ValueError, match='not complete'):
            cli.prepare_test(root, output)

        summary = cli.run_training(root, cfg, generate=provider, resume=True)
        assert summary['method'] == config.METHOD_VERSION
        assert summary['rounds_completed'] == 7 and summary['optimization_count'] == 74
        assert not summary['test_started'] and not output.exists()
        assert not (root / 'rounds/R08').exists()
        assert (len(actor.requests), len(provider.calls)) == (148, 28)
        prompts = config.render_prompts()
        for name, messages in provider.calls:
            assert messages[0] == {'role': 'system', 'content': prompts[name]}
        for number, tasks in enumerate(cfg['batches'], 1):
            rd = root / 'rounds' / f'R{number:02}'
            assert evolution.read(rd / 'round_input.json')['tasks'] == tasks
            ident = evolution.read(rd / 'preconditioner/identity.json')
            assert ident['prompt'] == protocol.PRECONDITIONER_VERSION
            message = evolution.read(rd / 'diagnosis/base_messages.json')[1]
            payload = restore_model_input(json.loads(message['content']), module='diagnosis')
            assert len(payload['runs']) == len(tasks)
            assert {r['task_id'] for r in payload['runs']} == set(tasks)
        for request in actor.requests:
            override = 'Question for UID0007?' in json.dumps(request['messages'])
            assert request['max_tokens'] == (65536 if override else 32768)
        prior = memory.load_memory(root / 'memory')
        assert len(prior['memory']['rounds']) == 7
        assert sum(len(r['entries']) for r in prior['memory']['rounds']) == 74

        # Only synthetic files and the in-process provider reach evaluation.
        actor.scripts[method.dataset.splits['test'][0]] = [KeyboardInterrupt('synthetic Test interruption')]
        with pytest.raises(KeyboardInterrupt):
            cli.run_test(root, output)
        incomplete = evolution.read(output / 'incomplete.json')
        assert incomplete['em'] is None and incomplete['f1'] is None
        report = cli.run_test(root, output, resume=True)
        assert report['count'] == report['correct'] == report['completed'] == 172
        assert report['method'] == config.METHOD_VERSION
        assert all(r['max_tokens'] == 32768 for r in actor.requests[148:])
        assert (root / 'final_skill.md').read_bytes() == (output / 'skill.md').read_bytes()
        assert memory.load_memory(root / 'memory') == prior


@pytest.mark.parametrize(('mode', 'outcome'), [
    ('withdraw', 'preconditioner_withdrawn'), ('empty', 'editor_no_change'), ('null', None),
])
def test_short_circuits(tmp_path, mode, outcome):
    method, actor, cfg = synthetic_method(tmp_path)
    root = tmp_path / 'campaign'
    provider = MethodProvider(mode)
    with method.using():
        if outcome is None:
            with pytest.raises(evolution.Stopped, match='patch=null'):
                evolution.run_round(root, config=cfg, generate=provider)
            with pytest.raises(ValueError, match='null blocks publication'):
                evolution.resume_round(root, generate=provider)
        else:
            assert evolution.run_round(root, config=cfg, generate=provider)['outcome'] == outcome
    rounds = memory.load_memory(root / 'memory')['memory']['rounds']
    assert len(rounds) == (1 if mode == 'empty' else 0)
    assert len(actor.requests) == 11
    assert not (root / 'rounds/R01/candidate_runs').exists()


def test_eleven_cited_runs_replace_and_unattributed_transition(tmp_path):
    method, actor, cfg = synthetic_method(tmp_path)
    root = tmp_path / 'campaign'
    provider = MethodProvider('candidate')
    actor.scripts[cfg['batches'][0][0]] = [response('0'), response('1000')]
    text = 'Verify operand roles when the table header is ambiguous.'

    def generate(name, messages, directory, call_config):
        result = provider(name, messages, directory, call_config)
        value = json.loads(result['content'])
        if name == 'diagnosis':
            value['plan']['updates'][0]['basis'] = [f'P{i}:1' for i in range(1, 12)]
        elif name == 'preconditioner':
            payload = restore_model_input(json.loads(messages[1]['content']), module=name)
            assert len(payload['runs']) == 11
            if directory.name == '001':
                value['adjustments'][0]['action'] = 'UNKNOWN'
            else:
                assert directory.name == '002' and len(messages) == 4
                value['adjustments'][0].update(action='REPLACE', text=text)
        elif name == 'editor':
            assert json.loads(messages[1]['content'])['plan']['updates'] == [{'id': 'u1', 'text': text}]
        elif name == 'replay':
            value['entries'][0]['knowledge'][0]['update_id'] = None
        return {**result, 'content': json.dumps(value)}

    with method.using():
        result = evolution.run_round(root, config=cfg, generate=generate)
    assert result['selected_execution_source'] == 'parent'
    gate = evolution.read(root / 'rounds/R01/gate/result.json')
    assert gate['decisions'] == [dict(update_id='u1', G=0, L=0, gate_decision='Defer')]
    entries = memory.load_memory(root / 'memory')['memory']['rounds'][0]['entries']
    assert len(entries) == 1 and entries[0]['knowledge']['update_id'] is None


def test_eleven_long_inputs_respect_frozen_capacity(tmp_path):
    from src.skill_evolution.v27.capacity import account

    method, _, cfg = synthetic_method(tmp_path)
    tasks = cfg['batches'][0]
    with method.using():
        records = batch(method, tmp_path / 'parent', tasks=tasks)
        call = diagnosis.diagnosis_call(facts.build_parent_bundle(records, 'current'))
        basis = [f'P{i}:1' for i in range(1, 12)]
        saved = call.complete({'decision': 'revise', 'reason': 'Compare runs', 'plan': {
            'goal': 'Verify evidence', 'updates': [{'id': 'u1', 'text': 'Verify operands', 'basis': basis}]}})

        # Use the real 11-run input projection and full-size synthetic Memory.
        def measure(filler):
            entries = [{'id': f'M{i}', 'knowledge': {'task_id': uid, 'update_id': None, 'text': filler}}
                       for i, uid in enumerate(tasks, 1)]
            history = {'rounds': [{'round_id': 'previous', 'source_updates': [], 'entries': entries}]}
            messages = preconditioner.preconditioner_call(saved, history).messages
            payload = restore_model_input(json.loads(messages[1]['content']), module='preconditioner')
            assert len(payload['runs']) == 11 and payload['memory'] == history
            return account(messages, cfg['module_calls']['preconditioner'],
                           max_input_chars=cfg['max_input_chars'],
                           max_message_utf8_bytes=cfg['max_message_utf8_bytes'])

        amount = measure('数' * 175000)
        assert 5_700_000 < amount['input_utf8_bytes'] <= 6_000_000
        assert amount['reserved_output_tokens'] == 32768
        for filler in ('数' * 190000, 'x' * 370000):
            with pytest.raises(ValueError, match='capacity'):
                measure(filler)


def test_v26_1_checkpoint_rejected_before_execution(tmp_path):
    from src.skill_evolution.v26_1 import evolution as old_evolution

    old, actor, old_cfg = make(tmp_path / 'fixture', full=True)
    root = tmp_path / 'campaign'
    with old.using():
        old_evolution.initialize(root, old_cfg)
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    old.dataset.batches = deepcopy(protocol.PLAN['schedule']['batches'])
    method = CampaignAdapter(old.dataset, Runtime(old.runtime.parsed_root), old.transport,
                             task_transports={k: v.transport for k, v in old.task_adapters.items()})
    provider = MethodProvider()
    with method.using(), pytest.raises(ValueError, match='Frozen value changed'):
        evolution.run_campaign(root, config=config.campaign_config(method), resume=True, generate=provider)
    assert {p: p.read_bytes() for p in root.rglob('*') if p.is_file()} == before
    assert not actor.requests and not provider.calls
