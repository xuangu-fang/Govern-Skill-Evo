import json
from unittest.mock import Mock

import pytest
from src.skill_evolution.v18 import monitor_benchmark_v18 as m
from src.skill_evolution.v18.monitor_v18 import MonitorCall, MonitorRejected, digest


def test_backend_checkpoint_binds_skill_config_and_files(tmp_path):
    backend=object.__new__(m.CurrentBenchmarkMonitor)
    backend.root=tmp_path
    backend.task_ids=['task'];backend.config_digest='a'*64
    backend.skills={'CANDIDATE':''}
    backend.initial_path=tmp_path/'S0.md';backend.initial_path.write_text('# Skill')
    backend.initial_text='# Skill';candidate=tmp_path/'candidate.md';candidate.write_bytes(b'')
    backend.paths={'CANDIDATE':candidate};backend.base_config={};backend.resume=False
    orchestrator=Mock();orchestrator.environment.tools.db.model_dump.return_value={}
    orchestrator.run.return_value.model_dump.return_value={'task_id':'task','seed':200}
    backend.adapter=Mock();backend.adapter.build_orchestrator.return_value=(orchestrator,None)
    backend.evaluator=Mock();backend.evaluator.evaluate.return_value={'success':True,'compliant':True}
    call=MonitorCall('task',1,200,'CANDIDATE','',digest(''),'a'*64)
    result=backend(call)
    assert result['success'] and result['compliant']
    backend.resume=True
    assert backend(call)==result
    orchestrator.run.assert_called_once()
    backend.evaluator.evaluate.assert_called_once()
    checkpoint=next(tmp_path.glob('CANDIDATE/*/checkpoint.json'))
    evaluation=checkpoint.parent/'evaluation.json'
    evaluation.write_text(json.dumps({'success':False,'compliant':True}))
    with pytest.raises(MonitorRejected,match='checkpoint mismatch'):backend(call)
