"""Synthetic view, permission and archive tests; no model or Actor service calls."""
from copy import deepcopy
import json
import shutil

import pytest

from src.skill_evolution.v23 import memory as archive
from src.skill_evolution.v23_5 import preconditioner as pc, replay, evolution
from src.skill_evolution.v23_5.config import method_config, baseline_config, validate_method
from src.skill_evolution.v23_5.memory_view import (
    KNOWLEDGE_ONLY, MEMORY_V3, knowledge_only, historical_references, project_payload)
from src.skill_evolution.v23_5.update_patch import normalize_update_patches
from .helpers import Fake, keep, memory, legacy_memory, read, revise
from .test_baseline import Harness, config


def save(path, value):
    path.write_text(json.dumps(value))


@pytest.mark.parametrize('legacy', [False, True])
def test_projection_is_lossless_detached_and_validated(payload, legacy):
    source = legacy_memory(payload) if legacy else memory(payload)
    contract = archive.LEGACY_CONTRACT if legacy else archive.MULTI_KNOWLEDGE_CONTRACT
    if not legacy:
        source['entries'][0]['knowledge'].append({
            'text': 'Another condition and uncertainty.  \n', 'evidence': ['R1/P1:outcome']})
        source['entries'].append({'id': 'M3', 'knowledge': deepcopy(source['entries'][0]['knowledge'])})
    before = deepcopy(source)
    view = knowledge_only(source, memory_contract=contract)
    assert view == {'format': KNOWLEDGE_ONLY,
                    'entries': archive.normalize_memory(source, source_contract=contract)['entries']}
    assert source == before
    view['entries'][0]['knowledge'][0]['text'] = 'mutated'
    assert source == before
    source['entries'][0]['evidence' if legacy else 'knowledge'] = []
    with pytest.raises(ValueError): knowledge_only(source, memory_contract=contract)


def test_empty_and_unknown_history_are_not_silent_fallbacks():
    assert knowledge_only(archive.empty_memory()) == {'format': KNOWLEDGE_ONLY, 'entries': []}
    with pytest.raises(ValueError): knowledge_only({'entries': [], 'sources': {'bad': {}}})
    with pytest.raises(ValueError): project_payload({'memory': archive.empty_memory()}, 'unknown')


def test_preconditioner_current_facts_unchanged_and_no_raw_history(upstream, payload):
    saved = {**upstream[2], 'memory': memory(payload)}
    original = deepcopy(saved)
    saved['memory']['sources']['R1/diff']['parent'] = 'HIDDEN_HISTORICAL_PARENT'
    view = pc.model_input(saved, memory_view=KNOWLEDGE_ONLY)
    assert {k: v for k, v in view.items() if k != 'memory'} == {
        k: v for k, v in payload.items() if k != 'memory'}
    assert set(view['memory']) == {'format', 'entries'}
    assert view['memory']['entries'] == original['memory']['entries']
    messages = pc.messages_for(saved, memory_view=KNOWLEDGE_ONLY)
    assert 'HIDDEN_HISTORICAL_PARENT' not in json.dumps(messages)
    assert json.loads(messages[1]['content']) == view
    assert 'Knowledge Only input view' in messages[0]['content']
    assert 'Multi-Knowledge Memory representation v1' not in messages[0]['content']
    assert 'inspect the historical Parent and actual Diff' not in messages[0]['content']


@pytest.mark.parametrize('reference', ['R1/P1', 'R1/P1:0', 'R1/P1:outcome', 'R1/P1:2',
                                     'R1/P1:999', 'R1/P1:1-2', 'R1/P1:1–2', 'R99/diff'])
@pytest.mark.parametrize('field', ['reason', 'change', 'check', 'update'])
def test_preconditioner_denies_unsupplied_history_everywhere(payload, reference, field):
    payload = {**payload, 'memory': memory(payload)}
    result = keep(payload)
    if field == 'reason': result['adjustments'][0]['reason'] = f'Reported in `{reference}`.'
    elif field == 'change':
        result['adjustments'][0] = revise(payload)
        result['adjustments'][0]['change'] += f' See {reference}.'
    elif field == 'check':
        result['checks'] = [{'id': 'c1', 'update_ids': ['u1'], 'question': f'As in {reference}?'}]
    else:
        result['adjustments'][0] = revise(payload, replacement=f'Rule from {reference}.\n')
    with pytest.raises(ValueError, match='historical|reference'):
        normalize_update_patches(result, payload, memory_view=KNOWLEDGE_ONLY)


