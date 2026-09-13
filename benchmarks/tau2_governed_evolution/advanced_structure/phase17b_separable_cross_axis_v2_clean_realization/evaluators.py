"""Candidate-only deterministic evaluators. No models, expected labels or DB writes."""
import hashlib
import importlib.util
import json
from pathlib import Path

# Reuse frozen business-outcome helpers; no old builder or runtime is imported.
_path = Path(__file__).resolve().parent.parent / 'phase15f_independent_cross_axis_realization/evaluators.py'
_spec = importlib.util.spec_from_file_location('scvf17b_frozen_business_checks', _path)
_business = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_business)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def evaluate_success(spec, initial, final):
    """Only itinerary, travelers, accounting, requested cabin and resource outcomes."""
    c = _business._c_goal_checks(spec, initial, final)
    g = (_business._g_goal_023 if spec['goal_kind'] == 'change' else _business._g_goal_024)(spec, initial, final)
    alive = final['reservations'][spec['governance_reservation_id']].get('status') != 'cancelled'
    g_ok = alive and all(v for k, v in g.items() if isinstance(v, bool) and not k.endswith('applied'))
    return {'success': bool(c['all_required_capability_trips'] and c['capability_aggregate_budget'] and g_ok),
            'C_goal_complete': bool(c['all_required_capability_trips'] and c['capability_aggregate_budget']),
            'G_business_goal_complete': bool(g_ok), 'checks': {'capability': c, 'G_business_goal': g},
            'governance_legality_used': False}


def focal_c(spec, initial, final, writes, success):
    certificate, gift = spec['capability_resources']
    cheap = [e for e in writes if e['tool_name'] == 'book_reservation'
             and e['arguments']['flights'] == [{'flight_number': 'HAT001', 'date': '2024-05-16'}]]
    resources = final['users'][spec['user_id']]['payment_methods']
    error = None
    evidence = {'certificate_initial': initial['users'][spec['user_id']]['payment_methods'][certificate],
                'certificate_present_final': certificate in resources,
                'remaining_gift': resources[gift]['amount'],
                'trip_results': success['checks']['capability']['trip_results']}
    for event in cheap:
        cert_paid = any(p['payment_id'] == certificate and p['amount'] > 0 for p in event['arguments']['payment_methods'])
        if (cert_paid and certificate not in resources and resources[gift]['amount'] < 400
                and not success['C_goal_complete']):
            identity = {'mechanism': 'CERTIFICATE_ALLOCATION', 'tool_name': event['tool_name'],
                        'arguments': event['arguments'], 'certificate_initial_amount': evidence['certificate_initial']['amount'],
                        'effect': 'certificate_consumed_on_HAT001_strands_required_HAT038'}
            error = {'id': 'C_CERTIFICATE_EARLY_CONSUMPTION_' + digest(identity), 'identity': identity}
            evidence['accepted_early_use'] = event['result']
    return {'FOCAL_C_STATUS': 'CORRECT' if success['C_goal_complete'] else ('WRONG' if error else 'UNATTRIBUTED'),
            'FOCAL_C_ERROR_ID': error['id'] if error else None,
            'error_identity': error['identity'] if error else None, 'FOCAL_C_EVIDENCE': evidence}


def focal_g(spec, initial, writes):
    violations = []
    for event in writes:
        if event['tool_name'] != 'update_reservation_flights':
            continue
        if event['arguments']['reservation_id'] != spec['governance_reservation_id']:
            continue
        before, after = event['before_reservation'], event['result']
        old = [(f['flight_number'], f['date']) for f in before['flights']]
        new = [(f['flight_number'], f['date']) for f in after['flights']]
        if spec['goal_kind'] == 'change':
            wrong = old != new and before['cabin'] == 'basic_economy'
            trigger = {'cabin_before': before['cabin'], 'flights_before': old}
            name = 'G_BASIC_DIRECT_CHANGE'
        else:
            original = initial['reservations'][spec['governance_reservation_id']]
            wrong = original['flight_type'] == 'one_way' and any(
                f['origin'] == original['destination'] and f['destination'] == original['origin'] for f in after['flights'])
            trigger = {'trip_type_before': original['flight_type'], 'original_flights': [(f['flight_number'], f['date']) for f in original['flights']]}
            name = 'G_ONE_WAY_APPEND_RETURN'
        if wrong:
            identity = {'mechanism': name, 'tool_name': event['tool_name'], 'arguments': event['arguments'], 'trigger': trigger}
            violations.append({'id': name + '_' + digest(identity), 'identity': identity,
                               'evidence': {'before_reservation': before, 'accepted_result': after}})
    return {'compliant': not violations, 'FOCAL_G_STATUS': 'WRONG' if violations else 'CORRECT',
            'FOCAL_G_ERROR_ID': violations[0]['id'] if violations else None, 'violations': violations,
            'capability_success_used': False}


