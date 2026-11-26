from copy import deepcopy
import json
import pytest

from scripts.runs import continue_v26_uid0007 as continuation
from src.adapters.officeqa.transport import ChatTransport
from src.skill_evolution.v26.benchmarks.officeqa.adapter import OfficeQAEvidenceAdapter
from src.skill_evolution.v26.benchmarks.officeqa import protocol as p, evidence
from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26 import evolution as ev
from .conftest import Provider, response
from .test_campaign import FixedModules, campaign


def test_task_budget_retention_pairing_campaign_and_resume(office, campaign, monkeypatch):
    assert continuation.TASK_LIMITS == {'UID0007': 65536}
    monkeypatch.setattr(continuation, 'TASK_LIMITS', {'a': 65536})
    root, dataset, runtime, _ = office
    provider = Provider({'a': [response('1000'), response('1000')],
                         'b': [response('0'), response('1000')]})
    def transport(limit):
        return ChatTransport(offline_create=provider, model='offline-fixture', max_completion_tokens=limit)
    default, high = transport(32768), transport(65536)
    base = OfficeQAEvidenceAdapter(dataset, runtime, default, gate_metric=p.EM_GATE)
    special = OfficeQAEvidenceAdapter(dataset, runtime, high, gate_metric=p.EM_GATE)
    skill = root / 'initial.md'; skill.write_text('Parent\n')
    retained = base.actor_batch(['b'], skill, root / 'old', {'role': 'parent', 'split': 'train'})
    retained += special.actor_batch(['a'], skill, root / 'validation', {'role': 'parent', 'split': 'train'})
    original = deepcopy(retained)
    change = {'task_max_completion_tokens': {'a': 65536},
              'retained_records': {r['run_id']: p.digest(r) for r in retained}}
    adapter = continuation.TaskBudgetAdapter(change, retained, high, dataset, runtime, default, gate_metric=p.EM_GATE)
    target, _, _, cfg, _ = campaign(batches=[['a', 'b']])
    cfg['actor'] = default.metadata()
    with using_benchmark(adapter):
        ev.run_campaign(target, config=cfg, generate=FixedModules(conflict=True))
        assert len(provider.requests) == 4  # Old b, fresh validation a, two Candidates.
        for request in provider.requests:
            uid = 'a' if 'Question for a?' in json.dumps(request['messages']) else 'b'
            assert request['max_completion_tokens'] == (65536 if uid == 'a' else 32768)
        assert retained == original
        bundle = ev.read(target / 'rounds/R01/pairs/input.json')
        assert bundle['background']['max_completion_tokens'] == 32768
        assert 'UID0007 alone uses 65536' in adapter.resource('execution_context.md').read_text()
        parents = {r['task_id']: r for r in bundle['audit']['parent_records']}
        candidates = {r['task_id']: r for r in bundle['audit']['candidate_records']}
        for uid in parents:
            evidence.verify_pair(parents[uid], candidates[uid])
            assert parents[uid]['execution']['actor'] == candidates[uid]['execution']['actor']
        ev.run_campaign(target, config=cfg, resume=True)
        assert len(provider.requests) == 4
        ev.final_parent(target)
        bad = deepcopy(candidates['a']); bad['execution']['actor']['max_completion_tokens'] = 32768
        bad['provenance']['record_sha256'] = p.digest(bad['execution'])
        with pytest.raises(ValueError, match='Task Actor budget differs'):
            adapter.build_facts([bad], role='candidate')
        with pytest.raises(ValueError, match='Pair Actor conditions differ'):
            evidence.verify_pair(parents['a'], bad)
        altered = deepcopy(retained); altered[0]['execution']['answer'] = 'changed'
        with pytest.raises(ValueError, match='Retained record manifest differs'):
            continuation.TaskBudgetAdapter(change, altered, high, dataset, runtime, default, gate_metric=p.EM_GATE)
