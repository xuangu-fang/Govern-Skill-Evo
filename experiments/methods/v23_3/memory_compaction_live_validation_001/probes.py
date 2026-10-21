"""Fixed factual comprehension checks; expected answers never enter model input."""
from copy import deepcopy
import json

from experiments.methods.v23_3.memory_compaction_offline_001.compact import (
    menus_for, validate_view,
)


def build_probe(original, compact, *, case):
    memory, view = original["memory"], compact["memory"]
    validate_view(view, memory)
    questions, expected = [], {}

    def add(qid, question, answer):
        questions.append({"id": qid, "question": question})
        expected[qid] = deepcopy(answer)

    def step(key, n):
        return memory["sources"][key]["run"]["steps"][n - 1]

    def full_state(key, n, side):
        source = view["sources"][key]
        for w in source["windows"]:
            if w["start"] <= n <= w["end"]:
                i = n - w["start"]
                state = (w["before"] if i == 0 else w["after"][i - 1]) if side == "before" else w["after"][i]
                assert state == step(key, n)[side]
                return state
        raise ValueError("Probe assumes unavailable detailed state")

    add("window_start",
        "Return the exact before-state of S1_R03/Q2:23 as "
        '{"observation": string, "commands_ref": string_or_null}.',
        full_state("S1_R03/Q2", 23, "before"))
    add("inside_window",
        "Return the exact before-state of S1_R03/Q4:13 as "
        '{"observation": string, "commands_ref": string_or_null}.',
        full_state("S1_R03/Q4", 13, "before"))

    # Find a real same-name, different-content local menu collision across contexts.
    candidates = {}
    collision = None
    for key, source in view["sources"].items():
        if "run" not in source:
            continue
        for cid, commands in menus_for(view, source).items():
            for prior_key, prior_commands in candidates.get(cid, []):
                if prior_key.split("/")[0] != key.split("/")[0] and prior_commands != commands:
                    collision = [(prior_key, cid, prior_commands), (key, cid, commands)]
                    break
            if collision:
                break
            candidates.setdefault(cid, []).append((key, commands))
        if collision:
            break
    assert collision is not None
    a, b = collision
    add("menu_namespaces",
        f"Resolve local command table {a[1]} separately in {a[0]} and {b[0]}. "
        'Return {"first":{"count":integer,"first_three":[strings]},'
        '"second":{"count":integer,"first_three":[strings]},"same_contents":boolean}. '
        "First/second refer to those sources in the order given; preserve list order.",
        {"first": {"count": len(a[2]), "first_three": a[2][:3]},
         "second": {"count": len(b[2]), "first_three": b[2][:3]},
         "same_contents": False})
    key, n = "S1_R04/Q3", 5
    state = full_state(key, n, "before")
    commands = menus_for(view, view["sources"][key])[state["commands_ref"]]
    add("operation_precondition",
        'For S1_R04/Q3:5 return {"before_observation":string,"commands_ref":string,'
        '"pool_ref":string,"heat_is_listed":boolean,"action":string}. '
        'heat_is_listed tests the exact command "heat potato 3 with microwave 1" '
        "in the before-state menu, not whether heat later succeeded.",
        {"before_observation": state["observation"], "commands_ref": state["commands_ref"],
         "pool_ref": view["sources"][key]["command_sets"][state["commands_ref"]],
         "heat_is_listed": "heat potato 3 with microwave 1" in commands,
         "action": step(key, n)["action"]})
    add("omitted_precondition",
        'For S1_R03/Q6:26 return {"action":string,'
        '"recorded_action_in_admissible_commands":boolean,'
        '"exact_before_observation":string_or_null,"complete_before_menu":array_or_null}. '
        "Use null when the exact before-state/menu is not supplied. Do not infer it from "
        "nearby/repeated actions or the recorded legality flag.",
        {"action": step("S1_R03/Q6", 26)["action"],
         "recorded_action_in_admissible_commands":
             step("S1_R03/Q6", 26)["feedback"]["action_in_admissible_commands"],
         "exact_before_observation": None, "complete_before_menu": None})
    add("omitted_after",
        'For S1_R03/Q2:36 return {"action":string,"exact_after_observation":string_or_null}. '
        "Use only explicitly supplied state evidence; repeating a location does not "
        "authorize reconstructing an omitted observation.",
        {"action": step("S1_R03/Q2", 36)["action"], "exact_after_observation": None})
    trace = view["sources"]["S1_R03/Q2"]["run"]["trace"]
    add("whole_trace",
        'Across the entire S1_R03/Q2 trace, return {"countertop2_steps":[step_ID_strings],'
        '"countertop3_steps":[step_ID_strings],"trace_length":integer,"outcome":object}. '
        'Match the exact actions "go to countertop 2" and "go to countertop 3".',
        {"countertop2_steps": [s["step"] for s in trace if s["action"] == "go to countertop 2"],
         "countertop3_steps": [s["step"] for s in trace if s["action"] == "go to countertop 3"],
         "trace_length": len(trace), "outcome": view["sources"]["S1_R03/Q2"]["run"]["outcome"]})
    actions = ["take bread 1 from diningtable 1", "cool bread 1 with fridge 1",
               "move bread 1 to countertop 1"]
    trace = view["sources"]["S1_R03/Q4"]["run"]["trace"]
    add("action_order",
        'In S1_R03/Q4, return {"steps":[step_ID_strings],"success":boolean}, listing the '
        "first occurrence of each exact action in this requested order: " + json.dumps(actions) + ".",
        {"steps": [next(s["step"] for s in trace if s["action"] == action) for action in actions],
         "success": view["sources"]["S1_R03/Q4"]["run"]["outcome"]["success"]})
    source = view["sources"]["S1_R03/Q2"]
    add("coverage",
        'For S1_R03/Q2 return {"detail_coverage":string,"detailed_step_count":integer,'
        '"omitted_detail_ranges":[[start,end],...]}. Count only steps inside declared windows, '
        "not additionally exposed boundary states.",
        {"detail_coverage": source["detail_coverage"],
         "detailed_step_count": sum(w["end"] - w["start"] + 1 for w in source["windows"]),
         "omitted_detail_ranges": source["omitted_detail_ranges"]})
    add("mixed_response",
        'Compare S1_R03/P2 and S1_R03/Q2. Return '
        '{"parent_success":boolean,"parent_steps":integer,'
        '"candidate_success":boolean,"candidate_steps":integer}.',
        {"parent_success": view["sources"]["S1_R03/P2"]["run"]["outcome"]["success"],
         "parent_steps": len(view["sources"]["S1_R03/P2"]["run"]["trace"]),
         "candidate_success": view["sources"]["S1_R03/Q2"]["run"]["outcome"]["success"],
         "candidate_steps": len(view["sources"]["S1_R03/Q2"]["run"]["trace"])})
    source_keys = [k for k in view["sources"] if k.startswith("S1_R03/") and not k.endswith("/diff")]
    add("source_coverage",
        'For historical context S1_R03 return {"supplied_execution_sources":integer,'
        '"all_ten_parent_candidate_pairs_supplied":boolean}. Count only actual sources, '
        "not claims in knowledge or present-round runs.",
        {"supplied_execution_sources": len(source_keys),
         "all_ten_parent_candidate_pairs_supplied":
             all(f"S1_R03/{side}{i}" in source_keys for side in ("P", "Q") for i in range(1, 11))})
    if case == "R06":
        assert full_state("S1_R05/P6", 3, "after") and full_state("S1_R05/Q6", 16, "after")
        add("instance_vs_category",
            'Compare the reached locations at S1_R05/P6:3 and S1_R05/Q6:16. Return '
            '{"parent_location":string,"candidate_location":string,"same_receptacle_type":boolean}. '
            'Use location names as written in actions, without the "go to " prefix. '
            "Evaluate the raw evidence even if knowledge describes a new family.",
            {"parent_location": step("S1_R05/P6", 3)["action"].removeprefix("go to "),
             "candidate_location": step("S1_R05/Q6", 16)["action"].removeprefix("go to "),
             "same_receptacle_type": True})
        diff = memory["sources"]["S1_R05/diff"]["diff"]
        fragment = next(line for line in diff.splitlines()
                        if line.startswith("+") and "distinct receptacle families" in line)
        fragment = fragment.split("distinct receptacle families", 1)[1].split(".", 1)[0].strip()
        add("actual_edit",
            'In the ADDED search instruction of S1_R05/diff, return {"continuation":string}: '
            'the exact text after "distinct receptacle families" and before the next period. '
            "Trim surrounding whitespace and exclude the period. Read actual Diff, not knowledge.",
            {"continuation": fragment})
        add("absence_boundary",
            'Can the compact records for S1_R05/P7 and Q7 establish that no exact butterknife '
            'exists anywhere in the environment? Return {"global_absence_proven":boolean}. '
            "Base this on the evidence coverage, not on treating knowledge as an oracle.",
            {"global_absence_proven": False})
    return questions, expected


def score_answers(parsed, expected):
    require_shape = isinstance(parsed, dict) and set(parsed) == {"answers"} and isinstance(parsed["answers"], dict)
    if not require_shape:
        return {"passed": False, "schema_valid": False, "checks": {}}
    answers = parsed["answers"]
    exact = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    checks = {qid: {"passed": qid in answers and exact(answers[qid]) == exact(answer),
                    "expected": answer, "actual": answers.get(qid)}
              for qid, answer in expected.items()}
    return {"passed": set(answers) == set(expected) and all(c["passed"] for c in checks.values()),
            "schema_valid": True, "unexpected_ids": sorted(set(answers) - set(expected)), "checks": checks}
