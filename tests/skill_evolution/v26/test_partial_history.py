from copy import deepcopy
import json

import pytest

from src.skill_evolution.v26 import modules, stages
from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26.contracts.editor import actual_diff
from src.skill_evolution.v26.benchmarks.officeqa import evidence, facts, input_view as iv, prompting as pr
from .conftest import response
from .test_evidence import proposal
from .test_prompts import conflict


@pytest.fixture
def partial_case(make_run):
    turn = response(calls=[('read', {'path': 'treasury_bulletin_2011_03.txt', 'start': 1, 'limit': 80}),
                           ('read', {'path': 'not_allowed.txt', 'start': 1, 'limit': 1})])
    parent, adapter, _, _ = make_run([turn]*4 + [response('0')])
    candidate, _, _, _ = make_run([turn]*3 + [response('1000')], role='candidate', skill='Candidate\n')
    saved = {**facts.build_facts([parent]), 'editor_status': 'candidate', 'candidate_text': 'Candidate\n',
             'actual_diff': actual_diff('Parent\n', 'Candidate\n'),
             'effective_plan': {'goal': 'Check evidence.', 'updates': [{'id': 'U1', 'text': 'Read.'}], 'checks': []}}
    refs = ['diff', 'P1:2_t1', 'P1:3', 'P1:4_t1', 'P1:4_t2', 'P1:5', 'Q1:3', 'Q1:outcome']
    proposed = proposal(refs=refs)
    with using_benchmark(adapter):
        bundle = evidence.build_replay_from_editor(saved, 'offline', [parent], [candidate])
        value, _ = evidence.build_input(bundle, proposed)
    return value, adapter, bundle, proposed


def pointers(encoded):
    return [(ref, record['request_messages']) for ref, record, _ in iv._partial_contexts(encoded)
            if isinstance(record['request_messages'], dict)]


def test_partial_prefixes_preserve_context_boundaries_events_and_scope(partial_case):
    value, _, _, _ = partial_case; before = deepcopy(value)
    encoded = iv.project(value); decoded = iv.restore(encoded)
    assert iv.equal(decoded, before) and iv.equal(value, before)
    assert pointers(encoded)
    assert len(iv.exact(encoded)) < len(iv.exact(iv.project(value, input_view=iv.PREVIOUS)))
    assert list(encoded['source_records']) == list(value['source_records'])
    assert encoded['context'] == value['context'] and encoded['targets'] == value['targets']
    assert 'Q1:3' not in dict(pointers(encoded))  # Same text in a paired execution is not shared.
    for ref, original in value['source_records'].items():
        actual = decoded['source_records'][ref]
        assert actual == original  # Includes errors, repeated observations, IDs and ordering.
    assert 'P1:1_t1' not in encoded['source_records']  # No inferred citations.


def test_descending_and_divergent_contexts_only_copy_exact_prefix(partial_case):
    value, _, _, _ = partial_case
    refs = ['P1:5', 'P1:4_t1', 'P1:3', 'P1:2_t1']
    value['source_records'] = {ref: value['source_records'][ref] for ref in refs}
    # A deliberately divergent provided context must not be normalized or overwritten.
    value['source_records']['P1:3']['record']['request_messages'][-1]['content'] += '\r\n区别 é e\u0301'
    encoded = iv.project(value)
    assert iv.equal(iv.restore(encoded), value)
    assert len(pointers(encoded)) == 3
    for ref, pointer in pointers(encoded):
        source = value['source_records'][pointer[iv.HISTORY]]['record']['request_messages']
        own = value['source_records'][ref]['record']['request_messages']
        n = pointer['prefix_messages']
        assert own[:n] == source[:n]
        assert n <= len(own)


@pytest.mark.parametrize('identity', ['run_id', 'task_id', 'role', 'namespace'])
def test_history_sharing_cannot_cross_execution_identity(partial_case, identity):
    value, _, _, _ = partial_case
    a = deepcopy(value['source_records']['P1:4_t1']); b = deepcopy(a)
    if identity != 'namespace': b[identity] += '_different'
    right = 'old/P1:4_t2' if identity == 'namespace' else 'P1:4_t2'
    value['source_records'] = {'P1:4_t1': a, right: b}
    encoded = iv.project(value)
    assert not pointers(encoded)
    assert iv.equal(iv.restore(encoded), value)


