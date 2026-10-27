"""Frozen small live study; up to three explicitly authorized technical restarts."""
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import time

import requests
from experiments.methods.v23_3.archive_io import load_saved
from experiments.methods.v23_4.archive_io import archive_glob, resolve, runtime_root, source_path
from experiments.methods.v23_3.memory_compaction_live_validation_001.run import environment, transport
from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from src.skill_evolution.v23 import diagnosis as old_diagnosis, editor as old_editor, replay as old_replay
from src.skill_evolution.v23.preconditioner import preconditioner_input
from src.skill_evolution.v23.prompts import render_prompt
from src.skill_evolution.v23_3 import diagnosis as d233
from src.skill_evolution.v23_3.memory_view import project_messages
from src.skill_evolution.v23_4 import diagnosis, preconditioner, replay
from src.skill_evolution.v23_4.update_patch import normalize_update_patches
from tests.skill_evolution.v23_4.offline_cases import cases

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIMARY = ('R05', 'R06', 'A3', 'A5')


def now(): return datetime.now(timezone.utc).isoformat()
def read(path): return json.loads(resolve(path).read_text())
def sha(path): return hashlib.sha256(resolve(path).read_bytes()).hexdigest()


def save(path, value):
    path = resolve(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f: json.dump(value, f, ensure_ascii=False, indent=2)


def configuration():
    key, config = environment()
    return key, {**config, 'max_tokens': 32768}


def pc_messages(material):
    messages = [{'role': 'system', 'content': render_prompt(preconditioner.PROMPT_PATH.read_text(), material['background'])},
                {'role': 'user', 'content': json.dumps(material['payload'], ensure_ascii=False, separators=(',', ':'))}]
    return project_messages(messages)


def prepare():
    source_paths = []
    dd = ROOT / 'experiments/methods/v23_3/p3a_first_live_comparison_001/runs/diagnosis'
    saved = load_saved(d233.load_diagnosis, dd)
    mp = resolve(dd.parents[1] / 'config/memory.json')
    saved['memory'] = read(mp)
    source_paths += list(archive_glob(dd, '*.json')) + [mp]
    primary = {'R05': {'kind': 'real_development_archive', 'payload': preconditioner_input(saved),
                      'background': saved['background'], 'source': str(dd.relative_to(ROOT))}}
    save(HERE / 'config/current_grouping.json', {k: v for k, v in saved.items() if k not in ('diagnosis', 'memory')})
    refs_path = ROOT / 'experiments/methods/v23_3/p1r_multiline_001/fixtures/sources.json'
    refs = read(refs_path)['sources']['R06']
    original = read(ROOT / refs['diagnosis']); saved6 = read(ROOT / refs['facts'])
    response_path = (ROOT / refs['diagnosis']).with_name('response.json')
    assert parse_json_response(read(response_path)['content']) == original
    assert read(response_path)['finish_reason'] == 'stop'
    saved6.update(diagnosis=original, memory=read(ROOT / refs['memory'])['memory'])
    primary['R06'] = {'kind': 'real_development_archive', 'payload': preconditioner_input(saved6),
                      'background': saved6['background'], 'source': refs['diagnosis']}
    source_paths += [refs_path, response_path, *[ROOT / p for p in refs.values()]]
    synthetic = {c['id']: c for c in cases()}
    for label in ('A3', 'A5'):
        primary[label] = {'kind': 'synthetic_not_actor_evidence', 'payload': synthetic[label]['payload'],
                          'background': saved['background'], 'source': 'tests/skill_evolution/v23_4/offline_cases.py'}
    changed = deepcopy(primary['A3'])
    for rid in ('P1', 'Q1'):
        r = changed['payload']['memory']['sources'][f'H_A3/{rid}']['run']
        initial = 'A is unavailable; this historical task needs only a coarse estimate, which B supplies.'
        r['initial']['observation'] = initial; r['steps'][0]['before']['observation'] = initial
        r['steps'][0]['after']['observation'] = 'A remains unavailable.' if rid == 'P1' else 'A coarse estimate is obtained; no exact reading was measured.'
    changed['payload']['memory']['entries'][0]['knowledge'] = 'Using B met a coarse-estimate requirement. This observation does not establish suitability for the current exact-reading requirement.'
    primary['A3_quality_shift'] = changed
    for label, data in primary.items():
        old_diagnosis.validate_diagnosis({'decision': 'revise', 'reason': 'Frozen Original', 'plan': data['payload']['plan']}, data['payload'])
        save(HERE / f'config/cases/{label}.json', data)
        save(HERE / f'config/messages/{label}.json', pc_messages(data))
    rp = ROOT / 'artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/R03/replay/attempts/001'
    old = old_replay.load_replay(rp)
    save(HERE / 'config/replay_bundle.json', {k: v for k, v in old.items() if k != 'replay'})
    source_paths += list(rp.glob('*.json'))
    _, cfg = configuration()
    paths = [HERE / 'run.py', HERE / 'PROTOCOL.md', *archive_glob(HERE, 'config/**/*.json'),
             ROOT / 'tests/skill_evolution/v23_4/offline_cases.py',
             ROOT / 'src/skill_evolution/v22/diagnosis_editor.py']
    for folder in ('v23', 'v23_3', 'v23_4'):
        paths.extend((ROOT / 'src/skill_evolution' / folder).glob('*.py'))
        paths.extend((ROOT / 'src/skill_evolution' / folder).glob('*.md'))
    paths += source_paths
    paths += [ROOT / 'experiments/methods/v23_3/memory_compaction_live_validation_001/run.py',
              ROOT / 'experiments/methods/v23_3/p3a_transport_retry_001/run.py']
    save(HERE / 'config/freeze.json', {'at': now(), 'call_config': cfg, 'max_restarts': 3,
         'max_logical_calls': 13, 'max_http_attempts': 52,
         'sha256': {str(p.relative_to(ROOT)): sha(p) for p in paths}})
    print('Frozen', list(primary), 'Replay R03', flush=True)


def verify():
    frozen = read(HERE / 'config/freeze.json')
    key, cfg = configuration()
    assert cfg == frozen['call_config']
    for path, digest in frozen['sha256'].items(): assert sha(ROOT / path) == digest, path
    return key, cfg


def validate(stage, parsed, material):
    if stage == 'pc':
        legacy, effective = normalize_update_patches(parsed, material['payload'])
        return {'raw_preconditioner': parsed, 'preconditioner': legacy, 'effective_plan': effective}
    if stage == 'editor':
        status, candidate = old_editor.validate_editor(parsed, material['parent'])
        return {'editor': parsed, 'editor_status': status, 'candidate_text': candidate,
                'actual_diff': None if candidate is None else old_editor.actual_diff(material['parent'], candidate)}
    if stage == 'diagnosis':
        old_diagnosis.validate_diagnosis(parsed, old_diagnosis.diagnosis_input(material))
        return {'diagnosis': parsed}
    if stage == 'replay':
        old_replay.validate_entries(parsed, material['payload'])
        return {'replay': parsed}
    raise ValueError('Unknown stage')


def load(label, stage):
    root = HERE / 'runs' / f'{label}_{stage}'
    chosen = read(root / 'selected.json')
    attempt = root / f'attempt_{chosen["attempt"]:03}'
    response = read(attempt / 'response.json')
    assert response['finish_reason'] == 'stop'
    parsed = parse_json_response(response['content'])
    assert parsed == read(attempt / 'parsed.json')
    material = read(root / 'material.json')
    result = validate(stage, parsed, material)
    assert result == read(attempt / 'result.json')
    return result


def inputs(label, stage):
    if stage == 'diagnosis':
        assert label == 'fresh'
        material = read(HERE / 'config/current_grouping.json')
        return material, diagnosis.messages_for(material)
    if stage == 'replay':
        assert label == 'R03'
        material = read(HERE / 'config/replay_bundle.json')
        return material, replay.messages_for(material)
    if stage == 'pc':
        if label == 'fresh':
            saved = {**read(HERE / 'config/current_grouping.json'), **load('fresh', 'diagnosis'),
                     'memory': read(HERE / 'config/cases/R05.json')['payload']['memory']}
            material = {'payload': preconditioner_input(saved), 'background': saved['background'], 'kind': 'new_real_diagnosis'}
        else:
            assert label in (*PRIMARY, 'A3_quality_shift')
            material = read(HERE / f'config/cases/{label}.json')
        return material, pc_messages(material)
    assert stage == 'editor' and label in (*PRIMARY, 'fresh')
    conditioned = load(label, 'pc')
    if conditioned['effective_plan'] is None: raise ValueError('Legitimate all-withdrawn stop: no Editor call')
    pc_material = read(HERE / 'runs' / f'{label}_pc/material.json')
    material = {'parent': pc_material['payload']['parent'], 'plan': conditioned['effective_plan'],
                'background': pc_material['background']}
    messages = [{'role': 'system', 'content': render_prompt(old_editor.PROMPT_PATH.read_text(), material['background'])},
                {'role': 'user', 'content': json.dumps({k: material[k] for k in ('parent', 'plan')}, ensure_ascii=False, separators=(',', ':'))}]
    return material, messages


def run(label, stage):
    key, cfg = verify()
    material, messages = inputs(label, stage)
    root = runtime_root(HERE) / 'runs' / f'{label}_{stage}'; root.mkdir(parents=True, exist_ok=True)
    with (runtime_root(HERE) / 'live.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if resolve(root / 'selected.json').exists():
            load(label, stage); print('Reused', label, stage); return
        if resolve(root / 'material.json').exists():
            assert read(root / 'material.json') == material and read(root / 'messages.json') == messages
        else:
            save(root / 'material.json', material); save(root / 'messages.json', messages)
        max_tokens = 32768
        for attempt_number in range(1, 5):
            dest = root / f'attempt_{attempt_number:03}'
            if resolve(dest).exists():
                # Never repeat an attempted HTTP. Unknown interrupted attempts consume a slot.
                prior = read(dest / 'attempt.json') if resolve(dest / 'attempt.json').exists() else {'retryable': True}
                if resolve(dest / 'response.json').exists() and read(dest / 'response.json').get('finish_reason') == 'length': max_tokens = 65536
                if prior.get('status') == 'valid':
                    save(root / 'selected.json', {'attempt': attempt_number}); load(label, stage); return
                if not prior.get('retryable'): raise RuntimeError('Prior non-retryable failure')
                continue
            dest.mkdir()
            body = {k: v for k, v in cfg.items() if k not in ('endpoint', 'timeout_seconds')}
            body.update(messages=messages, max_tokens=max_tokens)
            request = {'endpoint': cfg['endpoint'], 'body': body}
            meta = {'started_at': now(), 'label': label, 'stage': stage, 'attempt': attempt_number, 'max_tokens': max_tokens}
            save(dest / 'started.json', meta)
            print('START', label, stage, attempt_number, 'max_tokens', max_tokens, flush=True)
            began = time.monotonic()
            try:
                response = transport()(request, key, dest / 'http', {'connect_upload_timeout_seconds': 60, 'read_timeout_seconds': 300})
                save(dest / 'response.json', response)
                (dest / 'raw_output.txt').write_text(response['content'])
                if response['finish_reason'] != 'stop': raise ValueError('Model response did not finish normally')
                parsed = parse_json_response(response['content']); save(dest / 'parsed.json', parsed)
                result = validate(stage, parsed, material); save(dest / 'result.json', result)
                if stage == 'editor' and result['candidate_text'] is not None:
                    (dest / 'candidate.md').write_text(result['candidate_text'])
                    (dest / 'actual.diff').write_text(result['actual_diff'])
                meta.update(status='valid', retryable=False)
            except Exception as exc:
                status_path = dest / 'http/http_status.json'
                code = read(status_path)['status_code'] if resolve(status_path).exists() else None
                response = read(dest / 'response.json') if resolve(dest / 'response.json').exists() else {}
                retryable = (code in (408, 429, 500, 502, 503, 504) or
                    (code is None and isinstance(exc, (requests.Timeout, requests.ConnectionError))) or
                    (code is not None and 200 <= code < 300 and isinstance(exc, (ValueError, KeyError, TypeError))))
                meta.update(status='technical_failure', retryable=retryable, http_status=code,
                            error_type=type(exc).__name__, error=str(exc)[:1200])
                if response.get('finish_reason') == 'length': max_tokens = 65536
            meta.update(finished_at=now(), elapsed_seconds=round(time.monotonic()-began, 3))
            save(dest / 'attempt.json', meta)
            print('END', label, stage, attempt_number, meta['status'], meta['elapsed_seconds'], meta.get('error', ''), flush=True)
            if meta['status'] == 'valid':
                save(root / 'selected.json', {'attempt': attempt_number}); load(label, stage); return
            if not meta['retryable']: raise RuntimeError('Non-retryable failure; inspect attempt archive')
            if attempt_number < 4: time.sleep((15, 30, 60)[attempt_number-1])
        raise RuntimeError('Three authorized restarts exhausted')


if __name__ == '__main__':
    if sys.argv[1] == 'prepare': prepare()
    else: run(sys.argv[1], sys.argv[2])
