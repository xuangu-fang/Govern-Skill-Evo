#!/usr/bin/env python3
"""Prepare/check by default. --start is required to execute either experiment."""
import argparse
import inspect
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'external/SkillOpt'))
from alfworld_aligned_common import (EXPERIMENT, actor_command, check, configure_runtime,
                                     read, require, run_batch, write)


def build_adapter(cfg, actor):
    from skillopt.envs.alfworld.adapter import ALFWorldAdapter, ALFWorldBatchRun
    from skillopt.model.openai_compatible_backend import tracker
    canonical = {t['id']: t for split in ('train', 'val', 'test')
                 for t in read(EXPERIMENT / f'splits/{split}/items.json')}

    class CurrentActorAdapter(ALFWorldAdapter):
        def rollout(self, batch, skill_content, out_dir, **kwargs):
            require(isinstance(batch, ALFWorldBatchRun), 'Expected a frozen ALFWorld task batch')
            items = []
            for raw in batch.items or []:
                item = canonical[raw['id']]
                actual = Path(raw['gamefile'])
                if not actual.is_absolute():
                    actual = Path(actor['environment_root']) / actual
                expected = Path(actor['environment_root']) / item['gamefile']
                require(actual.resolve() == expected.resolve(), 'Batch gamefile differs from frozen task')
                items.append(item)
            require(len(items) == batch.env_num, 'Batch task count differs')
            require(bool(skill_content.strip()), 'SkillOpt must start with a real Initial Skill')
            return run_batch(actor, items, skill_content, out_dir, tracker)

    parameters = inspect.signature(ALFWorldAdapter.__init__).parameters
    return CurrentActorAdapter(**{k: v for k, v in cfg.items() if k in parameters})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', nargs='?', choices=['check', 'noskill', 'skillopt'], default='check')
    parser.add_argument('--start', action='store_true', help='Explicitly execute the selected experiment')
    args = parser.parse_args(argv)
    report = check()
    if not args.start:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    require(args.target != 'check', 'Select noskill or skillopt to start')
    actor = read(EXPERIMENT / 'actor.json')
    from skillopt.config import flatten_config, load_config
    cfg = flatten_config(load_config(str(EXPERIMENT / 'skillopt.yaml')))
    no = read(EXPERIMENT / 'noskill.json')
    output = ROOT / (no['output_root'] if args.target == 'noskill' else cfg['out_root'])
    # Fresh runs only: never overwrite a prior run or implicitly restart failed tasks.
    output.mkdir(parents=True, exist_ok=False)
    write(output / 'launch.json', {'target': args.target, 'status': 'starting',
                                 'prepared_manifest': read(EXPERIMENT / 'manifest.json'),
                                 'actor': actor})
    configure_runtime(actor)
    if args.target == 'noskill':
        items = read(EXPERIMENT / no['tasks'])
        results = run_batch(actor, items, None, output)
        success = sum(r['hard'] for r in results)
        write(output / 'summary.json', {'status': 'complete', 'completed': len(results),
                                       'success': success, 'success_rate': success / len(results),
                                       'skill_mode': 'none', 'tasks': results})
    else:
        for key in ('split_dir', 'skill_init', 'out_root'):
            cfg[key] = str(ROOT / cfg[key])
        from skillopt.engine.trainer import ReflACTTrainer
        trainer = ReflACTTrainer(cfg, build_adapter(cfg, actor))
        trainer.train()
    write(output / 'completion.json', {'status': 'complete', 'target': args.target})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
