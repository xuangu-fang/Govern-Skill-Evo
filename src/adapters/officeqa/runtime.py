"""Shared SkillAdam-based OfficeQA Actor, without the 8/96 tool-call caps.

No client, credentials, Stage0, or model is loaded implicitly. Direct HTTP is
configured explicitly; offline checks use fixtures. Per-round requests and
per-tool commits are persisted before proceeding.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from skilladam.backends import openai_compatible as native
from skilladam.benchmarks.officeqa.adapter import OfficeQAAdapter
from skilladam.benchmarks.officeqa.rollout import build_messages
from skilladam.benchmarks.officeqa import tool_runtime
from skilladam.execution.backend import BackendConfigurationError

from .data import PROFILE
from .local import source_references
from .execution import atomic_json, _locked
from .transport import ChatTransport
from .retry import GenerationExhausted, generate_round, parse_turn, assistant_message
from .history import validate_history


MAX_MODEL_ROUNDS = 24


class ToolExecutionInterrupted(RuntimeError):
    """A started tool has no committed observation; never silently replay it."""


class Runtime:
    def __init__(self, parsed_root):
        self.parsed_root = Path(parsed_root).resolve()
        self.text_root = self.parsed_root / 'transformed'
        if not self.text_root.is_dir():
            raise FileNotFoundError(self.text_root)
        self.roots = [str(self.text_root)]
        self.scorer = OfficeQAAdapter(self.parsed_root)

    def prepare(self, case, skill):
        payload = case.payload
        if 'document_text' in payload:
            raise ValueError('Inline evidence may not bypass the shared page renderer')
        refs = source_references(payload['source_files'], payload['source_docs'])
        if tool_runtime._iter_oracle_refs(payload['source_files'], payload['source_docs']) != refs:
            raise ValueError('Task has not received the common source mapping correction')
        allowed = native._officeqa_allowed_files(payload)
        if not allowed:
            raise BackendConfigurationError('OfficeQA requires a nonempty source-file allowlist')
        for name in allowed:
            path = self.text_root / name
            if tool_runtime._safe_enumerated_file(path, self.text_root) is None:
                raise ValueError(f'Missing or out-of-corpus source file: {name}')
        for name, page, _ in refs:
            path = tool_runtime._locate_parsed_json(name, self.roots)
            if path is None or not tool_runtime._render_parsed_page(str(path), page):
                raise ValueError(f'Missing parsed source page: {name}:{page}')
        # build_messages is method-independent in the pinned SkillAdam source.
        messages = build_messages(case, method='skilladam', skill=skill)
        messages = native._officeqa_add_oracle_context(messages, payload=payload, allowed_roots=self.roots)
        return messages, allowed

    def run(self, case, skill, transport, *, owner, directory):
        with _locked(Path(directory)):
            return self._run(case, skill, transport, owner=owner, directory=Path(directory))

    def _run(self, case, skill, transport, *, owner, directory):
        if owner not in ('govern', 'skillopt', 'skilladam'):
            raise ValueError('Unknown OfficeQA method owner')
        initial, allowed = self.prepare(case, skill)
        identity = {'profile': PROFILE, 'method': owner, 'task_id': case.case_id,
                    'skill': skill, 'actor': transport.metadata(),
                    'input_sha256': hashlib.sha256(json.dumps(
                        {'messages': initial, 'reference': list(case.reference)},
                        sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
        path = directory / 'actor_state.json'
        reasoning = transport.metadata()['reasoning_mode'] == 'deepseek_thinking'
        if path.exists():
            state = json.loads(path.read_text())
            if state.get('schema') != 1 or state['identity'] != identity:
                raise ValueError('OfficeQA Actor resume identity differs')
            if state['initial'] != initial:
                raise ValueError('OfficeQA initial messages changed')
            validate_history(state, reasoning=reasoning)
        else:
            state = {'schema': 1, 'identity': identity, 'initial': initial,
                     'messages': deepcopy(initial), 'rounds': [], 'calls': 0,
                     'complete': False, 'status': 'running', 'response': '',
                     'redactions': native._officeqa_redactions(data_root=self.parsed_root, allowed_roots=self.roots)}
        def save():
            atomic_json(path, state)
        save()
        if 'record' in state:
            return state['record']
        while not state['complete']:
            if not state['rounds'] or state['rounds'][-1]['phase'] == 'done':
                if len(state['rounds']) == MAX_MODEL_ROUNDS:
                    state.update(complete=True, termination='max_tool_turns')
                    save()
                    break
                state['rounds'].append({'number': len(state['rounds']) + 1,
                                        'phase': 'generation', 'attempts': [], 'repair': None, 'tools': []})
                save()
            current = state['rounds'][-1]
            if current['phase'] == 'generation':
                try:
                    turn = generate_round(current, state['messages'], transport, save)
                except GenerationExhausted:
                    state['status'] = 'generation_incomplete'
                    save()
                    raise
                if not turn.tool_calls:
                    state['messages'].append(assistant_message(turn, current['attempts'][-1]['response'], reasoning=reasoning))
                    state.update(response=turn.text, complete=True, termination='answer')
                    current['phase'] = 'done'
                    save()
                    break
                state['messages'].append(assistant_message(turn, current['attempts'][-1]['response'], reasoning=reasoning))
                current.update(phase='tools', tools=[{'status': 'pending'} for _ in turn.tool_calls])
                save()
            # All calls were validated before the assistant message was committed.
            turn = parse_turn(current['attempts'][-1]['response'], require_reasoning=reasoning)
            for call, tool in zip(turn.tool_calls, current['tools']):
                if tool['status'] == 'done':
                    continue
                if tool['status'] == 'started':
                    raise ToolExecutionInterrupted('Tool outcome unknown; automatic replay is forbidden')
                state['redactions'].extend(native._officeqa_external_path_redactions(call.arguments, allowed_roots=self.roots))
                tool['status'] = 'started'
                save()
                observation = native._run_officeqa_tool(call, allowed_roots=self.roots, allowed_files=allowed)
                tool.update(status='done', observation=observation)
                state['messages'].append({'role': 'tool', 'tool_call_id': call.call_id,
                                          'name': call.name, 'content': observation})
                state['calls'] += 1
                save()
            current['phase'] = 'done'
            save()
        attempts = [attempt for rd in state['rounds'] for attempt in rd['attempts']]
        raw = {'response': state['response'], 'messages': state['messages'],
               'usage_records': [attempt['usage'] for attempt in attempts],
               'n_turns': len(state['rounds']), 'n_tool_calls': state['calls'],
               'api_requests': len(attempts),
               'termination_reason': state['termination'],
               'fail_reason': '' if state['termination'] == 'answer' else f'Exceeded tool-turn budget ({MAX_MODEL_ROUNDS})'}
        raw = native._redact_officeqa_value(raw, state['redactions'])
        # References are accessed for scoring only after the Actor has terminated.
        parsed = self.scorer.parse_result(case, raw)
        metrics = self.scorer.evaluate(parsed)
        record = {'profile': PROFILE, 'method': owner, 'task_id': case.case_id,
                  'skill': skill, 'actor': transport.metadata(),
                  'initial_messages': native._redact_officeqa_value(initial, state['redactions']),
                  'raw_result': raw, 'answer': parsed.output, 'metrics': dict(metrics.metrics),
                  'request_audit': native._redact_officeqa_value(state['rounds'], state['redactions'])}
        state.update(status='completed', record=record)
        save()
        return record
