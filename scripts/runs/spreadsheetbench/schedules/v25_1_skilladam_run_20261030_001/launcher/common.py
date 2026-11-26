import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[6]
HOME = ROOT / 'experiments/comparisons/v25_1_skilladam_run_20261030_001'
SETTINGS = ROOT / 'experiments/benchmarks/spreadsheetbench/schedules/v25_1_skilladam_run_20261030_001'


def load_settings():
    settings = read(SETTINGS / 'settings.json')
    settings['official_env'] = str(ROOT / settings['official_env'])
    settings['repository'] = str(ROOT)
    settings['python'] = sys.executable
    for info in settings['arms'].values():
        for key in ('folder', 'manifest', 'record'):
            if key in info:
                info[key] = str(ROOT / info[key])
    return settings


def record_folder(info):
    return Path(info.get('record', info['folder']))


def read(path):
    return json.loads(Path(path).read_text())


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)


def now():return datetime.now(timezone.utc).isoformat()


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def require(ok,message):
    if not ok:raise ValueError(message)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def verify():
    settings = load_settings()
    for side, info in settings['arms'].items():
        if side == 'v25_1':
            config = read(Path(info['folder']) / info['config'])
            require(config['method']['preconditioner_prompt'] == 'v25_1_current_update_evidence_to_behavior_v1',
                    'Wrong v25.1 prompt in scheduler configuration')
            continue
        manifest = Path(info['manifest'])
        require(sha(manifest) == info['manifest_sha256'], 'Frozen manifest changed: ' + side)
        for name, digest in read(manifest).items():
            require(sha(record_folder(info) / name) == digest, 'Frozen experiment file changed: ' + name)
        from src.skill_evolution.skilladam.spreadsheetbench.layout import read_actor_config
        from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.binding import components
        _, _, shared, optimizer = components()
        require(shared == read_actor_config(Path(info['folder']) / info['config']), 'Aligned Actor configuration differs')
        require(optimizer['optimizer_retry_policy'] == 'upstream_sdk2_patch3_v1', 'Native retry policy differs')
    return settings


def barrier(settings):
    receipts={}
    for side,info in settings['arms'].items():
        folder=record_folder(info);receipt=read(HOME/side/'validation.json')
        require(receipt['status']=='validated' and receipt['rounds']==8,'Both validated trainings required')
        for name,digest in receipt['files'].items():
            require(sha(folder/name)==digest,'Validated training artifact changed: '+name)
        complete=read(folder/'training_complete.json')
        require(complete['status']=='complete' and complete['rounds']==8,'Incomplete training receipt')
        require(sha(folder/'final_skill.md')==complete['skill_sha256'],'Final Skill hash differs')
        receipts[side]=receipt
    return receipts
