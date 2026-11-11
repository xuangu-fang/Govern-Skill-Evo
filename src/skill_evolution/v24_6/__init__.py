"""ALFWorld v24.6: completion and efficiency evidence for per-Update selection."""
from src.skill_evolution.v24_2 import ROOT, STAGES

PROMPTS = ROOT / 'src/skill_evolution/v24_6/prompts'


def system_prompt(name):
    if name not in STAGES:
        raise ValueError(f'Unknown v24.6 stage: {name}')
    return (PROMPTS / f'{name}.md').read_text(encoding='utf-8')
