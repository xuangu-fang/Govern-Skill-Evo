"""Engineering fixtures test mechanics, not empirical attribution accuracy."""
from copy import deepcopy
from dataclasses import replace
import shutil
import pytest

from src.skill_evolution import attribution_pairs_v19 as pair
from src.skill_evolution.edit_tracking_v19 import encode, parse
from src.skill_evolution.evolution_replay_v19 import _load, _save
from src.skill_evolution.memory_store_v19 import initialize_memory, commit_round_memory, load_memory
from src.skill_evolution.memory_retrieval_v19 import retrieve_memory
from tests.skill_evolution.test_attribution_v19 import prepared, complete
from tests.skill_evolution.test_evolution_replay_v19 import scenario
from tests.skill_evolution.test_edit_tracking_v19 import case
from tests.skill_evolution.test_memory_v19 import receipt, make_round


def raw(packet, *, status='ATTRIBUTED', ids=None):
    observation = {'status': status, 'edit_ids': ([e['edit_id'] for e in packet['edits']] if ids is None else ids),
        **{role+'_evidence_refs': [next(e['evidence_ref'] for e in packet['pair'][role]['events']
                                       if e['actor'] == 'assistant')] for role in ('parent', 'candidate')},
        'behavior_comparison': 'Observed the stated behavior on both sides.', 'reason': 'Tentative behavioral association.'}
    return encode({'schema_version': pair.RESPONSE_SCHEMA, 'observations': [observation]})


def transport(request):
    return complete(raw(parse(request['user_prompt'])))


def test_packet_complete_local_and_safe(prepared):
    _, _, data = prepared
    packets = pair.build_pair_packets(data)
    assert len(packets) == 3
    for packet, original in zip(packets, data['pairs']):
        for role in ('parent', 'candidate'):
            assert [{**e, 'evidence_ref': packet['evidence_aliases'][e['evidence_ref']]}
                    for e in packet['pair'][role]['events']] == original[role]['events']
        assert len(packet['edits']) == len(data['edits'])
        assert {c['context_ref'] for c in packet['contexts']} == {original[r]['context_ref'] for r in ('parent', 'candidate')}
        for secret in ('PRIVATE-', 'HIDDEN_', 'private_database', 'expected_action', 'gate_decision'):
            assert secret not in encode(packet)
    assert pair.profile(data, pair.settings())['over_budget_count'] == 0


def test_mixed_unattributed_empty_and_aliases(prepared):
    packet = pair.build_pair_packets(prepared[2])[0]
    attributed = parse(raw(packet))
    unattributed = parse(raw(packet, status='UNATTRIBUTED', ids=[]))['observations'][0]
    attributed['observations'].append(unattributed)
    result = pair.validate_pair(encode(attributed), packet)
    assert len(result['observations']) == 2
    assert all(o['parent_evidence_refs'][0].startswith('PAIR/') for o in result['observations'])
    assert pair.validate_pair(encode({'schema_version':pair.RESPONSE_SCHEMA,'observations':[]}), packet)['observations'] == []


@pytest.mark.parametrize('change', [
    lambda o: o.update(status='UNKNOWN'), lambda o: o.update(edit_ids=[]),
    lambda o: o.update(status='UNATTRIBUTED'), lambda o: o.update(parent_evidence_refs=['C2']),
    lambda o: o.update(parent_evidence_refs=['PAIR/unknown/PARENT/E0001']),
    lambda o: o.update(parent_evidence_refs=[]), lambda o: o.update(reason=''),
    lambda o: o.update(suggested_followup='REVISE'), lambda o: o.update(parent_evidence_refs=['P1']),
])
def test_reference_and_status_contract(prepared, change):
    packet = pair.build_pair_packets(prepared[2])[0]; value = parse(raw(packet))
    change(value['observations'][0])
    with pytest.raises(pair.AttributionRejected): pair.validate_pair(encode(value), packet)


