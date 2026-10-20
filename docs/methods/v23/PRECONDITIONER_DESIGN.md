# V23 Preconditioner 设计方案

- 研究主题：基于诊断预条件化的持续 Skill 自进化。
- 状态：正式 Prompt、实现与离线测试已完成；无历史真实验证见文末报告，历史响应驱动验证尚未开展。
- 更新日期：2026-10-18。
- 范围：Preconditioner 的输入、D/S/C 更新变换、输出及 Effective Plan 构造。

## 1. 模块定位

Preconditioner 接收 Diagnosis 提出的原始 Skill 更新，结合当前执行证据和历史更新产生的行为响应，对更新的方向、作用尺度和关联关系进行必要调整。

它主要回答：

> 历史上类似的 Skill 修改，在什么条件下产生了什么行为响应？据此，当前更新应该保持、改变策略、调整范围或强度，还是协调不同要求之间的关系？

整体流程：

```text
Grouping
    ↓
Diagnosis
    │ 原始 Plan
    ↓
Preconditioner ← 历史 Memory
    │
    │ 输出必要 Adjustments
    ↓
程序生成 Effective Plan
    ↓
Editor
```

**Preconditioner 不重新进行 Diagnosis，也不直接编写 Skill。**

Diagnosis 应尽力形成合理的更新初稿，不需要为了凸显 Preconditioner 的作用而故意降低初稿质量。

Preconditioner 不要求每次都修改原始更新。调整可以加强、扩大、收窄、替换、协调或撤下，不默认采取保守策略。

## 2. 输入设计

### 2.1 输入结构

Preconditioner 使用以下六个顶层字段：

```json
{
  "parent": null,
  "plan": {
    "goal": "...",
    "updates": [],
    "checks": []
  },
  "command_sets": {},
  "runs": [],
  "grouping": {
    "groups": []
  },
  "memory": {"entries": [], "sources": {}}
}
```

| 字段 | 作用 |
|---|---|
| `parent` | 当前实际 Parent Skill，用于判断原始更新与已有规则的关系 |
| `plan` | Diagnosis 生成的完整原始 Plan，不提前修改 |
| `command_sets` | 当前相关执行中 Actor 实际可见的动作候选 |
| `runs` | 当前 Parent 的真实执行事实及必要上下文 |
| `grouping` | 相关决策问题、共同条件和重要差异 |
| `memory` | 当前有效的历史 MemoryEntry 及理解其作用所需的上下文 |

上面的 JSON 仅展示字段，不代表可执行的空 Plan。正式 Prompt 和模型输出使用英文。

Actor 能力、实际基础协议和执行限制沿用 Diagnosis 的共享执行背景，不另外创建一套能力说明。

只有 Diagnosis 返回 `revise` 时，才进入 Preconditioner。

Diagnosis 返回 `no_change` 或 `need_evidence` 时，不允许 Preconditioner 凭空生成另一份 Plan。

### 2.2 当前执行证据

Preconditioner 不默认重新读取整批 Parent 轨迹。首版采用确定性装配：**根据原始 Plan 中的执行引用，提供被引用执行的完整记录及其引用的动作菜单，不实现片段截取。**

具体规则：

- 直接复用 Grouping／Diagnosis 的共享事实和引用；不重新转换轨迹或编号。
- 一个执行、步骤、初始状态或 outcome 引用，定位到对应执行，并提供该执行的完整记录；同一执行只装配一次。
- 保留任务、初始状态、完整步骤、反馈及最终结果，步骤继续采用 `before → action → after`。
- `command_sets` 沿用共享事实中的 Actor 可见菜单及原 C 编号。只过滤精确等于 `"help"` 的历史规则由上游事实装配负责，Preconditioner 不再次改造菜单；Actor 可见候选与环境动作合法性保持区分。
- 相关 Group 内容原样保留。一个 Group 引用不自动展开该组所有执行，分组文字不替代原始事实；发生矛盾时以执行事实为准。
- 如果原始 Plan 引用了全部执行，就自然提供全批记录，不为了压缩而截断。

