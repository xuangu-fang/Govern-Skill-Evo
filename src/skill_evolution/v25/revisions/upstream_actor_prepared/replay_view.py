from .benchmark import current as benchmark_current
"""Full current paired facts plus Knowledge Only history; no historical lookup."""
from .facts import require
from .replay_shared_initial import share_initial


LEGACY_FORMAT = "v25_replay_pairs_knowledge_only_v1"
PAIRED_FORMAT = "v25_replay_pairs_knowledge_only_v2"
SHARED_INITIAL_FORMAT = "v25_replay_pairs_knowledge_only_v3"
FORMAT = "v25_replay_pairs_knowledge_only_v4"
SUPPORTED_FORMATS = (LEGACY_FORMAT, PAIRED_FORMAT, SHARED_INITIAL_FORMAT, FORMAT)


def model_input(bundle, *, input_view=FORMAT, **kwargs):
    require(input_view in SUPPORTED_FORMATS, 'Unsupported Replay input view')
    # The adapter validates pair identity and coverage before any presentation change.
    view = benchmark_current().evidence("replay_view.model_input", bundle, **kwargs)
    if input_view == LEGACY_FORMAT:
        return view
    runs = {run['ref']: run for run in view['runs']}
    ordered = [runs[pair[side]] for pair in view['pairs'] for side in ('parent', 'candidate')]
    paired = {**{key: view[key] for key in ('parent', 'diff', 'plan')},
              'pairs': view['pairs'], 'runs': ordered, 'memory': view['memory']}
    if input_view == PAIRED_FORMAT:
        return paired
    shared = share_initial(paired)
    return benchmark_current().evidence('replay_view.share_code', shared) if input_view == FORMAT else shared
