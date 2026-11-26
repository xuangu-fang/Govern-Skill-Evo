#!/usr/bin/env python3
"""Prepare/check a paired V25 + SkillAdam configuration; never launch training."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts/runs')]
from scripts.runs.skilladam.spreadsheetbench.shared_actor import run_skilladam_spreadsheetbench_aligned as bridge
from src.skill_evolution.v25 import baseline, evolution as ev
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter

DEFAULT_TEMPLATE=ROOT/'experiments/methods/skilladam/spreadsheetbench/shared_actor/skilladam_spreadsheetbench_v25matched_exec30_gen6_20261026/config/skilladam.json'


def relative(path):return os.path.relpath(Path(path).resolve(),ROOT)


def check_pair(output):
    output=Path(output).resolve();v25=output/'v25/config';skilladam=output/'skilladam'
    shared=bridge.read(v25/'campaign.json');cfg=bridge.read(skilladam/'skilladam.json')
    baseline.validate_latest_configuration(shared)
    bridge.require(cfg.get('comparison_profile')==baseline.COMPARISON_PROFILE,'Missing paired comparison profile')
    bridge.require((ROOT/cfg['reference_preparation']).resolve()==v25,'SkillAdam references a different preparation')
    with using_benchmark(SpreadsheetBenchAdapter()):ev.validate_config(shared)
    report=bridge.check(skilladam)
    return {**report,'comparison_profile':baseline.COMPARISON_PROFILE,
            'training_artifacts_present':(output/'v25/campaign').exists() or (skilladam/'campaign').exists(),
            'v25_config':str(v25/'campaign.json'),'skilladam_config':str(skilladam/'skilladam.json'),
            'v25_module_tokens':{name:ev.stage_call_config(shared,name)['max_tokens'] for name in ev.enabled_modules(shared)}}


def prepare_pair(output, *, template=DEFAULT_TEMPLATE):
    output=Path(output).resolve();template=Path(template).resolve()
    bridge.require(not output.exists(),'Comparison preparation requires a new directory')
    source=bridge.read(template)
    output.mkdir(parents=True)
    baseline.prepare(output/'v25')
    v25=output/'v25/config';shared=bridge.read(v25/'campaign.json')
    baseline.validate_latest_configuration(shared)
    with using_benchmark(SpreadsheetBenchAdapter()):
        ev.validate_config(shared)
        contract=ev.frozen_contract()
        runtime=ev.runtime_snapshot(shared)
    bridge.write(v25/'contract.json',contract);bridge.write(v25/'runtime.json',runtime)

    # Preserve every native method setting. Only bind the same task pool and environment.
    cfg=deepcopy(source)
    cfg.pop('reference_campaign',None)
    cfg.update(comparison_profile=baseline.COMPARISON_PROFILE,actor_evidence_view='execution_only_v1',
               reference_preparation=relative(v25),python=sys.executable,
               not_before=datetime.now(timezone.utc).isoformat())
    ids=[task for batch in shared['batches'] for task in batch]
    bridge.require(cfg['native']['optimization_case_ids']==ids,'Native template task order differs')
    bridge.require(cfg['optimizer_transport']['max_tokens']==16384,'Native optimizer budget differs')
    bridge.require(cfg['native']['trajectory_compression']=='llm' and cfg['native']['optimizer_context_limit']==96000,
                   'Native compression settings differ')
    bridge.validate_actor_protocol(shared,cfg)
    directory=output/'skilladam'
    bridge.write(directory/'shared_config.json',shared);bridge.write(directory/'skilladam.json',cfg)
    (directory/'initial_skill.md').write_text(shared['initial_skill']['text'])

    # Freeze sources, paired configs and dataset files. No request, Skill optimization or task execution.
    files={ROOT/p for p in contract}
    files.update(p for p in (bridge.UPSTREAM/'skilladam').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    files.update({Path(__file__).resolve(),Path(bridge.__file__).resolve(),template})
    files.update(p for p in output.rglob('*') if p.is_file())
    files.update(Path(t[k]) for t in shared['task_items'].values() for k in ('input_path','answer_path'))
    image=bridge.subprocess.check_output(['docker','image','inspect',shared['executor']['image'],'--format','{{.Id}}'],text=True).strip()
    manifest={'version':'paired_comparison_v1','comparison_profile':baseline.COMPARISON_PROFILE,
              'python_version':sys.version,'python_executable':sys.executable,'docker_image_id':image,
              'packages':{name:importlib.metadata.version(name) for name in ('openpyxl','pandas','numpy','requests','python-dotenv')},
              'files':{relative(p):bridge.sha(p) for p in sorted(files)},
              'created_at':datetime.now(timezone.utc).isoformat()}
    bridge.write(directory/'manifest.json',manifest)
    report=check_pair(output)
    bridge.write(output/'preflight.json',report)
    bridge.write(output/'alignment.json',{'comparison_profile':baseline.COMPARISON_PROFILE,
        'shared_config_sha256':bridge.sha(directory/'shared_config.json'),
        'v25_config_sha256':bridge.sha(v25/'campaign.json'),'native_template':str(template),
        'native_method_settings_unchanged':cfg['native']==source['native'],
        'optimizer_transport_unchanged':cfg['optimizer_transport']==source['optimizer_transport'],
        'actor_evidence_view':cfg['actor_evidence_view'],'model_requests':0,'dataset_tasks_executed':0})
    (output/'README.md').write_text(
        '# Prepared V25 / SkillAdam comparison\n\n'
        'Configuration only. No campaign, model request, training or Test was started.\n'
        'Both methods share execution_only_v1, 4 workers, 49152 Actor tokens, 30 executions, '
        '6 requests per program, no cumulative task deadline, and the original 8 x 15 task order.\n'
        'SkillAdam native optimizer/compression/Momentum/Gate settings are preserved.\n'
        'Recheck before any separately authorized launch:\n\n'
        f'`{sys.executable} scripts/runs/prepare_spreadsheetbench_comparison.py --output {output} --check`\n\n'
        'V25 configuration: `v25/config/campaign.json`; future campaign directory: `v25/campaign` (not created).\n'
        'SkillAdam experiment directory: `skilladam`; its campaign directory is not created.\n'
        'Source/config/runtime drift must fail preflight; do not rewrite freezes to bypass it.\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--skilladam-template',type=Path,default=DEFAULT_TEMPLATE)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    report=check_pair(args.output) if args.check else prepare_pair(args.output,template=args.skilladam_template)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
