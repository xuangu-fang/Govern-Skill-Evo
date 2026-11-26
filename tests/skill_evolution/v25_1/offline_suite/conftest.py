"""Isolated imports and hard no-network/no-external-execution offline boundary."""
import os
import socket
import subprocess

import pytest
from src.skill_evolution.v25_1.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter


@pytest.fixture(autouse=True)
def synthetic_runtime(monkeypatch):
    monkeypatch.setattr(SpreadsheetBenchAdapter, 'runtime_snapshot', staticmethod(lambda config: None))


@pytest.fixture(autouse=True)
def offline_boundary(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('Offline test attempted network or process execution')

    for target, names in ((socket.socket, ('connect', 'connect_ex')),
                          (subprocess, ('Popen',)),
                          (os, ('system', 'execv', 'execve', 'posix_spawn', 'posix_spawnp'))):
        for name in names:
            monkeypatch.setattr(target, name, blocked)