模型看到的 `runs` 是本批被引用执行的完整记录，但可能不包含本批其他执行。相关 Group 的部分成员也可能未展示。必须在提示词中说明展示范围，不能将未展示的执行或事件认定为没有发生。

使用完整被引用执行，可以保留判断搜索循环和跨步依赖所需的连续事实，不让程序猜测孤立步骤是否足够。未来若确有成本问题，再单独确定片段规则；首版不使用“安全截取”“足够上下文”作为未定义的实现判断。

不增加独立证据检索 Agent、正反例筛选器或第二套轨迹摘要。

### 2.3 历史 Memory

Preconditioner 需要读取当前有效的历史 MemoryEntry。

这些历史认识应当能够帮助它理解：

1. 过去实际进行了什么 Skill 修改。
2. 修改后，在什么条件下观察到什么行为响应。
3. 哪些反例、联合归因限制和未验证范围仍然存在。
4. 历史认识对应哪些真实编辑和执行依据。

**MemoryEntry 的正式接口及维护规则现由 [Replay／Memory 设计](REPLAY_MEMORY_DESIGN.md) 规定。**

Preconditioner 接收 `memory: {entries, sources}`：entries 为当前 Active 认识，sources 为其实际编辑、执行事实及历史协议。步骤级引用展开完整执行，来源共享去重。模型判断适用性，不把认识当成强制 Skill 指令；非空 Memory 不要求一定产生 Adjustment。

历史引用需要具有可解析的稳定身份，与当前轮 `u1`、`P1:3` 等局部引用区分。

没有历史 Memory 时，新请求使用 `memory: {"entries": [], "sources": {}}`。旧冻结实验的 `memory: []` 保留原样，通过旧契约只读核验。

## 3. 输出设计

Preconditioner 不重新生成整份 Plan，而只输出必要的更新调整。

固定输出结构：

```json
{
  "decision": "ready",
  "reason": "The original plan remains appropriate.",
  "adjustments": [],
  "checks": null
}
```

| 字段 | 含义 |
|---|---|
| `decision` | 是否可以形成有效更新 |
| `reason` | 简短解释整体决定 |
| `adjustments` | 对原始 Updates 的必要调整 |
| `checks` | 保留或整体替换执行后观察问题 |

### 3.1 decision

保留三个决策：

| decision | 含义 |
|---|---|
| `ready` | 可以形成有效 Plan，包括完全保持原始方案 |
| `no_change` | 原始更新全部撤下，本轮没有需要落实的更新 |
| `need_evidence` | 缺少形成有依据、可落实更新所必需的事实 |

**Keep 与 `no_change` 不同。**

Keep 表示原始 Plan 合理，仍然交给 Editor：

```json
{
  "decision": "ready",
  "reason": "The original plan remains appropriate.",
  "adjustments": [],
  "checks": null
}
```

`no_change` 则表示没有剩余 Update 需要实施。

历史 Memory 不适用、更新后的效果尚未得到验证，都不自动构成 `need_evidence`。

某项更新存在证据缺口，不应自动阻断其他独立且可落实的更新；可以撤下该项，保留有依据的其余更新。但不能撤下必要依赖后，把剩余要求当作完整方案。真正缺少形成有效更新所必需的事实时，才使用 `need_evidence`。

## 4. Adjustments：如何调整原始 Update

### 4.1 输出结构

每项 Adjustment 使用四个字段：

```json
{
  "from": ["u2"],
  "to": [
    {
      "id": "u2",
      "text": "The complete adjusted behavioral requirement."
    }
  ],
  "basis": ["历史MemoryEntryID", "P2:21"],
  "reason": "Explain why the available historical response and current conditions justify this adjustment."
}
```

| 字段 | 作用 |
|---|---|
| `from` | 哪些原始 Update 被调整 |
| `to` | 调整后形成哪些完整行为要求 |
| `basis` | 本次调整的依据，可以包含历史 MemoryEntry 和当前执行事实 |
| `reason` | 解释为什么这些依据支持当前变换 |

