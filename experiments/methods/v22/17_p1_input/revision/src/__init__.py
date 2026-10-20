"""P1 overrides, contract-alignment overrides, then shared project source."""
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[6]
_BASE = _ROOT / "experiments/methods/v22/12_contract_alignment/revision"
__path__.extend([str(_BASE / "src"), str(_ROOT / "src")])
