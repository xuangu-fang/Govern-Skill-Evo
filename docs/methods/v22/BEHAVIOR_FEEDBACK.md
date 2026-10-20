# V22 Editor 要求保持与 Replay 行为反馈包

[返回索引](README.md) · [机制设计](DESIGN.md) · [无历史更新入口](NO_HISTORY_ROUND.md)

更新日期：2026-10-14。本文记录原 Editor v1 与独立 Replay 路径：执行前由 Editor 检查实际文本是否保持要求，执行后由 Replay 对完整已有轨迹形成有来源的行为观察。这套旧路径不提供 Memory 写入、Fusion 变换、追加比较调度或正式 Gate。

该协议的历史验证状态：两次 Replay 与两次独立 Editor 检查均未通过语义输出校验，没有形成该阶段有效的真实反馈包或 Editor v1 输出。代码和离线测试完成不代表真实调用成功；失败与全部成本见[验证报告](../../../experiments/methods/v22/02_behavior_feedback/reports/REPORT.md)，后续紧凑协议不会改写这项历史结论。

后续设计已按 [DESIGN](DESIGN.md) 第 4.4、5.3.4、6.6 节收敛为最小更新规则及案例走查，并在 [MINIMAL_INTERFACES](MINIMAL_INTERFACES.md) 明确共享方案、组级定位、稀疏反馈和未评估范围。初次接口设计阶段没有修改代码、补做真实调用或将失败产物转成有效反馈；之后新增的 `compact_learning.py`、`compact_update.py`、`compact_cycle.py` 已将这些职责落实为独立的紧凑 v1 本地协议，见 [紧凑反馈学习与后续更新](COMPACT_CYCLE.md)。旧六方面检查、逐目标逐任务输出及其核验入口保持原样。本文件继续说明旧协议；新入口不把空例外视为语义通过，也不把来源引用有效、watch 有去向或 Memory 写入成功视为认识正确和完整闭环成功。

## 1. 两种检查的职责与时序

| 环节 | 判断内容 | 不能据此断言 |
|---|---|---|
| Editor 执行前检查 | 实际文本是否保持目标相关条件、策略、范围、保留行为、关联和所需能力 | Agent 一定遵循、任务一定成功、语义等价已被程序证明 |
| Replay 实际落实检查 | 已执行 Candidate 的文本是否偏离原要求；发现偏离时记录真实版本 | 追认旧候选已通过后来新增的执行前检查 |
| Replay 行为观察 | 两侧机会、实际动作、目标与保留行为变化、原生结果和未知 | 未覆盖情境安全、每项编辑独立贡献、普遍因果效应 |

同一个成功结果不同时充当语义保持、作用归因和正式采用的证明。旧候选及其原始响应、预期、执行轨迹保持不变。

## 2. Editor v1：检查合并在同一次构造调用中

`editor_preservation.py` 为每项 proposal 生成可解析的要求来源，覆盖 `trigger`、`strategy`、`scope`、`preserve`、`interactions`、`capabilities`。保留要求同时包含该 proposal 的局部要求和全局保留行为；关联读取所有涉及它的关系及处理要求。

输出 `v22.editor.v1` 在原 Editor 字段上增加 `requirements_sha256` 与 `requirement_checks`。每项要求的六方面分别给出短文本摘录、判断理由和状态：

- `faithful`：未发现实质偏离。
- `expression_only`：只改变表达或组织，条件、顺序、义务和依赖等价；仍需说明依据。
- `needs_revision`：要求不具备可执行条件，或实现需要实质改变方向、范围、义务、条件或依赖。

任一方面需要修订，整个 Editor 返回 `needs_revision`，受影响 proposal 必须有对应的限制、反例、上游建议和范围变化；不输出可执行 Candidate。其他 proposal 仍要有去向。完整检查与构造在一次 Editor 响应内完成，不增加固定 Review Agent。

程序验证要求身份、完整覆盖、准确文本摘录、聚合状态、反馈与检查一致性，以及**已经声明的**能力依赖。Actor 只具备当前观察、合法动作、任务描述与最近两条前动作观察／动作，没有完整历史、持久笔记或隐藏状态；已声明依赖不可用能力时不能放行。

程序不会从任意自然语言中可靠推导所有隐含能力或证明语义等价。Editor 可能漏检或误判；测试中的“拒绝实质变化”指已经以结构化检查表达出来的变化，不能描述为通用语义判定器。

新 `run_round` 默认请求 v1，模型自行返回 v0 会被拒绝；历史 v0 prompt／validator 保留，旧产物可按原协议复核。显式 v0 配置仍可用于历史兼容测试，不代表通过了 v1。

## 3. 执行前观察说明

新轮次在 Candidate 文本和真实 diff 确定后、第一次 Candidate 动作之前，程序保存 `observation_plan.json`，并把 hash 写入 Candidate lineage。

该文件复用有效要求中的目标、全局保留行为、触发与预期、关联、边界案例和 Editor 未决预期；目标 ID 为 `goal:<id>`，全局保留行为为 `preserve:<index>`。数量随输入变化，不冻结行为维度，也不新增一轮模型规划。

当前逐任务覆盖仅强制目标和全局保留行为。proposal 内的局部 `preserve` 仍保存在完整要求中供语义分析，但未逐项建立执行观察目标；`realization` 也只强制每项 proposal 一次判断，不能保证每条局部保留要求分别得到文本核对与行为反馈。这是首版覆盖限制，后续应研究合并重复要求后怎样补齐必要的局部条件覆盖。

