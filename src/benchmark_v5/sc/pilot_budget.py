"""User-authorized 16K output budget rerun; original 8K trials remain immutable."""
import argparse
from unittest.mock import patch
from benchmark_v5.core import ROOT
from benchmark_v5.calibration.runner import read, write, sha, now
from . import pilot

DEST = ROOT/'artifacts/benchmarks/v5/sc-engineering-20261011-003'
PARENT = ROOT/'artifacts/benchmarks/v5/sc-engineering-20261011-002'
ORIGINAL_CONFIG = pilot.config


def budget_config():
    cfg = ORIGINAL_CONFIG()
    cfg['reasoning_effort'] = 'low'
    cfg['limits']['max_tokens_per_call'] = 16384
    cfg['classification'] = 'engineering_only_16k_output_rerun_no_final_test'
    return cfg


def run_action(action):
    with patch.object(pilot, 'DEST', DEST), patch.object(pilot, 'config', budget_config):
        if action == 'freeze':
            if DEST.exists():
                raise RuntimeError('RERUN_DESTINATION_ALREADY_EXISTS')
            protected = read(PARENT/'protected_before.json')
            for p in PARENT.rglob('*'):
                if p.is_file():
                    protected[str(p.relative_to(ROOT))] = sha(p)
            for p in (ROOT/'docs').glob('BENCHMARK_V5*.md'):
                protected[str(p.relative_to(ROOT))] = sha(p)
            write(DEST/'protected_before.json', protected)
            pilot.freeze()
            f = read(DEST/'freeze.json')
            doc = 'docs/benchmarks/v5/SC.md'
            f['source_sha256'][doc] = sha(ROOT/doc)
            f['parent_interrupted_run'] = str(PARENT.relative_to(ROOT))
            f['authorization'] = 'User requested raising the 8192 output cap and completing S0 to S1 to S2.'
            write(DEST/'freeze.json', f)
        else:
            try:
                getattr(pilot, action)()
            except Exception as exc:
                if action == 'run':
                    write(DEST/'interruption.json', dict(at_utc=now(),error_type=type(exc).__name__,
                        reason=str(exc),policy='Preserve failure; no silent replacement of results or Skills.'))
                raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze','run','validate'])
    run_action(parser.parse_args().action)
