"""Audited removal of an empty Parent section scaffold, without rule edits."""
import hashlib
from .memory_store_v19 import require


def apply_layout(text, layout):
    if layout is None:
        return text
    if layout == FLAT_LAYOUT:
        return flatten(text)
    require(type(layout) is dict and set(layout) == {'schema_version', 'source_sha256', 'candidate_sha256', 'removed_text', 'offset', 'authorization'}, 'invalid layout fields')
    require(layout['schema_version'] == 'candidate_layout_v19.1', 'invalid layout version')
    require(layout['authorization'] == 'USER_REQUESTED_FLAT_RULE_LAYOUT', 'layout authorization required')
    require(hashlib.sha256(text.encode()).hexdigest() == layout['source_sha256'], 'layout source mismatch')
    offset, removed = layout['offset'], layout['removed_text']
    require(type(offset) is int and offset >= 0 and isinstance(removed, str) and bool(removed), 'invalid layout span')
    require(text[offset:offset+len(removed)] == removed, 'layout span mismatch')
    require(all(not line.strip() or (line.startswith('## ') and line[3:].strip()) for line in removed.splitlines()), 'only section headings and whitespace may be removed')
    result = text[:offset] + text[offset+len(removed):]
    require(hashlib.sha256(result.encode()).hexdigest() == layout['candidate_sha256'], 'layout candidate mismatch')
    return result


FLAT_LAYOUT = {'schema_version':'candidate_layout_v19.2',
               'authorization':'USER_REQUESTED_FLAT_RULE_LAYOUT'}


def flat_spans(text):
    """Only remove Markdown section-heading lines; preserve all rule bodies."""
    import re
    spans=[];offset=0;fenced=False
    for line in text.splitlines(keepends=True):
        if re.match(r'^\s*(```|~~~)',line):fenced=not fenced
        if not fenced and re.match(r'^ {0,3}#{2,6}\s+\S',line):
            spans.append((offset,offset+len(line)))
        offset+=len(line)
    return spans


def flatten(text):
    result=text
    for lo,hi in reversed(flat_spans(text)):result=result[:lo]+result[hi:]
    return result
