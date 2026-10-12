"""Freeze three retrospective, learning-side validation cases; no model calls."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.v21.current_understanding_v21 import MAX_CHARACTERS
from src.skill_evolution.v21.modification_evidence_v21 import load_modification_evidence

HISTORY = 'artifacts/methods/v21/v21_memory_step4_preflight/round-03-import.json'
CHECK = 'artifacts/methods/v21/v21_memory_step4_preflight/check.json'
CURRENT = 'artifacts/methods/v20/v20_pilot_001_continuation_grouping24k/round-04/generation/source.json'
# Steps are navigation anchors, not a replacement for the complete trajectories.
CASES = [
    ('01_baggage', 'single-traveler-baggage-booking', {
        'T009': {'parent': [6, 11, 12, 13, 14], 'candidate': [6, 10, 11, 13, 14]},
        'T010': {'parent': [12, 13], 'candidate': [13, 14]},
    }),
    ('02_group_booking', 'group-booking-passenger-boundary', {
        'T013': {'parent': [2, 10, 11, 13, 14], 'candidate': [2, 9, 10, 12, 13, 14, 15]},
        'T016': {'parent': [2], 'candidate': [2, 9, 10, 12, 13, 14, 15]},
    }),
    ('03_protection', 'delivered-exchange-protection-condition', {
        'T035': {'parent': [13, 19, 20, 21, 22, 23, 24],
                 'candidate': [8, 11, 12, 13, 14, 15, 16]},
    }),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def prepare(output):
    source_bytes = {p: (ROOT / p).read_bytes() for p in (HISTORY, CHECK, CURRENT)}
    check = json.loads(source_bytes[CHECK])
    history = load_modification_evidence(ROOT / HISTORY, expected_ref=check['evidence_ref']).payload
    current = json.loads(source_bytes[CURRENT])
    archive = history['archive']
    require(MAX_CHARACTERS == 2000, 'This case set preserves the 2,000-character contract')
    require(current['parent_skill'] == history['candidate_skill'], 'Parent lineage differs')
    sources = {p: sha(raw) for p, raw in source_bytes.items()}
    # Exclude the historical Fusion output: it is neither an expected answer nor new evidence.
    shared = {k: current[k] for k in ('parent_skill', 'current_requests', 'current_findings', 'memory')}
    files = {'shared/predecision.json': encoded(shared),
             'shared/parent_skill.md': current['parent_skill'].encode()}
    report = {'model_calls': 0, 'rollout_calls': 0, 'memory_committed': False,
              'current_understanding_max_characters': MAX_CHARACTERS,
              'history_evidence_ref': check['evidence_ref'], 'source_sha256': sources,
              'current_parent_sha256': sha(current['parent_skill'].encode()),
              'all_current_groups': len(current['current_requests']), 'cases': []}
    for case_id, group_id, selections in CASES:
        requests = [r for r in current['current_requests'] if r['provenance']['group_id'] == group_id]
        findings = [f for f in current['current_findings'] if f['group_id'] == group_id]
        require(len(requests) == len(findings) == 1, 'Current group is not unique')
        request, finding = requests[0], findings[0]
        require(request['payload']['current_skill'] == current['parent_skill'], 'Current Skill differs')
        current_events = {e['evidence_ref'] for x in request['payload']['experiences'] for e in x['events']}
        for f in finding['findings']:
            require(set(f['evidence_refs']) <= current_events, 'Unresolved current finding evidence')
        pairs, trajectories, events, contexts, anchors, labels = {}, {}, {}, {}, {}, []
        for task, sides in selections.items():
            matches = [archive['pairs'][p] for p in history['current_pair_refs']
                       if archive['pairs'][p]['task_ref'] == task]
            require(len(matches) == 1, 'Historical pair is not unique')
            pair = matches[0]
            pairs[pair['pair_id']] = pair
            row = {'task_ref': task, 'pair_ref': pair['pair_id']}
            anchors[task] = {}
            for side, steps in sides.items():
                ref = pair[side]
                meta = archive['trajectories'][ref]
                trajectories[ref] = meta
                contexts[meta['context_ref']] = archive['contexts'][meta['context_ref']]
                complete = {r: e for r, e in archive['events'].items() if e['trajectory_ref'] == ref}
                require(bool(complete), 'Empty historical trajectory')
                events.update(complete)
                anchors[task][side] = [next(r for r, e in complete.items() if e['event']['step'] == step)
                                       for step in steps]
                row[side] = {k: meta['supervision'][k] for k in ('success', 'compliant')}
            labels.append(row)
        bindings = request['provenance']['experience_bindings']
        require(set(selections) <= {b['source']['task_ref'] for b in bindings}, 'Missing task alias mapping')
        packet = {
            'purpose': 'Retrospective validation material, not a native runtime input or a v21 result',
            'history_evidence_ref': check['evidence_ref'], 'source_sha256': sources,
            'current_parent_skill': current['parent_skill'],
            'historical_parent_skill': history['parent_skill'],
            'historical_candidate_skill': history['candidate_skill'],
            'historical_round_edits': history['edits'],
            'pairs': pairs, 'trajectories': trajectories, 'events': events, 'contexts': contexts,
            'current_request': request, 'current_findings': finding,
        }
        packet_bytes = encoded(packet)
        files[f'{case_id}/evidence.json'] = packet_bytes
        files[f'{case_id}/anchors.json'] = encoded(anchors)
        lines = [f'# {case_id}: evidence navigation', '',
                 'Historical labels are (success, compliant). Full pairs, public contexts/tools,',
                 'and the complete current group are in `evidence.json`. These excerpts are navigation only.', '']
        for row in labels:
            task = row['task_ref']
            lines += [f'## {task}', '', f"Pair: `{row['pair_ref']}`", '',
                      f"Parent: {row['parent']} → Candidate: {row['candidate']}", '']
            for side, refs in anchors[task].items():
                for ref in refs:
                    lines += [f'### {side}: {ref}', '', '```json',
                              json.dumps(events[ref]['event'], ensure_ascii=False, indent=2), '```', '']
        files[f'{case_id}/evidence.md'] = '\n'.join(lines).encode()
        report['cases'].append({'case_id': case_id, 'group_id': group_id, 'pairs': labels,
                                'historical_events': len(events), 'current_events': len(current_events),
                                'current_findings': len(finding['findings']), 'task_alias_bindings': bindings,
                                'packet_bytes': len(packet_bytes), 'packet_sha256': sha(packet_bytes)})
    report['file_sha256'] = {name: sha(raw) for name, raw in files.items()}
    report['checks'] = ['trusted history reference', 'historical Candidate equals current Parent',
                        'current Skill equality', 'both complete historical sides',
                        'current finding event references', 'explicit task alias bindings',
                        '2,000-character limit unchanged']
    files['manifest.json'] = encoded(report)
    # Validate all existing destinations first; a changed rerun must use a new directory.
    for name, raw in files.items():
        path = output / name
        require(not path.exists() or path.read_bytes() == raw, f'Refusing to replace different file: {path}')
    for name, raw in files.items():
        path = output / name
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/methods/v21/v21_validation_cases')
    args = parser.parse_args()
    result = prepare(args.output.resolve())
    print(json.dumps({'output': str(args.output.resolve()), 'cases': len(result['cases']),
                      'model_calls': 0, 'rollout_calls': 0,
                      'checks': result['checks']}, ensure_ascii=False))
