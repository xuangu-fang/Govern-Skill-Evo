"""Frozen candidate main Prompt; unchanged view, facts, configuration and transport."""
import json
from pathlib import Path
import sys

from experiments.methods.v23_4.semantic_generation_001 import run as core
from src.skill_evolution.v23.prompts import execution_context

core.HERE = Path(__file__).resolve().parent
HERE, ROOT = core.HERE, core.ROOT
BASELINE = HERE.with_name('replay_input_view_live_001')


def assemble(label):
    path = HERE / 'config' / label
    bundle = core.read(path / 'replay_bundle.json')
    sources = core.read(path / 'history_pair_sources.json')
    baseline_messages = core.replay.messages_for(bundle, history_sources=sources)
    assert baseline_messages == core.read(BASELINE / f'config/{label}/messages.json')
    assert json.loads(baseline_messages[1]['content']) == core.read(path / 'model_input.json')
    system = (HERE / 'candidate_prompt.md').read_text().rstrip()
    system += '\n\n' + execution_context(bundle['background'])
    system += '\n\n' + core.replay.MEMORY_FORMAT_PATH.read_text()
    system += '\n\n' + core.replay.VIEW_FORMAT_PATH.read_text()
    messages = [{'role': 'system', 'content': system}, baseline_messages[1]]
    for heading in ('## Execution Context', '## Historical Memory evidence view v3',
                    '## Replay paired-input view v1'):
        assert system.count(heading) == 1
    assert messages[1] == baseline_messages[1]
    assert len(json.dumps(messages, ensure_ascii=False)) <= 1_200_000
    return bundle, messages


def inputs(label, stage):
    assert stage == 'replay' and label in ('R05', 'R06')
    bundle, messages = assemble(label)
    assert messages == core.read(HERE / f'config/{label}/messages.json')
    return bundle, messages


core.inputs = inputs


def prepare():
    baseline = core.read(BASELINE / 'config/freeze.json')
    frozen = dict(baseline['sha256'])
    for path, digest in frozen.items():
        assert core.sha(ROOT / path) == digest, path
    _, cfg = core.configuration()
    assert cfg == baseline['call_config']
    original = Path('/Users/didi/Downloads/replay_prompt_v23_4.md')
    assert original.read_bytes() == (HERE / 'candidate_prompt.md').read_bytes()
    comparison = {}
    for label in ('R05', 'R06'):
        for name in ('replay_bundle.json', 'model_input.json', 'history_pair_sources.json'):
            core.save(HERE / f'config/{label}/{name}', core.read(BASELINE / f'config/{label}/{name}'))
        bundle, messages = assemble(label)
        core.save(HERE / f'config/{label}/messages.json', messages)
        (HERE / f'config/{label}/system_prompt.md').write_text(messages[0]['content'])
        inputs(label, 'replay')
        comparison[label] = {'user_message_identical': True, 'full_bundle_identical': True,
                             'history_sources_identical': True, 'call_config_identical': True,
                             'request_chars': len(json.dumps(messages, ensure_ascii=False))}
    core.save(HERE / 'config/comparison.json', comparison)
    paths = [HERE / 'run.py', HERE / 'check_memory.py', HERE / 'PROTOCOL.md',
             HERE / 'candidate_prompt.md', BASELINE / 'config/freeze.json',
             *core.archive_glob(HERE, 'config/**/*.json'), *HERE.glob('config/**/*.md')]
    frozen.update({str(p.relative_to(ROOT)): core.sha(p) for p in paths})
    core.save(HERE / 'config/freeze.json', {
        'at': core.now(), 'call_config': cfg, 'input_view': core.replay.INPUT_VIEW,
        'prompt_candidate': 'replay_prompt_candidate_001',
        'candidate_source': str(original), 'candidate_sha256': core.sha(original),
        'max_input_chars': 1_200_000, 'max_restarts_per_stage': 3,
        'max_logical_calls': 2, 'max_http_attempts': 8, 'sha256': frozen})
    core.verify()
    print('Frozen original candidate, unchanged R05/R06 user messages and call configuration.', flush=True)


if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['prepare']:
        prepare()
    elif args == ['audit']:
        from experiments.methods.v23_4.semantic_generation_001.audit import audit
        result = audit()
        assert result['logical_stages'] <= 2 and result['http_attempts'] <= 8
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        assert args == ['run']
        for label in ('R05', 'R06'):
            core.run(label, 'replay')
