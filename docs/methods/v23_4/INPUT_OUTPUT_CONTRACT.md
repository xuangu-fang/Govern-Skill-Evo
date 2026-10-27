# V23.4 输入输出契约

- 更新日期：2026-10-21（Asia/Shanghai）。
- 状态：v2 契约定稿；第三步最小实现已通过离线校验与交接测试，见[实现说明](../../../src/skill_evolution/v23_4/README.md)。真实生成与行为效果尚未验证。
- 契约标识：`v23_4_transformations_v2`，由程序记录在运行元数据中，不要求模型输出版本字段。本版替代此前嵌套的 v1 输出协议，D/S/C 方法与输入契约保持不变。
- 接口核对基点：仓库 HEAD `98ad799f`。该身份用于定位本次读取的源码，不代表工作区全部内容。

## 1 设计目标与范围

Preconditioner 利用当前事实与历史实际编辑—行为响应，直接为每个 Original Update 确定 D/S/C 更新决策，在对应 Adjustment 的 focus/change/reason 中表达，并由 to.patch 落实具体修改。没有独立的 Transformation 对象或生成阶段。D/S/C 必须参与决定变换，不能只给自由生成的修改结果分类。

| 维度 | 需要作出的决定 |
|---|---|
| D — Direction | 保留、强化、修正、替换或撤回什么行为方向 |
| S — Scope | 怎样调整适用条件、范围与强度，包括扩大、收窄、解除限制或重构条件 |
| C — Coordination | 怎样协调其他 Updates 与 Parent，补齐必要行为、解决冲突或整合要求 |

历史反例不自动触发收窄；历史正例不自动证明普遍有效。变换应保留改善作用，并允许有当前问题和历史响应动机的新探索。具体替代策略的收益仍可未知，应在 reason 中与已观察事实区分。单次调用不能证明内部推理先后，必须检查证据、维度判断、change 与 Patch 的一致性。

本契约保留一次 Preconditioner 调用和唯一 Effective Plan，不增加候选池、求解器、审核 Agent、行级授权或条件逻辑语言。Original Goal 不可编辑。Diagnosis、Editor、Replay、Gate 与 Memory 的职责不变。

第一版支持同 ID 修改、整项撤回、已有 Update 内新增行为要求，以及多个 Update 各自修改形成的协调。结构合并、拆分和独立新 Update ID 暂不支持；这只是接口范围，不表示方法只允许局部收窄。可以通过同 ID 的大幅替换实现方向重构，不设改字比例限制。

## 2 输入契约

只有 Diagnosis 为 `revise` 且包含合法非空 Plan 时进入 Preconditioner。Diagnosis 的既有停点仍由上游处理，不构造虚假的空 Original；本次仅取消 Preconditioner 输出中的决策状态，不修改 Diagnosis 契约。

模型业务输入保留六字段：

| 字段 | 内容与边界 |
|---|---|
| `parent` | 完整当前 Parent Skill 文本或 null；所有 Updates 相对于它提出 |
| `plan` | Original Plan，严格为 `goal / updates / checks` |
| `command_sets` | 当前所选执行引用的实际候选动作表 |
| `runs` | 按现有 Plan 引用选入的完整当前执行；不保证覆盖整个批次 |
| `grouping` | 现有选择规则得到的比较背景，不代替执行证据 |
| `memory` | 默认使用 `memory_evidence_view_v3` 模型视图 |

每个 Original Update 保留 `id / text / basis`；每个 Check 保留 `id / update_ids / question`。Original ID、文本、顺序、Goal 和输入证据在本轮冻结。旧单行文本不自动拆分；新 Diagnosis 的多行建议仍是表达方式，不是行级权限。

系统消息沿用当前真实 Actor 执行背景和 Memory v3 格式说明。程序侧保存完整 Memory、上游身份、来源、Prompt 和调用配置，不把这些私有交接字段追加到六字段业务输入。

