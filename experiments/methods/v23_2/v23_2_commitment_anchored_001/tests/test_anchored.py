"""Human-authored offline mechanics tests; no generated strategy is endorsed."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from anchored import transform, plan_hash, load_json
from src.skill_evolution.v23 import preconditioner as pc, editor

E=Path(__file__).resolve().parents[1];ROOT=E.parents[3]
@pytest.fixture
def payload():return load_json(E/'fixtures/payload.json')
@pytest.fixture
def single():return load_json(E/'fixtures/single_replace.json')
def prop(payload,edits=None,decision='ready',checks=None):
 return {'plan_sha256':plan_hash(payload['plan']),'decision':decision,'reason':'HUMAN offline test.', 'edits':edits or [],'checks':checks}
def edit(anchor,replacement,op='replace',uid='u1'):
 return dict(update_id=uid,operation=op,anchor_text=anchor,replacement_text=replacement,role='target',basis=['P6:6'],reason='HUMAN mechanics test, no semantic success claim.',depends_on=[])
def preserved(payload,value):
 for audit in value['audit']['updates']:
  uid=audit['update_id'];source=next(u['text'] for u in payload['plan']['updates'] if u['id']==uid).encode()
  if value['effective_plan'] is None:continue
  updates=[u for u in value['effective_plan']['updates'] if u['id']==uid]
  target=(updates[0]['text'] if updates else '').encode()
  for s in audit['preserved_segments']:
   a,b=s['source'];c,d=s['result'];assert source[a:b]==target[c:d]

def test_real_single_replace_preserves_every_unselected_byte(payload,single):
 before=deepcopy(payload);out=transform(payload,single);u=out['effective_plan']['updates'][0]['text'];e=single['edits'][0]
 assert u==payload['plan']['updates'][0]['text'].replace(e['anchor_text'],e['replacement_text'])
 assert 'sampled once' not in u and payload==before
 preserved(payload,out)
 assert out['preconditioner']['adjustments'][0]['to']==[{'id':'u1','text':u}]
 assert set(out['preconditioner']['adjustments'][0])=={'from','to','basis','reason'}
 assert pc.compile_effective_plan(out['preconditioner'],payload)==out['effective_plan']

def test_target_with_supporting_dependency(payload):
 p=load_json(E/'fixtures/target_supporting.json');out=transform(payload,p);preserved(payload,out)
 assert len(out['audit']['updates'][0]['edits'])==2
 for e in p['edits']:assert e['replacement_text'] in out['effective_plan']['updates'][0]['text']
 assert out['audit']['updates'][0]['edits'][0]['depends_on']==[0] # source order differs from proposal order
 assert out==transform(payload,p)

def test_cross_update_goal_checks_and_real_editor_handoff(payload,single):
 out=transform(payload,single);plan=out['effective_plan']
 assert plan['updates'][1]==payload['plan']['updates'][1]
 assert plan['goal']==payload['plan']['goal'] and plan['checks']==payload['plan']['checks']
 d=ROOT/'artifacts/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001'
 saved=load_json(d/'input.json');saved.update(diagnosis=load_json(d/'diagnosis.json'),memory=payload['memory'],preconditioner=out['preconditioner'],effective_plan=plan)
 assert pc.preconditioner_input(saved)==payload
 assert editor.editor_input(saved)=={'parent':payload['parent'],'plan':plan} # pure adapter only

def test_large_edit_has_no_length_limit(payload):
 out=transform(payload,load_json(E/'fixtures/large_replace.json'))
 assert len(out['effective_plan']['updates'][0]['text'])>len(payload['plan']['updates'][0]['text'])
 assert out['audit']['updates'][0]['preserved_segments']==[] # whole-text selection has no protected remainder

@pytest.mark.parametrize('operation',['insert_before','insert_after','delete'])
def test_unicode_crlf_insert_delete_and_preservation(payload,operation):
 payload['plan']['updates'][0]['text']='前🙂\r\n唯一锚点\r\n保留  ' # synthetic text using valid real refs
 replacement='' if operation=='delete' else '新增é'
 p=prop(payload,[edit('唯一锚点',replacement,operation)])
 value=transform(payload,p);preserved(payload,value)
 expected={'delete':'前🙂\r\n\r\n保留  ','insert_before':'前🙂\r\n新增é唯一锚点\r\n保留  ','insert_after':'前🙂\r\n唯一锚点新增é\r\n保留  '}[operation]
 assert value['effective_plan']['updates'][0]['text']==expected

def test_multi_edits_order_invariant_text_and_original_snapshot(payload):
 payload['plan']['updates'][0]['text']='alpha beta gamma'
 edits=[edit('alpha','beta'),edit('beta','delta')]
 a=transform(payload,prop(payload,edits));b=transform(payload,prop(payload,list(reversed(edits))))
 assert a['effective_plan']==b['effective_plan']
 assert a['effective_plan']['updates'][0]['text']=='beta delta gamma' # second edit matched original beta
 with pytest.raises(ValueError,match='anchor_missing'):
  transform(payload,prop(payload,[edit('alpha','created'),edit('created','bad')]))

@pytest.mark.parametrize('kind,match',[
 ('missing','anchor_missing'),('ambiguous','anchor_ambiguous'),('overlapping_occurrence','anchor_ambiguous'),
 ('overlap','anchor_or_insertion_conflict'),('same_insertion','anchor_or_insertion_conflict'),
 ('boundary_insertion','anchor_or_insertion_conflict'),('unknown_uid','unknown_update_id'),
 ('stale','stale_plan_hash'),('op','unsupported_operation'),('empty_anchor','Invalid anchor_text'),
 ('whitespace_anchor','Invalid anchor_text'),('goal','unexpected fields'),('bad_basis','invalid references'),
 ('empty_basis','invalid references'),('duplicate_basis','duplicate references'),('nested_basis','unexpected fields'),
 ('checks','check.update_ids: invalid references'),('empty_replacement','Invalid replacement_text'),('delete_nonempty','delete_requires'),
 ('role','unsupported_role'),('support_no_dependency','supporting_requires'),('self_dependency','invalid_dependency_index'),
 ('bad_dependency','invalid_dependency_index'),('cycle','dependency_must_be_root_edit'),
 ('nonroot_dependency','dependency_must_be_root_edit'),('bool_dependency','invalid_dependencies'),
 ('independent_dependency','only_supporting'),('identical','use_keep'),('bad_decision','invalid_decision'),
 ('prose_reference','unavailable evidence reference'),('empty_reason','Invalid edit.reason'),
])
def test_invalid_edits_fail_closed(payload,single,kind,match):
 p=deepcopy(single);e=p['edits'][0]
 if kind=='missing':e['anchor_text']='missing literal'
 elif kind in ('ambiguous','overlapping_occurrence'):
  payload['plan']['updates'][0]['text']='aaa' if kind=='overlapping_occurrence' else 'same same'
  p['plan_sha256']=plan_hash(payload['plan']);e['anchor_text']='aa' if kind=='overlapping_occurrence' else 'same'
 elif kind=='overlap':p['edits'].append(edit('series is exhausted','other'))
 elif kind=='same_insertion':p['edits']=[edit('This is coverage','x','insert_before'),edit('This is coverage','y','insert_after')]
 elif kind=='boundary_insertion':
  payload['plan']['updates'][0]['text']='alpha beta';p=prop(payload,[edit('alpha','x','insert_after'),edit(' beta','z')])
 elif kind=='unknown_uid':e['update_id']='u404'
 elif kind=='stale':payload['plan']['goal']+=' changed'
 elif kind=='op':e['operation']='fuzzy_replace'
 elif kind=='empty_anchor':e['anchor_text']=''
 elif kind=='whitespace_anchor':e['anchor_text']=' '
 elif kind=='goal':p['goal']='changed'
 elif kind=='bad_basis':e['basis']=['M999']
 elif kind=='empty_basis':e['basis']=[]
 elif kind=='duplicate_basis':e['basis']=['M6','M6']
 elif kind=='nested_basis':e['to']={'text':'ignored','basis':['M6']}
 elif kind=='checks':p['checks']=[{'id':'cnew','update_ids':['u404'],'question':'Does it work?'}]
 elif kind=='empty_replacement':e['replacement_text']=' '
 elif kind=='delete_nonempty':e['operation']='delete'
 elif kind=='role':e['role']='anything'
 elif kind=='support_no_dependency':e['role']='supporting'
 elif kind=='self_dependency':e.update(role='supporting',depends_on=[0])
 elif kind=='bad_dependency':e.update(role='supporting',depends_on=[9])
 elif kind in ('cycle','nonroot_dependency'):
  e.update(role='supporting',depends_on=[1]);p['edits'].append({**edit('This is coverage','Coverage'), 'role':'supporting','depends_on':[0]})
 elif kind=='bool_dependency':e.update(role='supporting',depends_on=[True])
 elif kind=='independent_dependency':e.update(role='independent',depends_on=[0])
 elif kind=='identical':e['replacement_text']=e['anchor_text']
 elif kind=='bad_decision':p['decision']='accept'
 elif kind=='prose_reference':e['reason']='M999 proves this.'
 elif kind=='empty_reason':e['reason']=' '
 with pytest.raises(ValueError,match=match):transform(payload,p)


def test_partial_withdraw_checks_must_be_explicit(payload):
 p=prop(payload,[edit(payload['plan']['updates'][0]['text'],'','delete')])
 with pytest.raises(ValueError):transform(payload,p)
 p['checks']=[];out=transform(payload,p)
 assert out['preconditioner']['adjustments'][0]['to']==[]
 assert out['effective_plan']['updates']==[payload['plan']['updates'][1]]

def test_keep_need_evidence_no_change_are_distinct(payload):
 keep=transform(payload,prop(payload));assert keep['effective_plan']==payload['plan']
 stop=transform(payload,prop(payload,decision='need_evidence'));assert stop['effective_plan'] is None
 edits=[edit(u['text'],'','delete',u['id']) for u in payload['plan']['updates']]
 none=transform(payload,prop(payload,edits,decision='no_change',checks=[]));assert none['effective_plan'] is None
 assert len(none['preconditioner']['adjustments'])==len(edits)
 for p in [prop(payload,decision='no_change'),prop(payload,edits),prop(payload,edits,decision='need_evidence'),prop(payload,decision='need_evidence',checks=[])]:
  with pytest.raises(ValueError):transform(payload,p)

def test_partial_deletes_cannot_silently_withdraw(payload):
 payload['plan']['updates'][0]['text']='alpha beta'
 p=prop(payload,[edit('alpha ','','delete'),edit('beta','','delete')],checks=[])
 with pytest.raises(ValueError,match='explicit_whole_delete'):transform(payload,p)

def test_semantic_risk_is_structurally_accepted_and_exposed(payload):
 p=load_json(E/'fixtures/semantic_risk.json');out=transform(payload,p);preserved(payload,out)
 assert 'each receptacle category has been sampled once' in out['effective_plan']['updates'][0]['text']
 assert out['audit']['semantic_validity']=='not_evaluated'
 assert out['audit']['updates'][0]['edits'][0]['replacement_text']==p['edits'][0]['replacement_text']
 assert 'sampled once' in out['audit']['updates'][0]['diff']

def test_duplicate_json_rejected(tmp_path):
 p=tmp_path/'bad.json';p.write_text('{"edits":[],"edits":[1]}')
 with pytest.raises(ValueError,match='duplicate_json_key'):load_json(p)

def test_contract_schema_rejects_manually_invalid_adjustment(payload):
 p={'decision':'ready','reason':'HUMAN invalid shape','adjustments':[{'from':['u1'],'to':[{'id':'u1','text':'Text','basis':['P6:6']}],'basis':['P6:6'],'reason':'Test'}],'checks':None}
 with pytest.raises(ValueError,match='Replacement Update'):pc.compile_effective_plan(p,payload)

@pytest.mark.parametrize('field',['text','checks','basis','order'])
def test_hash_covers_all_original_plan_fields(payload,single,field):
 if field=='text':payload['plan']['updates'][0]['text']+=' '
 elif field=='checks':payload['plan']['checks']=[]
 elif field=='basis':payload['plan']['updates'][0]['basis'].reverse()
 else:payload['plan']['updates'].reverse()
 with pytest.raises(ValueError,match='stale_plan_hash'):transform(payload,single)

def test_canonical_hash_ignores_object_key_order(payload):
 plan=payload['plan'];assert plan_hash(plan)==plan_hash(dict(reversed(list(plan.items()))))

def test_multiple_updates_and_supporting_edge(payload):
 a=edit('This is coverage','This supports coverage')
 b=edit('Do not spend steps','Avoid spending steps',uid='u2');b.update(role='supporting',depends_on=[0])
 p=prop(payload,[a,b]);out=transform(payload,p);preserved(payload,out)
 assert [x['from'] for x in out['preconditioner']['adjustments']]==[['u1'],['u2']]
 assert out['effective_plan']['goal']==payload['plan']['goal']

def test_future_draft_renders_without_analysis_answers(payload):
 from src.skill_evolution.v23.prompts import render_prompt
 p=E.parent/'v23_2_preconditioner_memory_ab_001'
 draft=(E/'config/anchored_prompt_draft.md').read_text().replace('{{plan_sha256}}',plan_hash(payload['plan']))
 rendered=render_prompt(draft,load_json(p/'config/background.json'))
 assert '{{' not in rendered and plan_hash(payload['plan']) in rendered
 assert 'S01' not in rendered and 'M6' not in rendered and 'R05' not in rendered
 assert 'merge, or split related Updates' not in rendered
