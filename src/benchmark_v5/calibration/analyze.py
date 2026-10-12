"""Post-run descriptive analysis and independent archive replay, no API calls."""
import argparse
from collections import Counter
from itertools import combinations
import math
import json
from copy import deepcopy
from pathlib import Path
import random
import statistics

from benchmark_v5.core import verify_audit
from benchmark_v5.session import build, AgentSession
from benchmark_v5.evaluation import evaluate
from .runner import read, write, verify_freeze, initial_messages


def wilson(k, n):
    if not n: return None
    z=1.959963984540054
    p=k/n; d=1+z*z/n
    center=(p+z*z/(2*n))/d
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0,center-half),min(1,center+half)]


def proportion(rows, metric):
    values=[r['score'][metric] for r in rows if r['valid'] and r['score'][metric] is not None]
    return {'k':sum(values),'n':len(values),'rate':sum(values)/len(values) if values else None,
            'wilson95_descriptive':wilson(sum(values),len(values))}


def summary(rows):
    return {'planned_n':len(rows),'valid_n':sum(r['valid'] for r in rows),
            'metrics':{k:proportion(rows,k) for k in ('S','C','P_complete','full_compliant_service')},
            'quadrants':dict(Counter(r['score']['quadrant'] for r in rows if r['valid'] and r['score']['quadrant'])),
            'usage':{k:sum(r['usage'][k] for r in rows) for k in ('prompt_tokens','completion_tokens','total_tokens','reasoning_tokens')},
            'api_attempts':sum(r['api_attempts'] for r in rows),
            'unknown_usage_attempts':sum(r['unknown_usage_attempts'] for r in rows),
            'mean_tool_calls':statistics.mean(r['tool_calls'] for r in rows),
            'mean_model_turns':statistics.mean(r['model_turns'] for r in rows),
            'median_episode_seconds':statistics.median(r['wall_seconds'] for r in rows),
            'stop_reasons':dict(Counter(r['stop'] for r in rows)), 'truncated_turns':sum(r.get('truncated_turns',0) for r in rows),
            'budget_nonconformant_episodes':sum(bool(r.get('budget_excess_responses')) for r in rows),
            'budget_conformant_valid_n':sum(r['valid'] and not r.get('budget_excess_responses') for r in rows),
            'budget_conformant_metrics':{k:proportion([r for r in rows if not r.get('budget_excess_responses')],k) for k in ('S','C','P_complete','full_compliant_service')}}


