from copy import deepcopy
import json
import re

import pytest

from src.skill_evolution.v23 import editor as old_editor
from src.skill_evolution.v23_4 import diagnosis as old_diagnosis, evolution as old_evolution
from src.skill_evolution.v23_5 import diagnosis, preconditioner, editor, evolution
from src.skill_evolution.v23_5.config import method_config, baseline_config, KNOWLEDGE_ONLY
from tests.skill_evolution.v23_4.test_evolution import Harness as OldHarness, config as old_config
from .helpers import Fake, keep, patch, read


class Harness(OldHarness):
    def generate(self, messages, dest):
        response = super().generate(messages, dest)
        result = json.loads(response['content'])
        # Synthetic model response conversion only; production rejects numbered hunks.
        if isinstance(result.get('patch'), str):
            result['patch'] = re.sub(r'^@@ [^\n]+\n', '@@\n', result['patch'], flags=re.M)
        for a in result.get('adjustments', []):
            if isinstance(a['to'], dict):
                a['to']['patch'] = re.sub(r'^@@ [^\n]+\n', '@@\n', a['to']['patch'], flags=re.M)
        response['content'] = json.dumps(result)
        return response


def config(rounds=2):
    result = old_config(rounds)
    result['method'] = method_config()
    return result


@pytest.mark.parametrize('outcome', ['ACCEPT', 'RETAIN'])
def test_two_rounds_and_reload_with_unchanged_replay_memory(tmp_path, outcome):
    h = Harness(outcome)
    h.stop = 'preconditioner_patch'
    result = evolution.run_campaign(tmp_path, config=config(), generate=h.generate, actor_runner=h.actor)
    assert result['state']['next_round'] == 3
    assert len(h.calls) == 10 and len(h.actor_calls) == 8
    rd = tmp_path/'rounds/R02'
    pc = rd/'preconditioner/attempts/001'
    ed = rd/'editor/attempts/001'
    assert read(pc/'effective_plan.json') == read(ed/'input.json')['plan']
    assert read(pc/'actual_diffs.json')['u1'].startswith('--- a/SKILL.md\n+++ b/SKILL.md\n@@ -')
    assert '@@\n' in read(ed/'editor.json')['patch']
    value = editor.load_editor(ed)
    assert old_editor.apply_patch(value['facts']['parent'], value['actual_diff']) == value['candidate_text']
    assert read(rd/'replay/attempts/001/run.json')['prompt_version'] == evolution.replay.KNOWLEDGE_PROMPT_VERSION
    assert len(h.memories[1]['entries'][0]['knowledge']) == 2
    before = len(h.calls), len(h.actor_calls)
    evolution.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    assert before == (len(h.calls), len(h.actor_calls))
    assert (evolution.final_parent(tmp_path) is not None) == (outcome == 'ACCEPT')


@pytest.mark.parametrize('mode', ['keep', 'withdraw'])
def test_keep_proceeds_withdraw_stops(tmp_path, mode):
    h = Harness()
    if mode == 'withdraw':
        h.stop = 'preconditioner_no_change'
    evolution.run_campaign(tmp_path, config=config(1), generate=h.generate, actor_runner=h.actor)
    assert ('editor' in h.calls) == (mode == 'keep')
    assert ('replay' in h.calls) == (mode == 'keep')


def test_versioned_config_and_unknown_view_reject_before_calls(tmp_path):
    original = deepcopy(old_evolution.METHOD)
    assert method_config(KNOWLEDGE_ONLY)['memory_view'] == KNOWLEDGE_ONLY
    with pytest.raises(ValueError, match='Unsupported'):
        method_config('unknown_view')
    with pytest.raises(ValueError, match='method freeze'):
        evolution.initialize(tmp_path/'old', old_config())
    value = config()
    value['method']['replay_prompt_version'] = 'different'
    with pytest.raises(ValueError, match='method freeze'):
        evolution.initialize(tmp_path/'bad', value)
    assert old_evolution.METHOD == original
    frozen = evolution.frozen_contract()
    assert 'src/skill_evolution/shared/unnumbered_patch.py' in frozen
    for name in ('diagnosis', 'preconditioner', 'editor'):
        assert f'src/skill_evolution/v23_5/{name}_prompt.md' in frozen


def test_baseline_config_preserves_runtime_and_input():
    old = old_config()
    frozen = deepcopy(old)
    new = baseline_config(old)
    assert old == frozen and new['method'] == method_config()
    assert {k: v for k, v in new.items() if k != 'method'} == {
        k: v for k, v in old.items() if k != 'method'}
    new['batches'][0].clear()
    assert old == frozen


@pytest.mark.parametrize('value,status', [('', 'no_change'), (None, 'needs_revision'), ('edit', 'candidate')])
def test_editor_outcomes_and_versions(upstream, payload, tmp_path, value, status):
    gd, dd, _, pd = upstream
    preconditioner.run_preconditioner(gd, dd, pd, generate=Fake(keep(payload)))
    ed = tmp_path/'editor'
    text = patch(payload['parent'], payload['parent'] + 'Extra guidance.\n') if value == 'edit' else value
    gen = Fake({'patch': text, 'reason': 'Offline contract example.'})
    result = editor.run_editor(pd, ed, generate=gen)
    assert result['editor_status'] == status
    assert (ed/'candidate.md').exists() == (status == 'candidate')
    assert (ed/'actual.diff').exists() == (status == 'candidate')
    assert editor.run_editor(pd, ed, generate=gen) == result and gen.calls == 1
    with pytest.raises(ValueError):
        old_diagnosis.load_diagnosis(dd)
    meta = read(ed/'run.json')
    meta['patch_contract'] = 'numbered'
    (ed/'run.json').write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='patch contract'):
        editor.load_editor(ed)


@pytest.mark.parametrize('patch_value', [' ', 'numbered', 'wrong_context'])
def test_editor_bad_patch_is_not_semantic_stop(upstream, payload, tmp_path, patch_value):
    gd, dd, _, pd = upstream
    preconditioner.run_preconditioner(gd, dd, pd, generate=Fake(keep(payload)))
    if patch_value == 'numbered':
        value = old_editor.actual_diff(payload['parent'], 'Changed.\n')
    elif patch_value == 'wrong_context':
        value = '--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-Not in Parent\n+Changed\n'
    else:
        value = patch_value
    ed = tmp_path/'editor'
    with pytest.raises(ValueError):
        editor.run_editor(pd, ed, generate=Fake({'patch': value, 'reason': 'Fixture.'}))
    assert read(ed/'run.json')['status'] == 'invalid'
    assert not (ed/'candidate.md').exists() and not (ed/'actual.diff').exists()


def test_preconditioner_rejects_editor_patch_sentinels(payload):
    from src.skill_evolution.v23_5.update_patch import normalize_update_patches
    for value in ('', None):
        result = keep(payload)
        result['adjustments'][0].update(focus=['S'], change='Modify.', to={'patch': value})
        with pytest.raises(ValueError):
            normalize_update_patches(result, payload)


def test_frozen_source_changes_reject_resume(tmp_path, monkeypatch):
    evolution.initialize(tmp_path, config(1))
    contract = evolution.frozen_contract()
    contract['src/skill_evolution/shared/unnumbered_patch.py'] += '\nchanged'
    monkeypatch.setattr(evolution, 'frozen_contract', lambda: contract)
    h = Harness()
    with pytest.raises(ValueError, match='Frozen source'):
        evolution.run_campaign(tmp_path, generate=h.generate, actor_runner=h.actor)
    assert not h.calls and not h.actor_calls
