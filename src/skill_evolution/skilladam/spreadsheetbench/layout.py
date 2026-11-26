"""Repository locations for the maintained SpreadsheetBench adapters and their published inputs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
UPSTREAM = ROOT / 'src/skill_evolution/skilladam/upstream'
PUBLISHED = ROOT / 'experiments/methods/skilladam/spreadsheetbench'
ARCHIVE = ROOT / 'artifacts/methods/skilladam/spreadsheetbench'
ALIGNED_CONFIG = ROOT / 'experiments/methods/skilladam/spreadsheetbench/aligned_actor/skilladam_v25_1_actor_aligned_20261030_001/config'
NATIVE_CONFIG = ROOT / 'experiments/methods/skilladam/spreadsheetbench/native_retry/skilladam_spreadsheetbench_native_retry_actor48k_20261029_001/config'
SHARED_CONFIG = ROOT / 'experiments/methods/skilladam/spreadsheetbench/shared_actor/v25_skilladam_execution_only_actor48k_20261027_001_skilladam/config'
UPSTREAM_CONFIG = ROOT / 'experiments/methods/skilladam/spreadsheetbench/upstream_actor/v25_skilladam_upstream_actor_prompt_20261030_001_skilladam/config'
ALIGNED_RECORD = ROOT / 'artifacts/methods/skilladam/spreadsheetbench/aligned_actor/skilladam_v25_1_actor_aligned_20261030_001'
UPSTREAM_RECORD = ROOT / 'artifacts/methods/skilladam/spreadsheetbench/upstream_actor/v25_skilladam_upstream_actor_prompt_20261030_001_skilladam'


def read_actor_config(path):
    """Resolve the recorded Verified-400 workbook locations in this checkout."""
    config = json.loads(Path(path).read_text())
    dataset = 'external/Trace2Skill/data/spreadsheetbench_verified/spreadsheetbench_verified_400/'
    for task in config['task_items'].values():
        for key in ('input_path', 'answer_path'):
            root, marker, name = task[key].partition(dataset)
            if marker and (not root or root.endswith('/')):
                task[key] = str(ROOT / dataset / name)
    return config
