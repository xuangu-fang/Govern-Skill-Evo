"""Shared authored fixtures; no model calls or measured semantic claims."""
from tests.skill_evolution.v29_2.test_diagnosis import proposal as original_proposal
from tests.skill_evolution.v29_2.test_preconditioner import decisions, memory_view
from tests.skill_evolution.v29_2.test_editor import offline, diff, output


def proposal():
    result = original_proposal()
    for update in result['plan']['updates']:
        update['basis'] = [ref for ref in update['basis'] if not ref.startswith('G')]
    return result
