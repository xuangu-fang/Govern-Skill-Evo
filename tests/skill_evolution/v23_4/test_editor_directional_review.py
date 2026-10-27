"""Targeted Editor review witnesses; injected outputs do NOT test model compliance."""
import json

import pytest

from src.skill_evolution.v23 import grouping
from src.skill_evolution.v23.editor import actual_diff, apply_patch, validate_editor
from src.skill_evolution.v23.facts import build_facts
from src.skill_evolution.v23_4 import diagnosis, editor, preconditioner, replay
from tests.skill_evolution.v23.test_grouping import result as groups
from tests.skill_evolution.v23.test_replay_memory import records
from .helpers import Fake, read

PRESERVED = 'Preserve exact target identification.\n'
WITHDRAWN = 'Search every category before stopping.\n'
CASES = {
    'redirect': {
        'old': ['Never return to a previously visited location.\n'],
        'effective': ['Avoid repeat searches when current and recent observations show no new information or task progress; allow returns needed for the current task.\n'],
        'focus': ['D', 'S'],
    },
    'widen': {
        'old': ['Use source A only; wait if A is unavailable.\n'],
        'effective': ['If A is unavailable, permit a visible alternative that meets the current information requirements; check suitability before using it.\n'],
        'focus': ['S'],
    },
    'coordinate': {
        'old': ['Retry after preparation.\n', 'Abandon an action after any failure.\n'],
        'effective': ['After repair, recheck current prerequisites and retry if ready.\n',
                      'Avoid retry while the prerequisite remains unmet; allow retry after visible repair and readiness checking.\n'],
        'focus': ['S', 'C'],
    },
}


def prepare(tmp_path, name):
    spec = CASES[name]
    parent = '# Skill\n' + ''.join(spec['old']) + PRESERVED
    parents = records(parent)
    for r in parents: r['run_id'] = 'parent-' + r['run_id']
    gd, dd, pd = [tmp_path / stage for stage in ('grouping', 'diagnosis', 'preconditioner')]
    grouping.run_grouping(parents, gd, round_id='editor-review',
                          generate=Fake(groups(build_facts(parents)['facts'])))
    texts = [*spec['old'], WITHDRAWN]
    updates = [{'id': f'u{i}', 'text': text, 'basis': ['P1:1', 'P2:1']} for i, text in enumerate(texts, 1)]
    plan = {'goal': 'Improve task progress while preserving necessary capabilities.',
            'updates': updates, 'checks': [{'id': 'c1', 'update_ids': ['u1'],
                'question': 'Does the required behavior occur without adding an exhaustive-search stopping requirement?'}]}
    diagnosis.run_diagnosis(gd, dd, generate=Fake({'decision': 'revise', 'reason': 'Synthetic interface fixture.', 'plan': plan}))
    adjustments = []
    for u, final in zip(updates, spec['effective']):
        adjustments.append({'target': u['id'], 'focus': spec['focus'], 'change': final.strip(),
                            'reason': 'Current `P1:1` motivates this synthetic, unverified proposal.',
                            'to': {'patch': actual_diff(u['text'], final)}})
    adjustments.append({'target': updates[-1]['id'], 'focus': ['D'],
                        'change': 'Withdraw the unsupported exhaustive-search stopping requirement.',
                        'reason': '`P2:1` does not establish a need for this additional stopping restriction.', 'to': []})
    saved = preconditioner.run_preconditioner(gd, dd, pd, generate=Fake({'adjustments': adjustments, 'checks': None}))
    candidate = '# Skill\n' + ''.join(spec['effective']) + PRESERVED
    return parents, pd, saved, parent, candidate