`to` 中只保留 `id / text`。

不需要让模型重复填写调整后 Update 的 `basis`。

### 4.2 一套结构表达全部变换

| 操作 | from | to |
|---|---|---|
| Keep | 不输出 Adjustment | — |
| 一对一修改 | `["u2"]` | 一项调整后的 Update |
| 合并相关要求 | `["u1","u2"]` | 一项新 Update |
| 拆分要求 | `["u1"]` | 多项新 Update |
| 撤下要求 | `["u2"]` | `[]` |

所有 Adjustment 同时作用于 Diagnosis 原始 Plan，不按模型输出顺序逐项修改中间 Plan。

- 每项 `from` 必须非空，只能引用原始 Plan 中实际存在的 Update，不能引用另一项 Adjustment 新生成的 Update。
- 同一原始 Update 在本次全部 `from` 中最多出现一次。
- 不允许 `from: []` 凭空新增另一套诊断要求。
- 一对一修改允许保留自己的原 Update ID；使用新 ID 时，不得占用其他原始 Update 的 ID。
- 合并、拆分产生新的唯一 ID，不复用其他原始 Update 的 ID，也不能与其他新 Update 冲突。

新 Update 按被替换原 Update 的最早位置插入，拆分结果按 `to` 顺序排列；其余 Update 保留原相对顺序。合并时依据按来源 Update 在原 Plan 中的顺序去重继承，不以 `from` 数组顺序改变来源排列。

通过 `from → to` 保存对应关系，不引入调整链或执行顺序依赖。

不增加 `disposition`、调整编号、额外状态或中间操作层。

### 4.3 D/S/C 如何体现

D/S/C 是更新变换的三个语义方面，不需要成为独立输出字段。

**D — Direction：策略方向**

改变原始更新要求的行为策略。

例如，将继续尝试相同位置，调整为在适当条件下探索其他合理位置。

**S — Scale：作用尺度**

改变策略的触发条件、适用范围和义务强度。

例如，将“目标未找到时持续搜索”，调整为“存在可识别的合理候选时继续探索”。

尺度可以收窄，也可以扩大；要求可以加强，也可以减弱。

**C — Coupling：更新关联**

协调不同 Update 及 Parent 已有规则之间的依赖和冲突。

例如，将“继续探索”和“避免无反馈重复”两个要求协调成一致的策略。

一项 Adjustment 可以同时涉及 D/S/C 的多个方面。

**不强制每轮发生非恒等变换，也不强制分别填写 D、S、C。**

## 5. Basis：证据如何保存，避免持续增长

这里明确区分两种依据。

### 5.1 Diagnosis Update 的 basis

记录本轮原始更新所依据的当前执行证据。

例如：

```json
{
  "id": "u2",
  "text": "Continue searching locations not yet checked.",
  "basis": ["G2", "P2:21", "P3:19"]
}
```

### 5.2 Preconditioner Adjustment 的 basis

记录为什么调整原始 Update。

例如：

```json
{
  "from": ["u2"],
  "to": [
    {
      "id": "u2",
      "text": "When recent repeated searches provide no new information, prefer another currently accessible location."
    }
  ],
  "basis": ["历史MemoryEntryID", "P2:21"],
  "reason": "The historical response indicates a risk of unproductive repetition, and current Actor capabilities do not support global visited-location conditions."
}
```

两者含义不同：

- Diagnosis 的 `basis`：**原始要求为什么被提出？**
- Adjustment 的 `basis`：**原始要求为什么需要这样调整？**

**两种依据分开保存，不机械合并。**

### 5.3 有效 Update 的 basis

程序生成 Effective Plan 时：

- Keep：原 Update 的 basis 原样保留。
- 一对一修改：继承原 Update 的当前 basis。
- 合并：对来源 Updates 的当前 basis 去重合并。
- 拆分：各新 Update 继承原 Update 的当前 basis。
- 撤下：不再生成对应 Update。