def test_aggregate_signs_joint_and_no_forced_credit(prepared):
    data = deepcopy(prepared[2]); second = deepcopy(data['edits'][0]); second['edit_id'] = 'EDIT/second'
    data['edits'].append(second)
    packets = pair.build_pair_packets(data)
    results = [pair.validate_pair(raw(p), p) for p in packets]
    batch = pair.aggregate(data, results).payload
    assert len(batch['records']) == 1
    record = batch['records'][0]
    assert len(record['edit_ids']) == 2 and 'effect' not in record
    assert record['associated_pair_outcome_counts']['success_delta'] == {'-1':1,'0':1,'1':1}
    assert 'suggested_followup' not in record
    # Multiple observations of one pair must not multiply outcome credit.
    results[0]['observations'].append({**results[0]['observations'][0], 'observation_id':'OBSERVATION/another'})
    assert pair.aggregate(data, results).payload['records'][0]['associated_pair_outcome_counts'] == record['associated_pair_outcome_counts']
    only_unknown = [pair.validate_pair(raw(p, status='UNATTRIBUTED', ids=[]), p) for p in packets]
    assert all('effect' not in r and not r['observations'] for r in pair.aggregate(data, only_unknown).payload['records'])
    with pytest.raises(pair.AttributionRejected): pair.aggregate(data, results[:2])


@pytest.mark.parametrize('indices,effect', [([0],'BENEFICIAL'),([1],'HARMFUL'),([2],'NO_OBSERVED_EFFECT'),([], 'UNKNOWN')])
def test_aggregate_directions(prepared, indices, effect):
    data = prepared[2]; packets = pair.build_pair_packets(data)
    results = [pair.validate_pair(raw(p) if i in indices else encode({'schema_version':pair.RESPONSE_SCHEMA,'observations':[]}), p)
               for i,p in enumerate(packets)]
    assert 'effect' not in pair.aggregate(data, results).payload['records'][0]
    assert pair.aggregate(data, results, facts_only=False).payload['records'][0]['effect'] == effect


def test_opposing_dimensions_mixed(prepared):
    data = deepcopy(prepared[2]); data['pairs'][0]['outcome_transition']['compliant_delta'] = -1
    packets = pair.build_pair_packets(data)
    results = [pair.validate_pair(raw(p) if i==0 else encode({'schema_version':pair.RESPONSE_SCHEMA,'observations':[]}), p)
               for i,p in enumerate(packets)]
    assert 'effect' not in pair.aggregate(data, results).payload['records'][0]


def test_runner_resume_and_tamper(prepared, tmp_path):
    ledger, kwargs, data = prepared; directory = tmp_path/'attr'; calls=[]
    def model(request): calls.append(request); return transport(request)
    result = pair.run_attribution(ledger, **kwargs, artifact_dir=directory, transport=model)
    assert len(calls) == 3 and result == pair.load_attribution(ledger, **kwargs, artifact_dir=directory)
    assert pair.run_attribution(ledger, **kwargs, artifact_dir=directory, transport=model, resume=True) == result
    assert len(calls) == 3
    _save(directory/'attributions.json', {})
    with pytest.raises(pair.AttributionRejected, match='digest'): pair.load_complete(directory, data)


def test_one_repair_and_all_raw_responses_saved(prepared, tmp_path):
    ledger, kwargs, _ = prepared; directory = tmp_path/'attr'; calls=[]
    def model(request):
        calls.append(request)
        if request.get('repair_protocol')!='contract_repair_v19.2': return complete('{}')
        packet = parse(request['user_prompt'])['original_input']
        return complete(raw(packet))
    pair.run_attribution(ledger, **kwargs, artifact_dir=directory, transport=model)
    assert len(calls) == 6
    assert all(a['repair'] and a['response']['raw_response'] == '{}' for a in _load(directory/'pair-audit.json'))
    pair.run_attribution(ledger, **kwargs, artifact_dir=directory, transport=model, resume=True)
    assert len(calls) == 6


