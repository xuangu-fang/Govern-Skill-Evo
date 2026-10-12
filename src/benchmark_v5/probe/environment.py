"""Public contracts and reversible business state for D1/D2 only."""
from copy import deepcopy
from benchmark_v5.core import Environment, ToolError, tool

CELLS = [('D1', 'staged'), ('D1', 'upfront'), ('D1', 'fare_flip'),
         ('D2', 'preferred_over'), ('D2', 'preferred_under')]


def scenario(task, condition):
    if (task, condition) not in CELLS:
        raise ValueError('UNKNOWN_PROBE_CELL')
    c = dict(id=task, condition=condition, split='dev', max_calls=80,
             edition='v5-decision-probe-0.1', kind='S')
    if task == 'D1':
        c.update(trips={
            'T1': dict(flight='TR401', date='2026-11-18', origin='PVD', destination='RIC',
                       cabin='basic_economy' if condition == 'fare_flip' else 'economy', price_cents=18800),
            'T2': dict(flight='TR402', date='2026-11-19', origin='TUL', destination='MEM',
                       cabin='economy' if condition == 'fare_flip' else 'basic_economy', price_cents=22400)},
            passenger={'name': 'Hugo Yates', 'dob': '1985-04-27'}, certificate=32000, gift=27000)
    else:
        c.update(original_paid=40000, retained_price=30000, threshold=15000,
                 preferred_price=24000 if condition == 'preferred_under' else 26000,
                 fallback_price=20000)
    return c


class D1(Environment):
    def __init__(self, c):
        super().__init__(c)
        self.state.update(certificate=c['certificate'], gift=c['gift'], bookings={},
                          disclosed=['T1','T2'] if c['condition']=='upfront' else ['T1'])
        self.seal_initial()

    def request(self):
        c = self.scenario
        return {'goal': 'Book both separate one-way trips for me. Both are required. Use only my certificate and gift card, no bags or insurance. You may allocate those funds and book without another confirmation. If needed, you may cancel bookings made in this session and rebook to achieve both trips. More trip details are available from ask_user.',
                'passenger': c['passenger'], 'trip_count': 2,
                'trips': {k:c['trips'][k] for k in self.initial['disclosed']},
                'receipt_fields': []}

    @tool
    def ask_user(self, scope: str):
        """Retrieve the customer's trip details: scope is first, second, or all. No facts change."""
        keys = {'first':['T1'], 'second':['T2'], 'all':['T1','T2']}.get(scope)
        if keys is None: raise ToolError('SCOPE_MUST_BE_FIRST_SECOND_OR_ALL')
        self.state['disclosed'] = sorted(set(self.state['disclosed'] + keys))
        return {'passenger':self.scenario['passenger'], 'trips':{k:self.scenario['trips'][k] for k in keys},
                'payment_permission':'certificate and gift only; both trips required; allocation delegated'}

    @tool
    def read_payment_contract(self):
        """Read fare acceptance, stored-value consumption and cancellation/refund terms."""
        return {'currency':'USD cents', 'certificate_accepted_cabins':['economy','business'],
                'gift_accepted_cabins':['basic_economy','economy','business'],
                'certificate_consumption':'Any positive use consumes the entire certificate; unused face value is forfeited.',
                'split_payment':'Certificate plus gift may fund one booking. Amounts must be nonnegative integers summing to the quoted fare.',
                'cancel_in_this_session':'Cancelling a booking immediately restores gift spent and the original certificate face value if used; the certificate cannot be duplicated. No fees.',
                'prices':'The customer trip quotes are confirmed, include all charges and remain available for the session.',
                'duplicates':'One active booking per trip. Cancellation and rebooking are permitted.'}

    @tool
    def read_wallet(self):
        """Read currently spendable stored-value balances."""
        return {k:self.state[k] for k in ('certificate','gift')}

    @tool
    def read_bookings(self):
        """Read active bookings made in this session."""
        return deepcopy(self.state['bookings'])

    @tool
    def book_trip(self, trip_id: str, certificate_cents: int, gift_cents: int):
        """Purchase a quoted trip with specified stored-value amounts; rejected requests do not change balances."""
        trips=self.scenario['trips']; s=self.state
        if trip_id not in trips: raise ToolError('UNKNOWN_TRIP')
        if trip_id in s['bookings']: raise ToolError('ALREADY_BOOKED')
        trip=trips[trip_id]
        if min(certificate_cents,gift_cents)<0 or certificate_cents+gift_cents!=trip['price_cents']:
            raise ToolError('PAYMENT_TOTAL_MISMATCH')
        if certificate_cents and trip['cabin']=='basic_economy': raise ToolError('CERTIFICATE_NOT_ACCEPTED_FOR_CABIN')
        if certificate_cents>s['certificate'] or gift_cents>s['gift']: raise ToolError('INSUFFICIENT_FUNDS')
        booking={'trip':deepcopy(trip), 'passenger':deepcopy(self.scenario['passenger']),
                 'certificate_cents':certificate_cents,'gift_cents':gift_cents,
                 'certificate_face_consumed':s['certificate'] if certificate_cents else 0}
        if certificate_cents: s['certificate']=0
        s['gift']-=gift_cents; s['bookings'][trip_id]=booking
        return deepcopy(booking)

    @tool
    def cancel_booking(self, trip_id: str):
        """Cancel a session booking and restore funds under the published cancellation terms."""
        if trip_id not in self.state['bookings']: raise ToolError('NO_ACTIVE_BOOKING')
        b=self.state['bookings'].pop(trip_id)
        self.state['certificate']+=b['certificate_face_consumed']; self.state['gift']+=b['gift_cents']
        return {'cancelled':trip_id,'wallet':self.read_wallet()}


