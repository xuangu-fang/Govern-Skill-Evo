"""Frozen archive bridge and original Editor failure semantics, without network."""
import json
import pytest
from experiments.methods.v23_2.v23_2_response_behavior_001 import run as r
from src.skill_evolution.v23 import editor


def test_frozen_handoff_and_original_editor_null_stop(tmp_path):
    saved, frozen, cfg = r.inputs()
    seen=[]
    def generate(messages, dest):
        seen.append(messages)
        return {'content':json.dumps({'patch':None,'reason':'Cannot faithfully implement.'}),'finish_reason':'stop'}
    out=r.invoke_editor(tmp_path/'editor',generate,cfg['call_config'],cfg['max_input_chars'])
    assert seen == [editor.messages_for(saved)]
    assert out['editor_status']=='needs_revision' and out['candidate_text'] is None
    assert out['facts']['parent']==frozen['parent']
    assert out['effective_plan']==saved['effective_plan']
    assert editor.load_editor(tmp_path/'editor',expected_preconditioner=saved)==out
    assert editor.load_preconditioner is not r.load_handoff


def test_bridge_preserves_strict_patch_rejection(tmp_path):
    _,_,cfg=r.inputs()
    response={'patch':'--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1 +1 @@\n-Wrong parent\n+Replacement\n','reason':'Test invalid patch.'}
    with pytest.raises(ValueError,match='Parent context'):
        r.invoke_editor(tmp_path/'editor',lambda *_:{'content':json.dumps(response),'finish_reason':'stop'},cfg['call_config'],cfg['max_input_chars'])
    assert not (tmp_path/'editor/candidate.md').exists()
    assert (tmp_path/'editor/patch.diff').read_text()==response['patch']
