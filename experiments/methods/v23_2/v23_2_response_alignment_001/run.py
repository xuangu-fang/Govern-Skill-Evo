"""Three fixed Preconditioner calls using the existing V23.2 local runner."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from experiments.methods.v23_2.v23_2_executability_001 import run as history
from src.skill_evolution.v23 import evolution, prompts
from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23_2 import local_validation as local

EXP = Path(__file__).resolve().parent
OUTPUT = history.ROOT/'artifacts/methods/v23_2/v23_2_response_alignment_001'
PROMPT = EXP/'config/preconditioner_prompt.md'
ROUNDS = ('R04', 'R05', 'R06')


def protected_files():
    roots = [history.ROOT/p for p in ('src/skill_evolution/v23', 'src/skill_evolution/v23_2',
             'src/adapters/alfworld', 'experiments/methods/v23', 'artifacts/methods/v23',
             'experiments/methods/v23_2', 'artifacts/methods/v23_2')]
    return {str(p.relative_to(history.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for root in roots for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts
            and not p.is_relative_to(EXP) and not p.is_relative_to(OUTPUT)}


def implementation():
    return {str(p.relative_to(history.ROOT)):p.read_text()
            for p in (Path(__file__), Path(local.__file__), Path(history.__file__), PROMPT)}


def check_baseline():
    history.check_v23_source()
    frozen = evolution.read(history.SOURCE/'contract.json')
    for p in [*local.PROMPTS.values(), prompts.CONTEXT_PATH]:
        require(p.read_text() == frozen[str(p.relative_to(history.ROOT))], 'Default baseline differs from formal V23')


def prepare():
    require(not OUTPUT.exists(), 'Experiment already started')
    check_baseline()
    entries = {}
    for r in ROUNDS:
        _, saved, _, cfg, paths = history.material(r)
        messages = local.messages_for('preconditioner', saved, prompt_path=PROMPT)
        old = evolution.read(Path(paths['preconditioner'])/'messages.json')
        require(messages[1:] == old[1:], 'Fixed user input changed')
        encoded = json.dumps(messages, ensure_ascii=False)
        entries[r] = {'config':cfg, 'paths':paths, 'memory_ids':[e['id'] for e in saved['memory']['entries']],
                      'input_chars':len(encoded), 'input_utf8_bytes':len(encoded.encode())}
    evolution.save(EXP/'config/plan.json', {'version':'V23.2', 'revision':'response_alignment',
                   'rounds':entries, 'prompt_path':str(PROMPT), 'context_override':None,
                   'max_logical_calls':3, 'max_http_requests':9, 'semantic_resampling':False, 'at':evolution.now()})
    evolution.save(EXP/'config/implementation.json', implementation())
    evolution.save(EXP/'config/protected_before.json', protected_files())
    print(json.dumps({r:{k:v[k] for k in ('memory_ids','input_chars','input_utf8_bytes')} for r,v in entries.items()}),flush=True)


def run():
    plan = evolution.read(EXP/'config/plan.json')
    require(tuple(plan['rounds']) == ROUNDS and plan['max_logical_calls'] == 3 and plan['max_http_requests'] == 9,
            'Fixed call budget differs')
    require(plan['prompt_path'] == str(PROMPT) and plan['context_override'] is None, 'Profile changed')
    require(implementation() == evolution.read(EXP/'config/implementation.json'), 'Frozen implementation changed')
    check_baseline()
    before = evolution.read(EXP/'config/protected_before.json')
    require(protected_files() == before, 'Protected files changed before run')
    OUTPUT.mkdir(parents=True, exist_ok=False)
    evolution.save(OUTPUT/'plan.json', plan)
    outcomes, comparisons = {}, {}
    started = time.monotonic()
    try:
        for r in ROUNDS:
            _, saved, old, cfg, paths = history.material(r)
            require(cfg == plan['rounds'][r]['config'] and paths == plan['rounds'][r]['paths'], 'Fixed material/config changed')
            outcomes[r] = {'status':'started'}
            evolution.save(OUTPUT/'status.json', outcomes)
            print('START '+r,flush=True)
            new = None
            try:
                new = local.run_stage('preconditioner', saved, OUTPUT/r, cfg, prompt_path=PROMPT)
                outcomes[r] = {'status':'valid','decision':new['preconditioner']['decision']}
            except evolution.Stopped as exc:
                outcomes[r] = {'status':'stopped','error':str(exc)}
            comparisons[r] = {'original_plan':saved['diagnosis']['plan'], 'memory_ids':plan['rounds'][r]['memory_ids'],
                              'v23':{k:old[k] for k in ('preconditioner','effective_plan')},
                              'v23_2':None if new is None else {k:new[k] for k in ('preconditioner','effective_plan')}}
            evolution.save(OUTPUT/'comparison.json', comparisons)
            evolution.save(OUTPUT/'status.json', outcomes)
            print(f'END {r}: {outcomes[r]}',flush=True)
    finally:
        after = protected_files()
        changed = [p for p in before.keys() | after.keys() if before.get(p) != after.get(p)]
        evolution.save(OUTPUT/'protection.json', {'checked_files':len(before),'unchanged':not changed,'changed':changed,'method':'SHA-256 and identical file set'})
        evolution.save(OUTPUT/'summary.json', {'elapsed_seconds':time.monotonic()-started,'logical_calls_started':len(outcomes),
                       'outcomes':outcomes,'cost':evolution.cost_summary(OUTPUT)})
        require(not changed, 'Protected files changed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','run'))
    prepare() if parser.parse_args().action == 'prepare' else run()
