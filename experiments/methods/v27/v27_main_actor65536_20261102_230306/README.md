# v27_main_actor65536_20261102_230306

6 轮训练使用 53 道优化题。Parent 和 Candidate 共执行 106 题次。保留文本发生变化的轮次为 R01、R04、R05、R06。R06 产生最终 Skill。

[训练配置](config/config.json) · [运行环境](config/runtime.json) · [冻结 Prompt](config/prompts) · [逐轮 Skill](results/skills) · [最终 Skill](results/final_skill.md) · [归档清单](archive.json) · [完整训练](../../../../artifacts/methods/v27/v27_main_actor65536_20261102_230306)

| 评测 | 受测节点 | 答对／已评分 | 计划题数 |
|---|---|---:|---:|
| [49,152-token 测试](../../../../artifacts/methods/v27/v27_main_actor65536_20261102_230306/test_49152/plan.json) | [R06](results/skills/R06.md) | 43/105 | 124 |
| [65,536-token 重新评测](../../../../artifacts/methods/v27/v27_main_actor65536_20261102_230306/test_65536_restart_20261103_v1/evaluation/report.json) | [R06](results/skills/R06.md) | 52/124 | 124 |

49,152-token 测试留下 105 题评分。65,536-token 重新评测覆盖全部 124 题，按新测试回执统计。旧报告对 JSON 编码后的 Skill 字符串取 SHA-256。归档已分别核对该哈希、计划中的 Skill、Markdown 原始字节和 124 份 Actor 回执。旧 `current_run.json` 是历史启动指针，完成状态以测试汇总为准。
