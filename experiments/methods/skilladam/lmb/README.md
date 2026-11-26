# SkillAdam · LiveMathematicianBench

八次历史训练按接入方式归档。各运行页提供冻结配置、检查点、逐轮保留 Skill、逐题评测和原始补测的入口。下表的分母为实际评分题数，所有 Test124 评测原计划均为 124 题。

| 批次 | 运行 | 完成轮次 | 最终 Skill 来源 | 关联 Test124 |
|---|---|---:|---|---|
| v27.5 aligned | [首次](lmb53_skilladam_v27_5_aligned_20261113/README.md) | 5/5 | R04 | 官方 Flash 70/123 |
| v27.5 aligned | [repeat](lmb53_skilladam_v27_5_aligned_repeat_20261114_0234/README.md) | 5/5 | R04 | R04 官方 Flash 16/52，项目版 Flash 补测合并后 42/124。R01 项目版 Flash 44/120 |
| v27.2 feedback | [首次](lmb53_v27_2_feedback_20261107_1848/README.md) | 6/6 | R05 产生，R06 保留 | 补测合并后 54/124 |
| v27.2 feedback | [repeat](lmb53_v27_2_feedback_repeat_20261112_2011/README.md) | 5/6 | R02 | 补测合并后 57/124 |
| 基础接入 | [首轮训练](lmb53_epoch1_20261031_003906/README.md) | 6/6 | R06 | 19/124 |
| 基础接入 | [49,152-token 运行](lmb53_actor49152_20261031_152036/README.md) | 6/6 | R06 | 38/122 |
| 基础接入 | [protocol-aligned](lmb53_protocol_aligned_20261101_205200/README.md) | 6/6 | R06 | R00 初始 Skill 42/121 |
| 基础接入 | [65,536-token 运行](lmb53_actor65536_20261103_115844/README.md) | 6/6 | R04 | 技术续测后 45/124 |

[v27.5 官方 Flash 代表运行](lmb53_skilladam_v27_5_official_flash_20261120_0020/README.md)的三次 DeepSeek Flash 完整评测进入[主对照](../../lmb/README.md)。同一份 R02 Skill 的 GPT‑5.4 mini 专项评测为 **41/124**。

上游发布的 [Best Skill](upstream_test124/skill.md)独立使用 DeepSeek Flash 评测，首测 **65/123**，合并一题补测后 **66/124**。[原始报告](../../../../artifacts/methods/skilladam/lmb/skilladam_lmb_open_source_best_v27_2_test124_20261106_012128/report.json) · [补测合并回执](../../../../artifacts/methods/skilladam/lmb/skilladam_lmb_open_source_best_v27_2_test124_20261106_012128/additional_three/summary.json)

[v27.2 feedback 历史审计](../../../analysis/lmb_skilladam_v27_2_feedback_audit.json) · [早期协议对齐准备记录](../../../../artifacts/benchmarks/livemathematicianbench/skilladam_protocol_aligned_20261101_205200/README.md)

## 离线读回

从仓库根目录执行以下命令，读回八次历史训练及 18 条评测记录。补测前、补测后的覆盖按原始阶段分别核对。验证器检查受测 Skill、Actor、逐题标签和缺题 ID。

```sh
python3 scripts/verification/verify_lmb_skilladam_archive.py
```

[历史索引](history.json) · [归档还原](../../../benchmark_record_refs/README.md) · [主对照离线读回](../../lmb/README.md#离线读回)
