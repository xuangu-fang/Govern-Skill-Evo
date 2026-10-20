"""Frozen one-shot phases. Run from repository root; never retries a task/call."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import urlparse
from dotenv import load_dotenv
from src.adapters.alfworld.skill_runtime import write_record, implementation_metadata, execution_protocol
from src.skill_evolution.v23 import editor, replay, memory, preconditioner as pc
from src.skill_evolution.v23.grouping import call_configuration, live_generator

ROOT = Path('artifacts/methods/v23/v23_replay_memory_001')
EXP = Path('experiments/methods/v23/v23_replay_memory_001')
BROOT = Path('artifacts/methods/v23/v23_preconditioner_with_memory_001')
BEXP = Path('experiments/methods/v23/v23_preconditioner_with_memory_001')
EDITOR = Path('artifacts/methods/v23/v23_editor_recovery_001/live')
UP = Path('artifacts/methods/v23/v23_prompt_alignment_001')
PYTHON = '/Users/didi/miniforge3/envs/alfworld/bin/python'

def read(p): return json.loads(Path(p).read_text())
def frozen_files():
    paths = [Path(p) for p in read(EXP/'config/plan.json')['parent_sources']]
    for root in [EDITOR, Path('artifacts/methods/v23/v23_editor_001/live'),
                 Path('artifacts/methods/v23/v23_preconditioner_001/live'), UP/'grouping', UP/'diagnosis']:
        paths.extend(p for p in root.rglob('*') if p.is_file())
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def check_frozen():
    assert frozen_files() == read(EXP/'config/upstream_hashes.json'), 'Frozen upstream changed'
    for name, sha in read(EXP/'config/source_hashes.json').items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == sha, f'Source changed: {name}'

def freeze():
    assert not (EXP/'config/plan.json').exists()
    config = call_configuration(base_url='https://api.deepseek.com', model='deepseek-flash', max_tokens=16384, timeout=300)
    plan = {'frozen_at': datetime.now(timezone.utc).isoformat(), 'call_config': config,
        'max_input_chars': 300000, 'max_input_utf8_bytes': 400000,
        'parent_sources': read('experiments/methods/v23/v23_prompt_alignment_001/config/plan.json')['sources'],
        'candidate_tasks': ['train:0012','train:0013','train:0014','train:0015'],
        'candidate_skill': str(EDITOR/'candidate.md'), 'candidate_budget': 4, 'max_steps': 50,
        'replay_calls': 1, 'preconditioner_empty_calls': 1, 'preconditioner_memory_calls': 1,
        'actor_transport': 'Existing bounded HTTP status retries only; no episode retry or semantic resampling.',
        'actor_seed': 42, 'actor_purpose': 'learning', 'actor_model': 'deepseek-flash',
        'preconditioner_grouping': str(UP/'grouping'), 'preconditioner_diagnosis': str(UP/'diagnosis'),
        'comparison_scope': 'Same-batch retrospective interface and update-construction test; no independent generalization or new Candidate execution.',
        'criteria': ['Actual diff matches edits described', 'Observed facts support knowledge', 'Actor-observable conditions',
                     'No per-edit causal attribution from joint edits', 'Technical interruptions distinguished',
                     'Historical sources complete and deduplicated', 'No forced entries or adjustments',
                     'Preserve meaningful conditions and boundaries', 'Keep is valid; stochastic differences not causal proof']}
    parents = [read(p) for p in plan['parent_sources']]
    assert len(parents) == 4 and sum(len(p['steps']) for p in parents) == 93
    assert all(p['protocol'] == execution_protocol(50) for p in parents)
    assert editor.load_editor(EDITOR)['candidate_text'].count('\n') == 23
    oldroot = Path('experiments/methods/v22/23_alfworld57_five_round/revision/src/adapters/alfworld')
    diff = []
    for name, sha in parents[0]['implementation']['files'].items():
        old = oldroot/name
        if name == 'run_task_upstream.py':
            old = Path('experiments/methods/v22/17_p1_input/revision/src/adapters/alfworld')/name
        assert hashlib.sha256(old.read_bytes()).hexdigest() == sha
        current = Path('src/adapters/alfworld')/name
        diff.extend(difflib.unified_diff(old.read_text().splitlines(True), current.read_text().splitlines(True),
                                       fromfile=str(old), tofile=str(current)))
    review = {'parent_files': parents[0]['implementation']['files'], 'candidate_files': implementation_metadata()['files'],
              'reason': 'Reviewed source differences: development-purpose access flag and CLI choice, repository-root resolution and implementation hashing bookkeeping; build_messages extracted unchanged to actor_prompt.render_messages. run_episode, chat parameters, action projection and environment operations unchanged. All recorded messages audited by facts.py; protocol and dependency versions checked per pair.',
              'diff': ''.join(diff)}
    write_record(EXP/'config/plan.json', plan)
    write_record(BEXP/'config/plan.json', plan)
    write_record(EXP/'config/implementation_review.json', review)
    write_record(EXP/'config/upstream_hashes.json', frozen_files())
    files = list(Path('src/skill_evolution/v23').glob('*.py')) + list(Path('src/skill_evolution/v23').glob('*.md'))
    files += list(Path('src/adapters/alfworld').glob('*.py'))
    source_dir = EXP/'config/source'; source_dir.mkdir()
    for p in files:
        dest = source_dir/p; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(p.read_bytes())
    write_record(EXP/'config/source_hashes.json', {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    print('Frozen budgets, source versions, Candidate and historical Parent hashes.')

def candidates():
    check_frozen(); plan = read(EXP/'config/plan.json')
    assert 'passed' in (ROOT/'offline_tests.txt').read_text() and 'failed' not in (ROOT/'offline_tests.txt').read_text()
    dest = ROOT/'candidate_runs'; dest.mkdir(exist_ok=False)
    def run(task):
        output = dest/task.replace(':','_'); output.mkdir()
        cmd = [PYTHON,'-m','src.adapters.alfworld.run_task_skill','--model',plan['actor_model'], '--split','train',
               '--purpose','learning','--task-id',task,'--skill-file',plan['candidate_skill'], '--max-steps','50',
               '--archive-responses','--output-root',str(output)]
        write_record(output/'command.json', cmd)
        start = time.monotonic()
        with (output/'run.log').open('w') as log:
            proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=False)
        result = {'task': task, 'exit_code':proc.returncode,'elapsed_seconds':time.monotonic()-start,
                  'trajectories':[str(p) for p in output.rglob('trajectory.json')]}
        write_record(output/'result.json',result)
        print(json.dumps(result),flush=True)
        return result
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, plan['candidate_tasks']))
    write_record(ROOT/'candidate_results.json',results)
    check_frozen()

def generator(plan):
    load_dotenv('.env',override=False)
    base = os.environ['OPENAI_BASE_URL']; assert urlparse(base).hostname=='api.deepseek.com'
    cfg=plan['call_config']
    return live_generator(base_url=base,key=os.environ['OPENAI_API_KEY'],model=cfg['model'],
                          max_tokens=cfg['max_tokens'],timeout=cfg['timeout_seconds'])

def learning():
    check_frozen(); plan=read(EXP/'config/plan.json')
    assert not (ROOT/'replay').exists(), 'No second Replay call'
    parents=[read(p) for p in plan['parent_sources']]
    results=read(ROOT/'candidate_results.json')
    assert len(results)==4 and all(len(r['trajectories'])==1 for r in results)
    paths=[r['trajectories'][0] for r in results]; candidates=[read(p) for p in paths]
    try:
        bundle=replay.build_replay(EDITOR,parents,candidates,implementation_review=read(EXP/'config/implementation_review.json'))
        bundle['record_paths']={'parent':plan['parent_sources'],'candidate':paths}
        messages=replay.messages_for(bundle)
        assert len(json.dumps(messages,ensure_ascii=False).encode())<=plan['max_input_utf8_bytes']
        write_record(ROOT/'pair_audit.json',bundle['pair_audit'])
        saved=replay.run_replay(bundle,ROOT/'replay',generate=generator(plan),call_config=plan['call_config'],max_input_chars=plan['max_input_chars'])
        commit=memory.commit_memory(ROOT/'memory',context_id='v23_replay_memory_001_R1',context=bundle,result=saved['replay'])
        write_record(ROOT/'memory_commit.json',commit)
        write_record(ROOT/'memory_view.json',memory.load_memory(ROOT/'memory'))
        # Exercise reuse with a generator that cannot issue a request.
        def forbidden(*_): raise AssertionError('Unexpected duplicate request')
        assert replay.run_replay(bundle,ROOT/'replay',generate=forbidden,call_config=plan['call_config'],max_input_chars=plan['max_input_chars'])==saved
        assert memory.commit_memory(ROOT/'memory',context_id='v23_replay_memory_001_R1',context=bundle,result=saved['replay'])==commit
        write_record(ROOT/'reuse.json',{'replay_additional_calls':0,'memory_duplicate_entries':0})
    except (Exception,KeyboardInterrupt) as exc:
        write_record(ROOT/'stop.json',{'stage':'pairing_or_replay','type':type(exc).__name__,'error':str(exc)})
        raise
    finally: check_frozen()

def preconditioner():
    check_frozen(); plan=read(BEXP/'config/plan.json')
    view=memory.load_memory(ROOT/'memory')
    if not view['entries']:
        write_record(BROOT/'stop.json',{'stage':'before_calls','reason':'Replay produced no active Memory. Nonempty real validation unavailable.'})
        return
    common=pc.read_upstream(UP/'grouping',UP/'diagnosis')
    write_record(BROOT/'common_input.json',common)
    write_record(BROOT/'memory_empty.json',memory.empty_memory());write_record(BROOT/'memory_real.json',view)
    baseline=pc.messages_for({**common,'memory':memory.empty_memory()})
    historical=pc.messages_for({**common,'memory':view})
    assert baseline[0]==historical[0]
    a,b=json.loads(baseline[1]['content']),json.loads(historical[1]['content']);a.pop('memory');b.pop('memory');assert a==b
    assert all(len(json.dumps(m,ensure_ascii=False).encode())<=plan['max_input_utf8_bytes'] for m in (baseline,historical))
    results={}
    for name,mem in [('empty',memory.empty_memory()),('real',view)]:
        dest=BROOT/name
        assert not dest.exists(), 'No repeated Preconditioner sampling'
        try:
            saved=pc.run_preconditioner(UP/'grouping',UP/'diagnosis',dest,generate=generator(plan),
                    call_config=plan['call_config'],memory=mem,max_input_chars=plan['max_input_chars'])
            results[name]={'preconditioner':saved['preconditioner'],'effective_plan':saved['effective_plan']}
            def forbidden(*_):raise AssertionError('Unexpected duplicate request')
            assert pc.run_preconditioner(UP/'grouping',UP/'diagnosis',dest,generate=forbidden,
                    call_config=plan['call_config'],memory=mem,max_input_chars=plan['max_input_chars'])==saved
        except (Exception,KeyboardInterrupt) as exc:
            results[name]={'error_type':type(exc).__name__,'error':str(exc)}
            if isinstance(exc,KeyboardInterrupt):raise
        finally: write_record(BROOT/'comparison.json',results)
    check_frozen()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['freeze','candidates','learning','preconditioner'])
    phase=parser.parse_args().phase
    globals()[phase]()
