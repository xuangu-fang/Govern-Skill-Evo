from copy import deepcopy
import json
import socket
from threading import Lock

import pytest

from src.adapters.officeqa.data import Dataset, PROFILE
from src.adapters.officeqa.runtime import Runtime
from src.adapters.officeqa.transport import ChatTransport
from src.skill_evolution.v26.benchmarks.officeqa.adapter import OfficeQAEvidenceAdapter


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('Network and provider clients are forbidden in V26 offline tests')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)
    import requests, openai
    monkeypatch.setattr(requests.Session, 'request', deny)
    monkeypatch.setattr(openai, 'OpenAI', deny)
    monkeypatch.setattr(openai, 'AzureOpenAI', deny)
    monkeypatch.setattr('src.adapters.officeqa.retry.retry_wait', lambda _: None)


def response(text=None, calls=()):
    return {'choices': [{'finish_reason': 'tool_calls' if calls else 'stop', 'message': {
        'content': text, 'tool_calls': [{'id': f'call_{i}', 'type': 'function', 'function': {
            'name': name, 'arguments': json.dumps(args)}} for i, (name, args) in enumerate(calls)]}}],
        'usage': {'prompt_tokens': 100, 'completion_tokens': 10, 'total_tokens': 110}}


class Provider:
    def __init__(self, scripts):
        self.scripts = {key: iter(deepcopy(value)) for key, value in scripts.items()}
        self.requests = []; self.lock = Lock()

    def __call__(self, **body):
        encoded = json.dumps(body['messages'])
        with self.lock:
            uid = next(key for key in self.scripts if f'Question for {key}?' in encoded)
            self.requests.append(deepcopy(body)); value = next(self.scripts[uid])
        if isinstance(value, BaseException): raise value
        return value() if callable(value) else value


@pytest.fixture
def office(tmp_path):
    parsed = tmp_path / 'raw/treasury_bulletins_parsed'
    (parsed / 'transformed').mkdir(parents=True); (parsed / 'jsons').mkdir()
    name = 'treasury_bulletin_2011_03.txt'
    (parsed / 'transformed' / name).write_text('Revenue 1000\nOther line\n' * 500)
    (parsed / 'jsons' / name.replace('.txt', '.json')).write_text(json.dumps({'document': {'elements': [
        {'bbox': [{'page_id': 2}], 'content': 'Visible source page 2: revenue 1000.'},
        {'bbox': [{'page_id': 3}], 'content': 'UNOBSERVED_PAGE_SENTINEL'}]}}))
    prepared = tmp_path / 'prepared'; splits = {'train': ['a', 'b'], 'val': ['v'], 'test': ['t']}
    for split, ids in splits.items():
        (prepared / split).mkdir(parents=True)
        rows = [{'id': uid, 'uid': uid, 'question': f'Question for {uid}?',
                 'ground_truth': 'GOLD_ONLY_SENTINEL', 'answers': ['1000', 'GOLD_ONLY_SENTINEL'],
                 'category': 'synthetic', 'task_type': 'officeqa', 'split': split,
                 'source_files': [name], 'source_docs': [
                     'https://fraser.stlouisfed.org/title/treasury-bulletin-407/march-2011-7147?page=2']} for uid in ids]
        (prepared / split / 'items.json').write_text(json.dumps(rows))
    (prepared / 'manifest.json').write_text(json.dumps({'profile': PROFILE, 'splits': splits}))
    dataset, runtime = Dataset(prepared), Runtime(parsed)

    def factory(scripts, **kwargs):
        provider = Provider(scripts)
        actor = ChatTransport(offline_create=provider, model='offline-fixture', max_completion_tokens=1234)
        return OfficeQAEvidenceAdapter(dataset, runtime, actor, **kwargs), provider
    return tmp_path, dataset, runtime, factory


@pytest.fixture
def make_run(office):
    root, _, _, factory = office; count = 0

    def run(responses=None, *, role='parent', task='a', split='train', skill='Parent\n'):
        nonlocal count
        count += 1; folder = root / f'run{count}'; skill_file = root / f'skill{count}.md'
        if skill is not None: skill_file.write_text(skill)
        adapter, provider = factory({task: responses or [response('1000')]})
        records = adapter.actor_batch([task], skill_file if skill is not None else None, folder,
                                      {'split': split, 'role': role}, final=role == 'evaluation')
        return records[0], adapter, provider, folder
    return run


@pytest.fixture
def make_bundle(make_run):
    from src.skill_evolution.v26.benchmark import using_benchmark
    from src.skill_evolution.v26.contracts.editor import actual_diff
    from src.skill_evolution.v26.benchmarks.officeqa import facts, evidence

    def make(*, memory=None, two=False, parent_answer='0', candidate_answer='1000'):
        parent = []; candidate = []; adapter = None
        for task in (['a', 'b'] if two else ['a']):
            tools = response(calls=[('glob', {'pattern': '*'}), ('glob', {'pattern': '*.txt'})])
            record, adapter, _, _ = make_run([tools, response(parent_answer)], task=task)
            parent.append(record)
            record, _, _, _ = make_run([tools, response(candidate_answer)], role='candidate', task=task, skill='Candidate\n')
            candidate.append(record)
        candidate.reverse()
        saved = {**facts.build_facts(parent), 'editor_status': 'candidate', 'candidate_text': 'Candidate\n',
                 'actual_diff': actual_diff('Parent\n', 'Candidate\n'),
                 'effective_plan': {'goal': 'Check the supplied document.',
                                    'updates': [{'id': 'U1', 'text': 'Read relevant evidence.'}], 'checks': []}}
        with using_benchmark(adapter):
            bundle = evidence.build_replay_from_editor(saved, 'offline-editor-handoff', parent, candidate, memory=memory)
        return bundle, adapter, parent, candidate
    return make
