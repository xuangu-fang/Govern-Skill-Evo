"""One bounded engineering restart with low reasoning; preserve the interrupted high run."""
import argparse
from unittest.mock import patch
from benchmark_v5.core import ROOT
from benchmark_v5.calibration.runner import read, write, sha
from . import pilot

DEST = ROOT/'artifacts/benchmarks/v5/sc-engineering-20261011-002'
PARENT = pilot.DEST
ORIGINAL_CONFIG = pilot.config


def low_config():
    cfg = ORIGINAL_CONFIG()
    cfg['reasoning_effort'] = 'low'
    cfg['classification'] = 'engineering_only_low_reasoning_restart_no_final_test'
    return cfg


def run_action(action):
    with patch.object(pilot, 'DEST', DEST), patch.object(pilot, 'config', low_config):
        if action == 'freeze':
            if DEST.exists():
                raise RuntimeError('RESTART_DESTINATION_ALREADY_EXISTS')
            protected = read(PARENT/'protected_before.json')
            for p in PARENT.rglob('*'):
                if p.is_file():
                    protected[str(p.relative_to(ROOT))] = sha(p)
            write(DEST/'protected_before.json', protected)
            pilot.freeze()
            f = read(DEST/'freeze.json')
            doc = 'docs/benchmarks/v5/SC.md'
            f['source_sha256'][doc] = sha(ROOT/doc)
            f['parent_interrupted_run'] = str(PARENT.relative_to(ROOT))
            write(DEST/'freeze.json', f)
        else:
            try:
                getattr(pilot, action)()
            except Exception as exc:
                if action == 'run':
                    write(DEST/'interruption.json', dict(error_type=type(exc).__name__, reason=str(exc),
                        policy='Final bounded engineering attempt; no further model calls.'))
                raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze','run','validate'])
    run_action(parser.parse_args().action)
