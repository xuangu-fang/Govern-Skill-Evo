# 自主且受治理的 Skill 演化 v0.1 协议

## 阅读说明

这份文档同时承担两项任务：向人说明实验如何运行，以及为程序实现提供不能随意改变的规则。正文优先使用中文解释；代码、文件和数据中必须保持不变的名称则保留英文。

文中常用名称的含义如下：

- **Campaign（正式实验）**：按照本协议完整运行一次实验。
- **Step（步骤）**：正式实验共有三个连续步骤，每一步使用一批新的训练任务。
- **Skill（技能）**：提供给 Agent 的可复用操作指导。
- **Parent（当前版本）**：某一步开始时正在使用的 Skill。第一步从没有附加 Skill 的 `S0_no_skill` 开始。
- **Candidate（候选版本）**：系统根据本步经验提出、但尚未被接受的新 Skill。
- **Selection（选择评测）**：用固定的18个任务比较候选版本和当前版本。
- **checkpoint（评测基准）**：当前已接受版本在这18个任务上的固定评测结果。
- **Evolution Gate（演化门槛）**：根据评测指标决定接受还是拒绝候选版本的规则。
- **artifact（正式文件）**：实验使用或产生的文件，例如配置、Skill 和评测结果。下文统一称为“正式文件”。
- **冻结（freeze）**：确认内容后将其锁定。冻结后的文件不能原地修改；如果规则需要变化，必须创建新版本。

## 1. 实验目标与结论边界

Autonomous Governed Skill Evolution v0.1（简称 Autonomous GSE v0.1）把已经分别验证过的 Skill 演化环节连接成一个自动循环。循环的步数和预算都是固定的，并由控制程序（Controller）统一安排：

```text
使用当前版本完成一批新的训练任务
→ 根据本批经验提出一个受规则约束的候选版本
→ 对候选版本进行选择评测
→ 按演化门槛作出决定
→ 接受候选版本，或者保留当前版本
→ 进入下一步
```

本实验要回答的问题是：在固定的51次训练交互内，Agent 能否从明确的“无附加 Skill”状态 `S0_no_skill` 出发，依次使用三批互不重叠的训练证据，自主提出候选 Skill，并在治理规则的约束下形成一条由已接受 Skill 组成的演进链。

本实验**不能**证明以下结论：

- Skill 可以无限期持续演化；
- 最终 Skill 在独立测试集（Test）上一定具有更好的泛化能力；
- 一次选择评测完全没有采样误差；
- 实验产生的 Skill 已经可以直接部署到生产环境。

本次正式实验未获准运行 Test。如果当前环境不能覆盖严重违规行为的检测，这一点必须被保留为研究限制，不能省略。

还需要区分“提出过的版本”和“最终接受的版本”：

```text
提出候选版本的过程 ≠ 已接受 Skill 的演进过程
```

候选版本可能被接受、被拒绝，也可能根本没有产生。只有通过演化门槛的候选版本，才能成为后续步骤使用的当前版本。

## 2. 不得改变的正式实验配置

本次正式实验只运行1轮，共3个步骤。51个训练任务被分成3批，每批17个；每一步最多提出1个候选版本。选择评测固定使用18个任务，独立 Test 禁止运行。

下面是程序实际读取的固定配置，字段名必须保持不变：

```yaml
campaign_id: autonomous_gse_v01
initial_parent: S0_no_skill
epochs: 1
steps_per_epoch: 3

train:
  total_tasks: 51
  intent_templates: 17
  batches: 3
  tasks_per_batch: 17
  tasks_per_template: 3
  template_balanced: true
  overlap_between_batches: 0
  cumulative_evidence: false
  replay_previous_batches: false

proposal:
  candidates_per_step: 1
  maximum_learner_calls: 3
  selection_feedback_to_learner: forbidden
  test_feedback_to_learner: forbidden

selection:
  protocol: accepted_parent_checkpoint
  tasks: 18
  initial_s0_checkpoint: fresh
  candidate_selection_each_step: fresh
  accepted_candidate_becomes_checkpoint: true
  rejected_candidate_keeps_checkpoint: true

test:
  authorized: false
```

## 3. 运行次数上限

“轨迹（trajectory）”指 Agent 完成一个任务时留下的一次完整交互记录。正式实验最多允许产生123条轨迹：

```text
训练任务（Train）                    3 × 17 = 51
S0的初始选择评测                               = 18
三个候选版本的选择评测              3 × 18 = 54
--------------------------------------------------
最多                                             = 123
```

