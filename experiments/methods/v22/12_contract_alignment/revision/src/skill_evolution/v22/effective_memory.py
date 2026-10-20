"""Explicitly retire invalid limits while preserving immutable evidence history.

This new contract does not alter previous learning messages or Memory snapshots.
It validates source/version routing, not the truth of a proposed knowledge revision.
"""

from copy import deepcopy
import json

from src.adapters.alfworld.verify_skill_run import require
from .compact_learning import INSTRUCTIONS, SHAPE, resolve_source, update_response_sources, validate_learning
from .compact_learning_view import _rewrite, scoped_learning_payload
from .unified_dsc import PROFILE as UNIFIED_PROFILE
from .contract_alignment import PROFILE as ALIGNED_PROFILE, VIEW_SCHEMA as ALIGNED_VIEW_SCHEMA
from .memory_identity import (
    PROFILE as STABLE_PROFILE, VIEW_SCHEMA as STABLE_VIEW_SCHEMA,
    capture_reference_contexts, reference_contexts_by_origin, rebind_history_references,
)


VIEW_SCHEMA = "v22.effective_memory_view.v1"
UNIFIED_VIEW_SCHEMA = "v22.unified_dsc_view.v1"
UNIFIED_PROFILES = (UNIFIED_PROFILE, STABLE_PROFILE, ALIGNED_PROFILE)
STABLE_PROFILES = (STABLE_PROFILE, ALIGNED_PROFILE)
EFFECTIVE_SHAPE = deepcopy(SHAPE)
EFFECTIVE_SHAPE["memory_delta"][0]["retire_limits"] = [{
    "effect_id": "replaced existing effect ID", "index": 0,
    "reason": "Why current findings invalidate this particular old limit",
    "findings": ["current finding ID"],
}]


def _contexts(effect):
    """Old single-context records are recoverable; mixed old provenance is unknown."""
    basis_contexts = list(dict.fromkeys(row["context_id"] for row in effect["basis"]))
    fallback = basis_contexts[0] if len(basis_contexts) == 1 else None
    claim_context = effect.get("claim_context_id", fallback)
    limit_contexts = effect.get("limit_contexts", [fallback] * len(effect["limits"]))
    require(isinstance(limit_contexts, list) and len(limit_contexts) == len(effect["limits"]), "Limit/context alignment mismatch.")
    require(claim_context is None or isinstance(claim_context, str), "Invalid claim context.")
    require(all(context is None or isinstance(context, str) for context in limit_contexts), "Invalid limit context.")
    return claim_context, list(limit_contexts)


def memory_view_schema(profile):
    if profile == ALIGNED_PROFILE:
        return ALIGNED_VIEW_SCHEMA
    if profile == STABLE_PROFILE:
        return STABLE_VIEW_SCHEMA
    return UNIFIED_VIEW_SCHEMA if profile == UNIFIED_PROFILE else VIEW_SCHEMA


