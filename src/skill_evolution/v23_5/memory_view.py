"""Knowledge Only is a model-input view, never a replacement for the archive."""
from copy import deepcopy
from pathlib import Path
import re

from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23.memory import MULTI_KNOWLEDGE_CONTRACT, normalize_memory
from src.skill_evolution.v23_3.memory_view import FORMAT as MEMORY_V3, project_payload as project_v3

KNOWLEDGE_ONLY = "memory_knowledge_only_v1"
PROMPT_PATH = Path(__file__).with_name("knowledge_only_view_prompt.md")
# Recognize explicit historical citations in prose, including attempted ranges.
# Evidence-array permissions are checked as exact strings, independently of this scan.
HISTORY_REF = re.compile(r"[A-Za-z0-9_-]+/(?:diff\b|[PQ]\d+(?::[A-Za-z0-9_]+)?)(?:[-–][A-Za-z0-9_:]+)?")
# Read the whole slash expression, including step colons and attempted ranges.
# Never restart inside it (e.g. at '35' in Q10:35/Q10:39).
PROSE_SLASH_REF = re.compile(
    r"(?<![A-Za-z0-9_:/–-])[A-Za-z0-9_:/–-]+/[A-Za-z0-9_:/–-]*(?![A-Za-z0-9_:/–-])")
CURRENT_RUN_REF = re.compile(r"[PQ]\d+(?::[A-Za-z0-9_]+)?")


def knowledge_only(memory, *, memory_contract=MULTI_KNOWLEDGE_CONTRACT):
    normalized = normalize_memory(memory, source_contract=memory_contract)
    return {"format": KNOWLEDGE_ONLY, "entries": normalized["entries"]}


def historical_references(view):
    """Exact supplied provenance only: no run, neighbor, outcome or Diff expansion."""
    require(view.get("format") == KNOWLEDGE_ONLY, "Expected Knowledge Only view")
    return {ref for entry in view["entries"] for item in entry["knowledge"] for ref in item["evidence"]}


def check_historical_prose(value, allowed, *, current=(), historical_contexts=(), location="Knowledge text"):
    """Validate prose without confusing verified current pairs with history.

    Evidence arrays remain exact IDs. Archive context names only detect ambiguity;
    they never grant access to historical evidence or change the model input.
    Return a temporary scan view masking validated expressions so callers can
    check remaining local references without rescanning inside historical IDs.
    """
    contexts = set(historical_contexts) | {ref.rsplit('/', 1)[0] for ref in allowed}
    def check(match):
        ref = match.group()
        parts = ref.split('/')
        # Ordinary prose such as 'and/or' is not an execution reference.
        if not any(re.match(r"(?:diff\b|[PQ]\d)", part) for part in parts[1:]):
            return ref
        excerpt = repr(ref[:120]) + ('...' if len(ref) > 120 else '')
        if all(CURRENT_RUN_REF.fullmatch(part) and part in current for part in parts):
            require(not any(part in contexts for part in parts[:-1]),
                    f"{location}: Ambiguous current/historical reference {excerpt}")
        else:
            require(ref in allowed, f"{location}: Unavailable historical reference in text: {excerpt}")
        return ' ' * len(ref)
    return PROSE_SLASH_REF.sub(check, value)


def project_payload(payload, memory_view, *, memory_contract=MULTI_KNOWLEDGE_CONTRACT):
    require(memory_view in (MEMORY_V3, KNOWLEDGE_ONLY), "Unsupported V23.5 Memory view")
    if memory_view == MEMORY_V3:
        return project_v3(payload, memory_view, memory_contract=memory_contract)
    # Do not even construct a compact historical source view on this path.
    result = {key: deepcopy(value) for key, value in payload.items() if key != "memory"}
    result["memory"] = knowledge_only(payload["memory"], memory_contract=memory_contract)
    return result