模型看到的压缩视图与完整校验数据分开保存。完整归档存在某项状态，不代表模型看到了该状态；trace 中有动作也不代表对应 before/after 详情可见。引用和语义审查必须以实际模型输入为边界，不跨省略窗口补造信息。空 Memory 是合法输入，不要求虚构历史动机或自动停止。

## 3 输出顶层

模型返回一个 JSON 对象，严格包含 `adjustments / checks`。不生成顶层 decision 或 reason，不生成独立的决策状态。正式生成的自然语言使用英文，与既有模块一致；本文中文解释不进入生产输出。

| 字段 | 约束 |
|---|---|
| `adjustments` | 非空 Adjustment 数组，每个 Original Update 恰好对应一项 |
| `checks` | null 或完整替换 Check 列表，不是增量补丁 |

所有结构、引用、Patch 和 Checks 检查通过后，由程序根据最终存活 Updates 决定下游交接：

| 编译结果 | Effective Plan | Editor |
|---|---|---|
| 至少一项 Update 存活，包括全部 Keep | 使用原 Goal、最终 Updates 和解析后的 Checks 生成非空 Plan | 进入 |
| 所有 Original 均显式撤回，解析后的 Checks 为空 | null | 不进入 |
| 结构、引用、Patch、Checks 或调用错误 | 明确技术失败，不发布有效结果 | 不进入 |

不再提供 `need_evidence` 输出或任何覆盖豁免。历史不充分时，可以根据当前事实 Keep 或提出待验证的合理变换。真正无法形成合法 Plan 时明确失败；例如已识别的不可消解 Goal 冲突应记录为 Plan 无法成立，而不能强行 Keep、撤回全部或伪装成技术校验通过。语义冲突并非都可由程序自动识别，检查边界见第 8 节。

Keep 是保留 Diagnosis 的更新提议，Editor 仍可能据此修改 Skill。失败与“合法全部撤回”必须在运行记录中区分；不能把错误自动转成 Keep 或空 Plan。

## 4 Adjustment 与 D/S/C 更新决策

每个 Adjustment 严格包含 `target / focus / change / reason / to`。target 标识 Original Update，focus/change/reason 共同表达 D/S/C 更新决策，to 承载保留、撤回或具体修改。不输出 from、transformations 数组、basis 或重复的整体理由。

所有 target 必须不重不漏覆盖 Original IDs；每个 Original 恰好对应一个 Adjustment，不允许遗漏、重复或新增目标。跨 Update 协调使用同一响应内的多个 Adjustment，并在各自 change/reason 中明确关系，不增加依赖图。

Adjustment 中目标与决策字段的约束为：

| 字段 | 类型与职责 |
|---|---|
| `target` | 合法的原始 Update ID 字符串，唯一确定 Patch 的输入文本和输出 ID |
| `focus` | 由 `D`、`S`、`C` 构成的无重复数组；顺序无语义，推荐 D/S/C 顺序 |
| `change` | 非空字符串，规定具体行为变化、变换方式及重要保留边界；精确值 `KEEP` 保留作整项保留标记 |
| `reason` | 非空字符串，说明当前问题、历史响应怎样影响维度判断及重要未知；引用遵守第 7 节 |

一个 Update 中的多项行为变化必须综合写入同一个 change，reason 解释其依据和相互关系，focus 可以同时包含多个维度；不拆成多条嵌套记录。target 不用行号。Adjustment 数组顺序不表示顺序应用，最终 Updates 始终按 Original 顺序排列。

### 4.1 Keep

整项 Keep 使用 `change: "KEEP"`、`focus: []`、`to: null`。三者必须同时成立：任意一个 Keep 标记出现时，其余两个也必须成立。不得为同一 Update 同时提供 Keep 与修改。

reason 必须解释为何当前不修改。存在重要相关反例时，应具体回应，例如原条件已排除反例、编辑或执行条件不相容、联合编辑不足以定位作用。不能用无依据的“历史无关”或“证据不足”回避风险。没有历史时可以根据当前事实说明保留，不能声称历史已证明有效。

部分修改不使用 KEEP 记录；重要保留要求写进 change。`focus: []` 只用于整项 KEEP，表示未实施变换，不表示未判断 D/S/C。

