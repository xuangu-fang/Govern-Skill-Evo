# SpreadsheetBench v25.7

v25.7 基于 v25.6，修改 Diagnosis、[Preconditioner](../../../src/skill_evolution/v25_7/prompts/preconditioner.md) 和 [Replay](../../../src/skill_evolution/v25_7/prompts/replay.md) 的提示词。Diagnosis 根据本轮证据提出可独立实施、能迁移到其他题的修改，每轮 Update 数量不设目标。Preconditioner 比较同一表格决策下的旧规则、提案和执行证据，明确适用条件及旧条款的处理。Replay 要求有归属的事件解释补丁涉及的行为如何影响整题成败翻转。

## 提示词设计

Preconditioner 以 `Compare the Parent and the proposal on the same workbook decision` 和 `Find the rule that governs the decision` 两节组织判断。正文使用具体问题，涉及行为变化、可见线索、例外和旧条款整合。验证或恢复提案需要考虑最后一次保存后的状态，公式交付保留题目要求的公式。输出使用 `KEEP`、`REPLACE`、`WITHDRAW`，有效文本包含 Editor 实施所需的要求，依据和不确定性进入 `reason`。

Replay 分别核对代码路径、执行记录和保存结果。填写 `update_id` 需要两侧证据同时支持补丁的行为关联及该变化对整题翻转的解释。只能解释局部变化、关键联系未明、多个补丁无法区分时填写 `null`，文字中保留观察。若实现细节的不确定性仍允许相同的翻转解释，可以记录限制并关联补丁。正文与输出段使用同一归因条件。

## 版本与运行入口

方法标识为 `v25_7_selective_updates_prompt_v1`，候选标识为 `v25_7_spreadsheetbench`。独立包通过版本内的相对导入和符号链接复用现有引擎。Editor、执行上下文和 Gate 使用 v25.6 的实现。准备时记录代码与提示词哈希，恢复时校验版本身份。[基线哈希](baseline_sha256.json)记录实现前的 v25.6 源码和提示词。

正式配置来自 v25.5 DeepSeek 官方线路。优化使用 120 题、8 批、15 并发，最终评测使用固定 280 题、40 并发。每轮快照保存 Gate 发布的文本。训练结束后，评测入口读取导出的最终 Skill。

[实验归档](../../../experiments/methods/v25_7/README.md)分别记录内网训练、官方线路训练和仅准备的早期配置，附历史源码哈希及离线读回入口。

在仓库根目录执行离线验收。

```sh
/Users/didi/miniforge3/envs/spreadsheetbench/bin/python scripts/runs/v25_7/run_v25_7_train_test.py verify
```

[入口](../../../scripts/runs/v25_7/run_v25_7_train_test.py)支持 `prepare`、`verify`、`train` 和 `run`，可用 `--output` 指定目录。默认目录为 `artifacts/methods/v25_7/v25_7_spreadsheetbench_deepseek`。`prepare` 校验工作簿和 Docker 环境，冻结配置及初始 Skill。`verify` 在准备后执行离线验证。`train` 启动或恢复训练并导出最终 Skill。`run` 完成训练后继续评测最终 Skill。

`--api-profile internal` 使用 `http://llm-proxy.intra.xiaojukeji.com` 与 `deepseek-v4.1-flash`，同时配置 Actor 和四个优化模块。凭据从成对的 `OPENAI_BASE_URL`、`OPENAI_API_KEY` 环境变量读取，或从项目 `.env` 读取。入口校验凭据所属地址与运行配置一致。默认 `public` 配置使用 DeepSeek 官方线路。

## 离线验收

[验收程序](../../../scripts/verification/v25_7/verify_offline.py)检查实际发送的提示词、官方配置、基线哈希、逐轮快照和最终评测交付。它使用合成工作簿与预设响应走完整的四阶段流程，覆盖部分采纳、无归属翻转进入 Memory 且零计票、提交前中断恢复，以及已完成评测的重复调用。模拟调用期间拦截网络连接和子进程。

离线检查确认工程接入与输出合同。模型对新措辞的判断质量需要通过后续提示词评审或模型调用验证。

成对案例评审采用以下条件。

| 模块 | 输入差异 | 评审要点 |
|---|---|---|
| Preconditioner | 对同一覆盖提案，分别提供只讲追加和已区分追加与重算的 Parent | 有效修改是否填补旧规则的实际缺口，是否保留合法追加分支 |
| Preconditioner | 对相同 Parent，把宽泛提案改成条件及整合方式完整的提案 | 能否合理区分 REPLACE 与 KEEP，Editor 是否能独立实施 |
| Replay | 同一重开核验补丁，一侧证据支持核验触发修复，另一案例的成功由独立计算修正解释 | 前者有依据时关联 ID，后者用 null 保存局部发现 |
| Replay | 两条可能路径都支持同一解释，或只有其中一条支持补丁解释 | 不确定性是否影响整题翻转的解释，正向与负向事件采用同一门槛 |

2026-11-16 完成实现与离线验收。内网训练随后在 `artifacts/methods/v25_7/v25_7_spreadsheetbench_v41_20261116` 启动，使用 `train` 动作。该目录的 `launch.json` 记录启动信息，`run.log` 保存进程日志，`campaign/HEAD.json` 指向最近提交的训练状态。`skilladam_alignment.json` 记录与当天 SkillAdam 归档的参数核对，`offline_acceptance.json` 保存内网配置验收结果。
