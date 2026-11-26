"""Independent v29.8 Replay: verified joint execution, hard-transition Knowledge.

No Actor/model transport, independent Update execution, Gate or Memory writes.
The complete batch remains in the audit bundle; only transitions reach the model.
"""
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Callable

from src.skill_evolution.v27.benchmark import current
from src.skill_evolution.v27.contracts.diagnosis import fields
from src.skill_evolution.v27.contracts.editor import _utf8
from src.skill_evolution.v27.facts import require, text
from src.skill_evolution.v27.json_response import parse_json_response
from src.skill_evolution.v29.benchmarks.docvqa import evidence, protocol
from src.skill_evolution.v29.benchmarks.docvqa.facts import run_references
from . import prompt_execution_context, editor
from src.skill_evolution.v29_2 import replay_input_view
from src.skill_evolution.v29_2.explicit_references import parse as parse_references
from src.skill_evolution.v29_2.execution_references import references

PROMPT_VERSION = 'v29_8_docvqa_replay_v1'
CONTRACT_VERSION = 'v29_2_replay_transition_knowledge_v4'
PROMPT_PATH = Path(__file__).with_name('prompts') / 'replay.md'


def _same(left, right):
    # Do not accept booleans in place of numeric scores or counters.
    return (json.dumps(left, sort_keys=True, allow_nan=False) ==
            json.dumps(right, sort_keys=True, allow_nan=False))


def build_replay_from_editor(saved, parent_records, candidate_records):
    """Rebuild the complete verified comparison before selecting any tasks."""
    with current().memory_operation():
        view = editor.editor_input(saved)
        require(all(k in saved for k in ('editor', 'editor_status', 'candidate_text', 'actual_diff')),
                'Replay requires completed Editor output')
        constructed = editor.construct_candidate(saved['editor'], view)
        require(constructed['editor_status'] == 'candidate', 'Replay needs a real Candidate')
        require(_same(constructed, {k: saved[k] for k in constructed}), 'Editor handoff changed')
        parent = current().build_facts(parent_records, role='parent')
        candidate = current().build_facts(candidate_records, role='candidate')
        require(_same(parent['facts'], saved['facts']) and
                _same(parent['background'], saved['background']) and
                _same(parent['background'], candidate['background']), 'Frozen Parent lineage differs')
        require(candidate['facts']['parent'] == constructed['candidate_text'], 'Executed Candidate differs')
        by_task = {r['task_id']: (r, run) for r, run in zip(candidate_records, candidate['facts']['runs'])}
        tasks = [r['task_id'] for r in parent_records]
        require(len(set(tasks)) == len(tasks) and len(by_task) == len(candidate_records) and
                set(tasks) == set(by_task), 'Replay requires exact complete task coverage')
        runs, pairs = [], []
        for index, (record, prun) in enumerate(zip(parent_records, parent['facts']['runs']), 1):
            qr, qrun = by_task[record['task_id']]
            evidence.verify_pair(record, qr)
            # As in v29.1, assign Q references in Parent batch order, BEFORE filtering.
            qrun = evidence.relabel(qrun, f'Q{index}')
            runs.extend([deepcopy(prun), qrun])
            pair = {'parent': prun['ref'], 'candidate': qrun['ref'], 'task_id': prun['task_id'],
                    'parent_result': evidence.pair_result(prun), 'candidate_result': evidence.pair_result(qrun)}
            for side in ('parent_result', 'candidate_result'):
                require(type(pair[side]['hard']) is int and pair[side]['hard'] in (0, 1), 'Invalid hard result')
            pairs.append(pair)
        edits = {edit['update_id']: edit for edit in saved['editor']['edits']}
        payload = {'parent': view['parent'], 'diff': constructed['actual_diff'], 'plan': view['plan'],
                   'edits': [{'update_id': u['id'], 'patch': edits[u['id']]['patch']}
                             for u in view['plan']['updates']], 'pairs': pairs, 'runs': runs}
        return deepcopy({'payload': payload, 'background': parent['background'],
                         'audit': {'editor': saved, 'parent_records': parent_records,
                                   'candidate_records': candidate_records}})


def validate_bundle(bundle):
    fields(bundle, ('payload', 'background', 'audit'), 'Replay bundle')
    fields(bundle['audit'], ('editor', 'parent_records', 'candidate_records'), 'Replay audit')
    a = bundle['audit']
    rebuilt = build_replay_from_editor(a['editor'], a['parent_records'], a['candidate_records'])
    require(_same(bundle, rebuilt), 'Replay bundle differs from verified Editor/execution sources')
    return bundle


def replay_input(bundle):
    """Return the full-text transition subset, retaining complete audit validation."""
    validate_bundle(bundle)
    view = deepcopy(bundle['payload'])
    view['pairs'] = [pair for pair in view['pairs']
                     if pair['parent_result']['hard'] != pair['candidate_result']['hard']]
    refs = {pair[side] for pair in view['pairs'] for side in ('parent', 'candidate')}
    view['runs'] = [run for run in view['runs'] if run['ref'] in refs]
    return view


