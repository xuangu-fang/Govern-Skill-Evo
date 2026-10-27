"""Two frozen new-view Replay calls; reuse the established technical retry policy."""
import json
from pathlib import Path
import sys

from experiments.methods.v23_4.semantic_generation_001 import run as core

core.HERE = Path(__file__).resolve().parent
HERE, ROOT = core.HERE, core.ROOT
OFFLINE = HERE.with_name('replay_input_view_001')


def inputs(label, stage):
    assert stage == 'replay' and label in ('R05', 'R06')
    path = HERE / 'config' / label
    bundle = core.read(path / 'replay_bundle.json')
    sources = core.read(path / 'history_pair_sources.json')
    messages = core.replay.messages_for(bundle, history_sources=sources)
    assert messages == core.read(path / 'messages.json')
    assert json.loads(messages[1]['content']) == core.read(path / 'model_input.json')
    assert len(json.dumps(messages, ensure_ascii=False)) <= 1_200_000
    return bundle, messages


core.inputs = inputs


def prepare():
    frozen = core.read(OFFLINE / 'freeze.json')['sha256']
    for name, digest in frozen.items():
        assert core.sha(ROOT / name) == digest, name
    _, cfg = core.configuration()
    for label in ('R05', 'R06'):
        old = HERE.with_name(label.lower() + '_replay_memory_001')
        assert cfg == core.read(old / 'config/freeze.json')['call_config']
        core.save(HERE / f'config/{label}/replay_bundle.json', core.read(old / 'config/replay_bundle.json'))
        for name in ('history_pair_sources.json', 'messages.json', 'model_input.json'):
            core.save(HERE / f'config/{label}/{name}', core.read(OFFLINE / 'cases' / label / name))
        inputs(label, 'replay')
    paths = [HERE / 'run.py', HERE / 'check_memory.py', HERE / 'PROTOCOL.md',
             OFFLINE / 'freeze.json', *core.archive_glob(HERE, 'config/**/*.json'),
             ROOT / 'experiments/methods/v23_4/semantic_generation_001/run.py',
             ROOT / 'experiments/methods/v23_4/semantic_generation_001/audit.py',
             ROOT / 'experiments/methods/v23_3/memory_compaction_live_validation_001/run.py',
             ROOT / 'experiments/methods/v23_3/p3a_transport_retry_001/run.py']
    frozen.update({str(p.relative_to(ROOT)): core.sha(p) for p in paths})
    core.save(HERE / 'config/freeze.json', {
        'at': core.now(), 'call_config': cfg, 'input_view': core.replay.INPUT_VIEW,
        'max_input_chars': 1_200_000, 'production_default_input_chars': 400_000,
        'max_restarts_per_stage': 3, 'max_logical_calls': 2, 'max_http_attempts': 8,
        'sha256': frozen})
    core.verify()
    print('Frozen R05/R06 new-view Replay; 2 stages, <=4 attempts each', flush=True)


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
