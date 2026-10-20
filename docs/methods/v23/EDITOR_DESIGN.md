# V23 Editor 设计方案

- **研究主题：** 基于诊断预条件化的持续 Skill 自进化
- **状态：** 正式英文 Prompt、代码实现和离线回归已完成；单次真实补丁应用失败，未生成 Candidate，详见验证报告
- **更新日期：** 2026-10-18
- **范围：** Editor 的职责、输入输出、Skill 编辑方式、Patch 应用及验证
- **设计原则：** 局部编辑、忠实落实、保留已有能力、接口简洁

## 1. 模块定位

Editor 接收当前 Parent Skill 和 Preconditioner 形成的 Effective Plan，将全部有效 Updates 联合落实为一份可应用的 Skill 修改补丁（Patch）。

它主要回答：

> 为了忠实落实最终确定的行为更新要求，当前 Parent Skill 中哪些内容需要新增、替换或删除？

整体流程：

```text
Diagnosis
    ↓
Preconditioner
    │
    │ Effective Plan
    ↓
Editor ← Parent Skill
    │
    │ Unified Diff Patch
    ↓
程序严格应用 Patch
    │
    │ Candidate Skill
    ↓
Candidate Replay
```

**Editor 负责落实更新，不负责重新决定更新。**

Diagnosis 已经提出原始更新，Preconditioner 已经完成必要的方向、范围、强度和关联调整。

Editor 不应再次修改这些决策，也不需要读取历史 Memory 来重新判断更新是否合理。

本设计采用 **局部 Patch 编辑**，而不是让模型每轮重新生成完整 Skill。

## 2. 输入设计

### 2.1 输入结构

Editor 的模型数据输入只有两个字段：

```json
{
  "parent": null,
  "plan": {
    "goal": "...",
    "updates": [
      {
        "id": "u1",
        "text": "A complete, actionable behavioral requirement.",
        "basis": ["G2", "P2:21"]
      }
    ],
    "checks": [
      {
        "id": "c1",
        "update_ids": ["u1"],
        "question": "An important behavioral response to examine."
      }
    ]
  }
}
```

| 字段 | 内容与用途 |
|---|---|
| `parent` | 当前 Parent Skill 的完整正文；`null` 表示当前没有 Skill |
| `plan` | Preconditioner 输出并经程序编译的 Effective Plan |

Editor 直接使用 `load_preconditioner()` 返回的 `effective_plan`，不重新生成另一份 Editor Plan。

总 Prompt 继续通过 V23 的 `prompts.py` 装配唯一的 `execution_context.md`，不单独维护一套 Actor 能力说明。共享执行背景包括：

- 当前观察、Actor 可见动作候选及最近两组行动前观察与动作。
- 无完整执行历史、无可写持久笔记、不可访问隐藏评估状态；单次执行中 Skill 固定。
- 本批真实执行的基础系统指令、初始输入模板、历史输入模板及步数上限。

这些内容来自对应执行保存的 `background`，不能用当前默认配置替代历史配置。共享执行背景放在总 Prompt 中，不是第三个模型数据字段：

```text
system：Editor 职责 + 共享执行背景 + 编辑规则 + 输出格式
user：{"parent": ..., "plan": ...}
```

模型输出与最终 Skill 使用英文，正式 Prompt 见 [editor_prompt.md](../../../src/skill_evolution/v23/editor_prompt.md)。

只有 Preconditioner 返回 `ready` 且 Effective Plan 非空时，程序才调用 Editor。`parent` 来自同一份已核验交接中的实际 Parent，不能替换为另一版 Skill。Preconditioner 的 `no_change` 或 `need_evidence` 不进入 Editor。

Preconditioner 的 Keep 表示保留原 Plan，仍需 Editor 落实；Editor 的空 Patch 则表示现有指导已满足全部有效要求，两者含义不同。

**首版不额外输入 `runs`、`command_sets`、`grouping`、`memory` 或原始 Adjustments。**

Effective Update 应当已经是一项自足的行为要求。如果必须重新分析轨迹才能决定实施什么策略，说明上游更新尚不充分，而不是由 Editor 重新完成 Diagnosis。

