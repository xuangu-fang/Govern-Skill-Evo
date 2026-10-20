"""Two fixed-Plan calls using the existing V23.2 local runner; no environment execution."""
import argparse
import json
from pathlib import Path
import time

from experiments.methods.v23_2.v23_2_executability_001 import run as previous
from src.skill_evolution.v23 import evolution
from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23_2 import local_validation as local


EXP = Path(__file__).resolve().parent
OUTPUT = previous.ROOT/'artifacts/methods/v23_2/v23_2_executability_002'
PROMPT = EXP/'config/preconditioner_prompt.md'
ROUNDS = ('R03', 'R06')


def implementation():
    paths = [Path(__file__), Path(local.__file__), PROMPT]
    return {str(p.relative_to(previous.ROOT)): p.read_text() for p in paths}


def protected_bytes():
    snapshot = previous.protected_bytes()
    for root in (previous.EXP, previous.OUTPUT):
        snapshot.update({str(p): p.read_bytes() for p in root.rglob('*')
                         if p.is_file() and '__pycache__' not in p.parts})
    snapshot.update({str(p): p.read_bytes() for p in local.PROMPTS.values()})
    return snapshot


def prepare():
    require(not OUTPUT.exists(), 'Experiment already started')
    previous.check_v23_source()
    old_plan = evolution.read(previous.EXP/'config/plan.json')
    rounds = {}
    for r in ROUNDS:
        _, saved, _, _, paths = previous.material(r)
        prior_path = previous.selected(previous.OUTPUT, 'fixed_'+r)
        prior = local.load_attempt(prior_path)
        require(evolution.read(prior_path/'input.json') == saved, 'Prior fixed input differs')
        messages = local.messages_for('preconditioner', saved, prompt_path=PROMPT)
        require(messages[1] == evolution.read(prior_path/'messages.json')[1], 'Fixed model input changed')
        require(prior['diagnosis'] == saved['diagnosis'], 'Original Plan changed')
        encoded = json.dumps(messages, ensure_ascii=False)
        rounds[r] = {**old_plan['rounds'][r], 'paths': paths, 'prior_v23_2': str(prior_path),
                     'input_chars': len(encoded), 'input_utf8_bytes': len(encoded.encode('utf-8'))}
    evolution.save(EXP/'config/plan.json', {'version': 'V23.2', 'revision': 'final_update_executability',
                   'rounds': rounds, 'max_logical_calls': 2, 'max_http_requests': 6,
                   'prompt_path': str(PROMPT), 'semantic_resampling': False, 'at': evolution.now()})
    evolution.save(EXP/'config/implementation.json', implementation())
    print(json.dumps({r: {k: v[k] for k in ('input_chars', 'input_utf8_bytes', 'memory_ids')}
                      for r, v in rounds.items()}), flush=True)


def run():
    plan = evolution.read(EXP/'config/plan.json')
    require(tuple(plan['rounds']) == ROUNDS and plan['max_logical_calls'] == 2
            and plan['max_http_requests'] == 6 and plan['prompt_path'] == str(PROMPT), 'Experiment plan differs')
    require(implementation() == evolution.read(EXP/'config/implementation.json'), 'Frozen implementation changed')
    previous.check_v23_source()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    evolution.save(OUTPUT/'plan.json', plan)
    before = protected_bytes()
    started = time.monotonic()
    outcomes, comparisons = {}, {}
    try:
        for r in ROUNDS:
            _, saved, old, _, paths = previous.material(r)
            entry = plan['rounds'][r]
            require(paths == entry['paths'], 'Historical sources changed')
            prior_path = Path(entry['prior_v23_2'])
            require(evolution.read(prior_path/'input.json') == saved, 'Prior fixed input changed')
            prior = local.load_attempt(prior_path)
            print('START '+r, flush=True)
            outcomes[r] = {'status': 'started'}
            evolution.save(OUTPUT/'status.json', outcomes)
            new = None
            try:
                new = local.run_stage('preconditioner', saved, OUTPUT/r, entry['config'], prompt_path=PROMPT)
                outcomes[r] = {'status': 'valid', 'decision': new['preconditioner']['decision']}
            except evolution.Stopped as exc:
                outcomes[r] = {'status': 'stopped', 'error': str(exc)}
            comparisons[r] = {'original_plan': saved['diagnosis']['plan'],
                              'v23': {k: old[k] for k in ('preconditioner', 'effective_plan')},
                              'v23_2_previous': {k: prior[k] for k in ('preconditioner', 'effective_plan')},
                              'v23_2_final': None if new is None else {
                                  k: new[k] for k in ('preconditioner', 'effective_plan')}}
            evolution.save(OUTPUT/'comparison.json', comparisons)
            evolution.save(OUTPUT/'status.json', outcomes)
            print(f'END {r}: {outcomes[r]}', flush=True)
    finally:
        after = protected_bytes()
        changed = [p for p in before.keys() | after.keys() if before.get(p) != after.get(p)]
        evolution.save(OUTPUT/'protection.json', {'checked_files': len(before), 'unchanged': not changed, 'changed': changed})
        evolution.save(OUTPUT/'summary.json', {'elapsed_seconds': time.monotonic()-started,
                       'logical_calls_started': len(outcomes), 'outcomes': outcomes,
                       'cost': evolution.cost_summary(OUTPUT)})
        require(not changed, 'Historical files changed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run'))
    args = parser.parse_args()
    prepare() if args.action == 'prepare' else run()
