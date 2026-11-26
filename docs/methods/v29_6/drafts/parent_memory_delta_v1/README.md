# Parent＋Memory 行为差量预条件：设计与 Prompt 草案

状态：**已采纳两处澄清并同步到设计及运行时 Prompt；未调用真实模型、未启动训练或 Test**。本目录保留经确认的设计与 Prompt，修订标识为 `parent_memory_delta_v1`，配置方法身份不变。接入范围与离线验收见 [实现记录](../../PARENT_MEMORY_DELTA_REVIEW.md)。澄清前草案和静态结果另存于 [历史快照](../../revisions/parent_memory_delta_v1/draft_before_clarifications/)。

基线是当前 v29.6 的 `docvqa_domain_v1` 领域指南修订及 `env_adaptation_v1` 两处环境适配，不是原始已训练 v29.6。共享领域指南逐字保留。当前领域修订尚未实验，历史结果不能代表该修订或本草案的成绩。

## 1. 交付与阅读顺序

1. 本文：问题、具体设计、差异、模块交接、边界及未来验收建议。
2. [Preconditioner 完整英文 Prompt 草案](preconditioner.md)：包含原领域指南、证据和输出合同，不是需要手工拼接的片段。
3. [Editor 完整英文 Prompt 草案](editor.md)：仅两段职责说明调整。
4. [Preconditioner 精确 diff](preconditioner.diff)、[Editor 精确 diff](editor.diff)、[六项 before/after](changes.json)。
5. [草案清单](manifest.json)、[基线快照](baseline/)、[冻结文件哈希](frozen_files.json)、[静态审阅结果](review_validation.json)。

完整 Prompt 文件不在正文前插入“草案说明”，便于精确比较；当前生效副本已与本目录同步；加载路径保持不变。

## 2. 实验依据与问题定义

根据[既有实验复盘](../../../../../experiments/analysis/v29_6_regressions_preconditioner_20261105/analysis.json)：23 条 Original 中有 20 KEEP、2 REPLACE、1 WITHDRAW；最终保留的 11 条都来自 KEEP，其中 7 条为纯追加。两次 REPLACE 没有进入最终 Skill。高 KEEP 比例本身不证明失败，但限制了可观察到的调整贡献。

R09 以 Parent 没有明确提到撇号相邻为理由保留专门规则，体现了“未点名细节”被当作行为增量的风险。R11 撤回重复单位规则则是正例：既有 Parent 已覆盖、Memory 有相关支持，但没有新的触发、动作或优先级需要引入。

最终 Skill 的冗余判断来自重复决策与保留清单，不能只看长度。职位截断、极性编码两类 Test 回退与已保留规则高度吻合，但没有独立因果验证；其他回退也不能统一归因于 Preconditioner。13 道回退题已经参与分析，不再作为未受设计影响的泛化证据。

当前 Prompt 已要求覆盖检查、D/S/C、历史比较和显式整合。因此本草案不把这些描述成全新能力，而将其落实为更清楚的决策顺序和交付条件。

## 3. 核心目标与两个信息来源

目标：将每个 Original 转换为“相对当前 Parent、受当前证据及相关 Memory 约束的最小充分行为修正”。“最小”指不引入无依据的行为决定或重复规则，不指字数最少，也不指修改率最大。

| 输入 | 在预条件中的作用 | 不代表什么 |
|---|---|---|
| Parent 全文 | 判断覆盖、剩余行为差异、冲突及旧指导处理位置 | 出错即证明规则缺失；相似词句即证明已充分覆盖 |
| 当前 runs | 支持 Original 问题、行为差异和必要边界 | 可访问图像、完整批次或隐藏推理；reference 即 Actor 当时的推理 |
| Memory | 用相关历史比较调整方向、适用范围和强度，并避免重复已纳入的决策 | 成功概率、单条规则独立效果、历史 Retain 仍存在于 Parent |
| Original | 固定问题边界、ID、来源和目标 | 下游可借此开展全局规则重写 |

Parent 与 Memory 联合决定修正；下面的顺序用于组织分析，允许相互回看，不新增模型阶段。D/S/C 仍为判断维度，不新增输出字段或强制表格。

