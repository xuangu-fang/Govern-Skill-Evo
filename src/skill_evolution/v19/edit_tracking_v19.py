"""Deterministic edit ledger and cross-round provenance; no model or Gate calls.

The v18 compiler/application interfaces are reused read-only. Every ledger is
rebuilt from its bound sources before consumption, including after disk reload.
History links express intent; structural ancestry and text presence are separate.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from ..v18.compiler_contract_v18 import CompilerDiagnosisSource, CompilerInput
from ..v18.compiler_validation_v18 import plan_payload
from ..v18.compiler_v18 import compile_edit_plan
from ..v18.diagnosis_references_v18 import build_reference_catalogs, resolve_reference
from ..v18.diagnosis_validation_v18 import validate_diagnosis_response
from ..v18.editor_apply_v18 import apply_editor_response
from ..v18.editor_contract_v18 import EditorInput
from ..v18.editor_input_v18 import build_editor_input
from ..v17.group_diagnosis_input_v17 import GroupDiagnosisInput
from ..v15.information_boundary_v15 import _seal, unpack


class TrackingRejected(ValueError):
    pass


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _require(condition, reason):
    if not condition:
        raise TrackingRejected(reason)


def _text(value):
    return type(value) is str and bool(value.strip())


def parse(text):
    def pairs(items):
        output = {}
        for key, value in items:
            _require(key not in output, 'duplicate JSON key')
            output[key] = value
        return output

    def constant(_):
        raise TrackingRejected('nonfinite JSON value')

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, TypeError) as exc:
        raise TrackingRejected('invalid tracking JSON') from exc


def skill_ref(text):
    sha = digest(text)
    return {'skill_id': 'SKILL/' + sha, 'sha256': sha, 'text_ref': 'TEXT/' + sha}


@dataclass(frozen=True)
class EditLedger:
    """Immutable serialized source and result. Properties return fresh objects."""

    input_json: str
    output_json: str

    @property
    def payload(self):
        return parse(self.output_json)

    @property
    def source(self):
        return parse(self.input_json)


@dataclass(frozen=True)
class DecidedEdits:
    """Caller-supplied completed whole-package decision, not a memory commit.

    This layer checks ACCEPT/RETAIN and Skill continuity, not whether Monitor
    actually ran. The future campaign owns that trust boundary and atomic commit.
    """

    ledger: EditLedger
    gate_decision: str


def _snapshot(value):
    from .verified_compiler_v19 import VerifiedEditorInput
    if isinstance(value,VerifiedEditorInput):
        return {'schema_version':'verified_editor_snapshot_v19.1','parent_skill':value.compiler_input.parent_skill,
                'audit':parse(value.audit_json),'plan':plan_payload(value.plan)}
    return {
        'round_id': value.compiler_input.round_id,
        'parent_skill': value.compiler_input.parent_skill,
        'sources': [{
            'diagnosis_ref': s.diagnosis_ref,
            'request_payload': s.request.learner_payload,
            'provenance': s.request.provenance,
            'raw_response': unpack(s.validated, 'V18_VALIDATED_DIAGNOSIS')['raw_response'],
        } for s in sorted(value.compiler_input.diagnoses, key=lambda s: s.diagnosis_ref)],
        'plan': plan_payload(value.plan),
    }


def _restore(snapshot):
    if snapshot.get('schema_version')=='verified_editor_snapshot_v19.1':
        from .local_generation_v19 import restore_local_audit
        value,_=restore_local_audit(encode(snapshot['audit']))
        _require(_snapshot(value)==snapshot,'verified source snapshot changed')
        return value
    _require(type(snapshot) is dict and set(snapshot) == {
        'round_id', 'parent_skill', 'sources', 'plan'}, 'invalid source snapshot')
    _require(type(snapshot['sources']) is list, 'sources list required')
    sources = []
    for item in snapshot['sources']:
        _require(type(item) is dict and set(item) == {
            'diagnosis_ref', 'request_payload', 'provenance', 'raw_response'},
            'invalid Diagnosis snapshot')
        request = GroupDiagnosisInput(_seal('V17_GROUP_DIAGNOSIS_INPUT', item['request_payload']),
                                      encode(item['provenance']))
        validated = validate_diagnosis_response(item['raw_response'], request=request)
        sources.append(CompilerDiagnosisSource(item['diagnosis_ref'], request, validated))
    parent = snapshot['parent_skill']
    compiler_input = CompilerInput(snapshot['round_id'], parent, digest(parent), tuple(sources))
    plan = compile_edit_plan(compiler_input)
    _require(encode(plan_payload(plan)) == encode(snapshot['plan']), 'saved plan differs from sources')
    return EditorInput(compiler_input, plan)


def history_ref(history):
    """Order, decisions and full prior ledger contents participate in the binding."""
    return digest(encode([{
        'input_sha256': digest(h.ledger.input_json),
        'output_sha256': digest(h.ledger.output_json),
        'gate_decision': h.gate_decision,
    } for h in history]))


def _derive(run_id, value, raw_response, candidate_skill, history, links, generation_audit=None):
    _require(_text(run_id), 'nonempty run_id required')
    if any(s.request.learner_payload.get('consumer_version') == 'memory_diagnosis_v19.1'
           for s in value.compiler_input.diagnoses):
        # Recheck the v19 review-to-gap lineage even when restoring a ledger from
        # disk through the unchanged v18 compiler adapter.
        from .memory_diagnosis_v19 import memory_links_for_plan
        _require(links == memory_links_for_plan(value, run_id=run_id),
                 'memory links differ from reauthorized Diagnosis sources')
    if generation_audit is not None:
        from .separated_generation_v19 import validate_generation_audit, generation_history_links
        validate_generation_audit(generation_audit,value)
        _require(links == generation_history_links(generation_audit,value,run_id), 'separated history links changed')
    from .verified_compiler_v19 import VerifiedEditorInput, apply_verified_editor, build_verified_editor_input, restored
    local=isinstance(value,VerifiedEditorInput)
    applied = (apply_verified_editor if local else apply_editor_response)(raw_response, editor_input=value)
    _require(applied['status'] in ('EDITED', 'APPLIED_DETERMINISTIC'),
             'only a completed Candidate can publish an edit ledger')
    _require(type(candidate_skill) is str and candidate_skill == applied['candidate_skill'],
             'Candidate differs from deterministic application')
    request = (build_verified_editor_input if local else build_editor_input)(value)
    round_id = value.compiler_input.round_id
    prior_records = {}
    for prior in history:
        payload = prior.ledger.payload
        _require(payload['run_id'] == run_id, 'history belongs to another run')
        _require(payload['round_id'] != round_id, 'round already tracked')
        prior_records.update({e['edit_id']: e for e in payload['edits']})
    if history:
        last = history[-1]
        retained = last.ledger.source['candidate_skill'] if last.gate_decision == 'ACCEPT' else last.ledger.source['editor']['parent_skill']
        _require(retained == request.parent_skill, 'Parent does not match retained history')

    plan_ref = {'artifact_id': 'PLAN/' + request.plan_sha256, 'sha256': request.plan_sha256}
    parent_ref, candidate_ref = skill_ref(request.parent_skill), skill_ref(candidate_skill)
    by_source = {s.diagnosis_ref: s for s in value.compiler_input.diagnoses}
    local_sources={r.payload['proposal_id']:(q.payload,r.payload) for q,r in restored(value)} if local else {}
    edits, evidence = [], {}
    for unit in request.edit_units:
        plan_unit = value.plan.edit_units[unit.edit_unit_index]
        refs = []
        for gap_ref in plan_unit.supporting_gap_refs:
            if local:
                packet,result=local_sources[gap_ref.diagnosis_ref]
                gap={'evidence_refs':sorted(set(result['evidence_refs']+result['counterevidence_refs']))}
            else:
                source = by_source[gap_ref.diagnosis_ref]
                gap = unpack(source.validated, 'V18_VALIDATED_DIAGNOSIS')['semantic']['parent_skill_gaps'][gap_ref.gap_index]
            for ref in gap['evidence_refs']:
                if local:
                    kind='TRAJECTORY';event=packet['events'][ref]
                    resolved={'ref':ref,**event,'trajectory':packet['trajectories'][event['trajectory_ref']]}
                else:
                    kind = 'VISIBLE_POLICY' if ref in source.request.learner_payload['available_policy_refs'] else 'TRAJECTORY'
                    resolved = resolve_reference(source.request, ref, reference_type=kind)
                identity = {'run_id': run_id, 'round_id': round_id,
                            'diagnosis_ref': gap_ref.diagnosis_ref, 'reference_type': kind, 'ref': ref}
                evidence_id = 'EVIDENCE/' + digest(encode(identity))
                evidence[evidence_id] = {'evidence_id': evidence_id, **identity, 'resolved': resolved}
                refs.append(evidence_id)
        after = ''
        if unit.operation != 'DELETE':
            text = next(e['text'] for e in applied['output']['edits']
                        if e['edit_unit_index'] == unit.edit_unit_index)
            after = text if text.endswith('\n') else text + '\n'
        # Candidate digest is essential: a plan alone does not bind Editor text.
        identity = {'run_id': run_id, 'round_id': round_id, 'plan_sha256': request.plan_sha256,
                    'candidate_sha256': candidate_ref['sha256'], 'edit_unit_index': unit.edit_unit_index}
        edits.append({
            'schema_version': 'edit_record_v19.1', 'edit_id': 'EDIT/' + digest(encode(identity)),
            'run_id': run_id, 'round_id': round_id,
            'parent_skill_ref': parent_ref, 'candidate_skill_ref': candidate_ref,
            'plan_ref': plan_ref, 'edit_unit_index': unit.edit_unit_index, 'operation': unit.operation,
            'target_blocks': [{k: block[k] for k in ('ref', 'start_line', 'end_line', 'text')}
                              for block in parse(unit.target_rules_json)],
            'after_text': after,
            'source_gap_refs': [{'diagnosis_ref': r.diagnosis_ref, 'gap_index': r.gap_index}
                                for r in plan_unit.supporting_gap_refs],
            'source_evidence_refs': sorted(set(refs)), 'related_history': [],
        })

    _require(type(links) is list, 'history links must be a list')
    seen = set()
    for item in links:
        _require(type(item) is dict and set(item) == {'edit_unit_index', 'prior_edit_id', 'relation', 'basis_refs'},
                 'exact history link fields required')
        index = item['edit_unit_index']
        _require(type(index) is int and 0 <= index < len(edits), 'invalid linked edit index')
        _require(type(item['prior_edit_id']) is str and item['prior_edit_id'] in prior_records,
                 'link must address an earlier edit in this run')
        _require(item['relation'] in ('REVISES', 'RETRIES', 'REVERTS'), 'invalid history relation')
        basis = item['basis_refs']
        _require(type(basis) is list and bool(basis) and all(type(r) is str for r in basis)
                 and len(set(basis)) == len(basis), 'nonempty unique basis references required')
        available = set(edits[index]['source_evidence_refs']) | set(prior_records[item['prior_edit_id']]['source_evidence_refs'])
        _require(set(basis) <= available, 'history basis is not evidence of the linked edits')
        key = (index, item['prior_edit_id'])
        _require(key not in seen, 'duplicate or conflicting history link')
        seen.add(key)
        edits[index]['related_history'].append({k: item[k] for k in ('prior_edit_id', 'relation', 'basis_refs')})
    for edit in edits:
        edit['related_history'].sort(key=lambda r: r['prior_edit_id'])
    payload = {'schema_version': 'edit_ledger_v19.1', 'run_id': run_id, 'round_id': round_id,
               'parent_skill_ref': parent_ref, 'candidate_skill_ref': candidate_ref, 'plan_ref': plan_ref,
               'previous_history_sha256': history_ref(history),
               'edits': edits, 'evidence': [evidence[k] for k in sorted(evidence)]}
    layout = generation_audit.get('candidate_layout') if generation_audit else None
    if layout is not None:
        payload['candidate_layout'] = layout
    _require(reconstruct_candidate(request.parent_skill, edits, layout=layout) == candidate_skill,
             'ledger does not reconstruct Candidate')
    if generation_audit is not None:
        payload['generation_audit_sha256'] = digest(encode(generation_audit))
    return payload


def reconstruct_candidate(parent, edits, *, layout=None):
    """Reconstruct audited records. Public consumers must validate the ledger first."""
    text, _, _ = _apply_segments(parent, [(parent, None, ())], edits, layout=layout)
    return text


def build_edit_ledger(*, run_id, editor_input, raw_response, candidate_skill,
                      history=(), related_history=(), generation_audit=None):
    """Publish every applied unit or fail; this function never calls a model."""
    validate_history(history)
    links = list(related_history)
    payload = _derive(run_id, editor_input, raw_response, candidate_skill, history, links, generation_audit)
    source = {'schema_version': 'edit_tracking_input_v19.1', 'run_id': run_id,
              'editor': _snapshot(editor_input), 'raw_response': raw_response,
              'candidate_skill': candidate_skill, 'related_history': links,
              'previous_history_sha256': history_ref(history)}
    if generation_audit is not None:
        source['generation_audit'] = generation_audit
    return EditLedger(encode(source), encode(payload))


def _validate_ledger(ledger, history):
    _require(isinstance(ledger, EditLedger), 'EditLedger required')
    source = ledger.source
    _require(type(source) is dict and set(source) - {'generation_audit'} == {
        'schema_version', 'run_id', 'editor', 'raw_response', 'candidate_skill',
        'related_history', 'previous_history_sha256'}, 'invalid ledger input fields')
    _require(source['schema_version'] == 'edit_tracking_input_v19.1', 'invalid input version')
    _require(source['previous_history_sha256'] == history_ref(history), 'history binding mismatch')
    try:
        expected = _derive(source['run_id'], _restore(source['editor']), source['raw_response'],
                           source['candidate_skill'], history, source['related_history'], source.get('generation_audit'))
        _require(encode(expected) == encode(ledger.payload), 'ledger differs from revalidated sources')
    except (KeyError, TypeError, ValueError) as exc:
        raise TrackingRejected('invalid bound ledger: ' + str(exc)) from exc
    return expected


def validate_history(history):
    _require(type(history) is tuple, 'ordered history tuple required')
    for index, item in enumerate(history):
        _require(isinstance(item, DecidedEdits) and item.gate_decision in ('ACCEPT', 'RETAIN'),
                 'completed ACCEPT/RETAIN required for historical rounds')
        _validate_ledger(item.ledger, history[:index])


def validate_edit_ledger(ledger, *, history=()):
    validate_history(history)
    return _validate_ledger(ledger, history)


def _slice(segments, lo, hi):
    result, offset = [], 0
    for text, writer, ancestors in segments:
        start, end = max(lo - offset, 0), min(hi - offset, len(text))
        if start < end:
            result.append((text[start:end], writer, ancestors))
        offset += len(text)
    return result


def _apply_segments(parent, segments, edits, *, layout=None):
    """Track exact writes and structural ancestry without semantic text matching."""
    offsets = [0]
    for line in parent.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    changes, adds, events = [], [], []
    for edit in edits:
        targets, inherited = [], set()
        for block in edit['target_blocks']:
            start, end = block['start_line'], block['end_line']
            _require(type(start) is int and type(end) is int and 1 <= start <= end < len(offsets),
                     'invalid target range')
            lo, hi = offsets[start - 1], offsets[end]
            _require(parent[lo:hi] == block['text'], 'target text mismatch')
            targets.append((lo, hi))
            for _, writer, ancestry in _slice(segments, lo, hi):
                if writer is not None:
                    inherited.add(writer)
                inherited.update(ancestry)
        events.append({'edit_id': edit['edit_id'], 'operation': edit['operation'],
                       'affected_prior_edit_ids': sorted(inherited)})
        replacement = [(edit['after_text'], edit['edit_id'], tuple(sorted(inherited)))] if edit['after_text'] else []
        if edit['operation'] == 'ADD':
            adds.append(replacement)
        else:
            for i, (lo, hi) in enumerate(targets):
                changes.append((lo, hi, replacement if i == 0 else []))
    result, cursor = [], 0
    for lo, hi, replacement in sorted(changes):
        _require(lo >= cursor, 'overlapping target ranges')
        result.extend(_slice(segments, cursor, lo))
        result.extend(replacement)
        cursor = hi
    result.extend(_slice(segments, cursor, len(parent)))
    text = ''.join(s[0] for s in result)
    if adds:
        separator = (('' if text.endswith('\n') else '\n') + '\n') if text else ''
        if separator:
            result.append((separator, None, ()))
        for i, addition in enumerate(adds):
            if i:
                result.append(('\n', None, ()))
            result.extend(addition)
    if layout is not None:
        from .candidate_layout_v19 import apply_layout
        before = ''.join(s[0] for s in result)
        after = apply_layout(before, layout)
        from .candidate_layout_v19 import FLAT_LAYOUT, flat_spans
        spans=flat_spans(before) if layout==FLAT_LAYOUT else [(layout['offset'],layout['offset']+len(layout['removed_text']))]
        for lo,hi in reversed(spans):
            removed = _slice(result, lo, hi)
            _require(all(writer is None for _, writer, _ in removed), 'layout cannot remove learned rule text')
            result = _slice(result, 0, lo) + _slice(result, hi, sum(len(s[0]) for s in result))
        _require(''.join(s[0] for s in result) == after, 'layout lineage mismatch')
    return ''.join(s[0] for s in result), result, events


def _rules(text):
    return build_reference_catalogs({'current_skill': text, 'contexts': []})['available_rule_refs']


def _occurrences(text, needle):
    if not needle:
        return []
    result, pos = [], 0
    while True:
        pos = text.find(needle, pos)
        if pos < 0:
            return result
        end = pos + len(needle)
        # Rule/edit text starts on a line. Do not bind "rule" to "another rule"
        # or an unterminated old "- A" to the prefix of a new "- ABC".
        if ((pos == 0 or text[pos - 1] == '\n')
                and (end == len(text) or needle.endswith('\n') or text[end] == '\n')):
            result.append((pos, end))
        pos += 1


def trace_edit_history(history):
    """Rebuild current rules, accepted structural changes and rejected attempts.

    EXACT/PARTIAL describe literal text, not semantic correctness or causal value.
    Semantic rewrites and duplicate locations remain explicitly unresolved.
    """
    validate_history(history)
    _require(bool(history), 'nonempty history required')
    current = history[0].ledger.source['editor']['parent_skill']
    segments = [(current, None, ())]
    entries, changes = [], []
    for item in history:
        payload = item.ledger.payload
        entries.extend((edit, item.gate_decision) for edit in payload['edits'])
        if item.gate_decision == 'ACCEPT':
            current, segments, events = _apply_segments(current, segments, payload['edits'], layout=payload.get('candidate_layout'))
            changes.extend(events)
            _require(current == item.ledger.source['candidate_skill'], 'accepted lineage reconstruction mismatch')

    rules = _rules(current)
    line_offsets = [0]
    for line in current.splitlines(keepends=True):
        line_offsets.append(line_offsets[-1] + len(line))
    current_rules = []
    for ref, block in rules.items():
        lo, hi = line_offsets[block['start_line'] - 1], line_offsets[block['end_line']]
        pieces = _slice(segments, lo, hi)
        current_rules.append({'current_rule_ref': ref, **block,
                              'writer_edit_ids': sorted({w for _, w, _ in pieces if w is not None}),
                              'ancestor_edit_ids': sorted({a for _, _, ancestry in pieces for a in ancestry}),
                              'contains_initial_or_separator_text': any(w is None for _, w, _ in pieces)})

    def rule_refs(spans):
        return [r for r, b in rules.items()
                if any(line_offsets[b['start_line'] - 1] < hi and line_offsets[b['end_line']] > lo
                       for lo, hi in spans)]

    views = []
    for edit, decision in entries:
        # DELETE presence refers to its removed blocks, never to empty after_text.
        fragments = ([b['text'] for b in edit['target_blocks']] if edit['operation'] == 'DELETE'
                     else [edit['after_text']])
        matches = [_occurrences(current, fragment) for fragment in fragments]
        descendants = [r['current_rule_ref'] for r in current_rules
                       if edit['edit_id'] in r['writer_edit_ids'] + r['ancestor_edit_ids']]
        active_descendant = any(edit['edit_id'] == writer or edit['edit_id'] in ancestry
                                for _, writer, ancestry in segments)
        possible = [s for m in matches for s in m]
        status, spans = 'ABSENT', []
        if any(len(m) > 1 for m in matches) or len(set(fragments)) != len(fragments):
            status = 'UNRESOLVED'
        elif all(matches):
            status, spans = 'EXACT', [m[0] for m in matches]
        else:
            # Preserve exact surviving Markdown blocks; do not guess sentence
            # boundaries or semantic equivalence inside a rewritten block.
            blocks = [b['text'] for fragment in fragments for b in _rules(fragment).values()]
            block_matches = [_occurrences(current, b) for b in blocks]
            possible.extend(s for m in block_matches for s in m)
            if any(len(m) > 1 for m in block_matches):
                status = 'UNRESOLVED'
            elif any(block_matches):
                status, spans = 'PARTIAL', [m[0] for m in block_matches if m]
            elif active_descendant:
                status = 'UNRESOLVED'
        related = [{'edit_id': other['edit_id'], 'gate_decision': gate, **link}
                   for other, gate in entries for link in other['related_history']
                   if link['prior_edit_id'] == edit['edit_id']]
        if status == 'ABSENT' and any(r['gate_decision'] == 'ACCEPT'
                and any(r['edit_id'] == writer or r['edit_id'] in ancestry
                        for _, writer, ancestry in segments) for r in related):
            # An explicit rewrite/retry may preserve meaning without exact text.
            status = 'UNRESOLVED'
        views.append({'edit_id': edit['edit_id'], 'origin_round_id': edit['round_id'],
                      'operation': edit['operation'], 'gate_decision': decision,
                      'binding_status': status,
                      'binding_subject': 'DELETED_TARGETS' if edit['operation'] == 'DELETE' else 'AFTER_TEXT',
                      'current_rule_refs': rule_refs(spans),
                      'possible_rule_refs': rule_refs(possible) if status == 'UNRESOLVED' else [],
                      'descendant_rule_refs': descendants,
                      'binding_basis': 'EXACT_LITERAL_TEXT_AND_ACCEPTED_STRUCTURAL_HISTORY',
                      'structural_changes': [e for e in changes if edit['edit_id'] in e['affected_prior_edit_ids']],
                      'related_followups': related})
    return {'schema_version': 'edit_history_view_v19.1', 'run_id': history[0].ledger.payload['run_id'],
            'initial_skill_ref': skill_ref(history[0].ledger.source['editor']['parent_skill']),
            'current_skill_ref': skill_ref(current), 'current_skill': current,
            'history_sha256': history_ref(history), 'current_rules': current_rules, 'edits': views}
