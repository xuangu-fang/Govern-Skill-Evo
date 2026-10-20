"""Read-only V22 history audit; save V23 conversion and independently compare fields.

Run from the repository root with python -m scripts.analysis.v23.validate_grouping_history.
"""

import argparse
from collections import Counter
import json
from pathlib import Path

from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v23.facts import build_facts
from src.skill_evolution.v23.grouping import messages_for


def audit(paths, output):
    originals = [p.read_bytes() for p in paths]
    records = [json.loads(data) for data in originals]
    bundle = build_facts(records)
    facts = bundle["facts"]
    counts = Counter()
    for original, converted in zip(records, facts["runs"]):
        assert facts["parent"] == original["skill"]["text"]
        assert converted["initial"]["observation"] == original["initial_observation"]
        initial = [c for c in original["initial_admissible_commands"] if c != "help"]
        assert facts["command_sets"][converted["initial"]["commands_ref"]] == initial
        executed = [event for event in original["steps"] if event["phase"] == "executed"]
        assert len(converted["steps"]) == len(executed)
        for i, (old, new) in enumerate(zip(executed, converted["steps"])):
            expected_before = original["initial_observation"] if i == 0 else executed[i - 1]["observation"]
            assert new["before"]["observation"] == expected_before
            assert new["after"]["observation"] == old["observation"]
            assert new["action"] == old["action"]
            before_menu = [c for c in old["admissible_commands"] if c != "help"]
            assert facts["command_sets"][new["before"]["commands_ref"]] == before_menu
            for key in ("reward", "done", "won", "action_in_admissible_commands", "fallback"):
                if key in old:
                    assert new["feedback"][key] == old[key]
            if i + 1 < len(original["steps"]):
                after_menu = [c for c in original["steps"][i + 1]["admissible_commands"] if c != "help"]
                assert facts["command_sets"][new["after"]["commands_ref"]] == after_menu
                counts["restored_after_menus"] += 1
            else:
                assert new["after"]["commands_ref"] is None
                counts["missing_last_after_menus"] += 1
            counts["verified_steps"] += 1
            counts["filtered_help_occurrences"] += old["admissible_commands"].count("help")
        assert converted["outcome"]["status"] == original["status"]
        counts[original["status"]] += 1
    assert [p.read_bytes() for p in paths] == originals
    output.mkdir(parents=True, exist_ok=False)
    write_record(output / "input.json", bundle)
    write_record(output / "messages.json", messages_for(bundle))
    report = {"records": len(paths), "counts": dict(counts), "command_sets": len(facts["command_sets"]),
              "sources": [str(p) for p in paths], "source_files_unchanged": True,
              "prompt_comparison": "every recorded request equals reconstruction from saved protocol and state",
              "input_chars": len(json.dumps(messages_for(bundle), ensure_ascii=False)),
              "environment_executions": 0, "model_calls": 0}
    write_record(output / "report.json", report)
    print(json.dumps({k:v for k,v in report.items() if k != "sources"}, ensure_ascii=False))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.records, args.output)


if __name__ == "__main__":
    main()
