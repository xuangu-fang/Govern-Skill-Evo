"""Strict content-only evidence. Raw provider responses never enter this codec."""
from copy import deepcopy
import re
from ...facts import require, text
from . import protocol as p
from .scoring import score


def validate_envelope(record):
    p.fields(record,('schema','run_id','task_id','task','execution','provenance'),'Record')
    require(record['schema']==p.RECORD_VERSION,'Unknown LMB record schema')
    task=p.validate_task(record['task']); require(task['id']==record['task_id'],'Task identity differs')
    e=record['execution']; pr=record['provenance']
    p.fields(pr,('batch_id','role','case_sha256','task_context_sha256','scorer','record_sha256'),'Provenance')
    text(pr['batch_id'],'batch ID')
    require(record['run_id']==pr['batch_id']+':'+p.digest(record['task_id']),'Run identity differs')
    require(pr['role'] in ('parent','candidate','evaluation'),'Invalid role')
    require((pr['role']=='evaluation')==(task['split']=='test'),'Test/optimization role mismatch')
    require(pr['scorer']==p.EM_GATE,'Scorer identity differs')
    require(pr['task_context_sha256']==p.digest(p.messages(task,None)),'Task context differs')
    require(isinstance(pr['case_sha256'],str) and re.fullmatch('[0-9a-f]{64}',pr['case_sha256']),'Invalid source hash')
    require(pr['record_sha256']==p.digest(e),'Execution checksum differs')
    p.fields(e,('skill','actor','initial_messages','content','termination','answer','metrics','api_requests','usage_records'),'Execution')
    require(e['skill'] is None or isinstance(e['skill'],str),'Invalid Skill')
    p.background(e['actor'])
    require(p.equal(e['initial_messages'],p.messages(task,e['skill'])),'Actor input differs')
    require(e['termination'] == 'stop' and isinstance(e['content'],str),'Incomplete execution')
    answer,metrics=score(e['content'],task['choices'],e['answer']['correct_label'])
    require(p.equal(e['answer'],answer) and p.equal(e['metrics'],metrics),'Derived answer/score differs from content')
    p.integer(e['api_requests'],'api requests',1); require(e['api_requests']<=6,'Actor attempt budget exceeded')
    require(isinstance(e['usage_records'],list) and len(e['usage_records'])==e['api_requests'],'Usage/request count differs')
    for usage in e['usage_records']:
        p.fields(usage,('input_tokens','output_tokens','total_tokens','reasoning_tokens'),'Usage')
        for value in usage.values(): require(value is None or type(value) is int and value>=0,'Invalid usage')
    return record


def parent_text(record): return record['execution']['skill']


def run_references(run):
    return {run['ref'],run['initial']['ref'],run['outcome']['ref'],*[a['ref'] for a in run['attempts']]}


def validate_run(run):
    p.fields(run,('ref','task_id','run_id','initial','attempts','outcome'),'Run')
    ref=run['ref']; require(isinstance(ref,str) and re.fullmatch(r'[PQ][1-9]\d*',ref),'Invalid run reference')
    text(run['task_id'],'task ID');text(run['run_id'],'run ID')
    initial=run['initial']; p.fields(initial,('ref','task','messages'),'Initial')
    require(initial['ref']==ref+':0','Initial reference differs')
    p.fields(initial['task'],('question','choices'),'Visible task')
    text(initial['task']['question'],'question');p.validate_choices(initial['task']['choices'])
    messages=initial['messages']
    require(isinstance(messages,list) and len(messages)==2,'Invalid initial messages')
    for role,m in zip(('system','user'),messages):
        p.fields(m,('role','content'),'Message'); require(m['role']==role and isinstance(m['content'],str),'Invalid message')
    require(messages[1]==p.messages(initial['task'],None)[1],'Visible task message differs')
    require(isinstance(run['attempts'],list) and len(run['attempts'])==1,'Only one model round is allowed')
    a=run['attempts'][0]; p.fields(a,('ref','request_context','request_messages','assistant'),'Round')
    require(a['ref']==ref+':1' and a['request_context']==p.FORMAL_CONTEXT,'Round reference/context differs')
    require(p.equal(a['request_messages'],messages),'Formal request differs')
    p.fields(a['assistant'],('role','content'),'Assistant')
    require(a['assistant']['role']=='assistant' and isinstance(a['assistant']['content'],str),'Invalid assistant')
    o=run['outcome'];p.fields(o,('ref','status','termination','answer','model_rounds','tool_calls','api_requests','score'),'Outcome')
    require(o['ref']==ref+':outcome' and o['status']=='completed' and o['termination'] == 'stop','Invalid completion')
    require(type(o['model_rounds']) is int and o['model_rounds']==1 and type(o['tool_calls']) is int and o['tool_calls']==0,'Invalid counters')
    p.integer(o['api_requests'],'api requests',1);require(o['api_requests']<=6,'Invalid attempts')
    answer,metrics=score(a['assistant']['content'],initial['task']['choices'],o['answer']['correct_label'])
    require(p.equal(answer,o['answer']) and p.equal(metrics,o['score']),'Outcome differs from content')
    return run


def build_facts(records,*,role=None):
    require(isinstance(records,list) and records,'Missing completed executions')
    first=validate_envelope(records[0]); role=role or first['provenance']['role']
    require(role in ('parent','candidate'),'Test cannot become optimization evidence')
    skill=parent_text(first); runs=[];sources=[];tasks=set();identities=set()
    for i,record in enumerate(records,1):
        validate_envelope(record);e=record['execution'];ref=f'P{i}'
        require(record['provenance']['role']==role and e['skill']==skill,'Mixed roles/Skills')
        require(record['task_id'] not in tasks and record['run_id'] not in identities,'Duplicate run/task')
        tasks.add(record['task_id']);identities.add(record['run_id'])
        run={'ref':ref,'task_id':record['task_id'],'run_id':record['run_id'],
             'initial':{'ref':ref+':0','task':{k:deepcopy(record['task'][k]) for k in ('question','choices')},'messages':deepcopy(e['initial_messages'])},
             'attempts':[{'ref':ref+':1','request_context':p.FORMAL_CONTEXT,'request_messages':deepcopy(e['initial_messages']),
                          'assistant':{'role':'assistant','content':e['content']}}],
             'outcome':{'ref':ref+':outcome','status':'completed','termination':e['termination'],'answer':deepcopy(e['answer']),
                        'model_rounds':1,'tool_calls':0,'api_requests':e['api_requests'],'score':deepcopy(e['metrics'])}}
        runs.append(validate_run(run));sources.append({k:run[k] for k in ('ref','task_id','run_id')})
    return {'facts':{'parent':skill,'runs':runs},'background':p.background(first['execution']['actor']),'sources':sources}
