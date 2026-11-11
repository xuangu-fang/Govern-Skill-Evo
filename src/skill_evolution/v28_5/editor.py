"""Independent v28.5 Editor: mapped patches against one frozen Parent.

Structural validation and deterministic construction only; no model transport,
Actor execution, Gate, Memory publication or claim of semantic independence.
"""
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Callable

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.contracts.diagnosis import fields
from src.skill_evolution.v27.contracts.editor import _lines, _utf8, actual_diff, NO_NEWLINE
from src.skill_evolution.v27.facts import require, text
from src.skill_evolution.v27.json_response import parse_json_response
from src.skill_evolution.v28.benchmarks.searchqa import protocol
from . import preconditioner

PROMPT_VERSION = 'v28_5_searchqa_editor_v1'
CONTRACT_VERSION = 'v28_5_editor_mapped_patches_v1'
PROMPT_PATH = protocol.ROOT / 'docs/methods/v28_5/prompts' / 'editor.md'


def _validate_model_input(payload):
    fields(payload, ('parent', 'plan'), 'Editor input')
    require(payload['parent'] is None or isinstance(payload['parent'], str), 'Invalid Parent')
    _utf8(payload['parent'] or '')
    plan = payload['plan']
    fields(plan, ('goal', 'updates'), 'Effective Plan view')
    _utf8(text(plan['goal'], 'Goal'))
    require(isinstance(plan['updates'], list) and plan['updates'], 'Editor requires effective Updates')
    ids = set()
    for update in plan['updates']:
        fields(update, ('id', 'text'), 'Effective Update view')
        uid = text(update['id'], 'Update ID')
        _utf8(uid)
        require(uid not in ids, 'Duplicate Effective Update ID')
        ids.add(uid)
        _utf8(text(update['text'], 'Effective Update text'))


def editor_input(saved):
    """Recompile verified upstream decisions before projecting id/text only."""
    require(isinstance(saved, dict) and
            all(key in saved for key in ('memory', 'preconditioner', 'effective_plan')),
            'Editor requires completed v28.5 Preconditioner output')
    with current().memory_operation():
        upstream = preconditioner.preconditioner_input(saved, saved['memory'])
        effective = preconditioner.compile_effective_plan(saved['preconditioner'], upstream, saved=saved)
        require(effective == saved['effective_plan'], 'Saved Effective Plan differs from compiled decisions')
        require(effective is not None, 'Editor requires a nonempty Effective Plan')
        payload = {'parent': upstream['parent'], 'plan': {
            'goal': effective['goal'],
            'updates': [{'id': u['id'], 'text': u['text']} for u in effective['updates']],
        }}
        _validate_model_input(payload)
        return deepcopy(payload)


def validate_input(payload, *, saved):
    _validate_model_input(payload)
    require(payload == editor_input(saved), 'Editor input differs from verified Effective Plan projection')
    return payload


@dataclass(frozen=True)
class _Change:
    """Internal half-open original line range; start=end denotes an insertion."""
    start: int
    end: int
    lines: tuple
    update_id: str


def _parse_patch(parent, patch, uid):
    """Locate every hunk in Parent, then retain only its actual change blocks.

    Same grammar as v29.1. Context can overlap across different Updates, but
    hunks within one patch retain the old strict order/non-overlap requirement.
    No individual Skill is executed or required to be nonblank; the combined
    Candidate is checked after all ranges have been validated.
    """
    _utf8(patch)
    require(bool(patch.strip()), f'{uid}: whitespace-only patch is invalid')
    source, lines = _lines(parent or ''), _lines(patch)
    header = '--- /dev/null\n' if parent is None else '--- a/SKILL.md\n'
    require(len(lines) >= 3 and lines[:2] == [header, '+++ b/SKILL.md\n'],
            f'{uid}: expected exact unnumbered SKILL.md diff headers')
    changes, i, hunk, previous = [], 2, 0, None
    while i < len(lines):
        hunk += 1

        def check(condition, message):
            require(condition, f'{uid} hunk {hunk}: {message}')

        check(lines[i] == '@@\n', 'expected bare @@ header')
        i += 1
        old, new, body = [], [], []
        while i < len(lines) and lines[i] != '@@\n':
            line = lines[i]
            check(line[:1] in (' ', '-', '+') and line.endswith('\n'), 'invalid body line')
            prefix, content = line[0], line[1:]
            i += 1
            if i < len(lines) and lines[i] in (NO_NEWLINE, NO_NEWLINE + '\n'):
                content = content[:-1]
                i += 1
            body.append((prefix, content))
            if prefix in (' ', '-'): old.append(content)
            if prefix in (' ', '+'): new.append(content)
        check(old != new, 'hunk must make an actual change')
        check(all(line.endswith('\n') for line in old[:-1] + new[:-1]),
              'missing-newline marker before fragment EOF')
        if not source:
            check(hunk == 1 and not old and i == len(lines), 'empty source requires one addition-only hunk')
            start = 0
        else:
            check(bool(old), 'insertion into nonempty Parent requires context')
            matches = [at for at in range(len(source) - len(old) + 1)
                       if source[at:at + len(old)] == old]
            check(len(matches) == 1, f'expected one exact source match; found {len(matches)}')
            start = matches[0]
        if previous is not None:
            check(start > previous[0] and start >= previous[1],
                  'hunks must be in source order and cannot overlap, including context')
        previous = (start, start + len(old))
        # A run of +/- lines is one replacement; spaces are read-only anchors.
        at, j = start, 0
        while j < len(body):
            if body[j][0] == ' ':
                at += 1
                j += 1
                continue
            begin, added = at, []
            while j < len(body) and body[j][0] != ' ':
                prefix, content = body[j]
                if prefix == '-': at += 1
                else: added.append(content)
                j += 1
            if source[begin:at] != added:
                changes.append(_Change(begin, at, tuple(added), uid))
    require(bool(changes), f'{uid}: patch makes no actual modification')
    return changes


