"""Replayable v20 Fusion -> local reviews -> bounded Candidate generation.

No HistoricalReviews adapters, partial compile, Memory commit or campaign resume.
Stable v18 response validation and v19 deterministic text application are reused.
"""
from dataclasses import dataclass
from pathlib import Path

from .edit_tracking_v19 import encode, parse, digest, EditLedger, DecidedEdits, reconstruct_candidate
from .memory_store_v19 import require
from .issue_memory_v20 import IssueMemorySnapshot
from .issue_fusion_v20 import IssueFusionInput, IssueFusionResult
from .review_contract_v19 import CurrentDiagnosisInput, CurrentFindings
from .evidence_review_v20 import (EvidenceArchive, EvidenceReviewResult, build_evidence_review_inputs,
    validate_evidence_review, validate_evidence_review_result, build_evidence_review_request)
from .editor_apply_v18 import _parse, _validate
from .editor_contract_v18 import build_editor_response_format
from .editor_prompt_v18 import SYSTEM_PROMPT


@dataclass(frozen=True)
class GenerationInput:
    payload_json: str

    @property
    def payload(self):
        return parse(self.payload_json)

    @property
    def input_ref(self):
        return 'GENERATION_INPUT_V20/' + digest(self.payload_json)


def build_generation_input(*, memory, fusion_input, fusion_result, parent_skill, archive,
                           current_requests=(), current_findings=(), history=()):
    p = {'schema_version': 'generation_input_v20.1',
         'memory': memory.memory if isinstance(memory, IssueMemorySnapshot) else memory,
         'memory_head': memory.head if isinstance(memory, IssueMemorySnapshot) else None,
         'fusion_input': fusion_input.payload, 'fusion_result': fusion_result.payload,
         'parent_skill': parent_skill, 'archive': archive.payload,
         'current_requests': [{'payload': r.payload, 'provenance': r.provenance} for r in current_requests],
         'current_findings': [f.payload for f in current_findings],
         'history': [{'input_json': h.ledger.input_json, 'output_json': h.ledger.output_json,
                      'gate_decision': h.gate_decision} for h in history]}
    value = GenerationInput(encode(p))
    review_inputs(value)  # Validate source binding before any model dispatch.
    return value


def review_inputs(value):
    require(isinstance(value, GenerationInput), 'v20 GenerationInput required')
    p = value.payload
    require(p['schema_version'] == 'generation_input_v20.1', 'generation protocol mismatch')
    memory = (IssueMemorySnapshot(encode(p['memory_head']), encode(p['memory']))
              if p['memory_head'] is not None else p['memory'])
    return build_evidence_review_inputs(memory=memory,
        fusion_input=IssueFusionInput(encode(p['fusion_input'])),
        fusion_result=IssueFusionResult(encode(p['fusion_result'])), parent_skill=p['parent_skill'],
        archive=EvidenceArchive(encode(p['archive'])),
        current_requests=tuple(CurrentDiagnosisInput(encode(r['payload']), encode(r['provenance'])) for r in p['current_requests']),
        current_findings=tuple(CurrentFindings(encode(f)) for f in p['current_findings']),
        history=tuple(DecidedEdits(EditLedger(h['input_json'], h['output_json']), h['gate_decision']) for h in p['history']))


@dataclass(frozen=True)
class VerifiedEditorInput:
    source: GenerationInput
    reviews_json: str
    plan_json: str

    @property
    def plan(self):
        return parse(self.plan_json)