此外，最多允许调用 Learner（根据经验生成或修改 Skill 的模型）3次，因此最多有3次产生候选版本的机会。

如果某一步没有产生候选版本，就不运行该步对应的18个选择评测任务。这些没有使用的次数不能挪作其他用途，包括增加步骤、增加候选版本、让 Learner 重试或调用 Test。

## 4. 明确且不可修改的起点 S0

实验的起点 `S0_no_skill` 表示“没有附加学习得到的 Skill”。它必须由一个明确的文件表示，不能在代码中只用 `None` 暗示。

唯一作为正式依据的 S0 文件是：

```text
experiments/campaigns/autonomous_gse_v01/skills/S0_no_skill.json
```

使用 S0 运行时，应保留基准测试（benchmark）默认的 Agent 系统提示词和策略，但不能注入任何学习得到的 Skill。

S0 文件冻结后不能原地修改。如果需要修改 S0，必须创建新的正式实验版本。

## 5. 三批训练任务如何划分

51个冻结的训练任务来自17种意图模板，每种模板各有3个任务。批次规划程序（Batch Planner）必须把它们分成3批，并满足：

- 每批恰好包含每种意图模板的1个任务，共17个任务；
- 三批任务互不重复；
- 51个任务全部被使用，没有遗漏。

任务分批只能依据预先设定的种子和任务标识，不能查看或利用任务成功率、合规性、CuP、违规情况、难度、历史运行结果、历史 Skill 版本或演化门槛的决定。这样可以避免根据结果有意或无意地挑选任务。

固定使用的分批规则名为 `seeded_rank_v01`：

```text
对于每一种意图模板：
    根据 assignment_seed、intent_template_id 和 task_id 生成稳定排序值
    按照 (稳定排序值, task_id) 对该模板的三个任务排序
    第1名 → batch_001
    第2名 → batch_002
    第3名 → batch_003
```

这里的 `assignment_seed` 是固定的分配种子。相同输入和相同种子必须始终得到相同的分批结果。

Batch Planner 输出 `batch_map.json`，不再创建内容重复的附属文件。

`batch_map.json` 只保存以下内容：数据来源、分批算法、分配种子和三组实际分配结果。任务数、模板列表和覆盖情况由 Controller 与测试程序根据实际内容计算，避免在多个位置重复保存同一信息。

相同的输入清单和种子必须生成相同的标准 JSON 文件。当前 Batch Planner 和 `batch_map.json` 已经与实验清单绑定。冻结后的分批文件禁止原地覆盖；任何会改变分批含义的修改，都必须创建新的正式实验版本或 Batch Map 版本。

## 6. 每一步具体做什么

第 `k` 步按以下顺序执行：

```text
取得当前已接受版本 P(k-1)
→ 用 P(k-1) 完成本步对应的冻结训练批次
→ 检查训练交互记录并将其锁定
→ 只根据本批记录生成受治理的经验
→ 根据当前版本的类型选择候选版本生成方式
→ 锁定零个或一个候选版本
→ 如果存在候选版本，重新独立运行选择评测
→ 与当前版本的固定评测基准比较
→ 应用演化门槛
→ 接受候选版本，或者继续保留当前版本
```

每一步只能使用当前批次新产生的经验。不得累计前面批次的经验，不得重新使用前面批次的交互记录，也不得把 Selection 或 Test 的结果反馈给 Learner。

这里的“重新独立运行”是指真正执行一次新的评测，不能复制或复用之前候选版本的运行结果。

## 7. 如何生成候选版本

候选版本的生成方式完全由当前版本的类型决定：

```text
Parent.kind == no_skill
→ bootstrap（从无 Skill 状态生成第一个候选版本）

Parent.kind == accepted_skill
→ incremental（在已接受版本上进行受限的小幅修改）
```

`bootstrap` 只使用当前批次中 `task_success == true` 的两类成功经验：合规成功（Compliant Success）和发生违规但任务成功（Violating Success）。它们用于从 S0 生成初始候选版本。

`incremental` 用于修改已经被接受的当前版本，并且只能进行规则允许的增量编辑。

两种方式使用的提示词（Prompt）不另存重复副本，而以 Learner 的现有实现文件为唯一来源。正式实验记录 Prompt 的来源文件及版本，并在运行记录中保留实际使用的生成方式和模型参数。

两种候选版本生成方式共用以下固定 Learner 参数：

