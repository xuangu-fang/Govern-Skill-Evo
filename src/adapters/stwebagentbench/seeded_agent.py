"""Strict seed injection for ST-WebAgentBench OpenAI model calls."""

from __future__ import annotations

from typing import Any


class _SeededCompletions:
    def __init__(
        self, delegate: Any, seed: int, temperature: float | None
    ) -> None:
        self._delegate = delegate
        self._seed = seed
        self._temperature = temperature

    def create(self, **kwargs: Any) -> Any:
        kwargs["seed"] = self._seed
        if self._temperature is not None:
            kwargs["temperature"] = self._temperature
        return self._delegate.create(**kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)


class _SeededChat:
    def __init__(
        self, delegate: Any, seed: int, temperature: float | None
    ) -> None:
        self._delegate = delegate
        self.completions = _SeededCompletions(
            delegate.completions, seed, temperature
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)


class SeededOpenAIClient:
    """Proxy that freezes sampling arguments for every chat completion."""

    def __init__(
        self, delegate: Any, seed: int, temperature: float | None = None
    ) -> None:
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise TypeError("campaign_seed must be an integer.")
        if temperature is not None and not isinstance(temperature, (int, float)):
            raise TypeError("temperature must be numeric.")
        self._delegate = delegate
        self.chat = _SeededChat(delegate.chat, seed, temperature)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)


def seed_agent_client(
    agent: Any, seed: int, *, temperature: float | None = None
) -> Any:
    """Freeze sampling on an existing DemoAgent's final API client."""

    agent.openai_client = SeededOpenAIClient(
        agent.openai_client, seed, temperature
    )
    return agent