## 4. Preconditioner 的具体流程

### 4.1 明确相对 Parent 的行为差异

先问：在什么 Actor 可见的条件下，修正后的行为应与当前 Parent 不同？比较触发条件、答案对象、动作、范围、强度和优先级；不以关键词是否出现作为标准。

| 关系 | 预期处理 |
|---|---|
| 已覆盖，且不存在有依据的行为增量 | WITHDRAW，处理必要依赖 |
| 已有决策存在具体缺口 | 修订相关指导，补足触发、动作、范围或优先级 |
| 与旧决策部分重叠或冲突 | 明确限定、替换或整合，并保留必要分支 |
| 确实缺少受支持的新决策 | 允许新增，说明必要的关联处理 |

这些关系不是新标签或新的 action。后三种情况如果 Original 已完整说明所需修正，可以 KEEP；否则用 REPLACE。不能为了演示 Parent 的作用而强行改写。

已写规则仍出错，不足以证明需要重复或更强措辞；但有证据支持的执行方式、强度和优先级变化仍有效。不得机械地撤回所有重叠提案，也不得为解释错误虚构具体视觉过程。

### 4.2 让历史比较实际影响修正

按行为机制和适用条件关联历史，不按题型、实体或关键词相同简单匹配。

- 正向历史：可复用其局部支持的决策；先确认当前 Parent 是否已有，避免重复加入。
- 负向或混合历史：调整相关方向、条件、强度或组合，不以“不确定”一句话原样放行整个提案。
- 重复尝试：当先前有报告的无目标改善或相关回退时，说明本次机制或条件有何实质不同；不能仅以换题或换实体支持重试。
- Defer、空 Knowledge、null 归因：保持既有解释，不把它们直接视为失败、无效或成功。
- 无相关 Memory：依赖当前证据及 Parent；不虚构历史影响，也不把“没有反例”当成支持。

不增加历史数据，不估计数值置信度，不要求每项都引用 Memory。沿用现有来源引用、联合干预和图像不可见边界。

### 4.3 审查一个提案内的多个行为决定

方向有效不意味着所有附带决定都有效。例如，删除不必要解释与固定答案编码是不同决定；限制多余上下文与普遍截断完整字段也不同。检查材料性条件，不要求每个句子都有独立因果证据，不拆分或合并 ID，保留有依据的必要联合修改。

D 确定方向；S 限定适用范围和强度，保护明确题意及必要区分；C 安排旧指导处理与 Update 之间的关系。无依据的扩展直接去掉，不靠越来越长的例外清单防守。

### 4.4 通过现有 text 完成交接

REPLACE 的 text 必须足够完整，包含：预期行为与条件；需要时对可辨识旧指导的处理；实际受影响的有效分支、优先级和依赖。无需三段式模板、额外字段、rule ID 或字符位置，不复制大段 Parent。

“替换／整合旧指导”属于给 Editor 的实施要求；最终 Skill 只保留 Actor 应执行的行为。与修正无关的完整性保护清单、历史理由和引用不进入行为文字。

Preconditioner 已确认 Parent 完整覆盖且无合理行为增量时，首选 WITHDRAW。Editor 空 patch 仍是实施阶段发现原 Parent 已满足要求时的既有兜底，不能用来主动保留已知冗余提案；空 patch 合同不变。

KEEP 只有在 Original 本身足够完整时适用。若某个必要例外或旧规则处理仅存在于 reason，必须 REPLACE，并写进 text。reason 简要说明 Parent 关系、剩余差异和有影响的历史比较，不重复一遍完整方案。

### 4.5 多 Update 与删除范围

只有相关重复会使本次修正重复、冲突或不完整时，才整合该 Original 范围内的必要位置；发现重复本身不是额外编辑目标。不得跨 ID 搬运独立修复、合并 ID、重复分配同一修改，或假定另一个 Update 会被 Gate 保留来补齐自己。

若两个 Update 争用同一规则，只有在各自修正完整且忠实时才允许分别表达。无法在边界内形成完整受支持修正时，按现有 REPLACE/WITHDRAW 处理；不可把实际缺口包装成去重。Editor 仍遵守原有冲突、空 patch 与 blocker 合同。

