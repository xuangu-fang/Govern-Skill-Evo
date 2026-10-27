"""Run one request per round against the frozen obvious-fact screen."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.methods.v23_5.verifier_fact_screen_001 import prepare as contract
from experiments.methods.v23_5.verifier_input_001 import run_verifier as common

io = contract.io
OUT = ROOT/'artifacts/methods/v23_5/verifier_fact_screen_run_001'


def prepare(output):
    io.require(not output.exists(), 'Run directory already exists')
    contract.verify(contract.DEFAULT_OUTPUT)
    configs = [io.read(io.DEFAULT_OUTPUT/'cases'/name/'frozen/replay/run.json')['call_config']
               for name in io.ROUNDS]
    io.require(all(cfg == configs[0] for cfg in configs), 'Source configurations differ')
    output.mkdir(parents=True)
    (output/'reference_review.json').write_bytes((contract.DEFAULT_OUTPUT/'reference_review.json').read_bytes())
    (output/'run_verifier.py').write_bytes(Path(__file__).read_bytes())
    protocol = {'created_at': common.now(), 'policy_version': contract.VERSION,
                'contract_root': str(contract.DEFAULT_OUTPUT),
                'contract_manifest_sha256': io.digest(contract.DEFAULT_OUTPUT/'manifest.json'),
                'reference_sha256': io.digest(output/'reference_review.json'),
                'runner_sha256': io.digest(__file__), 'common_runner_sha256': io.digest(common.__file__),
                'call_config': configs[0], 'rounds': list(io.ROUNDS), 'max_transport_attempts': 1,
                'content_retries': 0, 'human_reviewed': False, 'prior_outputs_seen': True,
                'scope': 'Exactly one attempt per round. No automatic transport, length, schema or semantic retries. No Repair, Actor or Memory writes.',
                'scoring': 'Report valid coverage first. Score primary targets only; list both review_only targets separately. Check required findings by content, not only CONFLICT labels. Include failed-call usage; unknown usage is not zero.'}
    io.save(output/'protocol.json', protocol)
    return protocol


def check_frozen(output):
    p = io.read(output/'protocol.json')
    contract.verify(Path(p['contract_root']))
    io.require(p['policy_version'] == contract.VERSION, 'Policy changed')
    io.require(io.digest(Path(p['contract_root'])/'manifest.json') == p['contract_manifest_sha256'], 'Contract changed')
    io.require(io.digest(output/'reference_review.json') == p['reference_sha256'] ==
               io.digest(Path(p['contract_root'])/'reference_review.json'), 'Reference changed')
    io.require(io.digest(output/'run_verifier.py') == p['runner_sha256'] == io.digest(__file__), 'Runner changed')
    io.require(io.digest(common.__file__) == p['common_runner_sha256'], 'Shared runner changed')
    io.require(p['rounds'] == list(io.ROUNDS) and p['max_transport_attempts'] == 1 and p['content_retries'] == 0,
               'Single-attempt protocol changed')
    return p


def run(output):
    p = check_frozen(output)
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env', override=False)
    cfg = p['call_config']
    base = cfg['endpoint'].removesuffix('/chat/completions')
    io.require(os.environ.get('OPENAI_BASE_URL', '').rstrip('/') == base, 'Endpoint differs from frozen config')
    generate = common.grouping.live_generator(base_url=base, key=os.environ.get('OPENAI_API_KEY'),
               model=cfg['model'], max_tokens=cfg['max_tokens'], timeout=cfg['timeout_seconds'])
    io.require(generate.call_config == cfg, 'Call configuration differs')
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(common.run_round, output, p, name, generate) for name in p['rounds']]
        rows = [f.result() for f in futures]
    check_frozen(output)
    result = {'rounds': rows, 'elapsed_seconds_this_invocation': round(time.monotonic()-started, 3),
              'frozen_inputs_and_reference_unchanged': True, 'repair_calls': 0, 'actor_calls': 0, 'memory_commits': 0}
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