### 4.2 修改与撤回

非 KEEP Adjustment 的 focus 必须非空。change 明确修正、强化、范围调整、方向重构、必要新增或撤回等具体意图，不另设操作枚举。删除某个分支与撤回整项的区别由 change 和 to 共同表达。

依赖历史时，reason 应呈现“实际编辑与响应 → D/S/C 判断 → change”的关系。允许探索；新阈值、排序、停止标准等实质选择必须在 change 中声明，其待验证性质写在 reason 中。无需强制每条理由覆盖三个维度，也不以 reason 字数作为质量标准。

## 5 to 与 Patch

| `to` 形式 | 含义 | D/S/C 决策字段条件 |
|---|---|---|
| null | 原 Update 精确保留 | change 为 KEEP，focus 为空 |
| `[]` | 整项撤回 | change 非 KEEP、focus 非空，明确撤回理由和必要行为的覆盖情况 |
| `{"patch": "..."}` | 同 ID 替换 | change 非 KEEP、focus 非空，Patch 落实综合 change |

修改时 to 严格为仅含 patch 的对象，不接受非空数组、重复 id、完整 text 或其他字段。目标直接由 target 确定，输出继承原 ID。Patch 为非空字符串，必须使文本发生实际变化，结果不得为空白。完整撤回用空数组，不用删除全部文本的 Patch；空 Patch、无效 Patch、无变化 Patch 都不转换成 Keep。不得通过宽松真值判断混淆 null、空数组、空对象与空字符串。

沿用现有严格 Unified Diff 引擎，虚拟头为 `--- a/SKILL.md` 与 `+++ b/SKILL.md`。target 选择的是冻结的 Original Update 文本，头部名称不是修改 Parent Skill 的授权。保留精确空白、换行和必要的无末尾换行标记，不做模糊匹配、自动修复或自由 text 回退。

生成 Patch 前须检查解码后的 Original 文本是否以换行结束。若没有，包含旧文本最后一行的 Hunk 行后必须紧跟 `\ No newline at end of file`；替换文本若也没有末尾换行，新的最后一行后同样需要标记。JSON 字符串中的标记反斜杠须写成 `\\`。单行 Update 不等于带末尾换行；省略标记会改变待匹配的旧文本，仍按技术失败处理。

所有 Patch 针对冻结的 Original 同时应用；不同 Update 的协调不能引用彼此修改后的文本来计算 Patch。某一项失败时不发布部分 Effective Plan。

Adjustment 中的 D/S/C 更新决策与 Patch 必须双向对应：声明的变化与保留边界应落实，Patch 的每项实质性行为变化都应被 change 覆盖。位置精确与 Patch 可应用不证明语义忠实；同一行也可能夹带新行为限制，不建立行级授权系统掩盖这一问题。

## 6 Goal 与 Checks

编译后的 Goal 与 Original 完全一致。存活 Update 保持原顺序；Keep 的 text/basis 原样保留，同 ID 修改的 basis 仍按原编译器继承 Original basis。D/S/C 决策的历史依据保留在本版记录与派生 Adjustment 中，不冒充 Diagnosis 的当前事实依据。

`checks: null` 保留全部原 Checks；非 null 则提供完整新表，每项严格为 `id / update_ids / question`，ID 和证据引用遵守现有 Plan 契约。update_ids 非空，只能引用最终存活 Updates。`[]` 表示清空 Checks。

撤回导致原 Check 引用失效时必须明确提供合法新表；程序不猜测迁移或静默清空。全部撤回时，解析后的 Checks 必须为 `[]`：可显式输出 `[]`，也可在 Original Checks 已为空时使用 null；Original Checks 非空却输出 null 时，即使全部撤回也应失败。

Checks 用于观察改善、反例和能力保留，不能代替 Update 中缺失的行为指导。全部 Keep 可以调整 Checks，必要解释放在相关 Adjustment 的 reason 中，不恢复顶层 reason；Checks 改动不得报告为行为要求变换。全部 Keep 且 checks 为 null 时，Effective Plan 与 Original Plan 完全相同，仍进入 Editor。