def compile_verified(source, results):
    requests = {r.payload['proposal_id']: r for r in review_inputs(source)}
    require(all(isinstance(r, EvidenceReviewResult) for r in results), 'v20 review result required')
    by_id = {r.payload['proposal_id']: r for r in results}
    require(len(by_id) == len(results) and set(by_id) == set(requests),
            'every PROPOSE requires exactly one completed review; partial compile forbidden')
    rules = source.payload['fusion_input']['available_rule_refs']
    pending = []
    for pid in sorted(by_id):
        r = validate_evidence_review_result(by_id[pid], request=requests[pid]).payload
        if r['verdict'] == 'VERIFIED':
            pending.append({'operation': {'MISSING': 'ADD', 'NEEDS_REVISION': 'REPLACE',
                'SHOULD_REMOVE': 'DELETE'}[r['gap']['kind']],
                'target_rule_refs': r['gap']['related_rule_refs'], 'proposal_refs': [pid]})

    def overlaps(a, b):
        return any(rules[x]['start_line'] <= rules[y]['end_line'] and
                   rules[y]['start_line'] <= rules[x]['end_line']
                   for x in a['target_rule_refs'] for y in b['target_rule_refs'])

    for n, a in enumerate(pending):
        for b in pending[n + 1:]:
            require(a['operation'] == b['operation'] or not overlaps(a, b), 'MIXED_OPERATION_TARGET_CONFLICT')
    units = []
    while pending:
        unit = pending.pop(0)
        changed = True
        while changed:
            changed = False
            for other in list(pending):
                if unit['operation'] == other['operation'] and overlaps(unit, other):
                    unit['target_rule_refs'] = sorted(set(unit['target_rule_refs'] + other['target_rule_refs']))
                    unit['proposal_refs'] += other['proposal_refs']
                    pending.remove(other); changed = True
        unit['target_rule_refs'].sort(key=lambda r: (rules[r]['start_line'], rules[r]['end_line']))
        unit['proposal_refs'].sort()
        units.append(unit)
    plan = {'schema_version': 'verified_edit_plan_v20.1', 'input_ref': source.input_ref,
            'parent_skill_sha256': digest(source.payload['parent_skill']), 'edit_units': units}
    return VerifiedEditorInput(source, encode([by_id[k].payload for k in sorted(by_id)]), encode(plan))


def _restored(value):
    require(isinstance(value, VerifiedEditorInput), 'v20 VerifiedEditorInput required')
    results = tuple(EvidenceReviewResult(encode(r)) for r in parse(value.reviews_json))
    require(compile_verified(value.source, results) == value, 'verified plan changed or stale')
    return {r.payload['proposal_id']: r.payload for r in results}


def verified_editor_request(value):
    reviews = _restored(value)
    if not any(u['operation'] != 'DELETE' for u in value.plan['edit_units']):
        return None
    packets = {r.payload['proposal_id']: r.payload for r in review_inputs(value.source)}
    units = []
    for index, unit in enumerate(value.plan['edit_units']):
        if unit['operation'] == 'DELETE':
            continue
        evidence, trajectories, rules, memories, sources = {}, {}, {}, {}, {}
        for pid in unit['proposal_refs']:
            p = packets[pid]; r = reviews[pid]
            for ref in r['evidence_refs'] + r['counterevidence_refs']:
                event = p['events'][ref]
                evidence[ref] = event
                trajectories[event['trajectory_ref']] = p['trajectories'][event['trajectory_ref']]
            rules.update(p['rules'])
            memories.update({m['issue_id']: m for m in p['memory_issues']})
            sources.update(p['source_records'])
        units.append({'edit_unit_index': index, **unit,
            'target_rules': {r: rules[r] for r in unit['target_rule_refs']},
            'verified_reviews': [reviews[pid] for pid in unit['proposal_refs']],
            'memory_issues': list(memories.values()), 'source_records': sources,
            'events': evidence, 'trajectories': trajectories})
    payload = {'schema_version': 'verified_editor_request_v20.1',
        'parent_skill': value.source.payload['parent_skill'],
        'plan_sha256': digest(value.plan_json), 'edit_units': units}
    system = SYSTEM_PROMPT.replace('v18 Bounded Skill Editor', 'v20 Bounded Skill Editor')
    system += '''\nOnly verified_reviews authorize these units. Keep each review's scope, limitations
and known counterevidence. Memory summaries and source record IDs are not additional
edit authority. Original evidence is loaded only in events. Preserve all untargeted
Parent bytes. Never copy provenance IDs or historical assessments into Skill text.
'''
    return {'prompt_version': 'verified-editor-v20.1', 'system_prompt': system,
        'user_prompt': encode(payload), 'response_format': build_editor_response_format()}