### 2.2 Effective Plan 如何使用

**Goal**

描述整体希望改善的行为及需要保留的能力。Editor 应据此理解修改目标，避免局部编辑破坏共同保留要求。

**Updates**

这是 Editor 的主要执行依据。

每项 `updates[].text` 应当已经说明：

- 什么条件下需要采取什么策略；
- 适用范围和要求强度；
- 与其他要求的依赖及协调；
- 重要的保留条件和例外。

Editor 需要忠实落实这些要求，不得擅自扩大、收窄或改变其行为含义。

**Basis**

`basis` 用于保留更新来源，但不是让 Editor 重新推导策略的输入。

Editor 不需要根据 `P2:21` 等编号自行猜测执行事实，也不能声称已经查看未提供的轨迹。

**Checks**

Checks 是执行后的行为观察问题。

它可以帮助理解后续关注的行为，但**不是需要写入 Skill 的额外指令**。

Editor 不生成或修改 Checks。

## 3. 输出设计

### 3.1 最小输出结构

Editor 只输出两个字段：

```json
{
  "patch": "...",
  "reason": "A brief explanation of the editing result."
}
```

| 字段 | 含义 |
|---|---|
| `patch` | 对 Parent Skill 的 Unified Diff 修改；也可以是空字符串或 `null` |
| `reason` | 非空字符串，简短说明修改内容、无需修改的原因或无法落实的阻碍；三种合法结果均必填 |

不设置独立的 `decision` 字段。

`patch` 的值直接表达三种结果。

### 3.2 三种输出结果

| patch | 含义 | 程序处理 |
|---|---|---|
| 非空字符串 | 已提出实际 Skill 修改 | 严格应用 Patch，生成 Candidate |
| `""` | 原有指导已充分满足全部 Effective Updates | 无须编辑，保留现有 Parent，不生成新 Candidate |
| `null` | 存在无法忠实落实的必要要求 | 保存阻碍，停止 Editor |

**空字符串、null 和非法 Patch 必须区分。**

仅含空格或换行的字符串不是合法空 Patch，应作为技术性输出失败保存。程序不能先对 Patch 调用 `.strip()`，再把空白字符串转换成 `""`；也不能把无法应用的 Patch 转换成 `null`。

空 Patch 和 null 均不生成新 Candidate，不作为新编辑进入 Candidate Replay；前者正常结束且保持 Parent，后者保存需要上游修订的阻碍。

例如：

**情况 A：已有规则已经满足全部更新要求**

```json
{
  "patch": "",
  "reason": "The Parent Skill and base protocol already satisfy all effective Updates."
}
```

**情况 B：某项要求无法忠实落实**

```json
{
  "patch": null,
  "reason": "Update u2 requires information unavailable to the Actor. Implementing a local approximation would change its intended conditions."
}
```

`null` 不表示 Editor 可以放弃这项要求，而是明确说明需要上游修订。

本版暂不实现自动返回 Preconditioner 的循环。

## 4. Skill 修改方式

### 4.1 统一使用 Unified Diff Patch

新增、替换和删除 Skill 内容，均通过标准 Unified Diff 表达。

不需要分别建立 `add`、`replace`、`delete` 三种模型输出操作。

假设 Parent Skill 为：

```text
## Search
Repeat the same search until the target is found.

## Delivery
Clean the target before delivery.
```

Effective Plan 要求避免无反馈重复搜索。

Editor 可以生成：

```diff
--- a/SKILL.md
+++ b/SKILL.md
@@ -1,5 +1,5 @@
 ## Search
-Repeat the same search until the target is found.
+When repeated inspection provides no new information, consider another reasonable location available from the current observation.
 
 ## Delivery
 Clean the target before delivery.
```

程序将此 Patch 应用于 Parent，生成：

```text
## Search
When repeated inspection provides no new information, consider another reasonable location available from the current observation.

## Delivery
Clean the target before delivery.
```

其中：

- 搜索规则被替换；
- 清洁规则原样保留；
- Editor 不需要重新输出整个 Candidate Skill。

