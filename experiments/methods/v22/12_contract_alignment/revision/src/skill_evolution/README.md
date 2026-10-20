# 方法源码

`v01/` 至 `v22/` 中实际存在的版本目录保存对应方法实现；没有独立实现的版本不创建空包。文件名暂保留版本后缀，方便搜索和与历史记录对应。

| 目录 | 归属 |
| --- | --- |
| `v01/`—`v15/` | 各版 Autonomous GSE、诊断、门控及试验实现 |
| `v17/` | 经验分组、诊断、编译、编辑、Monitor |
| `v18/` | V18 方法及 benchmark V4 运行适配 |
| `v19/` | 演化、归因、记忆、评审、恢复 |
| `v20/` | V20 运行、分组、问题记忆、融合 |
| `v21/` | V21 证据、理解、记忆消费和更新 |
| `v22/` | 保留[无历史更新](../../docs/methods/v22/NO_HISTORY_ROUND.md)及 [Editor v1／独立 Replay](../../docs/methods/v22/BEHAVIOR_FEEDBACK.md)历史协议；[紧凑学习构造](../../docs/methods/v22/COMPACT_CYCLE.md)组织 Plan、Memory、Fusion、Editor 与执行；新增 [effective_memory／effective_reconciliation／effective_update／consume_fixed_plan](../../docs/methods/v22/FIXED_CONSUMPTION.md)，明确有效认识修订与具体更新决定，并用固定初稿作独立消费检查。新增 [conditional_update／conditional_trial／bounded_evaluation](../../docs/methods/v22/CONDITIONAL_TRIAL.md)，用通用条件化规则、同信息双分支构造和冻结后的独立 Selection 检验更新。最新 [grouped_representation／grouped_update／continual_state](../../docs/methods/v22/CONTINUAL_INTERFACES.md) 提供单主线共享决策来源、整体成功率 Gate 和真实 Parent／Memory 继承，已通过离线测试；[continual_runner／continual_runtime／continual_verify](../../docs/methods/v22/CONTINUAL_RUNNER.md) 已接通两轮主线、预算／冻结及档案核验，默认Actor最多8并行；真实两轮均已发布，第二轮Replay为7/10→8/10、Gate ACCEPT，最后经独立Memory恢复完成共同发布，见[08恢复报告](../../experiments/methods/v22/08_grouped_continual/reports/MEMORY_RECOVERY_REPORT.md)。旧双分支路径仅保留历史，程序通过不等于认识正确或收益已证实 |
| `shared/` | 通用经验表示、诊断格式、演化决策、二维门控及文件定位 |

某版本被后续版本复用时，直接导入原版本包，不复制实现，也不因此把版本专属逻辑改称通用工具。例如 V19 的经验卡实现仍归 V17。

源码在这里；命令入口见 [scripts](../../scripts/README.md)，方法配置见 [experiments/methods](../../experiments/methods/README.md)，测试见 [tests](../../tests/README.md)。

新导入示例：`from src.skill_evolution.v19.campaign_v19 import run_campaign_v19`。旧的顶层模块已移除，不提供旧模块别名。