def test_historical_prefixes_and_full_run_can_coexist_without_scope_expansion(partial_case):
    value, _, bundle, _ = partial_case
    value['source_records'] = {f'old/{ref}': source for ref, source in value['source_records'].items() if ref != 'diff'}
    value['source_records']['P1'] = {'task_id': bundle['payload']['runs'][0]['task_id'],
        'run_id': bundle['payload']['runs'][0]['run_id'], 'role': 'parent',
        'record': deepcopy(bundle['payload']['runs'][0])}
    encoded = iv.project(value)
    assert pointers(encoded) and all(p[iv.HISTORY].startswith('old/') for _, p in pointers(encoded))
    assert iv.equal(iv.restore(encoded), value)


@pytest.mark.parametrize('mutation', ['missing', 'self', 'forward', 'cross_role', 'negative',
                                    'too_long', 'bool', 'float', 'extra', 'suffix', 'noncanonical'])
def test_bad_partial_pointers_fail_closed(partial_case, mutation):
    value, _, _, _ = partial_case; encoded = iv.project(value)
    ref, pointer = pointers(encoded)[0]
    if mutation == 'missing': pointer[iv.HISTORY] = 'P1:99'
    elif mutation == 'self': pointer[iv.HISTORY] = ref
    elif mutation == 'forward': pointer[iv.HISTORY] = 'Q1:3'
    elif mutation == 'cross_role': encoded['source_records'][ref]['role'] = 'candidate'
    elif mutation == 'negative': pointer['prefix_messages'] = -1
    elif mutation == 'too_long': pointer['prefix_messages'] = 100000
    elif mutation == 'bool': pointer['prefix_messages'] = True
    elif mutation == 'float': pointer['prefix_messages'] = 2.0
    elif mutation == 'extra': pointer['extra'] = 'x'
    elif mutation == 'suffix': pointer['suffix'] = {}
    elif mutation == 'noncanonical':
        # Same logical value, but a redundant encoding must not silently pass.
        pointer['prefix_messages'] -= 1
        source = iv.project(value, input_view=iv.PREVIOUS)['source_records'][pointer[iv.HISTORY]]['record']['request_messages']
        pointer['suffix'].insert(0, source[pointer['prefix_messages']])
    with pytest.raises(ValueError): iv.restore(encoded)


def test_old_view_decodes_and_instruction_overhead_falls_back(partial_case):
    value, adapter, bundle, _ = partial_case
    old = iv.project(value, input_view=iv.PREVIOUS)
    assert old[iv.HEADER]['format'] == iv.PREVIOUS and iv.equal(iv.restore(old), value)
    with using_benchmark(adapter):
        raw = pr._messages('verifier', value, bundle['background'], input_view=iv.LEGACY)
        baseline = pr._messages('verifier', value, bundle['background'], input_view=iv.PREVIOUS)
        assert iv.model_messages(raw, pr._read('lossless_input_view.md'),
            history_instruction='Oversized decoder\n'*100000) == baseline
        with pytest.raises(ValueError, match='Missing partial'):
            iv.model_messages(raw, pr._read('lossless_input_view.md'))


@pytest.mark.parametrize('module', ['verifier', 'repair'])
def test_actual_review_calls_preserve_raw_contract_and_use_prefixes(partial_case, module):
    value, adapter, bundle, candidate = partial_case
    with using_benchmark(adapter):
        if module == 'repair':
            verdict = conflict(); verdict['results'][0]['issues'][0]['evidence'] = ['Q1:outcome']
            value = evidence.build_repair_input(value, verdict, candidate)
            call = modules.repair_call(value, candidate, bundle['payload'])
        else:
            call = modules.verifier_call(value)
        encoded = json.loads(call.messages[1]['content'])
        assert encoded[iv.HEADER]['format'] == iv.FORMAT and pointers(encoded)
        assert iv.equal(iv.restore(encoded), value)
        assert (call.input['view'] if module == 'repair' else call.input) == value
        assert 'partial_history_view.md' in pr.prompt_identity(module)['resources_sha256']
        assert 'Exact prefixes in partial citation contexts' in call.messages[0]['content']
        if module == 'repair':
            call.complete({'changes': [{'target': value['targets'][0]['target'],
                                        'knowledge': value['targets'][0]['knowledge']}]})
        else:
            verdict = conflict(); verdict['results'][0]['issues'][0]['evidence'] = ['Q1:outcome']
            call.complete(verdict)