旧轮次没有这个文件。后处理可以从已冻结的执行前要求与文本重建说明，但必须标记 `reconstructed_from_frozen_pre_execution_artifacts`；不能回写原轮次并宣称当时已有该检查。旧 Editor 标记 `not_recorded_legacy`，区别于新版本的 `recorded_self_check`。

## 4. Replay：事实、解释与未知分开保存

`feedback.py` 首先复核来源轮次、实际 Skill、diff、调用记录和任务条件，只读取 `learning/train` 的学习视图。完整轨迹参与分析，不能仅复述 Diagnosis 已引用的步骤。

**程序事实层**包含两侧运行身份、完整性、原生成功、动作数、合法列表之外的动作步骤、`look` 步骤、字面 `Nothing happens.` 步骤、已报告用量及未知用量。后两类信号仅是可机械提取的事件，不能直接判为失败、无效或行为保持。实际消息、模型推理、隐藏环境内容和本地文件路径不进入模型证据视图。

**一次 Replay 语义调用**输出：

| 内容 | 约束 |
|---|---|
| `realization` | 每项 proposal 对应实际要求和 Candidate 精确摘录，判断落实、偏离或未知 |
| `observations` | 每个目标／全局保留行为与每项已配对任务均有去向，区分两侧机会、行为、响应和未知 |
| `relations` | 覆盖已声明关联，只报告联合观察、执行依赖或未决；不声称单项因果或非加性交互 |
| `expectation_checks` | Editor 每项未决预期都明确已观察、未检验或未知 |
| `unexpected_changes` | 保存原方案外的新变化、反例与事实遗漏，连同来源和归因限制 |
| `untested`／`followups` | 保存未测边界；仅在答案会改变更新时建议有界比较，不自动执行 |

事件引用为 `{run_id, step}`，0 表示初始观察，正整数表示实际记录事件。程序检查引用属于正确的任务与 Parent／Candidate 一侧，拒绝伪造步骤、错误摘录、重复或漏项。文本含义和证据是否足够支持判断，仍属于可能出错的模型解释。

机会区分 `reached`、`external_absent`、`path_changed`、`unknown`。路径改变需要前序已执行决策的引用；未触发不能写成已遵循。只有两侧都观察到机会，才能报告 `observed_preservation`。条件不匹配或执行不完整时保留各自事实，但比较响应必须为 `unknown`；缺失任务显式列入 `unexecuted_tasks`，不构造假轨迹。

现有同任务 Parent／整包 Candidate 只能支持有边界的联合观察。局部动作可对应到某要求，但不能据此分摊独立收益；单条成功序列也不能证明其中每一步必要。

## 5. 反馈包、来源与成本

```text
feedback/
  manifest.json       # 源文件 hash、分析代码身份、模型和预算
  input.json          # 实际文本、要求、观察说明、事实及允许读取的完整轨迹
  calls/replay.json    # 一次请求、原始响应、HTTP 尝试、usage
  assessment.json     # 校验通过的语义解释
  package.json        # 事实、解释、学习边界及身份绑定
  report.json         # 操作状态和增量成本
```

输出目录必须在来源轮次之外且不存在。校验失败、格式错误或模型调用错误保留原始记录，不能发布 `package.json`、自动改成未知或伪装成无需修改。`feedback_ready` 只表示这个反馈产物通过约定校验，不表示源任务一定成功或解释已经证实。

包内明确 `unit=actual_candidate_bundle`、`causal_attribution=not_identified`、`memory_written=false`、`adoption_changed=false`。以后 Memory 可以消费这些带来源和限制的观察，但本阶段不将它们自动变为更新规律。

源轮次成本单独引用，不重复计费；本次 Replay 的调用、HTTP 尝试、token 与未知用量单独记录。一次操作最多一次 Replay，无自动语义修复。若研究过程中明确改变恢复预算，必须另存计划、保留全部失败与成本，不能把恢复后的结果报告为首次成功。

## 6. 运行与验证

```bash
conda activate alfworld
python -m src.skill_evolution.v22.feedback run \
  artifacts/methods/v22/no_history_20261014/round \
  --output-dir /path/to/new_feedback --dry-run
python -m src.skill_evolution.v22.feedback run \
  artifacts/methods/v22/no_history_20261014/round \
  --output-dir /path/to/new_feedback
python -m src.skill_evolution.v22.feedback verify /path/to/new_feedback
```

另有 `editor_check` 入口，以原 Parent／Diagnosis／执行前证据做一次独立 v1 构造检查。它不读取旧 Candidate 及其执行结果，返回的草稿不执行、不采用，也不追认旧版本：

```bash
python -m src.skill_evolution.v22.editor_check run \
  artifacts/methods/v22/no_history_20261014/round \
  --output-dir /path/to/new_editor_check
python -m src.skill_evolution.v22.editor_check verify /path/to/new_editor_check
python -m unittest discover -s tests/skill_evolution/v22 -q
```

`--dry-run` 只检查输入，不读凭据、调用模型或生成输出。本阶段的具体真实验证与失败记录单独保存于 `experiments/methods/v22/02_behavior_feedback/`；没有新增环境执行、Memory 写入或 Skill 采用。