例如，调整后的有效 Update 为：

```json
{
  "id": "u2",
  "text": "When recent repeated searches provide no new information, prefer another currently accessible location.",
  "basis": ["G2", "P2:21", "P3:19"]
}
```

这里不自动追加历史 MemoryEntry ID。

程序另行保存原始 Plan 与 Adjustment，后续可以从调整记录查明历史认识为什么影响了 u2。

因此，最终 Update 不需要在每轮反复复制历史依据。

需要注意：**继承的 basis 表示当前更新的来源关系，并不意味着原始证据单独证明调整后文本中的每个条件。** 完整解释仍需要结合 Adjustment 的依据与理由。

后续分析预条件化作用或更新响应时，必须结合原始 Plan、Adjustment 和实际编辑，不能仅根据 Effective Update 的 basis 判断调整依据。拆分后的每项 Update 继承同一份 basis，也不表示这些证据分别独立证明了每个新要求。

Editor 可以只读取自足的 Effective Plan；后续 Replay／Memory 需要保留并读取完整的更新来源链。本节规定信息语义，不提前实现后续模块，也不新增模型输出字段。

## 6. Checks：如何随 Update 调整

Checks 表示 Candidate 执行后值得观察的行为问题，不是 Actor 的执行指令。

新协议将 Check 的关联字段统一命名为：

`update_ids`

例如：

```json
{
  "id": "c1",
  "update_ids": ["u2"],
  "question": "Does the Actor switch to another accessible location when repeated inspections provide no new information?"
}
```

### 6.1 整体替换规则

Preconditioner 不需要另一套 Check 增删改操作。

仅保留三种情况：

| checks 输出 | 含义 |
|---|---|
| `null` | 原始 Checks 全部继承 |
| `[...]` | 使用调整后的完整 Checks 列表 |
| `[]` | 清空全部 Checks |

例如，Diagnosis 原 Check 是：

> Agent 是否继续探索，而不是过早停止？

Preconditioner 收窄搜索条件后，可以调整为：

> 在重复操作没有新反馈时，Agent 是否转向其他合理位置，同时避免过早放弃仍有价值的探索？

如果 Update 没有变化，Check 仍然适用，可以返回 `checks: null`。即便一对一替换保留了 Update ID，只要行为要求的含义变化，也必须判断原问题是否仍适用，不能只因引用合法就机械继承。

如果 Update 合并、拆分或撤下，导致原 Check 引用失效，则必须输出合法的新列表，不能让程序猜测迁移关系。

Checks 不要求覆盖每项 Update，也不需要建立覆盖矩阵。

### 6.2 与已有 Diagnosis 结果兼容

V23 Diagnosis 的首轮归档使用 `checks[].about`；当前正式 Prompt 和接口已经统一采用 `update_ids`，不改变 Checks 的语义。

旧 Diagnosis 档案先按原协议读取和校验，再在交接副本中确定性转换 `about → update_ids`。保留未经改动的原始 Plan，并保存归一后的交接输入；除这一字段名外，不修改原始内容。本文所说“不提前修改原始 Plan”指不提前改变其更新、依据和检查含义。

当前 `load_diagnosis()` 默认核对新 Prompt；读取旧结果需显式提供历史冻结模板，通过原协议的提示词、响应和结构校验后，再进行字段转换。旧模板读取入口与新调用复用分开，不放宽原始结果的一致性检查。

旧 Prompt、messages、模型响应和归档结果均不改写，不调用模型完成字段迁移。该兼容入口已在上游 Prompt 统一中实现，见 [V23 接口说明](../../../src/skill_evolution/v23/README.md)；Preconditioner 已复用该只读兼容入口。

## 7. 程序如何生成 Effective Plan

Preconditioner 只输出必要 Adjustments。

程序负责将这些调整应用到 Diagnosis 的原始 Plan：

