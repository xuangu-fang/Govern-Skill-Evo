from copy import deepcopy
import json
import pytest

from scripts.runs.continue_v26_pilot import PilotAdapter
from scripts.runs.run_v26_pilot import run_pilot
from src.adapters.officeqa.transport import ChatTransport
from src.skill_evolution.v26.benchmarks.officeqa.adapter import OfficeQAEvidenceAdapter
from src.skill_evolution.v26.benchmarks.officeqa import protocol as p, evidence, facts
from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26.config import method_config
from src.skill_evolution.v26.benchmarks.officeqa.prompting import PROMPT_VERSIONS
from .conftest import Provider
from .test_thinking import thinking, SECRET
from .test_campaign import FixedModules


@pytest.fixture
def mixed(office):
    root, dataset, runtime, _ = office
    def actor(provider, limit):
        return ChatTransport(offline_create=provider, model='deepseek-flash', max_completion_tokens=limit,
            reasoning_mode='deepseek_thinking', reasoning_effort='medium', token_limit_field='max_tokens')
    old_provider = Provider({'a': [thinking('0')]})
    old = OfficeQAEvidenceAdapter(dataset, runtime, actor(old_provider, 16384), gate_metric=p.EM_GATE)
    skill = root/'parent.md'; skill.write_text('Parent\n')
    records = old.actor_batch(['a'], skill, root/'old', {'split': 'train', 'role': 'parent'})
    provider = Provider({'a': [thinking('1000')], 'b': [thinking('0'), thinking('1000')]})
    transport = actor(provider, 32768)
    context = root/'pilot_context.md'
    context.write_text(old.resource('execution_context.md').read_text()+'\nMixed-budget functional pilot: Parent a used 16384; new requests use 32768.\n')
    change = {'old_actor': old.transport.metadata(), 'new_actor': transport.metadata(),
        'retained_records': {r['run_id']: p.digest(r) for r in records}, 'retained_task_ids': ['a'],
        'execution_context_path': str(context), 'execution_context_sha256': p.file_digest(context)}
    adapter = PilotAdapter(change, records, dataset, runtime, transport, gate_metric=p.EM_GATE)
    config = {'method': method_config(), 'benchmark': adapter.identity, 'actor': transport.metadata(),
        'gate_metric': p.EM_GATE, 'optimization_splits': ['train'], 'batches': [['a', 'b']],
        'initial_skill': {'source': 'synthetic', 'text': 'Parent\n'}, 'max_attempts': 6,
        'continue_no_change': True, 'max_input_chars': 5000000, 'max_message_utf8_bytes': 6000000,
        'module_calls': {n: {'endpoint': 'https://offline.invalid/chat/completions', 'model': 'fixture',
            'max_tokens': 32768, 'timeout_seconds': 300, 'temperature': 1.0} for n in PROMPT_VERSIONS}}
    return root, adapter, provider, records, config


def test_mixed_budget_full_seven_modules_and_archived_resume(mixed):
    root, adapter, provider, retained, config = mixed
    generate = FixedModules(conflict=True)
    original = deepcopy(retained)
    with using_benchmark(adapter):
        result = run_pilot(root/'campaign', config=config, generate=generate)
        assert result['outcome'] == 'ACCEPT'
        assert [c[0] for c in generate.calls] == list(PROMPT_VERSIONS)
        assert len(provider.requests) == 3  # b Parent; a/b Candidate. Never rerun a Parent.
        assert all(r['max_tokens'] == 32768 and r['thinking']['type'] == 'enabled' for r in provider.requests)
        assert retained == original
        for _, messages, _, _ in generate.calls:
            encoded = json.dumps(messages)
            assert 'reasoning_content' not in encoded and SECRET not in encoded
            assert 'Mixed-budget functional pilot' in messages[0]['content']
        bundle = json.loads((root/'campaign/rounds/R01/pairs/input.json').read_text())
        assert [r['ref'] for r in bundle['payload']['runs']] == ['P1', 'Q1', 'P2', 'Q2']
        assert bundle['audit']['parent_records'][0] == retained[0]
        assert bundle['audit']['parent_records'][0]['execution']['actor']['max_completion_tokens'] == 16384
        assert bundle['audit']['candidate_records'][0]['execution']['actor']['max_completion_tokens'] == 32768
        assert run_pilot(root/'campaign', resume=True)['outcome'] == 'ACCEPT'
        assert len(provider.requests) == 3 and not (root/'campaign/rounds/R02').exists()
    with pytest.raises(ValueError, match='Mixed execution'):
        evidence.validate_bundle(bundle)  # Mixed pilot cannot silently use an ordinary reader.


def test_retained_mutation_or_unapproved_profile_rejected(mixed):
    _, adapter, _, retained, _ = mixed
    modified = deepcopy(retained[0]); modified['execution']['actor']['max_completion_tokens'] = 32768
    modified['provenance']['record_sha256'] = p.digest(modified['execution'])
    with pytest.raises(ValueError, match='Retained record changed'): adapter.build_facts([modified])
    change = deepcopy(adapter.change); change['new_actor']['temperature'] = 0.5
    with pytest.raises(ValueError):
        PilotAdapter(change, retained, adapter.dataset, adapter.runtime, adapter.transport, gate_metric=p.EM_GATE)
    with pytest.raises(ValueError, match='Mixed execution'):
        new = deepcopy(retained[0]); new['execution']['actor']['max_completion_tokens'] = 32768
        new['provenance']['record_sha256'] = p.digest(new['execution'])
        facts.build_facts([retained[0], new])  # Ordinary OfficeQA remains strict.


def test_continuation_resumes_missing_actor_without_rerunning_retained(mixed):
    root, adapter, provider, retained, config = mixed
    generate = FixedModules()
    class StopOnce:
        def __call__(self, *args): raise KeyboardInterrupt('after Parent batch')
    with using_benchmark(adapter):
        with pytest.raises(KeyboardInterrupt): run_pilot(root/'campaign', config=config, generate=StopOnce())
        assert len(provider.requests) == 1
        run_pilot(root/'campaign', resume=True, generate=generate)
        assert len(provider.requests) == 3
