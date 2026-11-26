# SpreadsheetBench v25 原版实验记录

10 条训练或准备记录中，3 条完成 8 轮训练并各有一次 280 题测试。记录按训练来源绑定最终 Skill、实际受测文本和测试输入。

| 实验 ID | 状态 | 已发布轮次 | 配置与证据 |
|---|---|---:|---|
| v25_full120_exec30_gen6_actor32k_w4_20261026_004 | 停止／未完成 | 0 | [配置](v25_full120_exec30_gen6_actor32k_w4_20261026_004/config/config.json) · [状态证据](v25_full120_exec30_gen6_actor32k_w4_20261026_004/reports/stop.json) · [完整运行](../../../artifacts/methods/v25/v25_full120_exec30_gen6_actor32k_w4_20261026_004) |
| v25_full120_no_task_deadline_actor32k_w4_20261026_003 | 停止／未完成 | 0 | [配置](v25_full120_no_task_deadline_actor32k_w4_20261026_003/config/config.json) · [状态证据](v25_full120_no_task_deadline_actor32k_w4_20261026_003/reports/user_stop.json) · [完整运行](../../../artifacts/methods/v25/v25_full120_no_task_deadline_actor32k_w4_20261026_003) |
| v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001 | 完成训练 | 8 | [配置](v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001/config/config.json) · [状态证据](v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001/results/result.json) · [完整运行](../../../artifacts/methods/v25/v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001) |
| v25_full120_precondv2_batch15_exec30_gen6_actor32k_w4_20261026_006 | 停止／未完成 | 2 | [配置](v25_full120_precondv2_batch15_exec30_gen6_actor32k_w4_20261026_006/config/config.json) · [状态证据](v25_full120_precondv2_batch15_exec30_gen6_actor32k_w4_20261026_006/reports/stop.json) · [完整运行](../../../artifacts/methods/v25/v25_full120_precondv2_batch15_exec30_gen6_actor32k_w4_20261026_006) |
| v25_full120_precondv3_batch15_exec30_gen6_actor32k_w4_20261026_007 | 停止／未完成 | 7 | [配置](v25_full120_precondv3_batch15_exec30_gen6_actor32k_w4_20261026_007/config/config.json) · [状态证据](v25_full120_precondv3_batch15_exec30_gen6_actor32k_w4_20261026_007/reports/stop.json) · [完整运行](../../../artifacts/methods/v25/v25_full120_precondv3_batch15_exec30_gen6_actor32k_w4_20261026_007) |
| v25_full120_timeline_actor32k_w4_20261026_002 | 停止／未完成 | 1 | [配置](v25_full120_timeline_actor32k_w4_20261026_002/config/config.json) · [状态证据](v25_full120_timeline_actor32k_w4_20261026_002/reports/stop.json) · [完整运行](../../../artifacts/methods/v25/v25_full120_timeline_actor32k_w4_20261026_002) |
| v25_first15_001 | pilot 中断 | 0 | [配置](v25_first15_001/config/candidate_config.json) · [状态证据](v25_first15_001/reports/stop.json) · [完整运行](../../../artifacts/methods/v25/v25_first15_001) |
| v25_two_round_exploration_20261028_001 | 探索中断 | 1 | [配置](v25_two_round_exploration_20261028_001/config/config.json) · [状态证据](v25_two_round_exploration_20261028_001/reports/summary.json) · [完整运行](../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001) |
| v25_skilladam_execution_only_actor48k_20261027_001_v25 | 完成训练 | 8 | [配置](v25_skilladam_execution_only_actor48k_20261027_001_v25/config/config.json) · [状态证据](v25_skilladam_execution_only_actor48k_20261027_001_v25/results/final_monitor_report.json) · [完整运行](../../../artifacts/methods/v25/v25_skilladam_execution_only_actor48k_20261027_001_v25) |
| v25_skilladam_upstream_actor_prompt_20261030_001_v25 | 完成训练 | 8 | [配置](v25_skilladam_upstream_actor_prompt_20261030_001_v25/config/prepared/config.json) · [状态证据](v25_skilladam_upstream_actor_prompt_20261030_001_v25/results/training_complete.json) · [完整运行](../../../artifacts/methods/v25/v25_skilladam_upstream_actor_prompt_20261030_001_v25) |

## 完整评测

