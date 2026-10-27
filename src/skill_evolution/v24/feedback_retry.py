"""Bounded stage retries with persisted, stage-local output validation feedback."""
import json
import time

import requests

from src.skill_evolution.v24.facts import require
from . import output_feedback as feedback


class RequestFailure(ValueError):
    """A failure explicitly identified at the API request/response boundary."""

    def __init__(self, detail, *, retryable=True, truncated=False):
        super().__init__(detail)
        self.retryable = retryable
        self.truncated = truncated


def request_failure(exc, path):
    """Do not infer transient failures merely from the presence of response files."""
    from . import evolution as ev
    if isinstance(exc, (requests.Timeout, requests.ConnectionError, requests.exceptions.ChunkedEncodingError)):
        return RequestFailure(type(exc).__name__)
    # requests' JSONDecodeError also inherits OSError; classify it at the
    # decoder boundary below rather than mistaking it for a local disk error.
    if isinstance(exc, OSError) and not isinstance(exc, requests.exceptions.JSONDecodeError):
        return None
    if (path/'http_status.json').exists():
        status = ev.read(path/'http_status.json')['status_code']
        if status >= 300:
            return RequestFailure(f'Model API returned HTTP {status}', retryable=ev._retryable(exc, path))
    # Malformed API envelopes are technical errors. Unknown generator exceptions,
    # including disk errors, must stop rather than issuing another model request.
    tb = exc.__traceback__
    while tb:
        code = tb.tb_frame.f_code
        if ((code.co_name == 'response_value' and code.co_filename == ev.grouping.response_value.__code__.co_filename)
                or (code.co_name == 'json' and code.co_filename == requests.Response.json.__code__.co_filename)):
            if isinstance(exc, (ValueError, KeyError, IndexError, TypeError)):
                return RequestFailure('Malformed API response envelope')
        tb = tb.tb_next
    return None


