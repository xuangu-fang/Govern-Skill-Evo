from .comparison import behavior
"""Compare actual saved baseline evidence and paired offline campaign execution."""
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys

import pytest

from src.skill_evolution.v24 import evolution as new
from src.skill_evolution.v24 import config, baseline, knowledge_review, knowledge_evidence, knowledge_repair
from src.skill_evolution.v24.benchmark import current, using_benchmark
from src.skill_evolution.v24.contracts import gate, memory
from src.skill_evolution.v23_5 import evolution as old
from tests.skill_evolution.v23_5.test_knowledge_review import ReviewedHarness, cfg

ROOT = new.ROOT
CAMPAIGN = ROOT/'artifacts/methods/v23_5/alfworld_verified_feedback_001/S1'


def read(path):
    return json.loads(Path(path).read_text())


def selected(rd, name):
    return rd/name/read(rd/name/'result.json')['path']


def test_baseline_and_resolved_profile(tmp_path):
    evidence, original = baseline.audit()
    prepared = baseline.prepare(tmp_path/'prepared')
    resolved = read(tmp_path/'prepared/config/campaign.json')
    assert prepared['real_model_requests'] == prepared['environment_episodes'] == 0
    assert resolved['method']['knowledge_review'] == 'obvious_fact_verifier_targeted_repair_v1'
    assert resolved['method']['memory_publication'] == 'fact_screen_and_optional_repair_before_memory_commit'
    assert resolved['module_max_tokens'] == original['module_max_tokens']
    migrated = deepcopy(resolved)
    migrated.pop('benchmark')
    migrated['method']['version'] = original['method']['version']
    assert migrated['method']['preconditioner_prompt'] == new.preconditioner.KNOWLEDGE_PROMPT_VERSION
    migrated['method']['preconditioner_prompt'] = original['method']['preconditioner_prompt']
    expected = deepcopy(original)
    expected['initial_skill'] = {k: original['initial_skill'][k] for k in ('source', 'text')}
    assert migrated == expected
    assert len(evidence['source_files']) == 99
    with pytest.raises(ValueError, match='new directory'):
        baseline.prepare(tmp_path/'prepared')


def test_core_imports_without_any_environment_or_old_method():
    code = '''
import sys
from src.skill_evolution.v24 import evolution, evaluation
assert not [n for n in sys.modules if n.startswith(('src.adapters.', 'src.skill_evolution.v23', 'alfworld', 'textworld'))]
from src.skill_evolution.v24.facts import build_facts
try:
    build_facts([])
except RuntimeError as e:
    assert 'Bind a benchmark' in str(e)
else:
    raise AssertionError('implicit benchmark')
'''
    subprocess.run([sys.executable, '-c', code], cwd=ROOT, check=True, capture_output=True, text=True)


def test_unchanged_prompt_bytes_and_actor_commands_equal():
    evidence, original = baseline.audit()
    frozen = read(CAMPAIGN/'contract.json')
    for path, content in frozen.items():
        if path.startswith('src/skill_evolution/') and path.endswith('.md'):
            relative = Path(path)
            actual = current().resource('/'.join(relative.parts[-2:])).read_bytes()
            if relative.parent.name == 'v23_5' and relative.name.startswith('preconditioner'):
                assert actual != content.encode()
                assert behavior(actual.decode()) == content
            else:
                assert actual == content.encode()
    resolved = config.baseline_config(original, benchmark=current())
    for task, final in [('train:0000', False), ('val:0000', False), ('test:0000', True)]:
        command = new.actor_command(task, '/skill.md', '/output', resolved, final=final)
        previous = old.actor_command(task, '/skill.md', '/output', original, final=final)
        assert command[:2] + command[3:] == previous[:2] + previous[3:]
        assert command[2].endswith('v24.benchmarks.alfworld.actor.run_task_skill')
    for stage in new.enabled_modules(resolved):
        assert new.stage_call_config(resolved, stage) == old.stage_call_config(original, stage)


