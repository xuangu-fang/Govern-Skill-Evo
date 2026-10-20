"""Concentration-gated, context-only comparison using the existing local runner."""
import argparse
import json
from pathlib import Path
import time

from experiments.methods.v23_2.v23_2_executability_001 import run as first
from experiments.methods.v23_2.v23_2_executability_002 import run as second
from src.skill_evolution.v23 import evolution
from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23_2 import local_validation as local


EXP = Path(__file__).resolve().parent
OUTPUT = first.ROOT/'artifacts/methods/v23_2/v23_2_capability_001'
CONTEXT = EXP/'config/execution_context.md'
PROMPTS = {name: first.ROOT/f'src/skill_evolution/v23/{name}_prompt.md'
           for name in ('diagnosis', 'preconditioner')}
ROUNDS = ('R03', 'R06')


def protected_bytes():
    result = second.protected_bytes()
    for root in (second.EXP, second.OUTPUT):
        result.update({str(p): p.read_bytes() for p in root.rglob('*')
                       if p.is_file() and '__pycache__' not in p.parts})
    return result


def implementation():
    paths = [Path(__file__), Path(local.__file__), CONTEXT,
             EXP/'reports/CONCENTRATION.md', EXP/'results/concentration.json']
    return {str(p.relative_to(first.ROOT)): p.read_text() for p in paths}


def check_base():
    first.check_v23_source()
    frozen = evolution.read(first.SOURCE/'contract.json')
    for path in PROMPTS.values():
        require(path.read_text() == frozen[str(path.relative_to(first.ROOT))], 'Not the formal V23 template')
    return frozen


def prepare():
    require(not OUTPUT.exists(), 'Experiment already started')
    audit = evolution.read(EXP/'results/concentration.json')
    require(audit['concentrated'] and audit['new_model_calls_at_audit'] == 0, 'Concentration gate not passed')
    check_base()
    base_plan = evolution.read(first.EXP/'config/plan.json')
    entries = {}
    for r in ROUNDS:
        _, saved, _, _, sources = first.material(r)
        message = local.messages_for('preconditioner', saved,
                                     prompt_path=PROMPTS['preconditioner'], context_path=CONTEXT)
        old = evolution.read(Path(sources['preconditioner'])/'messages.json')
        require(message[1] == old[1], 'Fixed user message changed')
        encoded = json.dumps(message, ensure_ascii=False)
        entries[r] = {**base_plan['rounds'][r], 'paths': sources,
                      'input_chars': len(encoded), 'input_utf8_bytes': len(encoded.encode('utf-8'))}
    evolution.save(EXP/'config/plan.json', {'version': 'V23.2', 'revision': 'capability_only', 'rounds': entries,
                   'prompt_paths': {k: str(v) for k, v in PROMPTS.items()}, 'context_path': str(CONTEXT),
                   'baseline_contract': str(first.SOURCE/'contract.json'), 'max_logical_calls': 2,
                   'max_http_requests': 6, 'semantic_resampling': False, 'concentration': audit, 'at': evolution.now()})
    evolution.save(EXP/'config/implementation.json', implementation())
    print(json.dumps({r: {k: v[k] for k in ('input_chars', 'input_utf8_bytes')}
                      for r, v in entries.items()}), flush=True)


def run():
    plan = evolution.read(EXP/'config/plan.json')
    require(tuple(plan['rounds']) == ROUNDS and plan['max_logical_calls'] == 2 and plan['max_http_requests'] == 6,
            'Call budget differs')
    require(plan['prompt_paths'] == {k: str(v) for k, v in PROMPTS.items()} and plan['context_path'] == str(CONTEXT),
            'Prompt profile differs')
    require(plan['concentration']['concentrated'] and implementation() == evolution.read(EXP/'config/implementation.json'),
            'Frozen audit/implementation differs')
    check_base()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    evolution.save(OUTPUT/'plan.json', plan)
    before = protected_bytes()
    started = time.monotonic()
    outcomes, comparisons = {}, {}
    try:
        for r in ROUNDS:
            _, saved, old, _, sources = first.material(r)
            require(sources == plan['rounds'][r]['paths'], 'Historical source changed')
            p1, p2 = first.selected(first.OUTPUT, 'fixed_'+r), first.selected(second.OUTPUT, r)
            prior1, prior2 = local.load_attempt(p1), local.load_attempt(p2, prompt_path=second.PROMPT)
            require(evolution.read(p1/'input.json') == saved == evolution.read(p2/'input.json'), 'Prior input differs')
            outcomes[r] = {'status': 'started'}
            evolution.save(OUTPUT/'status.json', outcomes)
            print('START '+r, flush=True)
            new = None
            try:
                new = local.run_stage('preconditioner', saved, OUTPUT/r, plan['rounds'][r]['config'],
                                      prompt_path=PROMPTS['preconditioner'], context_path=CONTEXT)
                outcomes[r] = {'status': 'valid', 'decision': new['preconditioner']['decision']}
            except evolution.Stopped as exc:
                outcomes[r] = {'status': 'stopped', 'error': str(exc)}
            comparisons[r] = {'original_plan': saved['diagnosis']['plan']}
            for key, value in [('v23', old), ('v23_2_first', prior1), ('v23_2_second', prior2), ('capability_only', new)]:
                comparisons[r][key] = None if value is None else {k: value[k] for k in ('preconditioner', 'effective_plan')}
            evolution.save(OUTPUT/'comparison.json', comparisons)
            evolution.save(OUTPUT/'status.json', outcomes)
            print(f'END {r}: {outcomes[r]}', flush=True)
    finally:
        after = protected_bytes()
        changed = [p for p in before.keys() | after.keys() if before.get(p) != after.get(p)]
        evolution.save(OUTPUT/'protection.json', {'checked_files': len(before), 'unchanged': not changed, 'changed': changed})
        evolution.save(OUTPUT/'summary.json', {'elapsed_seconds': time.monotonic()-started,
                       'logical_calls_started': len(outcomes), 'outcomes': outcomes, 'cost': evolution.cost_summary(OUTPUT)})
        require(not changed, 'Protected historical files changed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run'))
    args = parser.parse_args()
    prepare() if args.action == 'prepare' else run()
