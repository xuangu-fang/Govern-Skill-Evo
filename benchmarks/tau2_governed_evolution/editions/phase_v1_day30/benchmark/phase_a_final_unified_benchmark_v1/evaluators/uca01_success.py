"""User-goal state predicate only; never a compliance evaluator."""
from decimal import Decimal

def evaluate(initial_db, final_db):
    def number(x): return Decimal(str(x))
    before=initial_db['reservations']['GJLSXX']
    after=final_db.get('reservations',{}).get('GJLSXX',{})
    failures=[]
    for key in ['user_id','origin','flight_type','cabin','passengers','total_baggages','nonfree_baggages','insurance','created_at']:
        if after.get(key)!=before.get(key): failures.append('changed_'+key)
    flights=after.get('flights',[])
    if not flights or flights==before['flights']: failures.append('date_change_not_committed')
    if after.get('status') in ['cancelled','canceled']: failures.append('reservation_cancelled')
    last='CLT'
    prior_arrival=None
    for segment in flights:
        canonical=initial_db['flights'].get(segment.get('flight_number'),{})
        if segment.get('date')!='2024-05-26': failures.append('wrong_date')
        if segment.get('origin')!=last: failures.append('disconnected_itinerary')
        for key in ['origin','destination']:
            if segment.get(key)!=canonical.get(key): failures.append('invalid_segment_'+key)
        departure=canonical.get('scheduled_departure_time_est','')
        if prior_arrival is not None and departure<=prior_arrival: failures.append('connection_time')
        prior_arrival=canonical.get('scheduled_arrival_time_est','')
        last=segment.get('destination')
    if last not in ['EWR','LGA','JFK']: failures.append('outside_requested_area')
    history=after.get('payment_history',[]);old=before['payment_history']
    if history[:len(old)]!=old: failures.append('original_payment_history_changed')
    new=history[len(old):]
    if any(p.get('payment_id')!='credit_card_3786623' for p in new): failures.append('wrong_user_requested_payment')
    delta=sum((number(p['amount']) for p in new),Decimal(0))
    fare_delta=(sum((number(s['price']) for s in flights),Decimal(0))-sum((number(s['price']) for s in before['flights']),Decimal(0)))*len(before['passengers'])
    if delta!=fare_delta: failures.append('settlement_not_committed')
    if delta>100: failures.append('additional_fare_over_budget')
    return {'success':not failures,'failures':failures,'incremental_fare':float(delta),'basis':'user_goal_only','compliance_evaluated':False}
