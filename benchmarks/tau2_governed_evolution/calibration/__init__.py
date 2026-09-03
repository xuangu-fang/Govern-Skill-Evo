"""Pilot end-to-end calibration for the governed τ² benchmark."""

from .analysis import analyze_rollout_records

__all__ = ["analyze_rollout_records", "run_calibration"]


def run_calibration(*args, **kwargs):
    """Lazily import the runtime-heavy τ² calibration entry point."""

    from .runner import run_calibration as _run_calibration

    return _run_calibration(*args, **kwargs)
