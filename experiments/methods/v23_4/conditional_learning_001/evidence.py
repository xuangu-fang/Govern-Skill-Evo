"""Deterministic facts for the unified review; no model grading or output edits."""
import json
from .run import HERE,P4,P6,core

def small_step(step):
    out={k:v for k,v in step.items() if k in ('step','action','feedback')}
    if len(out.get('action',''))>200:out['action']='[malformed long action omitted in this review extract; original archive unchanged]'
    return out

def main():
    out={}
    for case in ('R05','R06'):
        v=core.read(P4/f'cases/{case}/model_input.json');runs={r['ref']:r for r in v['runs']}
        data={'actual_diff':v['diff'],'pairs':v['pairs'],'current_actions':{},'history_summaries':{},'outputs':{}}
        ids=['P6','Q6','P7','Q7','P8','Q8','P9','Q9','P10','Q10'] if case=='R05' else list(runs)
        for rid in ids:
            r=runs[rid];data['current_actions'][rid]={'task':r['task'],'outcome':r['outcome'],'steps':[small_step(s) for s in r['steps']]}
        historical=['S1_R03/P2','S1_R03/Q2','S1_R03/P4','S1_R03/Q4','S1_R03/P6','S1_R03/Q6'] if case=='R05' else ['S1_R03/P7','S1_R03/Q7','S1_R04/P2','S1_R04/Q2','S1_R05/P6','S1_R05/Q6','S1_R05/P7','S1_R05/Q7','S1_R05/P8','S1_R05/Q8','S1_R05/P10','S1_R05/Q10']
        for key in historical:
            s=v['memory']['sources'][key];r=s['run']
            data['history_summaries'][key]={'task':r['task'],'outcome':r['outcome'],'windows':s['windows'],'steps':[small_step(t) for t in r['trace']]}
        if case=='R05':
            s=runs['P8']['steps'][7];data['P8_direct_open']={**s,'before_menu':v['command_sets'][s['before']['commands_ref']]}
            absent=[]
            for rid in ['P7','Q7','P8','Q8']:
                r=runs[rid];action='go to shelf 1' if rid.endswith('8') else 'go to cabinet 18'
                absent.append({'run':rid,'listed_action':action,'available':action in v['command_sets'][r['initial']['commands_ref']],
                 'visited':any(t['action']==action for t in r['steps'])})
            data['unvisited_current_locations']=absent
        else:
            r=v['memory']['sources']['S1_R05/Q7']['run'];action='go to cabinet 18'
            data['historical_butterknife_unvisited']={'available':action in v['memory']['command_pool'][r['initial']['commands_ref']],
                'visited':any(s['action']==action for s in r['trace'])}
        for version,root in [('p4_baseline',P6),('candidate',HERE)]:
            selected=core.read(root/f'runs/{case}_replay/selected.json')['attempt']
            proposal=core.read(root/f'runs/{case}_replay/attempt_{selected:03}/parsed.json')
            items=[]
            for i,e in enumerate(proposal['entries']):
                for j,k in enumerate(e['knowledge']):
                    items.append({'jsonpath':f'entries[{i}].knowledge[{j}]','revises':e['revises'],**k})
            refs={r for e in proposal['entries'] for k in e['knowledge'] for r in k['evidence']}
            data['outputs'][version]={'file':str((root/f'runs/{case}_replay/attempt_{selected:03}/parsed.json').relative_to(HERE.parent)),
              'items':items,'current_runs_cited':sorted({r.split(':')[0] for r in refs if '/' not in r and ':' in r}),
              'P8_8_cited':'P8:8' in refs,'Q7_25_cited':'Q7:25' in refs}
        out[case]=data
    (HERE/'EVIDENCE.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print('Saved visible facts and exact unchanged proposal excerpts')

if __name__=='__main__':main()