## 5. 与当前 v29.6 的精确差异

| 变更 | 当前领域修订版 | 草案 |
|---|---|---|
| P1 职责开头 | 综合 D/S/C，避免重复 | 直接定义相对 Parent 的最小充分行为修正，明确 Parent 和 Memory 分工 |
| P2 Parent 比较 | 要求检查覆盖和交互 | 明确行为差异问题及四种关系；未点名细节不能单独证明新决策 |
| P3 历史比较前两段 | 对相似失败比较，保留不确定性 | 补足正向复用与已纳入检查；明确无反例不等于支持，历史影响必须进入实际要求 |
| P4 D/S/C 与决策交付段 | 原则性协调与完整 text | 将材料性决定、旧指导处理、必要分支组成具体交付条件，明确拒绝附带推广 |
| E1 实施段 | 忠实修改相关旧指导 | 明确指定重复指导也须处理；编辑指令不能照抄进 Actor Skill |
| E2 自查段 | 查残留、重复、冲突 | 核对指定处理已落实且必要分支仍在，只针对受影响指导 |

两处澄清仅修改 P4：整合绑定本次修正必要性；冗余提案首选撤回，空 patch 保持 Editor 兜底角色。P3 后面的“联合干预、可观察性和混合结果”两段逐字不变。Preconditioner 的 `Full-text decisions and compilation` 至文末逐字不变。Editor 的 patch、映射、组合、空值与输出合同逐字不变。完整差异由 changes.json 和 diff 给出，而非仅由此表概括。

本草案替换现有职责段落，不在末尾另叠加一套去重流程。Preconditioner 全文由 29,090 增至 30,535 字符（+1,445），Editor 由 17,301 增至 17,656（+355）。不将此称为 Prompt 压缩；token 上限保持不变，实际调用长度和行为效果尚未验证。

## 6. Editor 最小配合

只调整 E1/E2 两段，不给予 Editor 判断历史、选择策略或开展全局压缩的权限。

1. 落实 Effective text 已指定的替换、限定、整合或删除，处理必要相关位置；不能只追加新段落而留下指定应去除的旧决策。
2. 将编辑要求转换成 Actor 行为，不把“替换旧规则”等元指令写进 Skill。
3. 自查既定旧规则处理是否完成、必要条件和分支是否保留，以及本次修改引入的重复或矛盾。

仍然只接收 Parent 与 Effective Plan，不接收 reason、basis、Memory、runs 或图像。依然每个有效 Update 一个 edit，全部 patch 针对同一个冻结 Parent。条件充分时可以自行选择简洁措辞和位置；真正缺少关键行为决定时使用原 blocker，不能擅自发明优先级。

## 7. 合成示例与未来审阅案例

以下是设计层的合成情境，不是历史模型输出、已通过的模型测试或新增运行时样例。它们不进入完整 Prompt，也不将 Test 答案迁入 Skill。

| 情境 | 应体现的判断 | 不应出现的行为 |
|---|---|---|
| Parent 完整规定值内单位与外围单位；Original 再次要求同样处理，Memory 报告该方向的局部收益 | 覆盖完整且无新动作时 WITHDRAW；正向 Memory 支持复用而非追加 | 因有历史 gain 再写一遍 |
| Parent 只有泛化复制原则，Original 的具体步骤有当前证据支持 | 可保留有效细化，必要时修改旧条款 | 仅因语义重叠就撤回 |
| Parent 已要求忠实字符间隔，Original 只将某一符号点名，无新的执行或条件差异 | 撤回重复提案 | 以 Parent 没出现符号名称为唯一理由 KEEP |
| Original 同时减少解释并固定一种输出编码，输入要求存在明确编码区分 | 保留所需范围修正，限定编码决定，并落实到 text | 将减少解释的证据推广为所有编码必须一致 |
| Memory 报告相似策略的局部收益及回退 | 保留有依据方向并针对相关风险调整；reason 说明历史影响 | 只写“不能证明因果”后原样 KEEP |
| Memory 只有 Defer 且无事件 | 依据 Parent 和当前证据判断，不作虚假负面推断 | 宣称历史证明无效 |
| 两个 Update 需要重写同一旧条款 | 在现有 ID 边界内处理；无法忠实组合时沿用原停止/撤回语义 | 合并 ID、重复删除或依赖另一个未来必留 patch |

