"""Run unchanged inherited tests against the sparse new implementation."""
from pathlib import Path
import sys,unittest
import fixtures as f
kind=sys.argv[1]
folder=f.REVISION/'tests'/('skill_evolution/v22' if kind=='v22' else 'adapters/alfworld')
prefix='tests.skill_evolution.v22.' if kind=='v22' else 'tests.adapters.alfworld.'
names=[prefix+p.stem for p in sorted(folder.glob('test_*.py'))]
suite=unittest.defaultTestLoader.loadTestsFromNames(names)
result=unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
