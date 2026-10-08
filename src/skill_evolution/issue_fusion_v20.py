"""v20 Issue Fusion: select issues by consuming compact issue Memory.

This module is deliberately a read-only boundary.  It gives a model the
current Findings, the short problem/attempt state, and the current Parent
rule catalogue.  It does not review raw evidence, authorize an edit, or write
Memory.  A later step consumes the selected references and opens the relevant
evidence locally.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from .edit_tracking_v19 import encode, digest
from .issue_memory_v20 import IssueMemorySnapshot, validate_memory, ISSUE_ID, ATTEMPT_ID
from .diagnosis_references_v18 import build_reference_catalogs
from .review_contract_v19 import CurrentDiagnosisInput, CurrentFindings
from .current_diagnosis_v19 import validate_current_batch


SCHEMA = {
    "type": "object",
    "required": ["schema_version", "issues", "unassociated_findings"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "string", "enum": ["issue_fusion_response_v20.1"]},
        "issues": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "required": ["current_finding_refs", "memory_issue_refs", "memory_attempt_refs",
                          "issue_statement", "decision", "reason", "related_rule_refs"],
            "properties": {
                "current_finding_refs": {"type": "array", "items": {"type": "string"}},
                "memory_issue_refs": {"type": "array", "items": {"type": "string"}},
                "memory_attempt_refs": {"type": "array", "items": {"type": "string"}},
                "issue_statement": {"type": "string"},
                "decision": {"type": "string", "enum": ["PROPOSE", "NO_EDIT"]},
                "reason": {"type": "string"},
                "related_rule_refs": {"type": "array", "items": {"type": "string"}},
            }}},
        "unassociated_findings": {"type": "array", "items": {"type": "object",
            "required": ["finding_ref", "reason"], "additionalProperties": False,
            "properties": {"finding_ref": {"type": "string"}, "reason": {"type": "string"}}}},
    },
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _text(value: Any, field: str) -> str:
    _require(type(value) is str and bool(value.strip()), f"{field} must be nonempty text")
    return value


def _refs(value: Any, field: str) -> list[str]:
    _require(type(value) is list and all(type(x) is str and x.strip() for x in value),
             f"{field} must be a list of nonempty references")
    _require(len(value) == len(set(value)), f"{field} contains duplicate references")
    return list(value)


def _check_schema(value: Any) -> dict[str, Any]:
    _require(type(value) is dict and set(value) == set(SCHEMA["properties"]),
             "invalid issue fusion response fields")
    _require(value["schema_version"] == "issue_fusion_response_v20.1", "unsupported issue fusion response")
    _require(type(value["issues"]) is list and type(value["unassociated_findings"]) is list,
             "issues and unassociated_findings must be lists")
    for item in value["issues"]:
        _require(type(item) is dict and set(item) == set(SCHEMA["properties"]["issues"]["items"]["required"]),
                 "invalid issue proposal fields")
        for field in ("current_finding_refs", "memory_issue_refs", "memory_attempt_refs", "related_rule_refs"):
            _refs(item[field], field)
        _text(item["issue_statement"], "issue_statement")
        _text(item["reason"], "reason")
        _require(item["decision"] in ("PROPOSE", "NO_EDIT"), "decision must be PROPOSE or NO_EDIT")
    for item in value["unassociated_findings"]:
        _require(type(item) is dict and set(item) == {"finding_ref", "reason"},
                 "invalid unassociated finding")
        _text(item["finding_ref"], "finding_ref")
        _text(item["reason"], "unassociated reason")
    return value


def _validate_input(request: IssueFusionInput) -> dict[str, Any]:
    p = request.payload
    required = {"schema_version", "run_id", "round_id", "memory_ref", "memory_revision",
                "memory_issues", "current_findings", "available_rule_refs", "batch",
                "parent_skill_sha256", "history_sha256", "authority"}
    _require(type(p) is dict and set(p) == required and p["schema_version"] == "issue_fusion_input_v20.1",
             "invalid issue fusion input")
    _text(p["run_id"], "input run_id"); _text(p["round_id"], "input round_id")
    _require(type(p["memory_ref"]) is str and p["memory_ref"].startswith("MEMORY_V20/"),
             "invalid memory_ref")
    _require(p["memory_revision"] is None or (type(p["memory_revision"]) is int and p["memory_revision"] >= 0),
             "invalid memory_revision")
    _require(type(p["memory_issues"]) is list and type(p["current_findings"]) is list and
             type(p["available_rule_refs"]) is dict and type(p["batch"]) is dict,
             "invalid issue fusion input collections")
    seen_i, seen_a = set(), set()
    for issue in p["memory_issues"]:
        _require(type(issue) is dict and set(issue) == {"issue_id", "problem", "attempts"},
                 "invalid compact memory issue")
        _require(type(issue["issue_id"]) is str and ISSUE_ID.fullmatch(issue["issue_id"])
                 and issue["issue_id"] not in seen_i, "invalid compact memory issue_id")
        seen_i.add(issue["issue_id"]); _text(issue["problem"], "memory problem")
        _require(type(issue["attempts"]) is list, "invalid compact memory attempts")
        for attempt in issue["attempts"]:
            _require(type(attempt) is dict and set(attempt) ==
                     {"attempt_id", "approach", "assessment", "current_binding"},
                     "invalid compact memory attempt")
            _require(type(attempt["attempt_id"]) is str and ATTEMPT_ID.fullmatch(attempt["attempt_id"])
                     and attempt["attempt_id"] not in seen_a, "invalid compact memory attempt_id")
            seen_a.add(attempt["attempt_id"])
            for field in ("approach", "assessment", "current_binding"):
                _text(attempt[field], "memory " + field)
    for finding in p["current_findings"]:
        _require(type(finding) is dict and "finding_id" in finding and "kind" in finding,
                 "invalid compact current finding")
        _text(finding["finding_id"], "finding_id")
        _require(finding["kind"] in ("OBSERVED_PROBLEM", "EFFECTIVE_BEHAVIOR",
                                      "COUNTEREVIDENCE", "UNCERTAINTY"), "invalid finding kind")
    return p


def _history_view(history: tuple, parent_skill: str) -> tuple[dict[str, Any], str]:
    """Return compact edit bindings and the full-history digest.

    History is optional at this boundary.  When it is absent, bindings stay
    unresolved; Fusion must never infer that an edit disappeared merely because
    its source history was not loaded.
    """
    if not history:
        return (), digest(encode([]))
    from .edit_tracking_v19 import validate_history, trace_edit_history, history_ref
    validate_history(history)
    view = trace_edit_history(history)
    _require(view["current_skill"] == parent_skill,
             "validated edit history does not bind to current parent skill")
    return tuple(view["edits"]), history_ref(history)


def _findings(current_requests, current_findings):
    if not current_requests and not current_findings:
        return (), {"run_id": None, "round_id": None, "parent_skill_ref": None,
                    "grouping_sha256": None, "group_ids": [], "evolution_manifest_sha256": None}
    _require(type(current_requests) is tuple and type(current_findings) is tuple,
             "current requests and findings must be tuples")
    _require(all(isinstance(x, CurrentDiagnosisInput) for x in current_requests),
             "CurrentDiagnosisInput required")
    _require(all(isinstance(x, CurrentFindings) for x in current_findings),
             "CurrentFindings required")
    batch = validate_current_batch(current_requests, current_findings)
    result = []
    for finding_set in current_findings:
        for finding in finding_set.payload["findings"]:
            # Evidence bodies and raw responses remain outside this model view.
            result.append({k: finding[k] for k in (
                "finding_id", "kind", "statement", "applicability", "dimensions",
                "related_rule_refs", "uncertainty")})
    return tuple(result), batch


def build_issue_fusion_input(*, memory: IssueMemorySnapshot | dict[str, Any],
                             current_requests=(), current_findings=(), parent_skill: str,
                             run_id: str, round_id: str, history=()):
    """Build the compact, read-only v20 Fusion input.

    ``memory`` may be a verified ``IssueMemorySnapshot`` or its complete
    payload.  The model view intentionally excludes cumulative source/edit
    lists; those are reopened by the next local Evidence Review step.
    """
    _text(run_id, "run_id"); _text(round_id, "round_id"); _text(parent_skill, "parent_skill")
    if isinstance(memory, IssueMemorySnapshot):
        mem = memory.memory
        memory_ref = memory.memory_ref
        revision = memory.head["revision"]
        _require(memory.head["run_id"] == run_id and mem["run_id"] == run_id, "memory run_id mismatch")
    else:
        mem = validate_memory(memory, run_id=run_id)
        memory_ref = "MEMORY_V20/" + digest(encode(mem))
        revision = None
    findings, batch = _findings(tuple(current_requests), tuple(current_findings))
    _require(not findings or batch["run_id"] == run_id, "current findings run_id mismatch")
    _require(not findings or batch["round_id"] == round_id, "current findings round_id mismatch")
    history_edits, history_sha = _history_view(tuple(history), parent_skill)
    by_edit = {e["edit_id"]: e for e in history_edits}
    issues = []
    attempt_ids = set()
    for issue in mem["issues"]:
        attempts = []
        for attempt in issue["attempts"]:
            _require(attempt["attempt_id"] not in attempt_ids, "duplicate memory attempt ownership")
            attempt_ids.add(attempt["attempt_id"])
            bindings = [by_edit[e]["binding_status"] for e in attempt["edit_refs"] if e in by_edit]
            if not bindings:
                binding = "UNRESOLVED"
            elif len(bindings) < len(attempt["edit_refs"]):
                binding = "PARTIAL"
            elif all(x == "EXACT" for x in bindings):
                binding = "EXACT"
            elif any(x == "UNRESOLVED" for x in bindings):
                binding = "UNRESOLVED"
            else:
                binding = "PARTIAL"
            attempts.append({"attempt_id": attempt["attempt_id"], "approach": attempt["approach"],
                             "assessment": attempt["assessment"], "current_binding": binding})
        issues.append({"issue_id": issue["issue_id"], "problem": issue["problem"], "attempts": attempts})
    rules = build_reference_catalogs({"current_skill": parent_skill, "contexts": []})["available_rule_refs"]
    payload = {"schema_version": "issue_fusion_input_v20.1", "run_id": run_id, "round_id": round_id,
               "memory_ref": memory_ref, "memory_revision": revision,
               "memory_issues": issues, "current_findings": list(findings),
               "available_rule_refs": rules,
               "batch": batch,
               "parent_skill_sha256": digest(parent_skill),
               "history_sha256": history_sha,
               "authority": "ISSUE_SELECTION_ONLY_NOT_EVIDENCE_VERIFIED_OR_EDIT_AUTHORIZATION"}
    return IssueFusionInput(encode(payload))


@dataclass(frozen=True)
class IssueFusionInput:
    payload_json: str
    @property
    def payload(self):
        return json.loads(self.payload_json)
    @property
    def input_ref(self):
        return "ISSUE_FUSION_INPUT_V20/" + digest(self.payload_json)


@dataclass(frozen=True)
class IssueFusionResult:
    payload_json: str
    @property
    def payload(self):
        return json.loads(self.payload_json)


def fusion_reference_map(request: IssueFusionInput) -> dict[str, str]:
    p = request.payload
    groups = [("F", [f["finding_id"] for f in p["current_findings"]]),
              ("I", [i["issue_id"] for i in p["memory_issues"]]),
              ("A", [a["attempt_id"] for i in p["memory_issues"] for a in i["attempts"]]),
              ("R", list(p["available_rule_refs"]))]
    return {f"{prefix}{n:02d}": ref for prefix, refs in groups
            for n, ref in enumerate(sorted(set(refs)), 1)}


def fusion_wire_payload(request: IssueFusionInput) -> dict[str, Any]:
    reverse = {v: k for k, v in fusion_reference_map(request).items()}
    p = request.payload
    out = json.loads(encode(p))
    for finding in out["current_findings"]:
        finding["finding_id"] = reverse[finding["finding_id"]]
    for issue in out["memory_issues"]:
        issue["issue_id"] = reverse[issue["issue_id"]]
        for attempt in issue["attempts"]:
            attempt["attempt_id"] = reverse[attempt["attempt_id"]]
    out["available_rule_refs"] = {reverse[k]: v for k, v in out["available_rule_refs"].items()}
    return out


def _expand(raw: str, request: IssueFusionInput) -> dict[str, Any]:
    out = _check_schema(json.loads(raw))
    aliases = fusion_reference_map(request)
    reverse = {v: k for k, v in aliases.items()}
    def resolve(ref, prefix):
        _require(ref in aliases and ref.startswith(prefix), f"unknown {prefix} reference: {ref}")
        return aliases[ref]
    for item in out["issues"]:
        for field, prefix in (("current_finding_refs", "F"), ("memory_issue_refs", "I"),
                              ("memory_attempt_refs", "A"), ("related_rule_refs", "R")):
            item[field] = [resolve(ref, prefix) for ref in item[field]]
    for item in out["unassociated_findings"]:
        item["finding_ref"] = resolve(item["finding_ref"], "F")
    return out


def validate_issue_fusion(raw: str, *, request: IssueFusionInput, wire: bool = False) -> IssueFusionResult:
    _require(isinstance(request, IssueFusionInput), "IssueFusionInput required")
    _validate_input(request)
    out = _expand(raw, request) if wire else _check_schema(json.loads(raw))
    p = request.payload
    findings = {f["finding_id"]: f for f in p["current_findings"]}
    issues = {i["issue_id"]: i for i in p["memory_issues"]}
    attempts = {a["attempt_id"]: i["issue_id"] for i in p["memory_issues"] for a in i["attempts"]}
    finding_use, problem_use, unassociated = set(), set(), set()
    canonical = []
    identities = set()
    # Check this first so an OBSERVED_PROBLEM cannot be hidden in the
    # unassociated bucket behind an otherwise malformed empty issue list.
    for item in out["unassociated_findings"]:
        ref = item["finding_ref"]
        _require(ref in findings, "unknown unassociated finding")
        _require(findings[ref]["kind"] != "OBSERVED_PROBLEM",
                 "observed problem requires explicit issue disposition")
    for index, item in enumerate(out["issues"]):
        currents, mems, ats = map(set, (item["current_finding_refs"], item["memory_issue_refs"], item["memory_attempt_refs"]))
        _require(currents <= findings.keys(), f"issue {index}: unknown current finding")
        _require(mems <= issues.keys(), f"issue {index}: unknown memory issue")
        _require(ats <= attempts.keys(), f"issue {index}: unknown memory attempt")
        _require(all(attempts[a] in mems for a in ats), f"issue {index}: attempt without owning memory issue")
        _require(currents or mems, f"issue {index}: source required")
        _require(set(item["related_rule_refs"]) <= set(p["available_rule_refs"]), f"issue {index}: stale rule ref")
        problems = {ref for ref in currents if findings[ref]["kind"] == "OBSERVED_PROBLEM"}
        _require(not problems & problem_use, f"issue {index}: observed problem assigned more than once")
        problem_use |= problems; finding_use |= currents
        identity = digest(encode(item)); _require(identity not in identities, f"issue {index}: duplicate issue")
        identities.add(identity)
        canonical.append({"proposal_issue_id": "PISSUE_V20/" + digest(encode({"input_ref": request.input_ref, "index": index, "issue": item})), **item})
    for item in out["unassociated_findings"]:
        ref = item["finding_ref"]
        _require(ref in findings and ref not in finding_use | unassociated, "unknown, used or repeated unassociated finding")
        _require(findings[ref]["kind"] != "OBSERVED_PROBLEM", "observed problem requires explicit issue disposition")
        unassociated.add(ref)
    _require(finding_use | unassociated == set(findings), "current finding coverage incomplete")
    proposal_id = "PROPOSAL_V20/" + digest(encode({"input_ref": request.input_ref, "response": out}))
    # Persist canonical IDs in the result.  Request-local aliases are only a
    # transport optimization and must not make a saved result unreplayable.
    canonical_raw = encode(out)
    return IssueFusionResult(encode({"schema_version": "issue_fusion_result_v20.1", "input_ref": request.input_ref,
        "proposal_id": proposal_id, "raw_response": canonical_raw, "issues": canonical,
        "unassociated_findings": out["unassociated_findings"],
        "authority": "ISSUE_SELECTION_ONLY_NOT_EVIDENCE_VERIFIED_OR_EDIT_AUTHORIZATION",
        "validation_scope": "SOURCE_COVERAGE_REFERENCES_AND_MEMORY_OWNERSHIP_NOT_SEMANTIC_CORRECTNESS"}))


def validate_issue_fusion_result(result: IssueFusionResult, *, request: IssueFusionInput) -> IssueFusionResult:
    _require(isinstance(result, IssueFusionResult), "IssueFusionResult required")
    _require(validate_issue_fusion(result.payload["raw_response"], request=request) == result,
             "issue fusion result changed or stale")
    return result
