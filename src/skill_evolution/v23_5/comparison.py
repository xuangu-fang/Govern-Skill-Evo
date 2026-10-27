"""Prepare, run/resume, and summarize the fixed R03-R06 history-view comparison."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import time

from src.skill_evolution.v22.diagnosis_editor import parse_json_response
from src.skill_evolution.v23 import grouping
from src.skill_evolution.v23.editor import _read_text, _write_text
from src.skill_evolution.v23.facts import require
from src.skill_evolution.v23.preconditioner import preconditioner_input
from . import evolution, preconditioner, replay
from .update_patch import normalize_update_patches, actual_update_diffs
from .config import method_config
from .output_feedback import LEGACY
from .comparison_inputs import (ARMS, CONTRACT, ROUNDS, STAGES, case_path, read, save,
                                prepare, verify)


def validate_output(root, cell, parsed):
    """Use production output validators on verified historical evaluation material."""
    label, stage, arm = cell['round'], cell['stage'], cell['arm']
    material = read(Path(root)/'cases'/label/stage/'material.json')
    method = method_config(ARMS[arm], retry_policy=LEGACY)
    if stage == 'preconditioner':
        payload = preconditioner_input(material, memory_contract=CONTRACT)
        normalized, effective = normalize_update_patches(parsed, payload, memory_view=ARMS[arm], memory_contract=CONTRACT)
        return {'preconditioner': normalized, 'effective_plan': effective,
                'actual_diffs': actual_update_diffs(payload, effective)}
    return {'replay': replay.validate_result(parsed, material['payload'],
            input_view=method['replay_input_view'], memory_contract=CONTRACT)}


def finish_response(root, cell, dest, response):
    save(dest/'response.json', response)
    _write_text(dest/'raw_output.txt', response.get('content') or '')
    require(response.get('finish_reason') == 'stop', 'Response did not finish normally')
    parse = preconditioner.parse_json_response if cell['stage'] == 'preconditioner' else parse_json_response
    parsed = parse(response['content'])
    save(dest/'parsed.json', parsed)
    validated = validate_output(root, cell, parsed)
    save(dest/'validated.json', validated)
    save(dest/'validation.json', {'valid': True})
    return validated


def check_attempt_inputs(root, cell, dest, spec):
    meta = read(dest/'attempt.json')
    require(meta['cell'] == cell and meta['call_config'] == spec['call_config'], 'Saved attempt configuration differs')
    frozen = read(case_path(root, cell['round'], cell['stage'], cell['arm'])/'messages.json')
    require(read(dest/'messages.json') == frozen,
            'Saved attempt messages differ')
    if (dest/'request.json').exists():
        request = read(dest/'request.json')
        cfg = spec['call_config']
        body = {k: v for k, v in cfg.items() if k not in ('endpoint', 'timeout_seconds')}
        require(request == {'endpoint': cfg['endpoint'], 'body': {**body, 'messages': frozen},
                            'timeout_seconds': cfg['timeout_seconds'], 'attempts': 1},
                'Actual transport request differs from frozen messages/configuration')
    return meta


def load_attempt(root, cell, dest, spec):
    meta = check_attempt_inputs(root, cell, dest, spec)
    require(meta['status'] == 'valid' and read(dest/'validation.json')['valid'] is True, 'Attempt is not valid')
    response = read(dest/'response.json')
    require(response.get('finish_reason') == 'stop', 'Saved response incomplete')
    require(response['content'] == _read_text(dest/'raw_output.txt'), 'Raw output differs')
    parse = preconditioner.parse_json_response if cell['stage'] == 'preconditioner' else parse_json_response
    parsed = parse(response['content'])
    require(parsed == read(dest/'parsed.json'), 'Saved parse differs')
    validated = validate_output(root, cell, parsed)
    require(validated == read(dest/'validated.json'), 'Saved result differs from production validation')
    return validated


def live_generator(spec):
    """The existing single-request transport; never archive credentials."""
    from dotenv import load_dotenv
    load_dotenv(evolution.ROOT/'.env', override=False)
    cfg = spec['call_config']
    base = cfg['endpoint'].removesuffix('/chat/completions')
    require(os.environ.get('OPENAI_BASE_URL', '').rstrip('/') == base,
            'Live endpoint differs from frozen endpoint')
    gen = grouping.live_generator(base_url=base, key=os.environ.get('OPENAI_API_KEY'), model=cfg['model'],
                                  max_tokens=cfg['max_tokens'], timeout=cfg['timeout_seconds'])
    require(gen.call_config == cfg, 'Transport configuration differs from freeze')
    return gen


def _failed(dest, meta, exc, *, retryable):
    # Generic transport exception strings can include URLs; preserve their type only.
    detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
    save(dest/'validation.json', {'valid': False, 'error_type': type(exc).__name__, 'error': detail})
    meta.update(status='invalid', retryable=retryable, error_type=type(exc).__name__, error=detail)


def _recover(root, cell, dest, spec):
    """A persisted response is reused without another request or budget reset."""
    meta = check_attempt_inputs(root, cell, dest, spec)
    if meta['status'] == 'valid':
        load_attempt(root, cell, dest, spec)
        return True
    if meta['status'] == 'invalid':
        return False
    require(meta['status'] == 'requesting', 'Unknown attempt status')
    try:
        if (dest/'response.json').exists():
            response = read(dest/'response.json')
        elif (dest/'http_status.json').exists() and 200 <= read(dest/'http_status.json')['status_code'] < 300:
            response = grouping.response_value(read(dest/'http_response.txt'))
        else:
            raise ValueError('Interrupted request; outcome and usage may be unknown')
        finish_response(root, cell, dest, response)
        meta.update(status='valid', recovered_without_request=True)
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        retryable = evolution._retryable(exc, dest) if (dest/'http_status.json').exists() else True
        _failed(dest, meta, exc, retryable=retryable)
    meta['finished_at'] = evolution.now()
    save(dest/'attempt.json', meta)
    return meta['status'] == 'valid'


def run_cell(root, cell, spec, generate, *, resume=False):
    folder = Path(root)/'runs'/cell['round']/cell['stage']/cell['arm']
    folder.mkdir(parents=True, exist_ok=True)
    attempts = folder/'attempts'; attempts.mkdir(exist_ok=True)
    marker = folder/'result.json'
    existing = sorted(attempts.iterdir())
    require([p.name for p in existing] == [f'{i:03}' for i in range(1, len(existing)+1)], 'Attempt sequence differs')
    require(len(existing) <= spec['max_attempts'], 'Attempt budget exceeded')
    if marker.exists():
        chosen = read(marker)['attempt']
        require(chosen in [p.name for p in existing], 'Selected attempt outside this cell')
        load_attempt(root, cell, attempts/chosen, spec)
        return {'status': 'valid', 'attempt': chosen}
    require(not existing or resume, 'Prior attempts require explicit resume')
    if existing:
        for previous in existing:
            if _recover(root, cell, previous, spec):
                require(previous == existing[-1], 'A valid attempt must terminate the cell')
                save(marker, {'attempt': previous.name})
                return {'status': 'valid', 'attempt': previous.name}
        if not read(existing[-1]/'attempt.json')['retryable']:
            return {'status': 'failed', 'reason': 'non_retryable'}
    frozen = read(case_path(root, cell['round'], cell['stage'], cell['arm'])/'messages.json')
    for index in range(len(existing)+1, spec['max_attempts']+1):
        if index > 1:
            time.sleep(spec['retry_delay_seconds'])
        dest = attempts/f'{index:03}'; dest.mkdir()
        save(dest/'messages.json', frozen)
        meta = {'cell': cell, 'call_config': spec['call_config'],
                'started_at': evolution.now(), 'status': 'requesting', 'request_invoked': True}
        save(dest/'attempt.json', meta)
        started = time.monotonic()
        try:
            # Request is exactly the frozen messages; no feedback, repair, or truncation.
            response = generate(frozen, dest)
            finish_response(root, cell, dest, response)
            meta['status'] = 'valid'
        except Exception as exc:
            _failed(dest, meta, exc, retryable=evolution._retryable(exc, dest))
        finally:
            meta.update(finished_at=evolution.now(), elapsed_seconds=time.monotonic()-started)
            save(dest/'attempt.json', meta)
        if meta['status'] == 'valid':
            load_attempt(root, cell, dest, spec)
            save(marker, {'attempt': dest.name})
            return {'status': 'valid', 'attempt': dest.name}
        if not meta['retryable']:
            return {'status': 'failed', 'reason': 'non_retryable'}
    return {'status': 'failed', 'reason': 'attempts_exhausted'}


def run(root, *, generate=None, resume=False, rounds=ROUNDS, stages=STAGES, arms=tuple(ARMS)):
    from .comparison_stats import summarize
    root = Path(root).resolve()
    manifest = verify(root)
    require(set(rounds) <= set(ROUNDS) and set(stages) <= set(STAGES) and set(arms) <= set(ARMS),
            'Unknown requested cell')
    require(bool(rounds) and bool(stages) and bool(arms), 'Empty cell selection')
    spec = manifest['spec']
    with (root/'.run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        gen = live_generator(spec) if generate is None else generate
        require(getattr(gen, 'call_config', spec['call_config']) == spec['call_config'], 'Generator configuration differs')
        results = []
        try:
            for cell in manifest['cells']:
                if cell['round'] in rounds and cell['stage'] in stages and cell['arm'] in arms:
                    results.append({**cell, **run_cell(root, cell, spec, gen, resume=resume)})
        finally:
            summarize(root)
        verify(root)
    return results


def main(argv=None):
    from .comparison_stats import summarize
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'verify', 'run', 'resume', 'summarize'])
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--rounds', nargs='+', choices=ROUNDS, default=ROUNDS)
    parser.add_argument('--stages', nargs='+', choices=STAGES, default=STAGES)
    parser.add_argument('--arms', nargs='+', choices=ARMS, default=tuple(ARMS))
    args = parser.parse_args(argv)
    if args.action == 'prepare':
        require(args.source is not None and args.config is not None, 'prepare requires --source and --config')
        prepare(args.source, args.root, read(args.config))
        result = summarize(args.root)
        print(json.dumps({'status': 'prepared', 'cells': len(result['cells']), 'requests': 0}))
    elif args.action == 'verify':
        result = verify(args.root)
        print(json.dumps({'status': 'verified', 'cells': len(result['cells'])}))
    elif args.action == 'summarize':
        result = summarize(args.root)
        print(json.dumps({'status': result['status'], 'report': str(args.root/'reports/REPORT.md')}))
    else:
        results = run(args.root, resume=args.action == 'resume', rounds=args.rounds, stages=args.stages, arms=args.arms)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        if any(r['status'] != 'valid' for r in results):
            raise SystemExit(1)


if __name__ == '__main__':
    main()
