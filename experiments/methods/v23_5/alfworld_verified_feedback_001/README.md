# V23.5 Memory 核验与 Actor 有限反馈配置

## 2026-10-27 当前材料状态

R01–R06 已完成；最终 Test 为 134 个任务、120 成功、14 失败，成功率 89.55%。

正式 config/、任务 data/ 原样保留；以下结果来自已有文件，本次没有运行实验或测试。

[逐轮汇总](results/round_summary.json) · [优化逐任务指标](results/optimization_task_metrics.json) · [原状态](evidence/S1/state.json) · [停止记录](evidence/S1/stop.json)

| 轮次 | 状态／决策 | Parent / Candidate 成功数 | 原轮次结果 |
|---|---|---|---|
| R01 | RETAIN | 10/10 → 10/10 | [result](evidence/S1/rounds/R01/result.json) |
| R02 | RETAIN | 8/10 → 7/10 | [result](evidence/S1/rounds/R02/result.json) |
| R03 | RETAIN | 7/10 → 6/10 | [result](evidence/S1/rounds/R03/result.json) |
| R04 | ACCEPT | 7/10 → 9/10 | [result](evidence/S1/rounds/R04/result.json) |
| R05 | ACCEPT | 9/10 → 10/10 | [result](evidence/S1/rounds/R05/result.json) |
| R06 | RETAIN | 6/7 → 5/7 | [result](evidence/S1/rounds/R06/result.json) |

[最终 Skill](evidence/S1/rounds/R05/editor/attempts/001/candidate.md)。state 中 active_memory 的完整 commits 仍在原归档，证据区只保留 active 索引、发布候选及对应审计结果，不是可恢复运行目录。

各完成轮次保留 Parent、Editor 候选与实际 Diff、Gate 逐任务配对、Replay 输出；启用知识核验的轮次另保留 Verifier、Repair、knowledge_review 候选。原 result.json 选择路径与原尝试编号保留，未把失败输出改成成功结果。

[最终 Test 汇总及全部 134 条逐任务指标](results/evaluation/summary.json) · [实际评估的 Skill](results/evaluation/final_skill.md) · [14 条失败任务的终态证据](evidence/test_failures.json)。最终 Skill 与状态指向的 R05 Candidate 原文一致；R06 为 RETAIN。SkillOpt 初始成绩是旧协议参考，不能据此宣称同条件提升。

[原 R06 Verifier 停止与恢复](evidence/S1/rounds/R06/verifier/attempts/)保留 001–009；[授权修订](evidence/S1/amendments/verifier_retry_v1/grant.json)将总尝试上限从 6 增至 12、输出上限从 32,768 增至 65,536、超时从 300 增至 600 秒，第 009 次通过。[历史训练完成记录](evidence/S1/amendments/verifier_retry_v1/completion_validation.json)早于 Test，其 test_started=false 是当时状态。旧 stop.json 仍保留，不能据此忽略后来 completed 的 R06 和最终评估。

后续版本的 v24 基线准备（本地 `src/skill_evolution/v24/baseline.py`）仍读取本目录 config/campaign.json、data/、budget 和初始基线说明，以及原 S1/config.json 和 initial_config.json；这些依赖未移动、未改写。v24 源码单独管理，不是读取本目录保留结果的前置条件。

当前通用脚本 [run_v23_5_verified_alfworld.sh](../../../../scripts/runs/run_v23_5_verified_alfworld.sh) 默认指向 alfworld_verified_feedback_001；下方旧入口说明保留历史阶段含义，通用脚本不会自动恢复旧目录。本次未执行任何入口。

[原始归档](../../../../artifacts/methods/v23_5/alfworld_verified_feedback_001/)继续保存完整输入、HTTP、轨迹、Memory、日志及源码快照；研究副本不参与运行恢复或自动更新。仅克隆 Git 不包含这些原始数据。

## 历史说明（保留原阶段记录）

从 `alfworld_verified_memory_001` 派生，仅启用 `actor_action_feedback=true`。
保留原有 Replay → Verifier → 必要时 Repair → Memory 链路及所有模型预算。

Actor 缺少完整 action 标签或提取命令不在列表时，追加最近一次实际失败正文和具体诊断；
技术重试原样保留当前请求。所有请求共用每步六次总额度，未通过校验不推进环境。

`scripts/runs/run_v23_5_verified_alfworld.sh` 默认指向本配置。
已停止的 `alfworld_verified_memory_001` 及其 R03 第 36 步失败记录保持原样。
新目录只完成离线准备，未启动真实请求、训练或 Test；这不是对旧实验的原地续跑。
