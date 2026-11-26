# SpreadsheetBench 上的 SkillAdam 实验

共归档 11 条训练或准备记录，其中 7 次训练各完成 8 轮，关联 29 次完整评测。早期 8 条记录沿用原来的配置分类。

| 配置 | 实验 ID | 状态 | 已完成轮次 | 证据 |
|---|---|---:|---:|---|
| 共享 Actor | skilladam_spreadsheetbench_v25matched_20261026 | 受阻 | 0 | [配置](shared_actor/skilladam_spreadsheetbench_v25matched_20261026/config/skilladam.json) · [状态记录](shared_actor/skilladam_spreadsheetbench_v25matched_20261026/reports/monitor_state.json) |
| 共享 Actor | skilladam_spreadsheetbench_v25matched_no_task_deadline_20261026 | 用户停止 | 0 | [配置](shared_actor/skilladam_spreadsheetbench_v25matched_no_task_deadline_20261026/config/skilladam.json) · [状态记录](shared_actor/skilladam_spreadsheetbench_v25matched_no_task_deadline_20261026/reports/user_stop.json) |
| 共享 Actor | skilladam_spreadsheetbench_v25matched_exec30_gen6_20261026 | 恢复后停止 | 3 | [配置](shared_actor/skilladam_spreadsheetbench_v25matched_exec30_gen6_20261026/config/skilladam.json) · [状态记录](shared_actor/skilladam_spreadsheetbench_v25matched_exec30_gen6_20261026/reports/outcome.json) |
| 原生重试 | skilladam_spreadsheetbench_native_retry_actor48k_20261029_001 | 仅准备 | 0 | [配置](native_retry/skilladam_spreadsheetbench_native_retry_actor48k_20261029_001/config/skilladam.json) · [状态记录](native_retry/skilladam_spreadsheetbench_native_retry_actor48k_20261029_001/reports/verification.json) |
| 共享 Actor | v25_skilladam_execution_only_actor48k_20261027_001_skilladam | 完成训练 | 8 | [配置](shared_actor/v25_skilladam_execution_only_actor48k_20261027_001_skilladam/config/shared_config.json) · [状态记录](shared_actor/v25_skilladam_execution_only_actor48k_20261027_001_skilladam/results/final_monitor_report.json) |
| 上游 Actor 提示词 | v25_skilladam_upstream_actor_prompt_20261030_001_skilladam | 完成训练 | 8 | [配置](upstream_actor/v25_skilladam_upstream_actor_prompt_20261030_001_skilladam/config/prepared/shared_config.json) · [状态记录](upstream_actor/v25_skilladam_upstream_actor_prompt_20261030_001_skilladam/results/training_complete.json) |
| 对齐 Actor | skilladam_v25_1_actor_aligned_20261030_001 | 完成训练 | 8 | [配置](aligned_actor/skilladam_v25_1_actor_aligned_20261030_001/config/skilladam.json) · [状态记录](aligned_actor/skilladam_v25_1_actor_aligned_20261030_001/results/training_complete.json) |
| 逐步轨迹反馈 | skilladam_spreadsheetbench_v25_5_feedback_20261108_234037 | 完成训练 | 8 | [配置](aligned_actor/skilladam_v25_1_actor_aligned_20261030_001/config/skilladam.json) · [状态记录](trajectory_feedback/skilladam_spreadsheetbench_v25_5_feedback_20261108_234037/results/final_skill.md) |

## 完整评测

所有评测均为 280 题。表中模型和并发数取自当次评测输入。