## 7 引用与旧编译器适配

不新增 evidence/limits 字段。为使 reason 中的引用能确定性提取，显式证据 ID 用单个反引号包围，每个片段一个 ID，如 `M2`、`P1:8`、`R1/diff`、`R1/Q1:10`。同样可用此形式引用本轮 Original Update ID 表达协调，或引用 Original Plan / 完整替换 Checks 中的合法 Check ID（例如 `c1`）说明检查项的保留、修订、替换或删除。Update / Check ID 是 Plan 结构对象，不是行为证据，不加入派生的 evidence basis；已被删除的 Original Check 仍可在理由中提及。替换 Checks 必须通过完整校验，不能靠声明一个 Check 绕过重复 ID、冲突 ID 或失效关联检查。reason 中反引号片段仅用于这些正式引用；不发明别名、缩写历史前缀、区间或未声明编号。

证据引用必须属于实际输入的当前证据、active Memory 或可见历史来源；结构对象引用须属于上述 Plan 对象集合。历史依赖应引用相应 Memory ID，并在涉及具体编辑/行为解释时引用必要的可见来源。空 Memory 只能引用可用当前依据。KEEP 的 reason 同样遵守引用规则，不强迫为每个 Keep 增加无关引用。

显式引用在 target、各项 reason 和 Checks 的关联字段中检查；后续实现也必须拒绝其他文本中可识别的伪造来源。声明的引用可校验存在与身份，不能靠字符串检查证明其支持自然语言结论。最终 Update 与 Checks 不应依赖 Preconditioner 私有解释才能被理解。

适配步骤固定为：

1. 按 V23.4 两字段顶层与五字段 Adjustment 契约验证完整输出、覆盖关系、引用和 Keep/Patch 对应。
2. 按 Original 顺序处理各项。Keep 保留原 Update，不生成旧 Adjustment；原始显式判断保留在本版归档中。
3. 修改以 target 查找冻结文本，严格应用 Patch；撤回保留 `to: []`。全部修改与 Checks 验证通过前，不发布任何部分结果。
4. 为每个非 Keep 派生旧 `from / to / basis / reason`：from 为 `[target]`；修改的 to 为 `[{"id": target, "text": 应用结果}]`，撤回为 `[]`。basis 先继承对应 Original basis，再按该项 reason 中出现顺序追加合法的当前证据及 active Memory IDs，首次出现顺序去重。带来源前缀的历史引用留在 reason 中，不塞入只接受当前证据/Memory ID 的旧 basis。原 basis 只是当前问题的来源，不自动构成变换支持。
5. 派生单项 reason 明确拼接 target、focus、change、reason，保留证据与未知，不再调用模型总结。统计最终存活 Updates，解析并验证完整 Checks。
6. 如调用现有 V23 编译器，兼容层内部根据存活数量填入其必需的 decision：非零为 `ready`，零为 `no_change`；内部顶层 reason 使用固定的程序编译说明，不替模型编造整体语义理由。Checks 传入已经解析的完整列表，全部撤回时为 `[]`。不生成或调用 `need_evidence` 分支。
7. 编译得到唯一 Effective Plan，或在合法全部撤回时得到 null；仅非空 Effective Plan 进入 Editor。任何错误明确失败，不回退成 Keep、全部撤回或成功的 null。

上述旧 decision/reason 只存在于程序内部兼容对象，不是 V23.4 模型输出字段，也不是新建的一套顶层决策接口。存档时应与原始模型输出分开标明，后续校验器、Patch 适配器与运行入口统一以本版新结构为模型契约。

旧编译器包含自然语言引用扫描，V23.3 加载器也严格绑定旧字段和 Prompt。新输出不能直接交给它们。后续实现须明确适配引用格式、版本加载与派生结果校验；遇到不兼容应显式报错或实现版本化处理，不能静默删引用、改原始理由、绕过检查或把失败改成 Keep。

