"""Compatibility entry point referenced by the frozen v24 source README."""
from pathlib import Path
from runpy import run_path


if __name__ == '__main__':
    run_path(str(Path(__file__).parent / 'v24' / 'verify_v24_offline.py'), run_name='__main__')