@pytest.mark.parametrize('module', ['verifier', 'repair'])
def test_partial_history_feedback_and_durable_response_resume(partial_case, tmp_path, module):
    value, adapter, bundle, candidate = partial_case
    verdict = conflict(); verdict['results'][0]['issues'][0]['evidence'] = ['Q1:outcome']
    seen = []
    with using_benchmark(adapter):
        if module == 'repair':
            value = evidence.build_repair_input(value, verdict, candidate)
            call = modules.repair_call(value, candidate, bundle['payload'])
            output = {'changes': [{'target': value['targets'][0]['target'],
                                   'knowledge': value['targets'][0]['knowledge']}]}
        else:
            call = modules.verifier_call(value); output = verdict
        def generate(name, messages, path, config):
            seen.append(deepcopy(messages))
            if len(seen) == 1:
                return {'content': '{}', 'finish_reason': 'stop'}
            stages.save(path/'response.json', {'content': json.dumps(output), 'finish_reason': 'stop'})
            raise KeyboardInterrupt('Response already durable')
        kwargs = dict(call_config={'endpoint': 'https://offline.invalid/v1', 'model': 'offline',
            'max_tokens': 100, 'timeout_seconds': 10, 'temperature': 0}, max_attempts=6,
            max_input_chars=10_000_000, max_message_utf8_bytes=10_000_000)
        folder = tmp_path/'stage'
        with pytest.raises(KeyboardInterrupt):
            stages.run_stage(folder, call, generate=generate, **kwargs)
        selected, result = stages.run_stage(folder, call, generate=None, resume=True, **kwargs)
        assert selected.name == '002' and len(seen) == 2
        assert len(seen[1]) == 4 and seen[1][:2] == seen[0] == call.messages
        assert iv.equal(iv.restore(json.loads(seen[1][1]['content'])), value)
        assert stages.read(folder/'input.json') == call.input
        assert stages.read(folder/'base_messages.json') == call.messages
        assert stages.read(selected/'recovery.json')['additional_requests'] == 0
        assert stages.run_stage(folder, call, generate=None, read_only=True, **kwargs)[1] == result


def test_other_five_modules_keep_previous_messages(office, monkeypatch):
    from scripts.runs.verify_v26_input_view import payloads
    from src.skill_evolution.v26.benchmarks.officeqa import protocol as p
    _, dataset, runtime, factory = office; adapter, _ = factory({})
    monkeypatch.setattr(runtime, 'run', lambda *a, **k: pytest.fail('No Actor execution'))
    with using_benchmark(adapter):
        background = p.background(adapter.transport.metadata())
        values = payloads(dataset.cases('train'), runtime, 'Parent\n', 8, background)
        for module in ('grouping', 'diagnosis', 'preconditioner', 'editor', 'replay'):
            assert pr._messages(module, values[module], background) == pr._messages(
                module, values[module], background, input_view=iv.PREVIOUS)


def test_measurement_partial_shapes_without_actor(office, monkeypatch):
    from scripts.runs.verify_v26_input_view import payloads
    from scripts.runs.verify_v26_partial_history import partial_views
    from src.skill_evolution.v26.benchmarks.officeqa import protocol as p
    _, dataset, runtime, factory = office; adapter, _ = factory({})
    monkeypatch.setattr(runtime, 'run', lambda *a, **k: pytest.fail('No Actor execution'))
    with using_benchmark(adapter):
        background = p.background(adapter.transport.metadata())
        values = payloads(dataset.cases('train'), runtime, 'Parent\n', 8, background)
        for historical in (False, True):
            for module, value in partial_views(values, dense=True, historical=historical).items():
                sent = pr._messages(module, value, background)
                encoded = json.loads(sent[1]['content'])
                assert pointers(encoded) and iv.equal(iv.restore(encoded), value)
                assert len(encoded['source_records']) == len(value['source_records'])
