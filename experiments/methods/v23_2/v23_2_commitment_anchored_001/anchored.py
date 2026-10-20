"""Experimental, offline anchored edits -> existing V23 Adjustments. No generation API."""
from copy import deepcopy
import difflib
import hashlib
import json
from pathlib import Path

from src.skill_evolution.v23.diagnosis import fields, links, validate_diagnosis
from src.skill_evolution.v23.facts import require, text
from src.skill_evolution.v23.memory import validate_memory
from src.skill_evolution.v23.preconditioner import compile_effective_plan

TOP = ('plan_sha256', 'decision', 'reason', 'edits', 'checks')
EDIT = ('update_id', 'operation', 'anchor_text', 'replacement_text', 'role',
        'basis', 'reason', 'depends_on')
OPS = {'replace', 'delete', 'insert_before', 'insert_after'}
ROLES = {'target', 'supporting', 'independent'}


def plan_hash(plan):
    data = json.dumps(plan, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def unique_span(source, anchor):
    """Exact UTF-8 offsets; detect overlapping occurrences too."""
    needle = anchor.encode('utf-8')
    start = source.find(needle)
    require(start >= 0, 'anchor_missing')
    require(source.find(needle, start + 1) < 0, 'anchor_ambiguous')
    return start, start + len(needle)


def transform(payload, proposal):
    """Atomic pure operation. On any failure no result is returned or persisted."""
    payload, proposal = deepcopy(payload), deepcopy(proposal)
    fields(proposal, TOP, 'Anchored proposal')
    plan = payload['plan']
    require(proposal['plan_sha256'] == plan_hash(plan), 'stale_plan_hash')
    validate_diagnosis({'decision': 'revise', 'reason': 'Frozen input', 'plan': plan}, payload)
    validate_memory(payload['memory'])
    require(proposal['decision'] in ('ready', 'no_change', 'need_evidence'), 'invalid_decision')
    text(proposal['reason'], 'reason')
    edits = proposal['edits']
    require(isinstance(edits, list), 'edits_must_be_array')
    if proposal['decision'] == 'need_evidence':
        require(not edits and proposal['checks'] is None, 'need_evidence_requires_no_edits')
    originals = {u['id']: u for u in plan['updates']}
    allowed = set(payload['command_sets']) | {g['group_id'] for g in payload['grouping']['groups']}
    allowed |= {e['id'] for e in payload['memory']['entries']}
    for run in payload['runs']:
        allowed.update([run['ref'], run['ref'] + ':0', run['ref'] + ':outcome'])
        allowed.update(s['step'] for s in run['steps'])
    located = []
    for i, edit in enumerate(edits):
        fields(edit, EDIT, f'Edit {i}')
        uid = text(edit['update_id'], 'update_id')
        require(uid in originals, 'unknown_update_id')
        require(isinstance(edit['operation'], str) and edit['operation'] in OPS, 'unsupported_operation')
        require(isinstance(edit['role'], str) and edit['role'] in ROLES, 'unsupported_role')
        anchor = text(edit['anchor_text'], 'anchor_text')
        replacement = edit['replacement_text']
        require(isinstance(replacement, str), 'replacement_must_be_string')
        if edit['operation'] == 'delete':
            require(replacement == '', 'delete_requires_empty_replacement')
        else:
            text(replacement, 'replacement_text')
            require(edit['operation'] != 'replace' or replacement != anchor, 'use_keep_for_identical_replacement')
        links(edit['basis'], allowed, 'edit.basis')
        text(edit['reason'], 'edit.reason')
        deps = edit['depends_on']
        require(isinstance(deps, list) and all(type(d) is int for d in deps), 'invalid_dependencies')
        require(len(deps) == len(set(deps)), 'duplicate_dependencies')
        if edit['role'] == 'supporting':
            require(bool(deps), 'supporting_requires_dependency')
            require(all(0 <= d < len(edits) and d != i for d in deps), 'invalid_dependency_index')
            require(all(isinstance(edits[d], dict) and edits[d].get('role') in ('target', 'independent')
                        for d in deps), 'dependency_must_be_root_edit')
        else:
            require(not deps, 'only_supporting_has_dependencies')
        source = originals[uid]['text'].encode('utf-8')
        a, b = unique_span(source, anchor)
        start, end = a, b
        if edit['operation'] == 'insert_before': end = start
        if edit['operation'] == 'insert_after': start = end
        located.append({**edit, 'index': i, 'anchor_span': [a, b], 'span': [start, end]})

    # Conservative simultaneous conflict policy includes read-only insertion anchors.
    for i, left in enumerate(located):
        for right in located[i + 1:]:
            if left['update_id'] != right['update_id']: continue
            a, b = left['anchor_span']; c, d = right['anchor_span']
            conflict = max(a, c) < min(b, d)
            for one, other in ((left, right), (right, left)):
                if one['span'][0] == one['span'][1]:
                    conflict |= other['anchor_span'][0] <= one['span'][0] <= other['anchor_span'][1]
            require(not conflict, 'anchor_or_insertion_conflict')

    output = {'decision': proposal['decision'], 'reason': proposal['reason'],
              'adjustments': [], 'checks': deepcopy(proposal['checks'])}
    audit = []
    for uid, original in originals.items():
        group = sorted((e for e in located if e['update_id'] == uid), key=lambda e: e['span'])
        source = original['text'].encode('utf-8')
        cursor, result, preserved, mappings = 0, bytearray(), [], []
        for edit in group:
            start, end = edit['span']
            if start > cursor:
                dest = len(result); part = source[cursor:start]; result.extend(part)
                preserved.append({'source': [cursor, start], 'result': [dest, len(result)],
                                  'sha256': hashlib.sha256(part).hexdigest()})
            dest = len(result); result.extend(edit['replacement_text'].encode('utf-8'))
            mappings.append({**edit, 'result_span': [dest, len(result)]})
            cursor = end
        if cursor < len(source):
            dest = len(result); part = source[cursor:]; result.extend(part)
            preserved.append({'source': [cursor, len(source)], 'result': [dest, len(result)],
                              'sha256': hashlib.sha256(part).hexdigest()})
        for segment in preserved:
            a, b = segment['source']; c, d = segment['result']
            require(source[a:b] == result[c:d], 'internal_preservation_failure')
        new_text = bytes(result).decode('utf-8')
        if group:
            withdraw = (len(group) == 1 and group[0]['operation'] == 'delete'
                        and group[0]['anchor_span'] == [0, len(source)])
            require(withdraw or bool(new_text.strip()), 'empty_text_requires_explicit_whole_delete')
            basis = list(dict.fromkeys(ref for edit in group for ref in edit['basis']))
            reason = '\n'.join(f"Edit {e['index']} ({e['role']}; depends_on={e['depends_on']}): {e['reason']}"
                               for e in group)
            output['adjustments'].append({'from': [uid], 'to': [] if withdraw else [{'id': uid, 'text': new_text}],
                                          'basis': basis, 'reason': reason})
        diff = ''.join(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n'
                       for line in difflib.unified_diff(original['text'].splitlines(keepends=True),
                                                       new_text.splitlines(keepends=True),
                                                       fromfile=f'Original/{uid}', tofile=f'Applied/{uid}'))
        audit.append({'update_id': uid, 'original_sha256': hashlib.sha256(source).hexdigest(),
                      'result_sha256': hashlib.sha256(result).hexdigest(), 'edits': mappings,
                      'preserved_segments': preserved, 'diff': diff})
    effective = compile_effective_plan(output, payload)
    return {'preconditioner': output, 'effective_plan': effective,
            'audit': {'plan_sha256': proposal['plan_sha256'], 'updates': audit,
                      'semantic_validity': 'not_evaluated', 'byte_preservation_verified': True}}


def load_json(path):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'duplicate_json_key')
            value[key] = item
        return value
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', required=True)
    parser.add_argument('--proposal', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=False)
    receipt = {'mode': 'offline_only', 'new_model_calls': 0, 'new_environment_calls': 0, 'sources': {}}
    try:
        for kind, name in (('payload', args.payload), ('proposal', args.proposal)):
            path = Path(name).resolve()
            receipt['sources'][kind] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        value = transform(load_json(args.payload), load_json(args.proposal))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        receipt.update(status='rejected', error={'type': type(exc).__name__, 'message': str(exc)})
        (out/'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
        raise SystemExit(2)
    for name, content in value.items():
        (out/(name+'.json')).write_text(json.dumps(content, ensure_ascii=False, indent=2)+'\n')
    (out/'changes.diff').write_text('\n'.join(u['diff'] for u in value['audit']['updates']))
    receipt.update(status='compiled', semantic_validity='not_evaluated')
    (out/'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
