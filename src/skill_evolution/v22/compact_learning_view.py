"""A separately versioned consumption view separating current and historical evidence.

Persistent Memory and old message reconstruction stay unchanged. This projection
removes repeated historical command lists, not observations or belief limitations.
"""

from copy import deepcopy
import json
import re

from .compact_learning import INSTRUCTIONS, SHAPE


VIEW_SCHEMA = "v22.compact_learning_scoped_view.v1"
EVENT_KEYS = {
    "run_id", "task_id", "skill_id", "step", "episode_complete", "phase", "action",
    "action_in_admissible_commands", "observation", "observation_before", "reward", "done", "won",
}
RUN_ALIAS = r"[PC]\d+(?::\d+)?"


def current_run_facts(payload):
    """Mechanical facts over executed events, not evidence of semantic benefit."""
    facts = {}
    for alias, run in payload["runs"].items():
        executed = [event for event in run["steps"] if event.get("phase") == "executed"]
        facts[alias] = {
            "run_id": run["run_id"], "task_id": run["task_id"], "skill_id": run.get("skill_id"),
            "status": run["status"], "episode_complete": run["episode_complete"],
            "native_success": run["native_success"], "executed_actions": len(executed),
            "non_admissible_steps": [event["step"] for event in executed
                                     if event.get("action_in_admissible_commands") is False],
            "look_steps": [event["step"] for event in executed if event.get("action") == "look"],
            "nothing_happens_steps": [event["step"] for event in executed
                                      if event.get("observation", "").strip() == "Nothing happens."],
        }
    return facts


def _prefix(context):
    return f"history[{context}]::" if "," in context else f"{context}::"


def _rewrite(value, context, aliases):
    """Mark references in prose as well as explicit fields; never change evidence meaning."""
    candidates = sorted((re.escape(alias) for alias in aliases if alias), key=len, reverse=True)
    pattern = re.compile(r"(?<![\w:])(?:" + "|".join(candidates + [RUN_ALIAS]) + r")(?![\w:])")

    def walk(item):
        if isinstance(item, str):
            return pattern.sub(lambda match: _prefix(context) + match.group(), item)
        if isinstance(item, list):
            return [walk(child) for child in item]
        if isinstance(item, dict):
            return {key: walk(child) for key, child in item.items()}
        return item

    return walk(value)


def scoped_learning_payload(payload):
    """Build a read-only model view; validate outputs against the ORIGINAL payload.

    Current sources/runs remain unchanged. Historical sources are materialized once
    under qualified aliases; historical about/refs are never current output IDs.
    """
    view = deepcopy(payload)
    view["consumption_view"] = VIEW_SCHEMA
    view["current_run_facts"] = current_run_facts(payload)
    view["historical_sources"] = {}
    view["memory"] = []
    context_aliases = {}
    for effect in payload["memory"]:
        for basis in effect["basis"]:
            aliases = context_aliases.setdefault(basis["context_id"], set())
            aliases.update(basis["sources"])
            aliases.update(basis["finding"]["about"])
            aliases.add(basis["finding"]["id"])
            aliases.update(source["id"] for source in basis["sources"].values()
                           if isinstance(source, dict) and "id" in source)
            editor = basis["actual_update"].get("update_context", {}).get("editor")
            if editor:
                aliases.update(ref for row in editor["mappings"] for ref in row["requirements"])
                aliases.update(ref for row in editor["issues"] for ref in row["about"])
    context_names = {context: f"H{number}" for number, context in enumerate(context_aliases, 1)}
    view["historical_contexts"] = {name: context for context, name in context_names.items()}
    for effect in payload["memory"]:
        contexts = list(dict.fromkeys(basis["context_id"] for basis in effect["basis"]))
        context_group = ",".join(context_names[context] for context in contexts) or "history_unknown"
        aliases = set().union(*(context_aliases[context] for context in contexts))
        projected = {key: deepcopy(effect[key]) for key in ("id", "supersedes", "attribution") if key in effect}
        projected.update(claim=_rewrite(effect["claim"], context_group, aliases),
                         limits=_rewrite(effect["limits"], context_group, aliases),
                         historical_contexts=[context_names[context] for context in contexts], basis=[])
        for basis in effect["basis"]:
            context = basis["context_id"]
            context_name = context_names[context]
            local_aliases = context_aliases[context]
            finding = _rewrite(basis["finding"], context_name, local_aliases)
            projected_basis = {"context_id": context, "finding": finding,
                               "actual_update": _rewrite(basis["actual_update"], context_name, local_aliases),
                               "sources": []}
            for ref, source in basis["sources"].items():
                qualified = _prefix(context_name) + ref
                if isinstance(source, dict) and "run_id" in source and "step" in source:
                    # Keep literal event content, excluding repeated huge action lists.
                    content = {key: deepcopy(value) for key, value in source.items() if key in EVENT_KEYS}
                else:
                    # Static requirements/Skill/capability evidence is retained in full.
                    content = deepcopy(source)
                    if isinstance(content, dict):
                        # IDs/references are namespaced; literal text is still exact evidence.
                        for key in ("id", "basis", "about", "refs"):
                            if key in content:
                                content[key] = _rewrite(content[key], context_name, local_aliases)
                previous = view["historical_sources"].get(qualified)
                if previous is not None and previous != content:
                    raise ValueError("Conflicting historical source snapshots: " + qualified)
                view["historical_sources"][qualified] = content
                projected_basis["sources"].append(qualified)
            projected["basis"].append(projected_basis)
        view["memory"].append(projected)
    return view