def test_preconditioner_exact_history_current_and_plan_refs_are_allowed(payload):
    payload = {**payload, 'memory': memory(payload)}
    result = keep(payload)
    result['adjustments'][0]['reason'] = (
        '`M1` reports a conditional response with provenance `R1/diff` and `R1/P1:1`. '
        'Current `P1`, `P1:0`, `P1:1`, `P1:outcome`, `C1`, `G1` motivate retaining `u1`.')
    normalize_update_patches(result, payload, memory_view=KNOWLEDGE_ONLY)
    # Archive existence alone was sufficient under v3, but not under Knowledge Only.
    result['adjustments'][0]['reason'] = 'Reported outcome `R1/P1:outcome`.'
    normalize_update_patches(result, payload, memory_view=MEMORY_V3)
    with pytest.raises(ValueError): normalize_update_patches(result, payload, memory_view=KNOWLEDGE_ONLY)


def test_associated_diff_is_not_automatically_allowed(payload):
    source = memory(payload)
    source['sources']['OTHER/diff'] = deepcopy(source['sources']['R1/diff'])
    source['entries'][0]['knowledge'][0]['evidence'][0] = 'OTHER/diff'
    allowed = historical_references(knowledge_only(source))
    assert allowed == {'OTHER/diff', 'R1/P1:1'}
    result = keep(payload)
    result['adjustments'][0]['reason'] = 'Not provided: `R1/diff`.'
    with pytest.raises(ValueError):
        normalize_update_patches(result, {**payload, 'memory': source}, memory_view=KNOWLEDGE_ONLY)


def test_preconditioner_run_reload_and_permission_recheck(upstream, payload):
    gd, dd, _, pd = upstream
    fake = Fake(keep(payload))
    value = pc.run_preconditioner(gd, dd, pd, generate=fake, memory=memory(payload), memory_view=KNOWLEDGE_ONLY)
    assert read(pd/'input.json')['memory'] == memory(payload)
    assert read(pd/'run.json')['prompt_version'] == pc.KNOWLEDGE_PROMPT_VERSION
    assert pc.load_preconditioner(pd) == value
    assert pc.run_preconditioner(gd, dd, pd, generate=fake, memory=memory(payload),
                                memory_view=KNOWLEDGE_ONLY) == value
    assert fake.calls == 1
    # Keep compiles identically even if its reason is changed; loader must recheck
    # reference permissions, not just compare the Effective Plan.
    raw = read(pd/'parsed.json')
    raw['adjustments'][0]['reason'] = 'Unsupported full-run access: `R1/P1`.'
    response = read(pd/'response.json'); response['content'] = json.dumps(raw)
    save(pd/'response.json', response); save(pd/'parsed.json', raw)
    (pd/'raw_output.txt').write_text(response['content'])
    with pytest.raises(ValueError, match='Update u1.reason: backtick content.*R1/P1.*allowed reference set'):
        pc.load_preconditioner(pd)


def test_invalid_preconditioner_reference_is_failed_attempt(upstream, payload):
    gd, dd, _, pd = upstream
    raw = keep(payload); raw['adjustments'][0]['reason'] = 'Unseen `R1/P1:outcome`.'
    fake = Fake(raw)
    with pytest.raises(ValueError):
        pc.run_preconditioner(gd, dd, pd, generate=fake, memory=memory(payload), memory_view=KNOWLEDGE_ONLY)
    assert fake.calls == 1 and read(pd/'run.json')['status'] == 'invalid'
    assert not (pd/'effective_plan.json').exists()


@pytest.fixture(scope='module')
def campaign(tmp_path_factory):
    root = tmp_path_factory.mktemp('knowledge_campaign')
    h = Harness(); h.stop = 'preconditioner_patch'
    result = evolution.run_campaign(root, config=baseline_config(config()),
                                    generate=h.generate, actor_runner=h.actor)
    return root, h, result


def test_two_rounds_preserve_archives_and_revised_knowledge(campaign):
    root, h, result = campaign
    assert result['state']['next_round'] == 3 and len(h.calls) == 10 and len(h.actor_calls) == 8
    assert h.memories[0] == {'format': KNOWLEDGE_ONLY, 'entries': []}
    assert len(h.memories[1]['entries'][0]['knowledge']) == 2
    rp = root/'rounds/R02/replay/attempts/001'
    bundle = read(rp/'input.json'); view = read(rp/'model_input.json')
    assert bundle['payload']['memory']['sources']
    assert view['memory'] == knowledge_only(bundle['payload']['memory'])
    assert read(rp/'history_pair_sources.json') == {}
    assert read(rp/'run.json')['prompt_version'] == replay.KNOWLEDGE_PROMPT_VERSION
    for key in ('parent', 'diff', 'plan', 'command_sets'):
        assert view[key] == bundle['payload'][key]
    assert {r['ref']: r for r in view['runs']} == {r['ref']: r for r in bundle['payload']['runs']}
    assert all(set(p) == {'parent', 'candidate', 'task_id', 'parent_result', 'candidate_result'}
               for p in view['pairs'])
    assert replay.load_replay(rp)['replay'] == read(rp/'replay.json')
    final = archive.load_memory(root/result['state']['active_memory'], memory_contract=evolution.MEMORY_CONTRACT)
    assert len(final['entries'][0]['knowledge']) == 4
    assert final['entries'][0]['knowledge'][:2] == h.memories[1]['entries'][0]['knowledge']
    assert (root/result['state']['active_memory']/f'archive/{root.name}_R01.json').exists()
    before = len(h.calls), len(h.actor_calls)
    evolution.run_campaign(root, resume=True, generate=h.generate, actor_runner=h.actor)
    assert before == (len(h.calls), len(h.actor_calls))


