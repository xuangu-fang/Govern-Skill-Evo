"""P6: exact P4 frozen messages, isolated outputs, bounded technical retries."""
from pathlib import Path
import json
import sys

from experiments.methods.v23_4.semantic_generation_001 import run as core
from experiments.methods.v23_4.multi_knowledge_p4_001 import prepare_inputs as p4
from src.skill_evolution.v23 import memory

HERE = Path(__file__).resolve().parent
ROOT = core.ROOT
core.HERE = HERE
NEW = memory.MULTI_KNOWLEDGE_CONTRACT


def inputs(label, stage):
    assert stage == 'replay' and label in ('R05', 'R06')
    path = p4.HERE / 'cases' / label
    bundle = core.read(path / 'replay_bundle.json')
    messages = core.read(path / 'messages.json')
    assert messages == core.replay.messages_for(bundle, memory_contract=NEW,
        prompt_version=core.replay.LEARNING_PROMPT_VERSION,
        history_sources=core.read(path / 'history_pair_sources.json'))
    assert len(json.dumps(messages, ensure_ascii=False)) <= 1_200_000
    return bundle, messages


def validate(stage, parsed, material):
    assert stage == 'replay'
    memory.validate_entries(parsed, material['payload'], memory_contract=NEW)
    return {'replay': parsed}


core.inputs = inputs
core.validate = validate


def prepare():
    checked = p4.verify()
    manifest = core.read(p4.HERE / 'freeze.json')
    _, cfg = core.configuration()
    assert cfg == manifest['call_config']
    frozen = dict(manifest['sha256'])
    paths = [p4.HERE / 'freeze.json', HERE / 'run.py', HERE / 'check_memory.py', HERE / 'PROTOCOL.md',
        ROOT / 'experiments/methods/v23_4/semantic_generation_001/run.py',
        ROOT / 'experiments/methods/v23_3/memory_compaction_live_validation_001/run.py',
        ROOT / 'experiments/methods/v23_3/p3a_transport_retry_001/run.py']
    frozen.update({str(p.relative_to(ROOT)): core.sha(p) for p in paths})
    core.save(HERE / 'config/freeze.json', {**manifest, 'status': 'authorized_live_p6',
        'at': core.now(), 'sha256': frozen})
    # Protect historical facts, prior experiments and all current production sources.
    protected = core.read(p4.HERE / 'protected_before.json')
    for rel, digest in protected.items():
        assert core.sha(ROOT / rel) == digest, rel
    protected.update({str(p.relative_to(ROOT)): core.sha(p) for p in core.archive_glob(p4.HERE, '*', recursive=True) if p.is_file()})
    core.save(HERE / 'protected_before.json', protected)
    core.verify()
    print(json.dumps(checked), flush=True)


def audit():
    core.verify()
    before = core.read(HERE / 'protected_before.json')
    assert all(core.sha(ROOT / p) == digest for p, digest in before.items())
    results = {}
    for label in ('R05', 'R06'):
        root = HERE / 'runs' / f'{label}_replay'
        attempts = []
        for path in core.archive_glob(root, 'attempt_*'):
            meta = core.read(path / 'attempt.json')
            response = core.read(path / 'response.json') if core.resolve(path / 'response.json').exists() else {}
            request = core.read(path / 'http/request.json')
            assert request['body']['messages'] == inputs(label, 'replay')[1]
            assert request['transport_retries'] == 0
            attempts.append({**meta, 'usage': response.get('usage'), 'finish_reason': response.get('finish_reason')})
        assert len(attempts) <= 4
        if core.resolve(root / 'selected.json').exists(): core.load(label, 'replay')
        results[label] = attempts
    result = {'cases': results, 'http_attempts': sum(map(len, results.values())),
        'protected_files_unchanged': len(before), 'memory_contract': NEW,
        'prompt_version': core.replay.LEARNING_PROMPT_VERSION}
    (HERE / 'AUDIT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']: prepare()
    elif sys.argv[1:] == ['audit']: audit()
    elif sys.argv[1:] == ['run']:
        failures = []
        for label in ('R05', 'R06'):
            try: core.run(label, 'replay')
            except Exception as exc:
                failures.append({'case': label, 'error_type': type(exc).__name__, 'error': str(exc)})
        if failures:
            core.save(HERE / 'failures.json', failures)
            raise SystemExit('See failures.json; no additional retries authorized.')
    else: raise SystemExit('Use prepare, run, or audit')
