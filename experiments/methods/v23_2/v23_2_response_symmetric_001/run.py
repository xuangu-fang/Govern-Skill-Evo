"""Isolated symmetric-evidence profile; reuse the existing three-call runner."""
import argparse
from pathlib import Path
from unittest.mock import patch
from experiments.methods.v23_2.v23_2_response_alignment_001 import run as base

EXP=Path(__file__).resolve().parent
OUTPUT=base.history.ROOT/'artifacts/methods/v23_2/v23_2_response_symmetric_001'
PROMPT=EXP/'config/preconditioner_prompt.md'
original_implementation=base.implementation


def implementation():
    frozen=[Path(__file__).resolve(),EXP/'reports/PRECALL_REVIEW.md',EXP/'config/replacement.txt',
            *[EXP/f'config/{name}.diff' for name in ('v23','alignment','construction')],
            EXP/'config/precall_evidence_checks.json']
    return {**original_implementation(),**{str(p.relative_to(base.history.ROOT)):p.read_text() for p in frozen}}


def execute(action):
    with patch.multiple(base,EXP=EXP,OUTPUT=OUTPUT,PROMPT=PROMPT,implementation=implementation):
        if action=='prepare':
            base.prepare()
            plan=base.evolution.read(EXP/'config/plan.json');plan['revision']='response_symmetric'
            base.evolution.save(EXP/'config/plan.json',plan)
        else:
            base.run()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','run'))
    execute(p.parse_args().action)
