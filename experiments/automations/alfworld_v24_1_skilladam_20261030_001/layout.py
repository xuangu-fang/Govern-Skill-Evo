"""Locate the original schedule inputs and the current executable job paths."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from src.skill_evolution.shared.experiment_paths import resolve_experiment_path
from src.skill_evolution.skilladam.alfworld.shared_actor.paths import historical_input


def execution_dir(job, *, test=False):
    # A fresh one-shot supervisor must keep its receipts outside the still-empty output.
    name = f"{job}.test.state.json" if test else f"{job}.state.json"
    previous = HERE / 'execution' / name
    archived = resolve_experiment_path(previous)
    return archived.parent if archived.exists() else previous.parent


def job_command(args):
    return [str(resolve_experiment_path(arg).relative_to(ROOT))
            if arg.startswith(('scripts/', 'experiments/', 'artifacts/')) else arg for arg in args]


def load_plan(path):
    plan = json.loads(path.read_text())
    for job in plan['jobs'].values():
        for key in ('experiment', 'training_output', 'test_output'):
            job[key] = str(resolve_experiment_path(job[key]).relative_to(ROOT))
        for key in ('train_command', 'resume_command', 'test_command'):
            job[key] = job_command(job[key])
    return plan


def frozen_file(name):
    path = ROOT / name
    if path.parent == HERE:
        snapshot = HERE / 'revisions/before_native_retry_layout' / path.name
        if snapshot.is_file():
            return snapshot
    return historical_input(path)
