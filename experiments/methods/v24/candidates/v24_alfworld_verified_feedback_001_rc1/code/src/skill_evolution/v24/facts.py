"""Shared assertions and explicit dispatch to the bound evidence codec."""
from .benchmark import current as benchmark_current


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, name):
    require(isinstance(value, str) and bool(value.strip()), f'Invalid {name}')
    return value


def build_facts(records):
    return benchmark_current().build_facts(records)


def parent_text(record):
    return benchmark_current().parent_text(record)
