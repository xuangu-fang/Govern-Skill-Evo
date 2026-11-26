"""Journaled optimizer transport used only during OfficeQA SkillOpt training."""
from collections import Counter
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from functools import wraps
import inspect
import json
import os
from pathlib import Path
from unittest.mock import patch

from .execution import atomic_json as save
from .skillopt_budget import OptimizerBudget, TrainingPaused, digest, read

_scope = ContextVar('skillopt_call_scope', default=None)


@contextmanager
def slot(identity):
    token = _scope.set(identity)
    try:
        yield
    finally:
        _scope.reset(token)


def _bind_native_slots(stack, campaign):
    from skillopt.gradient import aggregate, reflect

    def analyst(fn, kind):
        @wraps(fn)
        def scoped(skill_content, items, prediction_dir, *args, **kwargs):
            location = os.path.relpath(prediction_dir, campaign)
            with slot([location, kind, [item['id'] for item in items]]):
                return fn(skill_content, items, prediction_dir, *args, **kwargs)
        return scoped

    for kind in ('error', 'success'):
        name = f'run_{kind}_analyst_minibatch'
        stack.enter_context(patch.object(reflect, name, analyst(getattr(reflect, name), kind)))

    native_merge = aggregate._merge_batch

    @wraps(native_merge)
    def group(skill_content, patches, system_prompt, update_mode, meta_skill_context='', level=1):
        # This runs inside the native worker. Input patches and group distinguish
        # parallel merges; restored skill/context text cannot reset their budgets.
        with slot(['group', digest(system_prompt), level, digest(patches)]):
            return native_merge(skill_content, patches, system_prompt, update_mode, meta_skill_context, level)

    stack.enter_context(patch.object(aggregate, '_merge_batch', group))

    # Native reflection initially returns patches in completion order, but reads
    # cached patches in filename order. Restore the original order for downstream
    # merge/ranking calls on resume, including duplicate and empty patches.
    native_reflect = reflect.run_minibatch_reflect

    @wraps(native_reflect)
    def ordered(*args, **kwargs):
        patches = native_reflect(*args, **kwargs)
        params = inspect.signature(native_reflect).bind(*args, **kwargs).arguments
        order = Path(params['patches_dir']).parent / 'optimizer_reflection_order.json'
        hashes = [digest(p) for p in patches]
        if order.exists():
            saved = read(order)
            if Counter(saved) != Counter(hashes):
                raise TrainingPaused(f'Reflection patches changed on resume: {order}')
            by_hash = dict(zip(hashes, patches))
            return [by_hash[key] for key in saved]
        save(order, hashes)
        return patches

    stack.enter_context(patch.object(reflect, 'run_minibatch_reflect', ordered))


@contextmanager
def configured_provider(campaign, *, http_transport=None):
    """Use the configured optimizer's model/limits, independent of Actor transport."""
    import httpx
    from skillopt.model import openai_compatible_backend as backend

    campaign = Path(campaign)
    config = backend.OPTIMIZER_CONFIG
    endpoint = config.base_url.rstrip('/') + '/chat/completions'
    extra = json.loads(os.environ.get('OPTIMIZER_OPENAI_COMPATIBLE_EXTRA_BODY') or '{}')
    base = {**extra, 'model': config.deployment}
    if config.temperature is not None:
        base['temperature'] = config.temperature
    with ExitStack() as stack:
        client = stack.enter_context(httpx.Client(
            follow_redirects=False, transport=http_transport, timeout=config.timeout_seconds,
            headers={'Authorization': 'Bearer ' + (config.api_key or 'dummy')},
        ))

        def send(folder, stem, messages, cap):
            body = dict(base, messages=messages, max_tokens=cap)
            # Reserve and persist the exact payload before a single HTTP send.
            with budget.guard:
                budget.check()
                save(folder / (stem + '_request.json'), {'url': endpoint, 'body': body})
            try:
                response = client.post(endpoint, json=body)
            except httpx.RequestError as exc:
                save(folder / (stem + '_outcome.json'), {'action': 'transport_error', 'error': type(exc).__name__})
                return
            try:
                data = response.json()
                usage = data.get('usage') if isinstance(data, dict) else None
            except ValueError:
                usage = None
            save(folder / (stem + '_response.json'), {'status': response.status_code, 'usage': usage})
            raw = folder / (stem + '_response_body.bin')
            tmp = raw.with_suffix('.tmp')
            tmp.write_bytes(response.content)
            tmp.replace(raw)

        budget = OptimizerBudget(campaign, send, backend.tracker.record)
        budget.recover()
        native = backend._chat_messages_impl

        def dispatch(messages, max_completion_tokens, retries, stage, **kwargs):
            if kwargs['role'] != 'optimizer':
                return native(messages, max_completion_tokens, retries, stage, **kwargs)
            try:
                state = campaign / 'runtime_state.json'
                completed = read(state)['last_completed_step'] if state.exists() else 0
                identity = [completed, _scope.get()]
                return budget.generate(identity, stage, messages, min(max_completion_tokens, config.max_tokens))
            except Exception as exc:
                raise TrainingPaused(f'Optimizer {stage} journal or contract error: {exc}') from exc

        _bind_native_slots(stack, campaign)
        stack.enter_context(patch.object(backend, '_chat_messages_impl', dispatch))
        yield budget
