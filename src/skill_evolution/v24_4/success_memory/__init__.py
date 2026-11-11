"""Retained v24.4 prompts with a separate success-pair Replay reader."""
from src.skill_evolution.v24_4 import ROOT, system_prompt as frozen_prompt

REVISIONS = ROOT / 'src/skill_evolution/v24_4/revisions'
PROMPT_FILES = {
    'diagnosis': REVISIONS / 'decision_priority/prompts/diagnosis.md',
    'preconditioner': REVISIONS / 'historical_attempt/prompts/preconditioner.md',
    'replay_success': REVISIONS / 'success_memory/prompts/replay_success.md',
}


def system_prompt(name):
    if name in PROMPT_FILES:
        return PROMPT_FILES[name].read_bytes().decode()
    return frozen_prompt(name)