新增规则使用 `+`，删除规则使用 `-`，替换规则同时使用两者。

同一份 Patch 可以包含多个修改位置。

### 4.2 首轮没有 Parent Skill

当 `parent=null` 时，Editor 将 Parent 视为空 Skill 文件，使用标准新文件 Patch 创建 Skill。

例如：

```diff
--- /dev/null
+++ b/SKILL.md
@@ -0,0 +1,2 @@
+## Search
+Avoid repeating actions that provide no new information.
```

只有初始创建时，Patch 可能包含较多新增文本。

后续轮次通常针对已有 Skill 局部修改。

### 4.3 联合落实全部 Updates

Editor 应将 Effective Plan 中的全部 Updates 作为一份联合方案处理。

一项 Update 不必对应一个独立 Skill 段落。

多项 Update 也可以落实在同一处文本中。

例如：

- u1：继续合理探索；
- u2：避免重复执行无反馈动作。

如果两项要求能够形成一条一致的搜索策略，Editor 可以在同一段 Skill 中联合实现。

但这种整合只能改变**文本组织方式**，不能偷偷改变已经确定的策略方向、触发条件或作用范围。

如果其中一项必要要求无法落实，也不能只实施其余要求，再将部分 Patch 当成完整 Candidate。

## 5. Editor 的编辑原则

### 5.1 最小必要修改

Editor 应优先修改与 Effective Updates 直接相关的内容。

已有有效规则应尽量保留。

例如，本轮只需要修改搜索策略，就不应顺便重写清洁、加热或放置流程。

Unified Diff 本身不保证局部性：模型仍可能通过删除全文再添加全文来重写 Skill。因此，局部修改是 Editor 的行为原则。优先保留与本轮 Updates 无关的文本；只有落实更新确实需要时，才调整相关内容的组织方式。

不设置机械的修改比例阈值，也不把 Patch 可应用解释为其他能力已得到保留。

**生成完整 Candidate 是程序的工作；Editor 只需表达必要的文本差异。**

### 5.2 不重复已有指导

如果 Parent Skill 或基础协议已经充分满足某项 Update，不必再重复添加同义规则。

例如，基础协议已经要求选择合法动作，Editor 不应机械复制一条相同指令来增加 Skill 长度。

但如果 Update 同时包含基础协议尚未覆盖的具体恢复策略，可以落实新增部分。

判断依据是 Parent 与基础协议组合起来是否充分满足全部有效要求，而不是某处是否出现过相似语句。如果基础协议包含正确要求，但 Parent 中仍有冲突指导，不能仅凭前者就返回空 Patch；应判断是否需要在本轮要求范围内消除冲突。

如果全部 Updates 均已得到满足，返回 `patch: ""`。

### 5.3 忠实保留更新语义

Editor 可以调整措辞、章节和组织方式，但必须保留有效要求的实际含义，包括：

- 行为策略；
- 触发条件；
- 适用范围；
- 要求强度；
- 重要例外；
- 与其他要求的依赖关系；
- 共同保留边界。

如果原始要求是“在条件 A 下执行动作 B”，Editor 不能擅自写成“始终执行 B”。

如果落实某项 Update 必须改变上述含义，应返回 `patch: null`，说明具体 Update ID 和阻碍原因。

**Editor 不应替代 Preconditioner 进行新的 D/S/C 变换。**

### 5.4 不增加无依据的规则

Editor 不应根据自己的推测，在 Effective Plan 之外新增行为要求。

Candidate Skill 也不应包含：

- 执行编号或来源引用；
- 当前训练任务的具体答案；
- 模型编辑理由；
- 实验成功率或评价结果；
- 对未来任务成功的保证。

最终 Skill 应当是一份能够被 Actor 直接使用的通用行为指导。

## 6. 程序如何应用 Patch

程序负责确定性地生成 Candidate Skill。

```text
Parent Skill
     +
Editor Patch
     ↓
严格校验与应用
     ↓
Candidate Skill
     ↓
保存实际 Diff 与更新来源
```

### 6.1 严格应用

Patch 必须针对输入的准确 Parent Skill。

程序应检查：