def run_stage(root, rd, name, invoke, config, generate, resume):
    # Import lazily: the legacy runner remains available for saved configurations.
    from . import evolution as ev
    stage = rd/name
    stage.mkdir(exist_ok=True)
    attempts = stage/'attempts'
    attempts.mkdir(exist_ok=True)
    marker = stage/'result.json'
    cfg = ev.stage_call_config(config, name)

    def invoke_checked(path, generator):
        ev._check_contract(root)
        return invoke(path, generator, cfg)

    def check_saved(path):
        require(ev.read(path/'run.json')['call_config'] == cfg, 'Saved call configuration differs')
        require(feedback.policy(feedback.saved_context(path)) == feedback.POLICY,
                'Saved retry policy differs')

    def selected(path, value):
        ev.save(marker, {'path': str(path.relative_to(stage))})
        return path, value

    def record_error(path, exc, *, called):
        try:
            response = ev.read(path/'response.json') if (path/'response.json').exists() else {}
        except (ValueError, OSError):
            response = {}
        if isinstance(exc, RequestFailure) and exc.truncated:
            kind = 'truncated'
        elif isinstance(exc, feedback.OutputValidationError):
            kind = 'output_validation'
        else:
            kind = 'technical'
        retryable = ((isinstance(exc, feedback.OutputValidationError) and
                      response.get('finish_reason') == 'stop') or
                     (isinstance(exc, RequestFailure) and exc.retryable))
        value = {'kind': kind, 'error_type': type(exc).__name__,
                 'error': str(exc)[:600] if isinstance(exc, ValueError) else type(exc).__name__,
                 'retryable': retryable, 'request_invoked': called, 'at': ev.now()}
        if kind == 'output_validation':
            value['diagnostic'] = exc.diagnostic
        ev.save(path/'error.json', value)
        return value

    def saved_response(path):
        if (path/'response.json').exists():
            response = ev.read(path/'response.json')
        elif (path/'http_response.txt').exists() and (path/'http_status.json').exists():
            if ev.read(path/'http_status.json')['status_code'] >= 300:
                return None
            response = ev.grouping.response_value(ev.read(path/'http_response.txt'))
            ev.save(path/'response.json', response)
        else:
            return None
        return response if response.get('finish_reason') == 'stop' else None

    def recover(path, response):
        # Explicit resume can finish an interrupted saved response without a new
        # request. Any local failure stops; there is no automatic disk/code retry.
        def cached(messages, dest):
            require(messages == ev.read(path/'messages.json'), 'Recovery messages differ')
            ev.save(dest/'recovered_from.json', {'path': str(path), 'additional_requests': 0})
            return response

        cached.request_context = context
        recovered = path/'recovered'
        number = 1
        while recovered.exists():
            meta = ev.read(recovered/'run.json') if (recovered/'run.json').exists() else {}
            if meta.get('status') == 'valid':
                check_saved(recovered)
                return selected(recovered, invoke_checked(recovered, None))
            number += 1
            recovered = path/f'recovered_{number:03}'
        return selected(recovered, invoke_checked(recovered, cached))

    if marker.exists():
        path = stage/ev.read(marker)['path']
        check_saved(path)
        # Reload failures are archive/program failures, not fresh model output.
        return path, invoke_checked(path, None)

    existing = sorted(p for p in attempts.iterdir() if p.is_dir())
    context = {'policy': feedback.POLICY, 'feedback_from': None}
    if existing:
        last = existing[-1]
        prior_error = ev.read(last/'error.json') if (last/'error.json').exists() else None
        if prior_error and not prior_error['retryable']:
            raise ev.Stopped(f'{name}: preserved non-retryable technical failure')
        context = feedback.saved_context(last)
        require(feedback.policy(context) == feedback.POLICY, 'Missing saved request context')
        meta = ev.read(last/'run.json') if (last/'run.json').exists() else {}
        if meta.get('status') == 'valid' or prior_error is None:
            if meta:
                check_saved(last)
            try:
                if meta.get('status') == 'valid':
                    return selected(last, invoke_checked(last, None))
                response = saved_response(last)
                if response is not None:
                    return recover(last, response)
                # An interrupted request without a saved response still consumes its slot.
                if prior_error is None:
                    prior_error = {'kind': 'technical', 'retryable': True,
                                   'error': 'Interrupted request; response unavailable', 'request_invoked': True}
                    ev.save(last/'error.json', prior_error)
            except ev.Stopped:
                raise
            except Exception as exc:
                prior_error = record_error(last, exc, called=False)
        require(resume, 'Prior attempts require explicit resume')
        if prior_error and not prior_error['retryable']:
            raise ev.Stopped(f'{name}: preserved non-retryable technical failure')
        if prior_error and prior_error['kind'] == 'output_validation':
            context = {'policy': feedback.POLICY, 'feedback_from': str(last.resolve())}

    # Directory slots persist across process restarts. Recovery uses no new slot.
    request_limit = config['max_attempts']
    for number in range(len(existing) + 1, request_limit + 1):
        path = attempts/f'{number:03}'
        called = False
        started = time.monotonic()

        def request(messages, dest):
            nonlocal called
            require(len(json.dumps(messages, ensure_ascii=False).encode('utf-8')) <= ev.message_byte_limit(config),
                    'Input exceeds frozen byte budget')
            if existing:
                previous = ev.read(existing[-1]/'messages.json')
                require(messages[:2] == previous[:2], 'Retry base input or Prompt changed')
                old_context = feedback.saved_context(existing[-1])
                if context == old_context:
                    require(messages == previous, 'Technical retry request changed')
            ev.save(dest/'request_started.json', {'at': ev.now()})
            called = True
            generator = generate if generate is not None else ev._generator({**config, 'call_config': cfg})
            try:
                response = generator(messages, dest)
            except Exception as exc:
                failure = request_failure(exc, dest)
                if failure is not None:
                    raise failure from exc
                raise
            if not isinstance(response, dict):
                raise RequestFailure('Malformed API response envelope')
            if response.get('finish_reason') != 'stop':
                ev.save(dest/'response.json', response)
                raise RequestFailure('Model response did not finish normally',
                                     truncated=response.get('finish_reason') == 'length')
            if not isinstance(response.get('content'), str):
                ev.save(dest/'response.json', response)
                raise RequestFailure('API response content must be a string')
            return response

        request.request_context = context
        try:
            value = invoke_checked(path, request)
            ev.save(path/'attempt.json', {'elapsed_seconds': time.monotonic()-started,
                                         'request_invoked': called, 'at': ev.now()})
            return selected(path, value)
        except Exception as exc:
            error = record_error(path, exc, called=called)
            if not error['retryable']:
                raise ev.Stopped(f'{name}: {error["error"]}') from exc
            if error['kind'] == 'output_validation':
                context = {'policy': feedback.POLICY, 'feedback_from': str(path.resolve())}
            # Technical errors and length stops retain the complete existing request.
            existing.append(path)
            if number < request_limit:
                time.sleep(config.get('retry_delay_seconds', 0) * number)
    raise ev.Stopped(f'{name}: frozen request budget exhausted; resume does not reset it')
