# V23 Replay 与 Memory 设计方案

**研究主题：** 基于诊断预条件化的持续 Skill 自进化（Continual Skill Evolution through Diagnostic Preconditioning）

**状态：** 正式 Prompt、Replay／Memory 实现、离线回归、首次真实响应学习与有 Memory 的 Preconditioner 对照已完成；跨轮修订及行为收益尚未验证

**更新日期：** 2026-10-18

**设计范围：** Replay 的输入输出、MemoryEntry 的形成与修订、历史记忆维护、Preconditioner 的 Memory 输入及使用

本方案在 [V22 全流程简化方案 §2.4、§6](../v22/UNIFIED_DSC_WORKFLOW_SIMPLIFICATION.md) 的候选机制基础上，确定 V23 使用 `MemoryEntry / entries / knowledge`。本版输出进一步收敛为 `entries`，每条提案只有 `revises / knowledge / evidence`，不保留独立 `updates` 或 `unresolved` 字段。

上游接口参见 [Preconditioner 设计](PRECONDITIONER_DESIGN.md) 与 [Editor 设计](EDITOR_DESIGN.md)。当前实现支持 `memory: {entries, sources}`。旧实验的 Prompt、请求、输出及 `memory=[]` 原样保留，通过已冻结旧契约只读核验。实际结果与限制见本文 §13。

## 1. 设计目标与整体思路

### 1.1 核心目标

本方法希望从 Agent 的实际执行中持续学习：

> 什么样的 Skill 编辑，在什么条件下，会伴随什么行为响应；新的执行证据又怎样改变我们对这种编辑作用的认识？

这些认识在下一轮更新时参与预条件化，使系统不只是根据当前诊断生成新的 Skill 修改，还能够根据过去实际观察到的编辑效果，调整当前更新的方向、范围、强度或关联方式。

因此，Memory 的核心不是记录任务经验，也不是保存历史修改清单，而是维护**可持续修订的条件化编辑—行为响应认识**。

### 1.2 整体机制

```text
当前 Parent Skill
       │
       ▼
Grouping → Diagnosis
                  │
                  │ Original Plan
                  ▼
             Preconditioner ← Active Memory
                  │
                  │ Effective Plan
                  ▼
                Editor
                  │
                  │ Patch
                  ▼
         Candidate Skill
                  │
                  ▼
       Parent/Candidate 配对执行
                  │
                  ▼
      执行证据与配对条件核验
                  │
                  ▼
                Replay
                  │
                  │ entries
                  ▼
          Memory 确定性维护
                  │
                  ▼
             Active Memory
                  │
                  └────→ 下一轮 Preconditioner
```

其中：

- **Diagnosis：** 提出当前希望改变的行为与初步更新要求。
- **Preconditioner：** 根据当前证据及历史响应认识，调整原始更新。
- **Editor：** 将 Effective Plan 落实为实际 Skill Patch。
- **Replay：** 对照实际编辑和执行行为，学习或修订编辑作用认识。
- **Memory：** 持续维护这些认识，并提供给下一轮 Preconditioner。

Replay 的响应学习阶段只进行一次模型调用，不再额外设置 Memory Review、Findings Fusion 或独立的知识总结 Agent。

Candidate 的任务执行仍由 Actor 完成，可能包含多次模型调用，不属于上述“一次响应学习调用”的限制。

## 2. Replay 的职责

Replay 要回答：

> 本轮真正修改了哪些 Skill 指导？Parent 和 Candidate 在可比较的执行情境中分别表现如何？这些观察支持我们对编辑作用形成什么新的认识，或怎样修订已有认识？

Replay 不负责：

- 重新诊断原始任务问题；
- 重新决定 Effective Plan；
- 修复 Editor 产生的 Candidate；
- 根据整体成功率直接认定某个编辑有效；
- 将历史经验直接写成下一轮必须执行的 Skill 指令；
- 决定 Candidate 是否晋级为 Parent。

Replay 负责的是**行为响应学习**，而不是再次进行 Skill 更新决策。

需要特别区分三个对象：

| 对象 | 回答的问题 |
|---|---|
| Effective Plan | 本轮原本希望怎样改变 Agent 行为？ |
| Actual Diff | 本轮实际上怎样修改了 Skill？ |
| Parent/Candidate Runs | 修改前后实际观察到了什么行为？ |

Replay 必须以实际 Diff 和真实执行作为作用认识的依据，不能把 Plan 中提出的理想要求直接当成已经实现的编辑。

## 3. Replay 输入设计

### 3.1 输入结构

Replay 采用七个顶层字段：