def _check_conflicts(changes):
    for i, left in enumerate(changes):
        for right in changes[i + 1:]:
            overlap = max(left.start, right.start) < min(left.end, right.end)
            interior = ((left.start == left.end and right.start < left.start < right.end) or
                        (right.start == right.end and left.start < right.start < left.end))
            require(not (overlap or interior),
                    f'Conflicting patches: {left.update_id} [{left.start}:{left.end}] and '
                    f'{right.update_id} [{right.start}:{right.end}]')


@dataclass(frozen=True)
class _InlineChange:
    """A uniquely located, contiguous character edit in one original line."""
    start: int
    end: int
    text: str
    update_id: str


def _inline_change(old, new, uid):
    # Keep the maximal identical prefix and suffix. If these overlap, a
    # deletion/insertion can slide through repeated text: do not pick a side.
    # An edit spanning multiple changed islands remains one conservative span;
    # no heuristic alignment or semantic merging is used to split it further.
    limit, prefix, suffix = min(len(old), len(new)), 0, 0
    while prefix < limit and old[prefix] == new[prefix]:
        prefix += 1
    while suffix < limit and old[len(old) - suffix - 1] == new[len(new) - suffix - 1]:
        suffix += 1
    require(prefix + suffix <= limit, f'{uid}: Ambiguous inline modification location')
    return _InlineChange(prefix, len(old) - suffix, new[prefix:len(new) - suffix], uid)


def _prepare_changes(parent, changes):
    """Refine shared single-line replacements, then check all actual ranges.

    Only one-old-line/one-new-line blocks qualify. Other replacements keep
    their original line ranges; they are not guessed into line correspondences.
    Raw patches and Update ownership remain intact for subset reconstruction.
    """
    source, groups = _lines(parent or ''), {}
    for change in changes:
        if change.end == change.start + 1 and len(change.lines) == 1:
            groups.setdefault(change.start, []).append(change)
    merged = {}
    for line, group in groups.items():
        if len(group) < 2:
            continue
        spans = [_inline_change(source[line], change.lines[0], change.update_id) for change in group]
        _check_conflicts(spans)
        ordered = sorted(spans, key=lambda c: (c.start, c.start != c.end))
        pieces, cursor = [], 0
        for span in ordered:
            pieces.extend((source[line][cursor:span.start], span.text))
            cursor = span.end
        pieces.append(source[line][cursor:])
        merged[line] = _Change(line, line + 1, (''.join(pieces),),
                               ','.join(change.update_id for change in group))
    prepared = []
    for change in changes:
        if change.start in merged and change in groups[change.start]:
            if change is groups[change.start][0]:
                prepared.append(merged[change.start])
        else:
            prepared.append(change)
    _check_conflicts(prepared)
    return prepared


def _compose(parent, changes, *, label):
    """Compose original-source ranges in supplied Effective Update order."""
    changes = _prepare_changes(parent, changes)
    # Stable sorting preserves Update order at a shared insertion gap. At a
    # replacement's start boundary, insertions precede the replacement.
    ordered = sorted(changes, key=lambda c: (c.start, c.start != c.end))
    source, output, cursor = _lines(parent or ''), [], 0
    for change in ordered:
        output.extend(source[cursor:change.start])
        output.extend(change.lines)
        cursor = change.end
    output.extend(source[cursor:])
    require(all(line.endswith('\n') for line in output[:-1]), f'Missing-newline marker before {label} EOF')
    return ''.join(output)


