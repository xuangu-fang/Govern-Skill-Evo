"""Audit raw Actor archives before projecting versioned execution evidence."""
from copy import deepcopy
from pathlib import Path
from ...facts import require
from . import protocol, scoring


def parent_text(record):return record['skill']


def audit_execution_history(record, ref):
    """Validate every real request; expose only completed program executions."""
    profile=record['protocol'];messages=deepcopy(record['initial_messages']);repair=None
    require(protocol.separate_budgets(profile) and profile['actor_task_timeout_seconds']==0,'Invalid execution history protocol')
    attempts=record['attempts'];by_path={a['request_path']:a for a in attempts}
    require(len(by_path)==len(attempts),'Duplicate response request')
    require([a['number'] for a in attempts]==list(range(1,len(attempts)+1)),'Invalid raw response order')
    require(len({r['path'] for r in record['requests']})==len(record['requests']),'Duplicate request archive')
    executions=0;seen=[];visible=[]
    for request in record['requests']:
        expected=protocol.generation_messages(messages,repair)
        require(request['messages']==expected,'Archived API request differs')
        require(request['code_attempt']==executions+1,'Request execution slot differs')
        response=request['response']
        if response is None:
            require(request['path'] not in by_path,'Response missing from request archive')
            continue
        require(request['path'] in by_path,'Unconsumed archived response')
        a=by_path[request['path']];seen.append(a['number'])
        require(a['processed'] and a['request_messages']==expected,'Actor request differs')
        require(a['response']==response['content'] and a['finish_reason']==response['finish_reason'],'Archived response differs')
        require(a['finish_reason'] in ('stop','length'),'Unfinished non-retryable response')
        require(a['code_attempt']==executions+1,'Execution slot differs')
        require(type(a['executed']) is bool and type(a['response_in_history']) is bool
                and a['response_in_history']==a['executed'],'Response history visibility differs')
        error=None;actual=None
        if a['finish_reason']=='length':
            error=('generation_truncated','Model generation did not finish normally; return a complete program')
        elif not a['response'].strip():error=('empty_output','Model returned an empty response')
        else:
            try:_,actual=protocol.extract_code(a['response'])
            except (ValueError,SyntaxError) as exc:error=('format_error',str(exc))
        if error:
            category,detail=error
            require(not a['executed'] and not a.get('execution_started') and a['executed_code'] is None
                    and a['feedback_to_actor'] is None,'Generation failure entered execution history')
            require(a['execution']==dict(status=category,error_category=category,error_detail=detail,
                    exit_status='not_executed',output_openable=False),'Generation failure record differs')
            feedback=protocol.format_feedback(detail,profile) if category=='format_error' else None
            require(a['repair_feedback']==feedback,'Format repair feedback differs')
            if feedback:repair={'response':a['response'],'feedback':feedback}
            continue
        require(a['executed'] and a.get('execution_started') and a['executed_code']==actual
                and a['repair_feedback'] is None,'Executable response has no valid execution')
        e=deepcopy(a['execution']);e.pop('output_path',None)
        visible.append(dict(ref=f"{ref}:{a['number']}",request_messages=deepcopy(messages),
            request_context=protocol.EXECUTION_HISTORY,response=a['response'],executed_code=actual,
            executed=True,execution=e,feedback_to_actor=deepcopy(a['feedback_to_actor']),
            response_in_history=True,code_attempt=a['code_attempt'],finish_reason=a['finish_reason']))
        messages.append({'role':'assistant','content':a['response']});repair=None;executions+=1
        feedback=a['feedback_to_actor']
        needs_feedback=not (e.get('status')=='success' and e.get('output_openable')) and executions<profile['max_code_attempts']
        require((feedback is not None)==needs_feedback,'Missing or unexpected execution feedback')
        if feedback is not None:
            require(not e.get('output_openable'),'Feedback after valid submission')
            require(feedback==protocol.feedback(e['error_category'],e['error_detail'],e['exit_status'],executions,profile),'Runtime feedback differs')
            messages.append(feedback)
    require(seen==list(range(1,len(attempts)+1)),'Response archive order differs')
    require(record['format_repair']==repair and record['messages']==messages,'Formal or temporary history differs')
    return visible,executions


