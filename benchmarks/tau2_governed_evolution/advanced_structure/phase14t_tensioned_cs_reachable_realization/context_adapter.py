"""Bind the frozen candidate public view; no Oracle/task metadata projection."""
import json
from pathlib import Path
from src.skill_evolution.information_boundary_v15 import capture_agent_visible_view, agent_payload, BoundaryError

HERE=Path(__file__).resolve().parent

def bind_candidate_context(agent):
    expected=json.loads((HERE/'contexts/agent_visible_view.json').read_text())
    policy=(HERE/'contexts/airline_visible_policy.md').read_text()
    if expected['visible_policy'] != policy:
        raise BoundaryError('Candidate policy differs from saved public view')
    agent.domain_policy=policy
    view=capture_agent_visible_view(agent,'airline')
    if agent_payload(view) != expected:
        raise BoundaryError('Runtime public tools differ from candidate-native schema')
    return view
