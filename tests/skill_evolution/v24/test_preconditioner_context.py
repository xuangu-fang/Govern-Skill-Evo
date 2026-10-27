"""Integrated history/plan review boundaries; no model or environment execution."""
from copy import deepcopy
import json

import pytest

from src.skill_evolution.v24 import preconditioner as pc, output_feedback as feedback
from src.skill_evolution.v24.config import method_config, validate_method
from src.skill_evolution.v24.contracts.memory import empty_memory
from src.skill_evolution.v24.memory_view import KNOWLEDGE_ONLY, MEMORY_V3
from src.skill_evolution.v24.update_patch import normalize_update_patches
from tests.skill_evolution.v23.test_diagnosis import make_grouping
from src.skill_evolution.v23.grouping import load_grouping
from tests.skill_evolution.v23.test_preconditioner import proposal
from tests.skill_evolution.v23_5.helpers import keep, revise, memory


@pytest.fixture
def saved(tmp_path):
    grouped = load_grouping(make_grouping(tmp_path, parent='Preserve the task goal.\n'))
    return {**grouped, 'diagnosis': proposal(), 'memory': empty_memory()}


@pytest.mark.parametrize('view', [KNOWLEDGE_ONLY, MEMORY_V3])
@pytest.mark.parametrize('policy', [feedback.LEGACY, feedback.POLICY])
def test_both_views_and_retry_prompts_preserve_reference_context(saved, view, policy):
    before = deepcopy(saved)
    internal = pc.preconditioner_input(saved)
    assert {g['group_id'] for g in internal['grouping']['groups']} == {'G1', 'G2'}
    messages = pc.messages_for(saved, memory_view=view, retry_policy=policy)
    visible = json.loads(messages[1]['content'])
    assert set(visible) == {'parent', 'plan', 'runs', 'command_sets', 'memory'}
    for field in ('parent', 'plan', 'runs', 'command_sets'):
        assert visible[field] == internal[field]
    assert visible['command_sets']
    assert visible == pc.model_input(saved, memory_view=view)
    prompt = messages[0]['content']
    assert 'Using historical Knowledge about actual edit–behavior responses is a core part' in prompt
    assert 'normally KEEP' not in prompt
    assert 'History is not required to correct a concrete plan defect.' in prompt
    assert 'do not separate them into exclusive categories or fixed passes' in prompt
    assert 'Command sets retain the available-action context' in prompt
    assert 'absence from one supplied menu\ndoes not establish permanent impossibility' in prompt
    assert 'Exploration is allowed: current problems' not in prompt
    assert '{{execution_context}}' not in prompt
    assert saved == before


def test_empty_memory_keep_and_inherited_provenance_preserve_plan(saved):
    payload = pc.preconditioner_input(saved)
    result = keep(payload)
    cid = next(iter(payload['command_sets']))
    result['adjustments'][0]['reason'] = f'Retain `u1`; `G1` is upstream provenance and `{cid}` supplies its action context.'
    _, effective = normalize_update_patches(result, payload)
    assert effective == payload['plan']


@pytest.mark.parametrize('ref', ['G2', 'P99:1', 'C999', 'M99'])
def test_unsupplied_references_are_rejected(saved, ref):
    payload = pc.preconditioner_input(saved)
    result = keep(payload)
    result['adjustments'][0]['reason'] = f'Claim based on `{ref}`.'
    with pytest.raises(ValueError, match='allowed reference set'):
        normalize_update_patches(result, payload)


def test_unreferenced_group_cannot_enter_checks(saved):
    payload = pc.preconditioner_input(saved)
    result = keep(payload)
    result['checks'] = [{'id': 'c1', 'update_ids': ['u1'], 'question': 'Does G2 improve?'}]
    with pytest.raises(ValueError, match='G2'):
        normalize_update_patches(result, payload)


@pytest.mark.parametrize('dimension', ['D', 'S', 'C'])
def test_history_based_adjustment_keeps_output_contract(saved, dimension):
    payload = pc.preconditioner_input(saved)
    saved['memory'] = payload['memory'] = memory(payload)
    visible = pc.model_input(saved)
    assert visible['memory']['entries'] == payload['memory']['entries']
    assert set(visible['memory']) == {'format', 'entries'}
    result = keep(payload)
    adjustment = revise(payload)
    adjustment['focus'] = [dimension]
    mid = payload['memory']['entries'][0]['id']
    adjustment['reason'] = f'`{mid}` motivates this adaptation; `P1:1` provides the current reference context.'
    result['adjustments'][0] = adjustment
    _, effective = normalize_update_patches(result, payload)
    assert effective['goal'] == payload['plan']['goal']
    assert effective['checks'] == payload['plan']['checks']
    assert effective['updates'][0]['basis'] == payload['plan']['updates'][0]['basis']
    assert effective['updates'][0]['text'] != payload['plan']['updates'][0]['text']
    assert [u['id'] for u in effective['updates']] == [u['id'] for u in payload['plan']['updates']]


@pytest.mark.parametrize('version', [
    'v23_5_preconditioner_knowledge_only_v1',
    'v24_preconditioner_knowledge_only_history_primary_v2',
])
def test_old_prompt_freeze_is_not_accepted_as_current(version):
    frozen = method_config()
    frozen['preconditioner_prompt'] = version
    with pytest.raises(ValueError, match='method freeze'):
        validate_method(frozen)


@pytest.mark.parametrize('view', [KNOWLEDGE_ONLY, MEMORY_V3])
@pytest.mark.parametrize('has_history', [False, True])
def test_plan_correction_needs_no_historical_citation_in_either_view(saved, view, has_history):
    payload = pc.preconditioner_input(saved)
    if has_history:
        payload['memory'] = memory(payload)
    before = deepcopy(payload)
    cid = next(iter(payload['command_sets']))
    result = keep(payload)
    adjustment = revise(payload, replacement='Use observations and available actions at the relevant state; preserve the task goal.\n')
    adjustment['change'] = 'Tie the action requirement to state-specific available information.'
    adjustment['reason'] = (f'`u1` needs a state-specific condition: `{cid}` records only its associated '
                            'state, and `P1:1` supplies current action context, not a global action inventory.')
    result['adjustments'][0] = adjustment
    _, effective = normalize_update_patches(result, payload, memory_view=view)
    assert effective['goal'] == payload['plan']['goal']
    assert effective['updates'][0]['text'] != payload['plan']['updates'][0]['text']
    assert [u['id'] for u in effective['updates']] == [u['id'] for u in payload['plan']['updates']]
    assert effective['checks'] == payload['plan']['checks']
    assert payload == before


@pytest.mark.parametrize('view', [KNOWLEDGE_ONLY, MEMORY_V3])
def test_empty_memory_withdrawal_preserves_remaining_updates_and_valid_checks(saved, view):
    payload = pc.preconditioner_input(saved)
    result = keep(payload)
    result['adjustments'][0] = {'target': 'u1', 'focus': ['D'],
                               'change': 'Withdraw the infeasible requirement.',
                               'reason': '`u1` assumes information beyond the supplied Actor context at `P1:1`.',
                               'to': []}
    result['checks'] = [c for c in payload['plan']['checks'] if 'u1' not in c['update_ids']]
    _, effective = normalize_update_patches(result, payload, memory_view=view)
    assert [u['id'] for u in effective['updates']] == [u['id'] for u in payload['plan']['updates'] if u['id'] != 'u1']
    assert effective['checks'] == result['checks']
