"""Integration with accepted views, complete archives, and old saved runs."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from experiments.methods.v23_3.archive_io import materialized

from src.skill_evolution.v23 import preconditioner as old_pc
from src.skill_evolution.v23.memory import empty_memory
from src.skill_evolution.v23_3 import preconditioner as pc
from src.skill_evolution.v23_3.memory_view import FORMAT, LEGACY, compact_memory, project_messages
from tests.skill_evolution.v23_3.helpers import Fake, keep, read
from tests.skill_evolution.v23_3.test_preconditioner import upstream

ACCEPTED = Path("experiments/methods/v23_3/memory_compaction_v3_validation_001")
ORIGINAL = ACCEPTED.parent / "memory_compaction_offline_001"


@pytest.mark.parametrize("case", ["R04", "R05", "R06", "P3A_A", "P3A_B"])
def test_projection_equals_accepted_view_exactly(case):
    full = read(ORIGINAL / "cases" / case / "original_payload.json")["memory"]
    untouched = deepcopy(full)
    assert compact_memory(full) == read(ACCEPTED / "cases" / case / "compact_payload.json")["memory"]
    assert full == untouched


def test_empty_memory_and_invalid_source():
    assert compact_memory(empty_memory())["sources"] == {}
    full = read(ORIGINAL / "cases/R05/original_payload.json")["memory"]
    full["sources"]["S1_R03/Q6"]["run"]["steps"][25]["step"] = "Q5:26"
    with pytest.raises(ValueError):
        compact_memory(full)


def test_same_ab_input_and_unchanged_original_policy(upstream):
    saved = upstream[2]
    a = project_messages(old_pc.messages_for(saved))
    b = pc.messages_for(saved)
    assert a[1] == b[1]
    assert a[0]["content"].startswith(old_pc.messages_for(saved)[0]["content"])
    assert b[0]["content"].startswith(pc.messages_for(saved, memory_view=LEGACY)[0]["content"])
    assert json.loads(b[1]["content"])["memory"]["format"] == FORMAT
    assert "format" not in old_pc.preconditioner_input(saved)["memory"]


def test_old_preconditioner_handoff_to_current_editor(tmp_path):
    with materialized(Path("experiments/methods/v23_3/p2_offline_001/mock_chain")) as root:
        before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        saved = pc.load_preconditioner(root / "preconditioner")
        assert "memory_view" not in read(root / "preconditioner/run.json")
        assert read(root / "preconditioner/messages.json") == pc.messages_for(saved, memory_view=LEGACY)
        from src.skill_evolution.v23_3 import editor
        # The historical response is an offline fixture, not a fresh model decision.
        # Save and reload a new archive with the current Prompt, leaving history intact.
        fake = Fake(read(root / "editor/editor.json"))
        out = tmp_path / "current_editor"
        result = editor.run_editor(root / "preconditioner", out, generate=fake,
                                   max_input_chars=4000000)
        assert fake.messages == editor.messages_for(saved)
        assert (out / "prompt.md").read_text() == fake.messages[0]["content"]
        assert result["effective_plan"] == saved["effective_plan"]
        assert editor.load_editor(out, expected_preconditioner=saved) == result
        assert editor.run_editor(root / "preconditioner", out, generate=fake,
                                 max_input_chars=4000000) == result
        assert fake.calls == 1
        assert before == {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_archive_view_version_resume_and_tamper(upstream):
    gd, dd, saved, out = upstream
    fake = Fake(keep())
    result = pc.run_preconditioner(gd, dd, out, generate=fake, memory=saved["memory"],
                                  max_input_chars=4000000)
    assert result["memory"] == saved["memory"]
    assert read(out / "run.json")["memory_view"] == FORMAT
    with pytest.raises(ValueError):
        pc.run_preconditioner(gd, dd, out, generate=fake, memory=saved["memory"],
                              memory_view=LEGACY, max_input_chars=4000000)
    assert fake.calls == 1
    meta = read(out / "run.json")
    meta["memory_view"] = "unknown"
    (out / "run.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        pc.load_preconditioner(out)
    # Removing the version must not allow a compact archive to masquerade as legacy.
    del meta["memory_view"]
    (out / "run.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        pc.load_preconditioner(out)


def test_new_explicit_legacy_archive(upstream):
    gd, dd, saved, out = upstream
    fake = Fake(keep())
    result = pc.run_preconditioner(gd, dd, out, generate=fake, memory=saved["memory"],
                                  memory_view=LEGACY, max_input_chars=4000000)
    assert read(out / "model_input.json") == old_pc.preconditioner_input(saved)
    assert pc.load_preconditioner(out) == result
