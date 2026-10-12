"""Learner-local evidence aliases: deliberately no canonical-policy lookup map."""
import copy


def build_provenance_alias_context(rollouts):
    presented = copy.deepcopy(rollouts)
    evidence, supervision = {}, {}
    for r in presented:
        for step in r['trajectory']:
            alias = f'E{len(evidence)+1:03d}'
            evidence[alias] = {'source_id': r['source_id'], 'step_id': step['step']}
            step['evidence_ref'] = alias
        alias = f'S{len(supervision)+1:03d}'
        supervision[alias] = {'source_id': r['source_id'], 'level': r['supervision']['level']}
        r['supervision']['supervision_ref'] = alias
    return {'rollouts': presented, 'evidence_aliases': evidence, 'supervision_aliases': supervision}


def resolve_semantic_provenance(semantic, alias_context):
    mechanism = semantic['behavioral_mechanism']
    result = {}
    for field in ('support_evidence_refs', 'counterevidence_refs'):
        result[field] = [dict(alias=key, **alias_context['evidence_aliases'][key]) for key in mechanism[field]]
    result['supervision_refs'] = [dict(alias=key, **alias_context['supervision_aliases'][key]) for key in semantic['supervision_refs']]
    return result
