"""Compatibility entry for the former Step 5 supplement, now a formal run."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from scripts.runs.skillopt.searchqa.run import main

if __name__ == '__main__':
    if 'train' in sys.argv[1:] and '--from-step5' not in sys.argv:
        sys.argv.append('--from-step5')
    main()
