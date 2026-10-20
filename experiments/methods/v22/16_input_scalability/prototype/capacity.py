"""Reproducible OFFLINE capacity scenarios; zero API/environment calls.
Synthetic rows are storage-shaped fixtures, NOT valid environment executions.
"""
from pathlib import Path
from copy import deepcopy
import json, sys, hashlib
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT/'experiments/methods/v22/12_contract_alignment/revision'))
from src.skill_evolution.v22.effective_memory import effective_consumption_payload
from src.skill_evolution.v22.contract_alignment import PROFILE
from views import compact, size, sha, lossless_pack, lossless_unpack, editor_role_view, history_cards, INSTRUCTIONS
OUT=ROOT/'artifacts/methods/v22/16_input_scalability'
D=ROOT/'artifacts/methods/v22/08_grouped_continual_fusion_resumed_20261015/rounds/r2'
R1=ROOT/'artifacts/methods/v22/08_grouped_continual_live_20261015/rounds/r1'
FREEZE=ROOT/'artifacts/methods/v22/15_unified_dsc_v3_editor_recovery_live_20261016/runtime_freeze.json'
read=lambda p:json.loads(p.read_text())
SYSTEM=read(FREEZE)['system_prompts']
STAGES=['classification','diagnosis','fusion','main_editor','post_gate_learning']
BASE={s:read(D/'inputs'/f'{s}.json') for s in STAGES}
EDITOR=read(D/'outputs/main_editor.json')
MEM=read(R1/'memory_after.json')


def view_for(stage,payload):
    p=deepcopy(payload)
    if stage=='classification': return p
    p['update_profile']=PROFILE
    if stage=='post_gate_learning':
        p['update_context']['editor']={k:deepcopy(EDITOR[k]) for k in ('decision','mappings','issues','watch')}
        p['sources']['editor']={'kind':'editor'}
    return p if stage=='diagnosis' else effective_consumption_payload(p)


def metric(stage,view,packed=False):
    system=SYSTEM[stage]['text']+ ('\n'+INSTRUCTIONS if packed else '')
    messages=[{'role':'system','content':system},{'role':'user','content':compact(view)}]
    content=sum(len(m['content']) for m in messages)
    # Coarse historical density range, NOT the DeepSeek tokenizer or a guarantee.
    return {'message_chars':size(messages),'content_chars':content,
            'token_estimate_range':[round(content/4),round(content/2)],
            'token_estimator':'offline broad sensitivity range: 2-4 content chars/token; excludes provider framing; not model-tokenizer counts',
            'over_300k':size(messages)>300000,'over_400k':size(messages)>400000,
            'sha256':sha(messages)}


def compare(stage,view):
    packed=lossless_pack(view)
    assert lossless_unpack(packed)==view
    results={'v3':metric(stage,view),'lossless':metric(stage,packed,True)}
    role=editor_role_view(view) if stage=='main_editor' else view
    role_packed=lossless_pack(role);assert lossless_unpack(role_packed)==role
    results['role']=metric(stage,role_packed,True)
    # Deliberately incomplete lower-cost bound, not a recommended deployment.
    if stage in ('fusion','main_editor','post_gate_learning'):
        cards=history_cards(role); cp=lossless_pack(cards);assert lossless_unpack(cp)==cards
        results['cards_only_insufficient']=metric(stage,cp,True)
    results['coverage']={'lossless_roundtrip':True,'current_event_count':sum(len(r['steps']) for r in view.get('runs',{}).values()),
                         'role_omits_evidence':stage=='main_editor','cards_have_full_historical_basis':False,
                         'archive_digest':sha(view)}
    return results


def replace_strings(x, substitutions):
    if isinstance(x,str):
        for before,after in substitutions.items():x=x.replace(before,after)
        return x
    if isinstance(x,list):return [replace_strings(v,substitutions) for v in x]
    if isinstance(x,dict):return {k:replace_strings(v,substitutions) for k,v in x.items()}
    return x


def histories(round_index,mode):
    """Fixed three claims with accumulating basis OR three new effects per round.
    No actual historical trial is counted again as independent support.
    """
    if round_index==1:return []
    result=[]
    for i,original in enumerate(MEM):
        accumulated=[]
        for h in range(1,round_index):
            context=f'synthetic_history_round_{h}'
            e=deepcopy(original)
            changes={b['context_id']:context for b in e['basis']}
            e=replace_strings(e,changes)
            for b in e['basis']:
                b['context_id']=context
                # All bases for one context must reference the same joint update.
                b['actual_update']=replace_strings(deepcopy(MEM[0]['basis'][0]['actual_update']),
                                                   {MEM[0]['basis'][0]['context_id']:context})
                b['actual_update']['synthetic_fixture']=True
                for src in b['sources'].values():
                    if isinstance(src,dict) and 'run_id' in src:
                        src['run_id']=f'synthetic:h{h}:'+src['run_id']
                        if 'observation' in src:
                            src['observation'] += (' [SYNTHETIC response: new candidate became visible and the target action completed.]' if h%2 else ' [SYNTHETIC counterexample: a fresh candidate was available; target action repeated without progress and a prior opportunity was missed.]')
            accumulated.extend(e['basis'])
            e['id']=f'synthetic:h{h}:effect{i+1}';e['claim_context_id']=context
            # Contradictory *interpretations* plus explicit untested condition.
            # They are synthetic and never represented as measured effects.
            e['claim']=('SYNTHETIC: Under comparable fresh-observation conditions, increasing exploration improved target progress.' if h%2 else 'SYNTHETIC: Under comparable fresh-observation conditions, increasing exploration did not improve target progress and displaced a previously effective action.') + f' Evidence family {i+1}; conflicting interpretations are retained, not reconciled by the fixture.'
            e['limits']=original['limits']+[f'SYNTHETIC h{h}: condition without a new observable alternative remains untested; joint attribution only.']
            e['limit_contexts']=[context]*len(e['limits'])
            if mode=='growing_effects':result.append(e)
            elif h==round_index-1:
                e['basis']=deepcopy(accumulated)
                # Keep every synthetic round's new uncertainty even with a fixed count.
                e['limits'] += [f'SYNTHETIC h{k}: older untested boundary remains active.' for k in range(1,h)]
                e['limit_contexts'] += [f'synthetic_history_round_{k}' for k in range(1,h)]
                result.append(e)
    return result


