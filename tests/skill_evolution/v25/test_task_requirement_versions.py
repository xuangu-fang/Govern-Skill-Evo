"""Offline archive compatibility across Diagnosis and Preconditioner Prompt revisions."""
import json
from pathlib import Path
import shutil

import pytest

from src.skill_evolution.v25 import diagnosis, preconditioner, editor, output_feedback
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.config import method_config
from src.skill_evolution.v25.update_patch import CONTRACT_VERSION
from .test_pipeline import campaign


@pytest.mark.parametrize('diagnosis_version,preconditioner_version', [
    (diagnosis.LEGACY_PROMPT_VERSION, preconditioner.EXPLICIT_PROMPT_VERSION),
    (diagnosis.TASK_REQUIREMENTS_PROMPT_VERSION, preconditioner.TASK_REQUIREMENTS_PROMPT_VERSION),
    (diagnosis.SELF_CHECK_PROMPT_VERSION, preconditioner.SELF_CHECK_PROMPT_VERSION),
    (diagnosis.FALLBACK_REQUIREMENTS_PROMPT_VERSION, preconditioner.SELF_CHECK_PROMPT_VERSION),
    (diagnosis.FALLBACK_REQUIREMENTS_PROMPT_VERSION, preconditioner.EVIDENCE_DECISION_PROMPT_VERSION),
    (diagnosis.FALLBACK_REQUIREMENTS_PROMPT_VERSION, preconditioner.SCOPE_AWARE_PROMPT_VERSION),
])
def test_previous_prompts_reload_by_version_without_reinterpreting_archives(tmp_path, diagnosis_version, preconditioner_version):
    root, _, adapter, _, _, _ = campaign(tmp_path)
    round_path = root/'rounds/R01'
    with using_benchmark(adapter):
        current_d = round_path/'diagnosis/attempts/001'
        current_p = round_path/'preconditioner/attempts/001'
        old_d = tmp_path/'old_diagnosis'
        old_p = tmp_path/'old_preconditioner'
        shutil.copytree(current_d, old_d)
        shutil.copytree(current_p, old_p)

        def read(path, name):
            return json.loads((path/name).read_text())

        def write(path, name, value):
            (path/name).write_text(json.dumps(value))

        def replace_messages(path, messages):
            messages = output_feedback.request_messages(messages, output_feedback.saved_context(path))
            assert messages[1] == read(path, 'messages.json')[1]  # user input unchanged
            write(path, 'messages.json', messages)
            (path/'prompt.md').write_text(messages[0]['content'])

        dm = read(old_d, 'run.json')
        assert dm['prompt_version'] == diagnosis.PROMPT_VERSION
        dm['prompt_version'] = diagnosis_version
        write(old_d, 'run.json', dm)
        with pytest.raises(ValueError, match='prompt/input differs'):
            diagnosis.load_diagnosis(old_d)  # metadata alone cannot relabel a new Prompt
        replace_messages(old_d, diagnosis.messages_for(read(old_d, 'input.json'),
            retry_policy=output_feedback.policy(output_feedback.saved_context(old_d)),
            prompt_version=diagnosis_version))
        assert diagnosis.load_diagnosis(old_d) == diagnosis.load_diagnosis(current_d)

        pm = read(old_p, 'run.json')
        assert pm['prompt_version'] == preconditioner.KNOWLEDGE_PROMPT_VERSION
        assert pm['contract_version'] == CONTRACT_VERSION
        pm.update(prompt_version=preconditioner_version,
                  diagnosis_directory=str(old_d))
        write(old_p, 'run.json', pm)
        if preconditioner_version != preconditioner.KNOWLEDGE_PROMPT_VERSION:
            with pytest.raises(ValueError, match='prompt/input differs'):
                preconditioner.load_preconditioner(old_p)
        else:
            # Diagnosis-only revisions leave the Preconditioner request unchanged.
            assert preconditioner.load_preconditioner(old_p) == preconditioner.load_preconditioner(current_p)
        replace_messages(old_p, preconditioner.messages_for(read(old_p, 'input.json'),
            retry_policy=output_feedback.policy(output_feedback.saved_context(old_p)),
            prompt_version=preconditioner_version))
        before = {str(f): f.read_bytes() for folder in [old_d, old_p]
                  for f in folder.iterdir() if f.is_file()}
        old_saved = preconditioner.load_preconditioner(old_p)
        new_saved = preconditioner.load_preconditioner(current_p)
        assert old_saved == new_saved
        assert editor.editor_input(old_saved) == editor.editor_input(new_saved)
        assert all(Path(f).read_bytes() == content for f, content in before.items())


def test_future_config_uses_current_prompts_with_unchanged_preconditioner_contract():
    path = Path(__file__).resolve().parents[3]/'experiments/methods/v25/configurations/v25_spreadsheetbench_full120_batch15.json'
    method = json.loads(path.read_text())['method']
    assert method['knowledge_review'] == 'obvious_fact_verifier_targeted_repair_v1'
    assert method == method_config(method['knowledge_review'])
    assert method['preconditioner_contract'] == 'v25_explicit_references_v2'
    assert method['diagnosis_version'] == 'v25_diagnosis_evidence_scoped_updates_v5'
    assert method['preconditioner_prompt'] == 'v25_preconditioner_evidence_decision_boundaries_v7'
    assert method['replay_prompt_version'] == 'v25_replay_decision_fidelity_v4'
