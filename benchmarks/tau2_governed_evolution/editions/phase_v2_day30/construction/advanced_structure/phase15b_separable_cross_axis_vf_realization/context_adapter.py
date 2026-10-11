"""Candidate public-view binding only; no task, oracle, or solution loading."""
import json
from pathlib import Path
from src.skill_evolution.information_boundary_v15 import capture_agent_visible_view, agent_payload, BoundaryError

HERE = Path(__file__).resolve().parent


def bind_candidate_context(agent):
    policy = (HERE / 'contexts/airline_visible_policy.md').read_text()
    expected = json.loads((HERE / 'contexts/agent_visible_view.json').read_text())
    if expected['visible_policy'] != policy:
        raise BoundaryError('Frozen policy/view mismatch')
    agent.domain_policy = policy
    envelope = capture_agent_visible_view(agent, 'airline')
    if agent_payload(envelope) != expected:
        raise BoundaryError('Public schema drift')
    return envelope
