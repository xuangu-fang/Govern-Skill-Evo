"""ALFWorld v24.11 with success-flip Replay and per-update selection."""
from pathlib import Path

from src.skill_evolution.v24_2 import ROOT, STAGES

PROMPTS = Path(__file__).with_name('prompts')


def prompt_path(name):
    if name not in STAGES:
        raise ValueError(f'Unknown v24.11 stage: {name}')
    if name == 'diagnosis':
        return ROOT / 'src/skill_evolution/v24_10/prompts/diagnosis.md'
    return PROMPTS / f'{name}.md'


def system_prompt(name):
    return prompt_path(name).read_text(encoding='utf-8')
