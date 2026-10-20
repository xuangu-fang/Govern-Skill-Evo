"""Split an Editor citation only across an omitted numbered-list marker.

No Candidate bytes or semantic fields are changed. This offline operation does
not repair an instruction, infer missing words, or certify its behavior.
"""

from copy import deepcopy
import re

from src.adapters.alfworld.verify_skill_run import require
from .compact_update import validate_editor


NORMALIZATION = "v22.editor_numbered_span_split.v1"
_MARKER = r"[ \t]*\r?\n[ \t]*[1-9][0-9]*\.[ \t]+"


def _numbered_spans(excerpt, text):
    # Only an actual ASCII space in the citation can represent an omitted line
    # break and numeric marker. Every other character must match byte for byte.
    pattern = re.compile((r"(?: |(" + _MARKER + r"))").join(
        re.escape(part) for part in excerpt.split(" ")))
    matches, position = [], 0
    while position <= len(text):
        match = pattern.search(text, position)
        if match is None:
            break
        matches.append(match)
        require(len(matches) == 1, "Numbered-span citation has ambiguous matches.")
        position = match.start() + 1  # Also detect overlapping alternative matches.
    require(len(matches) == 1, "Citation differs by more than numbered-list formatting.")
    match = matches[0]
    gaps = [match.span(index) for index, gap in enumerate(match.groups(), 1) if gap is not None]
    require(bool(gaps), "Citation has no omitted numbered-list marker.")
    spans, start = [], match.start()
    for left, right in gaps:
        spans.append(text[start:left])
        start = right
    spans.append(text[start:match.end()])
    require(all(span and span in text for span in spans) and " ".join(spans) == excerpt,
             "Splitting would change the citation's nonformatting content.")
    return spans


def normalize_numbered_spans(value, payload):
    """Return exact mappings, splitting only uniquely located Candidate citations.

    Exact citations remain untouched, even if their text occurs more than once.
    A malformed Parent citation cannot be repaired by this Candidate-only rule.
    Existing Editor validation remains authoritative for all other constraints.
    """
    require(isinstance(value, dict) and isinstance(value.get("mappings"), list),
             "Editor mappings must be an array.")
    normalized = deepcopy(value)
    normalized["mappings"] = []
    for row in value["mappings"]:
        require(isinstance(row, dict) and isinstance(row.get("excerpt"), str) and bool(row["excerpt"]),
                 "Mapping citation must be nonempty text.")
        text = (payload.get("parent", {}).get("text") or "") if row.get("side") == "parent" else value.get("candidate_text")
        require(isinstance(text, str), "Citation side has no text.")
        if row["excerpt"] in text:
            normalized["mappings"].append(deepcopy(row))
            continue
        require(row.get("side") == "candidate", "Only Candidate numbered spans can be split.")
        for span in _numbered_spans(row["excerpt"], text):
            replacement = deepcopy(row)
            replacement["excerpt"] = span
            normalized["mappings"].append(replacement)
    return validate_editor(normalized, payload)