```yaml
requested_model: openai/gpt-5.6-terra
resolved_model: gpt-5.6-terra
reasoning_effort: low
max_completion_tokens: 8000
temperature: null
temperature_policy: not_sent
```

每次正式调用 Learner，都必须记录：使用的生成方式、输入经验数量、模型输出解析结果和用量信息。记录中不能包含 Selection 或 Test 输入。

出现以下任一情况时，本步结果为 `NO_CANDIDATE`，即“没有候选版本”：

- 当前批次没有符合条件的经验；
- Learner 返回了格式合法但内容为空的修改（empty patch）。

此时保留当前版本并进入下一步。如果 Learner 返回的提议无效，本步的候选机会仍视为已经用掉；不得参考 Selection 结果重试或修改候选版本。

## 8. 当前版本的固定评测基准

正式实验开始时，用 S0 重新独立运行18个 Selection 任务，并把结果锁定为初始评测基准（checkpoint）。

之后，每个候选版本都必须在同一组18个 Selection 任务上重新独立运行，再与当前已接受版本的固定评测基准比较：

- `ACCEPT`：接受候选版本。它成为新的当前版本，它的 Selection 结果成为新的评测基准；
- `REJECT`：拒绝并归档候选版本。当前版本及其评测基准保持不变；
- `NO_CANDIDATE` 或 `INVALID_PROPOSAL`：不运行候选版本的 Selection。当前版本及其评测基准保持不变。

已经锁定的评测基准不能因为后续步骤而重新运行。这样既能控制运行成本，也能保证每个新候选版本始终与当时真正的当前版本进行比较。

## 9. 接受候选版本的判断规则

演化门槛使用三项汇总指标的变化量：

- Task Success：任务成功率；
- Compliance：合规率；
- CuP：本研究采用的综合效用指标。

变化量（`delta`，符号为 `Δ`）等于“候选版本指标减去当前版本指标”。只有三项指标都没有下降，并且至少一项确实上升，候选版本才会被接受：

```text
满足以下全部条件时才 ACCEPT：

ΔTaskSuccess >= 0
并且 ΔCompliance >= 0
并且 ΔCuP >= 0
并且至少一项变化量 > 0
```

出现以下任一情况时，候选版本必须被拒绝（`REJECT`）：

- 任一汇总指标下降；
- 三项指标完全持平；
- 评测确认出现严重违规。

如果当前环境无法评测严重违规覆盖情况，应记录为 `not_evaluated`。这不会阻止本研究实验继续进行，但实验结果不能因此被描述为“已经可以部署”。

实验清单中的指标名 `compliance` 对应演化门槛代码中的变化量字段 `compliant`；`task_success` 和 `cup` 名称保持不变。代码返回值与步骤结果的对应关系为：

```text
continue_evolution → ACCEPT
reject             → REJECT
```

协议测试必须使用一组预先写明输入和预期结果的代表性案例（工程上称为 `golden cases`），验证字段对应关系和上述判断规则，不能只检查实现文件的版本信息。

## 10. 步骤进度与最终结果

`status` 和 `outcome` 不能混用：

```text
status
→ 表示当前步骤执行到了哪里

outcome
→ 表示步骤结束后发生了什么
```

程序使用以下 `status` 值记录步骤进度。这些名称属于数据协议，必须保持英文原值：

```text
STEP_REGISTERED
TRAIN_RUNNING
TRAIN_COMPLETED
TRAIN_VALIDATED
EXPERIENCE_FROZEN
PROPOSAL_RUNNING
CANDIDATE_FROZEN
CANDIDATE_SELECTION_RUNNING
SELECTION_VALIDATED
EVOLUTION_SUMMARY_FROZEN
GATE_DECIDED
STEP_COMPLETED
STEP_INVALID
```

它们依次表示：步骤已登记、训练运行中、训练已完成、训练结果已验证、经验已锁定、候选生成中、候选版本已锁定、候选版本评测中、评测已验证、演化摘要已锁定、门槛已决定、步骤正常完成，以及步骤因完整性问题而无效。

`status` 与 `outcome` 必须满足以下关系：

```text
status == STEP_COMPLETED
→ outcome ∈ {ACCEPT, REJECT, NO_CANDIDATE, INVALID_PROPOSAL}

status == STEP_INVALID
→ outcome == INTEGRITY_FAILURE

其他尚未结束的 status
→ 不能出现 outcome 和 next_parent
```

