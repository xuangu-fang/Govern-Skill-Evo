"""Maintainer-side synthetic turnaround laws, never part of public tool payloads."""
from dataclasses import asdict, dataclass
from itertools import product


@dataclass(frozen=True)
class World:
    fixture_minutes: int = 6
    rise_minutes: int = 4
    fall_minutes: int = 8
    overlap: bool = True
    per_unit_handling: bool = False
    reuse: bool = True

    def durations(self, before, after, quantity, previous_batch, recipe_minutes):
        fixture = self.fixture_minutes if before[0] != after[0] else 0
        if previous_batch and not self.reuse:
            fixture = self.fixture_minutes
        thermal = 0
        if before[1] != after[1]:
            thermal = self.rise_minutes if after[1] == "high" else self.fall_minutes
        setup = max(fixture, thermal) if self.overlap else fixture + thermal
        handling = 4 * (quantity if self.per_unit_handling else 1)
        return setup, recipe_minutes + handling

    def record(self):
        return asdict(self)


def hypotheses():
    """64 declared competing models, not a universal identifiability claim."""
    return [World(*values) for values in product(
        (6, 10), (4, 8), (4, 8), (False, True), (False, True), (False, True))]