```json
{
  "parent": null,
  "diff": "Actual unified diff...",
  "plan": {
    "goal": "...",
    "updates": [
      {
        "id": "u1",
        "text": "..."
      }
    ],
    "checks": [
      {
        "id": "c1",
        "update_ids": ["u1"],
        "question": "..."
      }
    ]
  },
  "command_sets": {},
  "runs": [],
  "pairs": [
    {
      "parent": "P1",
      "candidate": "Q1"
    }
  ],
  "memory": {
    "entries": [],
    "sources": {}
  }
}
```

共享 Actor 能力与执行协议继续由现有 `execution_context.md` 提供，通过统一 Prompt 装配函数输入。

### 3.2 各字段含义

| 字段 | 内容 | 用途 |
|---|---|---|
| `parent` | 本轮实际 Parent Skill，允许为 `null` | 理解本次修改的原始基础 |
| `diff` | Parent 到 Candidate 的实际文本差异 | 确定真正写入的编辑 |
| `plan` | Effective Plan 的行为目标、更新要求与 Checks | 理解期望响应及观察重点 |
| `command_sets` | Actor 执行时可见的动作候选列表 | 判断某一决策点实际有哪些可用选择 |
| `runs` | 本轮完整 Parent/Candidate 执行事实 | 比较实际行为与任务结果 |
| `pairs` | 经程序核验的 Parent/Candidate 配对关系 | 明确哪些执行属于对应任务 |
| `memory` | 当前有效 MemoryEntry 及必要历史证据 | 判断新增、修订还是保留历史认识 |

### 3.3 Plan 的使用边界

`plan` 来自 Preconditioner 的 Effective Plan。

Replay 使用其中的：

- `goal`：整体希望改善和保留的行为；
- `updates[].id/text`：最终更新要求；
- `checks[].id/update_ids/question`：重要的执行后观察问题。

这是供 Replay 使用的精简读取视图，不修改程序归档中的正式 Effective Plan。

Checks 用来提醒模型关注哪些行为，并不要求逐条产生 MemoryEntry。

**Check 本身不是执行证据。**

Replay 必须根据真正发生的行动、反馈和结果判断是否观察到了相关行为。

### 3.4 实际 Diff 与 Candidate 的关系

Replay 不额外传入完整 `candidate`。

原因是：

- 程序已经保存准确的 Parent、Candidate 和实际 Diff；
- Replay 可以通过 Parent 与 Diff 理解真实修改；
- 重复输入完整 Candidate 会增加输入内容。

程序在调用前必须核对实际 Diff 与已保存的 Parent/Candidate 版本一致。

完整 Candidate 仍然长期归档，供执行、复现与审计使用。

**若 Diff 不能与已保存的实际版本对应，则不能启动本轮响应学习。**

### 3.5 执行事实与配对

`runs` 沿用 V23 已有的执行事实结构，不重新设计轨迹表示。

每个执行步骤保留：

```text
before → action → after
```

并通过 `command_sets` 获取该步 Actor 实际可见的动作候选。

Parent 保留 `P1:3` 等执行引用；Candidate 使用独立引用，例如 `Q1:3`。

`pairs` 明确保存 `P1 ↔ Q1` 等对应关系。

程序在模型调用前核验可比较性，包括任务身份、初始状态、Actor 配置、执行协议和预算等必要条件，并将核验结果归档。Skill 的 Parent／Candidate 差异是预期比较对象；其他条件不能仅凭任务名称相同就视为一致。无法核验时保留阻碍，不把未经确认的配对当成可靠对照。

内容相同不等于执行身份相同。即使两侧动作和观察完全一致，也保留各自真实执行及请求来源；共享菜单或其他内容不会合并两次执行。不同长度、不同路径的轨迹不强行逐步对应。

但需要注意：

**相同任务配对，不代表 Parent 和 Candidate 在中间每一步都处于相同状态。**

Replay 应比较真实的行为选择与可观察条件，而不是强行逐步对齐两条不同长度的轨迹。

完整执行证据应保留，包括成功、失败、重复动作、提前停止、未遵循新规则等情况。首版不增加关键步骤语义筛选或独立轨迹摘要模型。

### 3.6 不需要的输入

首版不输入以下信息：

| 字段 | 不输入的原因 |
|---|---|
| `original_plan` | 本轮学习对象是最终实际编辑的行为响应，不是原始提案的未执行效果 |
| `adjustments` | 预条件化决策来源已归档，不必在 Replay 中重新分析 |
| `candidate` | 与 Parent 和实际 Diff 所表达的文本信息重复 |
| `grouping` | Replay 直接分析完整配对执行，不依赖原 Parent 分组重新组织 |
| 完整历史 `contexts` | 历史按 Active 条目的明确引用装配原始证据及其依赖上下文，不读取整个 Archive |

这些材料不从实验档案中删除，只是不进入每次 Replay 的常规模型输入。

