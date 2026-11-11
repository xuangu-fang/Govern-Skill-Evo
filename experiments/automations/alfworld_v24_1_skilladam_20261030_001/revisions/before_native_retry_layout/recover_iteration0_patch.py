"""One explicitly authorized patch-call recovery, then unchanged native training.

No flags: reconstruct the interrupted call offline and stop before generation.
--start: spend at most the durable three-request grant, then continue the loop.
"""
import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / 'scripts/runs'), str(ROOT / 'external/SkillAdam'), str(ROOT)]
import run_skilladam_alfworld_official_models as native
from alfworld_aligned_common import read, require, sha, validate_trajectory

GRANT = 'skilladam.train.iteration_0.iteration_patch.89df679521f2d6dfc7f1d5775c925c204efb340b6ff68e2bc294699c6035c01f'


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class Reconstructed(Exception):
    pass


class GrantExhausted(RuntimeError):
    pass


def consume(ledger_path, grant_id, attempt_dir, request):
    """Called by the HTTP send hook, before transport gets the request."""
    ledger = read(ledger_path)
    grant = ledger['grants'][grant_id]
    require(grant['status'] not in ('succeeded', 'exhausted', 'blocked'), 'Grant is terminal')
    if grant['consumed'] >= grant['limit']:
        raise GrantExhausted('Three additional physical requests already consumed')
    grant['consumed'] += 1
    ledger['extra_requests_consumed'] += 1
    grant['requests'].append({'number': grant['consumed'], 'at': now(),
                              'evidence': str(attempt_dir), 'status': 'dispatching'})
    grant['status'] = 'recovering'
    save(ledger_path, ledger)
    save(attempt_dir / 'request.json', request)


def recover(signature, cfg, auth, *, ledger_path=None, recovery_root=None, client_factory=None):
    """Keep the exact native payload and parser; never change a model response."""
    import httpx
    from openai import OpenAI, DefaultHttpxClient, APIStatusError, APIConnectionError, APITimeoutError
    from skilladam.backends.openai_compatible import _generation_result
    from skilladam.execution.backend import BackendProtocolError
    from skilladam.usage import normalize_usage
    ledger_path = ledger_path or HERE / 'recovery_ledger.json'
    recovery_root = recovery_root or HERE / 'recovery_iteration0_patch'
    original = ROOT / auth['failed_call_directory']
    require(signature == read(original / 'request.json'), 'Recovered request differs')
    grant = read(ledger_path)['grants'][GRANT]
    require(grant['limit'] == 3 and grant['consumed'] == 0 and grant['status'] == 'authorized',
            'Recovery already attempted; inspect evidence, never reset automatically')
    usage = [normalize_usage(read(original / 'response.json').get('usage'), requests=1)]
    expected_body = read(original / 'http_request_01.json')['body']
    t = cfg['optimizer_transport']
    for number in range(1, 4):
        attempt = recovery_root / f'attempt_{number:02d}'
        require(not attempt.exists(), 'Existing recovery attempt requires explicit reconciliation')
        sent_count = 0

        def sent(request):
            nonlocal sent_count
            require(sent_count == 0, 'More than one HTTP request in an SDK invocation')
            body = json.loads(request.content)
            require(str(request.url) == 'https://api.deepseek.com/chat/completions' and body == expected_body,
                    'Recovery endpoint or physical request body differs')
            consume(ledger_path, GRANT, attempt, {'url': str(request.url), 'body': body})
            sent_count += 1

        def received(response):
            save(attempt / 'http_response.json', {'status_code': response.status_code})

        options = dict(api_key=os.environ['OPENAI_API_KEY'], base_url='https://api.deepseek.com',
                       max_retries=0, timeout=httpx.Timeout(t['timeout_seconds'], connect=t['connect_timeout_seconds']),
                       http_client=DefaultHttpxClient(event_hooks={'request': [sent], 'response': [received]}))
        client = (client_factory or OpenAI)(**options)
        raw = None
        error = None
        retryable = False
        try:
            response = client.chat.completions.create(**signature['payload'])
            raw = response.model_dump(mode='json')
            save(attempt / 'response.json', raw)
            usage.append(normalize_usage(raw.get('usage'), requests=1))
            result = _generation_result(raw)
        except Exception as exc:
            error = type(exc).__name__
            retryable = (isinstance(exc, (APIConnectionError, APITimeoutError, BackendProtocolError)) or
                         isinstance(exc, APIStatusError) and (exc.status_code in (408, 409, 429) or exc.status_code >= 500))
            save(attempt / 'error.json', {'error_type': error, 'retryable': retryable})
            if isinstance(exc, APIStatusError):
                save(attempt / 'error_response.json', {'status_code': exc.status_code,
                     'body': exc.response.text})
            if raw is None and sent_count:
                usage.append(normalize_usage(None, requests=1))
        finally:
            client.close()
        ledger = read(ledger_path)
        grant = ledger['grants'][GRANT]
        if sent_count:
            grant['requests'][-1]['status'] = 'failed' if error else 'succeeded'
        if not error:
            save(recovery_root / 'success.json', {'signature': signature, 'response': raw,
                 'usage': [asdict(u) for u in usage], 'original_response_preserved': True})
            grant.update(status='succeeded', finished_at=now())
            save(ledger_path, ledger)
            return replace(result, usage=tuple(usage))
        if not retryable or number == 3:
            grant.update(status='exhausted' if retryable else 'blocked', finished_at=now())
            save(ledger_path, ledger)
            raise GrantExhausted('Recovery stopped: ' + error)
        save(ledger_path, ledger)
    raise AssertionError('unreachable')


