# V23 Diagnosis 设计方案

- 研究主题：基于预条件的持续 Skill 自进化。
- 状态：设计已确认；正式提示词、实现、离线测试及一次真实模型验证已完成，见[实现与验证报告](../../../experiments/methods/v23/v23_diagnosis_001/reports/REPORT.md)。
- 当前 Prompt 与接口验证：[统一实现报告](../../../experiments/methods/v23/v23_prompt_alignment_001/reports/REPORT.md)，使用共享执行背景及 update_ids；首轮报告保留历史状态。
- 更新日期：2026-10-18。
- 范围：Diagnosis 的共享输入、原始更新输出、证据引用、观察问题和语义停点。

## 1. 模块定位

Diagnosis 根据当前 Parent Skill 和本批真实执行事实，提出有依据、可落实的原始 Skill 更新，交给 Preconditioner 进一步调整。

```text
Grouping
共同决策问题、关键步骤依据和重要差异
    ↓
Diagnosis
结合完整当前事实，独立形成原始更新 Plan
    ↓
Preconditioner
结合历史实际更新的条件化响应，调整原始更新
```

Diagnosis 形成一份联合初稿，不按组分别生成 Plan，不要求先输出逐任务诊断报告。不读取历史 Memory，不为体现后续 Preconditioner 的作用而刻意弱化初稿。

更新要能由实际 Actor 能力落实。Diagnosis 应区分可通过 Skill 调整的行为问题、基础协议遵循问题、技术中断及尚不确定的解释，不把一次失败直接归因为 Skill 缺陷，也不把所有未知变成停止更新的理由。

本设计继承 [V22 统一流程简化方案](../v22/UNIFIED_DSC_WORKFLOW_SIMPLIFICATION.md)中共同证据、原始更新和简洁表达的方向，并采用已经确认的 `goal`、`updates` 命名。V23 本版进一步采用 `checks`，不单独保留 `open`／`issues`。

## 2. 输入

### 2.1 共享执行背景与任务说明

总提示词由两部分组成：

```text
共享执行背景
  与 Grouping 相同的 Actor 能力说明
  实际基础系统指令
  实际初始输入模板与历史输入模板
  本批执行的步数上限

Diagnosis 任务说明
  诊断目标、更新规则、证据边界和输出格式
```

通过 `prompts.py` 和唯一的 `execution_context.md` 与 Grouping 共用实际执行背景，不再从 Grouping Prompt 的标题段落中截取，不重新装配另一套能力描述，不恢复独立的 `capabilities`、`base_protocol`、`execution_constraints` 数据字段。

当前能力说明与 V22 执行方式一致：Actor 能看到当前观察、动作候选及最近两组行动前观察与动作，没有完整历史或可写的持久笔记。若实际能力变化，统一调整共享背景，不只修改 Diagnosis 一侧。

### 2.2 数据结构

数据输入在 Grouping 的共享事实基础上增加分组结果：

```json
{
  "parent": null,
  "command_sets": {},
  "runs": [],
  "grouping": {
    "groups": []
  }
}
```

以上仅展示顶层结构，不是可执行的空批次。

| 字段 | 内容及用途 |
|---|---|
| `parent` | 实际使用的完整 Skill 正文；无 Skill 时为 `null`，用于判断已有规则、修改位置和保留能力 |
| `command_sets` | Actor 实际可见动作候选列表，用于判断行动时展示的选择材料 |
| `runs` | 本批全部 Parent 执行事实，包括初始状态、完整步骤、反馈和结果 |
| `grouping` | 已保存的五字段分组结果，用于组织共同问题与条件比较 |

`parent`、`command_sets`、`runs` 直接复用 [Grouping 共享事实结构](AUTOMATIC_GROUPING_DESIGN.md)，不另做轨迹摘要，不筛选关键片段，不增加第二套编号。

动作候选仍只过滤精确等于 `"help"` 的命令，保留其他内容、顺序和重复项。环境动作合法性与 Actor 可见候选保持区分。步骤继续采用 `before → action → after`；行动后才出现的信息不能作为行动前已经知道的条件，缺失菜单与已确认空列表保持区别。

输入不包含 Candidate、历史 Memory 或旧更新方案。程序侧 `sources`、路径及运行元数据不整体搬入模型输入。

### 2.3 如何使用 Grouping

Grouping 是可核对的分析结构，不是原始事实或已证明正确的诊断。Diagnosis 读取完整轨迹，遇到分组说明与执行记录不一致时以执行事实为准，不沿用错误推断，也不增加一次分组修复调用。

例如，已有 [Grouping 真实调用](../../../experiments/methods/v23/v23_grouping_001/reports/REPORT.md)中出现将第 10 步事件写在第 1—17 步之后、将后续观察到的柜子状态概括为初始状态的问题。Diagnosis 应根据实际步骤判断，不把引用有效等同于解释正确。

不要求每组产生更新。一组可以支持多项更新，一项更新可以关联多个组；分组未突出的问题仍可由完整事实支持。Diagnosis 不据此重新生成或覆盖本轮 Grouping。