原始 Plan、Adjustments 与 Effective Plan 的来源链仍完整保存，供后续研究预条件化如何影响实际编辑时使用。这里细化了 Preconditioner 设计中的来源追溯要求：保留来源链，不等于每次响应学习都必须把整条来源链交给模型。

## 4. Replay 输出设计

### 4.1 最小输出格式

Replay 直接输出本轮提出的 Memory 更新：

```json
{
  "entries": [
    {
      "revises": [],
      "knowledge": "A complete, evidence-grounded understanding of an edit–behavior relationship.",
      "evidence": ["diff", "P1:8", "Q1:10"]
    }
  ]
}
```

顶层只有 `entries`。

每个 MemoryEntry 提案只有三个字段：

| 字段 | 含义 |
|---|---|
| `revises` | 本条新认识替代哪些已有有效 MemoryEntry；空数组代表新增 |
| `knowledge` | 完整、可复用、带条件与边界的编辑—行为响应认识 |
| `evidence` | 支撑该认识的实际编辑和执行证据引用 |

不单独输出：

- `summary`
- `findings`
- `responses`
- `checks`
- `unresolved`
- `updates`
- `confidence`
- `limitations`
- D/S/C 分类字段

这些内容不应成为新的复杂输出结构。

### 4.2 Knowledge 的内容要求

`knowledge` 是 Memory 最核心的内容。

它应当形成一项自足的认识，说明：

1. **实际编辑：** 修改了什么指导。
2. **作用条件：** 在什么可观察条件下考察修改。
3. **行为响应：** Parent 和 Candidate 表现出什么差异或一致性。
4. **作用认识：** 这些观察对编辑效果提供了什么支持或反证。
5. **证据边界：** 哪些情况仍未知，哪些作用无法单独归因。

这些是自然语言认识应考虑的内容，不要求拆成五个字段或固定五句话。

例如，以下是**假设案例，并非当前已运行的实验结果**：

> 在近期操作重复访问同一位置、观察未变化且仍存在其他可用搜索位置时，加入避免近期重复访问的搜索指导后，Candidate 转向了其他位置，而 Parent 继续重复访问。本次对照支持该组合指导可能促进搜索转移，但尚未检验候选位置耗尽后的行为，也无法区分同时新增的各项搜索要求的独立作用。

这种认识可以跨任务使用，因为它关注行为条件与编辑作用，而不是某个具体任务答案。

### 4.3 不只学习成功与失败

Replay 应关注：

- 预期行为是否发生；
- 旧问题是否仍然存在；
- 是否出现新增退化；
- 原有有效行为是否保留；
- Candidate 是否实际遵循新指导；
- 相关条件是否真正出现；
- 同样编辑在不同情境下是否表现不同。

一次任务成功，不代表所有编辑都有效。

一次任务失败，也不代表所有编辑都无效。

如果多条规则同时修改，而执行证据无法分离各自的作用，则记录它们的**联合响应**，不能人为分配独立贡献。

对于随机性较强的配对差异，应保留归因不确定性，不能将一次观察描述为已证明的因果规律。

### 4.4 证据与对象关联的边界

`evidence` 引用实际编辑和执行事实。Memory ID 用于 `revises` 指定认识修订对象；历史认识本身不能代替其原始事实。Check 和 Plan 表达观察问题与更新意图，也不能代替行为证据。

一条编辑—行为响应认识应有相应的实际编辑和执行依据。程序校验引用类型和存在性；认识是否得到充分支持，由模型分析并通过真实验证核查，不增加自然语言评分器。

删除 `updates` 不表示删除更新来源：完整 Effective Plan 仍在本轮归档中，`knowledge` 应自足地说明实际修改对象，`evidence` 指向真实编辑。删除 `unresolved` 后，相关未知写入认识；没有可形成的认识时允许不更新，不为逐项回答 Checks 增设报告对象。

### 4.5 允许不更新 Memory

当本轮没有值得新增或修订的响应认识时，Replay 可以返回：

```json
{
  "entries": []
}
```

这属于正常输出。

不强制每个 Check、每条 Update 或每条执行轨迹产生一条 Memory。

没有观察机会、证据不充分、行为差异无法支持有意义的认识，或者新证据没有实质改变当前理解时，都可以不更新。

已有完整轨迹、Checks 和模型结果仍在实验档案中。

## 5. Memory 的长期保存格式

Replay 生成的是本轮 Memory 更新提案；程序验证并提交后，才形成长期 MemoryEntry。

### 5.1 正式 MemoryEntry

程序补充稳定身份及上下文：

```json
{
  "id": "M1",
  "context_id": "R1",
  "revises": [],
  "knowledge": "...",
  "evidence": [
    "R1/diff",
    "R1/P1:8",
    "R1/Q1:10"
  ]
}
```

其中：