| 训练来源 | 整题成功 | 成功率 | 材料 |
|---|---:|---:|---|
| execution-only Actor | 224/280 | 80.00% | [摘要](v25_skilladam_execution_only_actor48k_20261027_001_v25/results/spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001_v25_test280/summary.json) · [受测 Skill](v25_skilladam_execution_only_actor48k_20261027_001_v25/results/spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001_v25_test280/evaluated_skill.md) · [逐题终报](../../../artifacts/methods/v25/spreadsheetbench_full280_skilladam_compat_actor48k_20261027_001_v25_test280/summary.json) |
| 上游 Actor 提示词（定时运行） | 219/280 | 78.21% | [摘要](v25_skilladam_upstream_actor_prompt_20261030_001_v25/results/v25_skilladam_upstream_actor_prompt_20261030_001_v25_test280/summary.json) · [受测 Skill](v25_skilladam_upstream_actor_prompt_20261030_001_v25/results/v25_skilladam_upstream_actor_prompt_20261030_001_v25_test280/evaluated_skill.md) · [逐题终报](../../../artifacts/methods/v25/v25_skilladam_upstream_actor_prompt_20261030_001_v25_test280/summary.json) |
| 官方线路 R08 | 237/280 | 84.64% | [摘要](v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001/results/v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001_test280/summary.json) · [受测 Skill](v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001/results/v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001_test280/evaluated_skill.md) · [逐题终报](../../../artifacts/methods/v25/v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001_test280/summary.json) |

## 其他实验材料

[方法、入口与离线命令](../../../docs/methods/v25/README.md) · [历史配置](configurations/) · [候选原始材料](../../../artifacts/methods/v25/candidates) · [离线检查原件](../../../artifacts/methods/v25/offline) · [分析原件](../../../artifacts/methods/v25/analysis)

