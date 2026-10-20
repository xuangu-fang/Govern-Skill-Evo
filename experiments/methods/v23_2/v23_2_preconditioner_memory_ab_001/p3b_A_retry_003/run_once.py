"""Third explicitly authorized A retry; reuse unchanged single-attempt runner."""
from pathlib import Path
import importlib.util
E=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("previous_a_runner", E.parent/"p3b_A_retry_001/run_once.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.E=E
if __name__=="__main__":m.run()