@pytest.mark.parametrize('round_name', ['R01', 'R02', 'R03'])
def test_recorded_round_inputs_messages_outputs_and_review_equal(round_name):
    rd = CAMPAIGN/'rounds'/round_name
    if not rd.exists():
        pytest.skip('Local raw baseline archives are not installed')
    # Unchanged loaders still replay old evidence; new Preconditioner lineage must
    # reject the old Prompt version rather than silently reinterpret its output.
    for name in ('grouping', 'diagnosis', 'preconditioner', 'editor', 'replay'):
        legacy = import_module('src.skill_evolution.v23_5.'+name)
        migrated = import_module('src.skill_evolution.v24.'+name)
        directory = selected(rd, name)
        original = getattr(legacy, 'load_'+name)(directory)
        if name in ('preconditioner', 'editor', 'replay'):
            with pytest.raises(ValueError, match='Preconditioner prompt version'):
                getattr(migrated, 'load_'+name)(directory)
        else:
            assert getattr(migrated, 'load_'+name)(directory) == original
    bundle = read(rd/'pairs/input.json')
    parents = [read(p) for p in bundle['record_paths']['parent']]
    candidates = [read(p) for p in bundle['record_paths']['candidate']]
    assert new.build_facts(parents) == old.build_facts(parents)
    assert new.build_facts(candidates) == old.build_facts(candidates)
    with pytest.raises(ValueError, match='Preconditioner prompt version'):
        new.replay.build_replay(selected(rd, 'editor'), parents, candidates,
                               memory=bundle['payload']['memory'])
    tasks = [p['task']['id'] for p in parents]
    paired = gate.build_gate(parents, candidates, tasks, parent_skill=bundle['payload']['parent'],
                             candidate_skill=bundle['candidate'])
    assert paired == read(rd/'gate/result.json')['input']
    assert gate.decide_gate(paired['input'], tasks) == read(rd/'gate/result.json')['result']
    previous = CAMPAIGN/read(rd/'result.json')['before']['active_memory']
    candidate = read(selected(rd, 'replay')/'replay.json')
    value, inventory, provenance = knowledge_review.prepare_input(bundle, candidate, previous)
    saved = read(rd/'knowledge_review/input.json')
    assert value == saved['verifier_input']
    assert inventory == saved['inventory'] and behavior(provenance) == behavior(saved['historical_sources'])
    def no_generation(*args):
        raise AssertionError('Saved valid response must not generate')
    verdicts = knowledge_review.run_model('verifier', value, selected(rd, 'verifier'), generate=no_generation,
        call_config=read(selected(rd, 'verifier')/'run.json')['call_config'],
        validate=lambda output: new.knowledge_review.verifier.validate_result(output, value), max_input_chars=4000000)
    repair_input = knowledge_evidence.build_repair_input(value, verdicts, candidate)
    checked = candidate
    if repair_input['targets']:
        assert repair_input == read(rd/'knowledge_review/repair_input.json')
        repaired = knowledge_review.run_model('repair', repair_input, selected(rd, 'repair'), generate=no_generation,
            call_config=read(selected(rd, 'repair')/'run.json')['call_config'],
            validate=lambda output: knowledge_repair.merge(output, repair_input, candidate, bundle['payload']),
            max_input_chars=4000000)
        checked = knowledge_repair.merge(repaired, repair_input, candidate, bundle['payload'])
    assert checked == read(rd/'knowledge_review/candidate.json')
    assert memory.load_memory(rd/'memory', memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT) == old.memory.load_memory(
        rd/'memory', memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)


class CapturedHarness(ReviewedHarness):
    def __init__(self, mode='replace', outcome='ACCEPT'):
        super().__init__(mode, outcome)
        self.requests = []

    def generate(self, messages, dest):
        self.requests.append(deepcopy(messages))
        return super().generate(messages, dest)


