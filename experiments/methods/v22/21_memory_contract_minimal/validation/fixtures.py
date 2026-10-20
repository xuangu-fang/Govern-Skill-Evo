"""Eight independent real-evidence P1 probes; construction is strictly offline.

The archived 08 R2 effective Plan, actual Editor, Candidate and paired executions
are used together for learning. No result from these probes is a learning input.
Import this module in a fresh process using the 17 revision, never production src.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
REVISION = ROOT / "experiments/methods/v22/21_memory_contract_minimal/revision"
sys.path.insert(0, str(REVISION))
from src.adapters.alfworld.skill_runtime import digest, object_digest
from src.skill_evolution.v22 import grouped_update, memory_contract
from src.skill_evolution.v22.compact_cycle import make_diff
from src.skill_evolution.v22.compact_update import validate_editor
from src.skill_evolution.v22.effective_memory import validate_effective_learning
from src.skill_evolution.v22.grouped_representation import build_grouping_input, freeze_grouping, grouping_messages

assert Path(memory_contract.__file__).resolve().is_relative_to(REVISION.resolve()), "Wrong revision imported"
assert Path(grouped_update.__file__).resolve() == (
    ROOT / "experiments/methods/v22/20_memory_contract_fix/revision/src/skill_evolution/v22/grouped_update.py"
), "Wrong shared implementation imported"
V3 = "v22.unified_dsc.v3"
V4 = "v22.unified_dsc.v4"
REAL = ROOT / "artifacts/methods/v22/08_grouped_continual_fusion_resumed_20261015/rounds/r2"
GROUP_PROMPT = ROOT / "experiments/methods/v22/08_grouped_continual/config/grouping_prompt.md"
OUT = ROOT / "artifacts/methods/v22/21_memory_contract_minimal/preparation"


def read(path):
    return json.loads(Path(path).read_text())


def _relative(path):
    return str(Path(path).resolve().relative_to(ROOT.resolve()))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_manifest():
    names = ["context.json", "grouping.json", "grouping_input.json", "initial_plan.json",
             "effective_plan.json", "execution_plan.json", "candidate.json", "gate.json",
             "outputs/main_editor.json", "outputs/classification.json", "learning_input.json",
             "memory_before.json", "parent_sources.json", "candidate_sources.json", "candidate/actual.diff"]
    paths = [REAL / name for name in names] + [GROUP_PROMPT]
    for name in ("parent_sources.json", "candidate_sources.json"):
        for row in read(REAL / name):
            path = Path(row["trajectory"])
            assert _sha(path) == row["sha256"], path
            paths.append(path)
    return {_relative(path): {"sha256": _sha(path), "bytes": path.stat().st_size} for path in paths}


def material(profile):
    """Rebuild legal stage payloads with real execution identities, not hand splicing."""
    context, grouping, initial, effective, execution, candidate, gate, editor = [
        read(REAL / name) for name in (
            "context.json", "grouping.json", "initial_plan.json", "effective_plan.json",
            "execution_plan.json", "candidate.json", "gate.json", "outputs/main_editor.json")]
    parents, candidates = [[read(Path(row["trajectory"])) for row in read(REAL / name)]
                           for name in ("parent_sources.json", "candidate_sources.json")]
    source_manifest()
    current = grouped_update.diagnosis_payload(context, parents, grouping, profile=profile)
    grouping_input = build_grouping_input(current, context["round_id"], grouping["seed"])
    assert grouping_input == read(REAL / "grouping_input.json")
    assert freeze_grouping(read(REAL / "outputs/classification.json"), grouping_input,
                           GROUP_PROMPT.read_text()) == grouping
    fusion = grouped_update.update_payload(context, current, initial)
    editing = grouped_update.update_payload(context, current, effective)
    validate_editor(editor, editing)
    realized, realized_plan = grouped_update.realize_editor(editor, editing)
    assert realized == candidate and realized_plan == execution
    learning = grouped_update.prepare_grouped_learning(
        context, grouping, execution, candidate, parents, candidates, gate,
        editor=editor, profile=profile)
    old = read(REAL / "learning_input.json")
    for key in ("parent", "candidate", "actual_diff", "plan", "runs", "pairs",
                "memory", "grouping", "command_sets"):
        assert learning[key] == old[key], key
    assert learning["memory"] == read(REAL / "memory_before.json") == context["memory"]
    assert learning["actual_diff"] == (REAL / "candidate/actual.diff").read_text()
    assert learning["actual_diff"] == make_diff(context["parent"], candidate)
    return {"classification": grouping_input["model_input"], "diagnosis": current,
            "fusion": fusion, "editor": editing, "learn": learning,
            "classification_binding": grouping_input}


COMMON_CRITERIA = [
    "Strict full JSON and unchanged production output contracts; do not extract a suffix, repair output, or retry.",
    "References use original task/event/requirement/Watch/Effect IDs; shared-table indices are not new source IDs.",
    "Check statements against decoded original facts, including exact step commands and pre/post observation order.",
    "One sample at temperature 1 can expose a failure but cannot identify a causal representation effect or reliability rate.",
]
CRITERIA = {
    "classification": [
        "Partition all ten opaque task refs exactly once; analyze shared decision conditions, not task-name or success-only buckets.",
        "Preserve successful paths and distinct local conditions; no invented opportunities from another task's shared action table.",
    ],
    "diagnosis": [
        "Read ten real Parent executions; no historical Memory is visible. Propose Goal, adjustable Update, conditional scope, preservation and Watch, or a grounded legal no-update result.",
        "Parent events and group provenance must validate; group IDs are provenance coordinates rather than applicability boundaries.",
        "Respect actual current/two-pair observations and offered controls; untested benefit alone does not require blocking exploration.",
    ],
    "fusion": [
        "Use exactly the archived R2 initial Plan and R1 effective Memory. Keep, D alternatives, both S directions, C coordination and bounded exploration remain legal.",
        "Compare actual historical edit/conditions/response/limits with current expectations; citing an Effect is insufficient evidence of historical contribution.",
        "Separate current capability correction from historical evidence; limited historical search response does not prove an alternative strategy effective.",
        "Preserve Goal and relevant exceptions; history or same-group membership never creates an unobserved action opportunity.",
    ],
    "editor": [
        "Use the frozen archived R2 effective Plan, not any result of this validation. Candidate remains an unexecuted validation artifact.",
        "Compare actual diff against the complete effective strategy, conditions, modal strength, dependencies and exceptions; legal text mapping is necessary but not sufficient.",
        "Do not independently select new mandatory strategies or remove effective exceptions. needs_revision requires a concrete unresolved issue, not generally unknown benefit.",
    ],
    "learn": [
        "Use only the real matched 08 R2 effective/execution Plan, actual archived Editor, Candidate/diff, ten paired executions and R1 Memory; never use this validation's new Editor output.",
        "Separately check implementation, opportunities on each path, chosen actions and outcomes; a Parent opportunity is not a Candidate opportunity.",
        "Current commands describe that step's pre-action availability, and observations describe its response; shared dictionaries do not imply all actions apply at every step.",
        "Separate untriggered, unexecuted, untested and executed-but-unsuccessful. Whole-task success does not identify isolated edit causality.",
        "Any replacement/limit retirement changes only supported scope; preserve untested residual conditions while allowing evidence-supported expansion or revision.",
    ],
}


def build_cases(profile_v4=V4):
    """Return five new-representation probes and three matched v3 controls.

    Parameters/messages must be frozen by the caller before any dispatch. The
    controls differ only in the profile/consumption encoding identity and the
    encoding instructions, not the real facts or chosen update.
    """
    materials = {V3: material(V3), profile_v4: material(profile_v4)}
    order = [("classification_p1", "classification", profile_v4),
             ("diagnosis_p1", "diagnosis", profile_v4),
             ("diagnosis_v3", "diagnosis", V3),
             ("fusion_p1", "fusion", profile_v4),
             ("fusion_v3", "fusion", V3),
             ("editor_p1", "editor", profile_v4),
             ("learning_p1", "learn", profile_v4),
             ("learning_v3", "learn", V3)]
    cases = []
    for case_id, stage, profile in order:
        cases.append({"id": case_id, "stage": stage, "profile": profile,
                      "payload": deepcopy(materials[profile][stage]),
                      "classification_binding": deepcopy(materials[profile]["classification_binding"]) if stage == "classification" else None,
                      "parameters": {"model": "deepseek-v4-pro", "temperature": 1.0,
                                     "max_tokens": 65536 if stage == "learn" else 32768,
                                     "thinking": {"type": "enabled"}, "reasoning_effort": "medium", "stream": False},
                      "timeout_seconds": 600, "material": "archived_real_08_r2_independent_probe",
                      "criteria": COMMON_CRITERIA + CRITERIA[stage]})
    # Program identities differ; no behavioral/trajectory field may differ.
    for stage in ("diagnosis", "fusion", "editor", "learn"):
        before, after = deepcopy(materials[V3][stage]), deepcopy(materials[profile_v4][stage])
        for value in (before, after):
            value.pop("update_profile", None)
            value.pop("binding_sha256", None)
        assert before == after, stage
    return cases


def validate_output(case, value):
    """Pure contract checks on original payload; no publishing or execution."""
    stage, payload = case["stage"], case["payload"]
    if stage == "classification":
        system = grouping_messages(payload, GROUP_PROMPT.read_text(), profile=case["profile"])[0]["content"]
        return freeze_grouping(value, case["classification_binding"], system)
    if stage == "diagnosis":
        return grouped_update.accept_diagnosis(value, payload)
    if stage == "fusion":
        return grouped_update.compile_update(value, payload)
    if stage == "editor":
        return validate_editor(value, payload)
    if stage == "learn":
        return validate_effective_learning(value, payload)
    raise ValueError(stage)


def baseline_audit():
    """Write only read-only source/fixture checks; no requests and no responses."""
    baseline = material(V3)
    old_messages = read(REAL / "messages/classification.json")
    assert old_messages == [{"role": "system", "content": GROUP_PROMPT.read_text()},
                            {"role": "user", "content": json.dumps(baseline["classification"], ensure_ascii=False, separators=(",", ":"))}]
    counts = {}
    for stage in ("classification", "diagnosis", "fusion", "editor", "learn"):
        messages = old_messages if stage == "classification" else grouped_update.grouped_messages(stage, baseline[stage])
        counts[stage] = {"messages_chars": len(json.dumps(messages, ensure_ascii=False, separators=(",", ":"))),
                         "payload_sha256": object_digest(baseline[stage]),
                         "messages_sha256": object_digest(messages)}
    learned = baseline["learn"]
    report = {"material": "real_08_r2", "source_root": _relative(REAL),
              "source_files": source_manifest(), "v3_baseline": counts,
              "parent_sha256": learned["parent"]["sha256"],
              "candidate_sha256": learned["candidate"]["sha256"],
              "current_runs": len(learned["runs"]), "paired_tasks": len(learned["pairs"]),
              "steps": sum(len(run["steps"]) for run in learned["runs"].values()),
              "historical_effects": len(learned["memory"]),
              "matches_archived_candidate_editor_plan_diff_and_twenty_traces": True,
              "no_model_calls": True, "no_environment_execution": True,
              "notes": "All stage cases are independent; classification/Diagnosis/Fusion/Editor outputs are never substituted into the real learning fixture."}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "baseline_fixture_audit.json"
    with path.open("x") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


if __name__ == "__main__":
    audit = baseline_audit()
    print(json.dumps({"baseline_stages": audit["v3_baseline"], "source_files": len(audit["source_files"])}, indent=2))
