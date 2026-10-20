"""One typed-reference boundary; definitions and archived local IDs stay unchanged.

Only declared reference fields are transformed. Evidence aliases, prose, Effect IDs,
Finding IDs, historical namespaces and P1 tables are never guessed or rewritten.
"""
from copy import deepcopy

PROFILE = 'v22.unified_dsc.v6'
VERSION = 'v22.typed_references.v1'
LOCAL_TYPES = ('requirement', 'watch')


def enabled(payload):
    return payload.get('update_profile') == PROFILE


def ref(kind, identifier):
    if kind not in LOCAL_TYPES:
        raise ValueError('Unsupported local reference type')
    return kind + ':' + identifier


def objects(plan, memory=()):
    result = {'intent': ('intent', 'intent')}
    for kind, field in [('requirement', 'requirements'), ('watch', 'watch')]:
        for row in plan.get(field, []):
            result[ref(kind, row['id'])] = (kind, row['id'])
    for row in memory:
        if row['id'] in result:
            raise ValueError('Effect identity collides with a current object reference')
        result[row['id']] = ('effect', row['id'])
    return result


def learning_objects(payload):
    return objects(payload['plan'], payload.get('memory', []))


def watch_ref(payload, identifier):
    return ref('watch', identifier) if enabled(payload) else identifier


def _links(values, catalog, outbound, kinds):
    if not isinstance(values, list):
        raise ValueError('References must be an array')
    allowed = {key: identifier for key, (kind, identifier) in catalog.items() if kind in kinds}
    if outbound:
        reverse = {}
        for key, identifier in allowed.items():
            if identifier in reverse:
                raise ValueError('Ambiguous internal local reference')
            reverse[identifier] = key
        allowed = reverse
    if any(not isinstance(v, str) or v not in allowed for v in values):
        raise ValueError('Unknown or noncanonical object reference')
    return [allowed[v] for v in values]


def _about(rows, catalog, outbound, kinds):
    for row in rows:
        row['about'] = _links(row['about'], catalog, outbound, kinds)


def plan_view(plan):
    result = deepcopy(plan)
    catalog = objects(plan)
    _about(result['watch'], catalog, True, {'intent', 'requirement'})
    _about(result.get('open', []), catalog, True, {'intent', 'requirement', 'watch'})
    return result


def convert(stage, value, payload, *, outbound=False):
    """Strict typed wire -> old internal compiler representation (or test/view inverse).

    This does not broaden any field's allowed source set. The existing compiler
    validates existence, replacements, scope, coverage and text mapping afterwards.
    """
    result = deepcopy(value)
    if stage == 'diagnosis':
        plan = result.get('plan')
        if plan is not None:
            catalog = objects(plan)
            _about(plan['watch'], catalog, outbound, {'intent', 'requirement'})
            _about(plan['open'], catalog, outbound, {'intent', 'requirement', 'watch'})
    elif stage == 'fusion':
        plan = payload['plan']; catalog = objects(plan)
        target = deepcopy(plan)
        for change in result['changes']:
            change['from'] = _links(change['from'], catalog, outbound, {'requirement'})
            # Effective-object catalog includes newly defined replacement IDs.
            target['requirements'].extend(change['to'])
        for change in result['watch_changes']:
            change['from'] = _links(change['from'], catalog, outbound, {'watch'})
            target['watch'].extend(change['to'])
        target_catalog = objects(target)
        for change in result['watch_changes']:
            _about(change['to'], target_catalog, outbound, {'intent', 'requirement'})
        _about(result['open'], target_catalog, outbound, {'intent', 'requirement', 'watch'})
    elif stage == 'editor':
        catalog = objects(payload['plan'])
        for mapping in result['mappings']:
            mapping['requirements'] = _links(mapping['requirements'], catalog, outbound, {'requirement'})
        _about(result['issues'], catalog, outbound, {'intent', 'requirement', 'watch'})
        _about(result.get('watch', []), catalog, outbound, {'intent', 'requirement'})
    else:
        raise ValueError('Unknown object-reference boundary')
    return result


def input_view(view, stage):
    result = deepcopy(view)
    result['reference_contract'] = {'version': VERSION, 'local_types': list(LOCAL_TYPES)}
    if 'plan' in result:
        result['plan'] = plan_view(result['plan'])
    if stage == 'learn':
        result['reference_contract']['about_objects'] = {
            key: kind for key, (kind, _) in learning_objects(view).items()}
    # update_context.editor is stored with typed refs by the new learning builder;
    # archived legacy snapshots are migrated explicitly at the import boundary.
    return result


def instructions(stage):
    common = ('\nReference contract: object definitions keep local IDs; references use '
              'requirement:<id> or watch:<id>. Intent is intent; Effect IDs and evidence '
              'source keys remain exactly as supplied. basis/refs retain their supplied evidence scope.\n')
    if stage == 'learn':
        common += ('about evaluates only reference_contract.about_objects; refs supports the '
                   'finding using current sources. A group/event source is evidence, not an about object.\n')
    return common


def shape(stage, original):
    result = deepcopy(original)
    if stage == 'learn':
        result['findings'][0]['about'] = ['key from reference_contract.about_objects']
        result['open'][0]['about'] = ['key from reference_contract.about_objects']
        return result
    if stage == 'diagnosis':
        return convert(stage, result, {}, outbound=True)
    sample = {'plan': {'requirements': [{'id': 'u1'}], 'watch': [{'id': 'w1'}]}}
    return convert(stage, result, sample, outbound=True)
