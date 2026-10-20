from pathlib import Path

_ROOT = Path(__file__).resolve().parents[6]
__path__.append(str(_ROOT / "tests"))
