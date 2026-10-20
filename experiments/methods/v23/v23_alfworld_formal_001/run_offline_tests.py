"""Run preparation/regression tests with external execution disabled."""
import socket
import subprocess
import sys
import pytest


def forbidden(*args, **kwargs):
    raise AssertionError('External network/environment execution forbidden during preparation')


socket.socket.connect = forbidden
socket.socket.connect_ex = forbidden
original_popen = subprocess.Popen


def local_metadata_only(args, *pos, **kwargs):
    # Existing execution-record tests inspect Git metadata; no runner is permitted.
    if isinstance(args, (list, tuple)) and args[:3] == ['git', 'rev-parse', 'HEAD']:
        return original_popen(args, *pos, **kwargs)
    return forbidden(args)


subprocess.Popen = local_metadata_only
sys.exit(pytest.main(['-q', 'tests/skill_evolution/v23', 'tests/adapters/alfworld',
                     'tests/skill_evolution/v22/test_grouped_representation.py']))