def reconstruct_and_continue(plan, auth, *, start=False):
    from skilladam.backends.openai_compatible import _generation_payload
    import skilladam.methods.skilladam as method
    job = plan['jobs']['skilladam']
    experiment, output = ROOT / job['experiment'], ROOT / job['training_output']
    cfg, actor = read(experiment / 'skilladam.json'), read(experiment / 'actor.json')
    bridge = native.bridge_module()
    bridge.EXPERIMENT = experiment
    expected = read(ROOT / auth['failed_call_directory'] / 'request.json')
    require(not (output / 'checkpoint.json').exists(), 'This wrapper is only for the pre-checkpoint failure')
    require(read(output.with_suffix('.launch.json')) == {'manifest_sha256': sha(experiment / 'manifest.json'), 'config': cfg},
            'Original launch signature differs')
    base = native.backend_type(bridge)

    class Backend(base):
        reached = False

        def generate(self, request):
            if not self.reached:
                payload = _generation_payload(request, native.transport_settings(self.cfg))
                payload.update(extra_body={'thinking': self.cfg['optimizer_transport']['thinking']}, stream=False)
                signature = {'iteration': self.iteration, 'stage': request.stage, 'payload': payload}
                require(signature == expected, 'Reconstructed logical call differs from saved failure')
                if not start:
                    raise Reconstructed()
                self.reached = True
                return recover(signature, cfg, auth)
            return super().generate(request)

        def execute_batch(self, execution):
            require(self.reached and start, 'Actor work is forbidden before the recovered call succeeds')
            return super().execute_batch(execution)

    backend = Backend(actor, cfg, output)
    runner = bridge.AlignedRunner(config=bridge.native_config(cfg), adapter=bridge.ALFWorldAdapter(experiment / 'splits'),
        backend=backend, context=native.context_for(bridge, actor, cfg), output_dir=output)
    trajectories = runner._load_trajectories(0)
    require([str(t.case_id) for t in trajectories] == auth['training_case_ids'], 'Cached trajectory order differs')
    # Only the storage guard uses resume semantics: loop state starts at its
    # original iteration zero, with already completed trajectories preloaded.
    # No fake checkpoint, no rollout, compression, usage append, or model replay.
    original_store = method.RunStore
    method.RunStore = lambda root, resume=False: original_store(root, resume=True)
    try:
        return runner.run(cases=bridge.cases_for(cfg), initial_skill=(experiment / 'initial_skill.md').read_text(), resume=False)
    finally:
        method.RunStore = original_store


