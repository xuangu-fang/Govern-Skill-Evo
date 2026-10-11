"""Explicit protocol selection for new runs; artifact-version dispatch for reads."""
from pathlib import Path
from . import attribution_v19 as legacy
from . import attribution_pairs_v19 as pairs
from .evolution_replay_v19 import _load


def is_pair(directory):
    path = Path(directory) / 'config.json'
    return path.exists() and _load(path).get('schema_version') == pairs.PROTOCOL


def archive_files(directory):
    return (*(pairs.FILES if is_pair(directory) else legacy.FILES), 'validation.json')


def load_complete(directory, data):
    if is_pair(directory):
        return pairs.load_complete(directory, data)
    request = _load(Path(directory) / 'request.json')
    legacy.require(request['user_prompt'] == legacy.encode(data), 'archived request input mismatch')
    return legacy._load_complete(Path(directory), data, request)


def load_attribution(ledger, *, backend, parent_dir, replay_dir, artifact_dir, history=()):
    data = legacy.build_attribution_input(ledger, backend=backend, parent_dir=parent_dir,
                                         replay_dir=replay_dir, history=history)
    return load_complete(artifact_dir, data)


def run_attribution(*args, protocol='pair', **kwargs):
    legacy.require(protocol in ('legacy', 'pair'), 'unknown Attribution protocol')
    return (pairs if protocol == 'pair' else legacy).run_attribution(*args, **kwargs)