- `id`：MemoryEntry 的唯一身份；
- `context_id`：认识形成的实验轮次；
- `revises`：被本条认识替代的历史有效条目；
- `knowledge`：模型形成的完整认识；
- `evidence`：解析到实际实验上下文的证据引用。

模型不负责分配 `id` 或 `context_id`。

例如，模型输出的当前轮引用：

```text
diff
P1:8
Q1:10
```

程序可以保存为：

```text
R1/diff
R1/P1:8
R1/Q1:10
```

这样跨轮次引用不会混淆。

对于来自不同实验的记录，还应保留对应实验身份，不能仅依赖不同实验中可能重复出现的 `R1`。

### 5.2 Archive 与 Active Memory

长期维护分为两个部分：

**Archive：完整历史档案**

保存所有曾经产生的 MemoryEntry，以及对应的实验、实际编辑和行为证据。

历史条目不可原地修改或删除。

**Active Memory：当前有效认识集合**

保存当前应被下一轮 Preconditioner 使用的 MemoryEntry 身份。

例如：

```json
{
  "active_ids": ["M2", "M3"]
}
```

这表示 M2、M3 是当前有效版本。

Archive 中可能还存在 M1，但 M1 已被后续认识替代，不再作为独立有效认识输入。

这里的“有效”不意味着已经科学证明正确，而是表示**目前采用的最新认识版本**。

### 5.3 Active Memory 的维护规则

程序依据 Replay 的 `revises` 直接更新 Active，不使用额外的评分、检索或 LLM 判断。

| Replay 输出 | 程序操作 |
|---|---|
| `revises: []` | 创建新 M ID，加入 Active |
| `revises: ["M1"]` | 创建新 M ID，从 Active 移出 M1 |
| `revises: ["M1","M3"]` | 创建一条完整合并认识，替代 M1 和 M3 |
| 某个 Active 条目未被提及 | 保持原样 |
| `entries: []` | Active 不变 |

其逻辑可以表示为：

\[
A_{t+1}=(A_t-\operatorname{Revised}_t)\cup\operatorname{New}_t
\]

其中 \(A_t\) 是当前 Active Memory ID 集合。

所有修订都基于 Replay 调用前的同一份 Active 快照。

程序需要确定性检查：

- `revises` 只能引用输入中有效的旧条目；
- 同一旧条目不能在同一轮被重复修订；
- 不允许在同一轮内形成新条目之间的修订链；
- `evidence` 必须引用存在且可解析的证据；
- `knowledge` 必须为非空文本；
- 全部提案验证通过后，才一次性提交 Archive 和 Active 更新；
- 验证失败不得部分更新 Memory。

程序不根据 `knowledge` 文本相似度自动决定合并或替代对象。

## 6. Memory 的新增、修订与合并原则

这是 Memory 机制的关键，不应简化为“每轮追加经验”。

### 6.1 什么情况下新增？

当实际编辑与行为对照产生一项尚未被现有 Memory 充分表达的关系时，创建新的 MemoryEntry。

例如已有认识主要讨论搜索重复，而本轮首次观察到某种清洁流程编辑与顺序行为的关系，可以新增独立认识。

### 6.2 什么情况下修订？

当新证据改变了对已有编辑作用的理解时，应修订原条目。

典型情况包括：

- 发现原认识的适用条件更窄；
- 发现不同条件下存在不同响应；
- 发现旧认识忽略了副作用；
- 新证据支持扩大原认识的适用范围；
- 原来的行为解释被反证；
- 多条认识存在需要联合表达的实际关联。

修订不是简单追加一句限制，也不是用最新结果直接覆盖旧结论。

### 6.3 修订必须输出完整新认识

假设 M1 记录：

> 在仍存在其他可用搜索位置时，加入避免近期重复搜索的指导，曾伴随探索转移。

后续又观察到更强的禁止回访指导在环境状态变化后可能妨碍必要回访。

Replay 可以输出：

```json
{
  "entries": [
    {
      "revises": ["M1"],
      "knowledge": "在近期重复访问且仍有其他可用位置时，局部防重复指导曾伴随搜索转移；但新一轮将限制扩大到状态变化后的回访情境时，观察到必要回访被跳过。两轮实际修改的范围不同，现有证据支持区分无反馈重复和状态变化后的合理回访，而不支持无条件禁止全部回访。",
      "evidence": [
        "R1/diff",
        "R1/P1:8",
        "R1/Q1:10",
        "diff",
        "P1:6",
        "Q1:7"
      ]
    }
  ]
}
```

这是形成于后续轮次的假设输出，因此同时引用历史和当前证据。

程序创建 M2，替代 M1 的有效位置。

新 M2 是**完整的当前认识**。下一轮不需要同时读取 M1 和 M2，再次推导应该怎样合并。

