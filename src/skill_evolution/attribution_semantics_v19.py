"""Facts-only projections. Association and pair outcomes are not edit effects."""
from copy import deepcopy


def record_facts(record, batch):
    value = deepcopy(record)
    value.pop('effect', None)
    value['schema_version'] = 'attribution_record_v19.3'
    value['associated_pair_outcome_counts'] = value.pop('outcome_counts', value.get('associated_pair_outcome_counts', {}))
    pair_ids = set(value.get('associated_pair_ids', [o['pair_id'] for o in value['observations']]))
    value['unattributed_context'] = [deepcopy(o) for result in batch.get('pair_results', [])
        if result['pair_id'] in pair_ids for o in result['observations'] if o['status']=='UNATTRIBUTED']
    value['interpretation'] = 'Behavior association and associated-pair outcome counts; neither establishes edit benefit or harm. Counts overlap across edit sets and must not be summed as contributions.'
    for observation in value['observations']:
        if 'relation' in observation:
            observation['legacy_relation'] = observation.pop('relation')
    return value


def judgment(record):
    return {k:record[k] for k in ('interpretation','applicability','uncertainty','alternative_explanations',
        'associated_pair_outcome_counts','unattributed_context') if k in record}
