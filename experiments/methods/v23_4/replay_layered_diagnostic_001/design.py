"""Deterministic evidence extraction and private answer key. No network calls."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from experiments.methods.v23_4.archive_io import archive_glob, resolve

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
P6 = HERE.with_name('multi_knowledge_p6_001')
RCA = HERE.with_name('p6_root_cause_analysis_001')

QUESTIONS = {
 'R05': [
  {'id':'T1','question':'For current Q7:25 and historical S1_R04/Q6:25, identify each task, action, observable preceding state, admissibility and feedback. What relationship, if any, do these records establish between the two executions?'},
  {'id':'T2','question':'Examine P8:8 within its paired task. What navigation and manipulation choices concerning cabinet 3 are recorded before the action, what was executed, and what response followed? What does this pair establish about behavior relevant to the added Admissible Actions guidance?'},
  {'id':'T3','question':'Using the Parent Skill and actual Diff, describe the placement and applicability of Admissible Actions and the revised search requirements. How should the pillow-with-desklamp pair be interpreted in relation to these changes?'},
  {'id':'T4','question':'What do current P8/Q8 and the related historical Memory establish about the requested soapbar\'s availability, explored locations and task outcomes? State the basis and scope of the conclusions and any unresolved points.'},
  {'id':'T6','question':'Compare current P10/Q10 across search and acquisition, conditioning, and placement. What differs or is preserved, and how do the total action counts relate to the actual guidance changes?'}],
 'R06': [
  {'id':'T4','question':'What do historical S1_R05/P7 and S1_R05/Q7 and the associated Memory establish about the requested butterknife\'s availability, explored locations and task outcomes? State the basis and scope of the conclusions and any unresolved points.'},
  {'id':'T5','question':'Compare the historical heat-plate pair S1_R04/P2 and S1_R04/Q2 in relation to its actual edit. Describe each side\'s target acquisition, conditioning behavior, task result and action count. What edit-related interpretation does the comparison support, and what remains unresolved?'},
  {'id':'T6','question':'Compare current P2/Q2 across search and acquisition, conditioning, and placement. What differs or is preserved, and how do the total action counts relate to the actual guidance changes?'}]
}

SYSTEM = '''Answer the diagnostic questions using the supplied evidence. This is an isolated reading and interpretation task, not a request to generate Memory updates. Use original source identifiers and return exactly one JSON object with this shape:
{"answers":[{"id":"question ID","facts":[{"sources":["source reference"],"text":"observed fact"}],"conditions":"applicable conditions","comparison":"relevant comparison","conclusion":"supported judgment","uncertainty":"unresolved issues, or none"}]}
Include exactly one answer for each supplied question. Keep each answer concise, approximately 100–180 words. Sources may identify an execution step or run, parent, diff, plan, or an existing Memory ID. Do not output commentary outside the JSON.
'''


def read(p): return json.loads(resolve(p).read_text())
def sha(p): return hashlib.sha256(resolve(p).read_bytes()).hexdigest()
def save(p,value):
    p=resolve(p)
    p.parent.mkdir(parents=True,exist_ok=True)
    encoded=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    if p.exists(): assert p.read_text()==encoded, f'Immutable artifact differs: {p}'
    else: p.write_text(encoded)
def compact(o): return json.dumps(o,ensure_ascii=False,separators=(',',':'))


def actual(case):
    selected=read(P6/f'runs/{case}_replay/selected.json')['attempt']
    request=read(P6/f'runs/{case}_replay/attempt_{selected:03}/http/request.json')
    messages=request['body']['messages']
    assert json.loads(messages[1]['content'])==read(HERE.with_name('multi_knowledge_p4_001')/f'cases/{case}/model_input.json')
    return request,messages,json.loads(messages[1]['content'])


def local(view,case):
    result=deepcopy(view)
    ids=({'P2','Q2','P7','Q7','P8','Q8','P10','Q10'} if case=='R05' else {'P2','Q2'})
    result['runs']=[r for r in view['runs'] if r['ref'] in ids]
    result['pairs']=[p for p in view['pairs'] if p['parent'] in ids and p['candidate'] in ids]
    menus=set()
    for r in result['runs']:
        menus.update(s['commands_ref'] for s in [r['initial'],*[t[side] for t in r['steps'] for side in ('before','after')]])
    result['command_sets']={k:v for k,v in view['command_sets'].items() if k in menus}
    memory=result['memory']; old=view['memory']
    mids={'M8'} if case=='R05' else {'M7','M10'}
    memory['entries']=[e for e in old['entries'] if e['id'] in mids]
    keys=set()
    for e in memory['entries']:
        for k in e['knowledge']:
            keys.update(ref.split(':')[0] for ref in k['evidence'])
    if case=='R05': keys.update(('S1_R04/P6','S1_R04/Q6'))
    keys.update(k.rsplit('/',1)[0]+'/diff' for k in list(keys))
    memory['sources']={k:s for k,s in old['sources'].items() if k in keys}
    assert keys==set(memory['sources'])
    used=set()
    for key,s in memory['sources'].items():
        if key.endswith('/diff'): continue
        used.update(state['commands_ref'] for state in [s['run']['initial'],*[t[side] for t in s['detailed_steps'] for side in ('before','after')]])
    memory['command_pool']={k:v for k,v in old['command_pool'].items() if k in used}
    memory['pairs']=[p for p in old['pairs'] if p['parent'] in keys and p['candidate'] in keys]
    paired={p[side] for p in memory['pairs'] for side in ('parent','candidate')}
    memory['unpaired_runs']=[k for k in memory['sources'] if not k.endswith('/diff') and k not in paired]
    for k,s in memory['sources'].items(): assert s==old['sources'][k]
    for r in result['runs']: assert r==next(x for x in view['runs'] if x['ref']==r['ref'])
    return result


def standards(views):
    rca=read(RCA/'EVIDENCE.json')
    expected={
      'R05':{
       'T1':{'core':['Q7:25: current butterknife task; go to drawer 2; admissible=true; arrives at open empty drawer 2.',
                    'S1_R04/Q6:25: historical two-candle task; before drawer 7; go to drawer 8; admissible=false; Nothing happens.',
                    'Different sources/tasks; no paired/counterpart relationship between these two events.'],
             'refs':['Q7:25','S1_R04/Q6:25'],'applicability_na':True},
       'T2':{'core':['P8:8 before menu lacks go to cabinet 3 but includes open cabinet 3.',
                    'Parent opens cabinet 3 legally, obtains empty-content observation; observed direct-action behavior exists before edit.',
                    'Q8:39 remains illegal navigation; no independent proof of added guidance causing success or gain; intent and optimality unknown.'],
             'refs':['P8:8','Q8:39','Q8:40','diff']},
       'T3':{'core':['Admissible Actions is a separate global heading before non-desklamp procedure.',
                    'Search changes belong to explicitly non-desklamp section.',
                    'Pillow Pair succeeds 5 vs 6, extra initial desk visit; not an in-scope test of the search clause; global guidance could apply without proof of effect.'],
             'refs':['parent','diff','P2','Q2']},
       'T4':{'core':['P8/Q8 both fail at 50 without soapbar acquisition; substitutes not manipulated.',
                    'Initial shelf 1 is available and never visited; cannot establish global nonexistence.',
                    'Old Memory interpretations are historical conditional claims, not proof of present task object availability.'],
             'refs':['P8:0','Q8:0','P8:50','Q8:50','M8']},
       'T6':{'core':['P10 succeeds14, acquires apple9; Q10 succeeds11, acquires6.',
                    'After acquisition five actions identical; three-action difference is search, no extra cooling improvement.',
                    'Consistent with search guidance; simultaneous edits and single runs do not isolate causal contribution.'],
             'refs':['P10','Q10','diff']}},
      'R06':{
       'T4':{'core':['Historical S1_R05/P7/Q7 both fail50; no exact butterknife acquired.',
                    'Q7 initial cabinet18 available but never visited, other coverage incomplete; not-found does not establish global absence.',
                    'Old M10 no exact butterknife was present is stronger than source supports; distinguish local visible knife from global availability.'],
             'refs':['S1_R05/P7','S1_R05/Q7','M10']},
       'T5':{'core':['S1_R04/P2 takes plate from countertop3 at4, heats11, succeeds13.',
                    'Q2 never reaches countertop3, never acquires/heats plate, fails50.',
                    'Candidate lacks conditioning opportunity, Parent has it; retain asymmetric outcome, cannot attribute discovery failure independently to temperature change.',
                    'P2:4 has trace action/feedback, not full before/after/menu in input.'],
             'refs':['S1_R04/diff','S1_R04/P2','S1_R04/Q2','M7']},
       'T6':{'core':['Current P2 succeeds18, acquires tomato13; Q2 succeeds10, acquires5.',
                    'Both direct cool at open fridge (P2:15/Q2:7); same five post-acquisition actions; zero additional local cooling saving.',
                    'Eight-action difference before acquisition; overall difference is not isolated causal effect of thermal rule.'],
             'refs':['P2','Q2','diff']}}
    }
    # Deterministic facts independently checked before issuing any request.
    for case,v in views.items():
        runs={r['ref']:r for r in v['runs']}
        if case=='R05':
            assert runs['Q7']['steps'][24]['action']=='go to drawer 2'
            assert runs['Q7']['steps'][24]['feedback']['action_in_admissible_commands'] is True
            src=v['memory']['sources']['S1_R04/Q6']
            assert src['run']['trace'][24]['action']=='go to drawer 8' and src['run']['trace'][24]['feedback']['action_in_admissible_commands'] is False
            s=runs['P8']['steps'][7];m=v['command_sets'][s['before']['commands_ref']]
            assert s['action']=='open cabinet 3' and 'open cabinet 3' in m and 'go to cabinet 3' not in m
            for rid in ('P8','Q8'):
                r=runs[rid];assert len(r['steps'])==50 and not r['outcome']['success']
                assert 'go to shelf 1' in v['command_sets'][r['initial']['commands_ref']]
                assert not any(s['action']=='go to shelf 1' for s in r['steps'])
            assert [s['action'] for s in runs['P10']['steps'][9:]]==[s['action'] for s in runs['Q10']['steps'][6:]]
            assert len(runs['P10']['steps'])==14 and len(runs['Q10']['steps'])==11
        else:
            for rid,count,success in [('S1_R04/P2',13,True),('S1_R04/Q2',50,False),('S1_R05/P7',50,False),('S1_R05/Q7',50,False)]:
                r=v['memory']['sources'][rid]['run'];assert len(r['trace'])==count and r['outcome']['success'] is success
            s=v['memory']['sources']['S1_R05/Q7'];assert 'go to cabinet 18' in v['memory']['command_pool'][s['run']['initial']['commands_ref']]
            assert not any(t['action']=='go to cabinet 18' for t in s['run']['trace'])
            assert [s['action'] for s in runs['P2']['steps'][13:]]==[s['action'] for s in runs['Q2']['steps'][5:]]
            assert len(runs['P2']['steps'])==18 and len(runs['Q2']['steps'])==10
    return {'expected':expected,'source_evidence':rca['cases'],
            'dimensions':['source_binding','factual_accuracy','applicability','conclusion_strength','behavior_comparison','uncertainty'],
            'scale':{'2':'meets criterion','1':'partial or material omission','0':'contradiction or unsupported claim','null':'not applicable'},
            'note':'PRIVATE. Never included in model messages. Semantic evaluation is manual, not keyword scoring.'}


def prepare():
    views={};measure={};config=None
    for case in ('R05','R06'):
        req,old,v=actual(case);views[case]=v
        cfg=read(P6/'config/freeze.json')['call_config']
        assert {k:val for k,val in req['body'].items() if k!='messages'}=={k:val for k,val in cfg.items() if k not in ('endpoint','timeout_seconds')}
        config=cfg
        suffix=old[0]['content'][old[0]['content'].index('## Execution Context'):]
        system=SYSTEM+'\n'+suffix
        save(HERE/f'config/{case}/questions.json',QUESTIONS[case])
        for arm in ('A','B'):
            evidence=local(v,case) if arm=='A' else v
            evidence_text=compact(evidence) if arm=='A' else old[1]['content']
            # Preserve B's complete serialized evidence exactly; framing identical in both arms.
            user='{"questions":'+compact(QUESTIONS[case])+',"evidence":'+evidence_text+'}'
            messages=[{'role':'system','content':system},{'role':'user','content':user}]
            body={k:val for k,val in cfg.items() if k not in ('endpoint','timeout_seconds')}
            body['messages']=messages
            save(HERE/f'config/{case}_{arm}/request.json',{'endpoint':cfg['endpoint'],'body':body})
            save(HERE/f'config/{case}_{arm}/evidence.json',evidence)
            assert json.loads(user)=={'questions':QUESTIONS[case],'evidence':evidence}
            assert 'expected' not in json.loads(user) and 'source_evidence' not in json.loads(user)
            measure[f'{case}_{arm}']={'evidence_chars':len(evidence_text),'user_chars':len(user),
                'current_runs':len(evidence['runs']),'history_runs':sum(not k.endswith('/diff') for k in evidence['memory']['sources']),
                'current_pairs':len(evidence['pairs']),'history_pairs':len(evidence['memory']['pairs']),
                'history_entries':[e['id'] for e in evidence['memory']['entries']]}
    save(HERE/'private/standard_facts.json',standards(views))
    save(HERE/'config/input_checks.json',measure)
    protected=read(RCA/'READ_ONLY_BEFORE.json')
    for p in RCA.rglob('*'):
        if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
    assert all(sha(ROOT/p)==d for p,d in protected.items())
    save(HERE/'protected_before.json',protected)
    files=[*HERE.glob('*.py'),HERE/'PROTOCOL.md',*archive_glob(HERE/'config', '*.json', recursive=True),HERE/'private/standard_facts.json']
    inherited=read(P6/'config/freeze.json')['sha256']
    save(HERE/'freeze.json',{'at':datetime.now(timezone.utc).isoformat(),'max_http':8,'call_config':config,
        'sha256':{**inherited,**{str(p.relative_to(ROOT)):sha(p) for p in files}}})
    print(json.dumps(measure,indent=2))


if __name__=='__main__':prepare()
