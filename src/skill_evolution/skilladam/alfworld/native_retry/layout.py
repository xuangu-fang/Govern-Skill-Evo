"""Runtime and configuration locations for ALFWorld native-retry experiments."""
import os
from pathlib import Path

from src.skill_evolution.shared.experiment_paths import ROOT, resolve_experiment_path

EXPERIMENTS = ROOT / 'experiments/methods/skilladam/alfworld/native_retry'
ARTIFACTS = ROOT / 'artifacts/methods/skilladam/alfworld/native_retry'


def is_method_config(experiment):
    return experiment.name == 'config' and experiment.parent.parent == EXPERIMENTS


def output_binding(experiment):
    experiment = resolve_experiment_path(experiment)
    output = ARTIFACTS / experiment.parent.name if is_method_config(experiment) else experiment / 'campaign'
    return os.path.relpath(output, ROOT)


def current_binding(cfg):
    """Normalize the output path in a copy for comparing a frozen configuration."""
    return {**cfg, 'output_root': os.path.relpath(resolve_experiment_path(cfg['output_root']), ROOT)}


def launch_files(output):
    if output.parent == ARTIFACTS:
        # Migrated runs retain their original launch records. Fresh native runs
        # require an empty output directory at RunStore initialization.
        launch = output / 'launch'
        if not (launch / 'campaign.launch.json').is_file():
            launch = ARTIFACTS / 'launch' / output.name
        return launch / 'campaign.lock', launch / 'campaign.launch.json'
    return output.with_suffix('.lock'), output.with_suffix('.launch.json')