def test_repair_failure_is_not_unattributed(prepared, tmp_path):
    ledger, kwargs, _ = prepared; directory = tmp_path/'attr'; calls=[]
    def model(request): calls.append(request); return complete('{}')
    with pytest.raises(pair.AttributionRejected): pair.run_attribution(ledger, **kwargs, artifact_dir=directory, transport=model)
    assert len(calls) == 6 and not (directory/'attributions.json').exists()
    assert len(list(directory.glob('pairs/*/repair/contract_rejection.json'))) == 3
    with pytest.raises(pair.AttributionRejected): pair.run_attribution(ledger, **kwargs, artifact_dir=directory, transport=model, resume=True)
    assert len(calls) == 6


def test_timeout_isolation_explicit_recovery(prepared, tmp_path):
    ledger, kwargs, data = prepared; directory = tmp_path/'attr'; calls=[]
    bad = data['pairs'][1]['pair_id']
    def model(request):
        packet = parse(request['user_prompt']); calls.append(packet['pair']['pair_id'])
        if packet['pair']['pair_id'] == bad: raise TimeoutError('test timeout')
        return transport(request)
    with pytest.raises(pair.AttributionRejected): pair.run_attribution(ledger, **kwargs, artifact_dir=directory, transport=model)
    assert len(calls) == 3 and not (directory/'attributions.json').exists()
    assert len(list(directory.glob('pairs/*/result.json'))) == 2
    with pytest.raises(pair.AttributionRejected): pair.run_attribution(ledger, **kwargs, artifact_dir=directory, transport=model, resume=True)
    assert len(calls) == 3
    archived = pair.archive_uncertain_call(directory, pair_id=bad)
    assert (archived/'request.json').exists() and (archived/'receipt.json').exists()
    finished=[]
    def good(request): finished.append(request); return transport(request)
    pair.run_attribution(ledger, **kwargs, artifact_dir=directory, transport=good, resume=True)
    assert len(finished) == 1


def test_budget_and_length_do_not_repair(prepared, tmp_path):
    ledger, kwargs, _ = prepared; calls=[]
    def model(request): calls.append(request); return {**complete('{}'),'finish_reason':'length'}
    with pytest.raises(pair.AttributionRejected): pair.run_attribution(ledger, **kwargs, artifact_dir=tmp_path/'budget',
        config=pair.settings(max_input_tokens=1), transport=model)
    assert not calls
    with pytest.raises(pair.AttributionRejected): pair.run_attribution(ledger, **kwargs, artifact_dir=tmp_path/'length', transport=model)
    assert len(calls)==3 and not list((tmp_path/'length').glob('pairs/*/repair'))


@pytest.mark.parametrize('decision', ['ACCEPT','RETAIN'])
def test_memory_roundtrip_and_legacy_chain(prepared, case, tmp_path, decision, monkeypatch):
    ledger, kwargs, _ = prepared; directory = tmp_path/'attr'; store = tmp_path/'memory'
    initialize_memory(store_dir=store, run_id='test-run', initial_skill=ledger.source['editor']['parent_skill'])
    pair.run_attribution(ledger, **kwargs, artifact_dir=directory, transport=transport)
    ref=commit_round_memory(ledger, **kwargs, attribution_dir=directory, store_dir=store, expected_head_ref=None,
                           gate_result=receipt(ledger,decision))
    assert commit_round_memory(ledger, **kwargs, attribution_dir=directory, store_dir=store, expected_head_ref=None,
                           gate_result=receipt(ledger,decision)) == ref
    snap=load_memory(store)
    assert snap.rounds[0]['attribution']['schema_version']=='attribution_batch_v19.3'
    second, options=make_round(case,tmp_path/'round2',history=snap.history,parent=snap.head['retained_skill'],round_id='r2')
    commit_round_memory(second, **options, store_dir=store, expected_head_ref=ref)
    shutil.rmtree(directory)
    monkeypatch.setattr(pair,'SYSTEM','future prompt must not rewrite archived history')
    snap=load_memory(store)
    assert snap.head['revision']==2
    assert retrieve_memory(store_dir=store,current_parent=snap.head['retained_skill'])