def model_input(bundle):
    return replay_input_view.model_input(replay_input(bundle))


def validate_input(payload, *, bundle):
    expected = model_input(bundle)
    require(_same(payload, expected), 'Replay model input differs from verified transition projection')
    return payload


def _validate_output(result, view):
    """Check coverage/identity/reference permissions, not causal semantics."""
    fields(result, ('entries',), 'Replay')
    require(isinstance(result['entries'], list), 'entries must be an array')
    pairs = {pair['task_id']: pair for pair in view['pairs']}
    require(len(result['entries']) == (1 if pairs else 0),
            'Hard transitions require exactly one entry' if pairs else
            'No hard transitions requires entries=[]')
    runs = {run['ref']: run for run in view['runs']}
    eligible = {edit['update_id'] for edit in view['edits'] if edit['patch'] != ''}
    originals = {u['id'] for u in view['plan']['updates']}
    found = {}
    for entry in result['entries']:
        fields(entry, ('knowledge',), 'Replay entry')
        require(isinstance(entry['knowledge'], list) and entry['knowledge'], 'knowledge must be a nonempty array')
        for item in entry['knowledge']:
            fields(item, ('task_id', 'update_id', 'text'), 'Knowledge')
            tid = text(item['task_id'], 'task_id')
            require(tid in pairs and tid not in found, 'Unknown, unchanged or duplicate task event')
            uid = item['update_id']
            if uid is not None:
                text(uid, 'update_id')
                require(uid in eligible, 'Update must have a current nonempty Patch')
            value = text(item['text'], 'Knowledge text')
            _utf8(value)
            pair = pairs[tid]
            refs = set().union(*(run_references(runs[pair[side]]) for side in ('parent', 'candidate')))
            parse_references(value, {'Memory': set(), 'Group': set(), 'Check': set(),
                                     'Update': originals, 'Evidence': refs | {'diff'}}, location=tid)
            require(references(value) <= refs, 'Knowledge cites unavailable or other-task executions')
            found[tid] = item
    require(set(found) == set(pairs), 'Every hard-transition task requires exactly one Knowledge')
    # Knowledge order within the sole entry is normalized to current batch order.
    return [deepcopy(found[tid]) for tid in pairs]


def validate_replay(result, *, bundle):
    _validate_output(result, replay_input(bundle))
    return result


def _finish(bundle, parsed, *, called):
    view = replay_input(bundle)
    knowledge = _validate_output(parsed, view)
    require(bool(view['pairs']) == called, 'Replay call/skip branch differs from verified transitions')
    return {**deepcopy(bundle), 'replay': deepcopy(parsed), 'knowledge': knowledge,
            'replay_called': called, 'replay_skip_reason': None if called else 'no_hard_transitions'}


def skip_replay(bundle):
    """Program-produced empty result; only valid after full verification and no flips.

    This does not commit Memory or decide Gate. Callers retain all source Updates
    from the bundle even though there is no new event Knowledge.
    """
    return _finish(bundle, {'entries': []}, called=False)


def render_prompt(background, *, prompt_version=PROMPT_VERSION):
    require(prompt_version == PROMPT_VERSION, 'Unknown Replay prompt version')
    prompt = PROMPT_PATH.read_text(encoding='utf-8')
    marker, end = '<actor_base_protocol>\n', '\n</actor_base_protocol>'
    require(prompt.count(marker) == prompt.count(end) == 1, 'Invalid Actor protocol quotation')
    require(prompt.split(marker)[1].split(end)[0] == protocol.actor_base_protocol(),
            'Replay/Actor base protocol differs')
    require(prompt_execution_context(background) in prompt, 'Replay/Actor runtime differs')
    return prompt


@dataclass(frozen=True)
class ReplayCall:
    """Local preparation/completion only; caller provides any model response."""
    name: str
    prompt_version: str
    contract_version: str
    input: dict
    messages: list
    complete: Callable

    def complete_text(self, content):
        return self.complete(parse_json_response(content))


def replay_call(bundle):
    """Return a prepared call, or None for no flips; use skip_replay for its receipt."""
    frozen = deepcopy(bundle)
    view = replay_input(frozen)
    if not view['pairs']:
        return None
    payload = replay_input_view.model_input(view)
    messages = [
        {'role': 'system', 'content': render_prompt(frozen['background'])},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False,
                                             separators=(',', ':'), allow_nan=False)},
    ]

    def complete(parsed):
        return _finish(frozen, parsed, called=True)

    return ReplayCall('replay', PROMPT_VERSION, CONTRACT_VERSION,
                      deepcopy(frozen), messages, complete)
