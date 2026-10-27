from src.skill_evolution.v24.benchmark import current as benchmark_current
"""Full current paired facts plus Knowledge Only history; no historical lookup."""


FORMAT = "v23_5_replay_pairs_knowledge_only_v1"


def model_input(*args, **kwargs):
    return benchmark_current().evidence("replay_view.model_input", *args, **kwargs)
