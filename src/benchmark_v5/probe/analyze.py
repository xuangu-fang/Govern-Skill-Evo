"""Read-only model-free replay, scoring and budget audit of the frozen probe."""
from collections import Counter
import json
from benchmark_v5.core import ROOT
from benchmark_v5.calibration.runner import read, write, sha
from .environment import build
from .evaluation import evaluate
from .runner import DEST, check


def analyze():
    frozen=check();rows=[];public=[]
    for job in frozen['jobs']:
        b=DEST/job['id'];r=read(b/'result.json');a=read(b/'audit.json');t=read(b/'trace.json')
        env=build(job['task'],job['condition'])
        assert env.initial==a['initial']
        for e in a['events']:
            if e['tool']=='__end__':env.end_budget()
            else:assert env.call(e['tool'],e['arguments'])==e['result']
        assert env.audit()==a,job['id']
        assert not r['valid'] or evaluate(a)==r['score']
        # Reconstruct actual model context from recorded public responses, including
        # provider-required reasoning fields internally, without publishing those fields.
        messages=t['initial_messages'].copy();expected_tools=t['tools']
        rounds=[];over=[];truncated=[];attempts=0
        totals=dict(prompt_tokens=0,completion_tokens=0,total_tokens=0)
        for n,rnd in enumerate(t['rounds'],1):
            p=rnd['request'];assert p['model']=='deepseek-v4-flash'
            assert p['messages']==messages and p['tools']==expected_tools
            attempts+=len(rnd['attempts'])
            responses=[x['response'] for x in rnd['attempts'] if 'response' in x]
            if not responses:break
            response=responses[-1];u=response['usage'];raw=response['choices'][0]['message']
            for k in totals:totals[k]+=u[k]
            if u['completion_tokens']>p['max_tokens']:over.append(n)
            if response['choices'][0].get('finish_reason')=='length':truncated.append(n)
            assistant={'role':'assistant','content':raw.get('content')}
            if raw.get('reasoning_content'):assistant['reasoning_content']=raw['reasoning_content']
            if raw.get('tool_calls'):assistant['tool_calls']=[{k:x[k] for k in ('id','type','function')} for x in raw['tool_calls']]
            messages.append(assistant)
            rounds.append({'turn':n,'content':raw.get('content'),'tool_calls':raw.get('tool_calls'),
                           'finish_reason':response['choices'][0].get('finish_reason'),'tool_results':rnd.get('tool_results')})
            for item in rnd.get('tool_results',[]):
                messages.append({'role':'tool','tool_call_id':item['tool_call_id'],'content':json.dumps(item['result'],ensure_ascii=False)})
        assert attempts==r['api_attempts']
        assert all(totals[k]==r['usage'][k] for k in totals)
        row={**r,'over_requested_budget_turns':over,'truncated_turns':truncated,
             'replay_verified':True,'score_verified':r['valid'],'public_context_verified':True}
        rows.append(row)
        public.append({'id':job['id'],'initial_messages':t['initial_messages'],'rounds':rounds,
                       'events':[{k:e[k] for k in ('seq','tool','arguments','result')} for e in a['events']]})
    protected=read(DEST/'protected_before.json')
    old_evidence=read(ROOT/'artifacts/benchmarks/v5/decision_difficulty_audit_001/source_sha256.json')
    protected.update(old_evidence)
    changed=[p for p,h in protected.items() if sha(ROOT/p)!=h]
    assert not changed,changed
    groups=[]
    for task,cond in sorted({(r['task'],r['condition']) for r in rows}):
        rs=[r for r in rows if (r['task'],r['condition'])==(task,cond)]
        groups.append(dict(task=task,condition=cond,n=len(rs),valid=sum(r['valid'] for r in rs),
            S=sum(bool(r['score'] and r['score']['S']) for r in rs),
            tool_errors=sum(len(r['score']['diagnostics']['tool_errors']) for r in rs if r['score']),
            mean_tool_calls=sum(r['tool_calls'] for r in rs)/len(rs)))
    output={'protocol_id':read(DEST/'protocol.json')['protocol_id'],'n':len(rows),'groups':groups,
        'api_attempts':sum(r['api_attempts'] for r in rows),'unknown_usage_attempts':sum(r['unknown_usage_attempts'] for r in rows),
        'usage':{k:sum(r['usage'][k] for r in rows) for k in ('prompt_tokens','completion_tokens','total_tokens','reasoning_tokens')},
        'invalid':sum(not r['valid'] for r in rows),'truncated_episodes':sum(bool(r['truncated_turns']) for r in rows),
        'over_budget_episodes':sum(bool(r['over_requested_budget_turns']) for r in rows),
        'protected_files_verified':len(protected),'changed_protected_files':changed,'results':rows}
    write(DEST/'analysis.json',output);write(DEST/'public_views.json',public)
    write(ROOT/'experiments/benchmarks/v5/decision_probe/results.json',output)
    print(json.dumps({k:v for k,v in output.items() if k!='results'},ensure_ascii=False,indent=2))

if __name__=='__main__':analyze()
