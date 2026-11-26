"""Offline Replay template selection and immutable archive compatibility."""
import json
import shutil

import pytest

from src.skill_evolution.v25 import output_feedback, replay
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.contracts.memory import MULTI_KNOWLEDGE_CONTRACT
from .support import MethodResponses
from .test_pipeline import campaign


@pytest.mark.parametrize('legacy_version', [replay.LEGACY_KNOWLEDGE_PROMPT_VERSION,
                                          replay.LEGACY_V2_KNOWLEDGE_PROMPT_VERSION,
                                          replay.LEGACY_V3_KNOWLEDGE_PROMPT_VERSION])
def test_replay_legacy_reload_preserves_input_history_output_and_archive(tmp_path, legacy_version):
    root, _, adapter, actors, method, _ = campaign(
        tmp_path, rounds=2, method=MethodResponses(history=True))
    current = root/'rounds/R02/replay/attempts/001'
    old = tmp_path/'legacy_replay'
    shutil.copytree(current, old)
    read = lambda path, name: json.loads((path/name).read_text())

    with using_benchmark(adapter):
        saved = replay.load_replay(current)
        assert saved['payload']['memory']['entries']
        meta = read(old, 'run.json')
        assert meta['prompt_version'] == replay.KNOWLEDGE_PROMPT_VERSION
        meta['prompt_version'] = legacy_version
        (old/'run.json').write_text(json.dumps(meta))
        # Changing only the label cannot reinterpret a current request as legacy.
        with pytest.raises(ValueError, match='Replay prompt differs'):
            replay.load_replay(old)
        context = output_feedback.saved_context(old)
        messages = replay.messages_for(read(old, 'input.json'),
            prompt_version=legacy_version,
            retry_policy=output_feedback.policy(context))
        messages = output_feedback.request_messages(messages, context)
        assert messages[1:] == read(current, 'messages.json')[1:]
        (old/'messages.json').write_text(json.dumps(messages))
        (old/'prompt.md').write_text(messages[0]['content'])
        before = {p: p.read_bytes() for p in old.iterdir() if p.is_file()}
        calls = (len(actors.calls), len(method.calls))
        assert replay.load_replay(old) == saved
        assert calls == (len(actors.calls), len(method.calls))
        assert all(p.read_bytes() == content for p, content in before.items())
        with pytest.raises(ValueError, match='Replay prompt version differs'):
            replay.load_replay(old, expected_prompt_version=replay.KNOWLEDGE_PROMPT_VERSION)
        with pytest.raises(ValueError, match='Unsupported Replay prompt version'):
            replay._prompt(MULTI_KNOWLEDGE_CONTRACT, 'unknown')
