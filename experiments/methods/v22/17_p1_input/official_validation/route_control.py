"""Endpoint-policy amendment; immutable original inputs, one request per probe."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'validation'))
import control as c

ORIGINAL = c.ROOT
OUT = ORIGINAL.parent / 'official_validation'
ROUTING = c.REPO / 'experiments/methods/v22/18_endpoint_model_routing/revision/src/skill_evolution/v22/model_routing.py'
spec = importlib.util.spec_from_file_location('frozen_endpoint_routing', ROUTING)
routing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routing)


def current_route():
    c.load_dotenv(c.REPO / '.env', override=False)
    return routing.evolution_route(os.environ.get('OPENAI_BASE_URL', ''), 'deepseek-v4-pro')


def prepare():
    c.ROOT = ORIGINAL
    c.verify()
    assert not list((ORIGINAL / 'cases').glob('*/attempt.lock'))
    route = current_route()
    assert route['base_url'].removesuffix('/v1') == 'https://api.deepseek.com'
    assert route['evolution'] == 'deepseek-v4.1-flash'
    OUT.mkdir(exist_ok=False)
    protocol = deepcopy(c.read(ORIGINAL / 'protocol.json'))
    for case in protocol['cases']:
        source = ORIGINAL / 'cases' / case['id']
        dest = OUT / 'cases' / case['id']
        dest.mkdir(parents=True)
        for path in source.iterdir():
            assert path.is_file()
            shutil.copyfile(path, dest / path.name)
        case['parameters']['model'] = route['evolution']
        request = c.read(source / 'request.json')
        request['model'] = route['evolution']
        (dest / 'request.json').write_text(json.dumps(request, ensure_ascii=False, indent=2) + '\n')
    protocol.update(model=route['evolution'], endpoint_route=route,
        endpoint_policy='2026-10-16 user rule: internal proxy -> deepseek-v4-pro; official -> deepseek-v4.1-flash. Freeze resolved endpoint/model before dispatch; no automatic fallback.',
        amendment='Only request model and authorized endpoint change. Same eight facts, messages, criteria, budgets, validators, and one-attempt failure policy.')
    c.save(OUT / 'protocol.json', protocol)
    for name in ('source_manifest.json', 'baseline_fixture_audit.json'):
        shutil.copyfile(ORIGINAL / name, OUT / name)
    c.save(OUT / 'amendment.json', {
        'created_at': c.timestamp(), 'user_authorized': True,
        'original_freeze': str((ORIGINAL / 'freeze.json').relative_to(c.REPO)),
        'original_freeze_sha256': c.digest((ORIGINAL / 'freeze.json').read_bytes()),
        'original_stop': 'Endpoint assertion before HTTP dispatch; original process.log retained.',
        'original_http_attempts': 0, 'original_tokens': 0, 'original_cost': 0,
        'route': route, 'new_max_http_attempts': 8, 'episodes': 0,
        'unchanged': ['messages', 'payloads', 'criteria', 'algorithm', 'output_schema', 'temperature', 'thinking', 'reasoning_effort', 'max_tokens', 'timeout', 'concurrency', 'failure_policy'],
        'no_official_publication': True,
    })
    c.ROOT = OUT
    for case in protocol['cases']:
        d = OUT / 'cases' / case['id']
        assert c.messages_for(case) == c.read(d / 'messages.json')
        assert c.read(d / 'request.json') == dict(case['parameters'], messages=c.read(d / 'messages.json'))
        for name in ('payload.json', 'messages.json', 'criteria.json'):
            assert (d / name).read_bytes() == (ORIGINAL / 'cases' / case['id'] / name).read_bytes()
    files = [p for top in (OUT, ORIGINAL, c.REVISION, HERE, HERE.parent / 'validation')
             for p in top.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [ROUTING]
    files += list((OUT.parent / 'offline').glob('*.json')) + list((OUT.parent / 'offline').glob('*.log'))
    manifest = {str(p.relative_to(c.REPO)): c.digest(p.read_bytes()) for p in sorted(set(files))}
    c.save(OUT / 'freeze.json', {'frozen_at': c.timestamp(), 'files': manifest,
        'manifest_sha256': c.object_digest(manifest), 'original_files_verified': c.check_originals(),
        'cases': 8, 'max_calls': 8, 'max_http_attempts': 8, 'max_concurrent_requests': 2,
        'new_environment_episodes': 0, 'publication': False, 'endpoint_route': route})
    print(json.dumps({'frozen_files': len(manifest), 'route': route, 'calls': 0}), flush=True)


def checked_route():
    c.ROOT = OUT
    c.verify()
    protocol = c.read(OUT / 'protocol.json')
    route = current_route()
    assert route == protocol['endpoint_route'], 'Endpoint/model changed after freeze'
    assert len(protocol['cases']) == 8
    assert all(case['parameters']['model'] == route['evolution'] for case in protocol['cases'])
    return route, protocol


def run():
    route, protocol = checked_route()
    assert not list((OUT / 'cases').glob('*/attempt.lock')), 'No resampling'
    key = os.environ.get('OPENAI_API_KEY')
    assert key, 'Missing API key'
    c.save(OUT / 'execution_claim.json', {'started_at': c.timestamp(), 'pid': os.getpid(),
        'maximum_attempts': 8, 'route': route})
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(c.run_one, case, route['base_url'] + '/chat/completions', key)
                for case in protocol['cases']]
        results = [job.result() for job in jobs]
    c.save(OUT / 'run_summary.json', {'completed_at': c.timestamp(), 'results': results,
        'total_attempts': sum(x['attempts'] for x in results), 'environment_episodes': 0,
        'publication': False, 'original_files_verified': c.verify(), 'route': route})


if __name__ == '__main__':
    {'prepare': prepare, 'verify': lambda: print(checked_route()[0]), 'run': run}[sys.argv[1]]()