@pytest.mark.parametrize('name', CASES)
def test_effective_only_input_and_reviewed_implementation(tmp_path, name):
    parents, pd, conditioned, parent, candidate = prepare(tmp_path, name)
    fake = Fake({'patch': actual_diff(parent, candidate), 'reason': 'Human-authored faithful implementation witness.'})
    ed = tmp_path / 'editor'
    saved = editor.run_editor(pd, ed, generate=fake)
    request = json.loads(fake.messages[1]['content'])
    assert request == {'parent': parent, 'plan': conditioned['effective_plan']}
    assert request['plan'] != conditioned['diagnosis']['plan']
    assert {'memory', 'diagnosis', 'adjustments', 'raw_preconditioner'}.isdisjoint(request)
    assert WITHDRAWN not in [u['text'] for u in request['plan']['updates']]
    assert len(request['plan']['updates']) == len(CASES[name]['effective'])
    assert saved['candidate_text'] == candidate and candidate.endswith(PRESERVED)
    assert WITHDRAWN.strip() not in candidate
    assert editor.load_editor(ed) == saved
    # Real Skill Diff is derived from Parent/Candidate, not an Update's local diff.
    update_patch = conditioned['raw_preconditioner']['adjustments'][0]['to']['patch']
    assert saved['actual_diff'] != update_patch
    assert apply_patch(parent, saved['actual_diff']) == candidate
    assert (ed / 'actual.diff').read_text() == actual_diff(parent, candidate)
    candidates = records(candidate)
    bundle = replay.build_replay(ed, parents, candidates)
    assert bundle['payload']['diff'] == saved['actual_diff']
    assert apply_patch(bundle['payload']['parent'], bundle['payload']['diff']) == bundle['candidate']
    assert bundle['payload']['plan']['updates'] == [
        {k: u[k] for k in ('id', 'text')} for u in conditioned['effective_plan']['updates']]
    # Substitution with the Preconditioner patch cannot silently become Replay evidence.
    (ed / 'actual.diff').write_text(update_patch)
    with pytest.raises(ValueError): replay.build_replay(ed, parents, candidates)


# These are intentionally semantic failures. Their labels come from the review,
# not a string-based semantic classifier or an actual model response.
BAD_CASES = [
    ('redirect', 'restore_blanket_ban'),
    ('redirect', 'restore_withdrawn_requirement'),
    ('redirect', 'retain_conflicting_parent_rule'),
    ('widen', 'turn_permission_into_obligation'),
    ('coordinate', 'omit_readiness_dependency'),
    ('coordinate', 'remove_unrelated_preservation'),
]


@pytest.mark.parametrize('name,violation', BAD_CASES, ids=[v for _, v in BAD_CASES])
def test_structural_validity_is_not_semantic_fidelity(tmp_path, name, violation):
    _, pd, _, parent, faithful = prepare(tmp_path, name)
    bad = faithful
    if violation == 'restore_blanket_ban':
        bad = '# Skill\nNever return to a previously visited location.\n' + PRESERVED + 'Maintain the goal.\n'
    elif violation == 'restore_withdrawn_requirement': bad += WITHDRAWN
    elif violation == 'retain_conflicting_parent_rule': bad += CASES[name]['old'][0]
    elif violation == 'turn_permission_into_obligation':
        bad = '# Skill\nAlways use B before considering A.\n' + PRESERVED
    elif violation == 'omit_readiness_dependency':
        bad = '# Skill\nRetry immediately after any repair.\n' + CASES[name]['effective'][1] + PRESERVED
    elif violation == 'remove_unrelated_preservation': bad = bad.replace(PRESERVED, '')
    output = {'patch': actual_diff(parent, bad), 'reason': 'Deliberately unfaithful offline counterexample.'}
    assert validate_editor(output, parent) == ('candidate', bad)
    ed = tmp_path / 'editor'
    saved = editor.run_editor(pd, ed, generate=Fake(output))
    assert read(ed / 'validation.json')['valid'] is True
    assert editor.load_editor(ed)['candidate_text'] == bad != faithful
    # Even an erroneous implementation must be recorded as the ACTUAL edit.
    assert apply_patch(parent, saved['actual_diff']) == bad
