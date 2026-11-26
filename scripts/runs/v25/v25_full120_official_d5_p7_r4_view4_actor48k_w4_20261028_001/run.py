"""Official-endpoint V25 campaign; production method and prompts are unchanged."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'artifacts/methods/v25/v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001'
PRIOR=ROOT/'experiments/methods/v25/v25_two_round_exploration_20261028_001/config'
sys.path.insert(0,str(ROOT))
from dotenv import load_dotenv
from src.skill_evolution.v25 import evolution as ev
from src.skill_evolution.v25.baseline import validate_latest_configuration
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from src.skill_evolution.v25.contracts.model_routing import route_call_config


def check_config(cfg):
    old=ev.read(PRIOR/'config.json')
    expected=deepcopy(old)
    expected.pop('comparison_profile')
    expected['actor_base_url']='https://api.deepseek.com'
    expected['actor_model']='deepseek-flash'
    expected['call_config']=route_call_config(old['call_config'],expected['actor_base_url'])
    assert cfg==expected, 'Only the documented endpoint adaptation is allowed'
    # The existing optional comparison label hard-codes the internal endpoint.
    # Enforce its full non-routing constraints using an explicitly normalized copy.
    normalized=deepcopy(cfg)
    for name in ['comparison_profile','actor_base_url','actor_model','call_config']:
        normalized[name]=old[name]
    assert normalized==old
    validate_latest_configuration(normalized)
    ev.validate_config(cfg)
    ev.check_environment_route(cfg)
    assert len(cfg['batches'])==8 and all(len(b)==15 for b in cfg['batches'])
    assert all(not t.startswith('test:') for b in cfg['batches'] for t in b)
    assert cfg['continue_no_change'] is True
    assert cfg == ev.read(ROOT / 'experiments/methods/v25/v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001/config/config.json'), 'Published official configuration differs'


def freeze_check():
    cfg=ev.read(OUT/'config.json');check_config(cfg)
    for name,digest in ev.read(OUT/'manifest.json')['files'].items():
        assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==digest,name
    return cfg


def prepare():
    assert not (OUT/'manifest.json').exists()
    old=ev.read(PRIOR/'config.json');cfg=deepcopy(old)
    cfg.pop('comparison_profile')
    cfg['actor_base_url']='https://api.deepseek.com';cfg['actor_model']='deepseek-flash'
    cfg['call_config']=route_call_config(old['call_config'],cfg['actor_base_url'])
    check_config(cfg);ev.check_live_environment(cfg)
    ev.save(OUT/'config.json',cfg)
    ev.save(OUT/'contract.json',ev.frozen_contract())
    runtime=ev.runtime_snapshot(cfg)
    assert runtime==ev.read(PRIOR/'runtime.json')
    ev.save(OUT/'runtime.json',runtime)
    ev.save(OUT/'route_change.json',{
        'previous_config':str(PRIOR/'config.json'),
        'previous_config_sha256':hashlib.sha256((PRIOR/'config.json').read_bytes()).hexdigest(),
        'endpoint':'https://api.deepseek.com/chat/completions','model':'deepseek-flash',
        'removed_metadata':{'comparison_profile':old['comparison_profile']},
        'reason':'Existing optional comparison label fixes the intranet endpoint; all its non-routing checks are independently enforced by check_config.',
        'non_routing_parameters_exact':True,'method_source_and_prompts_exact':True,
        'initial_skill':'original 224-word initial Skill','initial_memory':'empty',
        'rounds':8,'optimization_tasks':120,'final_test_enabled':False,
        'semantic_resampling':False,'retry_budgets_unchanged':True,
    })
    (OUT/'run.py').write_bytes(Path(__file__).read_bytes())
    names=['run.py','config.json','contract.json','runtime.json','route_change.json']
    ev.save(OUT/'manifest.json',{'at':ev.now(),'files':{n:hashlib.sha256((OUT/n).read_bytes()).hexdigest() for n in names}})
    freeze_check();print('Prepared official endpoint; frozen method, parameters, initial Skill and eight batches verified.',flush=True)


def run(resume=False):
    cfg=freeze_check();ev.check_live_environment(cfg)
    assert ev.read(OUT/'preflight/result.json')['status']=='passed'
    campaign=OUT/'campaign'
    assert resume or not campaign.exists(), 'New run requires a fresh campaign'
    ev.save(OUT/'process.json',{'pid':os.getpid(),'status':'running','at':ev.now(),'resume':resume})
    print('Starting official V25 full120 campaign',ev.now(),flush=True)
    try:
        result=ev.run_campaign(campaign,config=None if resume else cfg,resume=resume)
        freeze_check()
        status='completed' if result.get('status')=='complete' else 'stopped'
        ev.save(OUT/'result.json',{'status':status,'result':result,'cost':ev.cost_summary(campaign),'at':ev.now(),'final_test_used':False})
        ev.save(OUT/'process.json',{'pid':os.getpid(),'status':status,'at':ev.now()})
        if status=='completed':
            state=ev.read(campaign/'state.json')
            assert state['next_round']==9
            (OUT/'retained_skill.md').write_bytes((campaign/state['parent']).read_bytes())
        print('Campaign',status,ev.now(),flush=True)
    except BaseException as exc:
        ev.save(OUT/'result.json',{'status':'stopped','error_type':type(exc).__name__,'error':str(exc),
                                 'cost':ev.cost_summary(campaign),'at':ev.now(),'final_test_used':False})
        ev.save(OUT/'process.json',{'pid':os.getpid(),'status':'stopped','at':ev.now()})
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run','resume','status'])
    parser.add_argument('--output', type=Path, default=OUT)
    args=parser.parse_args()
    OUT = args.output.resolve()
    if args.action == 'prepare':
        OUT.mkdir(parents=True, exist_ok=True)
    if args.action != 'status':
        load_dotenv(ROOT/'.env',override=True)
    with using_benchmark(SpreadsheetBenchAdapter()):
        if args.action=='prepare':prepare()
        elif args.action=='status':print(json.dumps(ev.status(OUT/'campaign'),ensure_ascii=False))
        else:run(args.action=='resume')