def scenario_payload(stage,n,round_index,trajectory,history):
    p=deepcopy(BASE[stage]); p['synthetic_fixture']={'not_executed':True,'round':round_index,'task_count':n,
        'trajectory_scenario':trajectory,'history_scenario':history,'source':'08 r2 structure and verbatim seed events; transformations are synthetic'}
    def grow_steps(steps,alias):
        steps=deepcopy(steps)
        if trajectory!='observed_mix':
            original=deepcopy(steps)
            steps=(original+[deepcopy(next((e for e in reversed(original) if not e.get('done')),original[-1])) for _ in range(50)])[:50]
            for j,e in enumerate(steps,1):
                e['step']=j
                if j<len(steps): e['done']=False;e['won']=False;e['reward']=0
                if trajectory=='diverse50':e['observation'] += f' [SYNTHETIC distinct condition {alias}/{j}: new visible state changes this opportunity.]'
                if trajectory=='wide50':
                    e['observation']+=' '+('SYNTHETIC visible detail, not actual execution. '*14)+f'Unique opportunity {alias}/{j}.'
                    key=f'synthetic_{alias}_{j}'
                    p['command_sets'][key]=p['command_sets'][e['commands']]+[f'synthetic available operation {alias}/{j}/{k}' for k in range(80)]
                    e['commands']=key
        return steps
    if stage=='classification':
        rows=p['experiences'];p['experiences']=[]
        for i in range(n):
            row=deepcopy(rows[i%len(rows)]);row['task_ref']=f'T{i+1}'
            row['steps']=grow_steps(row['steps'],row['task_ref']);p['experiences'].append(row)
        return p
    runs=p['runs'];p['runs']={}
    sides=['P','C'] if stage=='post_gate_learning' else ['P']
    for side in sides:
        old=[r for alias,r in runs.items() if alias.startswith(side)]
        for i in range(n):
            row=deepcopy(old[i%len(old)]);alias=f'{side}{i+1}'
            row.update(run_id=f'synthetic:r{round_index}:{alias}',task_id=f'synthetic:r{round_index}:task{i+1}')
            row['steps']=grow_steps(row['steps'],alias);p['runs'][alias]=row
    p['sources']={k:v for k,v in p['sources'].items() if v.get('kind')!='event'}
    p['sources'].update({f'{alias}:{step}':{'kind':'event','run':alias,'step':step} for alias,run in p['runs'].items() for step in [0]+[e['step'] for e in run['steps']]})
    # Seed source metadata/group prose are retained verbatim for volume, not asserted
    # to classify the added synthetic tasks. This is not runnable campaign input.
    if stage=='post_gate_learning':
        p['pairs']=[{'task_id':f'synthetic:r{round_index}:task{i+1}','parent':f'P{i+1}','candidate':f'C{i+1}',
                     'recorded_conditions_match':True,'differences':[]} for i in range(n)]
    if stage not in ('classification','diagnosis'):p['memory']=histories(round_index,history)
    else:p.pop('memory',None)
    return p


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[]
    for stage in STAGES:
        view=view_for(stage,BASE[stage]);rows.append({'kind':'08_reencoded_v3_counterfactual_not_live','stage':stage,'metrics':compare(stage,view)})
    for trajectory in ('observed_mix','repeat50','diverse50','wide50'):
        for history in ('fixed_effects','growing_effects'):
            for rnd,n in enumerate((12,12,12,12,9),1):
                for stage in STAGES:
                    payload=scenario_payload(stage,n,rnd,trajectory,history);view=view_for(stage,payload)
                    row={'kind':'SYNTHETIC_CAPACITY_ONLY','round':rnd,'tasks':n,'trajectory':trajectory,'history':history,'stage':stage,
                         'effects':len(view.get('memory',[])),'basis':sum(len(e['basis']) for e in view.get('memory',[])),
                         'metrics':compare(stage,view)}
                    rows.append(row)
    (OUT/'capacity_results.json').write_text(json.dumps({'scope':'offline volume and representation fidelity, not semantic/environment validity',
        'fixtures':'All five-round rows are synthetic. Added tasks are not real selected Train/Selection tasks. No model calls, no valid Gate.',
        'round_sizes':[12,12,12,12,9],'rows':rows},ensure_ascii=False,indent=2)+'\n')
    print('capacity rows',len(rows),'all lossless roundtrips passed')
    for t in ('observed_mix','repeat50','diverse50','wide50'):
        sample=[r for r in rows if r.get('trajectory')==t and r.get('history')=='growing_effects']
        print(t,{s: [(r['round'],r['metrics']['v3']['message_chars'],r['metrics']['role']['message_chars']) for r in sample if r['stage']==s] for s in STAGES})

if __name__=='__main__':main()
