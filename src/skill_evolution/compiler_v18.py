"""Pure deterministic compilation; no model, filesystem writes or semantic repair."""
from __future__ import annotations

import hashlib
import json

from .compiler_contract_v18 import (
    CompilerInput, CompilerDiagnosisSource, CompilerRejected, EditPlan, EditUnit,
    GapRef, NoopRecord,
)
from .group_diagnosis_input_v17 import GroupDiagnosisInput
from .information_boundary_v15 import BoundaryError, unpack
from .diagnosis_validation_v18 import DiagnosisRejected, validate_diagnosis_response


def _require(condition, stage, reason):
    if not condition:
        raise CompilerRejected(stage, reason)


def _gap_key(ref):
    return ref.diagnosis_ref, ref.gap_index


def compile_edit_plan(value: CompilerInput) -> EditPlan:
    """Validate all sources before building a plan; reject the whole batch on error.

    Provenance is runtime-owned, as in GroupDiagnosisInput. This checks consistency,
    not independent authentication of a malicious caller's round/group metadata.
    """
    _require(isinstance(value, CompilerInput), 'INPUT', 'CompilerInput required')
    _require(isinstance(value.round_id, str) and bool(value.round_id.strip()), 'INPUT', 'round_id required')
    _require(isinstance(value.parent_skill, str), 'INPUT', 'Parent must be text')
    _require(isinstance(value.diagnoses, tuple) and bool(value.diagnoses), 'INPUT', 'nonempty source tuple required')
    digest = hashlib.sha256(value.parent_skill.encode('utf-8')).hexdigest()
    _require(value.parent_skill_digest == digest, 'BINDING', 'Parent digest mismatch')
    bound, groups, refs = [], set(), set()
    for source in value.diagnoses:
        _require(isinstance(source, CompilerDiagnosisSource), 'INPUT', 'invalid source type')
        _require(isinstance(source.request, GroupDiagnosisInput), 'INPUT', 'original group input required')
        try:
            saved = unpack(source.validated, 'V18_VALIDATED_DIAGNOSIS')
            payload = source.request.learner_payload
        except (BoundaryError, ValueError, TypeError) as exc:
            raise CompilerRejected('INPUT', 'untrusted source or request') from exc
        expected_ref = 'DIAGNOSIS/' + hashlib.sha256(source.validated.payload.encode('utf-8')).hexdigest()
        _require(source.diagnosis_ref == expected_ref, 'BINDING', 'Diagnosis reference digest mismatch')
        try:
            provenance = source.request.provenance
        except (ValueError, TypeError) as exc:
            raise CompilerRejected('INPUT', 'invalid provenance') from exc
        _require(isinstance(provenance, dict), 'INPUT', 'provenance object required')
        group = provenance.get('group_id')
        _require(isinstance(group, str) and bool(group.strip()), 'INPUT', 'group_id required')
        _require(group not in groups and source.diagnosis_ref not in refs, 'INPUT', 'duplicate group/source')
        groups.add(group)
        refs.add(source.diagnosis_ref)
        _require(provenance.get('round_id') == value.round_id, 'BINDING', 'round mismatch')
        _require(provenance.get('parent_skill_digest') == digest and
                 isinstance(payload, dict) and payload.get('current_skill') == value.parent_skill,
                 'BINDING', 'source Parent mismatch')
        _require(isinstance(saved, dict) and isinstance(saved.get('raw_response'), str),
                 'INPUT', 'validated response payload required')
        try:
            rebuilt = unpack(validate_diagnosis_response(saved['raw_response'], request=source.request),
                             'V18_VALIDATED_DIAGNOSIS')
        except (DiagnosisRejected, BoundaryError, KeyError, TypeError, ValueError) as exc:
            raise CompilerRejected('BINDING', 'Diagnosis does not validate against original input') from exc
        _require(rebuilt == saved, 'BINDING', 'validated contents or input binding mismatch')
        bound.append((source.diagnosis_ref, saved['semantic'], payload['available_rule_refs']))

    adds, noops = [], []
    targeted = {'REPLACE': [], 'DELETE': []}
    operation_for_kind = {'MISSING': 'ADD', 'NEEDS_REVISION': 'REPLACE', 'SHOULD_REMOVE': 'DELETE'}
    rules = {}
    for ref, semantic, catalog in sorted(bound, key=lambda entry: entry[0]):
        rules.update(catalog)  # Rebuilt catalogs all address the same exact Parent.
        state = semantic['skill_addressability']
        if state['status'] != 'ADDRESSABLE':
            noops.append(NoopRecord('NOOP', ref, state['status'], state['reason']))
            continue
        for index, gap in enumerate(semantic['parent_skill_gaps']):
            support = GapRef(ref, index)
            operation = operation_for_kind[gap['kind']]
            if operation == 'ADD':
                adds.append(EditUnit('ADD', (), (support,)))
            else:
                targeted[operation].append((set(gap['related_rule_refs']), [support]))

    def overlaps(a, b):
        return any(rules[x]['start_line'] <= rules[y]['end_line'] and
                   rules[y]['start_line'] <= rules[x]['end_line'] for x in a for y in b)

    # Operation conflicts are structural. Never choose a semantic winner or
    # silently convert removal to replacement, even if the prose seems compatible.
    for replace_targets, _ in targeted['REPLACE']:
        for delete_targets, _ in targeted['DELETE']:
            _require(not overlaps(replace_targets, delete_targets), 'PLAN',
                     'MIXED_OPERATION_TARGET_CONFLICT')

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
    return EditPlan('compiler_edit_plan_v18.1', value.round_id, digest, tuple(sorted(refs)),
                    tuple(components + adds), tuple(noops))