def construct_candidate(result, payload):
    """Pure structural entry point; archive-backed callers use validate_editor.

    Null is a legal semantic stop, not a schema failure. Still validate every
    supplied edit before returning a stop. Never return a partial Candidate.
    """
    _validate_model_input(payload)
    fields(result, ('edits',), 'Editor')
    require(isinstance(result['edits'], list), 'edits must be an array')
    ids = [u['id'] for u in payload['plan']['updates']]
    indexed = {}
    for edit in result['edits']:
        fields(edit, ('update_id', 'patch', 'reason'), 'Edit')
        uid = text(edit['update_id'], 'update_id')
        require(uid in ids and uid not in indexed, 'Unknown or duplicate Update mapping')
        _utf8(text(edit['reason'], f'{uid}.reason'))
        require(edit['patch'] is None or isinstance(edit['patch'], str), f'{uid}: invalid patch type')
        indexed[uid] = edit
    require(set(indexed) == set(ids), 'Every Effective Update requires exactly one edit')
    parent, changes, blocked = payload['parent'], [], False
    for uid in ids:
        patch = indexed[uid]['patch']
        if patch is None:
            blocked = True
        elif patch != '':
            changes.extend(_parse_patch(parent, patch, uid))
    if blocked or not changes:
        _prepare_changes(parent, changes)
        return {'editor_status': 'needs_revision' if blocked else 'no_change',
                'candidate_text': None, 'actual_diff': None}
    candidate = _compose(parent, changes, label='Candidate')
    require(bool(candidate.strip()) and candidate != (parent or ''),
            'Combined patches produce empty or unchanged Candidate')
    return {'editor_status': 'candidate', 'candidate_text': candidate,
            'actual_diff': actual_diff(parent, candidate)}


def validate_editor(result, payload, *, saved):
    validate_input(payload, saved=saved)
    return construct_candidate(result, payload)


def construct_selected(result, payload, selected_update_ids):
    """Pure subset reconstruction from the full, valid Editor result and Parent.

    Reject blocked or malformed full outputs even if their bad edit is omitted.
    Caller order cannot override Effective Update order. Empty selection (or
    only empty patches) preserves Parent exactly, including None/empty text.
    Validate the actual subset; no dependency inference, repair or silent
    fallback is performed. Text composition is not execution validation, and
    no Candidate score or execution status is attached to the Selected Skill.
    """
    full = construct_candidate(result, payload)
    require(full['editor_status'] != 'needs_revision', 'Cannot select from a blocked Editor result')
    ids = [u['id'] for u in payload['plan']['updates']]
    require(isinstance(selected_update_ids, list) and
            all(isinstance(uid, str) and uid in ids for uid in selected_update_ids),
            'Selection must be an array of Effective Update IDs')
    require(len(selected_update_ids) == len(set(selected_update_ids)), 'Duplicate selected Update ID')
    chosen = set(selected_update_ids)
    selected = [uid for uid in ids if uid in chosen]
    edits = {edit['update_id']: edit for edit in result['edits']}
    parent, changes = payload['parent'], []
    for uid in selected:
        patch = edits[uid]['patch']
        if patch != '':
            changes.extend(_parse_patch(parent, patch, uid))
    selected_text = parent
    if changes:
        selected_text = _compose(parent, changes, label='Selected Skill')
        require(bool(selected_text.strip()), 'Selected patches produce empty Skill')
    # A subset can cancel to Parent even when the complete Candidate differs.
    return {'selected_update_ids': selected, 'selected_text': selected_text,
            'actual_diff': '' if selected_text == parent else actual_diff(parent, selected_text)}


def select_skill(saved, selected_update_ids):
    """Archive-backed subset entry point. Does not choose IDs or publish results."""
    with current().memory_operation():
        view = editor_input(saved)
        require(all(k in saved for k in ('editor', 'editor_status', 'candidate_text', 'actual_diff')),
                'Selection requires completed Editor output')
        full = construct_candidate(saved['editor'], view)
        require(all(saved[key] == value for key, value in full.items()), 'Editor handoff changed')
        return construct_selected(saved['editor'], view, selected_update_ids)


def render_prompt(background, *, prompt_version=PROMPT_VERSION):
    require(prompt_version == PROMPT_VERSION, 'Unknown Editor prompt version')
    prompt = PROMPT_PATH.read_text(encoding='utf-8')
    marker, end = '<actor_base_protocol>\n', '\n</actor_base_protocol>'
    require(prompt.count(marker) == prompt.count(end) == 1, 'Invalid Actor protocol quotation')
    require(prompt.split(marker)[1].split(end)[0] == protocol.actor_base_protocol(),
            'Editor/Actor base protocol differs')
    require(protocol.execution_context(background) in prompt, 'Editor/Actor runtime differs')
    return prompt


@dataclass(frozen=True)
class EditorCall:
    """Versioned local preparation/completion; no publication or model transport."""
    name: str
    prompt_version: str
    contract_version: str
    input: dict
    messages: list
    complete: Callable

    def complete_text(self, content):
        return self.complete(parse_json_response(content))


def editor_call(saved):
    frozen = deepcopy(saved)
    payload = editor_input(frozen)
    messages = [
        {'role': 'system', 'content': render_prompt(frozen['background'])},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False,
                                             separators=(',', ':'), allow_nan=False)},
    ]

    def complete(parsed):
        with current().memory_operation():
            checked = editor_input(frozen)
            constructed = construct_candidate(parsed, checked)
        return {**deepcopy(frozen), 'editor': deepcopy(parsed), **constructed}

    return EditorCall('editor', PROMPT_VERSION, CONTRACT_VERSION,
                      deepcopy(frozen), messages, complete)