## 8 程序与语义检查边界

| 程序检查 | 语义检查 |
|---|---|
| 字段、类型、枚举、Original 覆盖和 ID 唯一性 | 是否正确理解当前问题与历史实际编辑 |
| 引用存在、来源身份、模型视图可见性 | 观察是否支持所作结论，是否超出归因与迁移边界 |
| KEEP、focus、to 的结构对应 | Keep 是否具体回应相关反例 |
| Patch 精确应用、结果非空且变化、Goal 和 Checks 合法 | D/S/C 是否参与决定 change，而非结果标签 |
| 归档可重算，原始响应与派生产物一致 | Patch 是否落实 change、是否夹带未声明行为、是否保留改善作用 |

结构通过不等于方法有效。语义问题通过人工案例走查与后续结果抽查识别，不增加复杂审核 Agent。四字段不承担通用自然语言证明。

## 9 最小格式示例

以下均为人工格式示例，不是历史实验、真实 Memory 或已经有效的策略。假设输入包含 u1/u2、当前依据 P1:1/P2:1，以及示意历史 M2、R_demo/diff、R_demo/P1:8、R_demo/Q1:10。原 Checks 为 `[]`，Goal 只描述改善与保留边界。Original 文本如下；每项末尾均有一个 LF：

```json
{
  "u1": "Preserve exact target identification.\n",
  "u2": "Do not return to previously visited locations.\n"
}
```

### 9.1 Keep 与变换共存

```json
{
  "adjustments": [
    {
      "target": "u1",
      "focus": [],
      "change": "KEEP",
      "reason": "The current evidence at `P1:1` supports preserving exact target identification. The revisit response in `M2` does not contradict this requirement.",
      "to": null
    },
    {
      "target": "u2",
      "focus": [
        "D",
        "S"
      ],
      "change": "Replace the blanket revisit prohibition with avoidance of repeated searches when current and recent observations show no new information and no changed task prerequisite. Preserve returns needed for the current task.",
      "reason": "In `M2`, the broad restriction in `R_demo/diff` accompanied an obstructed required return in the comparison of `R_demo/P1:8` and `R_demo/Q1:10`. D redirects the restriction toward uninformative repetition; S limits its trigger and preserves necessary returns. Joint edits limit causal attribution, and the new trigger remains an unverified hypothesis.",
      "to": {
        "patch": "--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1 +1 @@\n-Do not return to previously visited locations.\n+Avoid repeating a search when current and recent observations show no new information and no changed task prerequisite; allow returns needed for the current task.\n"
      }
    }
  ],
  "checks": [
    {
      "id": "c1",
      "update_ids": [
        "u2"
      ],
      "question": "Does uninformative repetition decrease while necessary task returns remain possible?"
    }
  ]
}
```

这个 Patch 明确了假设，不证明 Actor 已能可靠判断触发条件。结构可应用与语义、行为效果分别验证。两个 Update 都存活，由程序生成 Effective Plan 并进入 Editor。

### 9.2 全部 Keep

```json
{
  "adjustments": [
    {
      "target": "u1",
      "focus": [],
      "change": "KEEP",
      "reason": "The current evidence at `P1:1` supports preserving target identification.",
      "to": null
    },
    {
      "target": "u2",
      "focus": [],
      "change": "KEEP",
      "reason": "The current evidence at `P2:1` motivates the Original proposal. The response in `M2` was observed under a different return prerequisite; its applicability here is unresolved, so it does not establish the need for a particular revision. Keeping the proposal does not establish its effectiveness.",
      "to": null
    }
  ],
  "checks": null
}
```

第二项理由展示如何回应反例；是否真的存在条件差异仍需核对输入，不能把该措辞当作默认 Keep 模板。此例 checks 为 null，Effective Plan 等于 Original Plan，仍进入 Editor。

### 9.3 部分撤回