### 6.4 如何防止错误覆盖历史认识？

当新证据与旧认识不一致时，Replay 应首先比较：

- 实际编辑是否相同；
- 作用范围是否发生变化；
- 行为条件是否一致；
- 是否存在新的反例；
- 原解释是否仍得到已有证据支持。

如果旧观察仍然成立，新认识应保留它并说明新的边界。

如果旧解释已被反证，应明确纠正，而不是机械继承。

历史条目与证据始终在 Archive 中保存，保证这种修订可以回溯。

但程序的引用校验不能自动证明自然语言认识正确。这属于 Replay 模型需要通过真实实验检验的学习能力。

### 6.5 不应为了合并而合并

一条 MemoryEntry 应围绕相对完整、可复用的编辑—行为关系。

如果两条认识只是任务相似，但实际修改或作用条件不同，不必强行合并。

只有当多条认识确实能够被一份更准确的条件化作用认识替代时，才使用多个 `revises`。

不设置固定 Memory 数量、置信度分数或复杂生命周期状态。

## 7. 输入 Preconditioner 的 Memory 格式

### 7.1 统一读取结构

Replay 和 Preconditioner 共用同一种 Memory 读取格式：

```json
{
  "memory": {
    "entries": [
      {
        "id": "M2",
        "knowledge": "...",
        "evidence": [
          "R1/diff",
          "R1/P1:8",
          "R1/Q1:10",
          "R2/diff",
          "R2/P1:6",
          "R2/Q1:7"
        ]
      }
    ],
    "sources": {
      "R1/diff": {"parent": null, "diff": "...", "execution_context": {}},
      "R1/P1": {"run": {}, "command_sets": {}},
      "R1/Q1": {"run": {}, "command_sets": {}},
      "R2/diff": {"parent": "...", "diff": "...", "execution_context": {}},
      "R2/P1": {"run": {}, "command_sets": {}},
      "R2/Q1": {"run": {}, "command_sets": {}}
    }
  }
}
```

这里的省略号及空对象仅表示格式位置；实际输入必须使用已保存的原始 Diff 和执行事实，不能留空或生成概括性占位内容。

### 7.2 `entries` 的作用

`entries` 是从 Archive 中读取的**当前 Active MemoryEntry**。

每条只需要：

| 字段 | 作用 |
|---|---|
| `id` | 标识历史认识，供 Preconditioner 的 Adjustment 引用 |
| `knowledge` | 当前关于编辑—行为响应的完整认识 |
| `evidence` | 当前认识明确依赖的历史事实引用 |

不需要每次把 `revises`、`context_id` 和全部版本链输入 Preconditioner。

这些属于程序的长期维护信息，必要时可以在 Archive 中追溯。

### 7.3 `sources` 的作用与装配粒度

`knowledge` 是对历史事实的解释，`sources` 提供核对该解释所需的原始证据。它是按 Active 条目引用临时装配的共享来源表，不是另一份 Memory，也不是模型生成的摘要。

**引用精确到步骤，读取不必只剩下一个步骤。** 例如，“重复访问减少”需要连续行为，“原有清洁顺序保持”需要动作先后关系；孤立步骤不能充分展示这些事实。

首版采用以下确定性装配规则：

| 引用对象 | 提供的原始材料 |
|---|---|
| 执行、初始状态、步骤或 outcome 引用 | 对应的完整执行，包括任务、初始状态、全部有序步骤、反馈、结果和终止原因，以及其引用的 Actor 可见动作菜单与真实执行身份 |
| 实际编辑引用，如 `R1/diff` | 对应的实际 Parent、实际 Diff 和该轮真实 Actor 执行背景；完整 Candidate 继续归档，程序核验其与 Parent／Diff 的一致性 |
| 同一执行或编辑被多个条目引用 | 只装配一次，共享同一份原始来源 |

历史执行所需的真实 Actor 配置和协议应能够随来源核对，不能用当前默认配置代替历史事实。当前轮与历史轮的菜单及执行编号必须有各自命名空间。

`evidence` 保留精确引用，模型据此定位完整执行中的具体事件；不因装配完整执行而把整条轨迹都宣称为该认识的支持证据。§7.1 中 `R1/P1:8` 的证据引用在 `sources["R1/P1"].run` 中解析；同一执行只展开一次。历史菜单在该来源自身的 `command_sets` 中解析，不与当前菜单编号混淆。

首版不按自然语言判断“附近几步足够”，不增加片段筛选器。这里展开的是被引用事实的原始依赖上下文，不自动读取该历史轮次的其他未引用执行。

### 7.4 为什么不直接读取整个 Archive？

Archive 包含已被修订的旧认识和全部历史执行。每轮读取整个 Archive 会重复输入旧版本，也可能让已被纠正的解释重新干扰模型。

首版采用：

