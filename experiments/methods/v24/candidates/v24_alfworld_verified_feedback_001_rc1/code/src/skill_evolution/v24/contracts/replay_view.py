from src.skill_evolution.v24.benchmark import current as benchmark_current
from src.skill_evolution.v24.resources import resource
"""Deterministic Replay-only view; complete facts and Memory storage stay unchanged."""
from pathlib import Path
import re

from src.skill_evolution.v24.facts import require
from src.skill_evolution.v24.contracts.memory import load_memory, LEGACY_CONTRACT

FORMAT = 'v23_4_replay_pairs_memory_v3_v1'
LEGACY = 'entries_sources'
FORMAT_PATH = resource("v23_4/replay_view_prompt.md")


def history_pair_sources(directory, memory, *, memory_contract=LEGACY_CONTRACT):
    """Capture immutable archive locations, after checking the requested snapshot."""
    require(load_memory(directory, memory_contract=memory_contract) == memory, 'Historical Memory snapshot differs')
    result = {}
    for context in sorted({key.rsplit('/', 1)[0] for key in memory['sources']}):
        require(re.fullmatch(r'[A-Za-z0-9_-]+', context), 'Unsafe historical context')
        path = (Path(directory) / 'archive' / f'{context}.json').resolve()
        result[context] = {'path': str(path)}
    return result


def _historical_pairs(*args, **kwargs):
    return benchmark_current().evidence("contracts.replay_view._historical_pairs", *args, **kwargs)


def _current_pairs(*args, **kwargs):
    return benchmark_current().evidence("contracts.replay_view._current_pairs", *args, **kwargs)


def model_input(*args, **kwargs):
    return benchmark_current().evidence("contracts.replay_view.model_input", *args, **kwargs)
