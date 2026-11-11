"""ALFWorld v24.10: learning executable decisions from ALFWorld trajectories."""
from src.skill_evolution.v24_2 import ROOT, STAGES

PROMPTS = ROOT / 'src/skill_evolution/v24_10/prompts'


def system_prompt(name):
    if name not in STAGES:
        raise ValueError(f'Unknown v24.10 stage: {name}')
    return (PROMPTS / f'{name}.md').read_text(encoding='utf-8')
