# V23 验证与实验

[方法实验总索引](../README.md) · [V23 方法设计](../../../docs/methods/v23/README.md)

| 材料 | 范围 |
|---|---|
| [v23_grouping_001](v23_grouping_001/README.md) | Grouping 离线测试、24 条历史轨迹转换、4 条历史 Parent 的一次真实分组调用；零新增环境执行 |
| [v23_diagnosis_001](v23_diagnosis_001/README.md) | Diagnosis 正式实现、175 项测试与 19 个子测试、复用四条 Parent 的一次真实调用及原始 Plan 语义核查；零新增环境执行 |
| [v23_prompt_alignment_001](v23_prompt_alignment_001/README.md) | 当前 Grouping／Diagnosis Prompt 统一、共享背景、update_ids 迁移；210 项测试与 19 个子测试，新 Grouping→Diagnosis 各一次真实调用；旧档案不变 |
| [v23_preconditioner_001](v23_preconditioner_001/README.md) | 增量调整与 Effective Plan 编译；284 项测试及 19 个子测试，memory=[] 单次真实 Keep，零新增上游或环境执行；历史响应尚未验证 |
| [v23_editor_001](v23_editor_001/README.md) | Editor 正式实现及严格 Patch 应用；384 项测试与 19 个子测试通过，单次真实补丁格式失败，未生成 Candidate，无重试或新增环境执行 |
| [v23_editor_recovery_001](v23_editor_recovery_001/README.md) | 用户授权一次相同请求技术恢复；无失败反馈或补丁修补，严格应用成功生成 Candidate，原失败保留，未运行 Replay |
| [v23_replay_memory_001](v23_replay_memory_001/README.md) | Replay／Memory 实现；434 项测试与 19 个子测试；4 条 Candidate、一次 Replay 产生 3 条真实 Memory，完整来源及副作用记录 |
| [v23_preconditioner_with_memory_001](v23_preconditioner_with_memory_001/README.md) | 新 Prompt、同输入的空／真实 Memory 各一次；Keep 对照与 u1/u3 调整，记录同批回看和语义限制，未执行新 Candidate |
| [v23_gate_001](v23_gate_001/README.md) | 确定性 Gate；四组真实配对 Parent 3／Candidate 2，RETAIN；479 项测试与 19 个子测试，零模型调用及新增环境任务 |
| [v23_evolution_001](v23_evolution_001/README.md) | 统一调度、三次尝试、断点恢复、Skill／Memory 原子发布；离线 513 项及 19 个子测试，至多两轮真实验证结果见报告 |

- [v23_alfworld_formal_001](v23_alfworld_formal_001/README.md)：2026-10-19 正式实验数据与配置准备，READY；官方顺序 57 条分六轮，134 Test，No Skill/V23 两组冻结；无真实调用或 Episode。

## 运行产物归属

2026-10-20 整理：保留全部源码、实验源码副本、测试、提示词、配置、
任务与来源清单和现有目录结构；本次不做源码引用去重。
正式 Markdown 报告、精选结果、Candidate、实际修改和失败证据继续保留。
上表保留各阶段说明，正式实验最新状态见其 README 末尾与最终报告。

以下 **23 份生成记录**由根目录 `.gitignore` 按完整路径忽略，
文件仍留在本地原位置：

| 目录 | 本地生成记录 |
|---|---|
| `v23_editor_recovery_001/results/` | `validation.json` |
| `v23_evolution_001/results/` | `offline_tests.txt`、`verification.json` |
| `v23_gate_001/results/` | `tests.txt` |
| `v23_replay_memory_001/results/` | `validation.json` |
| `v23_alfworld_formal_001/reports/` | `input_capacity_preflight.json`、`input_capacity_progress.json`、`input_capacity_resume_check.json` |
| 同上 | `input_capacity_tests.txt`、`input_capacity_tests_final.txt`、`offline_tests.txt` |
| 同上 | `r04_input_capacity_preflight.json`、`r04_input_capacity_tests.txt`、`r04_preservation_start.json`、`r04_preservation_final.json` |
| 同上 | `test_evaluation_initial.txt`、`test_evaluation_regression.txt`、`test_evaluation_regression_final.txt` |
| 同上 | `test_execution_preflight.json`、`test_protection_start.json`、`test_protection_final.json` |
| 同上 | `test_transport_recovery_protection.json`、`test_transport_recovery_regression.txt` |

没有整体忽略 `results/` 或 `reports/`。特别保留：

- Gate 的 `results/verification.json`：包含实际决定和配对结果。
- Editor 的 `results/validation.json`、模型输出和补丁分析：记录真实失败。
- Replay／Memory 的 `results/final_verification.json`：包含调用量、费用与实验边界摘要。
- 正式实验的 `reports/r04_capacity_final_results.json`：包含六轮最终结果。
- 当前代码或测试读取的旧提示词、实验输入及配置清单。

完整请求、响应、轨迹和中间状态继续放在 `artifacts/methods/v23/`，
由已有规则忽略。历史报告中的测试日志、检查记录和原始产物链接仍指向
本地文件；仅获取 Git 源码时，需要另备这些本地材料才能打开它们。
本次未删除本地记录、改写实验结果或执行模型／环境调用。