def analyze(directory):
    verify_freeze()
    frozen=read(directory/'freeze.json')
    config=read(directory/'protocol.json')
    rows=[]; proofs=[]
    for job in frozen['jobs']:
        d=directory/job['id']
        r=read(d/'result.json'); a=read(d/'audit.json'); t=read(d/'trace.json')
        assert r['id']==job['id']
        verify_audit(a)
        replay=build(r['task'],a['scenario'])
        for event in a['events']:
            if event['tool']=='__end__':replay.end_budget()
            else:assert replay.call(event['tool'],event['arguments'])==event['result']
        assert replay.audit()==a
        assert (evaluate(a) if r['valid'] else None)==r['score']
        session=AgentSession(build(r['task'],a['scenario']))
        expected_messages=initial_messages(config,r,session)
        assert t['initial_messages']==expected_messages
        assert t['tools']==[{'type':'function','function':tool} for tool in session.tools]
        native_calls=[]
        executed=[]
        for round_ in t['rounds']:
            assert round_['request']['messages']==expected_messages
            assert round_['request']['tools']==t['tools']
            assert round_['request']['model']==r['model']
            assert round_['request']['temperature']==config['temperature']
            assert round_['request']['reasoning_effort']==config['reasoning_effort']
            assert not any(m['role'] not in ('system','user','assistant','tool') for m in round_['request']['messages'])
            attempts=round_['attempts']
            good=[x for x in attempts if 'response' in x]
            if good:
                msg=good[-1]['response']['choices'][0]['message']
                assistant={'role':'assistant','content':msg.get('content')}
                if msg.get('reasoning_content'):assistant['reasoning_content']=msg['reasoning_content']
                tc=msg.get('tool_calls') or []
                if tc:assistant['tool_calls']=[{k:c[k] for k in ('id','type','function')} for c in tc]
                expected_messages.append(assistant)
                for call, output in zip(tc,round_.get('tool_results',[])):
                    assert output['tool_call_id']==call['id']
                    native_calls.append(call['function'])
                    expected_messages.append({'role':'tool','tool_call_id':call['id'],'content':json.dumps(output['result'],ensure_ascii=False)})
                    if output['result'].get('error') not in ('SESSION_CLOSED','CALL_BUDGET_EXHAUSTED'):
                        fn=call['function']
                        try:args=json.loads(fn['arguments'])
                        except json.JSONDecodeError:args=None
                        executed.append((fn['name'],args,output['result']))
        assert executed==[(e['tool'],e['arguments'],e['result']) for e in a['events'] if e['tool']!='__end__']
        assert r['tool_calls'] <= len(native_calls)
        assert r['api_attempts']==sum(len(x['attempts']) for x in t['rounds'])
        r['budget_excess_responses']=[{'turn':rnd['turn'],'requested_max_tokens':rnd['request']['max_tokens'],
            'reported_completion_tokens':x['response']['usage']['completion_tokens']} for rnd in t['rounds'] for x in rnd['attempts']
            if 'response' in x and x['response']['usage']['completion_tokens']>rnd['request']['max_tokens']]
        r['observed_finish_reasons']=[x['response']['choices'][0].get('finish_reason') for rnd in t['rounds'] for x in rnd['attempts'] if 'response' in x]
        r['truncated_turns']=sum(reason=='length' for reason in r['observed_finish_reasons'])
        rows.append(r)
        proofs.append({'id':r['id'],'audit_replay_exact':True,'grade_recomputed':True,'public_messages_reconstructed':True,'native_calls_match_audit':True,
                       'tool_errors':[{'seq':e['seq'],'tool':e['tool'],'error':e['result']['error']} for e in a['events'] if isinstance(e['result'],dict) and 'error' in e['result']],
                       'tool_sequence':[e['tool'] for e in a['events']]})
    groups=[]
    for cond in config['conditions']:
        for model in config['models']:
            subset=[r for r in rows if r['condition']==cond and r['model']==model]
            groups.append({'condition':cond,'model':model,'task':'ALL',**summary(subset)})
            for task in config['tasks']:
                groups.append({'condition':cond,'model':model,'task':task,**summary([r for r in subset if r['task']==task])})
    paired=[]
    for m1,m2 in combinations(config['models'],2):
        diffs=[]
        for task in config['tasks']:
            sub=lambda m:[r for r in rows if r['condition']=='baseline' and r['model']==m and r['task']==task and r['valid']]
            x,y=sub(m1),sub(m2)
            if len(x)==len(y)==3:
                diffs.append(sum(r['score']['S'] for r in x)/3-sum(r['score']['S'] for r in y)/3)
        rng=random.Random(20261010)
        samples=sorted(statistics.mean(rng.choices(diffs,k=len(diffs))) for _ in range(10000)) if diffs else []
        paired.append({'models':[m1,m2],'paired_family_count':len(diffs),'family_S_differences':diffs,
            'mean_S_difference':statistics.mean(diffs) if diffs else None,
            'family_bootstrap95_descriptive':[samples[249],samples[9749]] if samples else None,
            'warning':'Very few Dev families; zero-width bootstrap under saturation does not establish equivalence.'})
    out={'protocol_id':config['protocol_id'],'n':len(rows),'total':summary(rows),'groups':groups,
         'paired_baseline':paired,'archive_validation':proofs,'results':rows}
    write(directory/'analysis.json',out)
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path)
    a=analyze(parser.parse_args().directory)
    print({'n':a['n'],'total':a['total']})
