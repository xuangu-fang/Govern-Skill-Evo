"""ALFWorld v24.8: learning executable decisions from ALFWorld trajectories."""
from src.skill_evolution.v24_2 import ROOT, STAGES

PROMPTS = ROOT / 'src/skill_evolution/v24_8/prompts'


def system_prompt(name):
    if name not in STAGES:
        raise ValueError(f'Unknown v24.8 stage: {name}')
    return (PROMPTS / f'{name}.md').read_text(encoding='utf-8')
