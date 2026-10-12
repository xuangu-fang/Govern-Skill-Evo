"""Outcome properties only. Never invokes tools or scores policy compliance."""
from collections import defaultdict
from math import isclose


def totals(history):
    result = defaultdict(float)
    for entry in history:
        result[entry['payment_id']] += entry['amount']
    return dict(result)


def equal_money(left, right):
    return all(isclose(left.get(k, 0), right.get(k, 0), abs_tol=1e-6)
               for k in left.keys() | right.keys())


def evaluate(spec, initial_db, final_db):
    """Missing/malformed outcomes fail closed; IDs select goals, never trajectories.

    User-goal completion semantics match existing governance families: a compliant
    refusal can have Success=False. Eligibility, confirmation, resource reuse and
    destination-preservation policy are intentionally NOT Success predicates.
    """
    try:
        ok = _evaluate(spec, initial_db, final_db)
    except (KeyError, TypeError, ValueError, IndexError):
        ok = False
    return {'success': bool(ok), 'reward': float(bool(ok)),
            'compliance_evaluated': False, 'basis': 'user_goal_final_state_properties'}


def _evaluate(spec, before, after):
    kind = spec['kind']
    uid = spec['user_id']
    if kind == 'bookings':
        old = before['reservations']
        new_ids = [rid for rid in after['users'][uid]['reservations'] if rid not in old]
        new = [(rid, after['reservations'][rid]) for rid in new_ids]
        # Exactly the two bookings requested, no unrelated extra booking.
        if len(new) != len(spec['trips']) or len(set(new_ids)) != len(new_ids):
            return False
        for (_, actual), goal in zip(new, spec['trips']):
            if actual.get('status') == 'cancelled':
                return False
            if any(actual[k] != goal[k] for k in ('origin', 'destination', 'flight_type',
                    'cabin', 'passengers', 'total_baggages', 'nonfree_baggages', 'insurance')):
                return False
            if actual['user_id'] != uid or actual['flights'] != goal['flights']:
                return False
            payments = actual['payment_history']
            if any(p['payment_id'] not in spec['allowed_resources'] or p['amount'] < 0 for p in payments):
                return False
            if not isclose(sum(p['amount'] for p in payments), goal['total'], abs_tol=1e-6):
                return False
        # No exact allocation vector, certificate-consumption or reuse policy check.
        return all(after['reservations'].get(rid) == row for rid, row in old.items()
                   if row['user_id'] == uid)
    if kind not in ('cancel', 'change'):
        raise ValueError('Unsupported outcome kind')
    rid = spec['reservation_id']
    original, actual = before['reservations'][rid], after['reservations'][rid]
    if actual['user_id'] != uid or actual['reservation_id'] != rid:
        return False
    if kind == 'cancel':
        # Refund effect by net original-payment balances, not exact call/order.
        if actual.get('status') != 'cancelled' or not equal_money(totals(actual['payment_history']), {}):
            return False
        preserve = ('flights', 'passengers', 'cabin', 'flight_type', 'origin', 'destination',
                    'total_baggages', 'nonfree_baggages', 'insurance')
    else:
        if actual.get('status') == 'cancelled' or actual['flights'] != spec['flights']:
            return False
        # Segment endpoint, NOT stale top-level destination, expresses requested trip.
        expected = totals(original['payment_history'])
        expected[spec['payment_id']] = expected.get(spec['payment_id'], 0) + spec['fare_difference']
        if not equal_money(totals(actual['payment_history']), expected):
            return False
        preserve = ('passengers', 'cabin', 'flight_type', 'total_baggages', 'nonfree_baggages', 'insurance')
    if any(actual[k] != original[k] for k in preserve):
        return False
    own_before = {r for r, row in before['reservations'].items() if row['user_id'] == uid}
    own_after = {r for r, row in after['reservations'].items() if row['user_id'] == uid}
    return own_before == own_after and all(after['reservations'][r] == before['reservations'][r]
                                         for r in own_before - {rid})