def build_facts(records):
    require(isinstance(records,list) and records,'Missing Actor executions')
    parent=records[0]['skill'];profile=records[0]['protocol'];runs=[];sources=[];identities=set();tasks=set()
    for i,record in enumerate(records,1):
        require(record['status']=='completed' and record['actor_complete'],'Actor task is incomplete')
        require(record['skill']==parent and record['protocol']==profile,'Mixed Actor conditions')
        require(record['run_id'] not in identities and record['task']['id'] not in tasks,'Duplicate execution/task')
        identities.add(record['run_id']);tasks.add(record['task']['id']);ref=f'P{i}'
        initial=record['initial_messages'];task=record['task']
        view=record.get('workbook_preview')
        require(view is not None,'Missing original preview')
        require(initial==protocol.initial_messages(task,parent,view,profile),'Initial Actor request differs')
        messages=deepcopy(initial);attempts=[];executions=0
        separate=protocol.separate_budgets(profile)
        requests={r['path']:r for r in record['requests']};response_paths=set()
        isolated=protocol.execution_history(profile)
        if isolated:
            attempts,executions=audit_execution_history(record,ref)
        else:
            for n,a in enumerate(record['attempts'],1):
                require(a['number']==n and a['request_messages']==messages,'Actor history differs')
                require(type(a['executed']) is bool,'Invalid execution flag')
                if separate:
                    require(a['code_attempt']==executions+1,'Execution slot differs')
                    require(a['request_path'] in requests and a['request_path'] not in response_paths,'Response request differs')
                    request=requests[a['request_path']];response_paths.add(a['request_path'])
                    require(request['code_attempt']==a['code_attempt'] and request['response']['content']==a['response']
                            and request['response']['finish_reason']==a['finish_reason'],'Archived response differs')
                    require(type(a['response_in_history']) is bool and a['response_in_history']==(a['finish_reason']=='stop'), 'Response history visibility differs')
                    require(a['finish_reason'] in ('stop','length'),'Unfinished non-retryable response')
                    if not a['response_in_history']:
                        require(not a['executed'] and a['feedback_to_actor'] is None,'Truncated generation was executed or returned as feedback')
                if a.get('response_in_history',True):messages.append({'role':'assistant','content':a['response']})
                executions+=int(a['executed'])
                feedback=a['feedback_to_actor']
                if feedback is not None:
                    e=a['execution']
                    require(not e.get('output_openable'),'Feedback after valid submission')
                    require(feedback==protocol.feedback(e['error_category'],e['error_detail'],e['exit_status'],executions if separate else n,profile),'Runtime feedback differs')
                    messages.append(feedback)
                e=deepcopy(a['execution'])
                if e:e.pop('output_path',None)
                attempts.append(dict(ref=f'{ref}:{n}',request_messages=deepcopy(a['request_messages']),response=a['response'],
                    executed_code=a['executed_code'],executed=a['executed'],execution=e,feedback_to_actor=deepcopy(feedback)))
                if separate:
                    attempts[-1].update(response_in_history=a['response_in_history'],code_attempt=a['code_attempt'],finish_reason=a['finish_reason'])
            require(messages==record['messages'],'Actor transcript contains unrecorded messages')
        used=executions if separate else len(attempts)
        require(record['code_attempts']==used and record['program_executions']==executions
                and record['api_requests']==len(record['requests']),'Actor counters differ')
        require(used<=profile['max_code_attempts'],'Code attempt limit exceeded')
        if separate:
            require(record['generation_responses']==len(record['attempts']),'Generation response count differs')
            slots=[r['code_attempt'] for r in record['requests']]
            require(all(type(s) is int and 1<=s<=profile['max_code_attempts'] for s in slots),'Invalid generation slot')
            require(all(slots.count(s)<=profile['request_attempts_total'] for s in set(slots)),'Generation request limit exceeded')
        if record['termination']=='valid_workbook_submitted':
            require(record['submitted_attempt']==len(record['attempts']) and attempts[-1]['execution']['output_openable'],'Invalid final submission')
        else:require(record['termination']=='budget_exhausted' and record['output_path'] is None,'Invalid budget termination')
        score=record['score'];require(score['total_cells']>0 and 0<=score['correct_cells']<=score['total_cells'],'Invalid score counts')
        rate=score['correct_cells']/score['total_cells']
        # Retain exact-rate historical archives; new scores follow SkillAdam's 4 decimals.
        require(score['hard']==int(score['correct_cells']==score['total_cells']) and score['per_cell_pass_rate'] in (rate,round(rate,4)),'Score counts/rates differ')
        outcome={k:record[k] for k in ('status','termination','code_attempts','program_executions','api_requests')}
        if isolated:outcome.pop('api_requests')
        elif separate:outcome['generation_responses']=record['generation_responses']
        outcome.update(ref=ref+':outcome',submitted_attempt=f"{ref}:{record['submitted_attempt']}" if record['submitted_attempt'] else None,score=scoring.model_view(score,profile))
        runs.append(dict(ref=ref,task_id=task['id'],run_id=record['run_id'],initial={'ref':ref+':0','messages':deepcopy(initial)},attempts=attempts,outcome=outcome))
        sources.append(dict(ref=ref,task_id=task['id'],run_id=record['run_id']))
    return {'facts':{'parent':parent,'runs':runs},'background':protocol.background(profile),'sources':sources}
