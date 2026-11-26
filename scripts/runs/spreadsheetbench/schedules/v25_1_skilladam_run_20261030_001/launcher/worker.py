"""Frozen-run orchestration only; no experiment source or parameter changes."""
import argparse
from dataclasses import asdict
import fcntl
import os
from pathlib import Path
import sys
import traceback
sys.path.insert(0, str(Path(__file__).resolve().parents[6]))
from scripts.runs.spreadsheetbench.schedules.v25_1_skilladam_run_20261030_001.launcher.common import record_folder, ROOT, HOME,read,save,sha,now,load,require,verify,barrier
from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.native_cache import cached_native


def method_module(side, name):
    from importlib import import_module
    version = 'v25_1' if side == 'v25_1' else 'skilladam.spreadsheetbench.aligned_actor.actor_runtime'
    return import_module(f'src.skill_evolution.{version}.{name}')


def setup(side):
    settings = verify()
    info = settings['arms'][side]
    folder = record_folder(info)
    from src.skill_evolution.skilladam.spreadsheetbench.layout import UPSTREAM, read_actor_config
    sys.path[:0] = [str(ROOT), str(UPSTREAM)]
    os.environ['PYTHONPATH'] = os.pathsep.join((str(ROOT), str(UPSTREAM)))
    os.chdir(ROOT)
    from dotenv import dotenv_values
    env=dotenv_values(settings['official_env'])
    require(env.get('OPENAI_BASE_URL','').rstrip('/')=='https://api.deepseek.com'
            and bool(env.get('OPENAI_API_KEY')),'Official credential source unavailable or route differs')
    config_path = Path(info['folder']) / info['config']
    cfg = method_module(side, 'cli').read_config(config_path) if side == 'v25_1' else read_actor_config(config_path)
    require(cfg['actor_model']==cfg['call_config']['model']=='deepseek-flash','Model differs')
    require(cfg['actor_base_url'].rstrip('/')=='https://api.deepseek.com'
            and cfg['call_config']['endpoint']=='https://api.deepseek.com/chat/completions','Endpoint differs')
    os.environ['OPENAI_API_KEY']=env['OPENAI_API_KEY'];os.environ['OPENAI_BASE_URL']=cfg['actor_base_url']
    ev = method_module(side, 'evolution')
    SpreadsheetBenchAdapter = method_module(side, 'benchmarks.spreadsheetbench.adapter').SpreadsheetBenchAdapter
    using_benchmark = method_module(side, 'benchmark').using_benchmark
    adapter=SpreadsheetBenchAdapter()
    with using_benchmark(adapter):
        adapter.validate_config(cfg);ev.check_live_environment(cfg)
        if side=='v25_1':ev.validate_config(cfg)
        else:
            from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor import binding
            native,bridge,shared,opt=binding.components()
            require(shared==cfg,'Binding uses another shared config')
            require(opt['optimizer_transport']['model']=='deepseek-flash'
                    and opt['optimizer_transport']['base_url']=='https://api.deepseek.com','Optimizer route differs')
        runtime=ev.runtime_snapshot(cfg)
        require(runtime==settings['runtime'],'Execution runtime differs from frozen baseline')
    return settings,folder,cfg,adapter,runtime


def train(side,folder,cfg):
    ev = method_module(side, 'evolution')
    output=folder/'campaign'
    require(not output.exists(),'Training directory exists; never restart implicitly')
    if side=='v25_1':
        result=ev.run_campaign(output,config=cfg)
        require(result['status']=='complete','Training did not complete')
        final=ev.final_parent(output)
        require(final is not None,'Missing final Skill')
        text=final.read_text()
    else:
        from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.binding import components
        native,bridge,shared,opt=components()
        backend=cached_native(native,bridge,shared,opt,output,os.environ['OPENAI_API_KEY'])
        runner=bridge.AlignedRunner(config=bridge.native_config(opt),adapter=bridge.AlignedAdapter(folder),
            backend=backend,context=bridge.context_for(shared,opt),output_dir=output)
        result=runner.run(cases=bridge.cases_for(shared,opt),initial_skill=(folder/'initial_skill.md').read_text())
        save(output/'completion.json',{'status':'complete','at':now(),
            'iterations':[r.to_dict() for r in result.feedback_loop.iterations]})
        cp=read(output/'checkpoint.json')
        require(cp['next_iteration']==8 and len(cp['iterations'])==8 and cp['pending_post_decision'] is None
                and not cp.get('terminal_stop_reason'),'SkillAdam training/Momentum incomplete')
        text=(output/'final_skill.md').read_text()
        require(text==cp['current_skill'],'Final Skill differs from checkpoint')
    require(bool(text.strip()),'Empty final Skill')
    (folder/'final_skill.md').write_text(text)
    save(folder/'training_complete.json',{'status':'complete','rounds':8,
        'skill_sha256':sha(folder/'final_skill.md'),'at':now()})