@pytest.mark.parametrize('reference', ['R01/P1', 'R01/P1:0', 'R01/P1:outcome', 'R01/P1:2',
                                     'R01/P1:999', 'R01/P1:1-2', 'M1', 'R99/diff'])
def test_replay_only_supplied_history_in_evidence(campaign, reference):
    root, _, _ = campaign
    payload = read(root/'rounds/R02/replay/attempts/001/input.json')['payload']
    reference = f'{root.name}_{reference}' if reference.startswith('R01/') else reference
    result = {'entries': [{'revises': [], 'knowledge': [{'text': 'Fixture.', 'evidence': ['diff', reference]}]}]}
    with pytest.raises(ValueError):
        replay.validate_result(result, payload, input_view=replay.KNOWLEDGE_INPUT_VIEW)


def test_replay_history_only_inherited_items_and_current_refs(campaign):
    root, _, _ = campaign
    payload = read(root/'rounds/R02/replay/attempts/001/input.json')['payload']
    result = {'entries': [{'revises': ['M1'], 'knowledge': deepcopy(payload['memory']['entries'][0]['knowledge'])}]}
    assert replay.validate_result(result, payload, input_view=replay.KNOWLEDGE_INPUT_VIEW) == result
    result['entries'][0]['knowledge'].append({'text': 'Current facts.', 'evidence': ['diff', 'P1:0', 'Q1:outcome']})
    replay.validate_result(result, payload, input_view=replay.KNOWLEDGE_INPUT_VIEW)
    result['entries'][0]['revises'] = ['M999']
    with pytest.raises(ValueError): replay.validate_result(result, payload, input_view=replay.KNOWLEDGE_INPUT_VIEW)


@pytest.mark.parametrize('where', ['text', 'evidence'])
def test_replay_generation_and_reload_recheck_permissions(campaign, tmp_path, where):
    root, _, _ = campaign
    rp = root/'rounds/R02/replay/attempts/001'
    bundle = read(rp/'input.json'); raw = read(rp/'replay.json')
    item = raw['entries'][0]['knowledge'][0]
    ref = f'{root.name}_R01/P1:outcome'
    if where == 'text': item['text'] += f' Claimed outcome {ref}.'
    else: item['evidence'].append(ref)
    # The reference exists; the old archive validator alone would accept it.
    archive.validate_entries(raw, bundle['payload'], memory_contract=evolution.MEMORY_CONTRACT)
    fake = Fake(raw)
    with pytest.raises(ValueError, match='historical'):
        replay.run_replay(bundle, tmp_path/'failed', generate=fake, input_view=replay.KNOWLEDGE_INPUT_VIEW)
    assert fake.calls == 1 and read(tmp_path/'failed/run.json')['status'] == 'invalid'
    assert not (tmp_path/'failed/replay.json').exists()
    dest = tmp_path/'tampered'; shutil.copytree(rp, dest)
    response = read(dest/'response.json'); response['content'] = json.dumps(raw)
    save(dest/'response.json', response)
    (dest/'raw_output.txt').write_text(response['content'])
    save(dest/'parsed.json', raw); save(dest/'replay.json', raw)
    with pytest.raises(ValueError, match='historical'): replay.load_replay(dest)


@pytest.mark.parametrize('kind', ['model_view', 'prompt', 'view_version', 'prompt_version', 'pairing'])
def test_replay_saved_view_and_prompt_tampering(campaign, tmp_path, kind):
    root, _, _ = campaign
    dest = tmp_path/'copy'; shutil.copytree(root/'rounds/R02/replay/attempts/001', dest)
    if kind == 'model_view':
        view = read(dest/'model_input.json'); view['memory']['entries'] = []
        save(dest/'model_input.json', view)
    elif kind == 'prompt': (dest/'prompt.md').write_text('changed')
    elif kind == 'pairing': save(dest/'history_pair_sources.json', {'R01': None})
    else:
        meta = read(dest/'run.json')
        meta['input_view' if kind == 'view_version' else 'prompt_version'] = (
            replay.INPUT_VIEW if kind == 'view_version' else replay.LEARNING_PROMPT_VERSION)
        save(dest/'run.json', meta)
    with pytest.raises(ValueError): replay.load_replay(dest)


