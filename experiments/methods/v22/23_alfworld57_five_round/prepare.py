"""Offline native identity freeze and prior-contact inventory; never a model call."""
from pathlib import Path
import sys, json, hashlib
from datetime import datetime, timezone
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE/'revision'))
from dotenv import load_dotenv
import os
from src.skill_evolution.v22.model_routing import model_route
from src.adapters.alfworld.skill_runtime import digest
from src.skill_evolution.v22.five_round_runtime import PROTOCOL,SIZES,STAGES

def read(p):return json.loads(p.read_text())
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def binding(p):return {'path':str(p.resolve()),'sha256':digest(p.read_bytes())}
load_dotenv(ROOT/'.env',override=False)
route=model_route(os.environ.get('OPENAI_BASE_URL',''),'deepseek-v4-flash','deepseek-v4-pro')
assert route['actor']==route['evolution']=='deepseek-flash' and route['base_url'].startswith('https://api.deepseek.com')
C=HERE/'config';C.mkdir(exist_ok=True)
sources=[ROOT/f'benchmarks/alfworld/editions/skillopt_39_18_134/{s}/items.json' for s in ['train','val']]
items=sum([read(p) for p in sources],[]); assert len(items)==57
manifest={'protocol':PROTOCOL,'sources':[binding(p) for p in sources], 'unique_tasks':57,
          'order':'native_train_manifest_then_native_val_manifest','environment_seed':42,'alias_seed':200,'rounds':[]}
i=0
for n,k in enumerate(SIZES,1):
    batch=items[i:i+k];i+=k
    manifest['rounds'].append({'round':n,'task_ids':[x['id'] for x in batch],'tasks':batch})
save(C/'task_manifest.json',manifest)
ids={x['id'] for x in items}; contacts={x:[] for x in ids}; skipped=0
# Inventory only archived development traces. No old outcomes or trace content
# enter the learner; preserve source identities rather than assert freshness.
for p in sorted((ROOT/'artifacts').rglob('trajectory.json')):
    if any(s in str(p).lower() for s in ['test_','/test/','/source_snapshot/','23_alfworld57_five_round']):continue
    try:r=read(p)
    except (ValueError,OSError):continue
    task=r.get('task',{}).get('id')
    if task in contacts:
        contacts[task].append({'trajectory':str(p.relative_to(ROOT)),'sha256':digest(p.read_bytes()),
             'run_id':r.get('run_id'),'split':r.get('split'),'purpose':r.get('purpose'),'model':r.get('model')})
# Include existing explicit exposure inventories, preserving their entire record
# independently; they may include semantic-only contacts without new episodes.
prior=ROOT/'experiments/methods/v22/11_unified_dsc_stream/config/task_inventory.json'
save(C/'prior_contact_inventory.json',{'created_at':datetime.now(timezone.utc).isoformat(),
 'scope':'Prior archived development episodes plus bound earlier exposure inventory; not a claim of never-seen tasks.',
 'learner_input':False,'prior_inventory':binding(prior),'contacts':contacts})
(C/'grouping_prompt.md').write_bytes((ROOT/'experiments/methods/v22/11_unified_dsc_stream/config/grouping_prompt.md').read_bytes())
plan=read(ROOT/'experiments/methods/v22/11_unified_dsc_stream/config/plan.json')
plan.update(protocol=PROTOCOL,status='authorized_formal_five_round',date='2026-10-16',update_profile='v22.unified_dsc.v6',
 input_encoding='v22.p1_shared_input.v1',reference_contract='v22.typed_references.v1',model_route=route)
plan['data']={'split':'train+val','purpose':'development','new_selection_episodes':36,'new_test_episodes':0,
 'task_manifest':'task_manifest.json','task_manifest_sha256':digest((C/'task_manifest.json').read_bytes()),
 'all_parent_slots_execute_fresh':True,'outcome_based_replacement':False,
 'selection_role':'Former Selection is now optimization/development; no independent selection claims.',
 'prior_contacts':'prior_contact_inventory.json; prior records remain intact, none imported as learner evidence.',
 **{f"round{x['round']}_task_ids":x['task_ids'] for x in manifest['rounds']}}
plan['models'].update(actor='deepseek-flash',evolution='deepseek-flash')
plan['classification']['model']='deepseek-flash'
plan['rounds']=[{'round':n,'parent':'initial No Skill' if n==1 else f'round{n-1} published Skill',
 'memory':'initial empty' if n==1 else f'round{n-1} published Memory','main_candidate_max':1,
 'fusion':'v6 model conditioned on current Memory, including empty Memory; Keep permitted',
 'semantic_calls_max':5,'episodes_max':2*k,'stage_calls_max':dict.fromkeys(STAGES,1)} for n,k in enumerate(SIZES,1)]
plan['budget'].update(rounds_max=5,tasks_per_round=SIZES,unique_tasks=57,environment_episodes_max=114,
 actor_logical_requests_max=5700,semantic_calls_max=25,logical_requests_max=5725,http_attempts_max=34225,
 semantic_output_tokens_max=983040,actor_output_tokens_max=5700*6*16384,actor_logical_output_tokens_max=5700*16384,
 model_context_tokens=1000000,monetary_cost=None,monetary_cost_status='Actual usage retained; no guaranteed monetary cost.')
plan['gate'].update(required_pairs=SIZES,eligibility='All declared pairs complete, provenance valid, matching recorded conditions; no-change uses complete Parent only.',
 scope='Overall promotion on current development batch; joint effects do not establish independent attribution.')
plan['replay']['condition_scope']='Within each round same native task, split, seed and configuration; no repeated task between rounds.'
plan['recovery']={'semantic_same_request_retries':0,'episode_retries':0,'on_exhaustion':'checkpoint_and_stop',
 'completed_stages':'reuse_only_with_identical_input_and_validated_artifacts','resume_after_failure':'stop_at_checkpoint_no_automatic_restart'}
plan['freeze'].update(implementation_ready=True,prepared_start='User authorized complete experiment; start exact unused preflight directory.',
 recovery='Frozen zero semantic/episode recovery budget. Technical failure saves checkpoint and stops; no new requests or repeated completed work.')
plan['stop_rules']=['No task replacement, outcome resampling, Prompt/algorithm/output repairs or independent Test use.',
 'Five rounds continue after legal ACCEPT/RETAIN/no_change; no semantic-quality early stop.',
 'Technical fault or capacity overflow saves all artifacts and costs, drains dispatched episodes, stops at exact stage.',
 'No automatic restart after technical failure: zero semantic/episode retry budget, existing bounded Actor HTTP policy retained.']
plan['claims_excluded']=['Causal benefit without ablation','Independent edit attribution from bundled outcomes',
 'Independent Selection evaluation','Generalization to unseen Test','Semantic correctness merely from contract validity']
plan['preparation_materials']=[{'path':p,'sha256':digest((C/p).read_bytes())} for p in
 ['prior_contact_inventory.json','../../11_unified_dsc_stream/config/task_inventory.json',
 '../../11_unified_dsc_stream/config/budget_evidence.json','../PROTOCOL.md','../prepare.py']]
save(C/'plan.json',plan)
print(json.dumps({'tasks':len(items),'sizes':SIZES,'prior_contact_tasks':sum(bool(v) for v in contacts.values()),'route':route}))
