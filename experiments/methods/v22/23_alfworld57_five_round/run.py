from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "revision"))
from src.skill_evolution.v22.continual_runner import main
if __name__ == "__main__":
    raise SystemExit(main())
