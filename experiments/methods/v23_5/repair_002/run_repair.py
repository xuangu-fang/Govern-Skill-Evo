"""One Repair request per frozen round; no retries, Actor or Memory commits."""
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
from experiments.methods.v23_5.repair_002 import prepare as contract
from src.skill_evolution.v23 import grouping

io, repair = contract.io, contract.repair
OUT = ROOT/'artifacts/methods/v23_5/repair_run_001'
HERE = Path(__file__).parent


def now():
    return datetime.now(timezone.utc).isoformat()


def prepare(output):
    io.require(not output.exists(), 'Run directory already exists')
    contract.verify(contract.OUTPUT)
    previous = io.read(contract.LIVE/'protocol.json')
    output.mkdir(parents=True)
    for name in ('run_repair.py', 'LIVE_PROTOCOL.md'):
        (output/name).write_bytes((HERE/name).read_bytes())
    protocol = {'created_at': now(), 'version': contract.VERSION,
                'contract_root': str(contract.OUTPUT),
                'contract_manifest_sha256': io.digest(contract.OUTPUT/'manifest.json'),
                'previous_protocol_sha256': io.digest(contract.LIVE/'protocol.json'),
                'runner_sha256': io.digest(__file__), 'transport_sha256': io.digest(grouping.__file__),
                'review_protocol_sha256': io.digest(output/'LIVE_PROTOCOL.md'),
                'call_config': previous['call_config'], 'rounds': list(io.ROUNDS),
                'max_attempts_per_round': 1, 'content_retries': 0, 'semantic_verifier_calls': 0,
                'memory_commits': 0, 'actor_calls': 0, 'human_reviewed': False}
    io.save(output/'protocol.json', protocol)
    return protocol


def check_frozen(output):
    p = io.read(output/'protocol.json')
    contract.verify(Path(p['contract_root']))
    io.require(p['version'] == contract.VERSION and p['rounds'] == list(io.ROUNDS), 'Run scope changed')
    io.require(io.digest(Path(p['contract_root'])/'manifest.json') == p['contract_manifest_sha256'], 'Contract changed')
    io.require(io.digest(contract.LIVE/'protocol.json') == p['previous_protocol_sha256'], 'Previous protocol changed')
    io.require(p['call_config'] == io.read(contract.LIVE/'protocol.json')['call_config'], 'Call config changed')
    io.require(io.digest(output/'run_repair.py') == p['runner_sha256'] == io.digest(__file__), 'Runner changed')
    io.require(io.digest(grouping.__file__) == p['transport_sha256'], 'Transport changed')
    io.require(io.digest(output/'LIVE_PROTOCOL.md') == p['review_protocol_sha256'] == io.digest(HERE/'LIVE_PROTOCOL.md'),
               'Review protocol changed')
    io.require(p['max_attempts_per_round'] == 1 and p['content_retries'] == 0, 'Single-call protocol changed')
    return p


def checked_result(response, value, candidate, payload):
    result = repair.validate_response(response, value)
    return result, repair.merge(result, value, candidate, payload)


def run_round(output, protocol, name, generate):
    source = Path(protocol['contract_root'])/'cases'/name
    messages = io.read(source/'messages.json')
    value, candidate = io.read(source/'repair_input.json'), io.read(source/'candidate.json')
    _, _, _, payload = contract.load_case(name)
    directory = output/'runs'/name/'attempts/001'
    if directory.exists():
        io.require(io.read(directory/'messages.json') == messages, 'Saved request differs')
        old = io.read(directory/'run.json')
        if old['status'] == 'valid':
            result, merged = checked_result(io.read(directory/'response.json'), value, candidate, payload)
            io.require(result == io.read(directory/'repair_output.json') and
                       merged == io.read(directory/'merged_candidate.json'), 'Saved output differs')
        # Failed or unknown outcomes are never resubmitted automatically.
        return {'round': name, 'status': old['status'] if old['status'] in ('valid', 'failed') else 'interrupted_unknown',
                'attempt': 1, 'reused': True}
    directory.mkdir(parents=True)
    io.save(directory/'messages.json', messages)
    meta = {'round': name, 'attempt': 1, 'started_at': now(), 'status': 'requesting',
            'call_config': protocol['call_config'], 'messages_sha256': io.digest(source/'messages.json')}
    io.save(directory/'run.json', meta)
    started = time.monotonic()
    try:
        response = generate(messages, directory)
        io.save(directory/'response.json', response)
        (directory/'raw_output.txt').write_text(response.get('content') or '', encoding='utf-8')
        result, merged = checked_result(response, value, candidate, payload)
        io.save(directory/'repair_output.json', result)
        io.save(directory/'merged_candidate.json', merged)
        io.save(directory/'validation.json', {'valid': True, 'semantic_truth_verified': False, 'memory_commits': 0})
        meta['status'] = 'valid'
    except Exception as exc:
        meta.update(status='failed', error_type=type(exc).__name__)
        io.save(directory/'validation.json', {'valid': False, 'error_type': type(exc).__name__,
                'error': str(exc) if isinstance(exc, ValueError) else 'Call failed; inspect archived HTTP records.',
                'retryable': False, 'memory_commits': 0})
    finally:
        meta.update(finished_at=now(), elapsed_seconds=round(time.monotonic()-started, 3))
        io.save(directory/'run.json', meta)
    return {'round': name, 'status': meta['status'], 'attempt': 1, 'reused': False}


def run(output):
    p = check_frozen(output)
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env', override=False)
    cfg = p['call_config']
    base = cfg['endpoint'].removesuffix('/chat/completions')
    io.require(os.environ.get('OPENAI_BASE_URL', '').rstrip('/') == base, 'Endpoint differs from frozen config')
    generate = grouping.live_generator(base_url=base, key=os.environ.get('OPENAI_API_KEY'),
               model=cfg['model'], max_tokens=cfg['max_tokens'], timeout=cfg['timeout_seconds'])
    io.require(generate.call_config == cfg, 'Generator config differs')
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(run_round, output, p, name, generate) for name in p['rounds']]
        rows = [f.result() for f in futures]
    check_frozen(output)
    result = {'rounds': rows, 'elapsed_seconds_this_invocation': round(time.monotonic()-started, 3),
              'frozen_sources_unchanged': True, 'actor_calls': 0, 'memory_commits': 0,
              'second_semantic_verifier_calls': 0}
    io.save(output/'run_summary.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'run', 'verify'))
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.output.resolve())
        result = {'prepared': True, 'model_calls': 0}
    elif args.command == 'verify':
        check_frozen(args.output.resolve())
        result = {'valid': True}
    else:
        result = run(args.output.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
