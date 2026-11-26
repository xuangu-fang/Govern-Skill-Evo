"""No models: scripted responses exercise the actual three Actor entry points."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest
from skilladam.backends import openai_compatible as native
from skilladam.benchmarks.officeqa.adapter import OfficeQAAdapter as NativeAdapter
from skilladam.execution.contracts import BackendContext, BackendInit, BatchExecution

from src.adapters.officeqa.bridges import GovernActor, SkillAdamAdapter, SkillAdamBackend, SkillOptAdapter
from src.adapters.officeqa.data import Dataset, PROFILE, split_source_urls
from src.adapters.officeqa.runtime import ChatTransport, Runtime


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('Network/provider clients forbidden in offline tests')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)
    import openai
    monkeypatch.setattr(openai, 'OpenAI', denied)
    monkeypatch.setattr(openai, 'AzureOpenAI', denied)
    monkeypatch.setattr('src.adapters.officeqa.retry.retry_wait', lambda _: None)


def response(text=None, calls=()):
    return {'choices': [{'finish_reason': 'tool_calls' if calls else 'stop', 'message': {'content': text, 'tool_calls': [
        {'id': f'call_{i}', 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}}
        for i, (name, args) in enumerate(calls)]}}],
        'usage': {'prompt_tokens': 100, 'completion_tokens': 10, 'total_tokens': 110}}


class ScriptedProvider:
    def __init__(self, responses):
        self.responses = iter(deepcopy(responses))
        self.bodies = []

    def __call__(self, **body):
        self.bodies.append(deepcopy(body))
        return next(self.responses)


@pytest.fixture
def fixture(tmp_path):
    parsed = tmp_path / 'raw/treasury_bulletins_parsed'
    (parsed / 'transformed').mkdir(parents=True)
    (parsed / 'jsons').mkdir()
    name = 'treasury_bulletin_2011_03.txt'
    (parsed / 'transformed' / name).write_text('MiXeD [literal] evidence\n' * 1000)
    (parsed / 'jsons' / name.replace('.txt', '.json')).write_text(json.dumps({'document': {'elements': [
        {'bbox': [{'page_id': 2}], 'content': 'Synthetic page evidence. <table><tr><td>A</td></tr></table>'}]}}))
    row = {'id': 'fixture', 'uid': 'fixture', 'question': 'Synthetic question?', 'ground_truth': '1000',
           'answers': ['1000'], 'category': 'synthetic', 'task_type': 'officeqa', 'split': 'train',
           'source_files': [name], 'source_docs': [
               'https://fraser.stlouisfed.org/title/treasury-bulletin-407/march-2011-7147?page=2']}
    prepared = tmp_path / 'prepared'
    for split in ('train', 'val', 'test'):
        (prepared / split).mkdir(parents=True)
        (prepared / split / 'items.json').write_text(json.dumps([row] if split == 'train' else []))
    (prepared / 'manifest.json').write_text(json.dumps({'profile': PROFILE,
        'splits': {'train': ['fixture'], 'val': [], 'test': []}}))
    return Dataset(prepared), Runtime(parsed), tmp_path


def invoke(owner, fixture, provider, *, limit=1234, skill='Shared test Skill'):
    dataset, runtime, root = fixture
    transport = ChatTransport(offline_create=provider, model='offline-fixture', max_completion_tokens=limit)
    if owner == 'govern':
        skill_path = root / 'skill.md'
        skill_path.write_text(skill)
        adapter = GovernActor(dataset, runtime, transport)
        path = adapter.actor_task('fixture', skill_path, root / owner, {'split': 'train'})
        return adapter.check_record(json.loads(path.read_text()), 'fixture', skill, {'split': 'train'})
    if owner == 'skillopt':
        adapter = SkillOptAdapter(dataset, runtime, transport)
        adapter.setup({})
        rows = adapter.rollout(adapter.get_dataloader().train_items, skill, root / owner)
        assert rows[0]['hard'] == rows[0]['aligned_record']['metrics']['em']
        return rows[0]['aligned_record']
    adapter = SkillAdamAdapter(dataset)
    case = adapter.load_cases('train')[0]
    request = adapter.build_rollout_request(case, method='skilladam', split='train', skill=skill, seed=42)
    context = BackendContext('officeqa', 'skilladam', 'offline-fixture', 'none', 1, 42)
    result = SkillAdamBackend(dataset, runtime, transport, output_dir=root/owner).execute_batch(BatchExecution((request,), context, 'offline'))[0]
    parsed = adapter.parse_result(case, result.result)
    assert adapter.evaluate(parsed).metrics == result.result['aligned_record']['metrics']
    return result.result['aligned_record']


@pytest.mark.parametrize('kind', ['comma', 'newline', 'json', 'mixed'])
def test_split_independent_urls(kind):
    urls = [f'https://example.com/{i}?page={i}' for i in range(1, 4)]
    value = {'comma': ', '.join(urls), 'newline': '\n'.join(urls), 'json': json.dumps(urls),
             'mixed': urls[0] + ', ' + urls[1] + '\n' + urls[2]}[kind]
    assert split_source_urls(value) == urls


@pytest.mark.parametrize('owner', ['govern', 'skillopt', 'skilladam'])
def test_all_bridges_allow_more_than_8_and_96_tools(fixture, owner):
    provider = ScriptedProvider([response(calls=[('glob', {'pattern': '*.txt'})] * 10)] * 10
                                + [response('<answer>1,000</answer>')])
    result = invoke(owner, fixture, provider)
    assert result['raw_result']['n_tool_calls'] == 100
    assert result['raw_result']['n_turns'] == 11
    assert result['metrics'] == {'em': 1.0, 'f1': 1.0}
    assert len([m for m in provider.bodies[-1]['messages'] if m['role'] == 'tool']) == 100
    if owner == 'skillopt':
        conversation = json.loads((fixture[2]/'skillopt/predictions/fixture/conversation.json').read_text())
        assert len([m for m in conversation if m.get('type') == 'tool_call']) == 100
        assert all('glob(' in m['cmd'] and '.txt' in m['obs']
                   for m in conversation if m.get('type') == 'tool_call')


def test_three_entry_points_have_identical_requests_and_per_method_output_limits(fixture):
    bodies, records = [], []
    for owner, limit in [('govern', 1111), ('skillopt', 2222), ('skilladam', 3333)]:
        provider = ScriptedProvider([response(calls=[('glob', {'pattern': '*.txt'})]), response('1,000')])
        record = invoke(owner, fixture, provider, limit=limit)
        assert record['actor']['max_completion_tokens'] == limit
        assert all(body.pop('max_completion_tokens') == limit for body in provider.bodies)
        bodies.append(provider.bodies); records.append(record)
    assert bodies[0] == bodies[1] == bodies[2]
    assert all(record['answer'] == '1,000' and record['metrics']['em'] == 1 for record in records)


def test_runtime_matches_native_skilladam_below_old_caps(fixture):
    dataset, runtime, root = fixture
    case = dataset.case('fixture')
    file = str(runtime.text_root / case.payload['source_files'][0])
    turns = [response(calls=[('read', {'path': file, 'start': 'bad'})]),
             response(calls=[('grep', {'path': file, 'pattern': '[LITERAL]'})]),
             response('Working done\n<answer>1,000</answer>')]
    reference = ScriptedProvider(turns)
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=reference)))
    context = BackendContext('officeqa', 'skilladam', 'offline-fixture', 'none', 1, 42)
    config = native.OpenAICompatibleConfig.from_mapping({'max_completion_tokens': 1234})
    backend = native.OpenAICompatibleBackend(init=BackendInit(root, root/'native', {}, context),
        config=config, client=client, environ={}, alfworld_environment_factory=None,
        spreadsheet_sandbox=None, spreadsheet_workbook_evaluator=None, spreadsheet_preview_factory=None)
    adapter = NativeAdapter(root)
    request = adapter.build_rollout_request(case, method='skilladam', split='train', skill='Shared test Skill', seed=42)
    expected = backend.execute_batch(BatchExecution((request,), context, 'offline'))[0].result
    provider = ScriptedProvider(turns)
    actual = invoke('skilladam', fixture, provider)
    assert all(body.pop('timeout') == 300 for body in provider.bodies)
    assert reference.bodies == provider.bodies
    assert actual['raw_result']['response'] == expected['response']
    assert actual['raw_result']['n_tool_calls'] == expected['n_tool_calls']
    # Frozen native containers and ordinary shared containers encode identically.
    assert actual['metrics'] == adapter.evaluate(adapter.parse_result(case, expected)).metrics
    assert 'invalid line window' in provider.bodies[1]['messages'][-1]['content']
    assert len(provider.bodies[2]['messages'][-1]['content'].splitlines()) == 20


def test_24_round_exhaustion_is_empty_answer_and_no_bonus_round(fixture):
    dataset, runtime, _ = fixture
    provider = ScriptedProvider([response(calls=[('glob', {'pattern': '*'})])] * 24)
    transport = ChatTransport(offline_create=provider, model='offline-fixture', max_completion_tokens=1234)
    record = runtime.run(dataset.case('fixture'), None, transport, owner='govern', directory=fixture[2]/'direct')
    assert len(provider.bodies) == record['raw_result']['n_turns'] == 24
    assert record['raw_result']['termination_reason'] == 'max_tool_turns'
    assert record['answer'] == '' and record['metrics']['em'] == 0


def test_gold_fields_do_not_enter_messages_and_no_initial_skill_is_invented(fixture):
    dataset, runtime, _ = fixture
    case = dataset.case('fixture')
    changed = replace(case, reference=['SECRET_GOLD_SENTINEL'], metadata={'raw_answer': 'SECRET_GOLD_SENTINEL'})
    assert runtime.prepare(case, None) == runtime.prepare(changed, None)
    messages, _ = runtime.prepare(changed, None)
    assert 'SECRET_GOLD_SENTINEL' not in json.dumps(messages)
    assert '## Skill' not in messages[0]['content']


@pytest.mark.parametrize('value', [None, 0, -1, True])
def test_output_limit_must_be_explicit_positive(value):
    with pytest.raises(ValueError):
        ChatTransport(offline_create=lambda **kw: None, model='fixture', max_completion_tokens=value)


def test_missing_source_empty_allowlist_and_symlink_escape_fail(fixture):
    dataset, runtime, root = fixture
    case = dataset.case('fixture')
    with pytest.raises(ValueError):
        runtime.prepare(replace(case, payload={**case.payload, 'source_files': []}), None)
    path = runtime.text_root / case.payload['source_files'][0]
    path.unlink()
    with pytest.raises(ValueError): runtime.prepare(case, None)
    outside = root / 'outside.txt'; outside.write_text('outside')
    path.symlink_to(outside)
    with pytest.raises(ValueError): runtime.prepare(case, None)


@pytest.mark.parametrize('bad', [response(''), {'choices': []}, response(calls=[('read', {})])])
def test_malformed_responses_and_disallowed_files(fixture, bad):
    dataset, runtime, root = fixture
    if bad == response(calls=[('read', {})]):
        bad['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = '{bad json'
    provider = ScriptedProvider([bad] * 6)
    from src.adapters.officeqa.retry import GenerationExhausted
    with pytest.raises(GenerationExhausted):
        runtime.run(dataset.case('fixture'), None,
            ChatTransport(offline_create=provider, model='fixture', max_completion_tokens=1234), owner='govern', directory=fixture[2]/'direct')


def test_tool_scope_read_truncation_and_error_recovery(fixture):
    dataset, runtime, root = fixture
    name = dataset.case('fixture').payload['source_files'][0]
    provider = ScriptedProvider([response(calls=[
        ('read', {'path': str(root/'answers.csv')}),
        ('read', {'path': str(runtime.text_root/name), 'limit': 1000}),
        ('read', {'path': str(runtime.text_root/'missing.txt')}),
    ]), response('<answer>1000</answer>')])
    invoke('govern', fixture, provider)
    outputs = [m['content'] for m in provider.bodies[-1]['messages'] if m['role'] == 'tool']
    assert 'path not allowed' in outputs[0] and len(outputs[1]) == 4000
    assert 'path not allowed' in outputs[2]


def test_govern_cannot_run_test_as_training_or_invent_a_skill(fixture):
    dataset, runtime, root = fixture
    provider = ScriptedProvider([response('1000')])
    actor = GovernActor(dataset, runtime, ChatTransport(offline_create=provider, model='fixture', max_completion_tokens=1234))
    with pytest.raises(ValueError):
        actor.actor_task('fixture', None, root/'denied', {'split': 'test'})
    assert not provider.bodies
    path = actor.actor_task('fixture', None, root/'no-skill', {'split': 'train'})
    assert json.loads(path.read_text())['skill'] is None
    assert '## Skill' not in provider.bodies[0]['messages'][0]['content']


def test_skilladam_environment_has_no_implicit_optimizer_or_stage0(fixture):
    dataset, runtime, _ = fixture
    provider = ScriptedProvider([])
    backend = SkillAdamBackend(dataset, runtime, ChatTransport(offline_create=provider, model='fixture', max_completion_tokens=1234),
                               output_dir=fixture[2]/'skilladam')
    with pytest.raises(RuntimeError, match='No optimizer configured'):
        backend.generate(None)
    assert not provider.bodies and backend.public_metadata()['stage0'] is False
