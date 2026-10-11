"""Verified local reviews -> deterministic v18 operation rules -> bounded editing.

The v18 Diagnosis interface is deliberately not impersonated. Its deterministic
planning/application rules are ported here, with original proposal provenance.
Frozen v18 sources stay unchanged; strict output parsing/schema are reused.
"""
from dataclasses import dataclass, asdict
from types import SimpleNamespace
import json

from .edit_tracking_v19 import encode,parse,digest
from .memory_store_v19 import require
from .compiler_contract_v18 import EditPlan,EditUnit,GapRef
from .compiler_validation_v18 import plan_payload
from .editor_contract_v18 import EditorRequest,EditorUnitPackage,EditorRejected,build_editor_response_format
from .editor_apply_v18 import _parse,_validate
from .editor_prompt_v18 import SYSTEM_PROMPT
from .evidence_review_v19 import validate_evidence_review_result

PROTOCOL='local_generation_v19.1'

@dataclass(frozen=True)
class VerifiedEditorInput:
    audit_json:str
    plan:EditPlan
    @property
    def compiler_input(self):
        p=parse(self.audit_json)['review_input']
        return SimpleNamespace(round_id=p['batch']['round_id'],parent_skill=p['current_skill'],
                               parent_skill_digest=digest(p['current_skill']),diagnoses=())


def compile_verified(audit, reviews):
    """reviews are fully restored (request, result) pairs, including NO_EDIT.

    Called only after complete Fusion coverage and local input reconstruction.
    Same-target same-operation gaps merge; opposite operations fail closed.
    ADDs stay separate: no semantic deduplication by program.
    """
    parent=audit['review_input']['current_skill'];round_id=audit['review_input']['batch']['round_id']
    rules={};refs=[];adds=[];targeted={'REPLACE':[],'DELETE':[]}
    operations={'MISSING':'ADD','NEEDS_REVISION':'REPLACE','SHOULD_REMOVE':'DELETE'}
    for request,result in sorted(reviews,key=lambda pair:pair[1].payload['proposal_id']):
        validate_evidence_review_result(result,request=request)
        require(request.payload['parent_skill_sha256']==digest(parent),'verified Parent mismatch')
        rules.update(request.payload['rules'])
        r=result.payload
        if r['verdict']!='VERIFIED':continue
        ref=r['proposal_id'];refs.append(ref);gap=r['gap'];support=GapRef(ref,0)
        op=operations[gap['kind']]
        if op=='ADD':adds.append(EditUnit(op,(),(support,)))
        else:targeted[op].append((set(gap['related_rule_refs']),[support]))

    def _gap_key(ref):return ref.diagnosis_ref,ref.gap_index
    def overlaps(a, b):
        return any(rules[x]['start_line'] <= rules[y]['end_line'] and
                   rules[y]['start_line'] <= rules[x]['end_line'] for x in a for y in b)

    # Operation conflicts are structural. Never choose a semantic winner or
    # silently convert removal to replacement, even if the prose seems compatible.
    for replace_targets, _ in targeted['REPLACE']:
        for delete_targets, _ in targeted['DELETE']:
            require(not overlaps(replace_targets, delete_targets), 'MIXED_OPERATION_TARGET_CONFLICT')

    # Merge connected components only within the same operation; retain every gap.
    components = []
    for operation, pending in targeted.items():
        while pending:
            targets, supports = pending.pop(0)
            changed = True
            while changed:
                changed = False
                remaining = []
                for other_targets, other_supports in pending:
                    if overlaps(targets, other_targets):
                        targets.update(other_targets)
                        supports.extend(other_supports)
                        changed = True
                    else:
                        remaining.append((other_targets, other_supports))
                pending = remaining
            ordered = tuple(sorted(targets, key=lambda r: (rules[r]['start_line'], rules[r]['end_line'], r)))
            components.append(EditUnit(operation, ordered, tuple(sorted(supports, key=_gap_key))))
    components.sort(key=lambda unit: (rules[unit.target_rule_refs[0]]['start_line'],
                                      unit.operation,
                                      tuple(_gap_key(r) for r in unit.supporting_gap_refs)))
    adds.sort(key=lambda unit: _gap_key(unit.supporting_gap_refs[0]))
    plan=EditPlan('verified_edit_plan_v19.1',round_id,digest(parent),tuple(sorted(refs)),tuple(components+adds),())
    return VerifiedEditorInput(encode(audit),plan)


def restored(value):
    from .local_generation_v19 import restore_local_audit
    rebuilt,reviews=restore_local_audit(value.audit_json)
    require(rebuilt==value,'verified plan differs from restored sources')
    return reviews