1. JSON 输出结构与字段类型合法。
2. 非空 Patch 是合法的 Unified Diff。
3. Patch 只修改目标 `SKILL.md`。
4. 删除行和上下文与 Parent 实际文本一致。
5. 全部 Hunk 能够正确应用。
6. 应用后产生有效且非空的 Candidate Skill，并且实际内容发生变化。

Hunk 必须在声明的位置与准确 Parent 匹配，行数及各 Hunk 的位置关系必须一致；不能搜索另一个相似段落来替代声明位置。多处编辑按 Unified Diff 的原文件／结果文件坐标确定性应用，不因前一处增删造成位置猜测。

不自动偏移定位，不使用模糊匹配、猜测修改位置、自动修复上下文或静默忽略失败 Hunk。只接受目标文件的补丁；已有 Parent 使用 `a/SKILL.md → b/SKILL.md`，`parent=null` 使用 `/dev/null → b/SKILL.md`，不执行补丁中的其他文件操作。

Parent 的空白、换行以及文件末尾是否有换行都属于准确文本的一部分。实现时必须正确处理 Unified Diff 的 `\ No newline at end of file` 标记；不得静默补换行、裁剪空白或转换换行来帮助应用。未修改区域保持原文。

非空 Patch 应产生非空白且实际变化的 Candidate，不能将无效编辑伪装成合法的空 Patch。

**Patch 无法应用属于技术性输出失败，不等于 Editor 合法返回 `null`。**

不因格式失败擅自改变模型生成的 Patch。

### 6.2 保存与追溯

建议程序保存：

| 内容 | 用途 |
|---|---|
| Parent Skill | 实际修改前的版本 |
| Effective Plan | 本轮要求落实的最终行为更新 |
| Editor 原始输出 | 保留模型提交的 Patch 和原因 |
| Candidate Skill | 严格应用 Patch 后的完整 Skill |
| 实际文本 Diff | 记录本轮真实发生的修改 |
| 请求及验证结果 | 保存完整 Prompt、messages、调用配置、原始响应、解析、Token、耗时和错误，支持复现、恢复和成本统计 |

模型 Patch 原文与程序根据 Parent／Candidate 得到的实际 Diff 分别保存，不通过重新生成 Diff 来覆盖或修复模型输出。对空 Patch、null 或技术失败，不伪造 Candidate。

同输入、同 Prompt、同配置的合法结果可以复用；复用时核对同一份 Parent、Effective Plan、执行背景和原始响应，并对非空 Patch 重新严格应用、比对保存的 Candidate。失败结果保留停点，不自动修补或重采样。

不需要模型再输出逐条 Update 映射、文本摘录或修改对照表。

后续 Replay／Memory 可以结合 Effective Plan、实际 Diff 以及 Parent/Candidate 执行，分析本轮编辑与行为响应之间的关系。

程序不需要猜测哪一行独立造成了某项行为改善。

## 7. 验证边界

### 7.1 离线测试

实现时重点验证：

- Parent 为 `null` 时可以创建 Skill。
- 已有 Parent 时正确新增、替换和删除文本。
- 一个 Patch 可以同时修改多个位置。
- 非法 Hunk、错误上下文、错误文件路径被拒绝。
- 重复段落中出现内容匹配但声明位置错误时拒绝，不自动偏移。
- 行数、空白、换行及文件末尾无换行标记正确处理，未修改区域原样保留。
- 非空 Patch 实际产生 Candidate。
- 精确空字符串表示无须修改，仅含空白的字符串属于技术性失败。
- `null` 表示无法落实；三种合法结果均要求非空 reason，阻碍说明定位具体 Update。
- Parent、Plan 和 Patch 的实际版本身份一致。
- 保存结果可以在相同输入和配置下正确复用。
- 上游 Preconditioner 的 Effective Plan 能直接交接，语义停点不调用 Editor。
- 非法 JSON、模型输出截断和补丁应用失败保留原始结果，不转为合法空 Patch 或 null。

不建立额外的语义评分器或审核 Agent。

### 7.2 真实模型验证

首版可以直接复用 V23 已保存的真实 Effective Plan。

模型可能输出：