def test_view_prompt_binding_and_no_history_lookup(campaign, tmp_path):
    root, _, _ = campaign
    bundle = read(root/'rounds/R02/replay/attempts/001/input.json')
    for view, prompt in [(replay.INPUT_VIEW, replay.KNOWLEDGE_PROMPT_VERSION),
                         (replay.KNOWLEDGE_INPUT_VIEW, replay.LEARNING_PROMPT_VERSION)]:
        fake = Fake({'entries': []})
        with pytest.raises(ValueError, match='mismatch'):
            replay.run_replay(bundle, tmp_path/'unused', generate=fake, input_view=view, prompt_version=prompt)
        assert fake.calls == 0 and not (tmp_path/'unused').exists()
    system = replay.messages_for(bundle, input_view=replay.KNOWLEDGE_INPUT_VIEW)[0]['content']
    assert 'Knowledge Only input view' in system
    assert 'Multi-Knowledge Memory representation v1' not in system
    assert 'references also control which steps' not in system
    original = method_config(KNOWLEDGE_ONLY)
    for field in ('memory_view', 'preconditioner_prompt', 'replay_input_view', 'replay_prompt_version'):
        changed = {**original, field: method_config(MEMORY_V3)[field]}
        with pytest.raises(ValueError): validate_method(changed)


@pytest.mark.parametrize('stage', ['preconditioner', 'replay'])
def test_permission_failure_retries_same_frozen_view(tmp_path, stage, monkeypatch):
    class RetryHarness(Harness):
        def __init__(self):
            super().__init__('RETAIN')
            self.injected = False

        def generate(self, messages, dest):
            response = super().generate(messages, dest)
            payload = json.loads(messages[1]['content'])
            name = messages[0]['content'].splitlines()[0][2:].split()[0].lower()
            if name == stage and payload['memory']['entries'] and not self.injected:
                self.injected = True
                context = payload['memory']['entries'][0]['knowledge'][0]['evidence'][0].split('/')[0]
                value = json.loads(response['content'])
                if stage == 'preconditioner':
                    value['adjustments'][0]['reason'] = f'Unseen `{context}/P1:outcome`.'
                else:
                    value['entries'][0]['knowledge'][0]['evidence'].append(f'{context}/P1:outcome')
                response['content'] = json.dumps(value)
            return response

    # Historical pairing retrieval must never be called for this configuration.
    def forbidden(*args, **kwargs):
        raise AssertionError('Knowledge Only expanded historical pairing sources')
    monkeypatch.setattr(replay, 'history_pair_sources', forbidden)
    h = RetryHarness()
    result = evolution.run_campaign(tmp_path, config=baseline_config(config()),
                                    generate=h.generate, actor_runner=h.actor)
    attempts = tmp_path/f'rounds/R02/{stage}/attempts'
    assert read(attempts/'001/run.json')['status'] == 'invalid'
    assert read(attempts/'002/run.json')['status'] == 'valid'
    for name in ('model_input.json', 'input.json'):
        assert read(attempts/'001'/name) == read(attempts/'002'/name)
    messages = read(attempts/'002/messages.json')
    assert messages[:2] == read(attempts/'001/messages.json')
    assert messages[2] == {'role': 'assistant', 'content': read(attempts/'001/response.json')['content']}
    assert messages[3]['content'].startswith('# Previous Output Validation Error')
    assert result['state']['parent'] is None and result['state']['next_round'] == 3
    final = archive.load_memory(tmp_path/result['state']['active_memory'], memory_contract=evolution.MEMORY_CONTRACT)
    assert len(final['entries'][0]['knowledge']) == 4
    assert len(h.calls) == 11 and len(h.actor_calls) == 8


def test_bad_full_archive_rejected_before_generation(upstream, payload, campaign, tmp_path):
    source = memory(payload)
    source['entries'][0]['knowledge'][0]['evidence'].append('R1/P1:999')
    fake = Fake(keep(payload))
    with pytest.raises(ValueError):
        pc.run_preconditioner(upstream[0], upstream[1], upstream[3], generate=fake,
                              memory=source, memory_view=KNOWLEDGE_ONLY)
    assert fake.calls == 0 and not upstream[3].exists()
    bundle = read(campaign[0]/'rounds/R02/replay/attempts/001/input.json')
    bundle['payload']['memory'] = source
    fake = Fake({'entries': []})
    with pytest.raises(ValueError):
        replay.run_replay(bundle, tmp_path/'invalid_replay', generate=fake, input_view=replay.KNOWLEDGE_INPUT_VIEW)
    assert fake.calls == 0 and not (tmp_path/'invalid_replay').exists()
