"""Explicit prompt revision leaves historical archives and all data contracts intact."""
from pathlib import Path

import pytest

from src.skill_evolution.v23 import editor, preconditioner
from src.skill_evolution.v23_2 import local_validation as local
from tests.skill_evolution.v23_2.test_local_validation import saved, config, keep
from tests.skill_evolution.v23.test_diagnosis import answer


PROMPT = Path('experiments/methods/v23_2/v23_2_executability_002/config/preconditioner_prompt.md')
OLD_PROMPT = Path('src/skill_evolution/v23_2/preconditioner_prompt.md')


def test_final_update_revision_and_historical_compatibility(saved, config, tmp_path):
    old = OLD_PROMPT.read_text()
    before = ('Check whether each Update is executable throughout its intended behavior. '
              'If it depends on unavailable information, adjust its strategy or scope to remove that dependency, or withdraw it. '
              'Merely acknowledging the limitation in the reason is insufficient.')
    after = ('Before finalizing, check every Update in the resulting Effective Plan, including unchanged ones. '
             'Each required decision must be supported by information available to the Actor when that decision is made. '
             'Otherwise, revise or withdraw the Update without introducing unsupported restrictions.')
    assert old.count(before) == 1 and PROMPT.read_text() == old.replace(before, after)
    original = local.messages_for('preconditioner', saved, prompt_path=OLD_PROMPT)
    changed = local.messages_for('preconditioner', saved, prompt_path=PROMPT)
    assert changed[1] == original[1] == preconditioner.messages_for(saved)[1]
    historical = local.run_stage('preconditioner', saved, tmp_path/'old', config, prompt_path=OLD_PROMPT,
                                 generate=lambda *_: answer(keep()))
    current = local.run_stage('preconditioner', saved, tmp_path/'new', config, prompt_path=PROMPT,
                              generate=lambda *_: answer(keep()))
    assert historical == current
    assert local.load_attempt(tmp_path/'old/attempts/001', prompt_path=OLD_PROMPT) == historical
    assert local.load_attempt(tmp_path/'new/attempts/001', prompt_path=PROMPT) == current
    with pytest.raises(ValueError, match='Saved messages differ'):
        local.load_attempt(tmp_path/'new/attempts/001')
    assert editor.editor_input(current)['plan'] == current['effective_plan']
    assert current['memory'] == saved['memory']


def test_previous_real_archive_still_loads():
    path = Path('artifacts/methods/v23_2/v23_2_executability_001/fixed_R03/attempts/002')
    if not path.exists():
        pytest.skip('Local historical archive unavailable')
    saved = local.load_attempt(path, prompt_path=OLD_PROMPT)
    assert saved['preconditioner']['decision'] == 'ready'