```text
Diagnosis 原始 Plan
        +
Preconditioner Adjustments
        ↓
确定性应用替换、合并、拆分或撤下
        ↓
形成最终 Updates
        ↓
处理最终 Checks
        ↓
Effective Plan
        ↓
Editor
```

### 7.1 Effective Plan 的统一结构

```json
{
  "goal": "...",
  "updates": [
    {
      "id": "u2",
      "text": "The final actionable behavioral requirement.",
      "basis": ["G2", "P2:21", "P3:19"]
    }
  ],
  "checks": [
    {
      "id": "c1",
      "update_ids": ["u2"],
      "question": "An important behavioral response to examine."
    }
  ]
}
```

Editor 只读取这一份有效 Plan。

程序分别保存：

- Diagnosis 原始 Plan；
- Preconditioner Adjustment；
- 程序生成的 Effective Plan。

不需要新的模型输出层，也不需要让 Editor 再次理解历史 Memory。

### 7.2 Goal 保持不变

Preconditioner 可以改变达到目标的策略、条件、范围、强度及要求组合，但不擅自修改 Diagnosis 确定的 Goal。

如果原始更新不适合，可以调整或撤下。

如果缺少形成有效更新所必需的事实，则按 `need_evidence` 处理，而不是暗中重新定义 Goal。

### 7.3 三种决定的程序处理

- `ready`：应用调整后，最终至少保留一项 Update，形成 Effective Plan。
- `no_change`：通过 Adjustments 显式撤下全部原始 Updates，`checks=[]`，不进入 Editor。不能用 `no_change` 加空 adjustments 暗中丢弃原始 Plan。
- `need_evidence`：不生成 Effective Plan；`adjustments=[]`、`checks=null`，在 reason 中说明缺少什么必要事实。

程序负责检查调整前后 ID、引用和结构的一致性，不自行改写更新策略。

## 8. Preconditioner 如何进行预条件化判断

这是整个模块的算法核心。

面对 Diagnosis 的原始 Update，Preconditioner 需要完成三个判断。

### 8.1 历史更新是否可比？

比较历史实际 Skill 修改和当前原始 Update：

- 是否涉及相近的行为策略？
- 触发条件和执行环境是否可比？
- 作用范围和要求强度是否相近？
- 是否涉及相同或相关的行为依赖？

不能仅凭任务名称相似或文字相似，就认定历史认识适用。

### 8.2 历史响应是否适用？

结合历史 MemoryEntry 和当前执行证据，判断：

- 历史上实际观察到什么行为变化？
- 这些变化发生在什么条件下？
- 当前 Parent 是否出现可比较的条件？
- 历史证据有哪些反例、未知范围和联合归因限制？

历史认识不能直接当作本轮新观察。

如果某条认识不适用于当前条件，Preconditioner 可以不使用它。

### 8.3 当前 Update 应怎样调整？

根据历史响应和当前依据，选择：

- 保持原始 Update；
- 改变策略方向；
- 扩大或收窄作用范围；
- 加强或减弱要求；
- 协调、合并或拆分相关 Updates；
- 撤下缺乏合理性的更新。

调整可以来自历史响应，也可以来自当前直接证据或 Actor 能力约束。

**必须区分这些依据，不把普通的能力约束修正包装成历史 Memory 驱动的预条件化收益。**

历史 Memory 没有提供有用认识时，可以 Keep。

不为了展示创新性而强制改变更新。

## 9. 完整示例

以下是机制示例，不是已经运行过的 V23 Preconditioner 输出。

### 第一步：Diagnosis 原始 Update

```json
{
  "id": "u2",
  "text": "Continue searching locations not yet checked when the target has not been found.",
  "basis": ["G2", "P2:21", "P3:19"]
}
```

该方向希望减少过早放弃和无效重复，但“尚未检查的全部位置”可能依赖 Actor 不具备的全局历史。

### 第二步：Preconditioner 参考历史响应

假设某条历史 MemoryEntry 表明：

