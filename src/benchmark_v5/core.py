"""A narrow tool boundary and private, copy-on-read audit record.

Only decorated tools enter the catalog. The agent never receives state snapshots,
scenario internals, grader results, or per-event authorization truth.
"""
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
from typing import get_args, get_origin, get_type_hints

from . import VERSION

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "benchmarks/standalone/editions/v5/prototypes/scenarios.json"


class ToolError(Exception):
    pass


def tool(fn):
    fn.is_v5_tool = True
    return fn


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def load_scenario(name):
    data = json.loads(FIXTURE.read_text())
    scenario = deepcopy(data["scenarios"][name])
    scenario.update(id=name, edition=data["edition"], split=data["split"], max_calls=data["max_calls"])
    return scenario


def schema_type(annotation):
    if get_origin(annotation) is list:
        return {"type": "array", "items": schema_type(get_args(annotation)[0])}
    return {"type": {str: "string", int: "integer", bool: "boolean", dict: "object"}[annotation]}


def matches(value, annotation):
    if get_origin(annotation) is list:
        return isinstance(value, list) and all(matches(v, get_args(annotation)[0]) for v in value)
    return type(value) is annotation


class Environment:
    def __init__(self, scenario):
        self.scenario = deepcopy(scenario)
        self.state = {"closed": False, "receipt": None, "protected": {"other_order": "unchanged"}}
        self.events = []
        self.initial = None
        self._tools = {name: getattr(self, name) for name in dir(self)
                       if getattr(getattr(self, name), "is_v5_tool", False)}

    def seal_initial(self):
        self.initial = deepcopy(self.state)

    def catalog(self):
        catalog = []
        for name, fn in sorted(self._tools.items()):
            sig, hints = inspect.signature(fn), get_type_hints(fn)
            catalog.append({"name": name, "description": inspect.getdoc(fn), "parameters": {
                "type": "object", "properties": {k: schema_type(hints[k]) for k in sig.parameters},
                "required": [k for k, p in sig.parameters.items() if p.default is inspect.Parameter.empty],
                "additionalProperties": False}})
        return catalog

    def call(self, name, arguments):
        if self.state["closed"]:
            return {"error": "SESSION_CLOSED"}
        if len(self.events) >= self.scenario["max_calls"]:
            self.end_budget()
            return {"error": "CALL_BUDGET_EXHAUSTED"}
        before = deepcopy(self.state)
        try:
            if name not in self._tools or type(arguments) is not dict:
                raise ToolError("UNKNOWN_TOOL_OR_INVALID_ARGUMENTS")
            fn = self._tools[name]
            try:
                bound = inspect.signature(fn).bind(**arguments)
            except TypeError as exc:
                raise ToolError("INVALID_ARGUMENTS") from exc
            hints = get_type_hints(fn)
            if not all(matches(v, hints[k]) for k, v in bound.arguments.items()):
                raise ToolError("INVALID_ARGUMENT_TYPES")
            result = fn(**deepcopy(arguments))
        except ToolError as exc:
            self.state = deepcopy(before)  # never alias a retained event snapshot
            result = {"error": str(exc)}
        except Exception:
            self.state = deepcopy(before)
            raise  # harness/infrastructure failure, never silently scored as agent failure
        self._record(name, arguments, result, before)
        return deepcopy(result)

    def _record(self, name, arguments, result, before):
        event = {"seq": len(self.events) + 1, "tool": name, "arguments": deepcopy(arguments),
                 "result": deepcopy(result), "before": deepcopy(before), "after": deepcopy(self.state),
                 "previous_hash": self.events[-1]["hash"] if self.events else digest(self.initial)}
        event["hash"] = digest(event)
        self.events.append(event)

    def end_budget(self):
        if not self.state["closed"]:
            before = deepcopy(self.state)
            self.state["closed"] = True
            self._record("__end__", {"reason": "execution_ended"}, {}, before)

    @tool
    def finish(self, receipt: dict):
        """Close service with the structured receipt fields declared in the user request.

        This records the agent's claims verbatim; it does not validate claims or
        manufacture success. Do not add unstructured prose or undeclared fields.
        """
        self.state["receipt"] = deepcopy(receipt)
        self.state["closed"] = True
        return {"closed": True}

    def audit(self):
        return deepcopy({"version": VERSION, "scenario": self.scenario, "initial": self.initial,
                         "events": self.events, "final": self.state})

    def reserve_id(self, prefix, mapping):
        return f"{prefix}-{len(mapping) + 1}"


def verify_audit(record):
    previous, state = digest(record["initial"]), record["initial"]
    for n, event in enumerate(record["events"], 1):
        body = {k: v for k, v in event.items() if k != "hash"}
        if (event["seq"] != n or event["previous_hash"] != previous or event["before"] != state
                or event["hash"] != digest(body)):
            raise ValueError("INVALID_AUDIT_CHAIN")
        previous, state = event["hash"], event["after"]
    if state != record["final"]:
        raise ValueError("INVALID_FINAL_STATE")
    return True
