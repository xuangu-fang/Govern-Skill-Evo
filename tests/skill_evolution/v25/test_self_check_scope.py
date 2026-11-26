"""Reproduce four self-check scopes offline; no inference or model evaluation."""
import json
from pathlib import Path

import openpyxl
import pytest

FIXTURES = Path(__file__).parent/'fixtures/self_check_scope'
SCENARIOS = json.loads((FIXTURES/'scenarios.json').read_text())['scenarios']
EVALUATION = json.loads((FIXTURES/'evaluation.json').read_text())


@pytest.mark.parametrize('scenario,expected', zip(SCENARIOS, EVALUATION['cases']),
                         ids=[s['id'] for s in SCENARIOS])
def test_observed_property_and_correctness_are_distinct(tmp_path, scenario, expected):
    """Demonstrate each premise with a real save/read, not a semantic evaluator."""
    assert expected['scenario'] == scenario['id']
    wb = openpyxl.Workbook()
    ws = wb.active
    ws['A1'], ws['A2'] = scenario['source_values']
    ws['B1'] = scenario['saved_cell']
    path = tmp_path/'output.xlsx'
    wb.save(path)
    wb.close()
    with open(path, 'rb') as stream:
        output = openpyxl.load_workbook(stream, data_only=True)
        value = output.active['B1'].value
        source_sum = output.active['A1'].value + output.active['A2'].value
        output.close()
    checks = {
        'non_empty': lambda: value is not None,
        'equals_program_value': lambda: value == scenario['program_computed_value'],
        'equals_source_sum': lambda: value == source_sum,
    }
    assert checks[scenario['self_check']]() is expected['expected_self_check']
    assert value == expected['expected_readback']
    assert (value == sum(scenario['source_values'])) is expected['expected_sum_requirement']
    if scenario['id'] == 'missing_formula_cache_detected':
        output = openpyxl.load_workbook(path, data_only=False)
        assert output.active['B1'].value == '=SUM(A1:A2)'
        output.close()


def test_evaluator_material_is_separate_and_no_semantic_run_is_claimed():
    assert EVALUATION['model_visible'] is False
    assert EVALUATION['model_evaluation'] == 'not_run'
    assert len(SCENARIOS) == 4
    assert {s['id'] for s in SCENARIOS} == {c['scenario'] for c in EVALUATION['cases']}
    for scenario in SCENARIOS:
        assert not any(k.startswith('expected') for k in scenario)
        assert 'supported_conclusion' not in scenario
