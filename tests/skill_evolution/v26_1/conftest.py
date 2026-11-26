"""All v26.1 acceptance is synthetic and network-denied."""
import socket
import pytest

@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    def deny(*args, **kwargs): raise AssertionError('Network/provider forbidden in v26.1 offline acceptance')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)
    import requests, openai
    monkeypatch.setattr(requests.Session, 'request', deny)
    monkeypatch.setattr(openai, 'OpenAI', deny)
    monkeypatch.setattr(openai, 'AzureOpenAI', deny)
    monkeypatch.setattr('src.adapters.officeqa.retry.retry_wait', lambda _: None)
    monkeypatch.setattr('src.skill_evolution.v26_1.stages.time.sleep', lambda _: None)
