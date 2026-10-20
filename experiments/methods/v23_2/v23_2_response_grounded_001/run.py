"""Isolated response-grounded profile; reuse the existing fixed-material runner."""
import argparse
import hashlib
from pathlib import Path
from unittest.mock import patch
from experiments.methods.v23_2.v23_2_response_alignment_001 import run as base

EXP = Path(__file__).resolve().parent
OUTPUT = base.history.ROOT/'artifacts/methods/v23_2/v23_2_response_grounded_001'
PROMPT = EXP/'config/preconditioner_prompt.md'
original_implementation = base.implementation
original_protected_files = base.protected_files


def protected_files():
    docs = [p for name in ('v23', 'v23_2')
            for p in (base.history.ROOT/f'docs/methods/{name}').rglob('*') if p.is_file()]
    return {**original_protected_files(), **{str(p.relative_to(base.history.ROOT)):
            hashlib.sha256(p.read_bytes()).hexdigest() for p in docs}}


def implementation():
    files = [Path(__file__).resolve(), EXP/'reports/DESIGN.md', EXP/'reports/OFFLINE_ANALYSIS.md',
             EXP/'config/replacement.txt', EXP/'config/original_passage.txt',
             EXP/'config/offline_read_receipt.json', EXP/'results/offline_tests.json',
             *[EXP/f'config/{n}.diff' for n in ('v23', 'alignment', 'construction', 'symmetric', 'calibration')]]
    return {**original_implementation(), **{str(p.relative_to(base.history.ROOT)):p.read_text() for p in files}}


def freeze_hashes():
    return {str(p.relative_to(EXP)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (EXP/'config/plan.json', EXP/'config/implementation.json',
                      EXP/'results/historical_comparison.json')}


def execute(action):
    with patch.multiple(base, EXP=EXP, OUTPUT=OUTPUT, PROMPT=PROMPT,
                        implementation=implementation, protected_files=protected_files):
        if action == 'prepare':
            base.prepare()
            plan = base.evolution.read(EXP/'config/plan.json')
            plan['revision'] = 'response_grounded'
            base.evolution.save(EXP/'config/plan.json', plan)
            base.evolution.save(EXP/'config/freeze.json', {'at':base.evolution.now(), 'sha256':freeze_hashes()})
        else:
            assert freeze_hashes() == base.evolution.read(EXP/'config/freeze.json')['sha256']
            base.run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run'))
    execute(parser.parse_args().action)
