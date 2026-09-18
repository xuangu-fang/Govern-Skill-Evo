"""Deterministic public-policy and Parent-rule citations, never oracle lookups."""
from __future__ import annotations

import copy
import hashlib
import re

from .diagnosis_contract_v17 import DiagnosisContractError, validate_diagnosis_output


def _digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def build_reference_catalogs(payload: dict) -> dict:
    """Index exact policy lines and Markdown rule blocks, scoped by full digest.

    Rule blocks start at bullets/numbered items or standalone prose, continue over
    adjacent nonheading lines, and end at blank lines/headings/next item. This is
    syntactic addressing, not semantic parsing. Empty headings are not rules.
    """
    policies, rules = {}, {}
    for context in payload['contexts']:
        text = context['visible_policy']
        digest = _digest(text)
        for number, line in enumerate(text.splitlines(keepends=True), 1):
            if line.strip():
                ref = f"POLICY/{context['context_ref']}/{digest}/L{number}"
                policies[ref] = {'reference_type': 'VISIBLE_POLICY',
                                 'context_ref': context['context_ref'], 'policy_digest': digest,
                                 'line': number, 'text': line}
    parent = payload['current_skill']
    digest = _digest(parent)
    lines = parent.splitlines(keepends=True)
    start, section = None, ''

    def flush(end):
        nonlocal start
        if start is not None:
            ref = f'RULE/{digest}/L{start+1}-{end}'
            rules[ref] = {'reference_type': 'PARENT_SKILL_RULE', 'parent_skill_digest': digest,
                          'section': section, 'start_line': start + 1, 'end_line': end,
                          'text': ''.join(lines[start:end])}
            start = None

    for i, line in enumerate(lines):
        heading = re.match(r'^#{1,6}\s+(.+)', line)
        item = re.match(r'^\s*(?:[-+*]|\d+[.)])\s+', line)
        if heading or not line.strip() or item:
            flush(i)
        if heading:
            section = heading.group(1).strip()
        elif line.strip() and start is None:
            start = i
    flush(len(lines))
    return {'available_policy_refs': policies, 'available_rule_refs': rules}


def _payload(request):
    from .group_diagnosis_input_v17 import GroupDiagnosisInput
    if not isinstance(request, GroupDiagnosisInput):
        raise DiagnosisContractError('signed GroupDiagnosisInput required')
    payload = request.learner_payload
    expected = build_reference_catalogs(payload)
    for key, catalog in expected.items():
        if payload.get(key) != catalog:
            raise DiagnosisContractError('missing or stale reference catalog: ' + key)
    return payload


def resolve_reference(request, ref: str, *, reference_type: str,
                      context_ref: str | None = None, quote: str | None = None) -> dict:
    """Resolve a typed citation and optionally verify exact quote and context.

    Quote matching is literal (no whitespace normalization). It verifies location,
    not whether that text entails a natural-language claim.
    """
    payload = _payload(request)
    catalogs = {'TRAJECTORY': 'available_evidence_refs',
                'SUPERVISION': 'available_supervision_refs',
                'VISIBLE_POLICY': 'available_policy_refs',
                'PARENT_SKILL_RULE': 'available_rule_refs'}
    if reference_type not in catalogs or not isinstance(ref, str):
        raise DiagnosisContractError('unknown reference type or invalid reference')
    catalog = payload[catalogs[reference_type]]
    if ref not in catalog:
        raise DiagnosisContractError('unknown, wrong-type, out-of-group or stale reference: ' + ref)
    resolved = copy.deepcopy(catalog[ref])
    if reference_type in ('TRAJECTORY', 'SUPERVISION'):
        experience = next(e for e in payload['experiences']
                          if (e['task_ref'], e['trajectory_ref'], e['rollout_index']) ==
                          (resolved['task_ref'], resolved['trajectory_ref'], resolved['rollout_index']))
        resolved['context_ref'] = experience['context_ref']
        if reference_type == 'TRAJECTORY':
            resolved['event'] = next(e for e in experience['events'] if e['evidence_ref'] == ref)
        else:
            resolved['supervision'] = experience['supervision']
    if context_ref is not None and resolved.get('context_ref') != context_ref:
        raise DiagnosisContractError('citation context mismatch')
    if quote is not None:
        if (reference_type not in ('VISIBLE_POLICY', 'PARENT_SKILL_RULE')
                or not isinstance(quote, str) or not quote.strip() or quote not in resolved['text']):
            raise DiagnosisContractError('quote is not an exact source excerpt')
    return {'reference_type': reference_type, 'ref': ref, **resolved}


def resolve_diagnosis_references(output: dict, *, request) -> dict:
    """Validate structure and resolve all explicit citation fields; no semantic judge.

    Analysis evidence_refs may cite observed events or visible policy. Each gap
    still needs at least one observed event, so policy alone cannot justify a gap.
    """
    validate_diagnosis_output(output)
    payload = _payload(request)

    def evidence(ref):
        kind = 'VISIBLE_POLICY' if ref in payload['available_policy_refs'] else 'TRAJECTORY'
        return resolve_reference(request, ref, reference_type=kind)

    result = {}
    for dimension in ('success_analysis', 'compliance_analysis'):
        analysis = output[dimension]
        result[dimension] = {
            'evidence_refs': [evidence(ref) for ref in analysis['evidence_refs']],
            'supervision_refs': [resolve_reference(request, ref, reference_type='SUPERVISION')
                                 for ref in analysis['supervision_refs']],
        }
    result['parent_skill_gaps'] = []
    for gap in output['parent_skill_gaps']:
        refs = [evidence(ref) for ref in gap['evidence_refs']]
        if not any(ref['reference_type'] == 'TRAJECTORY' for ref in refs):
            raise DiagnosisContractError('gap requires observed trajectory evidence')
        result['parent_skill_gaps'].append({
            'evidence_refs': refs,
            'related_rule_refs': [resolve_reference(request, ref, reference_type='PARENT_SKILL_RULE')
                                  for ref in gap['related_rule_refs']],
        })
    return result