def validate_training(side,folder,cfg):
    ev = method_module(side, 'evolution')
    receipt=read(folder/'training_complete.json')
    require(receipt['status']=='complete' and receipt['rounds']==8,'Training completion required')
    require(sha(folder/'final_skill.md')==receipt['skill_sha256'],'Final Skill changed')
    tracked=['final_skill.md','training_complete.json','config.json' if side=='v25_1' else 'shared_config.json']
    if side=='v25_1':
        published = method_module(side, 'cli').EXPERIMENT
        if folder == ROOT / 'artifacts/methods/v25_1' / published.name:
            contract = read(published/'config/frozen_contract.json')
            final = ev.final_parent(folder/'campaign', published_contract=contract)
        else:
            final = ev.final_parent(folder/'campaign')
        require(final.read_bytes()==(folder/'final_skill.md').read_bytes(),'Published Skill differs')
        require(method_module(side, 'cli').read_config(folder/'campaign/config.json')==cfg,'Campaign config differs')
        tracked+=['campaign/state.json','campaign/contract.json','campaign/config.json']
    else:
        cp=read(folder/'campaign/checkpoint.json')
        require(cp['next_iteration']==8 and len(cp['iterations'])==8
                and cp['pending_post_decision'] is None and not cp.get('terminal_stop_reason'),'Incomplete native checkpoint')
        require(cp['current_skill']==(folder/'final_skill.md').read_text()==(folder/'campaign/final_skill.md').read_text(),
                'Native Skill differs')
        from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.binding import components
        native,bridge,shared,opt=components()
        signature=cp['run_signature']
        require(signature['post_decision']['run_config']==bridge.native_config(opt).to_dict(),'Native run config differs')
        require(signature['post_decision']['backend_context']==asdict(bridge.context_for(shared,opt)),'Native context differs')
        from skilladam.methods.skilladam import _profile_gate,_gate_signature
        gate=_profile_gate(bridge.AlignedAdapter(folder),'spreadsheetbench',None,opt['native']['gate_profile'])
        require(signature['gate']==_gate_signature(gate,'spreadsheetbench',None,opt['native']['gate_profile']),'Native Gate differs')
        require(read(folder/'campaign/completion.json')['status']=='complete','Missing native completion')
        tracked+=['skilladam.json','campaign/checkpoint.json','campaign/completion.json','campaign/final_skill.md']
    save(HOME/side/'validation.json',{'status':'validated','rounds':8,'at':now(),
        'files':{name:sha(folder/name) for name in tracked}})


def test(side,settings,folder):
    evaluation = method_module(side, 'evaluation')
    actor = method_module(side, 'benchmarks.spreadsheetbench.actor')
    barrier(settings)
    inputs = Path(settings['arms'][side]['folder']) / 'config'
    cfg=read(inputs/'evaluation/config.json');require(len(cfg['test_tasks'])==280,'Full Test required')
    require(not (folder/'test').exists(),'Test output exists; explicit audited resume required')
    scorer=load('frozen_test_scoring',inputs/'evaluation/scoring.py')
    bundle={'campaign':str(folder/'campaign'),'skill_text':(folder/'final_skill.md').read_text(),
        'actor_config':cfg,'tasks':[cfg['task_items'][t] for t in cfg['test_tasks']],
        'initial_reference':None,'evaluation_policy':'Frozen final Skill, 280 tasks, no optimization or Skill update'}
    def invoke(task,skill,directory,config):
        return actor.run(config['task_items'][task],Path(skill).read_text(),directory,config,score=scorer.score)
    result=evaluation.run(folder/'test',bundle=bundle,runner=invoke)
    require(result['status']=='complete' and result['completed']==280 and len(result['tasks'])==280,'Incomplete Test')
    require([x['task_id'] for x in result['tasks']]==cfg['test_tasks'],'Test task coverage/order differs')
    require(result['success']==sum(x['hard'] for x in result['tasks']),'Test summary differs')
    barrier(settings)
    save(folder/'test_complete.json',{'status':'complete','completed':280,'success':result['success'],
        'hard':result['hard'],'per_cell_pass_rate':result['per_cell_pass_rate'],
        'summary_sha256':sha(folder/'test/summary.json'),'at':now()})


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['check','train','validate','test'])
    p.add_argument('--side',required=True,choices=['v25_1','skilladam']);p.add_argument('--token')
    a=p.parse_args();directory=HOME/a.side;directory.mkdir(exist_ok=True)
    with (directory/'.worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if a.action in ('train','test'):
            launch=read(directory/(a.action+'_launch.json'))
            require(a.token==launch['token'],'Missing matching launch authorization')
            require(not (directory/(a.action+'_process.json')).exists(),'Worker already consumed launch')
            save(directory/(a.action+'_process.json'),{'status':'running','pid':os.getpid(),'at':now()})
        try:
            settings,folder,cfg,adapter,runtime=setup(a.side)
            using_benchmark = method_module(a.side, 'benchmark').using_benchmark
            with using_benchmark(adapter):
                if a.action=='check':save(directory/'preflight.json',{'status':'passed','runtime':runtime,
                    'credential_source':settings['official_env'],'official_route':True,'real_model_requests':0,'at':now()})
                elif a.action=='train':train(a.side,folder,cfg);validate_training(a.side,folder,cfg)
                elif a.action=='validate':validate_training(a.side,folder,cfg)
                else:test(a.side,settings,folder)
            if a.action in ('train','test'):
                save(directory/(a.action+'_process.json'),{'status':'complete','pid':os.getpid(),'at':now()})
        except BaseException as exc:
            save(directory/(a.action+'_process.json'),{'status':'stopped','pid':os.getpid(),
                'error_type':type(exc).__name__,'at':now()})
            traceback.print_exc();raise SystemExit(1)


if __name__=='__main__':main()
