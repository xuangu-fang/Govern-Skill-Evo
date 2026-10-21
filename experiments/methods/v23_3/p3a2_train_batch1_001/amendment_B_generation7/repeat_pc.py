"""Explicitly authorized additional generation after the archived contract failures."""
import fcntl
import sys
import traceback
from . import run as base
from .run import HERE,read,save,now,verify,generate,cc,oldpc,pc,normalize_update_patches,parse_json_response
from experiments.methods.v23_3.memory_v3_integration_001.run import load_a

def selected(arm):
    path=HERE/'runs'/('B_retry_005' if arm=='B' else 'A_retry_001')
    if arm=='B':return pc.load_preconditioner(path)
    return load_a(path,read(HERE/'common_saved.json'))
def repeat(arm,generation=2):
    assert (arm,generation) in {('A',2),('B',2),('B',3),('B',4),('B',5),('B',6)}
    assert arm in {'A','B'};verify();original=HERE/'runs'/arm;out=HERE/'runs'/f'{arm}_retry_{generation-1:03d}'
    assert read(original/'run.json')['status']=='invalid'
    if out.exists():
        print('REUSE/STOP',arm,read(out/'run.json')['status'],flush=True);return
    
    if generation>=3:assert read(HERE/'runs'/f'B_retry_{generation-2:03d}'/'run.json')['status']=='invalid'
    out.mkdir();saved=read(HERE/'common_saved.json');messages=read(original/'messages.json')
    assert messages==read(HERE/f'{arm}_preconditioner_messages_frozen.json')
    for name,value in [('input',saved),('model_input',pc.model_input(saved)),('messages',messages)]:save(out/f'{name}.json',value)
    (out/'prompt.md').write_text(messages[0]['content'])
    meta={k:v for k,v in read(original/'run.json').items() if k not in {'status','started_at','finished_at','error','error_type'}}
    meta.update(status='requesting',started_at=now(),generation_index=generation,original_failed_generation=str(original),authorization=str(HERE/(f'amendment_B_generation{generation}/authorization.json' if generation>=3 else 'amendment_resampling/authorization.json')));save(out/'run.json',meta)
    try:
        response=generate(messages,'preconditioner',out)
        assert read(out/'call/request.json')['body']==read(original/'call/request.json')['body']
        save(out/'response.json',response);(out/'raw_output.txt').write_text(response.get('content') or '')
        assert response['finish_reason']=='stop','Incomplete response'
        parsed=parse_json_response(response['content']);save(out/'parsed.json',parsed)
        normalized,effective=(parsed,oldpc.compile_effective_plan(parsed,oldpc.preconditioner_input(saved))) if arm=='A' else normalize_update_patches(parsed,oldpc.preconditioner_input(saved))
        save(out/'preconditioner.json',normalized);save(out/'effective_plan.json',effective);save(out/'validation.json',{'valid':True});meta['status']='valid'
    except Exception as exc:
        (out/'traceback.txt').write_text(traceback.format_exc());save(out/'validation.json',{'valid':False,'error_type':type(exc).__name__,'error':str(exc)});meta.update(status='invalid',error_type=type(exc).__name__,error=str(exc))
    finally:meta['finished_at']=now();save(out/'run.json',meta)
    if meta['status']=='valid':selected(arm)
    print('REPEAT',arm,meta['status'],flush=True)
if __name__=='__main__':
    with (HERE/'process.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if sys.argv[1]=='editor':base.load_pc=selected;base.editor_call(sys.argv[2])
        else:repeat(sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 2)