- 可应用的 Patch；
- 合法的空 Patch；
- 合法的 `null`。

三种情况均应按实际结果处理，不预先要求生成 Candidate。

真实验证需要核查：

1. Patch 是否能够严格应用。
2. 实际修改是否与 Effective Updates 一致。
3. 是否遗漏必要条件或依赖。
4. 是否改变了无关有效规则。
5. 是否重复已有基础协议。
6. 是否存在无法落实却被模型强行实现的要求。

**Patch 可应用，只证明文本编辑合法，不证明行为要求已被忠实落实，更不证明 Skill 更新有收益。**

当前阶段不需要为了验证 Editor 重新执行 ALFWorld；真实行为效果由后续 Candidate Replay 检验。

## 8. 模块边界

Editor 不负责：

- 重新诊断当前执行问题；
- 重新选择历史 MemoryEntry；
- 调整 Effective Plan 的 D/S/C；
- 修改 Goal、Updates 或 Checks；
- 评估 Candidate 的任务成功率；
- 学习编辑产生的历史行为响应。

Editor 只负责将已经确定的行为要求落实为 Skill 修改。

如果无法落实，应明确暴露问题，而不是自行承担上游更新决策。

## 9. 最终设计结论

V23 Editor 采用简洁接口。

**输入：**

```text
parent
plan
```

其中 `plan` 是 Preconditioner 已生成的 Effective Plan。

**输出：**

```text
patch
reason
```

`patch` 的三种语义：

```text
非空 Unified Diff → 修改 Skill
""               → 无须编辑
null             → 无法忠实落实，需要上游修订
```

**Candidate Skill 由程序生成：**

```text
Candidate Skill = Apply(Parent Skill, Patch)
```

这套设计具有三个核心特点：

1. **局部更新：** 每轮只表达必要修改，不重新生成整份 Skill。
2. **忠实落实：** Editor 不重新决定策略方向、适用尺度或关联关系。
3. **简洁可追溯：** 模型只输出 Patch 和简短理由，程序负责应用、验证、保存及后续交接。

不增加独立 Add/Replace/Delete 操作、额外 decision、逐条实现映射、保留矩阵或复杂的补丁修复机制。

**核心原则：Preconditioner 决定应该怎样调整 Skill 更新要求；Editor 负责把这些要求转化为准确、局部、可应用的 Skill 文本修改；程序生成完整 Candidate，后续 Replay 验证实际行为。**

## 10. 接口依据与下一阶段

- [Preconditioner 设计方案](PRECONDITIONER_DESIGN.md)：Effective Plan 的结构、来源继承和进入 Editor 的条件。
- [V23 已实现接口](../../../src/skill_evolution/v23/README.md)：`load_preconditioner()` 返回实际事实、执行背景、原始 Plan、调整结果和 Effective Plan。
- [Preconditioner 无历史验证](../../../experiments/methods/v23/v23_preconditioner_001/reports/REPORT.md)：可供后续 Editor 验证的已保存 Effective Plan，以及当前可执行性和基础协议重复问题。

Editor 已按本设计完成正式 Prompt、代码实现、离线回归及一次真实验证；实际结果和限制见 [v23_editor_001 报告](../../../experiments/methods/v23/v23_editor_001/reports/REPORT.md)。没有实现 Replay、Memory、Gate 或完整演化循环。

## 11. 修订记录

2026-10-18：确认 `parent + plan → patch + reason`，用非空 Unified Diff、精确空字符串、null 区分三种合法结果。补充局部编辑的语义边界、声明位置严格匹配、空白与换行保真、技术失败独立保存、三种结果的非空原因要求，以及 Parent 与基础协议冲突时的处理原则。


2026-10-18：落地 [editor.py](../../../src/skill_evolution/v23/editor.py) 与正式英文 Prompt。复用现有调用、解析和保存基础设施，新增限定单文件、严格坐标的补丁应用；支持准确空白和末尾换行语义，区分三种合法结果与技术失败。实现接口见 [V23 README](../../../src/skill_evolution/v23/README.md#editor)，测试和实际模型结果以独立验证报告为准。
