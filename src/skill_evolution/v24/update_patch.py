from .benchmark import current as benchmark_current
"""Validate flat V23.5 decisions and atomically adapt them to the V23 compiler.

Checks establish structure, citation identity and exact patch application, not
whether history supports a claim or a patch faithfully implements its change.
"""
from copy import deepcopy
import json
import re

from src.skill_evolution.v24.contracts.diagnosis import fields, validate_diagnosis
from src.skill_evolution.v24.unnumbered_patch import apply_patch, actual_diff
from src.skill_evolution.v24.facts import require, text
from src.skill_evolution.v24.contracts.grouping import references
from src.skill_evolution.v24.contracts.memory import MULTI_KNOWLEDGE_CONTRACT, run_references, validate_memory
from .plan import compile_effective_plan as _compile_effective_plan
from .memory_view import KNOWLEDGE_ONLY, project_payload, historical_references, check_historical_prose

CONTRACT_VERSION = "v23_5_unnumbered_updates_v1"
HISTORY_REF = re.compile(r"[A-Za-z0-9_-]+/(?:diff\b|[PQ]\d+(?::[A-Za-z0-9_]+)?)")
LOCAL_REF = re.compile(r"\b(?:[PQ]\d+(?::[A-Za-z0-9_]+)?|[CGM]\d+)\b")


class OutputSchemaError(ValueError):
    """Located model-output structure error; never used for input validation."""

    def __init__(self, location, detail):
        self.location, self.detail = location, detail
        super().__init__(detail)


def _validate_output_schema(result):
    """Explain existing structure requirements before running the full validator."""
    errors, total = [], 0

    def issue(path, message):
        nonlocal total
        total += 1
        if len(errors) < 8:
            errors.append((path, message))

    def finish(group):
        if not total:
            return
        lines = []
        for path, message in errors:
            line = f'{path}: {message}'
            if len(line) > 440:
                line = line[:415] + '... (detail shortened).'
            if len('\n'.join([*lines, line])) > 500:
                break
            lines.append(line)
        if len(lines) < total:
            lines.append(f'{total - len(lines)} additional schema error(s) not shown.')
        location = errors[0][0] if total == 1 else group
        raise OutputSchemaError(location, '\n'.join(lines))

    def kind(value):
        if value is None: return 'null'
        if isinstance(value, bool): return 'boolean'
        if isinstance(value, dict): return 'object'
        if isinstance(value, list): return 'array'
        if isinstance(value, str): return 'string'
        if isinstance(value, (int, float)): return 'number'
        return type(value).__name__

    def typed(value, expected, path, label=None):
        if not isinstance(value, expected):
            label = label or {dict: 'object', list: 'array', str: 'string'}[expected]
            issue(path, f'expected {label}; got {kind(value)}.')
            return False
        return True

    def object_fields(value, keys, path):
        if not typed(value, dict, path):
            return False
        missing = [key for key in keys if key not in value]
        extra = [key for key in value if key not in keys]
        def names(items):
            return ', '.join(json.dumps(str(k)[:60], ensure_ascii=False) for k in items[:5])
        if missing:
            issue(path, f'missing field(s) {names(missing)}.')
        if extra:
            suffix = f' (and {len(extra)-5} more)' if len(extra) > 5 else ''
            issue(path, f'extra field(s) {names(extra)}{suffix}.')
        return not missing and not extra

    object_fields(result, ('adjustments', 'checks'), 'output')
    finish('output')
    typed(result['adjustments'], list, 'adjustments')
    if result['checks'] is not None:
        typed(result['checks'], list, 'checks', 'array or null')
    finish('output')

    for index, adjustment in enumerate(result['adjustments']):
        path = f'adjustments[{index}]'
        if isinstance(adjustment, dict) and isinstance(adjustment.get('target'), str):
            uid = json.dumps(adjustment['target'][:40], ensure_ascii=False)[1:-1]
            path += f' (Update {uid})'
        if not object_fields(adjustment, ('target', 'focus', 'change', 'reason', 'to'), path):
            continue
        for key in ('target', 'change', 'reason'):
            typed(adjustment[key], str, f'{path}.{key}')
        if typed(adjustment['focus'], list, f'{path}.focus'):
            for i, dimension in enumerate(adjustment['focus']):
                typed(dimension, str, f'{path}.focus[{i}]')
        replacement = adjustment['to']
        if replacement is None or replacement == []:
            continue
        if isinstance(replacement, dict):
            if object_fields(replacement, ('patch',), f'{path}.to'):
                typed(replacement['patch'], str, f'{path}.to.patch')
        else:
            issue(f'{path}.to', 'expected null, empty array, or object with field "patch"; '
                  f'got {kind(replacement)}' + (' (nonempty).' if isinstance(replacement, list) else '.'))
    finish('adjustments')

    for index, check in enumerate(result['checks'] or []):
        path = f'checks[{index}]'
        if not object_fields(check, ('id', 'update_ids', 'question'), path):
            continue
        for key in ('id', 'question'):
            typed(check[key], str, f'{path}.{key}')
        if typed(check['update_ids'], list, f'{path}.update_ids'):
            for i, uid in enumerate(check['update_ids']):
                typed(uid, str, f'{path}.update_ids[{i}]')
    finish('checks')