SCOPED_INSTRUCTIONS = """
CURRENT VERSUS HISTORICAL EVIDENCE BOUNDARY:
Only runs, sources, pairs, plan, actual_diff and current_run_facts describe THIS
comparison. Bare P1/C2 aliases belong only to these current runs. Current mechanical
facts count executed events only; list membership/look/zero reward are not task meaning.
Read the actual current steps before making each current behavior claim.

Memory is an earlier, fallible interpretation. Its basis and historical_sources belong
to H1::, H2:: namespaces resolved by historical_contexts, not current P1/C2. A history reference
never identifies a current event even when the alias or task ID looks identical.
Historical sources are deduplicated snapshots; repeated command lists/fingerprints are
omitted, but observations, limitations and static evidence remain. Do not infer facts
requiring omitted action lists. Multiple contexts on a claim mark historical scope only,
not proof that a bare reference identifies the same event in all contexts. Match exact
run_id, Skill identity and comparison conditions before relating old and current evidence.

Output findings.refs may cite ONLY keys in the current sources dictionary, never keys
from historical_sources or history-qualified finding/question IDs. Existing effect IDs
remain valid for findings.about and memory_delta.replace. Explain historical contrasts
as scoped comparisons, not as current events. Use current refs for the new observation.

Old claim/finding text may contain missed events, false counts or wrong explanations;
it is NOT a fact oracle. Compare it against current verified observations and mechanical
facts, especially when the same original Parent run reappears. If these establish that
an existing claim is wrong or overbroad, replace that effect with a corrected, limited
claim and relevant current finding IDs. Do not merely append another positive effect
while leaving a known false active claim untouched. Prior snapshots stay preserved by
the program; retaining history does not require retaining an incorrect active claim.
The current Memory writer also inherits old limits verbatim. If one of those limits
contains a factual error, explicitly state in the NEW limits which inherited assertion
is corrected or superseded and cite the current finding in your explanation. Do not
leave that old assertion looking like an active condition of the revised claim. This
clarification preserves the historical record; it does not erase old evidence.
Program validation checks source identities and question destinations, not the truth of
your statement. Do not copy a historical step count, action or look into a current run.
"""


def learning_messages_scoped(payload):
    return [{"role": "system", "content": INSTRUCTIONS + SCOPED_INSTRUCTIONS
             + "\nOutput shape: " + json.dumps(SHAPE, ensure_ascii=False)},
            {"role": "user", "content": json.dumps(scoped_learning_payload(payload), ensure_ascii=False,
                                                    separators=(",", ":"))}]
