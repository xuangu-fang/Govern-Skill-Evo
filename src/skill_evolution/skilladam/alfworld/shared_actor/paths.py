"""Locations for the shared Actor experiment and its original input manifests."""
from pathlib import Path

from scripts.runs.alfworld.alfworld_aligned_common import frozen_input
from src.skill_evolution.shared.experiment_paths import ROOT


RUN_ID = 'skilladam_current_actor_20261025'
CONFIG = ROOT / 'experiments/methods/skilladam/alfworld/shared_actor' / RUN_ID / 'config'
ARCHIVE = ROOT / 'artifacts/methods/skilladam/alfworld/shared_actor' / RUN_ID
COMMIT = 'b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1'


def default_upstream():
    local = ARCHIVE.parent / 'upstream' / COMMIT
    return local if local.is_dir() else ROOT / 'external/SkillAdam'


def historical_input(name, upstream=None):
    """Locate a file named in a pre-layout manifest, including its historical source."""
    path = Path(name)
    path = path if path.is_absolute() else ROOT / path
    provenance = CONFIG / 'provenance/before_layout'
    if path.is_relative_to(ROOT):
        relative = path.relative_to(ROOT)
        snapshot = provenance / relative
        if snapshot.is_file():
            return snapshot
        if relative == Path('experiments/baselines') / RUN_ID / 'README.md':
            return provenance / 'README.md'
    external = ROOT / 'external/SkillAdam'
    if upstream is not None and path.is_relative_to(external):
        return upstream / path.relative_to(external)
    resolved = frozen_input(path)
    if path.name == 'README.md' and path.parent.parent == ROOT / 'experiments/baselines':
        original_readme = resolved.parent / 'config/provenance/README.before-layout.md'
        if original_readme.is_file():
            return original_readme
    return resolved
