"""One frozen R06 Editor handoff, then at most seven existing Actor episodes."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from unittest.mock import patch

from experiments.methods.v23_2.v23_2_executability_001 import run as history
from experiments.methods.v23.v23_alfworld_formal_001 import evaluate
from src.skill_evolution.v23 import evolution as ev, editor
from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23_2 import local_validation as local

EXP = Path(__file__).resolve().parent
ROOT = history.ROOT
OUTPUT = ROOT/'artifacts/methods/v23_2/v23_2_response_behavior_001'
RD = history.SOURCE/'rounds/R06'
UPSTREAM = ROOT/'artifacts/methods/v23_2/v23_2_response_alignment_001/R06/attempts/001'
PROMPT = ROOT/'experiments/methods/v23_2/v23_2_response_alignment_001/config/preconditioner_prompt.md'


def protected_files():
    roots = ('src/skill_evolution/v23','src/skill_evolution/v23_2','src/adapters/alfworld',
             'experiments/methods/v23','artifacts/methods/v23','experiments/methods/v23_2','artifacts/methods/v23_2')
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for root in roots for p in (ROOT/root).rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and not p.is_relative_to(EXP) and not p.is_relative_to(OUTPUT)}


def inputs():
    history.check_v23_source()
    saved = local.load_attempt(UPSTREAM, prompt_path=PROMPT)
    frozen = ev.read(RD/'round_input.json')
    old = editor.load_editor(history.selected(RD,'editor'))
    require(saved['facts']['parent'] == frozen['parent'] == old['facts']['parent'], 'Wrong Parent')
    require(saved['background'] == old['background'], 'Editor background changed')
    require(editor.messages_for(saved)[0] == ev.read(history.selected(RD,'editor')/'messages.json')[0], 'Editor system changed')
    require(len(frozen['tasks']) == 7 and frozen['tasks'] == [f'val:{i:04}' for i in range(11,18)], 'Wrong seven tasks/order')
    cfg = ev._config(history.SOURCE)
    require(cfg['call_config'] == ev.read(history.selected(RD,'editor')/'run.json')['call_config'], 'Editor model changed')
    require(cfg['max_steps']==50 and cfg['actor_max_workers']==8 and cfg['actor_request_attempts']==3, 'Actor limits changed')
    expected = ev.read(history.SOURCE/'contract.json')
    for p in sorted((history.SOURCE/'recoveries').glob('*.json')):
        expected.update(ev.read(p).get('contract_changes',{}))
    # Only the already authorized, one-line transport retry fix may differ from training.
    recovery = evaluate.recovery(history.SOURCE.parent/'evaluation')
    require(recovery is not None, 'Missing existing transport authorization')
    for name, before in recovery['contract_before'].items():
        require(expected[name] == before, 'Transport recovery baseline differs')
    expected.update(recovery['contract_changes'])
    require(expected == ev.frozen_contract(), 'Unreviewed source drift')
    return saved, frozen, cfg


def load_handoff(path):
    """Only archive-format adaptation; original Editor still builds and validates its input."""
    require(Path(path).resolve() == UPSTREAM, 'Unexpected upstream archive')
    return local.load_attempt(UPSTREAM, prompt_path=PROMPT)


def invoke_editor(path, generate, cfg, max_input_chars):
    # The original loader expects a V23 archive. Replace only that read with the
    # existing V23.2 validating reader, never prompts, compilation, or patch logic.
    with patch.object(editor, 'load_preconditioner', load_handoff):
        return editor.run_editor(UPSTREAM, path, generate=generate, call_config=cfg,
                                 max_input_chars=max_input_chars)


def verify_protection():
    before = ev.read(EXP/'config/protected_before.json'); after = protected_files()
    changed = [p for p in before.keys()|after.keys() if before.get(p)!=after.get(p)]
    ev.save(EXP/'results/protection.json',{'checked_files':len(before),'unchanged':not changed,'changed':changed})
    require(not changed,'Historical files changed')


def prepare():
    require(not OUTPUT.exists() and not (EXP/'config/plan.json').exists(), 'Already prepared/started')
    saved, frozen, cfg = inputs()
    records = {}
    for side in ('parent_runs','candidate_runs'):
        records[side] = [ev.read(RD/side/t.replace(':','_')/'result.json')['trajectory'] for t in frozen['tasks']]
        for task,path in zip(frozen['tasks'],records[side]):
            value=ev.read(path)
            require(value['task']==cfg['task_items'][task] and value['status'] in ev.COMPLETE,'Invalid historical episode')
    ev.save(EXP/'config/plan.json',{'upstream':str(UPSTREAM),'prompt':str(PROMPT),'tasks':frozen['tasks'],
            'historical_records':records,'editor_call_config':cfg['call_config'],'max_editor_logical_calls':1,
            'max_editor_http_requests':3,'max_candidate_episodes':7,'max_steps':50,'max_workers':8,
            'config_sha256':hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest(),
            'actor_transport_fix':'existing evaluation/recoveries/001.json; no new source change','at':ev.now()})
    ev.save(EXP/'config/implementation.json',{'run.py':Path(__file__).read_text(),'contract':ev.frozen_contract()})
    ev.save(EXP/'config/protected_before.json',protected_files())
    ev.save(EXP/'config/effective_plan.json',saved['effective_plan'])
    print('Prepared: same R06 Parent, frozen Effective Plan, seven ordered tasks',flush=True)


def execute(phase):
    saved,frozen,cfg=inputs(); plan=ev.read(EXP/'config/plan.json')
    require(hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest()==plan['config_sha256'],'Config changed')
    require(ev.read(EXP/'config/implementation.json')=={'run.py':Path(__file__).read_text(),'contract':ev.frozen_contract()},'Implementation changed')
    require(saved['effective_plan']==ev.read(EXP/'config/effective_plan.json'),'Plan changed')
    verify_protection()
    if phase=='editor':
        OUTPUT.mkdir(parents=True,exist_ok=False)
        ev.save(OUTPUT/'contract.json',ev.frozen_contract())
    else:
        require(not (OUTPUT/'candidate_runs').exists(),'Candidate episodes already started; no implicit restart')
    started=time.monotonic(); status={'phase':phase,'started_at':ev.now()}
    try:
        if phase=='editor':
            ep,value=ev._model_stage(OUTPUT,OUTPUT,'editor',
                lambda p,g,c:invoke_editor(p,g,c,cfg['max_input_chars']),cfg,None,False)
            status.update(outcome=value['editor_status'],path=str(ep))
        else:
            ep=history.selected(OUTPUT,'editor')
            value=editor.load_editor(ep,expected_preconditioner=saved,expected_call_config=cfg['call_config'])
            require(value['editor_status']=='candidate','Editor did not produce Candidate')
            paths,records=ev._actors(OUTPUT,OUTPUT,'candidate_runs',frozen['tasks'],ep/'candidate.md',cfg,ev.actor_task,False)
            ev.save(OUTPUT/'candidate_results.json',{'paths':paths,'tasks':frozen['tasks']})
            status.update(outcome='complete',episodes=len(records),successes=sum(r['won'] for r in records))
    except Exception as exc:
        status.update(outcome='stopped',error_type=type(exc).__name__,error=str(exc))
        raise
    finally:
        status.update(finished_at=ev.now(),elapsed_seconds=time.monotonic()-started)
        ev.save(OUTPUT/(phase+'_status.json'),status)
        ev.save(OUTPUT/'cost.json',ev.cost_summary(OUTPUT))
        verify_protection()
        print(json.dumps(status,ensure_ascii=False),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','editor','episodes'))
    action=p.parse_args().action
    prepare() if action=='prepare' else execute(action)