@pytest.mark.parametrize('outcome', ['ACCEPT', 'RETAIN'])
@pytest.mark.parametrize('mode', ['supported', 'replace', 'unchanged'])
def test_two_round_campaign_messages_publication_and_zero_call_resume(tmp_path, outcome, mode):
    roots = [tmp_path/'old/S1', tmp_path/'new/S1']
    harnesses = [CapturedHarness(mode, outcome), CapturedHarness(mode, outcome)]
    results = []
    for module, root, h in zip((old, new), roots, harnesses):
        value = cfg(2)
        if module is new:
            value = config.baseline_config(value, benchmark=current())
        results.append(module.run_campaign(root, config=value, generate=h.generate, actor_runner=h.actor))
        before = deepcopy(h.requests), deepcopy(h.actor_calls)
        module.run_campaign(root, resume=True, generate=h.generate, actor_runner=h.actor)
        module.final_parent(root)
        assert before == (h.requests, h.actor_calls)
    assert results[0] == results[1]
    assert behavior(harnesses[0].requests) == behavior(harnesses[1].requests)
    assert old.cost_summary(roots[0]) == new.cost_summary(roots[1])
    for rnd in ('R01', 'R02'):
        for relative in ('result.json', 'gate/result.json', 'editor/attempts/001/editor.json',
                         'preconditioner/attempts/001/effective_plan.json', 'knowledge_review/candidate.json',
                         'memory/view.json'):
            assert behavior(read(roots[0]/'rounds'/rnd/relative)) == behavior(read(roots[1]/'rounds'/rnd/relative))


@pytest.mark.parametrize('mode', ['bad_verifier', 'bad_repair', 'unauthorized'])
def test_feedback_retry_budget_and_no_publication_equal(tmp_path, mode):
    captures = []
    for label, module in [('old', old), ('new', new)]:
        h = CapturedHarness(mode)
        value = cfg(1)
        value['max_attempts'] = 6
        if module is new:
            value = config.baseline_config(value, benchmark=current())
        root = tmp_path/label/'S1'
        with pytest.raises(module.Stopped):
            module.run_campaign(root, config=value, generate=h.generate, actor_runner=h.actor)
        before = len(h.requests)
        with pytest.raises(module.Stopped):
            module.run_campaign(root, resume=True, generate=h.generate, actor_runner=h.actor)
        assert len(h.requests) == before
        assert read(root/'state.json')['next_round'] == 1
        assert not (root/'rounds/R01/memory').exists()
        captures.append(h.requests)
    assert behavior(captures[0]) == behavior(captures[1])


def test_interrupted_publication_resumes_without_new_requests(tmp_path):
    h = CapturedHarness()
    h.technical_once = True
    def interrupt(stage):
        if stage == 'memory_prepared':
            raise KeyboardInterrupt()
    root = tmp_path/'S1'
    with pytest.raises(KeyboardInterrupt):
        new.run_campaign(root, config=config.baseline_config(cfg(1), benchmark=current()),
                         generate=h.generate, actor_runner=h.actor, hook=interrupt)
    before = deepcopy(h.requests), deepcopy(h.actor_calls)
    new.run_campaign(root, resume=True, generate=h.generate, actor_runner=h.actor)
    assert before == (h.requests, h.actor_calls)
    assert h.calls.count('verifier') == 2 and h.calls.count('repair') == 1
    new.final_parent(root)


def test_wrong_binding_and_tampered_source_rejected(tmp_path):
    value = config.baseline_config(cfg(1), benchmark=current())
    bad = deepcopy(value)
    bad['benchmark']['name'] = 'other'
    with pytest.raises(ValueError, match='binding'):
        new.initialize(tmp_path/'bad', bad)
    new.initialize(tmp_path/'S1', value)
    path = tmp_path/'S1/contract.json'
    frozen = read(path)
    frozen.pop(next(iter(frozen)))
    path.write_text(json.dumps(frozen))
    with pytest.raises(ValueError, match='Frozen source'):
        new.run_campaign(tmp_path/'S1', resume=True, generate=lambda *_: pytest.fail('model called'),
                         actor_runner=lambda *_: pytest.fail('actor called'))