## 3. 输出结构

固定顶层为 `decision`、`reason`、`plan`。非空 Plan 包含 `goal`、`updates`、`checks`：

```json
{
  "decision": "revise",
  "reason": "Briefly explain the current evidence and why an update is warranted.",
  "plan": {
    "goal": "The intended behavioral improvement and common preservation boundaries.",
    "updates": [
      {
        "id": "u1",
        "text": "A complete, actionable behavioral update.",
        "basis": ["G2", "P2:21", "P2:25"]
      }
    ],
    "checks": [
      {
        "id": "c1",
        "update_ids": ["u1"],
        "question": "An important behavioral response or counterexample to examine after execution."
      }
    ]
  }
}
```

示例中的文字和引用只用于说明结构，不代表已经完成真实 Diagnosis。

| 字段 | 职责 |
|---|---|
| `decision` | 判断是否形成更新，或当前缺少必要证据 |
| `reason` | 简短解释决定及关键依据，不重复整份 Plan |
| `goal` | 表达本次希望改善的行为目标及共同保留边界 |
| `updates` | 提出实际准备落实的行为要求 |
| `checks` | 指出执行后值得检查的关键响应、反例或保持情况 |

不增加逐任务原因报告、逐维 D/S/C 标签、自证表或额外诊断对象层。实际提示词和模型输出使用英文；已实现的[正式英文任务提示词](../../../src/skill_evolution/v23/diagnosis_prompt.md)遵循本设计。

## 4. 原始更新如何表达

### 4.1 goal 与 updates 的分工

`goal` 说明希望改善什么，以及共同需要保持什么，不预先把某个实现策略锁定为目标。`updates[].text` 说明准备怎样改变行为，使 Preconditioner 能在保持目标的前提下调整具体更新。

一项更新应能回答：

> 相对于当前 Parent，在什么 Actor 可识别的条件下，准备怎样改变行为；必要的范围、强度、依赖和保留要求是什么？

将这些内容写成完整自然语言要求，不拆出一组 D/S/C 字段。D/S/C 仍体现为可调整的策略方向、作用范围和强度，以及与其他更新或 Parent 既有行为的关联。

以下是写法示意，不是对某条真实轨迹已经形成的更新结论：

> 在目标尚未出现、近期可见历史显示同一位置被重复检查且观察没有变化时，优先尝试当前动作候选中近期尚未尝试的可访问位置。不能仅凭两步历史就认定所有位置已经检查完毕。

这一表达同时交代了触发条件、行为方向和能力边界。“减少重复搜索”本身不足以构成可落实要求；要求维护实际不存在的全局访问记录也不可落实。

### 4.2 更新范围与完整性

- 更新写成可复用行为要求，不写任务编号、实例答案或记住某个物体位置。
- 已有有效行为可以成为保留要求；每项 update 不一定产生新的文本 diff。
- 重要条件、依赖和例外直接写入要求，不让 Editor 从证据编号重新规划策略。
- 不能只写“按 G2 改进”或“保留 P3 的行为”。更新文字需要自足，后续 Editor 能从有效 Plan 理解应落实的行为。
- 不因失败就自动加强义务，也不因效果未证明就自动削弱或放弃合理更新。

### 4.3 basis 与证据

每项 update 使用简单引用数组保留必要依据：

```json
{
  "id": "u1",
  "text": "A complete behavioral update supported by current observations.",
  "basis": ["G2", "P2:21", "P2:25", "P3:17", "P3:18"]
}
```

`G2` 指向相关决策问题，执行或步骤引用支撑实际条件与行为。只有组引用不足以支持更新。引用数量不要求覆盖全部相似事件，也不新增一套 Findings 或诊断 ID 中转。

沿用当前事实引用，如 `P1:0`、`P1:3`、`P1:outcome` 和 `G1`，不另造任务编号。依据只能来自当前提供的事实与分组，不能引用不存在的历史 Memory。具体引用解析与合法范围在接口实现时统一核对，不将引用有效当作语义正确的证明。

## 5. checks 的含义

`checks` 替代原来的 `watch`，表示执行后需要检查的问题，不是 Actor 的新增指令，也不是独立执行模块。

每项检查包含 `id`、`update_ids`、`question`；`update_ids` 关联本 Plan 中的 update ID，可以关联多项更新。

```json
{
  "id": "c1",
  "update_ids": ["u1"],
  "question": "When recent repeated inspections reveal no new information, does the Actor move to another accessible location, and does it leave any location before completing a still-needed action?"
}
```

该例同时检查预期响应和可能的反例，增加了判断信息，不只是把“减少重复搜索”改成疑问句。

- 允许 `checks: []`。
- 不强制每条更新对应一个检查，不要求逐项生成覆盖矩阵。
- 一个检查可以关注多项更新的共同作用。
- 只保留会影响判断的重要行为响应、保持情况、反例或未知。
- 不机械地重复 goal、reason 和 updates。

Preconditioner 如何调整 checks，以及学习端如何消费检查问题，将在对应模块中继续对齐；本版不直接继承 V22 强制逐项 Watch 覆盖的维护规则。