def _excerpt(value):
    return repr(value[:120]) + ("..." if len(value) > 120 else "")


def _current_references(payload):
    # Only group IDs already present in the Original Plan are visible provenance.
    inherited_groups = (set(re.findall(r"\bG\d+\b", json.dumps(payload['plan'])))
                        & {g['group_id'] for g in payload['grouping']['groups']})
    return (benchmark_current().auxiliary_references(payload) | inherited_groups
            | {e['id'] for e in payload['memory']['entries']}
            | {ref for run in payload['runs'] for ref in run_references(run)})


def _prose_references(value, name, *, current, history, contexts):
    text(value, name)
    local = check_historical_prose(value, history, current=current,
                                   historical_contexts=contexts, location=name)
    for ref in sorted((set(LOCAL_REF.findall(local)) | references(local)) - current):
        raise ValueError(f"{name}: evidence reference {_excerpt(ref)} is not in the allowed reference set")


def compile_effective_plan(result, payload, *, memory_contract=MULTI_KNOWLEDGE_CONTRACT):
    """Use the same V23.5 prose interpretation during compilation and Editor reload.

    The upstream normalizer additionally restricts history to the selected view.
    This archive-level recheck preserves the original compiler's evidence scope.
    """
    history = validate_memory(payload['memory'], memory_contract=memory_contract)
    current = _current_references(payload)
    contexts = {ref.rsplit('/', 1)[0] for ref in payload['memory']['sources']}
    def prose(value, name):
        return _prose_references(value, name, current=current, history=history, contexts=contexts)
    return _compile_effective_plan(result, payload, memory_contract=memory_contract, prose_validator=prose)


