"""Same 11/14 factual checks, with only menu-address adaptation for v2."""
from copy import deepcopy
import re

from experiments.methods.v23_3.memory_compaction_live_validation_001.probes import (
    build_probe, score_answers,
)


def locate_local_menu(v1, source_key, cid):
    """Locate the same old menu by a state; no local C alias is exposed to the model."""
    source = v1["sources"][source_key]
    if source["run"]["initial"]["commands_ref"] == cid:
        return f"the initial state of {source_key}"
    context = source_key.rsplit("/", 1)[0]
    for w in source["windows"]:
        previous = w["before"]
        for n, after in enumerate(w["after"], w["start"]):
            step = f"{context}/{source['run']['trace'][n - 1]['step']}"
            if previous["commands_ref"] == cid:
                return f"the before-state of {step}"
            if after["commands_ref"] == cid:
                return f"the after-state of {step}"
            previous = after
    raise ValueError("Old menu has no delivered state anchor")


def adapted_probe(original, compact_v1, compact_v2, *, case):
    questions, old_answers = build_probe(original, compact_v1, case=case)
    answers = deepcopy(old_answers)
    v1, v2 = compact_v1["memory"], compact_v2["memory"]
    for qid, source_key, step_id in [
        ("window_start", "S1_R03/Q2", "S1_R03/Q2:23"),
        ("inside_window", "S1_R03/Q4", "S1_R03/Q4:13"),
    ]:
        before = next(s["before"] for s in v2["sources"][source_key]["detailed_steps"]
                      if s["step"] == step_id)
        assert before["observation"] == old_answers[qid]["observation"]
        assert before["commands_ref"] == v1["sources"][source_key]["command_sets"][
            old_answers[qid]["commands_ref"]]
        answers[qid] = deepcopy(before)
    answers["operation_precondition"]["commands_ref"] = old_answers["operation_precondition"]["pool_ref"]
    changes = []
    for question in questions:
        qid, old_text = question["id"], question["question"]
        if qid == "menu_namespaces":
            match = re.search(r"Resolve local command table (\S+) separately in (\S+) and (\S+)\.", old_text)
            assert match
            cid, first, second = match.groups()
            first_anchor, second_anchor = locate_local_menu(v1, first, cid), locate_local_menu(v1, second, cid)
            suffix = old_text.split(". ", 1)[1]
            question["question"] = (
                f"Compare the command menus referenced by {first_anchor} and {second_anchor}. "
                + suffix.replace("those sources", "those states"))
        elif qid == "operation_precondition":
            question["question"] += (
                " In v2 commands_ref directly names the global menu; "
                "report that same identifier as pool_ref.")
        changes.append({"id": qid, "question_changed": old_text != question["question"],
                        "old_question": old_text, "new_question": question["question"],
                        "answer_changed": answers[qid] != old_answers[qid]})
    # Normalize changed addresses back to v1 and verify all other answers unchanged.
    normalized = deepcopy(answers)
    for qid in ("window_start", "inside_window", "operation_precondition"):
        normalized[qid]["commands_ref"] = old_answers[qid]["commands_ref"]
    assert normalized == old_answers
    assert sum(c["question_changed"] for c in changes) == 2
    return questions, answers, changes
