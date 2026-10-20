"""Isolated calibration profile over the existing fixed-material runner."""
import argparse
import hashlib
from pathlib import Path
from unittest.mock import patch
from experiments.methods.v23_2.v23_2_response_alignment_001 import run as base

EXP=Path(__file__).resolve().parent
OUTPUT=base.history.ROOT/'artifacts/methods/v23_2/v23_2_evidence_calibration_001'
PROMPT=EXP/'config/preconditioner_prompt.md'
original_implementation=base.implementation


def implementation():
    files=[Path(__file__).resolve(),EXP/'reports/OFFLINE_ANALYSIS.md',EXP/'reports/DESIGN.md',
           EXP/'config/replacement.txt',EXP/'config/offline_read_receipt.json',
           *[EXP/f'config/{n}.diff' for n in ('v23','alignment','construction','symmetric')]]
    return {**original_implementation(),**{str(p.relative_to(base.history.ROOT)):p.read_text() for p in files}}


def freeze_hashes():
    return {str(p.relative_to(EXP)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (EXP/'config/plan.json',EXP/'config/implementation.json',EXP/'results/historical_comparison.json')}


def execute(action):
    with patch.multiple(base,EXP=EXP,OUTPUT=OUTPUT,PROMPT=PROMPT,implementation=implementation):
        if action=='prepare':
            base.prepare()
            plan=base.evolution.read(EXP/'config/plan.json');plan['revision']='evidence_calibration'
            base.evolution.save(EXP/'config/plan.json',plan)
            base.evolution.save(EXP/'config/freeze.json',{'at':base.evolution.now(),'sha256':freeze_hashes()})
        else:
            assert freeze_hashes()==base.evolution.read(EXP/'config/freeze.json')['sha256']
            base.run()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','run'))
    execute(p.parse_args().action)
