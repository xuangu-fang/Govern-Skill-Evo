"""ALFWorld V24.4 with frozen Diagnosis and history-guided Preconditioner prompts."""
from src.skill_evolution.v24_2 import ROOT, system_prompt as baseline_prompt

PROMPTS = ROOT / 'src/skill_evolution/v24_4/prompts'
REVISIONS = PROMPTS.parent / 'revisions'
PROMPT_FILES = {
    'diagnosis': REVISIONS / 'decision_priority/prompts/diagnosis.md',
    'preconditioner': REVISIONS / 'historical_attempt/prompts/preconditioner.md',
}
UPDATED = tuple(PROMPT_FILES)


def system_prompt(name):
    if name in UPDATED:
        return PROMPT_FILES[name].read_text(encoding='utf-8')
    return baseline_prompt(name)
