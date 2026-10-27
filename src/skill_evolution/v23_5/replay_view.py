"""Full current paired facts plus Knowledge Only history; no historical lookup."""
from copy import deepcopy

from src.skill_evolution.v23 import replay as original
from src.skill_evolution.v23.memory import MULTI_KNOWLEDGE_CONTRACT
from src.skill_evolution.v23_4.replay_view import _current_pairs
from .memory_view import knowledge_only

FORMAT = "v23_5_replay_pairs_knowledge_only_v1"


def model_input(bundle, *, memory_contract=MULTI_KNOWLEDGE_CONTRACT):
    payload = original.validate_payload(bundle["payload"], memory_contract=memory_contract)
    pairs, runs = _current_pairs(bundle)
    view = {key: deepcopy(payload[key]) for key in ("parent", "diff", "plan", "command_sets")}
    view.update(pairs=pairs, runs=runs,
                memory=knowledge_only(payload["memory"], memory_contract=memory_contract))
    return view