def build_verified_editor_input(value):
    reviews={result.payload['proposal_id']:(request.payload,result.payload) for request,result in restored(value)}
    units=[]
    for index,unit in enumerate(value.plan.edit_units):
        gaps=[];judgments=[];evidence={};rules={}
        for support in unit.supporting_gap_refs:
            request,result=reviews[support.diagnosis_ref]
            gaps.append({'gap_ref':asdict(support),'gap':result['gap']})
            judgments.append({'proposal_id':result['proposal_id'],'reason':result['reason'],
                'evidence_refs':result['evidence_refs'],'counterevidence_refs':result['counterevidence_refs']})
            for ref in result['evidence_refs']+result['counterevidence_refs']:
                event=request['events'][ref]
                record={'ref':ref,**event,'trajectory':request['trajectories'][event['trajectory_ref']]}
                require(ref not in evidence or evidence[ref]['event']==record['event'],'conflicting original events')
                evidence[ref]=record
            rules.update(request['rules'])
        targets=[{'ref':r,**rules[r]} for r in unit.target_rule_refs]
        units.append(EditorUnitPackage(index,unit.operation,encode(targets),encode(gaps),encode(judgments),encode(evidence)))
    return EditorRequest('verified_editor_request_v19.1',value.compiler_input.parent_skill,
        value.compiler_input.parent_skill_digest,digest(encode(plan_payload(value.plan))),tuple(units))


def verified_editor_request(value):
    packed=build_verified_editor_input(value)
    if not any(u.operation!='DELETE' for u in packed.edit_units):return None
    payload={'schema_version':packed.schema_version,'parent_skill':packed.parent_skill,
        'parent_skill_digest':packed.parent_skill_digest,'plan_sha256':packed.plan_sha256,
        'edit_units':[{'edit_unit_index':u.edit_unit_index,'operation':u.operation,
            'target_rules':parse(u.target_rules_json),'backing_gaps':parse(u.backing_gaps_json),
            'verified_reviews':parse(u.analyses_json),'evidence_catalog':parse(u.evidence_json)}
            for u in packed.edit_units if u.operation!='DELETE']}
    system=SYSTEM_PROMPT.replace('v18 Bounded Skill Editor','v19 Bounded Skill Editor').replace('analyses','verified reviews').replace('analysis','review').replace('Diagnosis','Evidence Review')
    if parse(value.audit_json).get('editor_policy')=='flat_task_rules_v19.1':
        from .editor_policy_v19 import INSTRUCTIONS
        system+=INSTRUCTIONS
    system=system.replace('No automatic output repair occurs.', 'One model-authored contract repair is allowed after local rejection.')
    user=encode(payload)
    return {'prompt_version':'verified-bounded-editor-v19.2','prompt_sha256':digest(system),
        'parent_skill_digest':packed.parent_skill_digest,'plan_sha256':packed.plan_sha256,
        'input_sha256':digest(user),'system_prompt':system,'user_prompt':user,
        'response_format':build_editor_response_format()}


def apply_verified_editor(raw, *, editor_input) -> dict:
    """Revalidate runtime input on every call; return no candidate on UNABLE/NOOP.

    No externally supplied offsets or mutable validated-output DTO are trusted.
    The program copies every untargeted original slice verbatim. Semantic fidelity
    of new text is not established by this boundary check.
    """
    request = build_verified_editor_input(editor_input)
    if not request.edit_units:
        if raw is not None:
            raise EditorRejected('COVERAGE', 'all-NOOP requires no model response')
        return {'status': 'NO_UPDATE', 'candidate_skill': None}
    text_indices = [u.edit_unit_index for u in request.edit_units if u.operation != 'DELETE']
    if text_indices:
        output = _parse(raw)
        _validate(output, text_indices)
    else:
        if raw is not None:
            raise EditorRejected('COVERAGE', 'pure DELETE requires no model response')
        output = None
    base = {'parent_skill_digest': request.parent_skill_digest,
            'plan_sha256': request.plan_sha256,
            'raw_response': raw, 'output': output}
    if output is not None and output['status'] == 'UNABLE':
        return {**base, 'status': 'UNABLE', 'candidate_skill': None}
    parent = request.parent_skill
    lines = parent.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    spans, additions, deletions = [], [], []
    texts = {e['edit_unit_index']: e['text'] for e in output['edits']} if output is not None else {}
    for unit in request.edit_units:
        if unit.operation == 'DELETE':
            block = ''
            deletions.append({
                'edit_unit_index': unit.edit_unit_index,
                'target_rules': json.loads(unit.target_rules_json),
                'backing_gaps': json.loads(unit.backing_gaps_json),
            })
        else:
            text = texts[unit.edit_unit_index]
            audit=parse(editor_input.audit_json)
            if audit.get('editor_policy')=='flat_task_rules_v19.1':
                from .editor_policy_v19 import validate_text,internal_ids
                validate_text(text,internal_ids(audit))
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
    from .candidate_layout_v19 import apply_layout
    before_layout=candidate
    candidate = apply_layout(candidate, parse(editor_input.audit_json).get('candidate_layout'))
    return {**base, 'status': 'EDITED' if text_indices else 'APPLIED_DETERMINISTIC',
            'candidate_skill': candidate, **({'layout_change':{'source_sha256':digest(before_layout),
                'candidate_sha256':digest(candidate),'policy':parse(editor_input.audit_json)['candidate_layout']}}
                if before_layout!=candidate else {}), 'model_edit_unit_indices': text_indices,
            'deterministic_deletions': deletions,
            'candidate_sha256': digest(candidate)}