def effective_consumption_payload(payload):
    """Read-only current-knowledge view for learning, Fusion and Editor.

    Full sources/comparison dependencies remain available. Archived interpretations
    and retired assertions stay in persistent Memory, not in the active model view.
    """
    source = deepcopy(payload)
    source.setdefault("runs", {})
    source.setdefault("memory", [])
    aligned = payload.get("update_profile") == ALIGNED_PROFILE
    view = scoped_learning_payload(source, qualify_punctuation=aligned)
    view["consumption_view"] = VIEW_SCHEMA
    names = {context: name for name, context in view["historical_contexts"].items()}
    stable = payload.get("update_profile") in STABLE_PROFILES
    bindings = reference_contexts_by_origin(source["memory"]) if stable else {}
    if stable:
        # Register all active origins before rebinding cross-context references.
        for effect in source["memory"]:
            claim_context, limit_contexts = _contexts(effect)
            for context in [claim_context] + limit_contexts:
                if context is not None and context not in names:
                    name = f"H{len(names) + 1}"
                    names[context] = name
                    view["historical_contexts"][name] = context
    for effect, projected in zip(source["memory"], view["memory"]):
        claim_context, limit_contexts = _contexts(effect)
        for context in [claim_context] + limit_contexts:
            if context is not None and context not in names:
                name = f"H{len(names) + 1}"
                names[context] = name
                view["historical_contexts"][name] = context
        aliases = {ref for basis in effect["basis"] for ref in basis["sources"]}
        aliases.update(item for basis in effect["basis"] for item in basis["finding"]["about"])
        aliases.update(source["id"] for basis in effect["basis"] for source in basis["sources"].values()
                       if isinstance(source, dict) and "id" in source)
        def prose(text, origin):
            if stable:
                text = rebind_history_references(text, origin, bindings, names)
            return _rewrite(text, names.get(origin, "history_unknown"), aliases,
                            qualify_punctuation=aligned)

        projected["claim"] = prose(effect["claim"], claim_context)
        projected["limits"] = [prose(limit, context)
                               for limit, context in zip(effect["limits"], limit_contexts)]
        projected["claim_context_id"] = claim_context
        projected["limit_contexts"] = limit_contexts
        for basis in projected["basis"]:
            # Raw source snapshots remain; a previous model's explanation is not a fact.
            basis["finding_id"] = basis.pop("finding")["id"]
    if payload.get("update_profile") in UNIFIED_PROFILES:
        # A round's diff, grouping and Editor realization are shared evidence,
        # not extra independent trials for every finding or Effect using them.
        view["consumption_view"] = memory_view_schema(payload["update_profile"])
        view["historical_updates"] = {}
        for effect in view["memory"]:
            for basis in effect["basis"]:
                context = names[basis["context_id"]]
                actual = basis.pop("actual_update")
                if stable:
                    # Generation-time aliases are program provenance, not another
                    # competing namespace for the model to interpret.
                    actual.pop("reference_contexts", None)
                require(context not in view["historical_updates"]
                        or view["historical_updates"][context] == actual,
                        "Conflicting actual updates in one historical context.")
                view["historical_updates"][context] = actual
                basis["actual_update_ref"] = context
        for effect in source["memory"]:
            for basis in effect["basis"]:
                context = names[basis["context_id"]]
                update = basis["actual_update"].get("update_context", {})
                for ref, field in (("diff", "actual_diff"), ("editor", "editor")):
                    if ref in basis["sources"] and field in update and basis["sources"][ref] == update[field]:
                        view["historical_sources"][context + "::" + ref] = {
                            "actual_update_ref": context, "path": ["update_context", field]}
    return view


