"""Separate 65k Actor baseline with v27.2 per-task training feedback."""
import argparse
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]

from src.adapters import lmb_skilladam_feedback as feedback
from src.adapters.lmb import skilladam as base
from src.skill_evolution.v27_1.lmb import protocol as reference

CONFIG = ROOT / 'experiments/configs/lmb_skilladam53_v27_2_feedback.json'


@contextmanager
def actor_profile():
    # The legacy LMB backend reads this module binding during requests and
    # recovery. Scope the 65k profile to this standalone command.
    previous = base.p.ACTOR
    base.require({**previous, 'max_tokens': 65536} == reference.ACTOR, 'Actor profile drift')
    base.p.ACTOR = reference.ACTOR.copy()
    try:
        yield
    finally:
        base.p.ACTOR = previous


def prepare():
    cfg, dataset, initial, native, context, snapshot = base.prepare(CONFIG)
    base.require(cfg['training_feedback'] == 'v27_2_diagnosis', 'Unexpected feedback mode')
    sources = {Path(__file__).resolve(), Path(feedback.__file__).resolve()}
    sources.update(ROOT / 'src/skill_evolution/v28' / name
                   for name in ('validation.py', 'storage.py', 'output_feedback.py'))
    for package in ('v27_1', 'v27_2'):
        sources.update((ROOT / 'src/skill_evolution' / package).rglob('*.py'))
    snapshot['sources'].update({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sources})
    return cfg, dataset, initial, native, context, snapshot


def run(output, resume):
    from dotenv import load_dotenv
    cfg, dataset, initial, native, context, snapshot = prepare()
    root = Path(output).resolve()
    allowed = ROOT / 'experiments/baselines/lmb_skilladam'
    base.require(root.is_relative_to(allowed) and root != allowed, 'Use a dedicated baseline directory')
    with base.locked(root):
        frozen = root / 'frozen.json'
        base.require(frozen.exists() == resume, 'Resume requires an existing aligned run')
        base.freeze(frozen, snapshot)
        load_dotenv(ROOT / '.env', override=False)
        generation = base.generation_transport(cfg, dataset, context, root / 'native', environ=os.environ)
        key = os.environ[cfg['optimizer']['backend_config']['api_key_env']]
        backend = base.Backend(dataset, base.ChatTransport(key), generation, context, root / 'rollouts', snapshot)
        runner = feedback.FeedbackRunner(config=native, adapter=base.NativeAdapter(dataset.root),
                                         backend=backend, context=context, output_dir=root / 'native')
        return runner.run(cases=base.native_cases(dataset), initial_skill=initial, resume=resume)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('preflight', 'run'), nargs='?', default='preflight')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if Path(sys.prefix).name != 'LiveMathematicianBench':
        parser.error('Use the independent LiveMathematicianBench environment')
    with actor_profile():
        if args.command == 'run':
            if args.output is None:
                parser.error('run requires --output')
            run(args.output, args.resume)
        else:
            prepare()
            print('v27.2 feedback configuration verified offline')
