"""P2-D full mock workflow; structural acceptance is never semantic approval."""
import json

import pytest

from src.skill_evolution.v23.editor import actual_diff
from src.skill_evolution.v23_3 import diagnosis, editor, preconditioner as pc
from tests.skill_evolution.v23_3.helpers import Fake, keep, patch_result, read, scenario
from tests.skill_evolution.v23_3.test_preconditioner import upstream


@pytest.mark.parametrize("name", [
    "single", "linked", "cross", "broad", "keep", "withdraw",
    "no_change", "need_evidence", "semantic_risk",
])
def test_full_mock_chain(upstream, tmp_path, name, request):
    gd, dd, original, pd = upstream
    raw = keep()
    if name in ("single", "linked", "cross", "broad"):
        raw = patch_result(original, scenario("R05", name)["patches"])
    elif name == "semantic_risk":
        text = original["diagnosis"]["plan"]["updates"][0]["text"]
        raw = patch_result(original, {"u1": actual_diff(
            text, text + "- 每个类别采样一次即可结束。\n")})
    elif name in ("withdraw", "no_change"):
        chosen = original["diagnosis"]["plan"]["updates"]
        if name == "withdraw": chosen = chosen[:1]
        raw["adjustments"] = [{"from": [u["id"]], "to": [], "basis": u["basis"],
                               "reason": "Human mock withdrawal."} for u in chosen]
        raw["checks"] = []
    if name in ("no_change", "need_evidence"): raw["decision"] = name
    fake_pc = Fake(raw)
    saved = pc.run_preconditioner(gd, dd, pd, generate=fake_pc,
                                 memory=original["memory"], max_input_chars=4000000)
    assert fake_pc.calls == 1
    assert saved["diagnosis"] == original["diagnosis"]
    assert saved["facts"]["parent"] == original["facts"]["parent"]
    assert saved["memory"] == original["memory"]
    ed = tmp_path / "editor"
    if saved["effective_plan"] is None:
        fake_editor = Fake({"patch": "", "reason": "Should not run"})
        with pytest.raises(ValueError):
            editor.run_editor(pd, ed, generate=fake_editor)
        assert fake_editor.calls == 0 and not ed.exists()
    else:
        effective = saved["effective_plan"]
        parent = original["facts"]["parent"]
        # Human mock Editor construction, not a learned strategy or faithful-edit score.
        candidate = parent + "\n## Offline human fixture\n" + "\n".join(
            u["text"] for u in effective["updates"])
        fake_editor = Fake({"patch": actual_diff(parent, candidate),
                            "reason": "Human integration fixture; behavioral validity untested."})
        result = editor.run_editor(pd, ed, generate=fake_editor, max_input_chars=4000000)
        assert json.loads(fake_editor.messages[1]["content"])["plan"] == effective
        assert fake_editor.calls == 1
        assert result["candidate_text"] == candidate
        assert editor.load_editor(ed) == result
        assert (ed / "candidate.md").read_bytes() == candidate.encode()
        assert (ed / "actual.diff").read_bytes() == actual_diff(parent, candidate).encode()
        if name == "semantic_risk":
            assert "每个类别采样一次即可结束" in candidate
            request.node.user_properties.append((
                "semantic_validity", "NOT_VERIFIED: deliberately unsupported stopping rule"))
    assert diagnosis.load_diagnosis(dd)["diagnosis"] == original["diagnosis"]
    assert pc.load_preconditioner(pd) == saved
    request.node.user_properties.append(("evidence_kind", "human_mock_engineering_only"))


def test_old_single_line_entire_chain_without_granularity_claim(upstream, tmp_path):
    gd, _, original, _ = upstream
    value = read("experiments/methods/v23_3/p1r_multiline_001/fixtures/R05.original.json")
    dd, pd, ed = (tmp_path / name for name in ("old_diag", "old_pc", "old_editor"))
    saved = diagnosis.run_diagnosis(gd, dd, generate=Fake(value), max_input_chars=4000000)
    old = value["plan"]["updates"][0]["text"]
    assert "\n" not in old
    new = old + " Human test-only additional condition."
    raw = patch_result(saved, {"u1": actual_diff(old, new)})
    conditioned = pc.run_preconditioner(gd, dd, pd, generate=Fake(raw),
                                       memory=original["memory"], max_input_chars=4000000)
    assert conditioned["effective_plan"]["updates"][0]["text"] == new
    assert "\n" not in conditioned["effective_plan"]["updates"][0]["text"]
    parent = saved["facts"]["parent"]
    result = editor.run_editor(pd, ed, generate=Fake({
        "patch": actual_diff(parent, parent + "\n" + new),
        "reason": "Human single-line compatibility fixture."}), max_input_chars=4000000)
    assert editor.load_editor(ed) == result
    assert result["diagnosis"] == value


def test_cross_stage_wrong_current_memory_and_editor_config_rejected(upstream, tmp_path):
    gd, dd, original, pd = upstream
    pc.run_preconditioner(gd, dd, pd, generate=Fake(keep()),
                          memory=original["memory"], max_input_chars=4000000)
    # Resume must not quietly replace the frozen memory snapshot with an empty one.
    fake = Fake(keep())
    with pytest.raises(ValueError):
        pc.run_preconditioner(gd, dd, pd, generate=fake, max_input_chars=4000000)
    assert fake.calls == 0
    ed = tmp_path / "editor"
    fake_editor = Fake({"patch": "", "reason": "Human no-change fixture."})
    with pytest.raises(ValueError):
        editor.run_editor(pd, ed, generate=fake_editor, max_input_chars=1)
    with pytest.raises(ValueError):
        editor.run_editor(pd, ed, generate=fake_editor, call_config={"different": True},
                          max_input_chars=4000000)
    assert fake_editor.calls == 0 and not ed.exists()
    editor.run_editor(pd, ed, generate=fake_editor, max_input_chars=4000000)
    with pytest.raises(ValueError):
        editor.load_editor(ed, expected_call_config={"different": True})
    with pytest.raises(ValueError):
        editor.load_editor(ed, expected_preconditioner={})
