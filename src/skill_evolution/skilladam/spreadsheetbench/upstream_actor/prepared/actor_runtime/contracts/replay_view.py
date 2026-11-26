from ..benchmark import current as benchmark_current

def _current_pairs(*args, **kwargs):
    return benchmark_current().evidence("contracts.replay_view._current_pairs", *args, **kwargs)