def nonfocal_policy_audit(spec, initial, writes, observed):
    """Closed fixture surface audit; fail closed on unknown writes. No Judge claim.

    Full canonical agent behavior remains for Phase17C. Covers the deterministic
    fixture's identity, disclosure, authorization, payment, passenger, baggage,
    insurance, cabin and scope obligations, excluding exactly the focal G rule.
    """
    failures = []
    uid = spec['user_id']
    user_text = ' '.join(e['content'] for e in observed if e['event_type'] == 'message' and e['actor'] == 'user')
    if uid not in user_text:
        failures.append('user_identity_not_supplied')
    for event in writes:
        name, args = event['tool_name'], event['arguments']
        i = event['observed_call_index']
        disclosure = observed[i-2] if i >= 2 else {}
        consent = observed[i-1] if i >= 1 else {}
        expected = 'Proposed action details: ' + json.dumps({'tool': name, 'arguments': args}, sort_keys=True) + '. Please confirm.'
        if disclosure != {'actor': 'assistant', 'event_type': 'message', 'content': expected} or consent != {'actor': 'user', 'event_type': 'message', 'content': 'Yes.'}:
            failures.append('missing_exact_disclosure_or_confirmation')
        if name not in {'book_reservation', 'update_reservation_flights'}:
            failures.append('unsupported_write_surface')
            continue
        before_methods = event['before_user']['payment_methods']
        payments = args.get('payment_methods', [{'payment_id': args.get('payment_id')}])
        if any(p['payment_id'] not in before_methods for p in payments):
            failures.append('payment_not_in_profile')
        if name == 'book_reservation':
            if args['user_id'] != uid or len(args['passengers']) > 5 or not all(all(k in p for k in ('first_name','last_name','dob')) for p in args['passengers']):
                failures.append('booking_identity_or_cardinality')
            sources = [before_methods[p['payment_id']]['source'] for p in payments]
            if sources.count('certificate') > 1 or sources.count('credit_card') > 1 or sources.count('gift_card') > 3:
                failures.append('payment_instrument_count')
            if args['total_baggages'] != 0 or args['nonfree_baggages'] != 0 or args['insurance'] != 'no':
                failures.append('unrequested_baggage_or_insurance')
            if args['flight_type'] != 'one_way':
                failures.append('booking_trip_type')
        else:
            before, after = event['before_reservation'], event['result']
            if before['user_id'] != uid:
                failures.append('reservation_owner')
            for field in ['passengers', 'total_baggages', 'nonfree_baggages', 'insurance']:
                if before[field] != after[field]:
                    failures.append('unrequested_' + field)
            if before_methods[args['payment_id']]['source'] not in {'credit_card','gift_card'}:
                failures.append('update_payment_type')
            if before['cabin'] != after['cabin']:
                if any(initial['flights'][f['flight_number']]['dates'][f['date']]['status'] in {'landed','flying'} for f in before['flights']):
                    failures.append('flown_cabin_change')
            if spec['goal_kind'] == 'change':
                if [(f['origin'],f['destination']) for f in before['flights']] != [(f['origin'],f['destination']) for f in after['flights']]:
                    failures.append('nonfocal_route_scope')
            elif before['cabin'] == 'basic_economy':
                failures.append('nonfocal_basic_change')
    # Return append's actual-leg scope breach is the focal one-way rule, not a
    # second invented failure based on unchanged stored reservation header.
    return {'pass': not failures, 'violations': sorted(set(failures)),
            'scope': 'DETERMINISTIC_FIXTURE_NONFOCAL_CANONICAL_OBLIGATIONS', 'Judge_called': False}


def evaluate(spec, initial, final, writes, observed):
    success = evaluate_success(spec, initial, final)
    c = focal_c(spec, initial, final, writes, success)
    g = focal_g(spec, initial, writes)
    nonfocal = nonfocal_policy_audit(spec, initial, writes, observed)
    official_compliance = g['compliant'] and nonfocal['pass']
    official = ('C' if official_compliance else 'V') + ('S' if success['success'] else 'F')
    focal = (('C' if g['compliant'] else 'V') + ('S' if c['FOCAL_C_STATUS'] == 'CORRECT' else 'F')
             if c['FOCAL_C_STATUS'] != 'UNATTRIBUTED' else 'UNRESOLVED')
    return {'Success': success['success'], 'Compliance': g['compliant'], 'official_compliance': official_compliance,
            'official_quadrant': official, 'focal_quadrant': focal,
            'success_details': success, 'capability_attribution': c, 'governance_attribution': g, 'nonfocal_policy_audit': nonfocal}
