"""Preconditioner input visibility and inherited Plan reference boundaries."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.skill_evolution.v25 import preconditioner
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from src.skill_evolution.v25.benchmarks.spreadsheetbench.evidence import preconditioner_input
from src.skill_evolution.v25.contracts.memory import empty_memory
from src.skill_evolution.v25.memory_view import KNOWLEDGE_ONLY
from src.skill_evolution.v25.update_patch import normalize_update_patches


ROOT = Path(__file__).resolve().parents[3]


def fixture():
    payload = json.loads((ROOT / 'docs/methods/v25/prompt_review/preconditioner_example.json').read_text())['input']
    payload['memory'] = empty_memory()
    group = payload['grouping']['groups'][0]
    group['members'] = ['P1']
    group['shared_basis'] = 'P1:1 applies the row loop.'
    other = deepcopy(group)
    other.update(group_id='G2', members=['P2'], shared_basis='P2:1 applies the row loop.')
    payload['grouping']['groups'].append(other)
    return payload


def keep(reason='The row coverage and preservation requirements in `Update:u1` remain appropriate for `Evidence:P1:0`.'):
    return {'adjustments': [{'target': 'u1', 'focus': [], 'change': 'KEEP',
                             'reason': reason, 'to': None}], 'checks': None}


def test_model_gets_plan_reference_runs_without_grouping_and_archive_is_unchanged():
    payload = fixture()
    saved = {'facts': {k: payload[k] for k in ('parent', 'runs')},
             'grouping': payload['grouping'], 'memory': payload['memory'],
             'diagnosis': {'decision': 'revise', 'reason': 'Review P1:1.', 'plan': payload['plan']}}
    before = deepcopy(saved)
    with using_benchmark(SpreadsheetBenchAdapter()):
        internal = preconditioner_input(saved)
        visible = preconditioner.model_input(saved)
    assert set(visible) == {'parent', 'plan', 'runs', 'memory'}
    assert visible['plan'] == payload['plan']
    assert visible['runs'] == payload['runs']
    assert visible['memory'] == {'format': 'memory_knowledge_only_v1', 'entries': []}
    assert internal['grouping'] == payload['grouping']
    assert saved == before


def test_empty_memory_keep_preserves_plan_and_inherited_group_provenance():
    payload = fixture()
    payload['plan']['checks'][0]['question'] += ' Preserve the Plan context from G1.'
    before = deepcopy(payload)
    with using_benchmark(SpreadsheetBenchAdapter()):
        _, effective = normalize_update_patches(keep('Retain `Update:u1`; `Group:G1` is its upstream Plan provenance.'), payload)
    assert effective == payload['plan']
    assert payload == before


@pytest.mark.parametrize('reason', [
    '`Group:G2` supports this adjustment.',
    'Group:G2 supports this adjustment.',
    '`Evidence:P99:1` supports this adjustment.',
    '`Memory:M99` motivates this adjustment.',
])
def test_unprovided_group_or_execution_or_memory_cannot_be_cited(reason):
    with using_benchmark(SpreadsheetBenchAdapter()), pytest.raises(ValueError, match='explicit reference|single-backtick'):
        normalize_update_patches(keep(reason), fixture())


def test_group_context_cannot_be_added_in_replacement_checks():
    result = keep()
    result['checks'] = [{'id': 'c1', 'update_ids': ['u1'], 'question': 'Does `Group:G2` improve?'}]
    with using_benchmark(SpreadsheetBenchAdapter()), pytest.raises(ValueError, match='G2'):
        normalize_update_patches(result, fixture())


def with_history(payload):
    """Synthetic reported history, not a model judgement or measured benefit."""
    payload['memory'] = {
        'entries': [{'id': 'M1', 'knowledge': [{
            'text': 'Including the final row helped coverage, but a footer was processed as data. '
                    'Use task-defined data boundaries when transferring this change.',
            'evidence': ['R_demo/diff', 'R_demo/P1:1'],
        }]}],
        'sources': {
            'R_demo/diff': {'parent': payload['parent'],
                            'diff': '--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-Exclude the last row.\n+Include the last row.\n',
                            'execution_context': {'description': 'Synthetic single-script execution.'}},
            'R_demo/P1': {'run': deepcopy(payload['runs'][0])},
        },
    }
    return payload


@pytest.mark.parametrize('history,reason', [
    (False, 'The requirement in `Update:u1` assumes that every populated row is data, '
            'but `Evidence:P2:0` distinguishes a footer; limit processing to task-defined data rows.'),
    (True, 'The requirement in `Update:u1` assumes that every populated row is data, '
           'but `Evidence:P2:0` distinguishes a footer; this correction does not rely on history.'),
    (True, '`Memory:M1` reveals the risk of treating a populated footer as data; `Evidence:P2:0` '
           'makes that distinction relevant to `Update:u1`. Narrow the requirement while '
           'retaining final-data-row coverage; broader effectiveness remains unverified.'),
])
def test_plan_correction_accepts_current_or_combined_grounds_without_history_requirement(history, reason):
    payload = fixture()
    original = '- Process every populated row, including the final row.\n'
    replacement = '- Process task-defined data rows, including the final data row; preserve footers.\n'
    payload['plan']['updates'][0]['text'] = original
    if history:
        with_history(payload)
    before = deepcopy(payload)
    result = {'adjustments': [{'target': 'u1', 'focus': ['S'],
                              'change': 'Limit processing to data rows while retaining final-data-row coverage.',
                              'reason': reason, 'to': {'patch':
                                  '--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-' + original + '+' + replacement}}],
              'checks': None}
    with using_benchmark(SpreadsheetBenchAdapter()):
        normalized, effective = normalize_update_patches(result, payload)
    assert effective['goal'] == before['plan']['goal']
    assert effective['updates'][0]['id'] == 'u1'
    assert effective['updates'][0]['text'] == replacement
    assert effective['checks'] == before['plan']['checks']
    assert ('M1' in normalized['adjustments'][0]['basis']) == ('`Memory:M1`' in reason)
    assert payload == before


def test_empty_memory_withdrawal_requires_resolving_dependent_checks():
    payload = fixture()
    result = {'adjustments': [{'target': 'u1', 'focus': ['D'],
                              'change': 'Withdraw the proposed requirement.',
                              'reason': '`Update:u1` cannot satisfy the task constraints described by `Evidence:P1:0`.',
                              'to': []}], 'checks': None}
    with using_benchmark(SpreadsheetBenchAdapter()):
        with pytest.raises(ValueError, match='checks='):
            normalize_update_patches(result, payload)
        result['checks'] = []
        normalized, effective = normalize_update_patches(result, payload)
    assert normalized['decision'] == 'no_change'
    assert effective is None


def test_history_primary_archive_is_not_reinterpreted_with_new_prompt(tmp_path):
    (tmp_path / 'input.json').write_text('{}')
    (tmp_path / 'run.json').write_text(json.dumps({
        'prompt_version': 'v25_preconditioner_history_primary_v2',
        'memory_view': KNOWLEDGE_ONLY,
    }))
    # Version rejection precedes upstream loading or any modification of the archive.
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(ValueError, match='Unsupported Preconditioner prompt version'):
        preconditioner.load_preconditioner(tmp_path)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
