"""Bounded C01 fixture through production projections and feedback construction."""
from pathlib import Path
import json
import re
from src.skill_evolution.v27 import modules, output_feedback, stages
from src.skill_evolution.v27.benchmarks.lmb import evidence, protocol as p
from src.skill_evolution.v27.capacity import account
from src.skill_evolution.v27.contracts import memory
from src.skill_evolution.v27.contracts.editor import actual_diff
from .support import SKILL, HIDDEN, record, grouping, diagnosis, keep

PROFILE_PATH=Path(__file__).with_name('capacity_profile.json')


def sized(prefix,size,suffix=''):
    return (prefix+'x'*size)[:size-len(suffix)]+suffix


def chain(records,active,round_id):
    calls={};outputs={}
    c=calls['grouping']=modules.grouping_call(records,round_id)
    outputs['grouping']=grouping(c.input['bundle']['facts']['runs'])
    saved=c.complete(outputs['grouping'])
    c=calls['diagnosis']=modules.diagnosis_call(saved)
    outputs['diagnosis']=diagnosis()
    outputs['diagnosis']['plan']['updates'][0]['basis']=[f'P{i}:1' for i in range(1,len(records)+1)]
    saved=c.complete(outputs['diagnosis'])
    c=calls['preconditioner']=modules.preconditioner_call(saved,active)
    outputs['preconditioner']=keep();saved=c.complete(outputs['preconditioner'])
    c=calls['editor']=modules.editor_call(saved)
    parent=records[0]['execution']['skill'];candidate=parent+'Check the required equality condition.\n'
    delta=re.sub(r'^@@[^\n]*@@[^\n]*$', '@@', actual_diff(parent,candidate), flags=re.M)
    outputs['editor']={'patch':delta,'reason':'Apply the scoped condition.'};saved=c.complete(outputs['editor'])
    qs=[record(r['task_id'],role='candidate',skill=candidate,question=r['task']['question'],
               content=r['execution']['content'].replace('<answer>B</answer>','<answer>A</answer>')) for r in records]
    bundle=evidence.build_replay_from_editor(saved,round_id+'_editor',records,qs,memory=active)
    calls['replay']=modules.replay_call(bundle);outputs['replay']={'entries':[]}
    return calls,outputs,bundle


def build(root,*,stress=False):
    root=Path(root);profile=json.loads(PROFILE_PATH.read_text())
    if stress:profile['content_chars_per_run']=profile['stress_content_chars_per_run']
    _,_,history=chain([record()],memory.empty_memory(),'C01_history')
    proposals={'entries':[{'revises':[],'knowledge':[{
        'text':sized(f'Historical bounded observation {i}: ',profile['knowledge_chars_per_entry']),
        'evidence':['diff','P1:1']}]} for i in range(profile['memory_entries'])]}
    memory.commit_memory(root/'history',context_id='C01_history',context=history,result=proposals,
                         memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
    active=memory.load_memory(root/'history',memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
    skill=sized(SKILL,profile['skill_chars'],'\n')
    records=[record(f'synthetic:c01:{i:03}',skill=skill,
                    question=sized(f'数学 question {i}: ',profile['question_chars_per_task']),
                    content=sized(f'Ordinary submitted derivation {i}: ',profile['content_chars_per_run'],'<answer>B</answer>'))
             for i in range(profile['tasks'])]
    calls,outputs,bundle=chain(records,active,'C01_current')
    invalid=json.dumps({'unexpected':sized('INVALID_BEGIN ',profile['previous_invalid_content_chars']-18,' INVALID_END')})
    assert len(invalid)==profile['previous_invalid_content_chars']
    previous=root/'previous';previous.mkdir(parents=True,exist_ok=True)
    stages.save(previous/'response.json',{'content':invalid,'finish_reason':'stop'})
    context={'policy':output_feedback.POLICY,'execution_view':output_feedback.TIMELINE,'feedback_from':str(previous)}
    report={'profile':profile,'stress':stress,'provider_capacity_verified':False,'unbounded_growth_verified':False,
            'parent_runs':len(records),'candidate_runs':len(bundle['audit']['candidate_records']),
            'skill_chars':len(skill),'memory_entries':len(active['entries']),'previous_invalid_content_chars':len(invalid),'modules':{}}
    messages={}
    for name,call in calls.items():
        try:output_feedback.output_call(f'{name} output',call.complete,json.loads(invalid))
        except output_feedback.OutputValidationError as error:
            stages.save(previous/'error.json',{'kind':'output_validation','diagnostic':error.diagnostic})
        else:raise AssertionError('C01 previous output must fail the actual module validator')
        reserve=16384 if name in ('grouping','editor') else 32768
        cfg={'max_tokens':reserve,'context_window_tokens':profile['context_window_tokens']}
        limits={k:profile[k] for k in ('max_input_chars','max_message_utf8_bytes')}
        full=output_feedback.request_messages(call.messages,context)
        assert full[-2]['content']==invalid and HIDDEN not in json.dumps(full)
        rejected=[]
        def measured(msg,label):
            try:return account(msg,cfg,**limits)
            except ValueError as error:
                if not stress:raise
                rejected.append({'input':label,'error':str(error)})
                # Measure the overflow; this does not accept or enlarge the frozen runtime budget.
                result=account(msg,{'max_tokens':reserve},max_input_chars=10000000,max_message_utf8_bytes=10000000)
                result['context_window_tokens']=profile['context_window_tokens']
                return result
        base=measured(call.messages,'base');total=measured(full,'with_feedback')
        report['modules'][name]={'base':base,'with_feedback':total,
            'fits_frozen_limits':not rejected,'rejected_inputs':rejected,
            'context_estimate_headroom':profile['context_window_tokens']-total['context_token_upper_estimate'],
            'messages_sha256':p.digest(full),'lossless_feedback':True}
        messages[name]=full
    return {'calls':calls,'outputs':outputs,'invalid':invalid,'report':report,'messages':messages}