> 增强搜索持续性在存在其他合理候选时，曾伴随更广泛的探索；但重复操作没有新反馈时，也曾观察到循环延长。历史修改包含多项要求，不能独立确认每项规则的作用。

当前 Actor 只有当前观察和最近两组历史，没有全局访问记录。

### 第三步：Preconditioner 输出

```json
{
  "decision": "ready",
  "reason": "The search direction remains useful, but its operating conditions require refinement.",
  "adjustments": [
    {
      "from": ["u2"],
      "to": [
        {
          "id": "u2",
          "text": "When the target remains unseen and recent visible history shows repeated inspection without new information, prefer another reasonable location available among the current action candidates. Do not assume all locations have been checked."
        }
      ],
      "basis": ["历史MemoryEntryID", "P2:21"],
      "reason": "Historical responses indicate a repetition risk, while the Actor's limited history cannot support global visited-location conditions."
    }
  ],
  "checks": [
    {
      "id": "c1",
      "update_ids": ["u2"],
      "question": "Does the Actor switch to another reasonable location after uninformative repetition while preserving useful exploration?"
    }
  ]
}
```

这里包含两种依据：

**当前能力约束：** 不应该要求 Actor 判断所有位置是否曾经检查。

**历史响应：** 无反馈重复与循环延长之间存在值得考虑的历史观察。

Preconditioner 因此保留探索方向，收窄触发条件，并协调有效探索与避免重复。

### 第四步：程序生成 Effective Plan

```json
{
  "goal": "Reduce unproductive repeated searching while preserving useful exploration.",
  "updates": [
    {
      "id": "u2",
      "text": "When the target remains unseen and recent visible history shows repeated inspection without new information, prefer another reasonable location available among the current action candidates. Do not assume all locations have been checked.",
      "basis": ["G2", "P2:21", "P3:19"]
    }
  ],
  "checks": [
    {
      "id": "c1",
      "update_ids": ["u2"],
      "question": "Does the Actor switch to another reasonable location after uninformative repetition while preserving useful exploration?"
    }
  ]
}
```

最终 Effective Plan 可以直接交给 Editor。

历史认识对更新的影响，通过保存的 Adjustment 追溯，不需要重复写入最终 Update 的 basis。

## 10. 模块边界与验证

### 10.1 Preconditioner 不负责

- 重新执行 Grouping 或 Diagnosis。
- 生成新的任务诊断报告。
- 直接编写最终 Skill。
- 生成或修订历史 MemoryEntry。
- 保证更新后 Candidate 一定成功。
- 强制每轮发生 D/S/C 变化。

### 10.2 程序负责验证

- 输出结构与 decision 合法性。
- `from` 非空且只对应原始 Update，不依赖其他 Adjustment 的输出。
- 同一 Update 不被重复调整。
- `to` 的 ID 唯一、不冲突。
- Adjustment 的依据真实可解析。
- Effective Plan 的结构及来源关系正确。
- 最终 Checks 引用的 Update 存在。
- 原始 Plan、Adjustment、Effective Plan 之间的确定性对应。
- 旧实验数据和来源身份不受影响。

不建立复杂的自然语言评分器，也不让程序假装能够证明更新一定有效。

### 10.3 真实模型验证关注什么

重点观察：

- 是否正确理解历史修改及其实际响应。
- 是否将历史响应与当前执行条件合理对应。
- 是否有依据地保持、加强、收窄或协调更新。
- 是否误将当前能力约束说成历史学习所得。
- 是否扩大历史响应的适用范围。
- 调整后的要求是否能够由 Actor 执行。
- Checks 是否与最终 Update 一致。

Keep 是合法结果，不应因为没有调整就被视为失败。

## 11. 最终设计结论

V23 Preconditioner 保持以下简洁接口。

**输入：**

```text
parent
plan
command_sets
runs
grouping
memory
```

**输出：**

```text
decision
reason
adjustments
checks
```

**Adjustment：**