def validate_effective_learning(value, payload):
    """Extend source-linked learning with explicit version-bound limit retirement."""
    require(isinstance(value, dict) and isinstance(value.get("memory_delta"), list), "Invalid effective learning response.")
    legacy = deepcopy(value)
    legacy["memory_delta"] = []
    validate_learning(legacy, payload)
    old = {effect["id"]: effect for effect in payload["memory"]}
    finding_ids = {row["id"] for row in value["findings"]}
    replaced = set()
    for delta in value["memory_delta"]:
        require(isinstance(delta, dict) and set(delta) == {"replace", "claim", "limits", "findings", "retire_limits"},
                "memory_delta requires exact effective fields, including retire_limits (possibly []).")
        require(isinstance(delta["claim"], str) and delta["claim"].strip(), "Empty memory claim.")
        require(isinstance(delta["limits"], list) and delta["limits"]
                and all(isinstance(item, str) and item.strip() for item in delta["limits"]), "Memory needs explicit active limits.")
        require(isinstance(delta["replace"], list) and all(isinstance(item, str) for item in delta["replace"])
                and len(set(delta["replace"])) == len(delta["replace"]) and set(delta["replace"]) <= set(old)
                and not set(delta["replace"]) & replaced, "Invalid or repeated effect replacement.")
        replaced.update(delta["replace"])
        require(isinstance(delta["findings"], list) and delta["findings"]
                and all(isinstance(item, str) for item in delta["findings"])
                and set(delta["findings"]) <= finding_ids, "Memory delta needs known current findings.")
        refs = {ref for finding in value["findings"] if finding["id"] in delta["findings"] for ref in finding["refs"]}
        events = [payload["sources"][ref] for ref in refs if payload["sources"][ref]["kind"] == "event"
                  and resolve_source(payload, ref).get("phase") == "executed"
                  and resolve_source(payload, ref)["episode_complete"]]
        current_candidate = any(source["run"].startswith("C") for source in events)
        realization = ("skill:candidate" in refs and bool(payload["candidate"].get("text"))
                       and any(payload["sources"][ref]["kind"] in {"requirement", "capabilities", "diff"} for ref in refs))
        inherited_candidate = any(
            (ref.startswith("C") and isinstance(source, dict) and source.get("phase") == "executed"
             and source.get("episode_complete")) or (ref == "skill:candidate" and isinstance(source, dict) and source.get("text"))
            for effect_id in delta["replace"] for basis in old[effect_id]["basis"] for ref, source in basis["sources"].items())
        require(current_candidate or realization or (events and inherited_candidate),
                "A new response needs Candidate evidence; revision needs current facts and existing actual-response basis.")
        retirements = delta["retire_limits"]
        require(isinstance(retirements, list), "retire_limits must be an array.")
        seen = set()
        for retirement in retirements:
            require(isinstance(retirement, dict) and set(retirement) == {"effect_id", "index", "reason", "findings"},
                    "Invalid limit retirement fields.")
            effect_id, index = retirement["effect_id"], retirement["index"]
            require(isinstance(effect_id, str) and effect_id in old and effect_id in delta.get("replace", []),
                    "Retirement must reference an effect replaced by this delta.")
            require(type(index) is int and 0 <= index < len(old[effect_id]["limits"]), "Retirement index is out of bounds.")
            require((effect_id, index) not in seen, "Duplicate limit retirement.")
            seen.add((effect_id, index))
            require(isinstance(retirement["reason"], str) and retirement["reason"].strip(), "Retirement needs a specific reason.")
            refs = retirement["findings"]
            require(isinstance(refs, list) and refs and all(isinstance(ref, str) for ref in refs)
                    and set(refs) <= set(delta.get("findings", [])), "Retirement needs current findings included in this delta.")
    return value


def _deduplicate(rows):
    return list({json.dumps(row, sort_keys=True, ensure_ascii=False): row for row in rows}.values())