## 6. 三种决策与停止边界

| decision | 含义 | plan |
|---|---|---|
| `revise` | 当前证据支持形成可落实的原始更新 | 非空，至少一项 update |
| `no_change` | 当前没有需要提出的新行为要求 | `null` |
| `need_evidence` | 缺少构造更新所必需的事实，无法形成有依据的方案 | `null` |

`reason` 在形成更新时简短说明主要判断；没有 Plan 时具体说明为什么不更新或缺少什么必要事实，可以在文字中引用相关执行步骤。

```json
{
  "decision": "need_evidence",
  "reason": "State the specific missing fact needed to construct an actionable update, with current references where available.",
  "plan": null
}
```

尚不知道修改后能否提高成功率，不是 `need_evidence` 的充分理由；效果本来就需要后续执行检验。模型调用失败、输出截断或 JSON 无效属于程序错误，不伪装成 `no_change` 或 `need_evidence`。

## 7. 不单独保留 open 或 issues

本版确认不在 Diagnosis 输出中单独设置 `open`／`issues`：

- 阻止形成整个方案的必要证据缺口，用 `need_evidence` 和具体 reason 表达。
- 某个方向无法构造，但其他方向已有充分依据时，可以提出其余可落实更新，并在 reason 中明确本次范围。
- 若被省略的部分是其余更新的必要依赖，不能把剩余要求冒充完整可执行方案。
- 效果未知及重要待检验条件进入 checks，不自动成为构造阻碍。

不要求 Preconditioner 接收含糊的未完成要求后自行补成方案。若后续确实需要传递独立的局部构造矛盾，再依据实际用途讨论字段变更，不预先恢复复杂维护结构。

## 8. 实现与验证重点

以下是本设计要求的核对重点。程序实现与离线／真实验证已经完成；具体通过项和未解决的语义限制以[实现与验证报告](../../../experiments/methods/v23/v23_diagnosis_001/reports/REPORT.md)为准，不能把结构校验通过等同于所有行为要求已验证：

| 范围 | 核对重点 |
|---|---|
| 输入复用 | 直接使用 Grouping 的事实和引用，背景一致，不混入历史 Memory |
| 事实优先 | Grouping 说明有误时，判断回到原始步骤，不复制错误时间关系或隐藏条件 |
| 输出结构 | 顶层和 Plan 字段固定，三种 decision 与 plan 的关系正确，ID 和引用合法 |
| 更新自足 | 条件、策略、范围、重要依赖和保留要求可理解、可落实，不依赖实例答案 |
| Actor 能力 | 不把学习端完整轨迹当成 Actor 记忆，不把行动后信息当成行动前条件 |
| checks | 允许为空或关联多项更新，不机械重复要求，不增加强制覆盖矩阵 |
| 语义停点 | 缺少必要事实与效果未验证分开；技术失败不变成语义决定 |
| 下游边界 | Diagnosis 提供独立原始更新；历史响应调整由 Preconditioner 完成 |

正式实现复用已保存的四条 Parent 分组，冻结预算后仅调用一次 deepseek-flash，得到可复用的原始 Plan。没有开发 Preconditioner、Editor、Memory、Replay 或 Gate，也没有启动完整自进化实验。调用配置、完整输出和保存路径见报告。

## 9. 相关材料

- [V23 自动分组设计](AUTOMATIC_GROUPING_DESIGN.md)：已确定的共享事实、时间语义和引用。
- [V23 Grouping 使用说明](../../../src/skill_evolution/v23/README.md)：已实现的 `load_grouping` 交接方式。
- [Grouping 实现验证报告](../../../experiments/methods/v23/v23_grouping_001/reports/REPORT.md)：实际输出及其语义限制。
- [Diagnosis 实现验证报告](../../../experiments/methods/v23/v23_diagnosis_001/reports/REPORT.md)：175 项测试与 19 个子测试、一次真实输出、语义核查及下游读取接口。
- [V22 统一流程简化方案](../v22/UNIFIED_DSC_WORKFLOW_SIMPLIFICATION.md)：原有 Diagnosis 方向与本版简化的来源。

2026-10-18（设计确认）：确认共享输入加 grouping，以及 `decision / reason / plan`、`goal / updates / checks` 输出；采用 checks 命名，不单独保留 open／issues。

2026-10-18（实现验证）：完成正式 Prompt、程序接口、离线回归和一次真实调用；保留原始模型输出及明确的语义限制，停止在 Diagnosis 交接边界。

2026-10-18（Prompt 统一）：按已确认的英文基线重组事实核对、行为问题识别、更新构造、Checks 与决定、输出格式。强调区分已有指导、协议未遵循与新的 Skill 要求，更新触发条件须在 Actor 决策时可识别；保留积极构造联合初稿的职责。新 Check 正式采用 `update_ids`，旧 `about` 结果通过显式历史模板先校验、再只读转换。完整 Prompt、配置与验证见 [Prompt 统一实验](../../../experiments/methods/v23/v23_prompt_alignment_001/README.md)。
