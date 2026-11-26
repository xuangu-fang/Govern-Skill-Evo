from scripts.runs.run_v26_pilot import run_pilot
from src.skill_evolution.v26.benchmark import using_benchmark
from .test_campaign import campaign


def test_pilot_and_resume_never_start_second_iteration(campaign):
    root, adapter, provider, config, generate = campaign()
    config['batches'] = [['a'], ['b']]
    with using_benchmark(adapter):
        result = run_pilot(root, config=config, generate=generate)
        count = len(provider.requests)
        assert result['rounds_completed'] == 1 and not result['next_round_started']
        def forbidden(*args): raise AssertionError('Completed pilot must not generate')
        assert run_pilot(root, generate=forbidden, resume=True)['outcome'] == result['outcome']
        assert len(provider.requests) == count and not (root/'rounds/R02').exists()
