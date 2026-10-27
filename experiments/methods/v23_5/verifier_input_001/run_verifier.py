"""Frozen three-round Verifier experiment; no Replay, Repair, Actor or Memory writes."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.methods.v23_5.verifier_input_001 import verifier as v
from src.skill_evolution.v23 import grouping

OUT = ROOT/'artifacts/methods/v23_5/verifier_run_001'
REFERENCE = Path(__file__).with_name('results')/'reference_review.json'


def now():
    return datetime.now(timezone.utc).isoformat()


def prepare(output):
    v.inputs.require(not output.exists(), 'Run directory already exists')
    v.verify_messages(v.DEFAULT_OUTPUT)
    review = v.inputs.read(REFERENCE)
    v.inputs.require(review['blind_to_live_verifier_outputs'] and len(review['items']) == 18, 'Missing pre-run reference')
    configs = [v.inputs.read(v.inputs.DEFAULT_OUTPUT/'cases'/r/'frozen/replay/run.json')['call_config']
               for r in v.inputs.ROUNDS]
    v.inputs.require(all(c == configs[0] for c in configs), 'Source model configurations differ')
    output.mkdir(parents=True)
    (output/'reference_review.json').write_bytes(REFERENCE.read_bytes())
    (output/'run_verifier.py').write_bytes(Path(__file__).read_bytes())
    protocol = {'created_at': now(), 'contract_root': str(v.DEFAULT_OUTPUT),
                'contract_manifest_sha256': v.inputs.digest(v.DEFAULT_OUTPUT/'manifest.json'),
                'reference_sha256': v.inputs.digest(output/'reference_review.json'),
                'runner_sha256': v.inputs.digest(output/'run_verifier.py'),
                'call_config': configs[0], 'rounds': list(v.inputs.ROUNDS),
                'max_transport_attempts': 3, 'content_retries': 0,
                'scope': 'One completed response per round; retry only HTTP 401/408/429/5xx or transport errors. No semantic, schema, or length retry. No Repair.',
                'human_reviewed': False}
    v.inputs.save(output/'protocol.json', protocol)
    return protocol


def check_frozen(output):
    p = v.inputs.read(output/'protocol.json')
    v.verify_messages(Path(p['contract_root']))
    v.inputs.require(v.inputs.digest(Path(p['contract_root'])/'manifest.json') == p['contract_manifest_sha256'], 'Contract changed')
    v.inputs.require(v.inputs.digest(output/'reference_review.json') == p['reference_sha256'] == v.inputs.digest(REFERENCE), 'Pre-run review changed')
    v.inputs.require(v.inputs.digest(output/'run_verifier.py') == p['runner_sha256'] == v.inputs.digest(__file__), 'Runner changed')
    return p


def retryable(directory, exc):
    if isinstance(exc, v.OutputValidationError):
        return False
    status = directory/'http_status.json'
    if status.exists():
        code = v.inputs.read(status)['status_code']
        return code in (401, 408, 429) or 500 <= code < 600
    import requests
    return isinstance(exc, requests.RequestException)


def finish(directory, response, model_input):
    v.inputs.save(directory/'response.json', response)
    (directory/'raw_output.txt').write_text(response.get('content') or '', encoding='utf-8')
    result = v.validate_response(response, model_input)
    v.inputs.save(directory/'verifier_output.json', result)
    v.inputs.save(directory/'validation.json', {'valid': True, 'semantic_truth_verified': False})
    return result


def run_round(output, protocol, name, generate):
    source = Path(protocol['contract_root'])/'cases'/name
    messages, model_input = v.inputs.read(source/'messages.json'), v.inputs.read(source/'verifier_input.json')
    for attempt in range(1, protocol['max_transport_attempts'] + 1):
        directory = output/'runs'/name/'attempts'/f'{attempt:03}'
        if directory.exists():
            v.inputs.require(v.inputs.read(directory/'messages.json') == messages, 'Saved request differs')
            old = v.inputs.read(directory/'run.json')
            if old['status'] == 'valid':
                result = v.validate_response(v.inputs.read(directory/'response.json'), model_input)
                v.inputs.require(result == v.inputs.read(directory/'verifier_output.json'), 'Saved output differs')
                return {'round': name, 'status': 'valid', 'attempt': attempt}
            if old['status'] == 'failed':
                if old['retryable']:
                    continue
                return {'round': name, 'status': 'failed', 'attempt': attempt}
            # Never silently duplicate a request whose outcome is unknown.
            return {'round': name, 'status': 'interrupted_unknown', 'attempt': attempt}
        directory.mkdir(parents=True)
        v.inputs.save(directory/'messages.json', messages)
        meta = {'round': name, 'attempt': attempt, 'started_at': now(), 'status': 'requesting',
                'call_config': protocol['call_config'], 'reference_sha256': protocol['reference_sha256'],
                'messages_sha256': v.inputs.digest(source/'messages.json')}
        v.inputs.save(directory/'run.json', meta)
        start = time.monotonic()
        try:
            response = generate(messages, directory)
            finish(directory, response, model_input)
            meta.update(status='valid', retryable=False)
        except Exception as exc:
            again = retryable(directory, exc)
            meta.update(status='failed', retryable=again, error_type=type(exc).__name__)
            v.inputs.save(directory/'validation.json', {'valid': False, 'error_type': type(exc).__name__,
                         'error': str(exc) if isinstance(exc, ValueError) else 'Transport error; inspect archived HTTP records.',
                         'retryable': again})
        finally:
            meta.update(finished_at=now(), elapsed_seconds=round(time.monotonic()-start, 3))
            v.inputs.save(directory/'run.json', meta)
        if meta['status'] == 'valid' or not meta['retryable']:
            return {'round': name, 'status': meta['status'], 'attempt': attempt}
        time.sleep(2)
    return {'round': name, 'status': 'failed', 'attempt': protocol['max_transport_attempts']}


def run(output):
    protocol = check_frozen(output)
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env', override=False)
    cfg = protocol['call_config']
    base = cfg['endpoint'].removesuffix('/chat/completions')
    v.inputs.require(os.environ.get('OPENAI_BASE_URL', '').rstrip('/') == base, 'Endpoint differs from frozen source config')
    generate = grouping.live_generator(base_url=base, key=os.environ.get('OPENAI_API_KEY'),
                                      model=cfg['model'], max_tokens=cfg['max_tokens'], timeout=cfg['timeout_seconds'])
    v.inputs.require(generate.call_config == cfg, 'Call configuration differs')
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(run_round, output, protocol, name, generate) for name in protocol['rounds']]
        rows = [future.result() for future in futures]
    check_frozen(output)
    result = {'rounds': rows, 'elapsed_seconds_this_invocation': round(time.monotonic()-started, 3),
              'frozen_inputs_and_reference_unchanged': True, 'actor_calls': 0, 'repair_calls': 0, 'memory_commits': 0}
    v.inputs.save(output/'run_summary.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'run', 'verify'))
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.output)
        result = {'prepared': True, 'model_calls': 0, 'reference_frozen_before_calls': True}
    elif args.command == 'verify':
        check_frozen(args.output)
        result = {'valid': True}
    else:
        result = run(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
