import pytest

from tests.skill_evolution.v19.test_evidence_review_v19 import setup, case, cases, final
from src.skill_evolution.v19.evidence_review_v19 import build_evidence_review_input, validate_evidence_review
from src.skill_evolution.v19.verified_compiler_v19 import compile_verified
from src.skill_evolution.v19.edit_tracking_v19 import encode


def source(case,kind):
    rules=sorted(case.payload['rules'])[:1]
    request=build_evidence_review_input(case,context_round=1,additional_rule_refs=rules)
    return request,validate_evidence_review(encode(final(request.payload,kind=kind)),request=request)


def compile_cases(setup,kinds):
    cs=cases(setup[2]);assert len(cs)>=len(kinds)
    # Low-level planner only: full generation restoration verifies complete Fusion
    # coverage before it calls this function.
    pairs=[source(c,k) for c,k in zip(cs,kinds)]
    # Fixture's real Parent is available through review_input.
    from tests.skill_evolution.v19.test_issue_fusion_v19 import review_input
    _,_,review=review_input(setup[2])
    return compile_verified({'review_input':review.payload},pairs)


@pytest.mark.parametrize('kind,operation',[('MISSING','ADD'),('NEEDS_REVISION','REPLACE'),('SHOULD_REMOVE','DELETE')])
def test_mapping(setup,kind,operation):
    value=compile_cases(setup,[kind])
    assert [u.operation for u in value.plan.edit_units]==[operation]
    assert value.plan.source_diagnosis_refs[0].startswith('ISSUE/')


def test_same_target_merge_preserves_sources(setup):
    value=compile_cases(setup,['NEEDS_REVISION','NEEDS_REVISION'])
    assert len(value.plan.edit_units)==1
    assert len(value.plan.edit_units[0].supporting_gap_refs)==2


def test_replace_delete_conflict(setup):
    with pytest.raises(ValueError,match='MIXED_OPERATION_TARGET_CONFLICT'):
        compile_cases(setup,['NEEDS_REVISION','SHOULD_REMOVE'])


def test_adds_not_semantically_deduplicated(setup):
    value=compile_cases(setup,['MISSING','MISSING'])
    assert len(value.plan.edit_units)==2
