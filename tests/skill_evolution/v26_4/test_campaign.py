"""Offline v26.4 acceptance using the production entry points and synthetic runs."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from scripts.runs import run_v26_3_campaign as previous_cli
from scripts.runs import run_v26_4_campaign as cli
from src.adapters.officeqa.runtime import Runtime
from src.adapters.officeqa.transport import ChatTransport
from src.skill_evolution.v26_4 import config, evolution, memory, protocol
from src.skill_evolution.v26_4.execution_input_view import restore_model_input
from tests.skill_evolution.v26_1.conftest import offline_only
from tests.skill_evolution.v26_1.support import MethodProvider, make, response

CONFIG = protocol.ROOT / 'experiments/configs/v26_4_officeqa_train74.json'
HASHES = {
    'diagnosis': '4e9c2875fff217d242833cac7a5589776e06d94e54d0fb8ae3b3ad3c0bc6bd0f',
    'preconditioner': 'f4f1d078c8b7d2812e18a7b68a61b4a99a0afe18ed238e03c2f434be8548815e',
    'editor': 'cb16d3045e4995ba2d5df6537bd6873c75dd60dc389571855419ca54d446df85',
    'replay': 'b68102bc029e8b123a6a214f2eaa22e7f5ad23b612f6d0fc667d18a2acdc84b5',
}


def test_production_config_and_readonly_preflight(tmp_path, monkeypatch, capsys):
    cfg = evolution.read(CONFIG)
    prior = deepcopy(cfg)
    prior['method']['version'] = 'v26_3_campaign_v1'
    prior['method']['prompts'].update(diagnosis='v26_1_officeqa_diagnosis_v1',
                                     preconditioner='v26_3_officeqa_preconditioner_v1',
                                     editor='v26_1_officeqa_editor_v1', replay='v26_1_officeqa_replay_v1')
    # Canonical digest of the actual v26.3 train74 config, independent of mutable defaults.
    assert protocol.digest(prior) == '8e32c8a791f78ddb987487a6e400eb56d70461a8426e540370f621f05faa1129'
    assert {name: sha256(text.encode()).hexdigest() for name, text in config.render_prompts().items()} == HASHES
    with cli.bind(cfg).using():
        for stage in HASHES:
            stale = deepcopy(cfg)
            stale['method']['prompts'][stage] = prior['method']['prompts'][stage]
            with pytest.raises(ValueError):
                config.validate_config(stale)

    def forbidden(*args, **kwargs):
        pytest.fail('Read-only preflight entered execution')
    for name in ('ChatTransport', 'HTTPGenerator', 'run_training', 'run_test'):
        monkeypatch.setattr(cli, name, forbidden)
    target = tmp_path / 'absent'
    cli.main(['train', str(target), '--config', str(CONFIG), '--validate-only'])
    assert json.loads(capsys.readouterr().out) == {
        'status': 'valid', 'method': 'v26_4_campaign_v1', 'optimization_count': 74, 'test_count': 172,
        'batch_sizes': [11, 11, 11, 11, 10, 10, 10], 'model_requests': 0,
        'training_started': False, 'test_started': False,
    }
    assert not target.exists()


@pytest.mark.parametrize('stage', HASHES)
def test_changed_reviewed_text_is_rejected(stage, monkeypatch):
    monkeypatch.setattr(protocol.previous, 'render_prompt', lambda path, value: path.read_text() + 'drift')
    with pytest.raises(ValueError, match='Approved v26.4'):
        config.MODULES[stage].render_prompt(protocol.expected_background())


def test_fixed_prompts_preserve_evidence_and_scoring_without_case_hints():
    prompts = config.render_prompts()
    for prompt in prompts.values():
        for hint in ('UID0007', '65,536', 'tenders received', 'amount-vs-percent',
                     'sample std dev', '32nds quotation', 'Watch for sign errors',
                     'retrieval_miss', 'percent convention', 'period-selection rule'):
            assert hint not in prompt
        assert 'Parent and Candidate runs use the same per-request output limit' in prompt
    for stage in ('diagnosis', 'preconditioner', 'replay'):
        original = (protocol.previous.PROMPT_ROOT / f'{stage}.md').read_text()
        scorer = next(p for p in original.split('\n\n') if p.startswith('The native response path'))
        assert scorer in prompts[stage]
    assert 'This Editor receives only the complete Parent and Effective Plan.' in prompts['editor']
    assert 'Identify which observed differences survive normalization.' in prompts['replay']


def test_v26_3_checkpoint_isolated(tmp_path):
    cfg = evolution.read(CONFIG.with_name('v26_3_officeqa_train74.json'))
    root = tmp_path / 'old'
    with previous_cli.bind(cfg).using():
        previous_cli.ev.initialize(root, cfg)
    original = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    provider = MethodProvider()
    with cli.bind(evolution.read(CONFIG)).using(), pytest.raises(ValueError):
        evolution.run_campaign(root, resume=True, generate=provider)
    assert not provider.calls
    assert original == {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_seven_round_handoff_reporting_and_independent_test(tmp_path):
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
    first = cfg['batches'][0]
    actor.scripts = {first[0]: [response('1000 items'), response('1000')],
                     first[1]: [response('1000 units'), response('1000')]}
    provider = MethodProvider('candidate')
    correction = 'Copy the checked value into the answer with only the label the question requests.'
    evidence = []

    def generate(name, messages, directory, call_config):
        assert sha256(messages[0]['content'].encode()).hexdigest() == HASHES[name]
        assert call_config == cfg['module_calls'][name]
        result = provider(name, messages, directory, call_config)
        value = json.loads(result['content'])
        round_id = directory.parents[2].name
        if name == 'diagnosis' and round_id == 'R01':
            payload = restore_model_input(json.loads(messages[1]['content']), module=name)
            refs = {r['task_id']: r['ref'] for r in payload['runs']}
            evidence.extend(refs[uid] + ':outcome' for uid in first[:3])
            value['plan']['updates'] = [
                {'id': 'u1', 'text': 'Use only the requested answer label.', 'basis': evidence},
                {'id': 'u2', 'text': 'Copy the checked value into the answer.', 'basis': evidence[:1]},
            ]
        elif name == 'diagnosis' and round_id != 'R02':
            value = {'decision': 'no_change', 'plan': None, 'reason': 'No new decision to correct.'}
        elif name == 'preconditioner':
            if round_id == 'R01':
                payload = restore_model_input(json.loads(messages[1]['content']), module=name)
                assert {r['task_id'] for r in payload['runs']} == set(first[:3])
                assert payload['plan']['updates'][0]['basis'] == evidence
                value['adjustments'] = [
                    {'target': 'u1', 'action': 'REPLACE', 'text': correction, 'reason': 'Clarify the existing rule.'},
                    {'target': 'u2', 'action': 'WITHDRAW', 'text': None, 'reason': 'Parent already covers it.'},
                ]
            else:
                value['adjustments'][0]['action'] = 'WITHDRAW'
        elif name == 'editor':
            payload = json.loads(messages[1]['content'])
            assert payload['plan']['updates'] == [{'id': 'u1', 'text': correction}]
            old = payload['parent'].splitlines()[-1]
            value['edits'][0]['patch'] = f'--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-{old}\n+- {correction}\n'
        return {**result, 'content': json.dumps(value)}

    root, output = tmp_path / 'campaign', tmp_path / 'evaluation'
    with method.using():
        def interrupt(point):
            if point == 'after_memory_commit':
                raise KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            evolution.run_round(root, config=cfg, generate=generate, hook=interrupt)
        counts = len(actor.requests), len(provider.calls)
        evolution.resume_round(root)
        assert counts == (len(actor.requests), len(provider.calls)) == (22, 4)
        summary = cli.run_training(root, cfg, generate=generate, resume=True)
        assert summary['method'] == protocol.METHOD_VERSION and summary['rounds_completed'] == 7
        assert not summary['test_started'] and not output.exists()
        assert len(actor.requests) == 74 + 11
        for req in actor.requests:
            override = 'Question for UID0007?' in json.dumps(req['messages'])
            assert req['max_tokens'] == (65536 if override else 32768)
            assert req['model'] == 'deepseek-v4.1-flash'
        rows = summary['rounds']
        assert rows[0]['updates'] == [{'update_id': 'u1', 'G': 2, 'L': 0, 'gate_decision': 'Retain'}]
        assert rows[1]['outcome'] == 'preconditioner_withdrawn'
        assert all(row['outcome'] == 'diagnosis_no_change' for row in rows[2:])
        for stage in HASHES:
            identity = evolution.read(root / 'rounds/R01' / stage / 'identity.json')
            assert identity['prompt'] == cfg['method']['prompts'][stage]
        selected = (root / 'final_skill.md').read_text()
        assert correction in selected
        for row in rows:
            archived = evolution.read(root / 'rounds' / row['round'] / 'round_summary.json')
            assert row == archived
            assert row['selected_skill_chars'] == len(selected)
            assert row['selected_skill_bullets'] == sum(line.startswith('- ') for line in selected.splitlines())
        prior = memory.load_memory(root / 'memory')
        actor.scripts[dataset.splits['test'][-1]] = [KeyboardInterrupt()]
        with pytest.raises(KeyboardInterrupt):
            cli.run_test(root, output)
        partial = evolution.read(output / 'incomplete.json')
        assert partial['em'] is None and partial['f1'] is None
        assert partial['correct'] == partial['completed'] < 172 and partial['pending']
        report = cli.run_test(root, output, resume=True)
        assert report['method'] == protocol.METHOD_VERSION and report['completed'] == report['correct'] == 172
        assert all(req['max_tokens'] == 32768 for req in actor.requests[85:])
        assert (root / 'final_skill.md').read_bytes() == (output / 'skill.md').read_bytes()
        assert memory.load_memory(root / 'memory') == prior