def apply_verified_editor(raw, *, editor_input):
    value = editor_input
    _restored(value)
    units = value.plan['edit_units']
    parent = value.source.payload['parent_skill']
    indices = [n for n, u in enumerate(units) if u['operation'] != 'DELETE']
    if not indices:
        require(raw is None, 'NO_UPDATE or pure DELETE requires no Editor response')
        output = None
    else:
        output = _parse(raw); _validate(output, indices)
    base = {'schema_version': 'generation_result_v20.1', 'input_ref': value.source.input_ref,
            'plan_sha256': digest(value.plan_json), 'raw_response': raw}
    if not units or (output is not None and output['status'] == 'UNABLE'):
        return {**base, 'status': 'NO_UPDATE' if not units else 'UNABLE', 'candidate_skill': None, 'edits': []}
    texts = {e['edit_unit_index']: e['text'] for e in output['edits']} if output else {}
    fusion = value.source.payload['fusion_input']
    rules = fusion['available_rule_refs']
    issues = {i['proposal_issue_id']: i for i in value.source.payload['fusion_result']['issues']}
    edits = []
    for index, unit in enumerate(units):
        block = texts.get(index, '')
        if block and not block.endswith('\n'):
            block += '\n'
        involved = [issues[pid] for pid in unit['proposal_refs']]
        edits.append({'edit_id': 'EDIT_V20/' + digest(encode({'input_ref': value.source.input_ref,
            'plan_sha256': digest(value.plan_json), 'index': index, 'after_text': block})),
            'operation': unit['operation'], 'target_blocks': [rules[r] for r in unit['target_rule_refs']],
            'after_text': block, 'proposal_refs': unit['proposal_refs'],
            'memory_issue_refs': sorted({r for i in involved for r in i['memory_issue_refs']}),
            'memory_attempt_refs': sorted({r for i in involved for r in i['memory_attempt_refs']}),
            'current_finding_refs': sorted({r for i in involved for r in i['current_finding_refs']})})
    # Same audited splice rules as v19: exact target text, disjoint spans and
    # verbatim copying of every unedited part. Pure DELETE never calls a model.
    candidate = reconstruct_candidate(parent, edits)
    return {**base, 'status': 'EDITED' if indices else 'APPLIED_DETERMINISTIC',
            'candidate_skill': candidate, 'candidate_sha256': digest(candidate), 'edits': edits}


def restore_generation(audit):
    require(audit['schema_version'] == 'generation_audit_v20.1', 'generation audit protocol mismatch')
    source = GenerationInput(encode(audit['source']))
    value = compile_verified(source, tuple(EvidenceReviewResult(encode(r)) for r in audit['reviews']))
    require(value.plan == audit['plan'], 'saved plan changed')
    result = apply_verified_editor(audit['result']['raw_response'], editor_input=value)
    require(result == audit['result'], 'saved Candidate changed')
    return value, result


def run_local_generation(*, source, output, review_transport=None, editor_transport=None, model='deepseek-v4-pro'):
    """Execute Step 4, saving source, calls and final audit. No silent retries.

    Existing output is refused; campaign run/resume and commit belong to Step 5.
    Failure leaves originals/calls for diagnosis and never publishes a Candidate.
    """
    from .attribution_v19 import _transport
    from .evolution_replay_v19 import _save
    path = Path(output)
    requests = review_inputs(source)
    path.mkdir(parents=True, exist_ok=False)
    _save(path / 'source.json', source.payload)

    def call(stage, request, transport):
        request = {**request, 'model': model, 'temperature': 0.0, 'reasoning_effort': 'high',
                   'max_completion_tokens': 24000, 'timeout_seconds': 600}
        _save(path / (stage + '-request.json'), request)
        response = (transport or _transport)(request)
        _save(path / (stage + '-response.json'), response)
        require(type(response) is dict and response.get('finish_reason') == 'stop' and not response.get('refusal'),
                'refused or incomplete completion; generation stopped')
        return response.get('raw_response')

    try:
        results = []
        for index, request in enumerate(requests):
            _save(path / f'review-{index}-input.json', request.payload)
            raw = call(f'review-{index}', build_evidence_review_request(request), review_transport)
            result = validate_evidence_review(raw, request=request)
            results.append(result)
            _save(path / f'review-{index}-result.json', result.payload)
        value = compile_verified(source, tuple(results))
        _save(path / 'edit-plan.json', value.plan)
        prompt = verified_editor_request(value)
        raw = call('editor', prompt, editor_transport) if prompt else None
        result = apply_verified_editor(raw, editor_input=value)
        audit = {'schema_version': 'generation_audit_v20.1', 'source': source.payload,
                 'reviews': [r.payload for r in results], 'plan': value.plan, 'result': result}
        restore_generation(audit)
        _save(path / 'generation-audit.json', audit)
        _save(path / 'status.json', {'status': result['status']})
        return audit
    except Exception as exc:
        _save(path / 'status.json', {'status': 'INCOMPLETE', 'error_type': type(exc).__name__, 'message': str(exc)})
        raise
