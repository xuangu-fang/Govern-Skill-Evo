"""Separate Oracle, deployed Agent, and experience-only Learner channels.

Runtime capture is the trust boundary: callers supply the actual bound agent and
observed events, never task/evaluator dictionaries as observations. Seals prevent
accidental DTO forgery/mutation, not malicious Python in the trusted process.
"""
from dataclasses import dataclass
import hashlib
import hmac
import json
import secrets

LEARNER_SETTING = "EXPERIENCE_GROUNDED_LEARNER"
INFORMATION_BOUNDARY_VERSION = "v15_learner_safe"
LEGACY_SETTING = {"learner_setting": "PRIVILEGED_LEARNER", "information_boundary_version": "v14_legacy"}
MAX_ALLOWED_SUPERVISION = 2
IMPLEMENTED_SUPERVISION_LEVEL = 0
_KEY = secrets.token_bytes(32)


class BoundaryError(ValueError):
    """An untrusted/missing boundary projection fails closed."""


@dataclass(frozen=True)
class Envelope:
    kind: str
    payload: str
    signature: str


def _seal(kind, value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    sig = hmac.new(_KEY, (kind + '\n' + payload).encode(), hashlib.sha256).hexdigest()
    return Envelope(kind, payload, sig)


def unpack(envelope, kind):
    if not isinstance(envelope, Envelope) or envelope.kind != kind:
        raise BoundaryError('Missing trusted ' + kind + ' projection')
    sig = hmac.new(_KEY, (kind + '\n' + envelope.payload).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, envelope.signature):
        raise BoundaryError('Altered or foreign-session projection')
    return json.loads(envelope.payload)


@dataclass(frozen=True)
class OracleView:
    """Oracle logging/evaluation input. Never accepted by learner serializers."""
    canonical_policy: str
    private_backend: dict
    evaluator_truth: dict
    mechanism_metadata: dict


def _public_schema(schema):
    # Use exactly the deployed function schema. No AST/docstring/ToolType loader.
    if not isinstance(schema, dict) or set(schema) != {'type', 'function'} or schema['type'] != 'function':
        raise BoundaryError('Not a public function schema')
    f = schema['function']
    if not isinstance(f, dict) or not {'name', 'description', 'parameters'} <= set(f) or set(f) - {'name', 'description', 'parameters', 'strict'}:
        raise BoundaryError('Private or malformed tool contract')
    if not isinstance(f['name'], str) or not isinstance(f['description'], str) or not isinstance(f['parameters'], dict):
        raise BoundaryError('Invalid public schema fields')
    return schema


def capture_agent_visible_view(agent, domain):
    """Capture AFTER existing benchmark bind_agent_context; no fallback loader."""
    if domain not in {'airline', 'retail'}:
        raise BoundaryError('Unknown domain')
    policy = getattr(agent, 'domain_policy', None)
    tools = getattr(agent, 'tools', None)
    if not isinstance(policy, str) or not policy.strip() or not tools:
        raise BoundaryError('Bound Agent policy/tools required')
    schemas = [_public_schema(tool.openai_schema) for tool in tools]
    if len({s['function']['name'] for s in schemas}) != len(schemas):
        raise BoundaryError('Duplicate public tools')
    return _seal('AGENT_VISIBLE_VIEW', {'domain': domain, 'visible_policy': policy, 'public_tools': schemas})


def agent_payload(view):
    return unpack(view, 'AGENT_VISIBLE_VIEW')


def project_oracle_supervision(success_record, raw_judge_output):
    """Content-independent Level 0 projection; no raw prose/IDs ever copied."""
    success = success_record.get('success') if isinstance(success_record, dict) else None
    compliant = raw_judge_output.get('compliant') if isinstance(raw_judge_output, dict) else None
    if type(success) is not bool or type(compliant) is not bool:
        raise BoundaryError('Explicit boolean labels required, no imputation')
    return _seal('LEARNER_SAFE_SUPERVISION', {
        'success': success, 'compliant': compliant, 'level': 0,
        'provenance': 'LEARNER_SAFE_SUPERVISION',
    })


def capture_experience(view, events, supervision, rollout_index):
    """Capture normalized OBSERVED events; task scripts and evaluator objects rejected.

    tool_call arguments and tool_result content retain actual observed semantics.
    Normalization of live framework messages is a runtime adapter responsibility.
    """
    public = agent_payload(view)
    labels = unpack(supervision, 'LEARNER_SAFE_SUPERVISION')
    if rollout_index not in (1, 2, 3) or type(rollout_index) is not int:
        raise BoundaryError('Require Parent rollout index 1/2/3')
    if not isinstance(events, (list, tuple)) or not events:
        raise BoundaryError('Observed trajectory required')
    names = {t['function']['name'] for t in public['public_tools']}
    steps = []
    for i, event in enumerate(events, 1):
        if not isinstance(event, dict):
            raise BoundaryError('Observed event must be an object')
        kind = event.get('event_type')
        allowed = {'actor', 'event_type', 'content'}
        if kind == 'tool_call':
            allowed = {'actor', 'event_type', 'tool_name', 'arguments'}
            if event.get('tool_name') not in names or not isinstance(event.get('arguments'), dict):
                raise BoundaryError('Unknown public tool or invalid arguments')
        elif kind == 'tool_result':
            allowed = {'actor', 'event_type', 'tool_name', 'content'}
            if event.get('tool_name') not in names:
                raise BoundaryError('Unknown result tool')
        elif kind != 'message':
            raise BoundaryError('Only observed messages/calls/results allowed')
        if set(event) != allowed or event.get('actor') not in {'user', 'assistant', 'tool'}:
            raise BoundaryError('Oracle/metadata fields in observed event')
        if (kind == 'message' and event['actor'] not in {'user', 'assistant'}) or (kind == 'tool_call' and event['actor'] != 'assistant') or (kind == 'tool_result' and event['actor'] != 'tool'):
            raise BoundaryError('Event actor mismatch')
        steps.append({'step': i, **event})
    return _seal('TRAJECTORY_DERIVED', {
        'view_digest': hashlib.sha256(view.payload.encode()).hexdigest(),
        'domain': public['domain'], 'rollout_index': rollout_index,
        'trajectory': steps, 'supervision': labels,
    })


def learner_safe_view(view, experiences, current_skill):
    public = agent_payload(view)
    if not isinstance(current_skill, str) or not current_skill.strip():
        raise BoundaryError('Current deployed Skill required')
    if not isinstance(experiences, tuple) or len(experiences) != 3:
        raise BoundaryError('Exactly three Parent experiences required')
    rollouts = [unpack(e, 'TRAJECTORY_DERIVED') for e in experiences]
    if sorted(r['rollout_index'] for r in rollouts) != [1, 2, 3]:
        raise BoundaryError('Independent rollout indices required')
    digest = hashlib.sha256(view.payload.encode()).hexdigest()
    for r in rollouts:
        if r['view_digest'] != digest:
            raise BoundaryError('Base/Learner context mismatch')
    return _seal('LEARNER_SAFE_VIEW', {
        **public, 'current_skill': current_skill,
        'rollouts': sorted(rollouts, key=lambda r: r['rollout_index']),
        'learner_setting': LEARNER_SETTING,
        'information_boundary_version': INFORMATION_BOUNDARY_VERSION,
    })