> **全部当前 Active MemoryEntry + 明确引用的原始来源及上述确定性依赖上下文。**

不沿 `revises` 链递归读取所有旧版本，不自动展开某个历史轮次的全部执行；但一个历史执行被引用时，提供它的完整记录。

如果新认识继续依赖旧观察，模型应在新条目的 `evidence` 中明确保留相应历史引用。程序不机械继承全部旧证据，也不替模型补齐遗漏的语义依据。旧条目及旧证据仍在 Archive 中，供追溯。

这种装配方式不能自动保证认识完整或正确。输入中没有展示的历史执行，不代表没有发生；模型不能把来源缺席当成反证。

### 7.5 空 Memory 的表示

当没有历史认识时：

```json
{
  "memory": {
    "entries": [],
    "sources": {}
  }
}
```

现有 Preconditioner 的顶层字段保持不变，只将原先占位的 `memory=[]` 统一为正式读取结构。

已冻结的无历史实验保留原样，不回写旧结果。

### 7.6 Archive 到 Preconditioner 的选择过程

需要区分两个步骤。

**第一步：Archive → Active Memory**

这是版本选择。

由 Replay 的 `revises` 和程序维护的 `active_ids` 确定。

不使用模型重新筛选。

**第二步：Active Memory → Preconditioner**

首版读取全部 Active 条目和必要证据。

Preconditioner 自己判断哪些认识与当前 Update 的编辑方向、行为条件和作用范围相关。

不因为某项历史认识被提供，就必须根据它修改当前 Update。

首版不引入独立 Memory 检索 Agent，也不预设按任务类型选择记忆。

如果后续有效 Memory 大量增长，导致实测输入成本不可接受，再研究相关认识选择与证据装配优化。

## 8. Memory 如何支持诊断预条件化

这部分是 Memory 与论文创新点的直接联系。

### 8.1 Memory 学习的不是任务规则

例如，普通任务经验可能是：

> 搜索物体时应该避免重复打开同一个柜子。

而编辑—行为响应认识应该是：

> 在近期观察不变、仍有其他可选位置的情境中，加入避免近期重复搜索的指导后，Candidate 曾表现出搜索转移；但将限制扩大为无条件禁止回访后，又观察到了状态变化情境下的必要回访缺失。

前者是直接指导 Agent 执行动作。

后者说明**改变 Skill 指导可能产生什么行为影响**。

这是两种不同的知识对象。

### 8.2 Preconditioner 如何使用 Memory

假设下一轮 Diagnosis 提出：

> 目标没找到时，禁止回访所有已检查位置。

Preconditioner 读取当前 M2，了解到历史上：

- 有其他搜索选择时，局部防重复编辑曾伴随探索转移；
- 状态变化后，过强的禁止回访限制曾伴随必要回访缺失。

Preconditioner 因此可以将原始 Update 调整为：

> 在近期重复操作未产生新反馈、且当前仍有其他合理搜索选择时，优先探索其他位置；当环境状态发生变化并提供新的操作机会时，不应仅因为此前访问过该位置就禁止回访。

这个变化主要体现在：

- **Direction：** 保留有效探索的修订方向。
- **Scale：** 调整禁止回访的适用条件与强度。
- **Coupling：** 协调避免无效重复和允许必要回访两个行为要求。

D/S/C 是分析修改作用的维度，不需要新增独立 Memory 字段。

### 8.3 通过现有 Preconditioner 输出落实

可以沿用已经实现的 Adjustments 接口。

例如，以下只展示一项假设 Adjustment：

```json
{
  "from": ["u1"],
  "to": [
    {
      "id": "u1",
      "text": "Avoid repeated searches when observations remain unchanged and another reasonable admissible search choice is available. Allow reconsideration of a previously visited location when a new observable state change provides a relevant opportunity."
    }
  ],
  "basis": ["M2"],
  "reason": "Historical paired evidence indicates different responses under unchanged and changed environment states."
}
```

Preconditioner 仍根据整体输入决定：

- Keep；
- 调整方向；
- 收窄或扩大作用条件；
- 协调或合并要求；
- 撤回缺乏合理实施基础的原始修改。

这些决定必须与当前问题及历史依据相符，不强制每次产生非恒等变换。

**Memory 的价值不在于让 Preconditioner 总是改动 Plan，而在于帮助它作出更有依据的更新变换。**

同时，历史响应属于观察证据，不自动构成强因果证明。

## 9. 与 Gate 和持续演化的关系

Replay 的 Memory 学习与 Candidate 是否被采用，应当明确分开。

- **Gate：** 决定 Candidate 是否晋级为下一轮 Parent。
- **Replay/Memory：** 决定本轮哪些实际编辑响应值得形成或修订认识。

