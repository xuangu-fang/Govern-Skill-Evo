#!/usr/bin/env python3
"""Run/resume only the first V26 iteration; never start R02 or test evaluation."""
import argparse
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.skill_evolution.v26 import evolution as ev
from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26.benchmarks.officeqa.adapter import OfficeQAEvidenceAdapter
from src.skill_evolution.v26.training import load_dataset
from src.skill_evolution.v26.transport import HTTPGenerator
from src.adapters.officeqa.runtime import Runtime
from src.adapters.officeqa.transport import ChatTransport


def read_credentials(path):
    # No shell evaluation, environment dumps or credential persistence.
    result = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        key, value = line.removeprefix('export ').split('=', 1)
        result[key.strip()] = value.strip().strip('\"\'')
    ev.require(bool(result.get('OPENAI_API_KEY')), 'Missing OPENAI_API_KEY in the selected env file')
    return result


def run_pilot(directory, *, config=None, generate=None, resume=False):
    root = Path(directory).resolve(); root.mkdir(parents=True, exist_ok=True)
    with (root/'.pilot.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if config is not None:
            ev.require(not (root/'state.json').exists(), 'Existing pilot requires explicit resume')
            ev.initialize(root, config)
        else:
            ev.require(resume, 'Existing pilot requires explicit resume')
        cfg = ev.read(root/'config.json')
        ev.freeze(root/'pilot_scope.json', {'stop_after_round': 1, 'tasks': cfg['batches'][0],
            'test_enabled': False, 'output_limits': 'temporary_pilot_limits_not_formal_budget'})
        ev.freeze_text(root/'pilot_entrypoint.py', Path(__file__).read_text())
        state = ev.read(root/'state.json')
        ev.require(state['next_round'] in (1, 2), 'Pilot advanced beyond first iteration')
        if state['next_round'] == 1:
            ev.run_round(root, generate=generate, resume=resume)
        with ev._lock(root):
            ev._check_contract(root)
            ev._audit_published(root, ev._config(root))  # Audit completed rounds only; no generation.
        ev.require(not (root/'rounds/R02').exists(), 'Unexpected second iteration')
        result = ev.read(root/'rounds/R01/result.json')
        summary = {'status': 'pilot_complete', 'rounds_completed': 1, 'next_round_started': False,
            'tasks': cfg['batches'][0], 'outcome': result['outcome'], 'cost': ev.cost_summary(root), 'at': ev.now()}
        ev.save(root/'pilot_summary.json', summary)
        return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory'); parser.add_argument('--config')
    parser.add_argument('--env-file', default=str(ROOT/'.env'))
    release = ROOT / 'data/officeqa/releases/763a8366abf2a3605c381d53586d844dc60fa756'
    parser.add_argument('--prepared-root', default=str(release / 'prepared'))
    parser.add_argument('--parsed-root', default=str(release / 'upstream/treasury_bulletins_parsed'))
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    ev.require(bool(args.config) != args.resume, 'Supply --config for a new pilot or --resume for existing work')
    cfg = ev.read(args.config or Path(args.directory)/'config.json'); actor = cfg['actor']
    credentials = read_credentials(args.env_file)
    ev.require(actor['endpoint'] == credentials['OPENAI_BASE_URL'].rstrip('/')+'/chat/completions',
               'Actor endpoint differs from selected env file')
    ev.require(all(c['endpoint'] == actor['endpoint'] for c in cfg['module_calls'].values()),
               'Method endpoint differs from selected env file')
    transport = ChatTransport(endpoint=actor['endpoint'], api_key=credentials['OPENAI_API_KEY'],
        **{k: actor[k] for k in ('model', 'max_completion_tokens', 'temperature', 'reasoning_effort',
                               'reasoning_mode', 'token_limit_field')})
    adapter = OfficeQAEvidenceAdapter(load_dataset(args.prepared_root, cfg.get('optimization_pool')),
        Runtime(args.parsed_root), transport, gate_metric=cfg['gate_metric'])
    with using_benchmark(adapter):
        result = run_pilot(args.directory, config=None if args.resume else cfg,
                          generate=HTTPGenerator(credentials['OPENAI_API_KEY']), resume=args.resume)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
