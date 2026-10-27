"""Reproduce historical failures using pre-P2 modules in memory; no file restoration."""
import contextlib
import json
from pathlib import Path
import sys
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
from experiments.methods.v23_4.archive_io import runtime_root
from src.skill_evolution.v23 import memory, replay

RAW = runtime_root(HERE)

for module in (memory, replay):
    source = (HERE / ('before_' + Path(module.__file__).name)).read_text()
    exec(compile(source, module.__file__, 'exec'), module.__dict__)

from src.skill_evolution.v23 import evolution
baseline_contract = evolution.frozen_contract()
for name in ('memory', 'replay'):
    baseline_contract[f'src/skill_evolution/v23/{name}.py'] = (HERE / f'before_{name}.py').read_text()

import pytest
with patch.object(evolution, 'frozen_contract', return_value=baseline_contract):
    with (RAW / 'pre_p2_failures.log').open('w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        code = pytest.main(['-q', '-p', 'no:cacheprovider',
            'tests/skill_evolution/v23/test_formal_evaluation.py',
            'tests/skill_evolution/v23/test_gate.py::test_real_archive_handoff_and_protection',
            '--junitxml=' + str(RAW / 'pre_p2_failures.xml')])
xml = ET.parse(RAW / 'pre_p2_failures.xml')
failed = [c.attrib['classname'] + '.' + c.attrib['name'] for c in xml.iter('testcase')
          if c.find('failure') is not None or c.find('error') is not None]
result = {'exit_code': int(code), 'failed_or_error_tests': failed,
          'method': 'Pre-P2 module source executed in memory; frozen_contract uses pre-P2 source strings. Disk source and historical archives unchanged.'}
(HERE / 'pre_p2_failures.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'exit_code': int(code), 'failed_or_error_count': len(failed)}))
