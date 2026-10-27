"""Isolated diagnostic calls. All sends, failures and repeats count toward eight."""
from datetime import datetime, timezone
import fcntl
import json
import sys
import time

from .design import HERE, ROOT, read, save, sha, QUESTIONS
from experiments.methods.v23_4.archive_io import archive_glob, resolve, runtime_root
from experiments.methods.v23_3.memory_compaction_live_validation_001.run import environment, transport
from src.skill_evolution.v22.diagnosis_editor import parse_json_response


def now(): return datetime.now(timezone.utc).isoformat()


def verify():
    frozen=read(HERE/'freeze.json')
    assert all(sha(ROOT/p)==digest for p,digest in frozen['sha256'].items())
    key,cfg=environment();cfg={**cfg,'max_tokens':32768}
    assert cfg==frozen['call_config']
    return key


def validate(result,case):
    if not isinstance(result,dict) or set(result)!= {'answers'} or not isinstance(result['answers'],list):
        raise ValueError('Expected answers array only')
    ids=[]
    for a in result['answers']:
        if not isinstance(a,dict) or set(a)!={'id','facts','conditions','comparison','conclusion','uncertainty'}:
            raise ValueError('Unexpected diagnostic answer fields')
        ids.append(a['id'])
        if not all(isinstance(a[k],str) and a[k].strip() for k in ('id','conditions','comparison','conclusion','uncertainty')):
            raise ValueError('Nonempty answer strings required')
        if not isinstance(a['facts'],list) or not a['facts']: raise ValueError('Facts array required')
        for fact in a['facts']:
            if not isinstance(fact,dict) or set(fact)!={'sources','text'}: raise ValueError('Invalid fact shape')
            if not isinstance(fact['text'],str) or not fact['text'].strip(): raise ValueError('Fact text required')
            if not isinstance(fact['sources'],list) or not fact['sources'] or not all(isinstance(x,str) and x for x in fact['sources']):
                raise ValueError('Source strings required')
    if sorted(ids)!=sorted(q['id'] for q in QUESTIONS[case]):raise ValueError('Question coverage mismatch')
    return result


def call(label,number):
    case,arm=label.split('_');assert case in QUESTIONS and arm in ('A','B') and number in (1,2)
    key=verify()
    if number==2:
        plan=read(HERE/'repeat_plan.json');assert label in plan['repeat_conditions']
    dest=runtime_root(HERE)/f'runs/{label}/attempt_{number:03}'
    with (runtime_root(HERE)/'live.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if resolve(dest).exists():
            print('EXISTS; never resend',label,number,flush=True);return
        previous=list(archive_glob(HERE/'runs', '*/attempt_*/started.json'))
        assert len(previous)<8,'Total HTTP budget exhausted'
        if number==2:assert resolve(HERE/f'runs/{label}/attempt_001/started.json').exists()
        request=read(HERE/f'config/{label}/request.json')
        meta={'label':label,'replicate':number,'started_at':now(),'purpose':'initial' if number==1 else 'preregistered_repeat',
              'http_ordinal':len(previous)+1,'max_tokens':32768}
        save(dest/'started.json',meta)
        print('START',label,number,'HTTP',len(previous)+1,flush=True)
        started=time.monotonic()
        try:
            response=transport()(request,key,dest/'http',{'connect_upload_timeout_seconds':60,'read_timeout_seconds':300})
            save(dest/'response.json',response)
            (dest/'raw_output.txt').write_text(response.get('content',''))
            meta.update(finish_reason=response.get('finish_reason'),usage=response.get('usage'),response_model=response.get('response_model'))
            if response['finish_reason']!='stop':raise ValueError('Non-stop completion')
            parsed=parse_json_response(response['content']);save(dest/'parsed.json',parsed)
            validate(parsed,case)
            meta.update(status='valid',semantic_score='not yet evaluated')
        except Exception as exc:
            meta.update(status='technical_failure',error_type=type(exc).__name__,error=str(exc)[:1000])
        meta.update(elapsed_seconds=round(time.monotonic()-started,3),finished_at=now())
        save(dest/'attempt.json',meta)
        print('END',label,number,meta['status'],meta['elapsed_seconds'],meta.get('error',''),flush=True)


def audit():
    verify()
    attempts=[]
    for path in archive_glob(HERE/'runs', '*/attempt_*/started.json'):
        dest=path.parent; meta=read(dest/'attempt.json') if resolve(dest/'attempt.json').exists() else read(path)
        req=read(dest/'http/request.json')
        expected=read(HERE/f"config/{meta['label']}/request.json")
        assert req['body']==expected['body'] and req['endpoint']==expected['endpoint']
        assert req['transport_retries']==0 and req['timeout']==[60,300]
        if meta.get('status')=='valid':validate(read(dest/'parsed.json'),meta['label'].split('_')[0])
        attempts.append(meta)
    assert len(attempts)<=8
    protected=read(HERE/'protected_before.json')
    assert all(sha(ROOT/p)==d for p,d in protected.items())
    total={k:sum(a.get('usage',{}).get(k,0) for a in attempts) for k in ('prompt_tokens','completion_tokens','total_tokens')}
    result={'attempts':attempts,'http_count':len(attempts),'usage':total,'protected_files_unchanged':len(protected),'model_config_unchanged':True}
    (HERE/'AUDIT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    if sys.argv[1:]==['initial']:
        for label in ('R05_A','R05_B','R06_B','R06_A'):call(label,1)
    elif sys.argv[1:]==['repeat']:
        for label in read(HERE/'repeat_plan.json')['repeat_conditions']:call(label,2)
    elif sys.argv[1:]==['audit']:audit()
    else:raise SystemExit('Use initial, repeat or audit')