```text
from
to
basis
reason
```

**调整后的 Update：**

```text
id
text
```

**Effective Plan：**

```text
goal
updates
checks
```

最终 Update 采用 `id / text / basis`，由程序根据原始 Plan 与调整记录确定性生成。

本设计不增加 D/S/C 独立字段、不重新生成完整 Plan、不设计复杂的 Check 维护操作，也不将历史依据不断合并进有效 Update。机制和接口已确认，正式实现及无历史验证见下方补充；不涉及 Memory 或后续演化模块。

**核心原则：Diagnosis 提出原始更新；Preconditioner 根据当前条件和历史响应输出必要变换；程序生成统一的 Effective Plan；Editor 负责落实。**


## 12. 相关材料与确认记录

- [V23 文档索引](README.md)。
- [V23 Grouping 设计](AUTOMATIC_GROUPING_DESIGN.md)：共享事实、时间语义和引用。
- [V23 Diagnosis 设计](DIAGNOSIS_DESIGN.md)：原始 Plan 的职责与当前输出协议。
- [Diagnosis 实现验证](../../../experiments/methods/v23/v23_diagnosis_001/reports/REPORT.md)：实际初稿及能力边界问题；不作为历史预条件化收益证据。
- [V23 已实现接口](../../../src/skill_evolution/v23/README.md)：当前 `load_grouping()` 与 `load_diagnosis()` 用法。
- [V22 统一流程简化方案](../v22/UNIFIED_DSC_WORKFLOW_SIMPLIFICATION.md)：直接依据、增量调整及条件化历史响应的设计来源；本文件采用已确认的 V23 接口。

2026-10-18：确认六字段输入、四字段输出、四字段 Adjustment、来源 basis 继承与调整依据分开保存、Checks 整体替换、Goal 保持和三种决定。补充首版完整被引用执行、所有调整同时作用于原始 Plan、下游保留更新来源链、旧 Checks 命名兼容及局部证据缺口的停止边界。未开展 Preconditioner 实现或实验。


### 正式实现补充（2026-10-18）

当前实现见 [preconditioner.py](../../../src/skill_evolution/v23/preconditioner.py)，正式英文全文见 [preconditioner_prompt.md](../../../src/skill_evolution/v23/preconditioner_prompt.md)，唯一共享执行背景来自 [execution_context.md](../../../src/skill_evolution/v23/execution_context.md) 和 `prompts.py`。Prompt 按已确认的通用设计编写，不追加针对当前实验的补丁。

首次 `v23_preconditioner_001` 验证阶段的 `memory` 固定为空。输入只选原 Plan 引用的完整执行及其动作菜单；Group 提供比较上下文，不自动展开其余成员。输出由程序确定性编译，两个合法语义停点的 Effective Plan 为 null。提供 `load_preconditioner()` 交接原始 Plan、Adjustment、Effective Plan 及原始来源，未开发 Memory／Editor／Replay／Gate。实现、测试、真实结果和限制见 [v23_preconditioner_001 报告](../../../experiments/methods/v23/v23_preconditioner_001/reports/REPORT.md)。


### 2026-10-18 非空 Memory 接入

当前代码接入 [Replay／Memory](REPLAY_MEMORY_DESIGN.md) 的正式读取结构；仅修改 Prompt 历史响应章节及输入／引用校验，不改变四字段 Adjustments 输出或 Effective Plan 编译。历史 M ID 留在 Adjustment basis，不自动进入 Effective Update 的 basis。

[真实匹配对照](../../../experiments/methods/v23/v23_preconditioner_with_memory_001/reports/REPORT.md) 使用同一新 Prompt，对同一冻结 Plan 进行空对象与真实 Memory 各一次调用。空侧 Keep；真实侧根据 M1／M2 调整 u1／u3，保留 u2。编译和来源交接通过，但输出仍有全局访问历史依赖、因果措辞过强及尚未验证的搜索策略。此为同批证据回看，不宣称独立泛化或任务收益。