def verify(plan, auth):
    require(sha(HERE / 'plan.json') == auth['plan_sha256'], 'Frozen plan differs')
    for path, expected in {**plan['frozen_inputs_sha256'], **auth['original_artifacts_sha256'],
                           **auth['recovery_sources_sha256']}.items():
        require(sha(ROOT / path) == expected, 'Frozen recovery input differs: ' + path)
    experiment = ROOT / plan['jobs']['skilladam']['experiment']
    native.check(experiment)
    actor = read(experiment / 'actor.json')
    skill = (experiment / 'initial_skill.md').read_text()
    tasks = {t['id']: t for t in read(experiment / 'optimization_items.json')}
    root = ROOT / plan['jobs']['skilladam']['training_output']
    for task in auth['training_case_ids']:
        paths = list((root / 'shared_actor/iter_000/training_rollout_0/episodes' / task.replace(':', '_')).glob('*/trajectory.json'))
        require(len(paths) == 1, 'Expected exactly one completed Actor trajectory')
        validate_trajectory(paths[0], actor, tasks[task], skill)
    before = {str(f): sha(f) for f in root.rglob('*') if f.is_file()}
    try:
        reconstruct_and_continue(plan, auth)
    except Reconstructed:
        pass
    else:
        raise AssertionError('Offline reconstruction did not reach expected call')
    require(before == {str(f): sha(f) for f in root.rglob('*') if f.is_file()}, 'Offline reconstruction modified artifacts')
    return {'status': 'passed', 'same_request': True, 'completed_actors_reused': 10,
            'network_requests': 0, 'training_output_unchanged': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    plan, auth = read(HERE / 'plan.json'), read(HERE / 'patch_recovery_authorization.json')
    output = ROOT / plan['jobs']['skilladam']['training_output']
    with output.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        report = verify(plan, auth)
        save(HERE / 'patch_recovery_preflight.json', report)
        if not args.start:
            print(json.dumps(report)); return
        # Same credential policy as with_official_credentials.py, without
        # widening that frozen wrapper's command allowlist.
        from dotenv import dotenv_values
        official = dotenv_values(ROOT / plan['credential_source']['env_file'])
        require(official.get('OPENAI_BASE_URL', '').rstrip('/') == 'https://api.deepseek.com'
                and official.get('OPENAI_API_KEY'), 'Official repository credentials missing')
        os.environ.update(OPENAI_API_KEY=official['OPENAI_API_KEY'], OPENAI_BASE_URL='https://api.deepseek.com',
                          PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
        native.bridge_module().configure_runtime(read(ROOT / plan['jobs']['skilladam']['experiment'] / 'actor.json'))
        state_path = HERE / 'execution/skilladam.state.json'
        state = {'job': 'skilladam', 'status': 'running', 'pid': os.getpid(), 'started_at': now(),
                 'command': [sys.executable, str(Path(__file__).resolve()), '--start'],
                 'training_output': str(output), 'recovery_grant': GRANT}
        save(state_path, state)
        try:
            result = reconstruct_and_continue(plan, auth, start=True)
            save(output / 'completion.json', {'status': 'complete', 'automatic_test': False,
                 'iterations': [r.to_dict() for r in result.feedback_loop.iterations],
                 'resumed_from_iteration': result.feedback_loop.resumed_from_iteration,
                 'recovery_grant': GRANT})
        except BaseException as exc:
            state.update(status='process_exited', exit_code=1, error_type=type(exc).__name__, finished_at=now())
            save(state_path, state)
            raise
        state.update(status='process_exited', exit_code=0, finished_at=now())
        save(state_path, state)


if __name__ == '__main__':
    main()
