from pathlib import Path

_ROOT = next(p for p in Path(__file__).resolve().parents
             if (p / "experiments/methods/v22").is_dir())
for revision in ('20_memory_contract_fix', '17_p1_input', '12_contract_alignment'):
    __path__.append(str(_ROOT / "experiments/methods/v22" / revision / "revision" / 'tests/skill_evolution/v22'))
__path__.append(str(_ROOT / 'tests/skill_evolution/v22'))
