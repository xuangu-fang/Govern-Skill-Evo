"""Replay presentation changes preserve evidence, retries and old archives offline."""
from copy import deepcopy
import json

import pytest

from src.skill_evolution.v25 import output_feedback as feedback, replay, replay_view
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench import timeline
from src.skill_evolution.v25.config import method_config
from .support import MethodResponses, response
from .test_pipeline import campaign


@pytest.fixture(scope='module')
def saved(tmp_path_factory):
    root, _, adapter, _, _, _ = campaign(tmp_path_factory.mktemp('paired_view'),
        rounds=2, method=MethodResponses(history=True, invalid_once='replay'))
    path = root/'rounds/R02/replay/attempts/001'
    return root, adapter, path, json.loads((path/'input.json').read_text())


def test_paired_view_changes_only_presentation_after_timeline(saved):
    _, adapter, path, bundle = saved
    before = deepcopy(bundle)
    with using_benchmark(adapter):
        old = replay.messages_for(bundle, input_view=replay_view.LEGACY_FORMAT)
        new = replay.messages_for(bundle, input_view=replay_view.PAIRED_FORMAT)
        context = feedback.saved_context(path)
        old_timeline = feedback.request_messages(old, context)
        new_timeline = feedback.request_messages(new, context)
    assert old[0] == new[0]  # Same learning prompt, execution context and view instructions.
    for left, right in [(old, new), (old_timeline, new_timeline)]:
        legacy, paired = json.loads(left[1]['content']), json.loads(right[1]['content'])
        assert list(legacy) == ['parent', 'diff', 'plan', 'runs', 'pairs', 'memory']
        assert list(paired) == ['parent', 'diff', 'plan', 'pairs', 'runs', 'memory']
        assert [r['ref'] for r in legacy['runs']] == ['P1', 'P2', 'Q1', 'Q2']
        assert [r['ref'] for r in paired['runs']] == ['P1', 'Q1', 'P2', 'Q2']
        assert {r['ref']: r for r in legacy['runs']} == {r['ref']: r for r in paired['runs']}
        assert all(legacy[k] == paired[k] for k in legacy if k != 'runs')
        assert len(left[1]['content']) == len(right[1]['content'])
    assert json.loads(new_timeline[1]['content']) == timeline.project(json.loads(new[1]['content']))
    assert bundle == before and bundle['payload']['memory']['entries']


def test_pair_order_comes_from_verified_pairs_not_run_positions(saved):
    _, adapter, _, original = saved
    bundle = deepcopy(original)
    bundle['payload']['runs'].reverse()
    bundle['payload']['pairs'].reverse()
    bundle['pair_audit'].reverse()
    with using_benchmark(adapter):
        view = replay_view.model_input(bundle)
    assert [r['ref'] for r in view['runs']] == ['P2', 'Q2', 'P1', 'Q1']


@pytest.mark.parametrize('damage', ['audit', 'counterpart', 'coverage'])
def test_pair_validation_is_not_bypassed(saved, damage):
    _, adapter, _, original = saved
    bundle = deepcopy(original)
    if damage == 'audit':
        bundle['pair_audit'][0]['verified'] = False
    elif damage == 'counterpart':
        bundle['payload']['pairs'][0]['candidate'] = 'Q2'
    else:
        bundle['payload']['pairs'].pop()
    with using_benchmark(adapter), pytest.raises(ValueError):
        replay_view.model_input(bundle)


@pytest.mark.parametrize('prompt', [replay.LEGACY_KNOWLEDGE_PROMPT_VERSION,
                                  replay.LEGACY_V2_KNOWLEDGE_PROMPT_VERSION,
                                  replay.LEGACY_V3_KNOWLEDGE_PROMPT_VERSION,
                                  replay.KNOWLEDGE_PROMPT_VERSION])
@pytest.mark.parametrize('input_view', [replay_view.LEGACY_FORMAT, replay_view.PAIRED_FORMAT, replay_view.SHARED_INITIAL_FORMAT])
def test_legacy_layout_reload_and_wrong_version_rejected(saved, tmp_path, prompt, input_view):
    _, adapter, current, bundle = saved
    answer = json.loads((current/'replay.json').read_text())
    calls = []
    def generate(messages, dest):
        calls.append(messages)
        return response(json.dumps(answer))
    generate.request_context = feedback.saved_context(current)
    with using_benchmark(adapter):
        expected = replay.run_replay(bundle, tmp_path/'legacy', generate=generate,
            input_view=input_view, prompt_version=prompt, max_input_chars=4000000)
        old = tmp_path/'legacy'
        before = {p: p.read_bytes() for p in old.iterdir()}
        assert replay.load_replay(old) == expected
        assert len(calls) == 1 and all(p.read_bytes() == b for p, b in before.items())
        meta = json.loads((old/'run.json').read_text())
        meta['input_view'] = replay_view.FORMAT
        (old/'run.json').write_text(json.dumps(meta))
        with pytest.raises(ValueError, match='Replay model view differs'):
            replay.load_replay(old)


def test_new_view_native_format_feedback_reconstruction(saved):
    root, adapter, _, _ = saved
    stage = root/'rounds/R01/replay/attempts'
    first, second = stage/'001', stage/'002'
    read = lambda p, name: json.loads((p/name).read_text())
    assert read(first, 'error.json')['kind'] == 'output_validation'
    assert read(first, 'run.json')['input_view'] == replay_view.FORMAT
    one, two = read(first, 'messages.json'), read(second, 'messages.json')
    assert len(one) == 2 and len(two) == 4 and two[:2] == one
    with using_benchmark(adapter):
        rebuilt = feedback.request_messages(replay.messages_for(read(second, 'input.json'),
            retry_policy=feedback.POLICY), feedback.saved_context(second))
        assert rebuilt == two
        replay.load_replay(second)


def test_unknown_view_and_current_defaults(saved):
    _, adapter, _, bundle = saved
    with using_benchmark(adapter), pytest.raises(ValueError, match='Unsupported Replay input view'):
        replay.messages_for(bundle, input_view='unknown')
    cfg = method_config()
    assert cfg['replay_input_view'] == replay_view.FORMAT
    assert cfg['replay_prompt_version'] == 'v25_replay_decision_fidelity_v4'
    assert cfg['preconditioner_prompt'] == 'v25_preconditioner_evidence_decision_boundaries_v7'
