"""ALFWorld V24.3 with decision-local Diagnosis and Preconditioner prompts."""
from src.skill_evolution.v24_2 import ROOT, system_prompt as baseline_prompt

PROMPTS = ROOT / 'src/skill_evolution/v24_3/prompts'
UPDATED = ('diagnosis', 'preconditioner')


def system_prompt(name):
    if name in UPDATED:
        return (PROMPTS / f'{name}.md').read_bytes().decode('utf-8')
    return baseline_prompt(name)