| 分析或验收材料 | 精选记录 |
|---|---|
| batch10_input_size_20261026 | [REPORT.md](batch10_input_size_20261026/reports/REPORT.md) · [report.json](batch10_input_size_20261026/results/report.json) |
| diagnosis_fallback_newdefaults_20261027_001 | [README.md](diagnosis_fallback_newdefaults_20261027_001/reports/README.md) |
| diagnosis_fallback_validation_20261027_001 | [README.md](diagnosis_fallback_validation_20261027_001/reports/README.md) |
| diagnosis_v5_r05_r06_20261028_001 | [README.md](diagnosis_v5_r05_r06_20261028_001/reports/README.md) |
| first_launch_alignment_20261026 | [REPORT.md](first_launch_alignment_20261026/reports/REPORT.md) · [report.json](first_launch_alignment_20261026/results/report.json) |
| first_round_module_review_20261026 | [REPORT.md](first_round_module_review_20261026/reports/REPORT.md) · [report.json](first_round_module_review_20261026/results/report.json) |
| fixed_module_validation4_20261027_001 | [README.md](fixed_module_validation4_20261027_001/reports/README.md) · [REPORT.md](fixed_module_validation4_20261027_001/reports/REPORT.md) |
| glm53_r05_r06_20261028_001 | [README.md](glm53_r05_r06_20261028_001/reports/README.md) |
| interrupted_timeline_audit_20261026 | [REPORT.md](interrupted_timeline_audit_20261026/reports/REPORT.md) · [report.json](interrupted_timeline_audit_20261026/results/report.json) |
| preconditioner_clean_r05_feedback_r06_20261028_001 | [README.md](preconditioner_clean_r05_feedback_r06_20261028_001/reports/README.md) |
| preconditioner_v7_deepseek_r05_r06_20261028_001 | [README.md](preconditioner_v7_deepseek_r05_r06_20261028_001/reports/README.md) |
| preconditioner_v8_deepseek_r05_r06_clean_20261028_001 | [README.md](preconditioner_v8_deepseek_r05_r06_clean_20261028_001/reports/README.md) |
| r01_six_changed_tasks_offline_20261027_001 | [REPORT.md](r01_six_changed_tasks_offline_20261027_001/reports/REPORT.md) |
| replay_code_duplication_audit_20261028_001 | [README.md](replay_code_duplication_audit_20261028_001/reports/README.md) |
| replay_comparison_diagnostic_20261028_001 | [README.md](replay_comparison_diagnostic_20261028_001/reports/README.md) |
| replay_evidence_revision_20261026_001 | [README.md](replay_evidence_revision_20261026_001/reports/README.md) |
| replay_evidence_revision_replay_20261026_001 | [README.md](replay_evidence_revision_replay_20261026_001/reports/README.md) |
| replay_exact_code_v4_offline_20261028_001 | [README.md](replay_exact_code_v4_offline_20261028_001/reports/README.md) |
| replay_existing_review_chain_20261027_001 | [README.md](replay_existing_review_chain_20261027_001/reports/README.md) |
| replay_local_revision_proposal_20261028_001 | [README.md](replay_local_revision_proposal_20261028_001/reports/README.md) |
| replay_local_revision_screen_20261028_001 | [README.md](replay_local_revision_screen_20261028_001/reports/README.md) |
| replay_memory_r05_r06_audit_20261028_001 | [README.md](replay_memory_r05_r06_audit_20261028_001/reports/README.md) |
| replay_paired_view_v2_offline_20261028_001 | [README.md](replay_paired_view_v2_offline_20261028_001/reports/README.md) |
| replay_prompt_v2_offline_20261028_001 | [README.md](replay_prompt_v2_offline_20261028_001/reports/README.md) |
| replay_prompt_v3_offline_20261028_001 | [README.md](replay_prompt_v3_offline_20261028_001/reports/README.md) |
| replay_prompt_v4_offline_20261028_001 | [README.md](replay_prompt_v4_offline_20261028_001/reports/README.md) |
| replay_shared_initial_v3_offline_20261028_001 | [README.md](replay_shared_initial_v3_offline_20261028_001/reports/README.md) |
| replay_single_pair_diagnostic_20261028_001 | [README.md](replay_single_pair_diagnostic_20261028_001/reports/README.md) |
| replay_v2_deepseek_r05_r06_clean_20261028_001 | [README.md](replay_v2_deepseek_r05_r06_clean_20261028_001/reports/README.md) |
| replay_v3_deepseek_r05_r06_clean_20261028_001 | [README.md](replay_v3_deepseek_r05_r06_clean_20261028_001/reports/README.md) |
| replay_view_v4_deepseek_r05_r06_clean_20261028_001 | [README.md](replay_view_v4_deepseek_r05_r06_clean_20261028_001/reports/README.md) |
| terra_r05_r06_20261028_001 | [README.md](terra_r05_r06_20261028_001/reports/README.md) |
| timeline_first15_001 | [REPORT.md](timeline_first15_001/reports/REPORT.md) · [report.json](timeline_first15_001/results/report.json) |
| v25_closed_loop_live_20261028_001 | [README.md](v25_closed_loop_live_20261028_001/reports/README.md) |
| v25_closed_loop_preflight_20261028_001 | [README.md](v25_closed_loop_preflight_20261028_001/reports/README.md) |
| v25_spreadsheetbench_rc1_001 | [result.json](v25_spreadsheetbench_rc1_001/results/result.json) |
| v25_spreadsheetbench_rc1_002 | [result.json](v25_spreadsheetbench_rc1_002/results/result.json) |
| v25_spreadsheetbench_rc1_003 | [result.json](v25_spreadsheetbench_rc1_003/results/result.json) |
| v25_spreadsheetbench_rc1_004 | [result.json](v25_spreadsheetbench_rc1_004/results/result.json) |
| v25_spreadsheetbench_verified400_rc1 | [README.md](v25_spreadsheetbench_verified400_rc1/reports/README.md) |
| verifier_prefix_sharing_20261026_001 | [REPORT.md](verifier_prefix_sharing_20261026_001/reports/REPORT.md) · [report.json](verifier_prefix_sharing_20261026_001/results/report.json) |

## 逐轮 Skill

三次完成训练的记录均附 R00–R08 保留 Skill 与历史来源。可运行 `python scripts/runs/v25/verify_bundle.py --archive` 读回压缩归档中的原始发布和测试轨迹。

[v25–v25.5 候选提交清单](checkout_paths.txt)覆盖早期版本的精选实验、源码、读取入口和依赖。独立检出先验证精选材料，挂载原始目录后验证 10 次完整评测与 v25.4 两次专项，共 2,814 条轨迹。v25.1 和 v25.2 的准备入口、v25.3 和 v25.4 的 Docker 预检均通过。v25.5 的提示词及工作簿专项验收使用 v25.4 历史现场，挂载归档后通过。
