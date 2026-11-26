"""Disposable, offline Docker program execution. Only input and attempt files mount."""
import json
from pathlib import Path
import shutil
import subprocess
import uuid
import openpyxl


class InfrastructureError(RuntimeError):
    pass


RUNNER = '''import sys
INPUT_PATH = "/work/input.xlsx"
OUTPUT_PATH = "/work/output/result.xlsx"
import openpyxl, pandas

def policy(event, args):
    if event.startswith(("subprocess.", "socket.", "os.exec", "os.spawn")) or event in ("os.system", "os.fork", "os.forkpty"):
        raise PermissionError("Network and external command execution are unavailable")
sys.addaudithook(policy)
with open("/work/program.py") as source:
    code = compile(source.read(), "solution.py", "exec")
exec(code, {"__name__": "__main__", "INPUT_PATH": INPUT_PATH, "OUTPUT_PATH": OUTPUT_PATH})
'''


def runtime_snapshot(config):
    image = config['executor']['image']
    code = 'import sys,json,importlib.metadata as m;print(json.dumps({"python":sys.version,"packages":{n:m.version(n) for n in ["openpyxl","pandas","numpy"]}}))'
    try:
        proc = subprocess.run(['docker','run','--rm','--network','none',image,'python','-c',code], capture_output=True,text=True,timeout=30)
        if proc.returncode: raise InfrastructureError('Docker image/runtime is unavailable')
        return {'backend':'docker', 'image':image, **json.loads(proc.stdout)}
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        raise InfrastructureError('Cannot inspect execution runtime') from exc


def execute(code, input_path, directory, timeout, config):
    directory = Path(directory).resolve(); directory.mkdir(parents=True,exist_ok=True)
    output = directory/'output'; output.mkdir(exist_ok=True); output.chmod(0o777)
    for name, content in [('program.py',code),('runner.py',RUNNER)]:
        (directory/name).write_text(content); (directory/name).chmod(0o644)
    shutil.copyfile(input_path,directory/'input.xlsx'); (directory/'input.xlsx').chmod(0o644)
    name = 'v25-'+uuid.uuid4().hex[:16]
    args = ['docker','run','--rm','--name',name,'--network','none','--read-only',
            '--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','64',
            '--memory',config['executor']['memory'],'--cpus',str(config['executor']['cpus']),
            '--user','65534:65534','--tmpfs','/tmp:rw,nosuid,nodev,size=64m',
            '-e','PYTHONDONTWRITEBYTECODE=1','-e','OPENBLAS_NUM_THREADS=1']
    for filename in ('program.py','runner.py','input.xlsx'):
        args += ['--mount',f'type=bind,src={directory/filename},dst=/work/{filename},readonly']
    args += ['--mount',f'type=bind,src={output},dst=/work/output',config['executor']['image'],'python','/work/runner.py']
    try:
        with (directory/'stdout.txt').open('w') as stdout, (directory/'stderr.txt').open('w') as stderr:
            proc = subprocess.run(args,stdout=stdout,stderr=stderr,timeout=timeout)
        status, exit_status = 'success', proc.returncode
    except subprocess.TimeoutExpired:
        status, exit_status = 'timeout', None
    except OSError as exc:
        raise InfrastructureError('Cannot launch Docker executor') from exc
    finally:
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15)
    stdout=(directory/'stdout.txt').read_text(errors='replace'); stderr=(directory/'stderr.txt').read_text(errors='replace')
    if exit_status in (125,126,127): raise InfrastructureError(f'Execution infrastructure exited {exit_status}')
    result={'status':status,'exit_status':exit_status,'stdout':stdout,'stderr':stderr,'output_openable':False}
    if status=='timeout': return {**result,'error_category':'execution_error','error_detail':'Program execution timed out.\n'+stderr}
    if exit_status != 0: return {**result,'status':'error','error_category':'execution_error','error_detail':stderr or stdout}
    path=output/'result.xlsx'
    # Reject links instead of inspecting a different host file after execution.
    if not path.is_file() or path.is_symlink():
        return {**result,'status':'error','error_category':'output_file_error','error_detail':'Output workbook is missing or is not a regular file'}
    try:
        wb=openpyxl.load_workbook(path); wb.close()
    except Exception:
        return {**result,'status':'error','error_category':'output_file_error','error_detail':'Output workbook cannot be opened as .xlsx'}
    return {**result,'output_openable':True,'output_path':str(path)}
