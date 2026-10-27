from src.skill_evolution.v24.benchmark import current as benchmark_current







def preconditioner_input(*args, **kwargs):
    return benchmark_current().evidence("contracts.preconditioner.preconditioner_input", *args, **kwargs)