Candidate 即使没有通过 Gate，也可能提供有价值的修改失败、副作用或局部改善证据。

Candidate 即使被采用，也不意味着它的每条规则都正确，更不意味着对应的 Memory 永久有效。

完整系统需要在推进下一轮时，保存一致的 Skill 状态、Memory 快照和轮次来源。

当前 Gate 尚未在 V23 中正式实现，本阶段不需要为了 Memory 再增加 Gate 算法，也不预先锁定 Gate 与 Replay 的所有运行顺序。只需保证：

**Memory 学习必须基于实际发生、来源可核验且配对条件得到确认的执行；候选是否采用，不改变历史事实。**

“实际发生”不要求任务成功，也不要求一定正常终止。技术中断时保留已发生步骤、原始错误与真实终止原因，不能把它改写成正常任务失败，也不能补造后续动作或结果。某段实际观察是否足以支持局部响应认识，由其证据范围决定。

任务身份或执行配置无法确认，与一条已核验执行在中途技术中断，是不同问题。前者不能冒充可靠配对；后者不能抹去已经发生的事实。两者都不能被解释成已证明某项 Skill 编辑有效或无效。

没有合法 Candidate 或有效配对执行时，不生成虚构的编辑响应记忆。

## 10. 实现与验证建议

建议按以下顺序实现，避免一次性进入完整自进化实验。

### 10.1 第一阶段：Memory 数据维护

先完成确定性功能：

- Archive 保存；
- Active ID 维护；
- 新增、单条修订和多条合并；
- 引用及版本冲突检查；
- 跨轮次证据身份；
- 原子提交；
- `entries + sources` 读取视图，包括完整被引用执行、菜单、历史 Parent／Diff 和真实执行背景；
- 多条 Memory 共享来源的确定性去重，以及跨实验、跨轮次引用不混淆；
- 验证失败时 Archive／Active 均不部分改变，同一已提交结果复用不重复创建条目。

使用人工构造的合法与非法输入做离线测试，不调用模型。

### 10.2 第二阶段：Replay 输入与 Prompt

沿用 V23 的执行事实结构，完成：

- Parent/Candidate 配对读取；
- 实际 Diff 与 Candidate 身份核验；
- 完整执行及动作候选装配；
- 当前 Active Memory 读取；
- Replay 一次模型调用；
- `entries` 严格结构验证与原始响应归档。

Prompt 重点要求：

1. 根据实际编辑而非理想 Plan 分析作用。
2. 比较有真实证据的行为条件与结果。
3. 区分观察、可能的编辑作用和归因限制。
4. 对相同作用认识进行有依据的修订。
5. 不强制每轮新增 Memory。
6. 直接输出 Memory 更新提案，不生成中间分析报告。

### 10.3 第三阶段：首次真实 Replay

复用当前已生成的 V23 Candidate Skill，在固定任务与执行配置下进行 Parent/Candidate 配对验证。

重点观察：

- 实际搜索策略是否改变重复搜索行为；
- 清洁顺序表达是否影响实际操作；
- admissible action 恢复指导是否被使用；
- 是否存在新增退化；
- Replay 是否能够区分实际修改与 Effective Plan 的意图。

首次 Memory 为空，重点验证**新认识的形成**。

不能因为第一次模型输出格式正确，就认定 Memory 学习已经有效。

### 10.4 第四阶段：跨轮修订和非空 Memory 预条件化

后续使用新的配对证据，验证：

- Replay 能否在新反例出现时合理修订旧认识；
- 仍然成立的旧观察是否被保留；
- Archive 与 Active 是否正确更新；
- 下一轮 Preconditioner 能否读取非空 Memory；
- Memory 是否产生与历史证据相符的非恒等 Update 变换；
- 变换后的 Candidate 是否带来可观察的行为改善或减少退化。

可以固定同一 Parent、Diagnosis Plan 和执行证据，分别进行无 Memory、有 Memory 的 Preconditioner 对照。

但不能将“产生了 Adjustment”本身当作效果证明，最终仍需要实际 Replay 观察行为。

### 10.5 阶段边界与验证要求

正式英文全文现保存于 [replay_prompt.md](../../../src/skill_evolution/v23/replay_prompt.md)，使用统一 execution_context 装配；不追加当前实验中特定 Update 的修补规则。实现与真实验证按用户授权的固定预算执行，结果见 §13。

离线测试应覆盖新增、修订、合并、空输出、非法和重复修订目标、历史与当前证据解析、完整来源还原、精确 Diff 对应、配对条件不一致、技术中断及原子提交。JSON、契约或调用失败必须保留原始请求、响应和错误，不能伪装成合法的 `entries: []`。

真实验证区分三个层次：结构可读取和可提交；认识是否忠实于编辑与执行；历史认识是否帮助后续更新并产生行为收益。前一层通过不代表后一层已经成立。正式调用前冻结输入、配置和调用次数，保留完整成本与输出；不因结果不理想自动重采样。

