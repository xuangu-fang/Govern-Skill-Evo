from src.skill_evolution.v24.benchmark import current as benchmark_current
from src.skill_evolution.v24.resources import resource
"""Deterministic model-only Memory projection; full archives remain authoritative."""
from copy import deepcopy
import json

from src.skill_evolution.v24.facts import require
from src.skill_evolution.v24.contracts.memory import validate_memory, LEGACY_CONTRACT, MULTI_KNOWLEDGE_CONTRACT

FORMAT = "memory_evidence_view_v3"
LEGACY = "entries_sources"
FORMAT_PATH = resource("v23_3/memory_view_prompt.md")
MULTI_FORMAT_PATH = resource("v23_3/multi_knowledge_view_prompt.md")


def ranges(numbers):
    result = []
    for number in sorted(set(numbers)):
        if result and number == result[-1][1] + 1:
            result[-1][1] = number
        else:
            result.append([number, number])
    return result


def compact_memory(*args, **kwargs):
    return benchmark_current().evidence("contracts.memory_view.compact_memory", *args, **kwargs)


def project_payload(payload, memory_view=FORMAT, *, memory_contract=LEGACY_CONTRACT):
    require(memory_view in (FORMAT, LEGACY), "Unsupported Memory view")
    validate_memory(payload["memory"], memory_contract=memory_contract)
    result = deepcopy(payload)
    if memory_view == FORMAT:
        result["memory"] = compact_memory(payload["memory"], memory_contract=memory_contract)
    return result


def project_messages(messages, memory_view=FORMAT, *, memory_contract=LEGACY_CONTRACT):
    """Also usable by the free-replacement A arm without changing its policy."""
    require(memory_view in (FORMAT, LEGACY), "Unsupported Memory view")
    result = deepcopy(messages)
    payload = project_payload(json.loads(result[1]["content"]), memory_view, memory_contract=memory_contract)
    if memory_view == FORMAT:
        result[1]["content"] = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        result[0]["content"] += "\n\n" + FORMAT_PATH.read_text(encoding="utf-8")
    if memory_contract == MULTI_KNOWLEDGE_CONTRACT:
        result[0]["content"] += "\n\n" + MULTI_FORMAT_PATH.read_text(encoding="utf-8")
    return result
