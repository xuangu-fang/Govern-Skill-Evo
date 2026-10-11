import json
from collections import Counter

import pytest

from scripts import run_v18_compiler_pilot as pilot
from src.skill_evolution.compiler_v18 import compile_edit_plan
from src.skill_evolution.compiler_validation_v18 import validate_edit_plan


def test_all_five_pilot_outputs_compile_without_semantic_filtering():
    values = pilot.replay_inputs()
    assert len(values) == 5
    operations = Counter()
    for key, data in values:
        plan = compile_edit_plan(data)
        validate_edit_plan(plan, compiler_input=data)
        operations.update(u.operation for u in plan.edit_units)
        source = data.diagnoses[0]
        original = pilot.load(pilot.ROOT / 'artifacts/v18_diagnosis_v2_pilot_001' / key / 'validated_diagnosis.json')
        assert json.loads(source.validated.payload) == original
    assert operations == {'ADD': 4, 'REPLACE': 1, 'DELETE': 1}


def test_pilot_rejects_source_drift(tmp_path, monkeypatch):
    manifest = pilot.load(pilot.MANIFEST)
    manifest[0]['files_sha256']['response.json'] = '0' * 64
    path = tmp_path / 'sources.json'
    path.write_text(json.dumps(manifest))
    monkeypatch.setattr(pilot, 'MANIFEST', path)
    with pytest.raises(ValueError, match='Pilot source changed'):
        pilot.replay_inputs()