def test_new_campaign_default_and_two_rounds(tmp_path):
    from tests.skill_evolution.test_local_campaign_v19 import transports, Evolution, Monitor
    from collections import Counter
    from src.skill_evolution.campaign_v19 import campaign_config, run_campaign_v19
    calls=Counter()
    def model(request):
        calls['pair']+=1
        for secret in ('PRIVATE-MONITOR','NEVER_LEARN_MONITOR_SECRET','PRIVATE_EXPECTED_ACTION'):
            assert secret not in request['user_prompt']
        return transport(request)
    kw=dict(output=tmp_path/'campaign',config=campaign_config(pilot=True,max_workers=2,generation_protocol='local'),
        run_id='engineering-run',initial_skill='- Parent\n',evolution_backend=Evolution(),monitor_backend=Monitor(),
        transports=replace(transports(calls),attribution=model))
    result=run_campaign_v19(**kw)
    assert result['committed_rounds']==2
    snap=load_memory(kw['output']/'memory')
    assert all(r['attribution']['schema_version']=='attribution_batch_v19.3' for r in snap.rounds)
    before=calls.copy(); assert run_campaign_v19(**kw,resume=True)==result; assert calls==before


def test_unattributed_regression_is_context_not_edit_harm(prepared):
    from src.skill_evolution.attribution_semantics_v19 import record_facts
    data=deepcopy(prepared[2]);packets=pair.build_pair_packets(data)
    results=[pair.validate_pair(raw(p),p) for p in packets]
    extra=pair.validate_pair(raw(packets[1],status='UNATTRIBUTED',ids=[]),packets[1])['observations'][0]
    results[1]['observations'].append(extra)
    batch=pair.aggregate(data,results).payload
    record=batch['records'][0]
    assert 'effect' not in record
    assert record['associated_pair_outcome_counts']['success_delta']['-1']==1
    assert record['unattributed_context']==[extra]
    assert record['unattributed_context'][0]['edit_ids']==[]
    assert record_facts(record,batch)==record
    old=pair.aggregate(data,results,facts_only=False).payload
    assert record_facts(old['records'][0],old)==record


@pytest.mark.parametrize('empty_role',['parent','candidate'])
def test_unattributed_one_sided_evidence(prepared,empty_role):
    packet=pair.build_pair_packets(prepared[2])[0]
    value=parse(raw(packet,status='UNATTRIBUTED',ids=[]))
    obs=value['observations'][0];obs[empty_role+'_evidence_refs']=[]
    result=pair.validate_pair(encode(value),packet)
    assert result['observations'][0][empty_role+'_evidence_refs']==[]
    other='candidate' if empty_role=='parent' else 'parent'
    assert result['observations'][0][other+'_evidence_refs']
    obs[other+'_evidence_refs']=[]
    with pytest.raises(pair.AttributionRejected,match='at least one side'):
        pair.validate_pair(encode(value),packet)


@pytest.mark.parametrize('bad',['missing','unknown','duplicate','wrong_side'])
def test_one_sided_still_requires_fields_and_valid_refs(prepared,bad):
    packet=pair.build_pair_packets(prepared[2])[0]
    value=parse(raw(packet,status='UNATTRIBUTED',ids=[]));obs=value['observations'][0]
    obs['parent_evidence_refs']=[]
    if bad=='missing':del obs['parent_evidence_refs']
    elif bad=='unknown':obs['candidate_evidence_refs']=['C999999']
    elif bad=='duplicate':obs['candidate_evidence_refs']*=2
    else:obs['candidate_evidence_refs']=parse(raw(packet))['observations'][0]['parent_evidence_refs']
    with pytest.raises(pair.AttributionRejected):pair.validate_pair(encode(value),packet)
