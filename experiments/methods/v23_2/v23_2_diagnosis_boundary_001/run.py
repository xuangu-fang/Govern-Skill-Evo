"""Freeze original Diagnosis requests; run only three isolated P1 requests."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from unittest.mock import patch

from experiments.methods.v23_2.v23_2_response_alignment_001 import run as base
from src.skill_evolution.v23 import diagnosis, grouping, evolution as ev
from src.skill_evolution.v23_2 import local_validation as local

ROOT = base.history.ROOT
SOURCE = base.history.SOURCE
EXP = Path(__file__).resolve().parent
OUTPUT = ROOT/'artifacts/methods/v23_2/v23_2_diagnosis_boundary_001'
PROMPT = EXP/'config/diagnosis_prompt.md'
ROUNDS = ('R04', 'R05', 'R06')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protected_files():
    with patch.multiple(base, EXP=EXP, OUTPUT=OUTPUT):
        values = base.protected_files()
    roots = ('docs/methods/v23', 'docs/methods/v23_2', 'tests/skill_evolution/v23',
             'tests/skill_evolution/v23_2', 'tests/adapters/alfworld')
    files = [p for name in roots for p in (ROOT/name).rglob('*')
             if p.is_file() and '__pycache__' not in p.parts]
    files += [ROOT/p for p in ('benchmarks/README.md', 'docs/04_EXPERIMENT_LOG.md',
              'docs/README.md', 'experiments/methods/README.md', 'src/skill_evolution/README.md')]
    return {**values, **{str(p.relative_to(ROOT)):digest(p) for p in files}}


def material(rnd):
    """Read the original upstream archive, never reconstruct it from a later Plan."""
    rd = SOURCE/'rounds'/rnd
    gp, dp = (base.history.selected(rd, n) for n in ('grouping', 'diagnosis'))
    grouped = grouping.load_grouping(gp)
    old = diagnosis.load_diagnosis(dp, expected_grouping=grouped)
    saved = ev.read(dp/'input.json')
    assert saved == grouped and set(saved) == {'facts','background','grouping','sources','round_id'}
    assert saved['facts']['parent'] == ev.read(rd/'round_input.json')['parent']
    messages, request, meta = (ev.read(dp/n) for n in ('messages.json','request.json','run.json'))
    assert messages == diagnosis.messages_for(saved) == request['body']['messages']
    assert set(json.loads(messages[1]['content'])) == {'parent','command_sets','runs','grouping'}
    cfg = ev.read(SOURCE/'config.json')
    recoveries = []
    for p in sorted((SOURCE/'recoveries').glob('*.json')):
        value = ev.read(p)
        if value['at'] <= meta['started_at']:
            if value.get('input_limits'):
                cfg.pop('max_input_bytes', None)
            cfg.update(value.get('input_limits') or {})
            recoveries.append(p)
    call = {**{k:v for k,v in request['body'].items() if k!='messages'},
            'endpoint':request['endpoint'], 'timeout_seconds':request['timeout_seconds']}
    assert call == meta['call_config'] and cfg['max_input_chars'] == meta['max_input_chars']
    config = {'call_config':call, 'max_input_chars':cfg['max_input_chars'],
              'max_message_utf8_bytes':ev.message_byte_limit(cfg), 'max_attempts':3,
              'retry_delay_seconds':0}
    files = [dp/n for n in ('input.json','messages.json','request.json','run.json','diagnosis.json','response.json','prompt.md')]
    files += [gp/'grouping.json', rd/'round_input.json', SOURCE/'config.json', *recoveries]
    entry = {'diagnosis_path':str(dp), 'grouping_path':str(gp), 'config':config,
             'original_output':old['diagnosis'], 'http_request_limit':1,
             'source_hashes':{str(p.relative_to(ROOT)):digest(p) for p in files}}
    return saved, entry


def verify_p0():
    base.check_baseline()
    cases = ev.read(EXP/'config/cases.json')
    for rnd in ROUNDS:
        assert material(rnd)[1] == cases[rnd]
    for name, value in ev.read(EXP/'config/p0_freeze.json')['sha256'].items():
        assert digest(EXP/name) == value
    assert protected_files() == ev.read(EXP/'config/protected_before.json')


def p0():
    assert not (EXP/'config/cases.json').exists() and not OUTPUT.exists()
    base.check_baseline()
    ev.save(EXP/'config/protected_before.json', protected_files())
    (EXP/'results/git_status_before.txt').write_text(subprocess.check_output(['git','status','--short'],text=True))
    ev.save(EXP/'config/cases.json', {rnd:material(rnd)[1] for rnd in ROUNDS})
    names = ('config/cases.json','config/history_receipt.json','reports/P0_BASELINE.md')
    ev.save(EXP/'config/p0_freeze.json', {'at':ev.now(), 'new_model_calls':0,
            'sha256':{n:digest(EXP/n) for n in names}})
    verify_p0()
    print('P0 verified: exact upstream requests, no Memory, historical capacities, 0 calls.')


def frozen_files():
    files = [Path(__file__), EXP/'tests/test_profile.py', PROMPT, EXP/'config/replacements.json',
             EXP/'config/v23.diff', EXP/'reports/P1_DESIGN.md', EXP/'results/offline_tests.json',
             EXP/'config/p0_freeze.json', EXP/'config/cases.json', Path(local.__file__)]
    return {str(p.relative_to(ROOT)):digest(p) for p in files}


def prepare():
    verify_p0()
    assert not OUTPUT.exists() and not (EXP/'config/p1_freeze.json').exists()
    for rnd in ROUNDS:
        saved, entry = material(rnd)
        old = ev.read(Path(entry['diagnosis_path'])/'messages.json')
        new = local.messages_for('diagnosis', saved, prompt_path=PROMPT)
        assert old[1:] == new[1:]
    ev.save(EXP/'config/p1_freeze.json', {'at':ev.now(), 'max_logical_calls':3,
            'max_http_requests':3, 'automatic_retries':0, 'sha256':frozen_files()})


def run_one(saved, directory, config, *, generate=None):
    # Experiment-only strict request budget; do not change shared retry policy.
    with patch.object(local.evolution, '_retryable', return_value=False):
        return local.run_stage('diagnosis', saved, directory, config,
                               prompt_path=PROMPT, generate=generate)


def run():
    verify_p0()
    assert frozen_files() == ev.read(EXP/'config/p1_freeze.json')['sha256']
    OUTPUT.mkdir(parents=True, exist_ok=False)
    outcomes = {}; started = time.monotonic()
    try:
        for rnd in ROUNDS:
            saved, entry = material(rnd)
            print('START '+rnd, flush=True)
            outcomes[rnd] = {'status':'started'}
            ev.save(OUTPUT/'status.json', outcomes)
            try:
                value = run_one(saved, OUTPUT/rnd, entry['config'])
                outcomes[rnd] = {'status':'valid', 'decision':value['diagnosis']['decision']}
            except ev.Stopped as exc:
                outcomes[rnd] = {'status':'stopped', 'error':str(exc)}
            ev.save(OUTPUT/'status.json', outcomes)
            print('END '+rnd+': '+str(outcomes[rnd]), flush=True)
    finally:
        ev.save(OUTPUT/'summary.json', {'logical_calls_started':len(outcomes), 'outcomes':outcomes,
                'elapsed_seconds':time.monotonic()-started, 'cost':ev.cost_summary(OUTPUT)})
        before = ev.read(EXP/'config/protected_before.json'); after = protected_files()
        changed = [p for p in before.keys()|after.keys() if before.get(p)!=after.get(p)]
        ev.save(EXP/'results/protection.json', {'checked_files':len(before), 'unchanged':not changed,'changed':changed})
        assert not changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('p0','check','prepare','run'))
    {'p0':p0,'check':verify_p0,'prepare':prepare,'run':run}[parser.parse_args().action]()