def apply_effective_memory(memory, value, context_id, payload):
    """Persist active claims/limits separately from archived retired assertions."""
    require(memory == payload["memory"], "Memory revision requires the bound source snapshot.")
    require(isinstance(context_id, str) and context_id.strip(), "Knowledge revision context required.")
    validate_effective_learning(value, payload)
    old = {effect["id"]: effect for effect in memory}
    result = deepcopy(memory)
    reference_contexts = None
    if payload.get("update_profile") in STABLE_PROFILES and value["memory_delta"]:
        reference_contexts = capture_reference_contexts(
            value, effective_consumption_payload(payload)["historical_contexts"])
    for number, delta in enumerate(value["memory_delta"], 1):
        effect_id = f"{context_id}:m{number}"
        require(effect_id not in old, "Knowledge revision context was already used.")
        retired = {(row["effect_id"], row["index"]): row for row in delta["retire_limits"]}
        basis, limits, archived = [], [], []
        for replaced in delta["replace"]:
            previous = old[replaced]
            _, previous_contexts = _contexts(previous)
            basis.extend(deepcopy(previous["basis"]))
            archived.extend(deepcopy(previous.get("retired_limits", [])))
            for index, (limit, limit_context) in enumerate(zip(previous["limits"], previous_contexts)):
                retirement = retired.get((replaced, index))
                if retirement is None:
                    limits.append({"text": limit, "context": limit_context})
                else:
                    archived.append({"effect_id": replaced, "index": index, "limit": limit,
                                     "limit_context_id": limit_context, "reason": retirement["reason"],
                                     "retirement_context_id": context_id, "findings": deepcopy(retirement["findings"])})
        limits.extend({"text": limit, "context": context_id} for limit in delta["limits"])
        limits = _deduplicate(limits)
        for finding in value["findings"]:
            if finding["id"] in delta["findings"]:
                basis.append({"context_id": context_id, "finding": deepcopy(finding),
                              "sources": (update_response_sources(payload, finding)
                                          if payload.get("update_profile") in UNIFIED_PROFILES
                                          else {ref: resolve_source(payload, ref) for ref in finding["refs"]}),
                              "actual_update": {"parent_skill_id": payload["parent"]["skill_id"],
                                                "candidate_skill_id": payload["candidate"]["skill_id"],
                                                "comparisons": deepcopy(payload["pairs"])}})
                if reference_contexts is not None:
                    basis[-1]["actual_update"]["reference_contexts"] = deepcopy(reference_contexts)
                if "update_context" in payload:
                    basis[-1]["actual_update"]["update_context"] = deepcopy(payload["update_context"])
        updated = {"id": effect_id, "claim": delta["claim"], "claim_context_id": context_id,
                   "limits": [row["text"] for row in limits], "limit_contexts": [row["context"] for row in limits],
                   "basis": _deduplicate(basis), "retired_limits": _deduplicate(archived),
                   "supersedes": deepcopy(delta["replace"]),
                   "attribution": "actual_candidate_bundle; isolated effects not identified"}
        result = [row for row in result if row["id"] not in delta["replace"]] + [updated]
    return result


EFFECTIVE_INSTRUCTIONS = """
EFFECTIVE KNOWLEDGE REVISION:
This can be a semantic correction from the SAME real feedback, not a new independent
execution or additional independent support. Use current run identities/observations
and current_run_facts. Do not count rereading evidence as a second successful trial.
Memory claim/limits are active, fallible knowledge. H1::/H2:: references resolve only
through historical_contexts; history_unknown:: marks ambiguous old provenance, never
current evidence. Each claim and limit has its OWN context, not all inherited contexts.
Historical source events, actual_update conditions and static evidence remain; old
model explanations and retired assertions are archival, not active knowledge inputs.
Do not infer admissible actions from omitted historical command lists.

Use only current sources keys in findings.refs; existing effect IDs may appear in
about/replace. Ground a correction in the actual current facts, even if they refer to
the same original Parent. Write persistent claim/limits using current aliases for
this input or exact run identities for historical comparisons, not temporary H1 labels.

Every memory_delta has retire_limits, an array (empty if none). An entry has effect_id,
zero-based index into that exact old effect's ACTIVE limits, reason, and current
finding IDs also included in this delta's findings. Only a limit in an effect named
in replace may be retired. Explain why that particular assertion is invalidated;
do not discard untested scope, counterexamples or attribution uncertainty wholesale.
Unretired old limits are inherited automatically. The program archives retired text,
reason and finding/context provenance and removes it from active limits. Do not copy
the retired erroneous assertion into the new active limits as a 'correction note'.
Use the corrected factual scope and remaining uncertainty instead. If no limit is
refuted, retire_limits=[]; changing a claim alone does not authorize deleting limits.

Replace wrong or overbroad active knowledge rather than merely appending another claim.
This stage revises knowledge only: do not prewrite Skill instructions or Fusion edits.
Limited joint observations may inform a bounded later construction without proving its
benefit, isolated contribution, necessity or generalization. Unknown effect is not a
construction blocker by itself. Structural validation is not semantic verification.
"""


def learning_messages_effective(payload):
    return [{"role": "system", "content": INSTRUCTIONS + EFFECTIVE_INSTRUCTIONS
             + "\nOutput shape: " + json.dumps(EFFECTIVE_SHAPE, ensure_ascii=False)},
            {"role": "user", "content": json.dumps(effective_consumption_payload(payload), ensure_ascii=False,
                                                    separators=(",", ":"))}]
