# V23.5 实验导航

[方法总索引](../README.md) · [实现与协议](../../../src/skill_evolution/v23_5/README.md) · [测试源码](../../../tests/skill_evolution/v23_5/) · [本机原始归档](../../../artifacts/methods/v23_5/)

本版本共有 24 个实验目录。以下状态依据 2026-10-27 本地已有记录整理；目录存在不代表实验完成。本次整理没有运行实验、测试或项目校验入口。

## 正式 ALFWorld 结果

已完成的正式运行是 [alfworld_verified_feedback_001](alfworld_verified_feedback_001/README.md)：六轮优化完成，最终 Test 为 **134 个任务、120 成功、14 失败（89.55%）**。最终发布 Skill 来自 R05，R06 为 RETAIN。

- [逐轮决策](alfworld_verified_feedback_001/results/round_summary.json)、[优化逐任务指标](alfworld_verified_feedback_001/results/optimization_task_metrics.json)。
- [最终 Test 汇总与全部逐任务指标](alfworld_verified_feedback_001/results/evaluation/summary.json)、[实际评估的 Skill](alfworld_verified_feedback_001/results/evaluation/final_skill.md)、[失败任务终态证据](alfworld_verified_feedback_001/evidence/test_failures.json)。
- R06 Verifier 保留原 001–006 和授权追加 007–009，第 009 次通过。旧停止记录及早于 Test 的完成检查保留其历史含义。

SkillOpt 初始成绩来自不同输出协议，只作历史参考，不能据此宣称同条件提升。

## 1. 输出协议与反馈小实验

| 目录 | 阅读入口与材料边界 |
|---|---|
| action_format_probe_001 | [16 次真实请求对照](action_format_probe_001/README.md)：输出格式、回答和必要失败证据 |
| preconditioner_output_protocol_001 | [Preconditioner 输出协议](preconditioner_output_protocol_001/README.md)：约束与历史验证材料 |
| feedback_smoke_001 | [有限反馈烟雾实验](feedback_smoke_001/README.md)：6 次新调用与 3 份种子证据分别保留 |
| feedback_schema_001 | [Schema 反馈实验](feedback_schema_001/README.md)：1 份导入失败与 2 次新调用，选择 attempt 003 |

## 2. Knowledge Only 单轮对照

[十批实验的详细导航](knowledge_only_single_round_001/README.md)。这些实验使用冻结输入，不能视为连续训练或新的最终 Test。

| 目录 | 独立边界 |
|---|---|
| knowledge_only_single_round_001 | [首批 32k 尝试](knowledge_only_single_round_001/README.md)，停止记录保留 |
| knowledge_only_single_round_002 | [65k 预算对照](knowledge_only_single_round_002/README.md)，与首批分别记录 |
| knowledge_only_single_round_003 | [R03 新 Prompt 对照](knowledge_only_single_round_003/README.md)，原始尝试保留 |
| knowledge_only_single_round_004 | [003 的追加实验之一](knowledge_only_single_round_004/README.md) |
| knowledge_only_single_round_005 | [003 的追加实验之二](knowledge_only_single_round_005/README.md) |
| knowledge_only_single_round_006 | [003 的追加实验之三](knowledge_only_single_round_006/README.md) |
| knowledge_only_single_round_007 | [R04 独立冻结对照](knowledge_only_single_round_007/README.md) |
| knowledge_only_single_round_008 | [R05 独立冻结对照](knowledge_only_single_round_008/README.md) |
| knowledge_only_single_round_009 | [R06 独立冻结对照](knowledge_only_single_round_009/README.md) |
| knowledge_only_single_round_010 | [008 的 R05 Preconditioner 追加尝试](knowledge_only_single_round_010/README.md) |

追加尝试不覆盖原始失败，也不合并改写各批报告。各目录保留候选、有效输出和必要失败证据；完整输入、messages、调用数据和 Memory 仍由原归档读取。

## 3. Verifier 与 Repair

