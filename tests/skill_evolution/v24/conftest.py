import socket
import pytest
from src.skill_evolution.v24.benchmark import using_benchmark
from src.skill_evolution.v24.benchmarks.alfworld.adapter import ALFWorldAdapter


@pytest.fixture(autouse=True)
def offline_benchmark(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('V24 offline tests must not access the network')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    with using_benchmark(ALFWorldAdapter()) as adapter:
        yield adapter


@pytest.fixture(autouse=True)
def current_actor_fixture_records(monkeypatch):
    """Paired mock campaigns use each version's actual record representation."""
    from tests.skill_evolution.v23_4.test_evolution import Harness
    from src.skill_evolution.v24.benchmarks.alfworld.actor import skill_runtime as rt
    from src.skill_evolution.v24 import evolution as ev
    original = Harness.actor
    def actor(self, task, skill, dest, cfg):
        path = original(self, task, skill, dest, cfg)
        if cfg['method']['version'] == 'v24_campaign_v1':
            value = ev.read(path)
            value = {k: value[k] for k in ('schema_version','run_id','task','split','purpose','access',
                     'skill','model','backend_id','gamefile','environment','protocol','versions','implementation',
                     'started_at','steps','won','status','initial_observation','initial_admissible_commands','goal',
                     'request_policy','finished_at') if k in value}
            value['skill'] = rt.load_skill(skill)
            value['protocol'] = rt.execution_protocol(cfg['max_steps'])
            value['environment'] = {'gamefile': value.get('gamefile'), 'manifest_path': 'fixture'}
            value['implementation'] = rt.implementation_metadata()
            ev.save(path,value)
        return path
    monkeypatch.setattr(Harness, 'actor', actor)