```json
{
  "adjustments": [
    {
      "target": "u1",
      "focus": [],
      "change": "KEEP",
      "reason": "The current evidence at `P1:1` supports preserving exact target identification. The revisit response in `M2` does not contradict this requirement.",
      "to": null
    },
    {
      "target": "u2",
      "focus": [
        "D",
        "C"
      ],
      "change": "Withdraw the blanket revisit prohibition; retain the necessary return and task-completion behavior already covered by Parent.",
      "reason": "The adverse response in `M2` motivates withdrawing this broad restriction. Parent already covers the necessary task behavior. This does not establish that every alternative restriction is harmful.",
      "to": []
    }
  ],
  "checks": []
}
```

仅在假设的 Parent 确实已覆盖必要行为时，撤回理由才成立。u1 存活，u2 被撤回；checks 明确替换为空表，程序生成仅含 u1 的 Effective Plan 并进入 Editor。

### 9.4 全部撤回

本例额外假设 Parent 已完整包含 u1 的精确目标识别要求，且无需重复强化；该假设只用于演示全部撤回结构，不是对 9.1 至 9.3 的结论。

```json
{
  "adjustments": [
    {
      "target": "u1",
      "focus": [
        "C"
      ],
      "change": "Withdraw the redundant target-identification Update while preserving the equivalent requirement already present in Parent.",
      "reason": "In this example Parent already contains the same complete requirement, and `P1:1` provides no distinct missing guidance. Removing this duplicate proposal does not remove target identification from Parent.",
      "to": []
    },
    {
      "target": "u2",
      "focus": [
        "D",
        "C"
      ],
      "change": "Withdraw the blanket revisit prohibition; retain the necessary return and task-completion behavior already covered by Parent.",
      "reason": "The adverse response in `M2` motivates withdrawing this broad restriction. Parent already covers the necessary task behavior. This does not establish that every alternative restriction is harmful.",
      "to": []
    }
  ],
  "checks": []
}
```

两项撤回理由均需核对实际 Parent 与证据。所有 Original 显式撤回且 checks 为空，程序得到 null Effective Plan，不进入 Editor。不由模型输出 no_change。若原 Checks 已为空，本例 checks 也可以为 null；若原 Checks 非空且仍用 null，则必须报告失效引用，不能将本例视为成功。

没有 need_evidence 或失败响应的模型 JSON 示例：两字段输出无法表达逃避覆盖的停点。调用、结构、引用或 Patch 错误由程序报告；已识别的无法形成合法 Plan 的情况明确失败，不编造 Keep 或撤回结果。

## 10 归档与下游交接

后续 V23.4 运行器在元数据中记录 `contract_version: "v23_4_transformations_v2"` 和实际 memory_view，保存完整输入、模型实际输入、Prompt/消息、原始响应与 parsed、结构校验、内部兼容对象、Effective Plan。原始响应只含 adjustments/checks，每个 Adjustment 的目标与 D/S/C 决策字段不被派生文本覆盖。失败只保存原始材料与明确错误，不发布合法 Effective Plan；合法全部撤回可保存成功的 null，两者不能混同。

加载时重建实际模型输入，重新验证原始输出、应用 Patch、编译并核对派生产物；契约、Prompt、Memory 视图或配置不匹配时拒绝静默复用。旧 V23/V23.3 归档按各自版本读取，不补造历史 Keep，也不改写旧响应。此前 V23.4 v1 嵌套结构不得冒充 v2 输入；若将来存在需读取的旧产物，必须显式按其契约处理，本步不新增迁移或兼容模块。

Editor 仍只读取 Parent、完整 Effective Plan 和既有执行背景。所有可执行条件必须写入最终 Update，不能只留在 Adjustment 的 change/reason 中。Replay 仍从实际 Skill Diff 与配对行为学习，不能将更新决策的预期效果直接写成已验证 Memory。

## 11 实现前验收与源码依据

