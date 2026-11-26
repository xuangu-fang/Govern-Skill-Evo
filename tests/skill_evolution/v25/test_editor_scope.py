"""Fixed scope-fidelity cases and offline Editor archive compatibility.

These checks validate fixture integrity and patch plumbing, not model semantics.
"""
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from src.skill_evolution.v25 import editor, output_feedback
from src.skill_evolution.v25.benchmark import using_benchmark
from .test_pipeline import campaign

FIXTURES = Path(__file__).parent/'fixtures/editor_scope'


def read(name):
    return json.loads((FIXTURES/name).read_text())


def test_fixed_cases_are_traceable_and_evaluation_is_separate():
    manifest = read('manifest.json')
    for name, digest in manifest['files'].items():
        assert hashlib.sha256((FIXTURES/name).read_bytes()).hexdigest() == digest
    for item in manifest['originals']:
        assert manifest['files'][item['snapshot']] == item['sha256']
    cases = read('cases.json')
    assert cases['model_visible'] is False
    assert cases['semantic_evaluation'] == 'not_run'
    original, positive = read('r05_input.json'), read('positive_input.json')
    assert set(original) == set(positive) == {'parent', 'plan'}
    messages = read('r05_messages.json')
    assert json.loads(messages[1]['content']) == original
    assert original['parent'] == positive['parent']
    assert original['plan']['updates'][:2] == positive['plan']['updates'][:2]
    negative, control = cases['cases']
    assert negative['observation_excerpt'] in original['plan']['updates'][2]['text']
    assert negative['baseline_excerpt'] in read('r05_editor.json')['patch']
    assert control['authorized_excerpt'] in positive['plan']['updates'][2]['text']
    assert control['authorized_excerpt'] not in original['plan']['updates'][2]['text']


@pytest.mark.parametrize('case', read('cases.json')['cases'], ids=lambda c: c['id'])
def test_reference_patches_apply_without_new_semantic_enforcement(case):
    payload = read(case['input'])
    result = read(case['reference_output'])
    status, candidate = editor.validate_editor(result, payload['parent'])
    assert status == 'candidate'
    assert candidate != payload['parent']
    if case['kind'] == 'observed_regression':
        # The historical problematic output also passes structure validation.
        # This change adds guidance, not an automatic semantic checker.
        old_status, old_candidate = editor.validate_editor(read(case['baseline_output']), payload['parent'])
        assert old_status == 'candidate'
        assert case['baseline_excerpt'] in old_candidate
        assert case['baseline_excerpt'] not in candidate
    else:
        assert case['authorized_excerpt'] in candidate


def test_editor_archive_versions_reload_with_their_own_prompts(tmp_path):
    root, _, adapter, _, _, _ = campaign(tmp_path)
    current = root/'rounds/R01/editor/attempts/001'
    old = tmp_path/'old_editor'
    shutil.copytree(current, old)
    with using_benchmark(adapter):
        original = editor.load_editor(current)
        meta = json.loads((old/'run.json').read_text())
        assert meta['prompt_version'] == editor.PROMPT_VERSION
        meta['prompt_version'] = editor.LEGACY_PROMPT_VERSION
        (old/'run.json').write_text(json.dumps(meta))
        with pytest.raises(ValueError, match='prompt/input differs'):
            editor.load_editor(old)
        saved = json.loads((old/'upstream.json').read_text())
        context = output_feedback.saved_context(old)
        messages = editor.messages_for(saved, memory_contract=meta['memory_contract'],
            retry_policy=output_feedback.policy(context), prompt_version=editor.LEGACY_PROMPT_VERSION)
        messages = output_feedback.request_messages(messages, context)
        assert messages[1] == json.loads((current/'messages.json').read_text())[1]
        (old/'messages.json').write_text(json.dumps(messages))
        (old/'prompt.md').write_text(messages[0]['content'])
        before = {f.name: f.read_bytes() for f in old.iterdir() if f.is_file()}
        assert editor.load_editor(old) == original
        assert before == {f.name: f.read_bytes() for f in old.iterdir() if f.is_file()}
        meta['prompt_version'] = 'unknown_editor_version'
        (old/'run.json').write_text(json.dumps(meta))
        with pytest.raises(ValueError, match='Unsupported Editor prompt version'):
            editor.load_editor(old)