例如，一个正常完成但候选版本被拒绝的步骤应记录为：

```json
{
  "status": "STEP_COMPLETED",
  "outcome": "REJECT"
}
```

不能把 `REJECT` 同时当作执行进度和演化结果。

所有正式结果及后续动作如下：

| 结果 | 含义与动作 | 后续处理 |
|---|---|---|
| `ACCEPT` | 接受候选版本，并更新当前版本和评测基准 | 继续下一步 |
| `REJECT` | 归档候选版本，保留当前版本和评测基准 | 继续下一步 |
| `NO_CANDIDATE` | 没有候选版本，不运行候选版本评测 | 保留当前版本并继续下一步 |
| `INVALID_PROPOSAL` | 候选提议无效，本步候选机会仍被消耗 | 保留当前版本并继续下一步 |
| `INTEGRITY_FAILURE` | 文件、数据关系或预算等完整性检查失败 | 立即停止正式实验，并将其标记为无效 |

候选版本没有通过是正常的实验结果；文件被意外修改、批次关系错误或预算越界则属于实验完整性失败。两者不能混为一谈。

除了由 JSON Schema 检查字段和固定取值外，Controller 还必须检查以下跨文件关系：

```text
第1、2、3步只能分别使用 batch_001、batch_002、batch_003
parent_checkpoint 必须属于当前 Parent
ACCEPT 后的 next_parent 必须与 Candidate 文件及其版本一致
REJECT 后的 next_parent 必须与原 Parent 文件及其版本一致
NO_CANDIDATE 和 INVALID_PROPOSAL 后的 next_parent 必须与原 Parent 一致
INTEGRITY_FAILURE 不能产生新的已接受 Parent
```

任一检查失败都不能降级成普通的 `REJECT`，必须记录为：

```text
status  = STEP_INVALID
outcome = INTEGRITY_FAILURE
```

## 11. 实验记录与版本管理

正式实验记录通过路径（path）、版本（version）和结构化关系说明所使用的内容，包括：

- 当前版本（Parent）；
- 候选版本（Candidate）；
- 评测基准（checkpoint）；
- 任务分批表（batch map）；
- 提示词（Prompt）。

Controller 检查批次、Parent、Candidate、checkpoint、预算与数据隔离等会改变实验含义的关系。文件内容本身不再重复登记摘要，也不再逐个绑定实现文件；正式实验使用过的实现由 Git 历史保存。

基准测试运行环境仍需遵守已记录的 Agent 模型参数、任务顺序执行要求、每次试验前的数据库重置和数据库快照要求。

候选版本编号与已接受 Skill 的版本号必须分开：

```text
epoch_001_step_001_candidate  # 候选版本的身份编号
S1                            # 第一个被接受的 Skill 版本号
```

被拒绝的候选版本不能占用已接受 Skill 的版本号，也不能被覆盖。候选版本被接受时，应另建一条晋升记录，明确它与新 Skill 版本之间的对应关系。

## 12. 已完成实验的清单与结果

本协议配套两个 JSON Schema。Schema 是供程序自动检查 JSON 文件结构和固定规则的说明文件：

- `schemas/autonomous_gse_v01_campaign.schema.json`：检查正式实验的固定设置、预算、数据隔离规则和文件路径；
- `schemas/autonomous_gse_v01_step.schema.json`：检查各步骤的当前版本、任务批次、候选生成方式、评测基准和最终状态。

唯一作为正式依据的实验清单是：

```text
experiments/campaigns/autonomous_gse_v01/campaign_manifest.json
```

v0.1 已于 2026-08-13 完成，当前清单状态为 `completed`。任务分配以已执行的 `batch_map.json` 为准，正式结果以 `experiments/results/autonomous_gse_v01/campaign_report.json` 为准。

当前正式入口保留两阶段执行方式：`initial-checkpoint` 先让 S0 完成18条 Selection Task，`run` 再从该 checkpoint 执行完整三步流程。已完成的 `autonomous_gse_v01` 不允许原地覆盖；重新运行应使用新的 Campaign ID。入口只校验路径、版本、Task ID、预算和结构化结果关系，不依赖逐文件内容摘要、实现绑定或单独冻结记录。

2026-08-14 的整理没有重新运行实验，也没有改变三步 outcome、最终 S1、87 条任务记录或 3 次 Learner 调用。整理只删除了逐文件内容摘要、实现绑定、单独冻结记录和配套检查代码；整理前的完整实现仍保存在 Git 历史中。
