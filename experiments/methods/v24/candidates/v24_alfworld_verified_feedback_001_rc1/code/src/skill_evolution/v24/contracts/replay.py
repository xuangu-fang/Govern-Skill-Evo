from src.skill_evolution.v24.benchmark import current as benchmark_current







def verify_pair(*args, **kwargs):
    return benchmark_current().evidence("contracts.replay.verify_pair", *args, **kwargs)


def build_replay_from_editor(*args, **kwargs):
    return benchmark_current().evidence("contracts.replay.build_replay_from_editor", *args, **kwargs)


def validate_payload(*args, **kwargs):
    return benchmark_current().evidence("contracts.replay.validate_payload", *args, **kwargs)

