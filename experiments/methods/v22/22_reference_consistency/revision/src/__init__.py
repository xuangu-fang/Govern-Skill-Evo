from pathlib import Path
_ROOT = next(p for p in Path(__file__).resolve().parents if (p/"experiments/methods/v22/21_memory_contract_minimal/revision").is_dir())
_BASE = _ROOT / "experiments/methods/v22/21_memory_contract_minimal/revision"
__path__.append(str(_BASE / 'src'))

for revision in ("20_memory_contract_fix", "17_p1_input", "12_contract_alignment"):
    __path__.append(str(_ROOT / "experiments/methods/v22" / revision / "revision" / 'src'))
__path__.append(str(_ROOT / 'src'))
