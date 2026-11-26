"""Independent v29.11 selective-Gate modules and recoverable training orchestration."""
from src.skill_evolution.v29.benchmarks.docvqa import protocol


def prompt_execution_context(background):
    context = protocol.execution_context(background)
    return context.replace(f" through {background['endpoint']}", "")