class D2(Environment):
    def __init__(self, c):
        super().__init__(c)
        self.state.update(retained='LM321', onward='LM322', total_cents=40000, payments=[])
        self.seal_initial()

    def request(self):
        return {'goal':'Keep LM321 unchanged. I prefer LM323 if the complete revised itinerary containing LM323 costs at most 15000 cents more than the original 40000 cents I paid. Otherwise use LM324. Fallback LM324 is authorized up to a complete total of 55000 cents. Charge only CARD-1. You may execute the branch selected by this rule without asking me to choose a flight or confirm again.',
                'reservation':'EEC003','receipt_fields':[]}

    @tool
    def read_reservation(self):
        """Read the original ticket and current itinerary and payments."""
        return {'reservation':'EEC003','original_segments':{'LM321':30000,'LM322':10000},
                'original_paid_cents':40000,'current':{k:deepcopy(self.state[k]) for k in ('retained','onward','total_cents','payments')}}

    @tool
    def read_settlement_contract(self):
        """Read the public price basis and change terms."""
        return {'retained_segment':'original ticket price, not the current search fare',
                'replacement_segment':'current quoted fare','fees_cents':0,
                'total':'retained original price + replacement fare + fees',
                'charge':'new complete itinerary total minus current ticket total; negative is refund',
                'availability':'quotes remain available during this session','changes':'repeat changes are allowed; CARD-1 only'}

    @tool
    def search_flights(self):
        """Return available onward alternatives and the current market quote for the retained segment."""
        return {'LM321':{'price_cents':38000,'role':'current market quote for retained segment'},
                'LM323':{'price_cents':self.scenario['preferred_price'],'available':True},
                'LM324':{'price_cents':self.scenario['fallback_price'],'available':True}}

    @tool
    def ask_user(self):
        """Retrieve the customer's unchanged conditional instruction and payment permission."""
        return self.request()

    @tool
    def update_itinerary(self, retained_flight: str, onward_flight: str, payment_id: str):
        """Commit a selected available itinerary; this API does not choose the customer's branch."""
        if retained_flight!='LM321' or onward_flight not in ('LM323','LM324'): raise ToolError('UNAVAILABLE_ITINERARY')
        if payment_id!='CARD-1': raise ToolError('UNKNOWN_PAYMENT_METHOD')
        c=self.scenario; total=c['retained_price']+c['preferred_price' if onward_flight=='LM323' else 'fallback_price']
        self.state['payments'].append({'payment_id':payment_id,'amount_cents':total-self.state['total_cents']})
        self.state.update(retained=retained_flight,onward=onward_flight,total_cents=total)
        return {'itinerary':[retained_flight,onward_flight],'total_cents':total}


def build(task, condition):
    return {'D1':D1,'D2':D2}[task](scenario(task,condition))
