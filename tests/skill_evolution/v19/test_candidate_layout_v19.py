import pytest
from src.skill_evolution.v19.candidate_layout_v19 import apply_layout
from src.skill_evolution.v19.edit_tracking_v19 import digest, _apply_segments, reconstruct_candidate


def receipt(before, removed, offset):
    after=before[:offset]+before[offset+len(removed):]
    return dict(schema_version='candidate_layout_v19.1', authorization='USER_REQUESTED_FLAT_RULE_LAYOUT',
        source_sha256=digest(before), candidate_sha256=digest(after), offset=offset, removed_text=removed)


def test_flatten_preserves_rule_writer_and_reconstruction():
    parent='# Skill\n\n## Empty\n'
    edit=dict(edit_id='E1', operation='ADD', target_blocks=[], after_text='Do this.\n')
    before=reconstruct_candidate(parent,[edit]);layout=receipt(before,'## Empty\n\n',len('# Skill\n\n'))
    after,segments,events=_apply_segments(parent,[(parent,None,())],[edit],layout=layout)
    assert after=='# Skill\n\nDo this.\n'
    assert any(text=='Do this.\n' and writer=='E1' for text,writer,_ in segments)
    assert len(events)==1
    assert reconstruct_candidate(parent,[edit],layout=layout)==after


def test_no_rule_body_deletion_or_digest_tamper():
    text='# Skill\n\nDo this.\n'
    with pytest.raises(ValueError,match='only section headings'):
        apply_layout(text,receipt(text,'Do this.\n',len('# Skill\n\n')))
    layout=receipt(text,'\n',len('# Skill\n'))
    with pytest.raises(ValueError,match='source mismatch'):
        apply_layout(text+'changed',layout)


def test_cannot_delete_heading_written_by_learned_edit():
    parent='# Skill\n'
    edit=dict(edit_id='E1', operation='ADD', target_blocks=[], after_text='## Learned\n')
    before=reconstruct_candidate(parent,[edit]);layout=receipt(before,'## Learned\n',len('# Skill\n\n'))
    with pytest.raises(ValueError,match='learned rule text'):
        _apply_segments(parent,[(parent,None,())],[edit],layout=layout)


def test_flat_policy_preserves_bodies_and_lineage():
    from src.skill_evolution.v19.candidate_layout_v19 import FLAT_LAYOUT
    parent='# Skill\n\n## First\nKeep this rule.\n\n## Empty\n'
    edit=dict(edit_id='E1',operation='ADD',target_blocks=[],after_text='New rule.\n')
    after,segments,_=_apply_segments(parent,[(parent,None,())],[edit],layout=FLAT_LAYOUT)
    assert after=='# Skill\n\nKeep this rule.\n\n\nNew rule.\n'
    assert reconstruct_candidate(parent,[edit],layout=FLAT_LAYOUT)==after
    assert any(text=='New rule.\n' and writer=='E1' for text,writer,_ in segments)
    assert 'Keep this rule.' in after


def test_editor_policy_uses_known_provenance_not_arbitrary_domain_numbers():
    from src.skill_evolution.v19.editor_policy_v19 import internal_ids, validate_text
    ids=internal_ids({'group_id':'GROUP-77','context_ref':'CTX-44','tool':{'name':'book_reservation'}})
    for text in ('## Recovery\nDo this.', 'Follow GROUP-77.', 'Use CTX-44.', 'Follow CF/unknown.'):
        with pytest.raises(ValueError):validate_text(text,ids)
    validate_text('Call book_reservation for flight AB123 with fare code C002.',ids)


def test_flat_policy_never_erases_newly_authored_heading():
    from src.skill_evolution.v19.candidate_layout_v19 import FLAT_LAYOUT
    parent='# Skill\n'
    edit=dict(edit_id='E1',operation='ADD',target_blocks=[],after_text='## New category\nRule.\n')
    with pytest.raises(ValueError,match='learned rule text'):
        _apply_segments(parent,[(parent,None,())],[edit],layout=FLAT_LAYOUT)
