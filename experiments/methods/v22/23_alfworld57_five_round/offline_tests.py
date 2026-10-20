"""Run inherited tests against the actual formal overlay, without live calls."""
from pathlib import Path
import os,sys,unittest
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE/'revision'))
# The tests package is inherited from revision 21; its package paths include the
# earlier revisions and project tests.
sys.path.append(str(ROOT/'experiments/methods/v22/21_memory_contract_minimal/revision'))
os.chdir(ROOT)
loader=unittest.TestLoader()
starts=[ROOT/'tests/skill_evolution/v22']
starts += [ROOT/'experiments/methods/v22'/name/'revision/tests/skill_evolution/v22'
           for name in ('12_contract_alignment','17_p1_input','20_memory_contract_fix','21_memory_contract_minimal')]
names={f'tests.skill_evolution.v22.{path.stem}' for start in starts
       for path in start.glob('test_*.py')
       if path.name != 'test_revision_imports.py'}
# Import-wiring tests describe their own historical revision, not this overlay.
suite=loader.loadTestsFromNames(sorted(names))
# Revision 23 intentionally overrides the compact-learning implementation.
# The unchanged-implementation assertion belongs to revisions 20/21 and is
# exercised by both of their complete suites; all behavioral tests still run.
from tests.skill_evolution.v22.test_memory_contract_v5 import ProfileTests
ProfileTests.test_original_algorithm_and_codec_and_validators_identical = unittest.skip(
    "Revision 20/21 identity check; revision 23 intentionally overrides compact learning."
)(ProfileTests.test_original_algorithm_and_codec_and_validators_identical)
result=unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(not result.wasSuccessful())