| 情形 | 契约要求 |
|---|---|
| adjustments 为空、遗漏或重复 Original | 拒绝，无语义停点豁免 |
| target 不是合法 Original ID | 拒绝 |
| KEEP 带 Patch、撤回数组或非空 focus | 拒绝 |
| change 非 KEEP 却使用 null to | 拒绝 |
| 非 KEEP 的 focus 为空 | 拒绝 |
| 顶层 decision/reason、from、transformations 嵌套、to 内 id/text、非空 to 数组 | 拒绝旧输出结构，不静默转换 |
| 未声明的新字段、行级 target、独立新 ID、结构拆合 | 当前接口拒绝，不静默转换 |
| 撤回使原 Checks 失效 | 要求完整合法替换表，否则拒绝 |
| 全部 Keep | 生成非空 Effective Plan，进入 Editor |
| 全部撤回且解析后的 Checks 为空 | 合法 null Effective Plan，不进入 Editor |
| 全部撤回但 Original Checks 非空且 checks 为 null | 拒绝失效引用，不能静默清空 |
| 无历史但提出合理变换 | 可接受，以当前事实和待验证假设说明 |
| 结构、引用、Patch 或调用错误 | 技术失败，禁止自动 Keep 或伪装成合法全部撤回 |
| Patch 能应用但夹带新限制 | 结构可能通过，语义不通过 |
| 条件不断缩窄导致改善作用丧失 | 语义问题，不能计作 D/S/C 成功 |

接口事实来自以下当前源码；本契约不声称这些文件已实现 V23.4：

- [V23 Preconditioner](../../../src/skill_evolution/v23/preconditioner.py)：六字段输入、来源依据继承、同时编译、Goal 与 Checks、旧引用检查。
- [V23.3 Patch 适配器](../../../src/skill_evolution/v23_3/update_patch.py)：同 ID 替换与整项撤回，严格应用后调用旧编译器。
- [V23.3 运行与加载入口](../../../src/skill_evolution/v23_3/preconditioner.py)：完整输入与模型视图分离、原始响应与派生结果重算。
- [V23.3 Diagnosis](../../../src/skill_evolution/v23_3/diagnosis_prompt.md)：Goal 不锁实现、多行行为要求、当前事实与历史职责分离。
- [Memory v3 说明](../../../src/skill_evolution/v23_3/memory_view_prompt.md)：完整来源身份、可见 trace 与详细状态窗口的区别。
- [Replay](../../../src/skill_evolution/v23/replay_prompt.md)：实际编辑、配对行为、联合归因与可修订知识。

规则与 Prompt 见 [D/S/C 决策规则与人工案例](DSC_DECISION_RULES.md)。第三步已按本契约完成[最小校验与适配实现](../../../src/skill_evolution/v23_4/README.md)；完整消融和跨轮收益验证后置。本契约的 v2 输入输出结构保持不变。

## 12 修订与文档核验

2026-10-21 初版 v1：固定嵌套契约并检查当时的 5 个 JSON 示例与 1 个示例 Patch。该次检查仅适用于旧结构，不作为本版验证结果。系统 Python 当时因缺少 `dotenv` 无法导入引擎，使用已有 τ² Python 环境完成检查，未安装或修改依赖。

2026-10-21 简化版 v2：模型顶层仅保留 adjustments/checks，每个 Original 对应一个展开的 Adjustment，to 使用 null、空数组或单 patch 对象。删除模型决策状态与 need_evidence 分支；程序按存活 Updates 与合法 Checks 推导 Editor 交接。内部旧编译器适配不改变模型契约，D/S/C 的决策含义与 Transformation/Patch 双向对应要求保持不变。

本版文档核验通过：相对链接与格式有效；1 个 Original 文本示例和 4 个完整输出示例可解析，字段、目标覆盖、引用、Keep/to 一致性和 Checks 引用通过示例级检查；1 个 Patch 由现有严格引擎应用成功。四种输出的存活 Update 数分别为 2、2、1、0，对应进入 Editor、进入 Editor、进入 Editor、不进入 Editor。使用已有 τ² Python 环境执行一次性文档核验，未新增校验器或测试模块。

文档示例核验不等于 V23.4 正式校验器、完整适配链或行为收益验证。本步仅修改协议文档与对应记录，不修改生产源码或 Prompt，不执行真实模型或 Actor 实验。
