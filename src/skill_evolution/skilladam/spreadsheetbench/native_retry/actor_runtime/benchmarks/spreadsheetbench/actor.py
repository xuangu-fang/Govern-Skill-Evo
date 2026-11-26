"""Persisted code-generation loop. Submission is irrevocable before scoring."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import time
import uuid
from ...storage import write_record
from . import protocol, executor, scoring, transport


class Interrupted(RuntimeError):
    pass


class GenerationExhausted(Interrupted):
    """No executable program was produced; this is not a graded submission."""


def run(task, skill, directory, config, *, generate=None, execute=None, score=None, clock=time.monotonic, hook=None):
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    state_file=directory/'actor_state.json';result_file=directory/'trajectory.json'
    profile=config['actor_profile'];generate=generate or transport.request;execute=execute or executor.execute;score=score or scoring.score
    separate=protocol.separate_budgets(profile)
    isolated=protocol.execution_history(profile)
    if isolated and (not separate or profile['actor_task_timeout_seconds']!=0):
        raise protocol.InputError('Execution-only history requires execution budgets and no cumulative task deadline')
    active_started=None;budget_frozen=False
    def save():
        if active_started is not None and not budget_frozen:
            state['elapsed_seconds']=elapsed_before+max(0,clock()-active_started)
        if separate:
            state.update(code_attempts=sum(bool(a.get('execution_started')) for a in state['attempts']),
                         program_executions=sum(a['executed'] for a in state['attempts']),
                         generation_responses=len(state['attempts']),api_requests=len(state['requests']))
        write_record(state_file,state)
    if state_file.exists():
        state=json.loads(state_file.read_text())
        if (state['task']!=task or state['skill']!=skill or state['protocol']!=profile or state['model']!=config['actor_model']):
            raise Interrupted('Saved Actor conditions differ')
        if state.get('pending'):
            spent=max(0,time.time()-state['pending']['wall_started']);limit=state['pending']['limit']
            state['elapsed_seconds']+=spent if limit is None else min(spent,limit)
            state['pending']=None;save()
    else:
        state=dict(version='v25_spreadsheet_actor_v1',run_id='run_'+uuid.uuid4().hex,task=deepcopy(task),skill=skill,
            model=config['actor_model'],protocol=deepcopy(profile),executor=deepcopy(config['executor']),
            attempts=[],requests=[],messages=[],elapsed_seconds=0.,pending=None,actor_complete=False,status='running')
        if isolated:state['format_repair']=None
        save()
    elapsed_before=state['elapsed_seconds'];active_started=clock();budget_frozen=state['actor_complete']
    def remaining():
        if profile['actor_task_timeout_seconds']==0:return float('inf')
        return max(0,profile['actor_task_timeout_seconds']-elapsed_before-max(0,clock()-active_started))
    def checkpoint(name):
        if hook:hook(name,state)
    def operation(kind,limit,fn):
        if limit is not None and limit<=0:raise Interrupted('No remaining Actor time')
        state['pending']={'kind':kind,'wall_started':time.time(),'limit':limit};save()
        try:return fn()
        finally:
            state['pending']=None;save()
    try:
        if state.get('status')=='completed':
            budget_frozen=True
            if not result_file.exists():write_record(result_file,state)
            return result_file
        if not state['messages']:
            def prepare():
                snapshot=directory/'original_input.xlsx'
                if snapshot.exists():
                    if snapshot.read_bytes()!=Path(task['input_path']).read_bytes():raise protocol.InputError('Original input changed')
                else:shutil.copyfile(task['input_path'],snapshot)
                state['input_snapshot']=str(snapshot)
                view=protocol.preview(snapshot,profile)
                state['workbook_preview']=view
                state['messages']=protocol.initial_messages(task,skill,view,profile)
                state['initial_messages']=deepcopy(state['messages']);save()
            operation('input_preparation',None if profile['actor_task_timeout_seconds']==0 else remaining(),prepare)
        while not state['actor_complete']:
            unprocessed=state['attempts'] and not state['attempts'][-1].get('processed')
            if not unprocessed:
                number=len(state['attempts'])+1;response=None
                used=sum(bool(a.get('execution_started')) for a in state['attempts']) if separate else len(state['attempts'])
                slot=used+1
                prior=[r for r in state['requests'] if r['code_attempt']==slot]
                consumed={a.get('request_path') for a in state['attempts']} if separate else set()
                for item in prior:
                    if item['path'] in consumed:continue
                    folder=directory/item['path']
                    if item.get('response') is None and (folder/'response.json').exists():
                        item['response']=json.loads((folder/'response.json').read_text());save()
                    if item.get('response') is not None:response=item['response'];break
                # Resolve saved responses before classifying an exhausted task.
                # An unanswered API request remains a technical interruption on
                # resume; it must not become a scored failure in learning/Gate.
                if prior and response is None and remaining()<=0:
                    raise Interrupted('API unavailable before task deadline')
                if used>=profile['max_code_attempts'] or remaining()<=0:
                    state.update(actor_complete=True,termination='budget_exhausted',submitted_attempt=None,output_path=None);save();break
                messages=protocol.generation_messages(state['messages'],state['format_repair']) if isolated else deepcopy(state['messages'])
                protocol.check_capacity(messages,config)
                if response is None:
                    if prior and prior[-1].get('retryable') is False:raise Interrupted('Preserved non-retryable API failure')
                    for request_number in range(len(prior)+1,profile['request_attempts_total']+1):
                        if remaining()<=0:raise Interrupted('API unavailable before task deadline')
                        path=directory/'requests'/f'{slot:03}_{request_number:02}';path.mkdir(parents=True,exist_ok=True)
                        item={'code_attempt':slot,'path':str(path.relative_to(directory)),'response':None}
                        if isolated:item['messages']=deepcopy(messages)
                        state['requests'].append(item);save()
                        write_record(path/'messages.json',messages)
                        def call():
                            value=generate(deepcopy(messages),path,min(profile['request_timeout_seconds'],remaining()),config)
                            if not isinstance(value,dict) or not isinstance(value.get('content'),str):raise transport.RequestError('Malformed model response')
                            write_record(path/'response.json',value);return value
                        try:
                            response=operation('api_request',min(profile['request_timeout_seconds'],remaining()),call)
                            item['response']=response;save();checkpoint('response_saved');break
                        except transport.RequestError as exc:
                            item.update(error=str(exc),retryable=exc.retryable);save()
                            if not exc.retryable:raise Interrupted(str(exc)) from exc
                            if request_number<profile['request_attempts_total'] and remaining()>0:
                                delay=min(config.get('retry_delay_seconds',0)*request_number,remaining())
                                if delay:operation('retry_wait',delay,lambda:time.sleep(delay))
                    if response is None:
                        if separate:raise GenerationExhausted('Generation request budget exhausted; resume does not reset it')
                        raise Interrupted('Frozen API attempts exhausted; resume does not reset them')
                attempt={'number':number,'request_messages':deepcopy(item['messages'] if isolated else state['messages']),'response':response['content'],
                         'finish_reason':response.get('finish_reason'),'executed_code':None,'executed':False,
                         'execution':None,'feedback_to_actor':None,'processed':False}
                if separate:
                    attempt.update(request_path=item['path'],code_attempt=slot,
                                   response_in_history=not isolated and response.get('finish_reason')=='stop')
                if isolated:attempt['repair_feedback']=None
                state['attempts'].append(attempt)
                if attempt.get('response_in_history',True):
                    state['messages'].append({'role':'assistant','content':response['content']})
                save()
            attempt=state['attempts'][-1];number=attempt['number'];folder=directory/'code'/f'{number:03}';folder.mkdir(parents=True,exist_ok=True)
            if (folder/'execution.json').exists():
                attempt['execution']=json.loads((folder/'execution.json').read_text());attempt['executed']=True
                attempt['executed_code']=(folder/'program.py').read_text()
            if attempt['execution'] is None:
                if separate and attempt['finish_reason'] not in ('stop','length'):
                    raise Interrupted(f"Non-retryable model finish reason: {attempt['finish_reason']}")
                try:
                    if attempt['finish_reason']!='stop':raise ValueError('Model generation did not finish normally; return a complete program')
                    if isolated and not attempt['response'].strip():raise ValueError('Model returned an empty response')
                    raw,actual=protocol.extract_code(attempt['response']);(folder/'raw.py').write_text(raw);(folder/'program.py').write_text(actual)
                except (ValueError,SyntaxError) as exc:
                    category='generation_truncated' if separate and attempt['finish_reason']=='length' else 'format_error'
                    if isolated and attempt['finish_reason']=='stop' and not attempt['response'].strip():category='empty_output'
                    attempt['execution']={'status':category,'error_category':category,'error_detail':str(exc),'exit_status':'not_executed','output_openable':False}
                else:
                    if remaining()<=0:
                        state.update(actor_complete=True,termination='budget_exhausted',submitted_attempt=None,output_path=None);save();break
                    if attempt.get('execution_started'):
                        raise Interrupted('Interrupted program has no saved outcome; do not execute it again')
                    attempt['executed_code']=actual
                    attempt['execution_started']=True;save()
                    def program():
                        result=execute(actual,state['input_snapshot'],folder,min(profile['program_timeout_seconds'],remaining()),config)
                        write_record(folder/'execution.json',result);return result
                    attempt['execution']=operation('program',min(profile['program_timeout_seconds'],remaining()),program)
                    attempt['executed']=True;save();checkpoint('execution_saved')
            if isolated and attempt['executed'] and not attempt['response_in_history']:
                state['messages'].append({'role':'assistant','content':attempt['response']})
                attempt['response_in_history']=True
                state['format_repair']=None;save()
            outcome=attempt['execution']
            if outcome.get('status')=='success' and outcome.get('output_openable') and remaining()>0:
                attempt['processed']=True
                state.update(actor_complete=True,termination='valid_workbook_submitted',submitted_attempt=number,output_path=outcome['output_path']);save();checkpoint('submitted');break
            attempt['processed']=True
            if isolated and not attempt['executed'] and outcome['status']=='format_error':
                attempt['repair_feedback']=protocol.format_feedback(outcome['error_detail'],profile)
                state['format_repair']={'response':attempt['response'],'feedback':deepcopy(attempt['repair_feedback'])}
            used=sum(bool(a.get('execution_started')) for a in state['attempts']) if separate else number
            if used<profile['max_code_attempts'] and remaining()>0 and attempt.get('response_in_history',True):
                msg=protocol.feedback(outcome.get('error_category','execution_error'),outcome.get('error_detail','Actor budget exhausted'),outcome.get('exit_status','unavailable'),used,profile)
                attempt['feedback_to_actor']=msg;state['messages'].append(msg)
            save();checkpoint('attempt_processed')
            if separate and not attempt['executed']:
                request_count=sum(r['code_attempt']==attempt['code_attempt'] for r in state['requests'])
                if request_count<profile['request_attempts_total'] and remaining()>0:
                    delay=min(config.get('retry_delay_seconds',0)*request_count,remaining())
                    if delay:operation('retry_wait',delay,lambda:time.sleep(delay))
        # No code path below this point appends an Actor message or calls a model.
        state['status']='scoring';save();budget_frozen=True
        score_file=directory/'score.json'
        if score_file.exists():result=json.loads(score_file.read_text())
        else:
            result=score(state['output_path'],task['answer_path'],task['answer_region'],profile)
            write_record(score_file,result);checkpoint('score_saved')
        state.update(score=result,status='completed',code_attempts=sum(a['executed'] for a in state['attempts']) if separate else len(state['attempts']),
                     program_executions=sum(a['executed'] for a in state['attempts']),api_requests=len(state['requests']))
        save();write_record(result_file,state);return result_file
    except BaseException as exc:
        state['status']='generation_incomplete' if isinstance(exc,GenerationExhausted) else ('scoring_interrupted' if state['actor_complete'] else 'technical_interruption')
        if isinstance(exc,GenerationExhausted):state['termination']='generation_budget_exhausted'
        state['error_type']=type(exc).__name__;save();raise
