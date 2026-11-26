"""v28.13 Gate: retain at least two net attributed EM gains per Update.

No model calls, independent Update execution, Memory writes or publication.
Retain is a selection decision, not proof of an independent causal effect.
Character deltas and legacy simplification flags are audit measurements only.
"""
from copy import deepcopy
import json

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.contracts.diagnosis import fields
from src.skill_evolution.v27.facts import require
from . import editor, replay

CONTRACT_VERSION = 'v28_13_gate_net_em_min2_v1'


def _same(left, right):
    # JSON equality distinguishes bool/int and int/float. Array types are
    # checked explicitly at the public boundaries below.
    try:
        return (json.dumps(left, sort_keys=True, allow_nan=False) ==
                json.dumps(right, sort_keys=True, allow_nan=False))
    except (TypeError, ValueError):
        return False


def _verified_receipt(replayed):
    fields(replayed, ('payload', 'background', 'audit', 'replay', 'knowledge',
                      'replay_called', 'replay_skip_reason'), 'Gate Replay receipt')
    bundle = {key: replayed[key] for key in ('payload', 'background', 'audit')}
    # Rebuild from registered archives, verify the entire batch including
    # unchanged tasks, then validate transition coverage and Update links.
    replay.validate_replay(replayed['replay'], bundle=bundle)
    pairs = [pair for pair in bundle['payload']['pairs']
             if pair['parent_result']['em'] != pair['candidate_result']['em']]
    found = {item['task_id']: item for entry in replayed['replay']['entries']
             for item in entry['knowledge']}
    knowledge = [found[pair['task_id']] for pair in pairs]
    require(isinstance(replayed['knowledge'], list) and _same(replayed['knowledge'], knowledge),
            'Saved Knowledge differs from canonical Replay output')
    called = bool(pairs)
    require(replayed['replay_called'] is called and
            replayed['replay_skip_reason'] == (None if called else 'no_em_transitions'),
            'Replay call/skip receipt differs from verified transitions')
    return bundle, knowledge


def _validate_output(result):
    fields(result, ('decisions', 'selection', 'selected_execution_source'), 'Gate result')
    require(isinstance(result['decisions'], list), 'Gate decisions must be an array')
    for decision in result['decisions']:
        fields(decision, ('update_id', 'G', 'L', 'delta_chars', 'pure_simplification', 'gate_decision'),
               'Gate Update decision')
        require(isinstance(decision['update_id'], str) and bool(decision['update_id'].strip()),
                'Invalid Gate Update ID')
        require(all(type(decision[key]) is int and decision[key] >= 0 for key in ('G', 'L')),
                'G/L must be nonnegative integers')
        require(type(decision['delta_chars']) is int and type(decision['pure_simplification']) is bool,
                'Invalid Gate patch measurements')
        require(decision['gate_decision'] in ('Retain', 'Reject', 'Defer', None), 'Invalid Gate decision')
    selection = result['selection']
    fields(selection, ('selected_update_ids', 'selected_text', 'actual_diff'), 'Gate selection')
    require(isinstance(selection['selected_update_ids'], list) and
            all(isinstance(uid, str) for uid in selection['selected_update_ids']), 'Invalid selected IDs')
    require(selection['selected_text'] is None or isinstance(selection['selected_text'], str),
            'Invalid selected text')
    require(isinstance(selection['actual_diff'], str), 'Invalid selected diff')
    require(result['selected_execution_source'] in ('parent', 'candidate', None),
            'Invalid selected execution source')


def _decision(patch, gains, losses):
    if patch == '':
        return None
    net = gains - losses
    if net < 0:
        return 'Reject'
    if net >= 2:
        return 'Retain'
    return 'Defer'


def evaluate_gate(replayed):
    """Verify a completed Replay receipt and deterministically select Updates.

    Reject/Defer omit only this round's patch; empty patches have no decision.
    Invalid selected subsets raise rather than triggering repair or fallback.
    Execution source refers only to exact text in this verified batch; a new
    combination has source=None and does not inherit Candidate scores.
    """
    frozen = deepcopy(replayed)
    with current().memory_operation():
        bundle, knowledge = _verified_receipt(frozen)
        payload = bundle['payload']
        patches = {edit['update_id']: edit['patch'] for edit in payload['edits']}
        pairs = {pair['task_id']: pair for pair in payload['pairs']}
        counts = {update['id']: {'G': 0, 'L': 0} for update in payload['plan']['updates']}
        for item in knowledge:
            uid = item['update_id']
            if uid is not None:
                pair = pairs[item['task_id']]
                # Transition coverage and binary numeric EM values have been
                # verified above. Prose and historical Memory never cast votes.
                key = 'G' if pair['candidate_result']['em'] == 1 else 'L'
                counts[uid][key] += 1
        require(sum(c['G'] + c['L'] for c in counts.values()) ==
                sum(item['update_id'] is not None for item in knowledge), 'Gate event accounting differs')
        decisions = []
        saved_editor = bundle['audit']['editor']
        # Replay validation already recompiled this Effective Plan from the Preconditioner receipt.
        for update in saved_editor['effective_plan']['updates']:
            uid = update['id']
            gains, losses = counts[uid]['G'], counts[uid]['L']
            patch = patches[uid]
            delta = editor.patch_char_delta(payload['parent'], patch, uid)
            pure = update.get('pure_simplification', False)
            decisions.append({'update_id': uid, 'G': gains, 'L': losses, 'delta_chars': delta,
                              'pure_simplification': pure, 'gate_decision': _decision(patch, gains, losses)})
        selected_ids = [d['update_id'] for d in decisions if d['gate_decision'] == 'Retain']
        selection = editor.select_skill(saved_editor, selected_ids)
        selected = selection['selected_text']
        source = ('parent' if selected == payload['parent'] else
                  'candidate' if selected == saved_editor['candidate_text'] else None)
        result = {'decisions': decisions, 'selection': selection, 'selected_execution_source': source}
        _validate_output(result)
        return deepcopy(result)


def validate_gate(result, *, replayed):
    """Validate exact schema and recompute decisions, selection and provenance."""
    _validate_output(result)
    require(_same(result, evaluate_gate(replayed)), 'Gate result differs from verified evidence and selection')
    return deepcopy(result)
