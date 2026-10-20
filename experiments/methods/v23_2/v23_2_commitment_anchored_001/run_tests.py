"""Offline pytest runner; fail any attempted network connection and write locally."""
from pathlib import Path
import socket,sys,json,time
import pytest
E=Path(__file__).resolve().parent;ROOT=E.parents[3];sys.path.insert(0,str(E));sys.path.insert(0,str(ROOT))
attempts=[]
def deny(*args,**kwargs):
 attempts.append('blocked_network');raise AssertionError('Network prohibited in offline prototype tests')
socket.socket.connect=deny;socket.socket.connect_ex=deny;socket.create_connection=deny
class Results:
 def __init__(self):self.cases=[]
 def pytest_runtest_logreport(self,report):
  if report.when=='call' or report.failed:self.cases.append({'id':report.nodeid,'phase':report.when,'outcome':report.outcome,'seconds':report.duration,'error':str(report.longrepr) if report.failed else None})
plugin=Results();start=time.monotonic()
args=['-q','-p','no:cacheprovider','--basetemp',str(E/'results/pytest_tmp'),str(E/'tests/test_anchored.py'),'tests/skill_evolution/v23/test_preconditioner.py','tests/skill_evolution/v23/test_editor.py::test_input_exact_parent_plan_context_and_checks','tests/skill_evolution/v23/test_editor.py::test_real_archives_handoff_readonly']
code=pytest.main(args,plugins=[plugin]);result={'exit_code':int(code),'seconds':time.monotonic()-start,'command_arguments':args,'cases':plugin.cases,'network_attempts':attempts,'new_model_calls':0,'new_tokens':0,'environment_calls':0,'note':'Regression generators are local mocks; no stage/API/episode execution.'}
(E/'results/tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
raise SystemExit(int(code) or int(bool(attempts)))