def normalize_update_patches(result, payload, *, memory_view=KNOWLEDGE_ONLY, memory_contract=MULTI_KNOWLEDGE_CONTRACT):
    """Return (internal legacy result, Effective Plan), without mutating inputs.

    Raw Keep decisions remain in the caller's V23.5 output; only non-Keep
    decisions become legacy adjustments. No partial Plan escapes on failure.
    """
    fields(payload, benchmark_current().plan_fields(), "Input")
    validate_memory(payload["memory"], memory_contract=memory_contract)
    view = project_payload(payload, memory_view, memory_contract=memory_contract)
    validate_diagnosis({"decision": "revise", "reason": "Original Plan", "plan": payload["plan"]}, payload)
    originals = {u["id"]: u for u in payload["plan"]["updates"]}
    _validate_output_schema(result)
    fields(result, ("adjustments", "checks"), "V23.5 Preconditioner")
    checks = deepcopy(payload["plan"]["checks"] if result["checks"] is None else result["checks"])
    require(isinstance(checks, list), "checks must be null or an array")
    # Reasons may discuss retained, replaced, or removed Checks. These are Plan
    # objects, not behavioral evidence; full Check validation still precedes return.
    check_ids = {c["id"] for c in payload["plan"]["checks"]}
    for check in checks:
        fields(check, ("id", "update_ids", "question"), "Check")
        check_ids.add(text(check["id"], "check.id"))
    current = _current_references(payload)
    contexts = {ref.rsplit('/', 1)[0] for ref in payload['memory']['sources']}
    if memory_view == KNOWLEDGE_ONLY:
        history = historical_references(view["memory"])
    else:
        history = set(view["memory"]["sources"])
        for key, source in view["memory"]["sources"].items():
            if key.endswith("/diff"):
                continue
            history.update((f"{key}:0", f"{key}:outcome"))
            history.update(step["step"] for step in source["run"]["trace"])

    def prose(value, name, *, reason=False):
        text(value, name)
        cited = []
        if reason:
            # Reason backticks are reserved for one exact formal ID per span.
            cited = re.findall(r"`([^`\n]+)`", value)
            uncited = re.sub(r"`([^`\n]+)`", "", value)
            if "`" in uncited:
                masked = re.sub(r"`([^`\n]+)`", lambda match: " " * len(match.group()), value)
                raise ValueError(f"{name}: malformed single-backtick citation near "
                                 f"{_excerpt(value[masked.index('`'):])}")
            unquoted = HISTORY_REF.search(uncited) or LOCAL_REF.search(uncited)
            require(not unquoted, f"{name}: ID {_excerpt(unquoted.group()) if unquoted else ''} "
                    "requires single-backtick citation format")
            for ref in cited:
                require(ref in current | history | originals.keys() | check_ids,
                        f"{name}: backtick content {_excerpt(ref)} is not in the allowed reference set")
        _prose_references(value, name, current=current, history=history, contexts=contexts)
        return cited

    require(isinstance(result["adjustments"], list), "adjustments must be an array")
    indexed = {}
    citations = {}
    for adjustment in result["adjustments"]:
        fields(adjustment, ("target", "focus", "change", "reason", "to"), "Adjustment")
        uid = text(adjustment["target"], "target")
        require(uid in originals and uid not in indexed, "Unknown or duplicate Original target")
        indexed[uid] = adjustment
        focus = adjustment["focus"]
        require(isinstance(focus, list) and all(isinstance(f, str) and f in ("D", "S", "C") for f in focus),
                "focus must contain only D/S/C")
        require(len(focus) == len(set(focus)), "Duplicate focus dimension")
        prose(adjustment["change"], f"Update {uid}.change")
        citations[uid] = prose(adjustment["reason"], f"Update {uid}.reason", reason=True)
        keep = adjustment["change"] == "KEEP"
        require(keep == (focus == []) == (adjustment["to"] is None), "Inconsistent KEEP/focus/to")
        if not keep and adjustment["to"] != []:
            fields(adjustment["to"], ("patch",), "Patch Update")
            text(adjustment["to"]["patch"], f"Update {uid}.to.patch (patch-level validation)")
    require(indexed.keys() == originals.keys(), "Every Original requires exactly one Adjustment")

    normalized, survivors = [], set(originals)
    for uid, original in originals.items():
        adjustment = indexed[uid]
        if adjustment["change"] == "KEEP":
            continue
        if adjustment["to"] == []:
            replacement = []
            survivors.remove(uid)
        else:
            try:
                adjusted = apply_patch(original["text"], adjustment["to"]["patch"])
            except ValueError as exc:
                location = "" if str(exc).startswith("Hunk") else "patch-level validation: "
                raise ValueError(f"Update {uid}.to.patch: {location}{exc}") from exc
            prose(adjusted, f"Update {uid}.text")
            replacement = [{"id": uid, "text": adjusted}]
        normalized.append({
            "from": [uid], "to": replacement,
            "basis": list(dict.fromkeys([*original["basis"], *[r for r in citations[uid] if r in current]])),
            "reason": f"target={uid}; focus={','.join(adjustment['focus'])}; "
                      f"change={adjustment['change']}; reason={adjustment['reason']}",
        })

    # V23 returns early for all-withdrawn results; don't let dangling Checks pass.
    if not survivors:
        require(checks == [], "All withdrawn Updates require resolved checks=[]")
    for check in checks:
        prose(check["question"], f"Check {check['id']}.question")
    legacy = {"decision": "ready" if survivors else "no_change",
              "reason": "Deterministically compiled from validated V23.5 adjustments.",
              "adjustments": normalized, "checks": checks}
    effective = compile_effective_plan(legacy, payload, memory_contract=memory_contract)
    return legacy, effective


def actual_update_diffs(payload, effective):
    """Standard diffs for modified surviving Updates; withdrawals remain explicit."""
    originals = {u["id"]: u["text"] for u in payload["plan"]["updates"]}
    return {u["id"]: actual_diff(originals[u["id"]], u["text"])
            for u in (effective["updates"] if effective else [])
            if u["text"] != originals[u["id"]]}
