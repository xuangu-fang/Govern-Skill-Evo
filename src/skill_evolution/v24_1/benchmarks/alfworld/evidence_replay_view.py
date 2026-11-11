from copy import deepcopy
from src.skill_evolution.v24_1.contracts import replay as original
from src.skill_evolution.v24_1.contracts.memory import MULTI_KNOWLEDGE_CONTRACT
from src.skill_evolution.v24_1.contracts.replay_view import _current_pairs
from src.skill_evolution.v24_1.memory_view import knowledge_only

def model_input(bundle, *, memory_contract=MULTI_KNOWLEDGE_CONTRACT):
    payload = original.validate_payload(bundle["payload"], memory_contract=memory_contract)
    pairs, runs = _current_pairs(bundle)
    view = {key: deepcopy(payload[key]) for key in ("parent", "diff", "plan", "command_sets")}
    view.update(pairs=pairs, runs=runs,
                memory=knowledge_only(payload["memory"], memory_contract=memory_contract))
    return view
