from pathlib import Path
_ROOT = next(p for p in Path(__file__).resolve().parents if (p/"benchmarks/alfworld").is_dir() and (p/"experiments/methods/v22/23_alfworld57_five_round").is_dir())
__path__.append(str(_ROOT / "experiments/methods/v22/22_reference_consistency/revision/src/skill_evolution"))
__path__.append(str(_ROOT / "experiments/methods/v22/21_memory_contract_minimal/revision/src/skill_evolution"))

for revision in ("20_memory_contract_fix", "17_p1_input", "12_contract_alignment"):
    __path__.append(str(_ROOT / "experiments/methods/v22" / revision / "revision" / 'src/skill_evolution'))
__path__.append(str(_ROOT / 'src/skill_evolution'))
