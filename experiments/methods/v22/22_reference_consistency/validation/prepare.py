"""Freeze one complete 08 R2 probe, without changing its execution evidence."""
from copy import deepcopy
import json
import fixtures as f
import control as c
from src.skill_evolution.v22 import reference_rules as r, memory_contract, p1_input
from src.skill_evolution.v22.grouped_update import grouped_messages, prepare_grouped_learning


def prepare():
    original=f.material(memory_contract.PROFILE)
    root=f.REAL
    context,grouping,plan,candidate,gate,editor=[f.read(root/name) for name in [
        'context.json','grouping.json','execution_plan.json','candidate.json','gate.json','outputs/main_editor.json']]
    parents,candidates=[[f.read(row['trajectory']) for row in f.read(root/name)]
                        for name in ['parent_sources.json','candidate_sources.json']]
    wire=r.convert('editor',editor,original['editor'],outbound=True)
    payload=prepare_grouped_learning(context,grouping,plan,candidate,parents,candidates,gate,editor=wire,profile=r.PROFILE)
    prior=original['learn']
    for key in ['parent','candidate','actual_diff','plan','runs','pairs','memory','grouping','command_sets','sources']:
        assert payload[key]==prior[key],key
    assert payload['update_context']['editor']['mappings']==wire['mappings']
    messages=grouped_messages('learn',payload);old=grouped_messages('learn',prior)
    decoded=p1_input.decode(json.loads(messages[1]['content']))
    assert set(decoded['reference_contract']['about_objects'])==set(r.learning_objects(payload))
    assert p1_input.decode(p1_input.encode(decoded))==decoded
    params={'model':'deepseek-flash','temperature':1.0,'max_tokens':65536,'thinking':{'type':'enabled'},'reasoning_effort':'medium','stream':False}
    case={'id':'r2_references','stage':'learn','profile':r.PROFILE,'parameters':params,'timeout_seconds':600,
          'source_archive':str(root.relative_to(f.ROOT)), 'messages_chars':len(p1_input.compact(messages)),
          'messages_sha256':c.object_digest(messages),'payload_sha256':c.object_digest(payload)}
    assert case['messages_chars']<400000
    d=f.OUT/'cases'/case['id'];d.mkdir(parents=True,exist_ok=False)
    for filename,value in [('payload.json',payload),('messages.json',messages),('request.json',dict(params,messages=messages)),
                          ('criteria.json',{'checks':f.CRITERIA['learn']+[
                              'Full JSON and whole effective-learning contract must pass unchanged evidence/retirement semantics.',
                              'about must use the exact generated object catalog; refs remains current source keys. No alias repair.',
                              'Separate evidence semantics from reference/format validity; no official publication or environment calls.']})]:c.save(d/filename,value)
    c.save(f.OUT/'protocol.json',{'profile':r.PROFILE,'reference_version':r.VERSION,'base_url':'https://api.deepseek.com',
        'model':'deepseek-flash','cases':[case],'max_calls':1,'authorized_ceiling':2,'max_http_attempts':1,
        'max_concurrency':1,'max_completion_tokens_total':65536,'transport_retries':0,'semantic_retries':0,
        'episodes':0,'publication':False,'failure_policy':'Preserve failures without repair or resampling; a second request is not automatic.'})
    c.save(f.OUT/'source_manifest.json',f.source_manifest())
    audit={'old_chars':len(p1_input.compact(old)),'new_chars':case['messages_chars'],
           'system_delta_chars':len(messages[0]['content'])-len(old[0]['content']),
           'pairs':len(payload['pairs']),'steps':sum(len(x['steps']) for x in payload['runs'].values()),
           'all_execution_facts_and_memory_identical':True,'about_objects':decoded['reference_contract']['about_objects']}
    c.save(f.OUT/'input_audit.json',audit);print(json.dumps(audit,ensure_ascii=False))

if __name__=='__main__':prepare()
