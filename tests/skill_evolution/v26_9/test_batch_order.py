import json

from src.adapters.officeqa import execution
from src.adapters.officeqa.runtime import Runtime
from src.skill_evolution.v26_9.campaign import CampaignAdapter
from tests.skill_evolution.v26_1.conftest import offline_only
from tests.skill_evolution.v26_1.support import batch, make


def test_parent_refs_follow_schedule_across_resume(tmp_path, monkeypatch):
    fixture, provider, _ = make(tmp_path / 'fixture')
    method = CampaignAdapter(fixture.dataset, Runtime(fixture.runtime.parsed_root), fixture.transport,
                             task_transports={'UID0007': fixture.task_adapters['UID0007'].transport})
    tasks = ['c', 'a']  # Neither lexical order nor completion order.
    monkeypatch.setattr(execution, 'as_completed', lambda futures: reversed(list(futures)))
    root = tmp_path / 'parent'
    with method.using():
        records = batch(method, root, tasks=tasks)
        journal = root / 'runs/actor/results.jsonl'
        original = journal.read_bytes()
        assert [json.loads(line)['id'] for line in original.splitlines()] == ['a', 'c']
        assert [r['task_id'] for r in records] == tasks
        resumed = batch(method, root, tasks=tasks)
        assert resumed == records and journal.read_bytes() == original
        assert len(provider.requests) == 2
        runs = method.build_facts(resumed)['facts']['runs']
        assert [(r['ref'], r['task_id']) for r in runs] == [('P1', 'c'), ('P2', 'a')]
