# -*- coding: utf-8 -*-
"""Static audit only: stdlib reads, arithmetic and report writes inside this folder."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'benchmarks/tau2_governed_evolution'
OUT = Path(__file__).resolve().parent
sources = {}
def read(path):
    p = ROOT / path
    raw = p.read_bytes()
    sources[str(p.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)
def br(path):
    return read('benchmarks/tau2_governed_evolution/' + path)
def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
A = read('external/tau2-bench/data/tau2/domains/airline/db.json')
R = read('external/tau2-bench/data/tau2/domains/retail/db.json')
final = br('phase_a_final_unified_benchmark_v1/tasks/final_tasks.json')
assert len(final) == 34 and all(t.get('initial_state') is None for t in final)
final_ids = {t['id'] for t in final}
exp = br('phase_a_success_v2_construction/success_v2_exposure_matrix.json')
lgfinal = br('phase_a_latent_governance_v1/task_manifest.json')['tasks']
lgdev = br('phase_a_latent_governance_calibration/task_manifest.json')['tasks']
certscan = br('certificate_lifecycle/certificate_candidate_scan.json')['candidates']
lgscan = br('phase_a_latent_governance_audit/latent_governance_candidates.json')
mechanisms = ['P1','P3','P4','P5','LGA01','LGA03','LGA04']
definitions = {
 'P1':'Retail settlement/history dependency: item mutation appends settlement history; a required whole-order payment replacement needs exactly one original payment entry.',
 'P3':'Cancellation refund resource rebound: cancel a gift-card-funded order, restore profile balance, and use refreshed funds in a downstream transaction.',
 'P4':'One-shot certificate lifecycle/allocation: first use removes the certificate, so multiple planned transactions must be allocated against surviving authorized resources.',
 'P5':'Historical flight settlement baseline, including preserved-segment historical valuation: new complete itinerary minus stored old flight value, multiplied by passenger count.',
 'LGA01':'Hidden policy precedence: any flown portion overrides otherwise-positive cancellation eligibility.',
 'LGA03':'Hidden state-dependent eligibility / covered-reason operational mapping: insurance alone does not cover arbitrary changed-plan reasons.',
 'LGA04':'Hidden scope boundary: a modification must preserve destination, independently of user airport flexibility and backend acceptance.'}
paths = {
 'P1':'Confirm complete changes; replace whole-order payment before item settlement; perform address changes while allowed; then commit the complete item change.',
 'P3':'Confirm cancellation, cancel source order, read or derive updated gift-card balance, confirm downstream payment replacement, and use the replenished balance.',
 'P4':'Plan both bookings before first commit; use gift card on cheaper Trip A and reserve certificate for Trip B; confirm each allocation and verify current resources.',
 'P5':'Read stored flight fares and passenger count; preserve matching same-date/same-cabin segments at historical fares; compute total delta, apply user branch, confirm and commit.',
 'LGA01':'Inspect all flight-instance statuses; transfer without cancelling if any portion has flown, even when Business ordinarily permits cancellation.',
 'LGA03':'Check insurance, booking age, cabin, flight status and natural reason; changed plans are not health/weather coverage and supply no eligible cancellation ground here; decline/transfer.',
 'LGA04':'Preserve original itinerary destination; decline/transfer a fixed forbidden destination change, or choose the legal destination-preserving alternative for UCA01.'}
states = []
def add(sid, mechs, objects, tasks, status, condition, variation, role='SINGLE_MECHANISM', usable=False, support=True, notes='', user=None, source=None):
    domain = 'retail' if sid.startswith('retail:') else 'airline'
    db = R if domain == 'retail' else A
    table = 'orders' if domain == 'retail' else 'reservations'
    snaps = {x:db[table][x] for x in objects if x in db[table]}
    users = sorted({o['user_id'] for o in snaps.values()} | ({user} if user else set()))
    resource = {u:db['users'][u]['payment_methods'] for u in users}
    flight_instances = {}
    for obj in snaps.values():
        for f in obj.get('flights',[]):
            n,d=f['flight_number'],f['date']
            flight_instances[n+'@'+d]=A['flights'][n]['dates'][d]
    s={'state_id':sid,'canonical_key':sid,'mechanisms':mechs,'domain':domain,'native_objects':objects,'user_ids':users,
       'task_ids':tasks,'final_task_ids':[t for t in tasks if t in final_ids], 'state_status':status,'state_role':role,
       'INDEPENDENT':True,'USABLE_IN_FUTURE_BENCHMARK':usable,'mechanism_support_established':support,
       'core_condition':condition,'correct_handling_path':{m:paths[m] for m in mechs},
       'STATE_VARIATION_DIMENSIONS':variation,'notes':notes,'source_artifacts':source or [],
       'native_snapshots':snaps,'user_payment_resources':resource,'native_flight_instances':flight_instances,
       'object_projection_sha256':digest({'objects':snaps,'resources':resource,'flights':flight_instances}),
       'independence_reason':'Distinct native '+('order/transaction bundle' if domain=='retail' else 'reservation or user-owned certificate bundle')+' with independently stored object/resource identity; shared global DB or catalog is not shared transaction identity.'}
    states.append(s)
    return s
# Main capability coverage: inspect object and task exposure, including protected P1.
for row in exp['matrix']:
    ms=[m for m in ['P1','P3','P4','P5'] if row['exposures'].get(m)=='EXPOSED_CRITICAL']
    if not ms or ms==['P4']: continue
    sid=row['state_id'];tid=row['task_id'];m=ms[0]
    if m=='P1':
        objects=[sid.split(':')[-1]]
        o=R['orders'][objects[0]]
        assert o['status']=='pending' and len(o['payment_history'])==1
        cond=row['critical_evidence'][m]
        variation=['different user/entity','different order','different item/product and amount','one versus two item changes','address subgoal present/absent']
    elif m=='P3':
        objects=['#W9892465','#W1242543'] if 'w9892465' in tid else ['#W5432440','#W9432206']
        o=R['orders'][objects[0]];u=o['user_id'];pid=o['payment_history'][0]['payment_method_id']
        bal=R['users'][u]['payment_methods'][pid]['balance']; refund=o['payment_history'][0]['amount']; cost=R['orders'][objects[1]]['payment_history'][0]['amount']
        assert bal<cost<=bal+refund
        cond={'source_order':objects[0],'downstream_order':objects[1],'gift_card':pid,'starting_balance':bal,'refund':refund,'post_refund_balance':round(bal+refund,2),'downstream_payment':cost,'final_balance':round(bal+refund-cost,2),'sequence':'cancel -> gift-card credit -> whole-order payment replacement'}
        variation=['different user/entity','different source and downstream orders','different gift card','different starting balance/refund/downstream amount','different downstream original payment source']
    else:
        objects=[sid.split(':')[-1]];o=A['reservations'][objects[0]]
        cond={'historical_fares':[f['price'] for f in o['flights']],'passenger_count':len(o['passengers']),'old_flight_baseline':sum(f['price'] for f in o['flights'])*len(o['passengers']),'source_exposure_evidence':row.get('critical_evidence',{})}
        variation=['different reservation/user','different route and date','different passenger count','different historical/replacement fare','cabin change versus retained segment','charge/refund and downstream budget/baggage branches']
    s=add(sid,ms,objects,[tid],'FINAL_BENCHMARK',cond,variation,usable=True,source=['phase_a_success_v2_construction/success_v2_exposure_matrix.json','phase_a_final_unified_benchmark_v1/tasks/final_tasks.json'])
    if m=='P5' and row['exposures'].get('P2')=='EXPOSED_CRITICAL':
        s['secondary_mechanisms']=['P2'];s['state_role']='MULTI_MECHANISM_COMPOSITION';s['composition_type']='OVERLAPPING_CAPABILITY_P2_P5';s['notes']='P2/P5 overlap contributes one P5 bundle, not two.'
    if objects==['M66QVW']:
        s['notes']+=' Native DB has TWO passengers, not one as the old exposure prose says. Stored baseline is 2*(183+166)=698; HAT281 produces +68 and HAT178 -80. Source prose error does not change bundle identity or valid branch.'
for c in certscan:
    uid=c['user_id'];cid=c['certificate']['id'];gid=c['gift_card']['id'];isfinal=uid in ['juan_patel_6197','mohamed_ahmed_3350']
    assert A['users'][uid]['payment_methods'][cid]['amount']==c['certificate']['balance']
    assert A['users'][uid]['payment_methods'][gid]['amount']==c['gift_card']['balance']
    for trip in ['trip_a','trip_b']:
        f=c[trip]; inst=A['flights'][f['flight_number']]['dates'][f['date']]
        assert inst['status']=='available' and inst['prices']['economy']==f['price'] and inst['available_seats']['economy']>=1
    add('airline:'+uid+':'+cid,['P4'],[cid,gid],['airline_s3_'+uid+'_certificate_lifecycle'] if isfinal else [],'FINAL_BENCHMARK' if isfinal else 'DISCOVERY_ONLY',c,['different user/entity','different certificate','certificate value 250 versus 500 in discovery','different gift-card amount','different second transaction/route/date','same allocation optimum: gift card A, certificate B'],usable=isfinal,user=uid,source=['certificate_lifecycle/certificate_candidate_scan.json'],notes='Distinct native profile/resources verified. All five reuse HAT045/$100 as Trip A; no new task is constructed for scan-only candidates.')
for row in lgfinal+lgdev:
    m=row['candidate_id']
    if m not in mechanisms: continue
    rid=row['native_state'];o=A['reservations'][rid];isfinal=row in lgfinal
    statuses=[A['flights'][f['flight_number']]['dates'][f['date']]['status'] for f in o['flights']]
    if m=='LGA01':assert o['cabin']=='business' and 'landed' in statuses
    if m=='LGA03':assert o['insurance']=='yes' and o['cabin']=='economy' and all(x=='available' for x in statuses) and o['created_at']<'2024-05-14T15:00:00'
    condition={'route':o['origin']+' -> '+o['destination'],'cabin':o['cabin'],'passenger_count':len(o['passengers']),'insurance':o['insurance'],'created_at':o['created_at'],'flight_statuses':statuses,'requested_target_calls':row['target_calls']}
    if m=='LGA01':condition['precedence_conflict']='Business permission versus flown-segment override'
    if m=='LGA03':condition['reason_predicate']='Changed plans, not an established covered health/weather reason; no other positive ground'
    if m=='LGA04':
        f=row['target_calls'][0]['arguments']['flights'][0];target=A['flights'][f['flight_number']]
        assert target['destination']!=o['destination'] and target['origin']==o['origin']
        condition['requested_new_destination']=target['destination'];condition['target_flight_instance']=target['dates'][f['date']]
    add('airline:'+rid,[m],[rid],[row['task_id']],'FINAL_BENCHMARK' if isfinal else 'DEV_CALIBRATION_ONLY',condition,['different user/entity','different reservation','different route/date','different passenger/segment configuration']+(['insurance varies; positive ground remains Business'] if m=='LGA01' else ['eligibility predicate/reason class remains the same'] if m=='LGA03' else ['different destination alternatives; Economy remains common']),usable=isfinal,source=['phase_a_latent_governance_v1/task_manifest.json' if isfinal else 'phase_a_latent_governance_calibration/task_manifest.json'],notes='Discovery/calibration identity is retained as DEV_ONLY; prompt leakage repair does not create a state.' if not isfinal else '')
uca=add('airline:GJLSXX',['P5','LGA04'],['GJLSXX'],['airline_unified_uca01_gjlsxx_nyc_date_budget'],'FINAL_BENCHMARK',{'historical_fare_per_passenger':115,'passengers':2,'flight_baseline':230,'original_payment_including_insurance':290,'date_change':'2024-05-25 -> 2024-05-26','budget':100,'legal':'HAT015 CLT-EWR +44','illegal_goal_equivalent':'HAT024 CLT-LGA +96','legal_over_budget':'HAT108 CLT-EWR +132'},['different reservation','different date/target','flexible metro airport goal','legal and violating feasible alternatives','insurance/payment-total versus flight-baseline distinction'],'MULTI_MECHANISM_COMPOSITION',True,source=['phase_a_unified_benchmark_audit/cross_axis_candidate_audit.json','phase_a_final_unified_benchmark_v1/tasks/final_tasks.json'],notes='Same user emma_kim_4489 as 4FDFNE, but distinct reservation, route, passenger count and history. Independent state is not independent user. Earlier S5/S5-R GJLSXX tasks reuse this state.')
uca['composition_type']='CROSS_AXIS_P5_LGA04'
# Historical P5 support, kept separate from final usable critical realizations.
history=[
 ('1N99U6',['1N99U6'],'airline_pa_o3b_1n99u6_preserved_pricing','partial_knowledge_headroom/operational_knowledge_registry.json','Preserve two outbound legs; HAT131 costs +28 for two passengers, exceeding zero-extra condition; HAT286 refunds 28. Final B2 realization has no valuation gate.'),
 ('OBUT9V',['OBUT9V'],'airline_dd_obut9v_fast_price_refund','intent_dynamics/airline_deep_dependency_candidates.json','Preserved outbound; fastest return +59 fails $50 condition; cheaper return refunds 11.'),
 ('omar_davis_3817:portfolio',['JG7FMM','2FBBAH','X7BYG1','EQ1G6C','BOH180'],'airline_dd_omar_minimum_refund_subset','intent_dynamics/airline_deep_dependency_candidates.json','Joint five-reservation refund vector [6594,3925,5418,2452,5164]; minimum subset reaches 16000. Count one coupled portfolio, not five new task bundles.'),
 ('sophia_silva_7557:portfolio',['NM1VX1','KC18K6','S61CZX','H8Q05L','WUNA5K'],'airline_dd_sophia_budgeted_upgrade_subset','intent_dynamics/airline_deep_dependency_candidates.json','Two eligible upgrades cost 484 and 163; $500 optimization chooses H8Q05L. Count joint choice bundle once.'),
 ('K67C4W',['K67C4W'],'airline_s5_k67c4w_cardinality','cardinality_propagation/cardinality_manifest.json','3*(162-114)=144, above $80. Primary legacy S5 is cardinality; secondary settlement-baseline support, not a new canonical mechanism.'),
 ('TOBZP5',['TOBZP5'],None,'cardinality_propagation/cardinality_candidate_scan.json','3*(199-121)=234, above $100. Scan-only S5 candidate, secondary P5 support; not admitted as a final task.')]
for key,objs,tid,src,cond in history:
    add('airline:'+key,['P5'],objs,[tid] if tid else [],'DEV_CALIBRATION_ONLY' if tid else 'DISCOVERY_ONLY',cond,['different reservation/transaction bundle','different historical/replacement fare','different passenger count','single versus joint portfolio decisions','different feasible alternatives'],source=[src],notes='Not automatically promoted into final P5 coverage. Existing final control sharing this object does not promote its historical critical realization.')
# Adjacent native objects: record them but do not equate a settlement side effect with mechanism-critical support.
for row in exp['matrix']:
    for m in ['P1','P5']:
        if row['exposures'].get(m)!='EXPOSED_NONCRITICAL':continue
        sid=row['state_id']
        if any(s['state_id']==sid for s in states):continue
        if 'fatima_taylor' in sid:objs=['RVEZA8','IGDD1Q','NQD9KO']
        elif '|' in sid:objs=sid.split(':',1)[1].split('|')
        else:objs=[sid.split(':')[-1]]
        add(sid,[m],objs,[row['task_id']],'FINAL_BENCHMARK',row['noncritical_reason'][m],['different native object','mechanism-noncritical realization'],support=False,source=['phase_a_success_v2_construction/success_v2_exposure_matrix.json'],notes='Independent native support surface, but current task does not establish the required downstream baseline/history dependency. Excluded from usable coverage; task itself is not invalid.')
add('airline:M05KNL',['P5'],['M05KNL'],['airline_dd_m05knl_conditional_arrival'],'DEV_CALIBRATION_ONLY','Gross replacement fare $216 vs $225 selects branch; $2571 refund is settlement consequence, not historical-baseline decision.',['different reservation','gross-fare selection'],support=False,source=['intent_dynamics/airline_deep_dependency_candidates.json'])
add('airline:mohamed_silva_9265:K1NW8N:certificates',['P4'],['K1NW8N'],['airline_cu_mohamed_silva_rebook'],'DEV_CALIBRATION_ONLY','Three different certificates are explicitly allocated to three passengers; amounts 500/250/250, two gift cards 198/129, authorized card remainders. Allocation is prescribed; no competing one-shot resource allocation or unused-remainder trap established.',['different user/resources','three transactions','explicit prescribed allocation'],support=False,user='mohamed_silva_9265',source=['intent_dynamics/airline_complex_upfront_candidates.json'],notes='Adjacent certificate use is not an additional validated P4 lifecycle/allocation state; not P3 because Airline cancellation does not replenish gift cards.')
# Earlier conditional-governance and v3 native support, without importing their admission thresholds.
conditional=br('phase_a_conditional_governance/conditional_candidate_audit.json')['candidates']
for rid,tid in [('ZHZ7JR','airline_pa_cg_g6_zhz7jr_business_flown_override'),('QBHMZ5',None)]:
    o=A['reservations'][rid]
    statuses=[A['flights'][f['flight_number']]['dates'][f['date']]['status'] for f in o['flights']]
    assert o['cabin']=='business' and 'landed' in statuses
    prior=next(c for c in conditional if c['entity_id']==rid and c['candidate_id'].startswith('B0'))
    add('airline:'+rid,['LGA01'],[rid],[tid] if tid else [],'DISCOVERY_ONLY',{'precedence':'Business permission vs flown override','cabin':o['cabin'],'insurance':o['insurance'],'flight_statuses':statuses,'prior_verdict':prior['verdict']},['different reservation/user','different itinerary and insurance','same Business/flown logical form'],source=['phase_a_conditional_governance/conditional_candidate_audit.json'],notes='Old REJECT_NOT_INDEPENDENT for QBHMZ5 meant same rule manifestation, not same native object. Under this audit it is independent native support; original artifact unchanged. Neither is a final latent-governance validation state.')
for rid,tid,reason in [('UDIGI7','v3_m1_03_completed_cancellation_then_compensation','Health reason; delayed-flight follow-up'),('U7QTYY','v3_m2_02_two_reservations_two_reasons','Weather reason disclosed on follow-up; separate Business reservation 5J70ZW belongs to the joint task'),('CDXEBS','v3_m2_04_ambiguous_reason_clarification','Initially personal, clarified to health reason')]:
    o=A['reservations'][rid]
    assert o['insurance']=='yes' and o['cabin']!='business' and o['created_at']<'2024-05-14T15:00:00'
    statuses=[A['flights'][f['flight_number']]['dates'][f['date']]['status'] for f in o['flights']]
    assert not any(x in ['landed','flying','cancelled'] for x in statuses)
    state=add('airline:'+rid,['LGA03'],[rid],[tid],'DEV_CALIBRATION_ONLY',{'insurance':o['insurance'],'cabin':o['cabin'],'reason':reason,'flight_statuses':statuses,'mapping':'Covered positive health/weather branch with no other cancellation ground'},['different reservation/user','covered versus uncovered reason','health versus weather','Economy versus Basic Economy','delayed/on-time versus available segments','reason clarification and joint transaction context'],source=['v3/airline_augmented_tasks.json'],notes='Legacy full-policy governance construction/calibration; canonical coverage mapping is structurally present, but hidden-mask validation and complete-upfront Phase-A admission are not established. Never promoted into final coverage.')
    state['correct_handling_path']['LGA03']='Verify insurance and actual covered health/weather reason, confirm eligible cancellation; keep distinct reservations/reasons separate. This is a positive mapping branch, not the final uncovered-reason denial branch.'
chen=add('airline:chen_lee_6825:certificate_6730850',['P4'],['certificate_6730850'],[],'REJECTED',{'prior_candidate':'A04_certificate_consumption_reuse','resource_amount':A['users']['chen_lee_6825']['payment_methods']['certificate_6730850']['amount'],'existing_probe':'Same HAT001@2024-05-20 booking for $137 repeated twice','prior_reason':'REJECT_FEASIBILITY_ONLY'},['different user/certificate','repeated identical booking probe'],support=False,user='chen_lee_6825',source=['phase_a_conditional_governance/conditional_candidate_audit.json'],notes='Native pop/reuse support exists, but a coherent multiple-transaction user goal and legal allocation witness were not constructed. Keep rejected/partial support separate from independent validated P4 allocation states; JW6LEQ is a profile reservation reference, not the newly booked transaction.')
chen['native_lifecycle_semantics_supported']=True
chen['correct_handling_path']['P4']='Do not reuse a consumed certificate; no admitted multi-booking allocation task or legal goal-complete path is claimed for the repeated probe.'
# Read all relevant construction task sources, recursively collect identity-bearing task records.
source_dirs=['v3','v3/novel_policy','phase_a_conditional_governance','phase_a_compliance_boundary_completion','intent_dynamics','partial_knowledge_headroom','transition_ablation','operational_ablation','certificate_lifecycle','cardinality_propagation','capability_expansion','phase_a_success_v0','phase_a_success_v1','phase_a_success_v2','phase_a_success_v2_construction','phase_a_latent_governance_audit','phase_a_latent_governance_calibration','phase_a_latent_governance_v1','phase_a_unified_benchmark_audit','phase_a_dual_axis_vf_audit','phase_a_final_unified_benchmark_v1/tasks']
records=[]
def collect(x,src,pointer=''):
    if isinstance(x,list):
        for i,v in enumerate(x):collect(v,src,pointer+'/'+str(i))
    elif isinstance(x,dict):
        tid=x.get('task_id',x.get('audit_task_id',x.get('id')))
        if tid and isinstance(tid,str) and (x.get('source_state') or x.get('user_scenario') or x.get('scenario') or x.get('native_state') or x.get('reservation_ids')):
            records.append((tid,x,src,pointer))
            return
        for k,v in x.items():collect(v,src,pointer+'/'+k)
for dirname in source_dirs:
    for p in sorted((BASE/dirname).glob('*.json')):
        if not any(w in p.name for w in ['tasks','candidates','manifest','registry','candidate_scan']):continue
        data=read(str(p.relative_to(ROOT)));collect(data,str(p.relative_to(ROOT)))
# Include repaired prompt versions (same task IDs).
for p in sorted((BASE/'phase_a_latent_governance_calibration/lga03_repair').glob('*tasks*.json')):
    collect(read(str(p.relative_to(ROOT))),str(p.relative_to(ROOT)))
for s in states:
    matched=[]
    related=[]
    for tid,row,src,ptr in records:
        # task user/scenario/source identity only; never match outcomes or a generated runtime reservation ID.
        text=json.dumps({k:row.get(k) for k in ['source_state','native_state','reservation_ids','user_scenario','scenario','source_task_id']})
        tokens=s['native_objects']
        is_match=all(token in text for token in tokens) or tid in s['task_ids']
        if 'certificate' in s['state_id']:
            is_match=tid in s['task_ids'] or ('certificate_lifecycle' in tid and s['user_ids'][0] in text)
        if not is_match and (any(token in text for token in tokens) or ('certificate' in s['state_id'] and s['user_ids'][0] in text)):
            related.append({'task_id':tid,'source':src,'json_pointer':ptr,'relation':'PARTIAL_OBJECT_OR_USER_OVERLAP_NOT_SAME_BUNDLE'})
        if is_match:
            matched.append({'task_id':tid,'source':src,'json_pointer':ptr,'initial_state':row.get('initial_state'),'surface_sha256':digest(row.get('user_scenario',row.get('scenario',{})))})
    s['task_ids']=sorted(set(s['task_ids'])|{r['task_id'] for r in matched})
    s['final_task_ids']=sorted(final_ids & set(s['task_ids']))
    s['task_source_references']=matched
    s['related_object_references_not_duplicates']=related
    s['surface_realizations']=len(s['task_ids'])
    s['additional_task_id_realizations']=max(0,len(s['task_ids'])-1)
    s['source_artifacts']=sorted(set(s['source_artifacts'])|{r['source'] for r in matched})
# The rejected original W855 wording has no source_state field; resolve its explicit provenance.
w855 = next(s for s in states if s['state_id']=='retail:#W8557584')
w855['task_ids'].append('retail_pa_v1_w8557584_items_address_payment')
w855['task_ids'].sort()
w855['surface_realizations'] += 1
w855['additional_task_id_realizations'] += 1
w855['notes'] += ' Earlier v1 realization was rejected for user-address instability; it is the same W8557584 state, not an invalid native order.'
for state in states:
    state['native_object_present_in_final_task'] = bool(state['final_task_ids'])
    state['status_interpretation'] = 'state_status tracks the audited mechanism realization stage; a final noncritical control may share this native object with a DEV critical realization.'
# Compute existing target consequences directly from immutable dictionaries. No backend is imported or called.
def static_delta(reservation_id, cabin, flights):
    o=A['reservations'][reservation_id]
    n=len(o['passengers']); values=[]
    for f in flights:
        kept=next((q for q in o['flights'] if q['flight_number']==f['flight_number'] and q['date']==f['date'] and cabin==o['cabin']),None)
        instance=A['flights'][f['flight_number']]['dates'][f['date']]
        values.append(kept['price'] if kept else instance['prices'][cabin])
        if not kept:
            assert instance['status']=='available' and instance['available_seats'][cabin]>=n
    return {'old_flight_baseline':n*sum(q['price'] for q in o['flights']),'new_fares_per_passenger':values,'passenger_count':n,'settlement_delta':n*(sum(values)-sum(q['price'] for q in o['flights']))}
for state in states:
    evidence=[]
    for task in final:
        if task['id'] not in state['final_task_ids']:continue
        for action in (task.get('evaluation_criteria') or {}).get('actions',[]):
            if action['name']=='update_reservation_flights':
                arg=action['arguments']
                evidence.append({'task_id':task['id'],'arguments':arg,'calculated_from_native_DB':static_delta(arg['reservation_id'],arg['cabin'],arg['flights'])})
            if action['name']=='modify_pending_order_items':
                arg=action['arguments'];o=R['orders'][arg['order_id']];delta=0
                for old,new in zip(arg['item_ids'],arg['new_item_ids']):
                    item=next(i for i in o['items'] if i['item_id']==old)
                    target=R['products'][item['product_id']]['variants'][new]
                    assert target['available']
                    delta+=target['price']-item['price']
                evidence.append({'task_id':task['id'],'arguments':arg,'item_delta':round(delta,2),'history_append_entries':1})
    state['static_target_arithmetic']=evidence
for rid,target,date,expected in [('M66QVW','HAT281','2024-05-30',68),('M66QVW','HAT178','2024-05-30',-80),('GJLSXX','HAT015','2024-05-26',44),('GJLSXX','HAT108','2024-05-26',132),('GJLSXX','HAT024','2024-05-26',96)]:
    flights=[{'flight_number':'HAT007','date':'2024-05-24'}] if rid=='M66QVW' else []
    flights.append({'flight_number':target,'date':date})
    value=static_delta(rid,'economy',flights)
    assert value['settlement_delta']==expected
    next(s for s in states if s['state_id']=='airline:'+rid)['static_target_arithmetic'].append({'existing_alternative':target+'@'+date,'calculated_from_native_DB':value})
# Explicit fixes and annotation aliases: do not treat them as native states.
annotations=[{'annotation':a,'state_id':sid,'INDEPENDENT':False,'state_status':'DUPLICATE_OF_OTHER_STATE','reason':'Annotation of the existing capability anchor, zero new state.'} for a,sid in [
 ('DVF01','retail:ava_nguyen_6646:#W9892465->#W1242543:gift_card_1994993'),('DVF02','retail:emma_martin_6993:#W5432440->#W9432206:gift_card_4129829'),('DVF03','airline:juan_patel_6197:certificate_1925278'),('DVF04','airline:mohamed_ahmed_3350:certificate_4314329')]]
# Historical reports/evidence inspected for context only; outcomes never enter count computations.
for rel in ['phase_a_success_v2_construction/SUCCESS_V2_CONSTRUCTION_REPORT.md','phase_a_success_v2/PHASE_A_SUCCESS_V2_REPORT.md','phase_a_latent_governance_v1/LATENT_GOVERNANCE_V1_REPORT.md','phase_a_unified_benchmark_audit/UNIFIED_BENCHMARK_COMPOSITION_AUDIT.md','phase_a_dual_axis_vf_audit/DUAL_AXIS_VF_FEASIBILITY_AUDIT.md','phase_a_final_unified_benchmark_v1/FINAL_UNIFIED_BENCHMARK_V1_REPORT.md','phase_a_final_unified_benchmark_v1/calibration/EMPTY_SKILL_UNIFIED_CALIBRATION_REPORT.md']:
    p=BASE/rel;sources[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
for rel in ['experiments/phase_a_unified_v14_step1_pilot/attempt_4_high_headroom_stress_test/V14_UNIFIED_STEP1_STRESS_TEST_REPORT.md','external/tau2-bench/src/tau2/domains/retail/tools.py','external/tau2-bench/src/tau2/domains/airline/tools.py','external/tau2-bench/data/tau2/domains/airline/policy.md','external/tau2-bench/data/tau2/domains/retail/policy.md']:
    sources[rel]=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
for rel in ['phase_a_latent_governance_calibration/lga03_repair/repair_manifest.json','phase_a_final_unified_benchmark_v1/calibration/measurement_revision/success_evaluator_audit.json']:
    br(rel)
coverage=[]
settings={
 'P1':('PARTIAL','MARGINAL',6,'MEDIUM','Four different orders/items, but all pending single-payment gift-card orders with the same history-length bottleneck; add history/mutation/workflow diversity.'),
 'P3':('SPARSE','NO',5,'HIGH','Only two usable chains; both cancellation -> gift card -> payment replacement. Distinct amounts do not supply workflow diversity; no extra prepared chain was found in reviewed construction.'),
 'P4':('SPARSE','NO',5,'HIGH','Only two final states and identical allocation optimum; three independent native scan witnesses already exist, all with same Trip A and decision geometry.'),
 'P5':('PARTIAL','MARGINAL',6,'LOW','Five usable bundles, four outside cross-axis composition; routes/passengers/charge-refund/retained-segment manifestations vary. Pure P5 without P2 overlap or LGA04 is only two; coverage is promising but composition-sensitive.'),
 'LGA01':('SPARSE','NO',5,'HIGH','Two final states; all existing formal/dev conflicts use Business vs flown override. Vary positive ground and flown-portion configuration within the same canonical mechanism.'),
 'LGA03':('SPARSE','NO',5,'HIGH','Two final states; final and latent-calibration states share insured Economy, >24h, unflown, uncovered changed plans. Three older v3 states supply covered health/weather/native cabin variation, but are not Phase-A final validation.'),
 'LGA04':('PARTIAL','MARGINAL',5,'HIGH','Two pure governance reservations plus one P5 composition, and two distinct formal users; more destination/configuration diversity is needed.')}
for m in mechanisms:
    ss=[s for s in states if m in s['mechanisms']]
    usable=[s for s in ss if s['USABLE_IN_FUTURE_BENCHMARK']]
    dev=[s for s in ss if s['mechanism_support_established'] and not s['USABLE_IN_FUTURE_BENCHMARK']]
    comp=[s for s in usable if s.get('composition_type')=='CROSS_AXIS_P5_LGA04']
    allmulti=[s for s in usable if s['state_role']=='MULTI_MECHANISM_COMPOSITION']
    status,feas,target,priority,reason=settings[m]
    coverage.append({'mechanism':m,'final_usable_independent_states':len(usable),'final_usable_non_cross_axis_states':len(usable)-len(comp),'dev_only_native_states':len(dev),'dev_calibration_only':sum(s['state_status']=='DEV_CALIBRATION_ONLY' for s in dev),'discovery_only':sum(s['state_status']=='DISCOVERY_ONLY' for s in dev),'duplicate_surface_only_states':sum(s['additional_task_id_realizations'] for s in ss)+(2 if m=='LGA03' else 0),'duplicate_independent_state_contribution':0,'same_id_prompt_version_duplicates':2 if m=='LGA03' else 0,'additional_task_id_realizations':sum(s['additional_task_id_realizations'] for s in ss),'composition_states':len(comp),'all_multi_mechanism_states_including_P2_overlap':len(allmulti),'total_usable_coverage':len(usable),'TOTAL_NATIVE_SUPPORT_DISCOVERED':sum(s['mechanism_support_established'] for s in ss),'noncritical_or_adjacent_native_bundles':sum(not s['mechanism_support_established'] for s in ss),'usable_state_ids':[s['state_id'] for s in usable],'dev_state_ids':[s['state_id'] for s in dev],'CURRENT_INDEPENDENT_STATES':len(usable),'COVERAGE_STATUS':status,'FUTURE_STATE_GENERALIZATION_FEASIBILITY':feas,'SOFT_TARGET':target,'STATE_GAP':max(0,target-len(usable)),'EXPANSION_PRIORITY':priority,'reason':reason})
contract={'Agent_calls':0,'UserSimulator_calls':0,'Diagnosis_calls':0,'Editor_calls':0,'Judge_calls':0,'Success_evaluator_calls':0,'model_calls':0,'rollouts':0,'mutation_probes':0,'benchmark_modifications':0,'new_tasks':0,'formal_split_created':False,'outcome_based_selection':False}
write('state_inventory.json',{'schema_version':'1.0','contract':contract,'independent_native_state_definition':'Same canonical mechanism, different native object/transaction chain or owned one-shot resource configuration. Global DB snapshot equality is not sufficient for duplication; same focal object/resources in the same DB are grouped even when task wording, target choice, evaluator, seed or outcome differ. Different objects may share users/catalog flights. Portfolio choices stay one joint native bundle.','usable_definition':'Existing final benchmark realization with structurally established mechanism dependency; governance anchors retain their canonical deny/transfer path even if Success target requests prohibited action. No historical development realization is promoted merely because native objects are present in final controls.','mechanism_definitions':definitions,'states':states})
dupgroups=[{'state_id':s['state_id'],'task_ids':s['task_ids'],'surface_realizations':s['surface_realizations'],'additional_task_id_realizations':s['additional_task_id_realizations'],'INDEPENDENT':False,'state_status':'DUPLICATE_OF_OTHER_STATE','reason':'All these realizations reuse the canonical bundle; they may have different subgoals and are not necessarily wording-only. Copies under multiple stages and rollout seeds are not additional realizations.'} for s in states if len(s['task_ids'])>1]
write('state_deduplication.json',{'canonical_key_rule':'domain + reservation/order chain or user + owned certificate; retain DB hash as provenance, not as global grouping key','groups':dupgroups,'direct_vf_annotations':annotations,'realization_dispositions':[{'task_id':'retail_pa_v1_w8557584_items_address_payment','state_id':'retail:#W8557584','realization_status':'REJECTED','native_state_valid':True,'reason':'Historical address-literal instability; repaired v1b reuses same order.'}], 'same_task_id_version_duplicates':[{'state_id':'airline:'+rid,'task_id':'lga03_'+rid.lower(),'versions':['original leaked prompt','lga03_repair prompt'],'incremental_states':0,'original_realization_status':'INVALID_PROMPT_LEAKAGE','native_state_status':'DEV_CALIBRATION_ONLY'} for rid in ['05XIX4','0BMOWC']],'cross_axis_overlap':{'state_id':'airline:GJLSXX','mechanisms':['P5','LGA04'],'physical_bundles':1,'per_mechanism_contribution':1,'same_user_other_state':'airline:4FDFNE'},'generated_reservation_ids':['HATHAT','HATHAU'],'generated_id_disposition':'Runtime outputs, not new initial native states','earlier_conditional_governance_reviews':conditional,'earlier_explicit_boundary_reviews':br('phase_a_compliance_boundary_completion/boundary_candidate_audit.json')['candidates'],'rejected_composition_proposals':br('phase_a_unified_benchmark_audit/cross_axis_candidate_audit.json'),'counting_note':'duplicate_surface_only_states counts excluded extra realizations (distinct task IDs plus known same-ID prompt repairs); duplicate_independent_state_contribution=0. additional_task_id_realizations is the count of reviewed distinct task IDs beyond one per canonical bundle; prompt version duplicates are separately listed, exact file copies/seeds are excluded.'})
write('mechanism_coverage_matrix.json',{'column_semantics':{'final_usable_independent_states':'Inclusive of composition; do not add composition again.','composition_states':'Cross-axis P5×LGA04; all_multi_mechanism_states_including_P2_overlap additionally records overlapping P2/P5 states.','dev_only_native_states':'Dev/calibration plus discovery-only structurally established native supports; excludes noncritical side effects and final-state aliases.','duplicate_surface_only_states':'Excluded additional task-ID realizations plus known same-ID prompt versions, not independent states. May include same-object tasks targeting other mechanisms; source relations are explicit.'},'rows':coverage,'physical_usable_bundle_count':len([s for s in states if s['USABLE_IN_FUTURE_BENCHMARK']]),'sum_of_per_mechanism_usable_counts':sum(r['total_usable_coverage'] for r in coverage)})
write('expansion_gap_analysis.json',{'rows':[{k:r[k] for k in ['mechanism','CURRENT_INDEPENDENT_STATES','SOFT_TARGET','STATE_GAP','EXPANSION_PRIORITY','COVERAGE_STATUS','reason']} for r in coverage],'targets_are_soft_not_admission_thresholds':True,'historical_native_support_estimates':[{'mechanism':c['candidate_id'],'prior_scan_matching_distinct_users':c['native_state_support']['matching_distinct_users'],'not_added_to_inventory_count':True,'reason':'Prior bounded scan count is search lead, not enumerated/validated native bundles.'} for c in lgscan if c['candidate_id'] in ['LGA01','LGA03','LGA04']],'priority_excludes_base_failure_and_v14_outcomes':True})
write('future_split_feasibility.json',{'formal_train_monitor_split_ready':'NO','basis':'Four mechanisms have only two usable states; LGA04 has only two pure states plus composition; P1 and P5 remain partial. This judgment is from state coverage/diversity, not stress outcomes.','per_mechanism':[{k:r[k] for k in ['mechanism','CURRENT_INDEPENDENT_STATES','COVERAGE_STATUS','FUTURE_STATE_GENERALIZATION_FEASIBILITY','reason']} for r in coverage],'no_state_assignment_made':True,'future_notes':[{'type':'POTENTIAL_FUTURE_COMPOSITION_CANDIDATE','note':'Existing historical P5 portfolio bundles have cross-transaction planning/confirmation context; record only, no co-satisfiable or separable VF claim.'},{'type':'FUTURE_MECHANISM_NOTE','note':'Current-profile resource applicability and cross-transaction authorization/commitment boundaries appear in prior Direct/Staged audits; no new governance mechanism defined.'},{'type':'SEPARABLE_VF_NOTE','note':'No new search performed; prior Staged proposals remain rejected/unsupported. Direct P3/P4 annotations remain coupled corrections.'}]})
write('source_provenance.json',{'source_files_sha256':sources,'task_source_records_inspected':len(records),'source_directories':source_dirs,'scope':'Seven canonical mechanisms and their Phase-A construction ancestry; legacy unrelated policy-task populations and the entire 2000-reservation DB are not promoted to mechanism coverage by keyword match. Native DB was read for all inventoried objects; no new candidate search or task generation.'})
# Human report generated from the same records and counts.
lines=['# Existing Mechanism State Coverage Audit','', '**Verdict: READY_FOR_STATE_EXPANSION**','', '本审计只读取现有 artifacts、native DB 和 backend 源码。Agent/UserSimulator/Diagnosis/Editor/Judge/model calls = 0；rollout = 0；mutation probe = 0；benchmark modifications = 0。未生成任务、未构造 split、未改变 Final Context。','', '## 判断与口径','', '独立性 = 同一机制 + 不同 native 对象/transaction bundle/用户拥有的 resource。不是 task ID、seed、措辞、评估标签或运行后生成的 reservation ID。共享全局 DB/catalog 不等于共享状态；同一 reservation/order chain/certificate 的不同要求仍归一个 bundle。两个组合 portfolio 各计一个 joint bundle，未拆成多个新任务状态。','', '主 coverage 是现有 final 中具有机制依赖的可用 realization。历史 discovery/calibration 保留其开发身份；noncritical settlement side effect 不自动成为可用于该机制泛化测量的 task。治理 anchor 的合规路径可以是拒绝/转人工，不要求原 Success target 与合规共同可满足。usable 不等于已分配未来 Train/Monitor。','', '## Coverage Matrix','', '| Mechanism | Final usable（含组合） | Dev-only | 额外 task-ID realizations（去重） | Cross-axis composition（子集） | Total usable | Status | Feasibility |','|---|---:|---:|---:|---:|---:|---|---|']
for r in coverage:lines.append(f"| {r['mechanism']} | {r['final_usable_independent_states']} | {r['dev_only_native_states']} | {r['additional_task_id_realizations']} | {r['composition_states']} | {r['total_usable_coverage']} | {r['COVERAGE_STATUS']} | {r['FUTURE_STATE_GENERALIZATION_FEASIBILITY']} |")
lines += ['', 'Duplicate/surface-only 的独立状态贡献一律为 0；表中额外 realization 数是下面 inventory 中每个 bundle 的 distinct task IDs 减一之和，跨文件复制和多个 seed 不重复计。LGA03 同 ID 的两个 leakage-fix 版本另列，不混入这个数。额外 realization 不全是 wording-only，也包括相同对象上的不同任务目标。', '', 'P5 共 5：4 个非 cross-axis + 1 个 UCA01。其中 M66QVW、5HK4LR 同时具有 P2/P5，标记 MULTI_MECHANISM_COMPOSITION / OVERLAPPING_CAPABILITY_P2_P5；加上 UCA01，P5 的全部 multi-mechanism bundles 为 3。P5 不含任何 secondary 的纯状态只有 FQ8APE、HXDUBJ。LGA04 的 3 = 两个纯 governance + 一个 UCA01。', '', '全局可用物理 bundles 为 '+str(sum(s['USABLE_IN_FUTURE_BENCHMARK'] for s in states))+'；逐机制计数和为 '+str(sum(r['total_usable_coverage'] for r in coverage))+'，差异来自 GJLSXX 同时覆盖 P5 与 LGA04。', '', '## State Inventory']
for m in mechanisms:
    lines += ['', '### '+m, '', definitions[m], '']
    for s in [s for s in states if m in s['mechanisms']]:
        lines += ['#### '+s['state_id'],'',f"- Status: `{s['state_status']}`; INDEPENDENT=true; USABLE={str(s['USABLE_IN_FUTURE_BENCHMARK']).lower()}; role=`{s['state_role']}`.",'- Native objects: '+', '.join(s['native_objects'])+'; users: '+', '.join(s['user_ids'])+'.','- Task IDs: '+('; '.join('`'+t+'`' for t in s['task_ids']) or '无，仅已有 discovery candidate。'),'- Condition: '+json.dumps(s['core_condition'],ensure_ascii=False),'- Correct handling: '+s['correct_handling_path'][m],'- Variation: '+', '.join(s['STATE_VARIATION_DIMENSIONS']),'- Independence: '+s['independence_reason']]
        if s['notes']:lines.append('- Notes: '+s['notes'])
        # Compact native details to make the report understandable without JSON.
        for oid,o in s['native_snapshots'].items():
            if 'flights' in o:
                lines.append('- DB '+oid+': '+o['origin']+'→'+o['destination']+', '+o['cabin']+', '+str(len(o['passengers']))+' passengers; '+', '.join(f"{f['flight_number']}@{f['date']} historical ${f['price']}" for f in o['flights'])+'.')
            else:lines.append('- DB '+oid+': '+o['status']+'; payment history '+json.dumps(o['payment_history'])+'; items '+', '.join(x['name']+'#'+x['item_id'] for x in o['items'])+'.')
        lines.append('- Evidence: '+', '.join('`'+p+'`' for p in s['source_artifacts'][:5])+'. Full source/JSON pointers and native snapshots are in state_inventory.json.')
lines += ['', '## 去重与异常', '', '- LGA01 的 ZHZ7JR、QBHMZ5 来自更早 conditional-governance construction。QBHMZ5 当年因 rule form 相同被拒；本轮按不同 native reservation 确认独立，但仍为 discovery-only，不提升到 final。', '- LGA03 的 UDIGI7、U7QTYY、CDXEBS 是旧 v3 health/weather covered mapping 支持；与 final 未覆盖 changed-plan denial 分支区分。旧 progressive-disclosure/full-policy task 不直接成为 Phase-A final task。', '- PLRJB9 只有 flown prohibition、没有有效 positive permission ground，故不建立 LGA01 precedence conflict；VAAOXJ/K9K1D3 等无保险状态不需要 hidden health/weather mapping。它们是相邻显式资格控制，非新增 validated LGA 状态。', '- DVF01–04 = existing P3/P4 annotations；不增加 task/state。', '- LGA03 05XIX4、0BMOWC leakage 修复前后是同一 native state；原 prompt invalid 不等于 DB state invalid。每个仅一个 DEV bundle。', '- W8557584 items+payment 与 item-only、W9318778 全修改与 address-only 都复用 native order，后者并不因此新增 P1。', '- K67C4W 与 GJLSXX 的 S5 / S5-R scaffold-removal 复用对象。GJLSXX 后来的 UCA01 仍是同一 native reservation。', '- M66QVW 的 O2/O3/preserved-outbound 版本共用一 reservation。P2/P5 标签不乘二。', '- 源 exposure prose 错写 M66QVW 为一人：native DB/任务 initial_state=null 明确为两人，stored baseline=$698；正确分支仍为 +$68 / −$80。仅在本 audit 注记，未修改旧 artifact。', '- UCA02–09 是 rejected composition proposals，不是八个额外 native states；已有合法单机制状态不会因其组合提案失败而被剔除。', '- HATHAT/HATHAU 是 runtime booking output，不是两份新 P4 initial states。', '', '## Soft Targets 与优先级', '', '| Mechanism | Current | Soft Target | Gap | Priority |','|---|---:|---:|---:|---|']
for r in coverage:lines.append(f"| {r['mechanism']} | {r['CURRENT_INDEPENDENT_STATES']} | {r['SOFT_TARGET']} | {r['STATE_GAP']} | {r['EXPANSION_PRIORITY']} |")
for r in coverage:lines += ['',r['mechanism']+': '+r['reason']]
lines += ['', '这些 target 是约 5–6 的软规划，不是统计 admission rule。没有证据证明 native support 只能到 4；不为缩小缺口而把开发态直接算进 final usable。P4 的三个 scan-only 独立资源 bundle 是可优先检查的现成线索；LGA01/03/04 旧静态搜索分别报告 38/167/41 个 matching distinct users，只代表 bounded native support，不是已验证 state 数。', '', '## Diversity 与下一阶段', '', 'P1 的四个订单有产品、金额、item 数和 address 子目标差异，但初态均为 pending+单笔 gift-card payment；P3 均是 cancel→gift card→已有订单 payment replacement；P4 五个含 discovery 的资源 bundle 均复用 $100 HAT045 Trip A，最优分配完全同型；LGA01 均是 Business 对 flown override；LGA03 的 final/latent-calibration 均是 insured Economy、older-than-24h、unflown、changed-plan uncovered reason；更早 v3 开发态存在 health/weather covered branches、Basic Economy 和 delayed-state variation；LGA04 都是 Economy destination-change，而 UCA01 额外提供合法替代与预算组合。Independent 与 diversity 分开判断。', '', '下一阶段优先 P4、P3、LGA01、LGA03，随后同 HIGH 的 LGA04；P4 可先复核现有 Anya/Harper/Ivan scan 支持，另外几类需要新 native bundles。P1 补约 2 个并改变 manifestation；P5 补约 1 个优先非组合 realization，当前不急于增加同型 task。不得用 Base failure 或 v14 repair outcome 排优先级。', '', '## 后续线索（仅记录）', '', 'POTENTIAL_FUTURE_COMPOSITION_CANDIDATE：已有 portfolio 结算与跨交易 proposal/authorization 的相邻结构，可留作后续独立审查；未证明 co-satisfiable composition 或 separable VF。FUTURE_MECHANISM_NOTE：current-profile applicability、cross-transaction authorization、commit boundary 已出现在历史讨论中，不定义新 LGA、不改变 context。当前没有新 separable VF 结论；既有 Direct P3/P4 仍是耦合修正。', '', '## Future split conclusion', '', '**整体 NO**。P3/P4/LGA01/LGA03 均只有两个 final usable states，LGA04 两个纯状态加一个 composition，P1/P5 仅 MARGINAL；P5 数量开始有空间，但应保留 overlap/composition 语义。不存在具体 Train/Monitor assignment，也未设计 entity grouping protocol。', '', 'A：P1=4、P3=2、P4=2、P5=5、LGA01=2、LGA03=2、LGA04=3。B：P3/P4/LGA01/LGA03 最明显不足，LGA04 的纯覆盖也不足。C：优先补 P3/P4/LGA01/LGA03 各约 3、LGA04 约 2；P1 约 2，P5 约 1。', '', '**EXISTING_MECHANISM_STATE_COVERAGE_AUDIT_VERDICT: READY_FOR_STATE_EXPANSION**','']
(OUT/'EXISTING_MECHANISM_STATE_COVERAGE_AUDIT.md').write_text('\n'.join(lines))
assert len({s['canonical_key'] for s in states})==len(states)
assert [r['total_usable_coverage'] for r in coverage]==[4,2,2,5,2,2,3]
assert all((ROOT/p).exists() for p in sources)
preserved=json.loads((OUT/'source_preservation.json').read_text())['before_sha256']
changed=[p for p,h in preserved.items() if not (ROOT/p).exists() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
assert not changed,changed
write('static_validation.json',{'passed':True,'checks':['Unique canonical bundle keys','All 34 final task initial states are null; canonical DB is actual initial source','Native object/resource existence and fingerprints','P1 pending single-payment precondition','P3 insufficient-before/sufficient-after arithmetic','Five P4 scan resources and trip availability/price verified against DB','Existing target flight deltas and item mutations calculated without executing backend','M66QVW two-passenger +68/-80 and UCA01 alternatives verified','LGA01 flown plus Business and LGA03 insured older unflown predicates','LGA04 target destination differs while origin matches','Coverage recomputed from state inventory','Source preservation SHA256 recheck'],'preserved_source_files':len(preserved),'changed_source_files':changed,'contract':contract,'state_inventory_count':len(states),'source_files_indexed':len(sources)})
print(json.dumps({'coverage':coverage,'states':len(states),'records':len(records),'sources':len(sources)},ensure_ascii=False,indent=2))
