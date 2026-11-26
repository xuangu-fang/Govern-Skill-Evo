import os
import platform
import socket
import subprocess
import sys
import pytest

from src.skill_evolution.skilladam.spreadsheetbench.layout import UPSTREAM

sys.path.insert(0, str(UPSTREAM))


@pytest.fixture(autouse=True)
def offline_boundary(monkeypatch):
    # The SDK stamps its HTTP headers with a platform string, even on MockTransport.
    monkeypatch.setattr(platform, 'platform', lambda: sys.platform)

    def blocked(*args, **kwargs):
        pytest.fail('Offline test attempted external I/O')
    for obj, names in [(socket.socket, ('connect', 'connect_ex')), (subprocess, ('Popen',)),
                       (os, ('system', 'execv', 'execve', 'posix_spawn', 'posix_spawnp'))]:
        for name in names:
            monkeypatch.setattr(obj, name, blocked)