| 目录 | 阅读入口与实际状态 |
|---|---|
| verifier_input_001 | [原始 Verifier 结果](verifier_input_001/evidence/README.md)：3 次原调用与 2 次 R01 追加调用；R01 无有效输出 |
| verifier_input_002 | [共享输入去重](verifier_input_002/evidence/README.md)：准备材料，复用前一目录候选，不冒充新增模型结果 |
| verifier_fact_screen_001 | [事实核验结果](verifier_fact_screen_001/evidence/README.md)：3 次调用，18 个目标、3 个冲突，保留遗漏说明 |
| repair_001 | [修复准备](repair_001/evidence/README.md)：候选、核验输入和历史测试结论，无已完成的真实修复结果 |
| repair_002 | [定向修复结果](repair_002/evidence/README.md)：3 次调用，修复输出及合并候选 |

Repair 的根 README 和部分历史协议/结果文档属于冻结材料，保持原文；整理后的导航位于各目录 `evidence/README.md`。完整测试日志位于原始归档，历史测试结论不表示本次重新运行通过。

## 4. ALFWorld 配置与运行

| 目录 | 当前记录 |
|---|---|
| alfworld_initial_skill_001 | [R01–R03 完成，R04 Editor 停止](alfworld_initial_skill_001/README.md)；保留原 001–006 与追加 007–012，无最终 Test |
| alfworld_action_only_001 | [仅准备配置](alfworld_action_only_001/README.md)，未发现对应运行归档 |
| alfworld_action_feedback_001 | [仅准备配置](alfworld_action_feedback_001/README.md)，未发现对应运行归档 |
| alfworld_verified_memory_001 | [R01–R02 完成，R03 Actor 停止](alfworld_verified_memory_001/README.md)；保留第 36 步六次回答证据，无最终 Test |
| alfworld_verified_feedback_001 | [六轮及最终 Test 完成](alfworld_verified_feedback_001/README.md)，保留 Memory 审计与授权修订边界 |

正式 `config/` 和任务 `data/` 保留原位。五份 `campaign.json` 各约 8.4 MB，内含冻结环境文件，属于正式配置；此次没有抽离这些字段，以免改变旧运行契约和后续版本读取。

## 文件读取与运行边界

- 本目录保存配置、Prompt、报告、候选、精选结果、逐任务指标和必要失败证据。`evidence/` 是阅读副本，不是可恢复 Campaign，也不会随新运行自动更新。
- `artifacts/methods/v23_5/` 保存完整输入、调用、轨迹、Memory、日志和源码快照，由 Git 忽略。只克隆仓库可查看保留材料；重读完整输入或恢复旧运行还需要相应本机归档。
- 证据 JSON 中的选择路径、来源路径及尝试号保持原始语义，应相对原归档解析，不把其中路径改为阅读副本。各实验的 `.gitignore` 只放行精选尝试文件。
- [通用运行入口](../../../scripts/runs/run_v23_5_alfworld.sh)默认使用 `alfworld_action_feedback_001`；[带 Memory 核验的入口](../../../scripts/runs/run_v23_5_verified_alfworld.sh)默认使用 `alfworld_verified_feedback_001`。旧 README 中的命令保留历史上下文，不表示当前脚本会自动恢复旧目录。
- [准备脚本](../../../scripts/runs/prepare_v23_5_alfworld.py)还读取 [SkillOpt 启动配置](../../../experiments/configs/skillopt_alfworld_deepseek_v23_4.yaml)和[启动脚本](../../../scripts/runs/run_skillopt_alfworld_deepseek.sh)，虽带 `v23_4` 名称，仍是此入口的直接文件依赖。准备依赖本机 SkillOpt checkout、历史基线归档及 ALFWorld 环境，并非只克隆代码即可完成。

v24 的本地基线准备继续从 `alfworld_verified_feedback_001/config/`、`data/` 和原 `artifacts/methods/v23_5/alfworld_verified_feedback_001/S1/` 读取材料；这些输入保留原位。v24、v25 的源码、实验和对比材料按各自版本管理，不是阅读本导航或导入 v23.5 的前置条件。
