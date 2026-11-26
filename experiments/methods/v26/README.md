# OfficeQA v26

| 实验 | 状态 |
| --- | --- |
| [pilot10_deepseek_flash_20261029_001](pilot10_deepseek_flash_20261029_001/README.md) | 中止 |
| [pilot10_deepseek_flash_20261029_002](pilot10_deepseek_flash_20261029_002/README.md) | 完成 Pilot |
| [v26_officeqa_official_train74_epoch1_20261029_230230](v26_officeqa_official_train74_epoch1_20261029_230230/README.md) | 完成训练 |
| [v26_officeqa_train74_epoch1_deepseek_flash_corrected_v2_20261029_001](v26_officeqa_train74_epoch1_deepseek_flash_corrected_v2_20261029_001/README.md) | 中止 |
| [v26_officeqa_train74_epoch1_uid0007_65536_20261029_002](v26_officeqa_train74_epoch1_uid0007_65536_20261029_002/README.md) | 完成训练 |

[v26_officeqa_initial_skill.md](profiles/v26_officeqa_initial_skill.md) · [v26_officeqa_pilot10_deepseek_flash.json](profiles/v26_officeqa_pilot10_deepseek_flash.json) · [v26_officeqa_train74_epoch1_deepseek_flash.json](profiles/v26_officeqa_train74_epoch1_deepseek_flash.json) · [v26_officeqa_training_selection.json](profiles/v26_officeqa_training_selection.json)

在仓库根目录运行。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --manifest experiments/benchmarks/officeqa/v26-remaining.json --method v26
```
