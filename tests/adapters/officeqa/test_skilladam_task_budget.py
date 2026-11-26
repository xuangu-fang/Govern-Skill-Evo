"""Task budget dispatch over the unchanged real Actor with offline responses."""
import json
from pathlib import Path
import socket
from concurrent.futures import ThreadPoolExecutor

import pytest

from scripts.runs import run_officeqa_skilladam_task_budget as entry
from src.adapters.officeqa.transport import ChatTransport
from src.skill_evolution.v26.training import load_dataset

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / 'experiments/configs/officeqa_skilladam_train74_epoch1_deepseek_flash_uid0007_64k.json'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*a, **k): raise AssertionError('Live network forbidden')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr('src.adapters.officeqa.retry.retry_wait', lambda _: None)


def answer():
    return {'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant',
        'content': '<answer>1000</answer>', 'reasoning_content': 'offline thinking'}}],
        'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}}


def dependencies(provider):
    cfg = entry.launch.read(CONFIG)
    dataset = load_dataset(cfg['prepared_root'], 'officeqa_train50_validation24_v1')
    runtime = entry.TaskBudgetRuntime(cfg['parsed_root'], cfg['actor_task_output_limits'])
    transport = ChatTransport(model='deepseek-flash', max_completion_tokens=32768,
        reasoning_effort='medium', reasoning_mode='deepseek_thinking', token_limit_field='max_tokens',
        offline_create=provider)
    return dataset, runtime, transport


def test_parallel_parent_candidate_and_other_tasks_have_exact_wire_budgets(tmp_path):
    requests = []
    def provider(**body):
        requests.append(body)
        return answer()
    dataset, runtime, transport = dependencies(provider)
    jobs = [('UID0007', 'Parent'), ('UID0007', 'Candidate'),
            ('UID0002', 'Parent'), ('UID0030', 'Candidate')]
    def execute(item):
        uid, skill = item
        return runtime.run(dataset.case(uid), skill, transport, owner='skilladam', directory=tmp_path / f'{uid}_{skill}')
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(execute, jobs))
    assert sorted(body['max_tokens'] for body in requests) == [32768, 32768, 65536, 65536]
    assert all(body['thinking'] == {'type': 'enabled'} for body in requests)
    for (uid, skill), record in zip(jobs, records):
        assert record['actor']['max_completion_tokens'] == (65536 if uid == 'UID0007' else 32768)
        assert record['skill'] == skill
    assert transport.metadata()['max_completion_tokens'] == 32768
    for job in jobs: execute(job)
    assert len(requests) == 4  # Completed identities are reused without new requests.


def test_unchanged_task_keeps_interrupted_attempt_on_resume(tmp_path):
    calls = []
    def provider(**body):
        calls.append(body)
        if len(calls) == 1: raise KeyboardInterrupt('offline interruption')
        return answer()
    dataset, runtime, transport = dependencies(provider)
    case = dataset.case('UID0030')
    with pytest.raises(KeyboardInterrupt):
        runtime.run(case, 'Parent', transport, owner='skilladam', directory=tmp_path)
    result = runtime.run(case, 'Parent', transport, owner='skilladam', directory=tmp_path)
    attempts = result['request_audit'][0]['attempts']
    assert [a['status'] for a in attempts] == ['interrupted', 'accepted']
    assert [a['number'] for a in attempts] == [1, 2]
    assert all(body['max_tokens'] == 32768 for body in calls)


def test_uid0007_cannot_resume_a_prior_32768_execution_in_place(tmp_path):
    dataset, runtime, transport = dependencies(lambda **body: answer())
    case = dataset.case('UID0007')
    entry.Runtime(runtime.parsed_root).run(case, 'Parent', transport, owner='skilladam', directory=tmp_path)
    before = (tmp_path / 'actor_state.json').read_bytes()
    with pytest.raises(ValueError, match='identity differs'):
        runtime.run(case, 'Parent', transport, owner='skilladam', directory=tmp_path)
    assert (tmp_path / 'actor_state.json').read_bytes() == before


def test_new_config_changes_only_task_dispatch_identity():
    new = entry.launch.read(CONFIG)
    old = entry.launch.read(ROOT / 'experiments/configs/officeqa_skilladam_train74_epoch1_deepseek_flash.json')
    assert new['actor_task_output_limits'] == {'UID0007': 65536}
    for key in ('actor_task_output_limits', 'base_launcher_sha256', 'launch_adapter'): new.pop(key)
    old.pop('launch_adapter')
    assert new == old


def test_larger_output_budget_still_has_six_attempts_without_resume_refill(tmp_path):
    from src.adapters.officeqa.retry import GenerationExhausted
    calls = []
    def truncated(**body):
        calls.append(body)
        result = answer(); result['choices'][0]['finish_reason'] = 'length'
        return result
    dataset, runtime, transport = dependencies(truncated)
    for _ in range(2):
        with pytest.raises(GenerationExhausted):
            runtime.run(dataset.case('UID0007'), 'Parent', transport,
                        owner='skilladam', directory=tmp_path)
    assert len(calls) == 6
    assert all(body['max_tokens'] == 65536 for body in calls)
