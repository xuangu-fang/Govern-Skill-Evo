"""Strict raw-response acceptance and bounded, deterministic text application."""
import hashlib
import json

from .editor_contract_v17 import EditorRejected
from .editor_input_v17 import build_editor_input


def _parse(raw):
    if not isinstance(raw, str):
        raise EditorRejected('PARSE', 'JSON text required')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('nonfinite value')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, RecursionError) as exc:
        raise EditorRejected('PARSE', 'invalid JSON response') from exc


def _validate(output, count):
    if type(output) is not dict or set(output) != {'status', 'reason', 'edits'}:
        raise EditorRejected('STRUCTURE', 'exact response fields required')
    if type(output['status']) is not str or output['status'] not in ('EDITED', 'UNABLE'):
        raise EditorRejected('STRUCTURE', 'invalid status')
    if not isinstance(output['reason'], str) or not output['reason'].strip() or type(output['edits']) is not list:
        raise EditorRejected('STRUCTURE', 'nonempty reason and edits list required')
    for edit in output['edits']:
        if type(edit) is not dict or set(edit) != {'edit_unit_index', 'text'}:
            raise EditorRejected('STRUCTURE', 'exact edit fields required')
        if type(edit['edit_unit_index']) is not int or edit['edit_unit_index'] < 0:
            raise EditorRejected('STRUCTURE', 'nonnegative integer index required')
        if not isinstance(edit['text'], str) or not edit['text'].strip():
            raise EditorRejected('STRUCTURE', 'nonempty edit text required')
        try:
            edit['text'].encode('utf-8')
        except UnicodeEncodeError as exc:
            raise EditorRejected('STRUCTURE', 'edit must be valid UTF-8 text') from exc
    expected = list(range(count)) if output['status'] == 'EDITED' else []
    if [e['edit_unit_index'] for e in output['edits']] != expected:
        raise EditorRejected('COVERAGE', 'exact ordered coverage required')


def apply_editor_response(raw, *, editor_input) -> dict:
    """Revalidate runtime input on every call; return no candidate on UNABLE/NOOP.

    No externally supplied offsets or mutable validated-output DTO are trusted.
    The program copies every untargeted original slice verbatim. Semantic fidelity
    of new text is not established by this boundary check.
    """
    request = build_editor_input(editor_input)
    if not request.edit_units:
        if raw is not None:
            raise EditorRejected('COVERAGE', 'all-NOOP requires no model response')
        return {'status': 'NO_UPDATE', 'candidate_skill': None}
    output = _parse(raw)
    _validate(output, len(request.edit_units))
    base = {'parent_skill_digest': request.parent_skill_digest,
            'plan_sha256': request.plan_sha256,
            'raw_response': raw, 'output': output}
    if output['status'] == 'UNABLE':
        return {**base, 'status': 'UNABLE', 'candidate_skill': None}
    parent = request.parent_skill
    lines = parent.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    spans, additions = [], []
    for unit, edit in zip(request.edit_units, output['edits']):
        text = edit['text']
        block = text if text.endswith('\n') else text + '\n'
        if unit.operation == 'ADD':
            additions.append(block)
            continue
        targets = json.loads(unit.target_rules_json)
        for index, rule in enumerate(targets):
            start, end = rule['start_line'], rule['end_line']
            if not (1 <= start <= end <= len(lines)):
                raise EditorRejected('APPLY', 'target outside Parent')
            lo, hi = offsets[start - 1], offsets[end]
            if parent[lo:hi] != rule['text']:
                raise EditorRejected('APPLY', 'target text mismatch')
            spans.append((lo, hi, block if index == 0 else ''))
    spans.sort(key=lambda s: s[0])
    cursor, parts = 0, []
    for lo, hi, replacement in spans:
        if lo < cursor:
            raise EditorRejected('APPLY', 'overlapping targets')
        parts.extend((parent[cursor:lo], replacement))
        cursor = hi
    parts.append(parent[cursor:])
    candidate = ''.join(parts)
    if additions:
        if candidate:
            if not candidate.endswith('\n'):
                candidate += '\n'
            candidate += '\n'
        candidate += '\n'.join(additions)
    return {**base, 'status': 'EDITED', 'candidate_skill': candidate,
            'candidate_sha256': hashlib.sha256(candidate.encode('utf-8')).hexdigest()}