@pytest.mark.parametrize('stage', ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay', 'verifier', 'repair'])
def test_all_stages_mixed_retry_requests_equal(tmp_path, stage):
    from tests.skill_evolution.v23_5.test_unified_retry import Scripted
    captures = []
    for label, module in [('old', old), ('new', new)]:
        h = Scripted(stage, ['json', 'timeout', 'length', 'schema', 'chunked', 'valid'])
        value = cfg(1)
        value.update(max_attempts=6, retry_delay_seconds=0)
        if module is new:
            value = config.baseline_config(value, benchmark=current())
        root = tmp_path/label/'S1'
        assert module.run_campaign(root, config=value, generate=h.generate, actor_runner=h.actor)['status'] == 'complete'
        assert len(h.requests) == 6
        module.final_parent(root)
        captures.append(h.requests)
    assert behavior(captures[0]) == behavior(captures[1])


@pytest.mark.parametrize('stage', ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay', 'verifier', 'repair'])
def test_all_stages_unknown_internal_fault_does_not_retry(tmp_path, stage):
    from tests.skill_evolution.v23_5.test_unified_retry import Scripted
    h = Scripted(stage, ['internal', 'valid'])
    value = config.baseline_config(cfg(1), benchmark=current())
    with pytest.raises(new.Stopped, match='unknown generator bug'):
        new.run_campaign(tmp_path, config=value, generate=h.generate, actor_runner=h.actor)
    with pytest.raises(new.Stopped):
        new.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    assert len(h.requests) == 1


@pytest.mark.parametrize('stop', ['diagnosis_no_change', 'preconditioner_no_change', 'diagnosis_need_evidence'])
def test_semantic_stops_remain_distinct_from_output_failures(tmp_path, stop):
    h = CapturedHarness()
    h.stop = stop
    value = config.baseline_config(cfg(1), benchmark=current())
    if stop.endswith('need_evidence'):
        with pytest.raises(new.Stopped, match='semantic'):
            new.run_campaign(tmp_path, config=value, generate=h.generate, actor_runner=h.actor)
        assert read(tmp_path/'state.json')['next_round'] == 1
    else:
        new.run_campaign(tmp_path, config=value, generate=h.generate, actor_runner=h.actor)
        assert read(tmp_path/'rounds/R01/result.json')['outcome'] == 'no_change'
    assert 'editor' not in h.calls and 'replay' not in h.calls


def test_empty_replay_skips_verifier_and_repair(tmp_path):
    h = CapturedHarness()
    h.empty_memory = True
    new.run_campaign(tmp_path, config=config.baseline_config(cfg(1), benchmark=current()),
                     generate=h.generate, actor_runner=h.actor)
    assert 'verifier' not in h.calls and 'repair' not in h.calls
    assert read(tmp_path/'rounds/R01/knowledge_review/result.json')['targets'] == 0


def test_bad_archive_input_is_not_reported_as_model_output():
    from src.skill_evolution.v24 import output_feedback
    with pytest.raises(ValueError) as caught:
        output_feedback.output_call('repair output', knowledge_repair.merge, {}, {}, {}, {})
    assert not isinstance(caught.value, output_feedback.OutputValidationError)


@pytest.mark.parametrize('mutation', ['task', 'protocol', 'environment', 'initial_observation', 'implementation'])
def test_pair_mismatch_rejection_equal(mutation):
    from src.skill_evolution.v23.replay import verify_pair as legacy_pair
    from src.skill_evolution.v24.contracts.replay import verify_pair
    bundle = read(CAMPAIGN/'rounds/R01/pairs/input.json')
    parent = read(bundle['record_paths']['parent'][0])
    candidate = read(bundle['record_paths']['candidate'][0])
    if mutation == 'task':
        candidate['task']['id'] = 'wrong'
    elif mutation == 'protocol':
        candidate['protocol']['history_length'] = 99
    elif mutation == 'environment':
        candidate['gamefile'] = 'wrong'
    elif mutation == 'initial_observation':
        candidate['initial_observation'] = 'wrong'
    else:
        candidate['implementation']['files'] = {}
    errors = []
    for function in ((verify_pair,) if mutation == 'environment' else (legacy_pair, verify_pair)):
        with pytest.raises(ValueError) as error:
            function(parent, candidate)
        errors.append(str(error.value))
    if len(errors) == 2: assert errors[0] == errors[1]


def test_explicit_adapter_binding_has_no_default_or_cross_context_leak():
    from src.skill_evolution.v24.facts import build_facts
    original = current()
    class OtherEvidence:
        def build_facts(self, records):
            return {'input_artifacts': records, 'events': []}
    with using_benchmark(OtherEvidence()):
        assert build_facts(['workbook']) == {'input_artifacts': ['workbook'], 'events': []}
    assert current() is original
