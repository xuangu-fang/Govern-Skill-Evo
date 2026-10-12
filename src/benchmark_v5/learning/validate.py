"""Pre-model engineering and shortcut checks; post-model replay and visibility audit."""
from copy import deepcopy
from benchmark_v5.core import verify_audit,canonical
from benchmark_v5.calibration.runner import read,write,sha
from .cases import heldout_cases,world_for
from .environment import build
from .evaluation import evaluate,possible_first_choices,settlement_predictions
from .experience import training_package,compatible_counts
from .rules import sufficient,valid_doc
from . import protocol
from .runner import DEST,check,verify_states,usage_and_message


def complete_ls(env,item):
    c=env.scenario
    env.call('accept_return',dict(item_id=item,operation_id='final-return'))
    env.call('purchase',dict(purchase_id=c['purchase']['id'],operation_id='buy'))
    env.call('finish',{'receipt':dict(stage='PURCHASED',returned_item=item,purchase_id=c['purchase']['id'])})


def complete_lg(env,submit):
    c=env.scenario;docs=[d['id'] for d in c['documents'] if valid_doc(d,c)]
    if submit:
        r=env.call('submit_application',dict(document_ids=docs,endpoint=c['endpoint'],authorization=c['auth_token'],operation_id='s'))
        stage='FULFILLED'
    else:
        r=env.call('request_supplement',dict(required_kinds=['I'],reason='Inspection evidence needed to complete the current proof package',authorization=c['auth_token'],operation_id='s'))
        stage='SUPPLEMENT_REQUESTED'
    env.call('record_basis',dict(receipt_id=r['receipt_id'],document_ids=docs,authorization=c['auth_token'],operation_id='b'))
    env.call('finish',{'receipt':dict(stage=stage,receipt_id=r['receipt_id'])})


def engineering():
    paths=[];counts={}
    for kind in ('LS1','LG1'):
        obs,audits=training_package(kind)
        n,h=compatible_counts(kind,obs)
        counts[kind]={'counts':n,'remaining':h,'observations':len(obs)}
        for a in audits:verify_audit(a)
    for c in heldout_cases():
        modes=['reference','always_first','balance_then_recover'] if c['kind']=='LS1' else ['reference','all_documents','always_handoff']
        for mode in modes:
            env=build(c,world_for(c['kind']))
            if c['kind']=='LS1':
                if mode=='reference':complete_ls(env,possible_first_choices(c,env.world)[0])
                elif mode=='always_first':complete_ls(env,c['allowed_returns'][0])
                else:
                    # No world access or refund prediction: try permitted candidates and read balance.
                    for n,item in enumerate(c['allowed_returns']):
                        env.call('accept_return',dict(item_id=item,operation_id=f'try-{n}'))
                        ledger=env.call('read_ledger',{})
                        if ledger['available_balance']>=c['purchase']['price']:
                            env.call('purchase',dict(purchase_id=c['purchase']['id'],operation_id='buy'))
                            env.call('finish',{'receipt':dict(stage='PURCHASED',returned_item=item,purchase_id=c['purchase']['id'])})
                            break
                        env.call('cancel_return',dict(item_id=item,operation_id=f'undo-{n}'))
            else:
                submit=sufficient(c['documents'],c,env.world) if mode=='reference' else mode=='all_documents'
                complete_lg(env,submit)
            env.end_budget();a=env.audit();verify_audit(a)
            row=dict(case_id=c['id'],kind=c['kind'],strategy=mode,score=evaluate(a))
            paths.append(row);write(DEST/f'engineering/{c["id"]}__{mode}.json',a)
            other=build(c,world_for(c['kind']))
            for e in a['events']:
                if e['tool']=='__end__':other.end_budget()
                else:assert other.call(e['tool'],e['arguments'])==e['result']
            assert other.audit()==a
            if mode=='reference':assert row['score']['full_service']
    write(DEST/'engineering.json',dict(identifiability=counts,paths=paths,
        limitations=['Synthetic contract only, external business validity pending',
                     'LS1 balance/recovery shortcut is retained; terminal Success cannot alone prove learning difficulty',
                     'Finite candidate enumeration is not proof over all possible programs']))
    print(canonical({'reference_paths':10,'total_paths':len(paths),'identifiability':counts}))


def replay_episode(job):
    d=DEST/job['id'];trace=read(d/'trace.json');a=read(d/'audit.json');r=read(d/'result.json')
    verify_audit(a)
    c=next(c for c in heldout_cases() if c['id']==job['case_id'])
    env=build(c,world_for(c['kind']))
    state=read(DEST/f'states/{job["kind"]}__{job["condition"]}.json')
    messages=protocol.initial_messages(env,state,job['condition'])
    assert messages==trace['initial_messages']
    catalog=[{'type':'function','function':t} for t in env.catalog()]
    assert trace['tools']==catalog
    tool_count=0
    for rnd in trace['rounds']:
        assert rnd['request']['messages']==messages
        assert rnd['request']['tools']==catalog
        successes=[at for at in rnd['attempts'] if 'response' in at]
        if not successes:continue
        _,assistant,_=usage_and_message(successes[-1]['response'],rnd['request'])
        messages.append(assistant)
        outcomes=[]
        for t in assistant.get('tool_calls',[]):
            if env.state['closed'] or tool_count>=protocol.LIMITS['tool_calls']:
                out={'error':'SESSION_CLOSED' if env.state['closed'] else 'CALL_BUDGET_EXHAUSTED'}
            else:
                tool_count+=1
                import json
                try:args=json.loads(t['function']['arguments'])
                except json.JSONDecodeError:args=None
                out=env.call(t['function']['name'],args)
            outcomes.append(dict(tool_call_id=t['id'],result=out))
            messages.append(dict(role='tool',tool_call_id=t['id'],content=canonical(out)))
        assert outcomes==rnd.get('tool_results',[])
    env.end_budget();assert env.audit()==a
    if r['valid']:assert evaluate(a)==r['score']
    # Public view deliberately excludes provider reasoning, private scores and state snapshots.
    public=[{k:v for k,v in m.items() if k!='reasoning_content'} for m in messages]
    return public


def validate_run():
    freeze=check();verify_states()
    views={job['id']:replay_episode(job) for job in freeze['jobs']}
    protected=read(DEST/'protected_before.json')
    from benchmark_v5.core import ROOT
    changed=[p for p,h in protected.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
    assert not changed,changed
    write(DEST/'public_views.json',views)
    summary=dict(replayed_and_rescored=len(views),public_context_reconstructed=len(views),
                 frozen_learning_states=10,protected_files_unchanged=len(protected))
    write(DEST/'validation.json',summary);print(canonical(summary))

if __name__=='__main__':
    import sys
    engineering() if sys.argv[1]=='engineering' else validate_run()
