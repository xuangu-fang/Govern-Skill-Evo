"""Explicit isolated profile reusing the completed three-round validation runner."""
import argparse
from pathlib import Path
from unittest.mock import patch
from experiments.methods.v23_2.v23_2_response_alignment_001 import run as base

EXP=Path(__file__).resolve().parent
OUTPUT=base.history.ROOT/'artifacts/methods/v23_2/v23_2_response_construction_001'
PROMPT=EXP/'config/preconditioner_prompt.md'
original_implementation=base.implementation


def implementation():
    return {**original_implementation(),str(Path(__file__).resolve().relative_to(base.history.ROOT)):Path(__file__).read_text()}


def execute(action):
    # Temporary profile values only; the archived runner and source files are untouched.
    with patch.multiple(base,EXP=EXP,OUTPUT=OUTPUT,PROMPT=PROMPT,implementation=implementation):
        if action=='prepare':
            base.prepare()
            plan=base.evolution.read(EXP/'config/plan.json')
            plan['revision']='response_construction'
            base.evolution.save(EXP/'config/plan.json',plan)
        else:
            base.run()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','run'))
    execute(p.parse_args().action)
