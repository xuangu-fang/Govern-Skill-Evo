"""Use the v25.2 frozen Actor (including its resources) under a distinct package.

The package is importable by name in the Actor's one-request child process too.
"""
from .. import BASELINE

__path__ = [str(BASELINE / 'frozen_workspace/src/skill_evolution/v25')]