下面展示一个 **REPLACE 的交付形式**。假定输入中 Parent 有两条同义的“一次呈现”规则，Original 的问题边界就是消除答案中的重复呈现；当前证据支持区分同一值的重复与题目请求的不同项。该例不预设任何真实运行具备这些条件。

```json
{
  "adjustments": [
    {
      "target": "u1",
      "action": "REPLACE",
      "text": "Consolidate the Parent guidance about one rendering and avoiding duplicate restatements into one decision: return each requested value once rather than adding an equivalent rendering of that same value. Preserve distinct items or alternatives when the question requests them. Replace the affected synonymous occurrences with this scoped guidance; leave unrelated selection and transcription decisions unchanged.",
      "reason": "In this synthetic input, Parent repeats the same rendering decision, while the Original does not distinguish equivalent restatements from separately requested items. The current evidence supports that distinction. No relevant historical comparison is supplied. The revision makes the necessary boundary and consolidation explicit without introducing a separate repair."
    }
  ]
}
```

示例使用现有四字段，不增加分析字段。真实输出必须以实际 Original ID、证据及可用 Memory 为依据；若整合仅是无行为增量的等价简化，不应借此生成独立修复。

## 8. 冻结项与明确限制

以下保持原样：共享领域指南、Diagnosis、Replay、Actor 基础 Prompt、初始 Skill、证据投影、basis 与引用权限、Memory 内容和发布、Gate、patch 格式和组合、请求重试、恢复与预算。没有同步 Brutus 后续补丁，没有增加检索、OCR、模型阶段、额外执行或全局压缩。

配置以[当前 v29.6 配置](../../../../../experiments/configs/v29_6_docvqa_optimization160.json)为准，文件哈希冻结：160 题优化集、原顺序与 11 批（10×15＋10）、374 题 Test；模型 deepseek-flash，temperature=1.0，thinking enabled，reasoning_effort=medium，Actor 与四模块 max_tokens=32768；训练并发 15、Test 并发 60；技术/长度重试、超时、Gate 和恢复参数不改。本次也不创建或迁移 campaign。

当前 Gate 仍只按明确关联 hard 翻转计票：G>0 且 L=0 才 Retain，0/0 为 Defer。纯等价压缩不因此获得新的采纳通道。目标是阻止无增量提案，并在有依据的行为修正内处理相关重复；不保证清空整个历史 Skill 的冗余。现有轨迹没有“压缩提案被 Gate 否决”的已证实实例。

Selected 仍可能是完整 Candidate 的保留子集，不新增组合复测。预条件判断不能保证每个子集语义独立，也不能解决所有归因噪声或视觉识别错误。

## 9. 本次审阅与将来验证的边界

澄清前草案曾通过 355 项静态检查；其结果保存在历史快照，不冒充本次结果。当前静态审阅核对六项改动可重放、两处澄清、diff、领域指南、机器合同、设计与运行时一致，以及授权范围以外的文件冻结；见 review_validation.json。接入后的既有离线测试及配置核对见实现记录。未调用真实模型；静态与离线通过不等于模型遵循或成绩改善。

本轮已授权并接入 Prompt；上述合成情境仍只是未来模型行为审阅用例，没有执行模型评测。后续可审阅行为差异、历史影响、text 交付和 Editor 落实。不能以 KEEP/REPLACE 比例、总字数或“引用过 Memory”代替效果评价。

未来如授权实验，应将当前领域指南固定，比较当前 Preconditioner 与草案，避免把领域指导变化和预条件变化混为一种收益。若进一步归因，可单独设计 Parent/Memory 信息对照；这不是本轮实施或运行计划。评估整合是否真正落地、相关重复是否减少、必要分支是否保留，同时考察准确率与回退。已分析的 13 题只作回归参考，泛化需未参与修订的数据。任何额外对照均应另行明确设计，不改写原始实验结果。
