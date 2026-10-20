"""Freeze two real independent learning cases, never call the model here."""
from copy import deepcopy
import json
import fixtures as f
import control as c
from src.skill_evolution.v22 import memory_contract as fix, p1_input
from src.skill_evolution.v22.grouped_update import grouped_messages


def prepare():
    f.OUT.mkdir(exist_ok=False)
    cases=[]; audit=[]; sources={}
    for name,archive in [
        ('r2_revision','08_grouped_continual_fusion_resumed_20261015/rounds/r2'),
    ]:
        f.REAL=f.ROOT/'artifacts/methods/v22'/archive
        payload=f.material(fix.PROFILE)['learn']
        previous=f.material(p1_input.PROFILE)['learn']
        messages=grouped_messages('learn',payload); old=grouped_messages('learn',previous)
        assert p1_input.decode(json.loads(messages[1]['content']))
        assert messages[0]['content']==old[0]['content'].replace(p1_input.PROFILE,fix.PROFILE,1).replace(fix.OLD,fix.NEW)
        norm=deepcopy(payload);norm['update_profile']=previous['update_profile'];norm['binding_sha256']=previous['binding_sha256'];assert norm==previous
        params={'model':'deepseek-flash','temperature':1.0,'max_tokens':65536,'thinking':{'type':'enabled'},'reasoning_effort':'medium','stream':False}
        case={'id':name,'stage':'learn','profile':fix.PROFILE,'parameters':params,'timeout_seconds':600,
              'source_archive':archive,'messages_chars':len(p1_input.compact(messages)),
              'messages_sha256':c.object_digest(messages),'payload_sha256':c.object_digest(payload)}
        assert case['messages_chars']<=400000
        d=f.OUT/'cases'/name;d.mkdir(parents=True)
        for file,value in [('payload.json',payload),('messages.json',messages),('request.json',dict(params,messages=messages)),
            ('criteria.json',{'checks':f.COMMON_CRITERIA+f.CRITERIA['learn']+[
                'Nonempty retirement has EXACT effect_id/index/reason/findings, effect in replace, index active and current findings in delta.',
                'Do not require retirement. Empty history cannot supply a replace or retirement ID.',
                'Evaluate evidence-supported scope and untested residuals separately from JSON/contract validity.',
                'No output repair, no resampling, no official publication.']})]:c.save(d/file,value)
        sources.update(f.source_manifest());cases.append(case)
        audit.append({'case':name,'history_effects':len(payload['memory']),'paired_tasks':len(payload['pairs']),
            'steps':sum(len(x['steps']) for x in payload['runs'].values()),
            'v4_chars':len(p1_input.compact(old)),'v5_chars':case['messages_chars'],
            'added_system_chars':len(messages[0]['content'])-len(old[0]['content']),
            'matched_archived_editor_candidate_diff_plan_runs':True})
    c.save(f.OUT/'protocol.json',{'profile':fix.PROFILE,'rule_version':fix.RULE_VERSION,
        'base_url':'https://api.deepseek.com','model':'deepseek-flash','cases':cases,
        'max_calls':1,'max_http_attempts':1,'max_concurrency':1,'transport_retries':0,'semantic_retries':0,
        'max_completion_tokens_total':65536,'episodes':0,'publication':False,
        'failure_policy':'Keep full raw failures; no output repair, resampling or parameter changes. Independent cases do not consume each other outputs.',
        'freeze_before_calls':True,'judgment':'Contract and natural-language evidence support are separate; no forced retirement or empty result.'})
    c.save(f.OUT/'source_manifest.json',sources);c.save(f.OUT/'input_audit.json',audit)
    print(json.dumps(audit,ensure_ascii=False))


if __name__=='__main__':prepare()