## 11. 最终接口汇总

| 环节 | 最终设计 |
|---|---|
| Replay 输入 | `parent / diff / plan / command_sets / runs / pairs / memory` |
| Replay 输出 | `entries: [{revises, knowledge, evidence}]` |
| 正式 MemoryEntry | `id / context_id / revises / knowledge / evidence` |
| Memory Archive | 所有历史条目及实验来源，不可覆盖 |
| Active Memory | 当前有效的 MemoryEntry ID 集合 |
| Memory 读取视图 | `memory: {entries, sources}` |
| Replay 使用 Memory | 决定新增、修订、合并或保持认识 |
| Preconditioner 使用 Memory | 判断历史作用认识的适用性，调整当前 Update |
| 历史证据读取 | 展开 Active 条目引用的完整执行及菜单、编辑及其 Parent／执行背景；共享去重，不递归读取整个 Archive |
| 学习调用次数 | 每批配对执行后最多一次 Replay 模型学习调用，首版不增加独立 Memory Review |

## 12. 设计结论

本机制以**条件化 Skill 编辑—行为响应认识**作为长期 Memory 的基本单位。

Replay 直接通过实际 Diff 和 Parent/Candidate 配对执行学习响应，输出新增或修订的 MemoryEntry。

程序保留所有历史版本及原始证据，通过明确的 `revises` 关系维护当前 Active Memory，不额外参与自然语言认识的合并和判断。

Preconditioner 读取当前有效认识与必要原始证据，判断历史修改的作用条件是否适用于新的诊断问题，进而调整原始 Skill 更新的方向、范围、强度或关联。

整个机制不依赖复杂的 Memory 状态机、评分体系、额外审核 Agent 或逐轮全文历史重读。

**核心研究主张：系统不仅从 Agent 执行结果中提出 Skill 修改，还通过真实配对执行持续学习这些修改的条件化行为响应，并将不断修订的响应认识用于预条件化后续 Skill 更新，从而形成持续校准的 Skill 自进化闭环。**

## 13. 正式实现与双阶段验证 2026-10-18

实现为 [replay.py](../../../src/skill_evolution/v23/replay.py) 和 [memory.py](../../../src/skill_evolution/v23/memory.py)，接口用法见 [V23 源码说明](../../../src/skill_evolution/v23/README.md)。本次没有修改 Actor 执行协议，也没有实现 Gate。

Memory Archive 使用按轮不可变提交文件，保存正式五字段 Entry、原始提案和真实上下文；Active 索引包含 `active_ids` 和已提交上下文列表。提交在文件锁内先写不可变文件，再原子切换索引；中断文件不进入有效视图，相同输入可恢复，同轮重复提交不产生新 ID。全部提案先校验，不部分激活。此持久化布局不是新增模型输出字段。

旧 Preconditioner 的 `memory=[]` 档案通过旧冻结 Prompt 只读验证；新调用仅装配 `memory: {entries, sources}`。历史事实通过 `sources` 还原；Adjustment 的 basis 可引用有效 M ID，Effective Update 的 basis 继承规则保持不变。

离线运行前 432 项测试与 19 个子测试通过；真实运行后增加两项产物交接检查，最终 **434 项测试与 19 个子测试通过**。

- [报告 A：Replay／Memory](../../../experiments/methods/v23/v23_replay_memory_001/reports/REPORT.md)：复用四条 Parent 的 93 步，未修改 23 行 Candidate；新增四条 Candidate／133 步，2 成功、2 达到步数上限。唯一一次 Replay 学习产生 3 条 Memory，Active 为 M1／M2／M3，读取视图展开 9 个共享来源。真实同轮复用零新增调用、零重复条目。
- [报告 B：有 Memory 的 Preconditioner](../../../experiments/methods/v23/v23_preconditioner_with_memory_001/reports/REPORT.md)：相同新 Prompt 和当前输入，仅 memory 不同，两侧各调用一次。空侧 Keep，真实侧引用 M1／M2 调整 u1／u3、保留 u2，程序生成 Effective Plan。没有执行该新 Plan。

M1 的搜索响应、M2 的相同非法动作、M3 的清洁子流程保持均有真实依据，但 M3 的列举和范围表述仍需谨慎解读。真实 Preconditioner 输出仍有全局访问历史依赖、因果措辞过强和未验证搜索策略等问题。原始结果不修补、不重采样。

该对照使用同批任务的历史响应回看原 Plan，不能证明独立跨轮泛化；两次随机生成的差异也不能完全归因于 Memory。真实跨轮认识修订、长期 Memory 质量、新调整的行为效果及完整演化状态推进仍未验证。
