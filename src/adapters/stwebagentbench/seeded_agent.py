"""Strict seed injection for ST-WebAgentBench OpenAI model calls."""

from __future__ import annotations

from typing import Any


class _SeededCompletions:
    def __init__(self, delegate: Any, seed: int) -> None:
        self._delegate = delegate
        self._seed = seed

    def create(self, **kwargs: Any) -> Any:
        kwargs["seed"] = self._seed
        return self._delegate.create(**kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)


class _SeededChat:
    def __init__(self, delegate: Any, seed: int) -> None:
        self._delegate = delegate
        self.completions = _SeededCompletions(delegate.completions, seed)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)


class SeededOpenAIClient:
    """Proxy that unconditionally adds one seed to every chat completion."""

    def __init__(self, delegate: Any, seed: int) -> None:
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise TypeError("campaign_seed must be an integer.")
        self._delegate = delegate
        self.chat = _SeededChat(delegate.chat, seed)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)


def seed_agent_client(agent: Any, seed: int) -> Any:
    """Make an existing DemoAgent fail-fast through seeded API calls."""

    agent.openai_client = SeededOpenAIClient(agent.openai_client, seed)
    return agent
