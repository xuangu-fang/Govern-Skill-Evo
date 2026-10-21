"""Extract checkable evidence for the manual audit; no semantic success scoring."""
from copy import deepcopy

from .run import HERE, read, write
from .compact import menus_for


def event(original, view, key, number):
    old = original["sources"][key]["run"]["steps"][number - 1]
    source = view["sources"][key]
    trace = source["run"]["trace"][number - 1]
    assert trace == {k: old[k] for k in ("step", "action", "feedback")}
    for window in source["windows"]:
        if window["start"] <= number <= window["end"]:
            index = number - window["start"]
            before = window["before"] if index == 0 else window["after"][index - 1]
            after = window["after"][index]
            assert before == old["before"] and after == old["after"]
            menus = menus_for(view, source)
            for state in (before, after):
                cid = state["commands_ref"]
                if cid is not None:
                    assert menus[cid] == original["sources"][key]["command_sets"][cid]
            return {"source": key, **deepcopy(old), "full_detail_delivered": True,
                    "before_commands": deepcopy(menus.get(before["commands_ref"])),
                    "after_commands": deepcopy(menus.get(after["commands_ref"]))}
    return {"source": key, **deepcopy(trace), "full_detail_delivered": False,
            "not_delivered": ["before observation/menu", "after observation/menu"]}


def main():
    examples = []
    for label in ("R04", "R05", "R06"):
        folder = HERE / "cases" / label
        original = read(folder / "original_payload.json")["memory"]
        view = read(folder / "compact_payload.json")["memory"]
        # Every numeric citation in every entry has its exact state/menu delivered.
        checked = 0
        for entry in original["entries"]:
            for ref in entry["evidence"]:
                context, local = ref.rsplit("/", 1)
                run, _, number = local.partition(":")
                if number.isdecimal() and int(number) > 0:
                    assert event(original, view, f"{context}/{run}", int(number))["full_detail_delivered"]
                    checked += 1
        specimens = []
        targets = {
            "S1_R03/Q4": [12, 13, 15, 17],
            "S1_R03/P2": [15, 16, 18, 20],
            "S1_R03/Q2": [25, 30, 36, 50],
            "S1_R03/P6": [32, 33, 36, 38],
            "S1_R03/Q6": [4, 10, 15, 20, 26, 37, 47, 48, 49, 50],
        }
        if label in ("R05", "R06"):
            # Actual operation-precondition anchors from the active M7.
            targets.update({"S1_R04/Q3": [5, 6, 7], "S1_R04/Q4": [5, 6, 7],
                            "S1_R03/P8": [19, 20], "S1_R03/Q8": [7]})
        if label == "R06":
            targets.update({
                "S1_R05/P6": [1, 2, 3, 31, 49, 50],
                "S1_R05/Q6": [12, 16, 17, 19, 21],
                "S1_R05/P8": [18, 19, 50], "S1_R05/Q8": [18, 19, 21, 23],
                "S1_R05/P7": [5, 7, 9, 50], "S1_R05/Q7": [2, 50],
                "S1_R05/P10": [32, 38], "S1_R05/Q10": [40, 46],
            })
        for key, numbers in targets.items():
            if key not in original["sources"]:
                continue
            specimens.extend(event(original, view, key, n) for n in numbers)
        examples.append({
            "case": label, "numeric_evidence_occurrences_verified": checked,
            "specimens": specimens,
            "notice": "Raw evidence extraction and equality checks only; semantic assessment is in EVIDENCE_AUDIT.md.",
        })
    write(HERE / "results/evidence_specimens.json", examples)
    a = read(HERE / "cases/P3A_A/compact_messages.json")
    b = read(HERE / "cases/P3A_B/compact_messages.json")
    assert a[1] == b[1]
    assert a[0] != b[0]
    write(HERE / "results/ab_input_checks.json",
          {"same_compact_user_content": True, "different_method_system_prompts": True,
           "same_format_instructions": True, "model_calls": 0})
    for example in examples:
        print(example["case"], "numeric citation occurrences checked",
              example["numeric_evidence_occurrences_verified"],
              "manual-audit specimens", len(example["specimens"]))


if __name__ == "__main__":
    main()
