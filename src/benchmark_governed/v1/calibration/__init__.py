"""Pilot end-to-end calibration for the governed τ² benchmark."""

from scripts.benchmarks.governed.v1.calibration.analysis import analyze_rollout_records

__all__ = ["analyze_rollout_records", "run_calibration"]


def run_calibration(*args, **kwargs):
    """Lazily import the runtime-heavy τ² calibration entry point."""

    from src.benchmark_governed.v1.calibration.runner import run_calibration as _run_calibration

    return _run_calibration(*args, **kwargs)
