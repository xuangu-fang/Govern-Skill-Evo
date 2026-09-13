"""v15 experience-grounded learner entrypoint, no evaluation/rollout execution.

Oracle evaluation remains independent and unchanged. At the runtime boundary,
call project_oracle_supervision on completed evaluator/Judge records, and capture
only actual normalized observed events. Never pass legacy governed-evidence blobs.
"""
from functools import partial
import json
from pathlib import Path
from .information_boundary_v15 import (
    BoundaryError, LEARNER_SETTING, INFORMATION_BOUNDARY_VERSION,
    capture_agent_visible_view, project_oracle_supervision,
    capture_experience, learner_safe_view, unpack,
)
from .diagnosis_v15 import MultiRolloutDiagnosisRequest, call_diagnosis
from .autonomous_gse_v15_proposal import MultiRolloutDiagnosisProposalOperator
from src.learners.stwebagentbench.generate_governed_skill_v15 import call_governed_editor

ROOT = Path(__file__).resolve().parents[2]
CONTEXT_MANIFEST = ROOT / 'benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/formal_manifestation_admission/contexts/context_manifest.json'


def normalize_stored_simulation(simulation):
    """Project a serialized tau2 Simulation onto events actually seen by participants."""
    if hasattr(simulation, 'model_dump'):
        simulation = simulation.model_dump(mode='json')
    if not isinstance(simulation, dict) or not isinstance(simulation.get('messages'), list):
        raise BoundaryError('Serialized tau2 messages required')
    events, call_names = [], {}
    for message in simulation['messages']:
        if not isinstance(message, dict) or message.get('role') not in {'user', 'assistant', 'tool'}:
            raise BoundaryError('Unsupported serialized message')
        role = message['role']
        content = message.get('content')
        if role in {'user', 'assistant'} and content:
            if not isinstance(content, str):
                raise BoundaryError('Serialized participant content must be text')
            events.append({'actor': role, 'event_type': 'message', 'content': content})
        calls = message.get('tool_calls')
        if role == 'assistant' and calls:
            if not isinstance(calls, list):
                raise BoundaryError('Serialized tool calls must be a list')
            for call in calls:
                if not isinstance(call, dict) or not isinstance(call.get('id'), str) or not isinstance(call.get('name'), str) or not isinstance(call.get('arguments'), dict):
                    raise BoundaryError('Malformed serialized tool call')
                call_names[call['id']] = call['name']
                events.append({'actor': 'assistant', 'event_type': 'tool_call',
                               'tool_name': call['name'], 'arguments': call['arguments']})
        elif role == 'tool':
            call_id = message.get('id')
            if not isinstance(call_id, str) or call_id not in call_names:
                raise BoundaryError('Tool result lacks a preceding observed call')
            events.append({'actor': 'tool', 'event_type': 'tool_result',
                           'tool_name': call_names[call_id], 'content': content})
    if not events:
        raise BoundaryError('Serialized trajectory is empty')
    return events


def bind_visible_context(agent, domain):
    """Use the frozen Base context; never load full canonical policy/source contracts."""
    manifest = json.loads(CONTEXT_MANIFEST.read_text())
    if domain not in manifest['contexts']:
        raise BoundaryError('No visible context projection')
    spec = manifest['contexts'][domain]
    agent.domain_policy = (ROOT / spec['policy_path']).read_text()
    overrides = json.loads((ROOT / spec['tool_overrides_path']).read_text())['overrides']
    names = {tool.name for tool in agent.tools}
    if not set(overrides) <= names:
        raise BoundaryError('Visible override tool missing')
    for tool in agent.tools:
        if tool.name in overrides:
            tool.short_desc = overrides[tool.name]['description']
            tool.long_desc = ''
    return capture_agent_visible_view(agent, domain)


def prepare_diagnosis(view, parent_skill, observed_rollouts, success_records, raw_judge_outputs):
    """Three observations + labels, no task scenario/evaluator objects in payload."""
    if not all(isinstance(x, (list, tuple)) and len(x) == 3 for x in (observed_rollouts, success_records, raw_judge_outputs)):
        raise BoundaryError('Three Parent rollouts and explicit labels required')
    experiences = tuple(
        capture_experience(view, events, project_oracle_supervision(success, judge), index)
        for index, (events, success, judge) in enumerate(zip(observed_rollouts, success_records, raw_judge_outputs), 1)
    )
    return MultiRolloutDiagnosisRequest(learner_safe_view(view, experiences, parent_skill))


def prepare_diagnosis_from_stored(view, parent_skill, serialized_rollouts, success_records, raw_judge_outputs):
    """Replay stored tau2 serialization through the same v15 projection and routing."""
    if not isinstance(serialized_rollouts, (list, tuple)) or len(serialized_rollouts) != 3:
        raise BoundaryError('Three serialized Parent rollouts required')
    observed = [normalize_stored_simulation(value) for value in serialized_rollouts]
    return prepare_diagnosis(view, parent_skill, observed, success_records, raw_judge_outputs)


def propose_from_experience(requests, *, diagnosis_transport, editor_transport):
    """No privileged fallback, no selection, no automatic model/provider default."""
    if not isinstance(requests, tuple) or not requests:
        raise BoundaryError('Explicit learner-safe requests required')
    operator = MultiRolloutDiagnosisProposalOperator()
    result = operator.propose(
        requests,
        diagnosis_call=partial(call_diagnosis, learner_call=diagnosis_transport),
        editor_call=partial(call_governed_editor, learner_call=editor_transport),
    )
    result.update(learner_setting=LEARNER_SETTING, information_boundary_version=INFORMATION_BOUNDARY_VERSION)
    return result
