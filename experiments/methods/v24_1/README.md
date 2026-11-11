# v24.1 ALFWorld 实验索引

| 实验 | 状态与材料 |
|---|---|
| [复审配置](alfworld_reviewed_no_review_workers10_20261030_001/README.md) | 四个模块采用 review_02，完成离线验收，仅准备 |
| [官方模型正式训练](alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/README.md) | 六轮、57 道优化题；R06 发布[最终 Skill](alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/results/final_skill.md) |
| [官方首测](alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/results/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001_test134/summary.json) | 121/134 |
| [独立复测](alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/results/v24_1_alfworld_retest134_20261107_231217/summary.json) | 119/134，同一份最终 Skill |

[方法设计](../../../docs/methods/v24_1/README.md) · [逐轮结果与两次 Test 的逐题对照](alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/reports/REPORT.md) · [准备配置复查](v24_1_recheck_20261030_001/results/report.json) · [训练与首测费用估算](v24_1_cost_estimate_20261106/results/v24_1_cost_estimate_20261106.json)

两份配置的 `data/` 是 Test 入口直接读取的题单，官方配置的 `config/campaign.json` 和 `config/runtime.json` 也是 v24.2 的基线输入。两份准备清单仍在实验根目录，供原[联合调度计划](../../automations/alfworld_v24_1_skilladam_20261030_001/plan.json)及其模型切换前的版本读取。联合运行的材料由 v24.1 和 SkillAdam 共用。

各次 Test 的完整回执和轨迹位于本机的 [v24.1 运行归档](../../../artifacts/methods/v24_1/)。历史 JSON 保留当时记录的路径，[路径映射](../canonical-paths.json)可将这些引用定位到现址。
