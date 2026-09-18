"""Assemble group-local, learner-safe Diagnosis inputs; no Diagnosis/model call."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass

from .experience_cards_v17 import CapturedGroupingExperience, build_experience_cards
from .experience_grouping_contract_v17 import (
    GroupingContractError, GroupingScope, bind_grouping_result,
)
from .experience_grouping_v17 import prepare_grouping_request
from .information_boundary_v15 import Envelope, _seal, unpack
from .diagnosis_references_v17 import build_reference_catalogs


@dataclass(frozen=True)
class GroupDiagnosisInput:
    """Only learner_payload is intended for a future Diagnosis model."""

    learner_view: Envelope
    provenance_json: str

    @property
    def learner_payload(self) -> dict:
        return unpack(self.learner_view, 'V17_GROUP_DIAGNOSIS_INPUT')

    @property
    def provenance(self) -> dict:
        return json.loads(self.provenance_json)


def build_group_diagnosis_inputs(
    sources: tuple[CapturedGroupingExperience, ...], *, scope: GroupingScope,
    grouping_result: dict, parent_skill: str,
) -> tuple[GroupDiagnosisInput, ...]:
    """Revalidate partition/bindings, then join only each group's full experiences.

    Parent digest is SHA-256 over the exact UTF-8 Skill text, without normalization.
    Group explanations are model hypotheses. They never become evidence entries.
    The trusted caller remains responsible for truthful task/round source binding.
    """
    if not isinstance(parent_skill, str):
        raise GroupingContractError('Parent Skill must be text')
    if hashlib.sha256(parent_skill.encode('utf-8')).hexdigest() != scope.parent_skill_digest:
        raise GroupingContractError('Parent Skill content digest mismatch')
    batch = build_experience_cards(sources, scope=scope)
    fields = {'schema_version', 'round_id', 'parent_skill_digest', 'origin',
              'experience_refs', 'groups'}
    if not isinstance(grouping_result, dict) or set(grouping_result) not in (fields, fields | {'alias_to_source'}):
        raise GroupingContractError('invalid bound grouping result fields')
    expected = bind_grouping_result(batch.payload, {'groups': grouping_result['groups']}, scope=scope)
    if any(grouping_result[key] != expected[key] for key in fields):
        raise GroupingContractError('grouping round/Parent/experience binding mismatch')

    # Preserve the namespace used in Grouper prose. Never copy the global map into
    # a group request: that would expose out-of-group identifiers and context.
    if 'alias_to_source' in grouping_result:
        maps = prepare_grouping_request(batch, scope=scope)['alias_to_source']
        if grouping_result['alias_to_source'] != maps:
            raise GroupingContractError('grouping alias map mismatch')
    else:
        # Step 1 bind_grouping_result has no anonymization; its prose uses local refs.
        maps = {field: {getattr(ref, field): getattr(ref, field) for ref in scope.experiences}
                for field in ('task_ref', 'context_ref', 'trajectory_ref')}
    forward = {field: {source: alias for alias, source in mapping.items()}
               for field, mapping in maps.items()}
    by_task = {source.ref.task_ref: source for source in sources}
    cards = {card['task_ref']: card for card in batch.payload['cards']}
    contexts = {context['context_ref']: context for context in batch.payload['contexts']}
    requests = []
    for group in expected['groups']:
        hints = copy.deepcopy(group)
        hints['members'] = [forward['task_ref'][task] for task in group['members']]
        hints['origin'] = 'LEARNER_INFERRED_GROUPING'
        experiences, local_contexts, evidence, supervision, lineage = [], {}, {}, {}, []
        for task in group['members']:
            source = by_task[task]
            observed = unpack(source.experience, 'TRAJECTORY_DERIVED')
            labels = observed['supervision']
            if (not isinstance(labels, dict)
                    or set(labels) != {'success', 'compliant', 'level', 'provenance'}
                    or type(labels['success']) is not bool or type(labels['compliant']) is not bool
                    or type(labels['level']) is not int or labels['level'] != 0
                    or labels['provenance'] != 'LEARNER_SAFE_SUPERVISION'):
                raise GroupingContractError('only Level-0 boolean supervision is allowed')
            rollout_index = observed['rollout_index']
            if type(rollout_index) is not int or rollout_index < 1:
                raise GroupingContractError('invalid captured rollout index')
            card = copy.deepcopy(cards[task])
            for field in forward:
                card[field] = forward[field][card[field]]
            context = copy.deepcopy(contexts[source.ref.context_ref])
            context['context_ref'] = card['context_ref']
            local_contexts[card['context_ref']] = context
            identity = {'task_ref': card['task_ref'], 'trajectory_ref': card['trajectory_ref'],
                        'rollout_index': rollout_index}
            namespace = f"{card['task_ref']}/{card['trajectory_ref']}/R{rollout_index}"
            for event in card['events']:
                alias = f"{namespace}/E{event['step']:04d}"
                event['evidence_ref'] = alias
                evidence[alias] = {**identity, 'step': event['step']}
            supervision_ref = namespace + '/S'
            supervision[supervision_ref] = {**identity, 'level': 0}
            card['rollout_index'] = rollout_index
            card['supervision'] = {**labels, 'supervision_ref': supervision_ref}
            experiences.append(card)
            lineage.append({'source': vars(source.ref), 'presented': {
                field: card[field] for field in forward}, 'rollout_index': rollout_index})
        payload = {
            'schema_version': 'group_diagnosis_input_v17.2',
            'grouping_hint': hints,
            'grouping_hint_authority': 'ANALYSIS_HINT_ONLY_NOT_EVIDENCE_OR_POLICY',
            'current_skill': parent_skill,
            'contexts': list(local_contexts.values()), 'experiences': experiences,
            'available_evidence_refs': evidence, 'available_supervision_refs': supervision,
        }
        payload.update(build_reference_catalogs(payload))
        provenance = {'round_id': scope.round_id, 'parent_skill_digest': scope.parent_skill_digest,
                      'group_id': group['group_id'], 'experience_bindings': lineage}
        requests.append(GroupDiagnosisInput(
            _seal('V17_GROUP_DIAGNOSIS_INPUT', payload),
            json.dumps(provenance, ensure_ascii=False, sort_keys=True, allow_nan=False),
        ))
    return tuple(requests)
