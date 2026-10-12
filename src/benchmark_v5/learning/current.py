"""Current reusable sandbox API: interface 0.2 and corrected obligation grader 0.2.

Historical calibration runners intentionally retain their frozen implementation.
Import build/evaluate here for new integrations; pass an explicit Case and World.
"""
from .interface_revision import build
from .evaluation_revision import evaluate

VERSION = 'learning-0.2'
__all__ = ['VERSION','build','evaluate']
