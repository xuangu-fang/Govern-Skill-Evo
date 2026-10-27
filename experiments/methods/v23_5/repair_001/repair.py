"""Strict local Repair contract and copy-only merge. No model or Memory writes."""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.methods.v23_5.verifier_input_001 import verifier as v
from src.skill_evolution.v23_5.replay import validate_result as validate_candidate


def exact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def validate_result(result, model_input):
    """model_input must be from the verified frozen package. No semantic checks."""
    expected = {v.position(t['target'], 'input.target'): t['knowledge'] for t in model_input['targets']}
    v.check(len(expected) == len(model_input['targets']), 'input.targets', 'duplicate target')
    v.fields(result, ('changes',), 'output')
    v.check(isinstance(result['changes'], list), 'output.changes', 'must be an array')
    seen = set()
    for index, change in enumerate(result['changes']):
        loc = f'changes[{index}]'
        v.fields(change, ('target', 'knowledge'), loc)
        key = v.position(change['target'], f'{loc}.target')
        v.check(key in expected and key not in seen, loc, 'unauthorized or duplicate target')
        seen.add(key)
        knowledge = change['knowledge']
        if knowledge is None:
            continue
        v.fields(knowledge, ('text', 'evidence'), f'{loc}.knowledge')
        v.nonempty(knowledge['text'], f'{loc}.knowledge.text')
        refs = knowledge['evidence']
        v.check(isinstance(refs, list) and bool(refs), loc, 'evidence must be a nonempty array')
        used = set()
        for ref in refs:
            v.nonempty(ref, f'{loc}.evidence')
            v.check(ref in model_input['source_records'] and ref not in used, loc,
                    'unprovided or duplicate evidence')
            used.add(ref)
        v.check(exact(knowledge) != exact(expected[key]), loc, 'unchanged Knowledge is not a repair')
    v.check(seen == set(expected), 'output.changes', 'missing authorized targets')
    return result


def validate_response(response, model_input):
    v.check(isinstance(response, dict) and response.get('finish_reason') == 'stop',
            'response', 'must finish with stop')
    return validate_result(v.parse_output(response.get('content')), model_input)


def merge(result, model_input, candidate, payload):
    """Apply all edits against original indices; return a detached, validated candidate.

    Original Memory is untouched. Existing revision IDs/Entry order are preserved.
    A last-item deletion or loss of Entry-level evidence fails the existing schema.
    Preservation is relative to the frozen candidate, not a semantic judgment of
    which historical experiences Replay should have retained.
    """
    validate_candidate(candidate, payload)
    validate_result(result, model_input)
    changes = {v.position(c['target'], 'change.target'): c['knowledge'] for c in result['changes']}
    for target in model_input['targets']:
        ei, ki = v.position(target['target'], 'input.target')
        v.check(ei < len(candidate['entries']) and ki < len(candidate['entries'][ei]['knowledge']),
                'input.target', 'outside frozen candidate')
        v.check(exact(candidate['entries'][ei]['knowledge'][ki]) == exact(target['knowledge']),
                'input.target', 'candidate Knowledge differs from authorized original')
    merged = deepcopy(candidate)
    for ei, entry in enumerate(candidate['entries']):
        items = []
        for ki, item in enumerate(entry['knowledge']):
            replacement = changes.get((ei, ki), item)
            if replacement is not None:
                items.append(deepcopy(replacement))
        merged['entries'][ei]['knowledge'] = items
    validate_candidate(merged, payload)  # Formal schema, active revisions, historical permissions.
    return merged