| 配置 | 评测 | 整题成功 | Actor 模型 | 最大并发 | 材料 |
|---|---|---:|---|---:|---|
| 共享 Actor | 完整 Test | 231/280 | deepseek-v4.1-flash | 4 | [成绩摘要](shared_actor/v25_skilladam_execution_only_actor48k_20261027_001_skilladam/results/spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001_skilladam_test280/summary.json) · [受测 Skill](shared_actor/v25_skilladam_execution_only_actor48k_20261027_001_skilladam/results/spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001_skilladam_test280/evaluated_skill.md) · [逐题终报](../../../../artifacts/methods/skilladam/spreadsheetbench/shared_actor/spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001_skilladam_test280/summary.json) |
| 上游 Actor 提示词 | 完整 Test | 220/280 | deepseek-flash | 4 | [成绩摘要](upstream_actor/v25_skilladam_upstream_actor_prompt_20261030_001_skilladam/results/v25_skilladam_upstream_actor_prompt_20261030_001_skilladam_test280/summary.json) · [受测 Skill](upstream_actor/v25_skilladam_upstream_actor_prompt_20261030_001_skilladam/results/v25_skilladam_upstream_actor_prompt_20261030_001_skilladam_test280/evaluated_skill.md) · [逐题终报](../../../../artifacts/methods/skilladam/spreadsheetbench/upstream_actor/v25_skilladam_upstream_actor_prompt_20261030_001_skilladam_test280/summary.json) |
| 对齐 Actor | 完整 Test | 229/280 | deepseek-flash | 4 | [成绩摘要](aligned_actor/skilladam_v25_1_actor_aligned_20261030_001/results/skilladam_v25_1_actor_aligned_20261030_001_test280/summary.json) · [受测 Skill](aligned_actor/skilladam_v25_1_actor_aligned_20261030_001/results/skilladam_v25_1_actor_aligned_20261030_001_test280/evaluated_skill.md) · [逐题终报](../../../../artifacts/methods/skilladam/spreadsheetbench/aligned_actor/skilladam_v25_1_actor_aligned_20261030_001_test280/summary.json) |
| 对齐 Actor | 同一 Skill 全量复测 | 230/280 | deepseek-flash | 40 | [成绩摘要](aligned_actor/skilladam_v25_1_actor_aligned_20261030_001/results/skilladam_v25_1_actor_aligned_20261030_001_full_40w_20261108_1710/summary.json) · [受测 Skill](aligned_actor/skilladam_v25_1_actor_aligned_20261030_001/results/skilladam_v25_1_actor_aligned_20261030_001_full_40w_20261108_1710/evaluated_skill.md) · [逐题终报](../../../../artifacts/methods/skilladam/spreadsheetbench/aligned_actor/skilladam_v25_1_actor_aligned_20261030_001_full_40w_20261108_1710/summary.json) |
| 逐步轨迹反馈 | 完整 Test | 223/280 | deepseek-flash | 40 | [成绩摘要](trajectory_feedback/skilladam_spreadsheetbench_v25_5_feedback_20261108_234037/results/skilladam_spreadsheetbench_v25_5_feedback_20261108_234037_test280/summary.json) · [受测 Skill](trajectory_feedback/skilladam_spreadsheetbench_v25_5_feedback_20261108_234037/results/skilladam_spreadsheetbench_v25_5_feedback_20261108_234037_test280/evaluated_skill.md) · [逐题终报](../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v25_5_feedback_20261108_234037_test280/summary.json) |

## 复查训练状态

[方法和离线入口](../../../../docs/methods/skilladam/spreadsheetbench/README.md) · [早期八条运行 ID](runs.json)。读回逐题证据需要本机的原始运行和 SpreadsheetBench 共享压缩归档。

## 轨迹反馈训练与逐轮评测

| 训练 | 配置来源 | 本页补充评测 |
|---|---|---:|
| [11 月 8 日](trajectory_feedback/skilladam_spreadsheetbench_v25_5_feedback_20261108_234037/README.md) | 对齐 Actor | 4 |
| [11 月 12 日](trajectory_feedback/skilladam_spreadsheetbench_v25_5_feedback_20261112_201115/README.md) | 复用对齐 Actor，保留 checkpoint 和恢复入口 | 2 |
| [11 月 16 日](trajectory_feedback/skilladam_spreadsheetbench_v41_feedback_20261116_142340/README.md) | 内网 DeepSeek v4.1 Flash | 6 |
| [11 月 20 日](trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/README.md) | 官方 DeepSeek Flash | 12 |

从仓库根目录执行。基础模式核验精选材料。加 `--archive` 时会核对原生轮次、批次绑定、实际受测 Skill 和 8,120 份测试轨迹。

```sh
python3 scripts/runs/skilladam/spreadsheetbench/verify_bundle.py
python3 scripts/runs/skilladam/spreadsheetbench/verify_bundle.py --archive
```

[候选提交清单](checkout_paths.txt)覆盖本基准的精选历史、运行入口和依赖。独立检出中，精选材料校验和挂载后的归档读回均通过。
