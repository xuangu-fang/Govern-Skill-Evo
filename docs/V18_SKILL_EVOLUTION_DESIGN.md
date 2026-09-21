# v18 Skill 自进化方案：保持经验语义，补全删除能力

更新：2026-09-19。状态：第 1–5 步工程实现完成；Editor 纯删除已用已有 Pilot 输出验证，模型文本路径已完成工程测试，尚未接入完整 v18 调度或运行正式实验。

## 1. 目标与边界

v18 在 v17 的 Grouping → 双维 Diagnosis → 确定性 Compiler → Bounded Editor → Monitor/Gate 流程上，提高证据在 `Analysis → Addressability → Gap → Skill` 中的语义保持能力。核心要求是：保留经验中有用的可观察条件、行为关系、适用范围和确定性，不把机制未知自动变成额外的执行门槛。

本版包含两项独立变更：

1. **benchmark / simulator 修复**：用户确认待执行动作时，不在同一回复中结束会话。
2. **learner v18**：加强 Diagnosis 与 Editor 的语义契约，新增 `SHOULD_REMOVE → DELETE`。

正式职责边界为：`Benchmark / User Simulator → 生成语义合理、可学习的 trajectory`；`Diagnosis → 归纳可观察规律、判断 Skill 可修改问题并保持 Analysis → Addressability → Gap 的语义与确定性`。正式 benchmark 在上游负责消除或避免确认同时终止等交互 artifact。Diagnosis 不负责识别、解释或补救 benchmark/runtime artifact，不检查终止标记、终态或下一回合。输入协议不新增 terminated、termination_reason、agent_has_next_turn 等字段；Diagnosis 不增加对应结构/语义校验或专项验收测试。历史 artifact 原样保留用于复现，其解释正确性不作为 v2 核心语义验收标准。

保留 v17 的经验分组、两维监督、引用与 Parent 绑定、一次 Diagnosis/Editor 调用、不自动修补、完整计划原子应用、Monitor 数据隔离和 Four-Δ Gate。不增加在线语义裁判，不增加全任务 rollout 次数，不引入跨轮经验池。候选经验规律仍可进入实验；不要求先确定真实机制才能学习。

## 2. 四轮证据与设计依据

数据来自 `experiments/v17_formal_001` 各轮 `monitor_private/monitor/summary.json`，已逐轮核对。每侧 41 个任务；S 为成功数，C 为合规数，CS 为成功合规数，CF 为失败合规数。

| 轮次 | S：Parent → Candidate | C | CS | CF | Gate |
|---|---:|---:|---:|---:|---|
| R1 | 29 → 26 | 34 → 39 | 22 → 24 | 12 → 15 | RETAIN |
| R2 | 32 → 17 | 34 → 41 | 25 → 17 | 9 → 24 | RETAIN |
| R3 | 25 → 37 | 35 → 39 | 19 → 35 | 16 → 4 | ACCEPT |
| R4 | 33 → 37 | 39 → 39 | 32 → 35 | 7 → 4 | ACCEPT |

R1–R3 的 Parent 都是 S0；R4 才从 R3 接受的 Skill 出发。R1/R2 被拒绝的 Candidate 没有成为后续 Parent。不能把四轮解释为四次连续累积更新。

具体证据及含义：

- **不可执行的 STOP 规则**：R1 学出确认中含停止标记仍应继续 booking 的指导，R3/R4 Skill 中也留有此类指导。`UserSimulator.is_stop` 检查消息中的终止标记，orchestrator 随之终止，Agent 没有下一次决策机会。鼓励 Agent 继续执行无法改变这个结果。
- **已经发现的规律丢失**：R1 定价 Analysis 提到了渠道与保留航段价格的关系，最终 Skill 没有完整保留映射。v17 Editor 输入已有完整 Analysis，故不能只归因于 gap 太短或输入缺失。
- **未归纳条件差异**：R2 定价组中四条 horizon 保留原价，四条 summit 发生重定价。四条 summit 缺少保留航段当前搜索价，因此支持“渠道相关重定价”的候选关系，尚不能完整证明“结算价等于当前搜索价”。不能将其概括为任意变化，也不能补造未观测的价格映射。
- **未知变成停止条件**：R2 的权威结算金额要求被 Editor 强化为执行前无法核实就不修改；姓名字段缺失被扩大为对姓名外观的有效性审查。Monitor 出现大量未执行任务，与 CF 从 9 增至 24 的方向一致。
- **可执行规律能够学出**：R3 保留了更具体的渠道、人数及支付分配经验，整体 S/C/CS 改善。支付组即使所有 Evolution 结果失败，也能从工具状态支持可执行的行为假设；不应把“必须有成功样本”设为统一门槛。
- **已有 Skill 能被继续修订**：R4 产生 3 个 REPLACE、1 个 ADD；地址顺序经验从不完整对照发展为明确的条件映射，部分已有指导不再重复修改。需要保留这一能力，而非通过一律 NOT_ADDRESSABLE 压低学习量。

因果边界：这是轨迹来源追踪与单次 matched Monitor，不能量化各层方差贡献，也不能把改善全部归因于某条规则。相同 seed 不消除 Agent/User 模型变化。R4 仍有 2 个 CS → CF；ACCEPT 只表示整份 Candidate 满足本次总体 Gate，不是逐条语义正确性证明。

更详细的历史追踪见 [learner_instability.md](../experiments/v17_formal_001/offline_analysis/learner_instability.md) 和 [实验日志 v17 记录](04_EXPERIMENT_LOG.md)。这些事后分析不作为新 learner 的经验输入。

## 3. 先修复共享 User Simulator Prompt

当前接入点是 `external/tau2-bench/src/tau2/user/user_simulator.py` 中的共享 `SYSTEM_PROMPT` / global guidelines 装配路径。普通文本 guidelines 来自 `external/tau2-bench/data/tau2/user_simulator/simulation_guidelines.md`。实施时应在 benchmark 公共装配层注入一份版本化约束，使所有参试任务、领域、Parent/Candidate 使用同一内容，并检查实际请求；不按任务追加特例。

建议加入的通用英文条款：

```text
Confirmation of a pending action is not completion of that action. When your
reply authorizes or confirms an action that the assistant still needs to carry
out, do not include an end-of-conversation signal in that same reply. Allow the
assistant another turn to perform the confirmed action and report the result.
After receiving the assistant's response about the action's outcome, decide
whether to continue or end the conversation under the normal stopping rules.
This does not require you to approve an action, relax your requirements, or
continue after you withdraw the request or genuinely choose to end the interaction.
```

用户仍可拒绝、撤回、结束或接受合法转人工。约束只消除“要求 Agent 继续执行，但同条确认消息终止交互”的矛盾，不要求无条件成功，也不改变任务条件。Simulator 依据其可见交互判断，不读取隐藏 evaluator 来决定完成。

首版只改 prompt，不忽略 STOP、不在终止后强行运行 Agent、不自动删标记并重放消息。如果仍发生异常，保留原始轨迹并报告残余发生率；不按结果补跑或筛除不利样本，也不把失败改记为成功。Prompt 不能确定性保证异常为零。

单独记录 simulator 版本、共享条款摘要和实际装配后 prompt 摘要，纳入冻结配置与 Monitor 配对绑定。新旧 simulator 的结果分开报告；历史 v17 冻结目录、轨迹、标签不改写。

## 4. Diagnosis：同一轮推理内保持语义

沿用 v17 的 `success_analysis`、`compliance_analysis`、`skill_addressability` 和 `parent_skill_gaps`，不新增推理阶段或输出字段。

### 4.1 Analysis 优先归纳可观察关系

两维 Analysis 的 `finding` 应清楚表达：观察到什么条件、Agent 做了什么、工具或结果出现什么差异；哪些是直接观察、哪些只是候选解释。先检查组内可观察条件能否解释差异，再认定“尚无可用规律”。保留正例、反例与未知项，不要求一定归纳出规律。

当支持不完整时，保留在已有范围内成立的候选关系，明确缺少哪项观察。例如可以说“本组渠道 A 保留原值、渠道 B 发生变化；B 的精确计算机制尚不确定”，不能因此写成“变化完全不可解释”，也不能补全一个没有证据的精确公式。

`unresolved` 存放未解决问题，不自动产生 Agent 核实任务。Agent 在轨迹中的拒绝、解释或自述，不自动成为合法的 policy 依据。标签说明结果，不能单独推出原因、隐藏规则或修复动作。

### 4.2 Addressability 指向实际可改变的决策

`ADDRESSABLE` 的 `reason` 必须说明：修改 Skill 能够改变哪个具体 Agent 决策或行为，依据哪些可见信息、合法工具或合法交互；Parent 缺少或错误地引导了什么。这是行为可修改性的判断，不是 runtime 回合可达性检查。可补救交互可以是向用户澄清已存在且可能取得的信息，但不能假定用户一定能提供，也不能发明可查询的权威机制。

以下情况采用 `NOT_ADDRESSABLE`，且不产生对应 gap：

- 证据不支持通过 Skill 指导改变具体 Agent 行为；
- 信息或业务规则条件不支持合法可行的行为修正；
- 只有负标签或机制疑问，尚无证据支持具体决策变化；
- Parent 已有充分指导，证据不能指出应改动哪条指导。

缺信息本身不必然不可修复：若已有合法工具能读取所需字段，或可向用户进行有意义的澄清，并有证据指向 Agent 漏做了该步骤，仍可 ADDRESSABLE。反之，不得因失败而额外要求用户提供不可取得的信息。

一组含有可修复与不可修复问题时，只对前者生成 gap，后者保留在分析与 reason 中。`NO_ISSUE` 仍要求没有观测到需修复的问题，所有 supplied success/compliant 标签为 true；不是无法解释失败时的替代状态。

### 4.3 Gap 是保留语义的修改依据

每个 `gap` 文本必须保留其依赖规律的条件、具体行为方向、经验确定性和限制；不要仅写“检查上下文”“遵循权威规则”这类丢失规律的泛化句。candidate empirical pattern 在 gap 本身仍须保持条件性和暂定性质，不能先写成普适强规则、再附一段不确定性声明。不得为了显得更安全或保守而扩展范围、增加义务。

未知机制或信息不完整不自动产生 verification duty、execution prerequisite、prohibition、escalation 或 stopping condition。确需新增的限制必须已经被来源 Analysis 的证据支持其必要性，需完成的核实或前提还必须有合法可行路径；Gap 转写不能独立加入这些要求。仅避免执行、披露不确定性或转人工，不等于修复已识别的问题。实际 policy 与用户条件仍然有效。

经验候选指导不能覆盖可见 policy、工具约束或用户条件。用户明确禁止某项不确定后果时，原有授权边界仍有效；“避免新增停止条件”不等于默认授权执行。

五字段结构继续沿用：

```json
{
  "kind": "NEEDS_REVISION",
  "gap": "保留有价值的行为方向，修正其条件或范围；同时保留证据中的不确定性。",
  "evidence_refs": ["<本组轨迹引用>"],
  "related_rule_refs": ["<当前 Parent 规则引用>"],
  "source_dimensions": ["SUCCESS"]
}
```

占位符只用于说明结构，不是可通过验证的实例。引用存在性、组归属、Parent 摘要、Analysis 与 gap 的结构引用关联继续严格校验；这些检查不证明自然语言蕴含或因果正确。

## 5. 三种 gap 与删除证据门槛

| Gap kind | 判定语义 | related_rule_refs | Compiler |
|---|---|---|---|
| MISSING | 缺少证据支持的指导 | 空 | ADD |
| NEEDS_REVISION | 核心方向仍有价值，条件、范围或内容需修改 | 非空 | REPLACE |
| SHOULD_REMOVE | 现有规则本身被证据证明不必要、错误或不应保留，删除优于修订 | 非空 | DELETE |

`SHOULD_REMOVE` 的证据门槛高于 `NEEDS_REVISION`。Diagnosis 必须在 Analysis 与 gap 原文中解释：

1. 哪条当前规则的核心指令被什么证据否定，或为何该指令没有应继续保留的作用；
2. 为什么问题涉及整个目标规则，而不只是一个条件、范围或措辞；
3. 为什么缩小范围、降低确定性或保留有效部分的 REPLACE 不合适；
4. 删除会如何改变 Agent 的具体决策，且不要求它绕过有效 policy、用户约束或工具契约。

证据强度取决于可否明确否定规则核心、是否处理适用范围与反例，不机械规定最低样本数。清晰的可见工具契约矛盾可以很强；多条无法归因的失败仍然很弱。单次失败、规则本轮未触发、没有看到收益、表述不确定，均不足以直接删除。证据不足则保留；存在可支持的局部修订时使用 NEEDS_REVISION。

**目标粒度**：v17 的 rule ref 指向 Markdown 指令块，一个块可能含多个语义。只要块中还有应保留的内容，就用 REPLACE 删除其中错误部分、保留有效部分。DELETE 只用于整个已引用块都应移除，不让 Compiler 猜测块内句子范围。

benchmark/runtime artifact 的治理独立于三种 gap 判定，不以历史终止标记解释作为 SHOULD_REMOVE 样本或专项验收项。删除证据门槛针对规则本身的必要性、正确性与修改价值，不要求 Diagnosis 解释运行器语义。

## 6. Compiler 与确定性应用

Compiler 仍然不读取自然语言来重新判定 gap，不调用模型，不作证据强弱判断。它只做已验证类别映射、引用绑定、目标合并、完整覆盖与排序。

新增规则：

- DELETE 的目标恰好为其 supporting SHOULD_REMOVE gaps 的 `related_rule_refs` 并集；每个 gap 恰好绑定一个 edit unit。
- 同操作的 REPLACE 重叠目标继续按传递闭包合并；DELETE 使用相同结构规则合并重叠目标并保留全部来源。
- REPLACE 与 DELETE 指向相同或重叠原始范围时，拒绝整份计划，记录 `PLAN / MIXED_OPERATION_TARGET_CONFLICT`。不设删除优先级，不自动降为 REPLACE，不丢弃任何来源，不发布部分 Candidate。
- 不相交的 REPLACE/DELETE 按最早 Parent 行排序，再按操作名和 GapRef 作稳定排序；ADD 仍在后，按 GapRef 排序。所有坐标基于同一个原始 Parent，不能基于已改动文本重新定位。
- NO_ISSUE / NOT_ADDRESSABLE 仍映射为 NOOP record；所有单元为空才是 NO_UPDATE。空输入仍是配置错误。

DELETE 由文本应用器删除目标原始范围，不产生替代文本、不自动删除标题或相邻空行、不整理整份 Markdown。非目标片段逐字保留。允许 Candidate 为空或仅剩标题，并像 S0 一样进入正常 Monitor，不把纯删除误判为无更新。

REPLACE 继续要求非空文本，禁止以空字符串绕过 DELETE 的证据门槛。多个编辑一次性应用；解析、绑定、覆盖或范围失败均不输出部分有效 Candidate。

## 7. Editor：受限语义改写器

Editor 只将 Diagnosis 已授权的修改依据表达为可用 Skill，不独立分析新问题。沿用每个 unit 的 backing gaps、完整两维 analyses/unresolved、引用证据及目标规则；保留 v17 已有完整输入，不用删减 Analysis 来解决语义漂移。

固定 prompt 增加以下通用约束：

```text
Preserve the diagnosis-supported observable conditions, concrete behavioral
relations, applicability limits, and epistemic status. Do not discard a useful
condition or replace a supported relation with generic advice.
Do not independently add verification duties, execution prerequisites,
prohibitions, stopping conditions, or broader applicability. An unresolved
mechanism is not itself a new instruction for the acting agent to verify it.
Do not turn a candidate empirical pattern into a mandatory rule or a requirement
to stop when it cannot be confirmed. Preserve applicable policy and user limits.
Use analyses and evidence to faithfully express the backing gaps, not to create
additional changes beyond them. If the supplied basis is contradictory or cannot
support the requested edit, return UNABLE rather than inventing a resolution.
```

允许改善句式、组织步骤、在明确授权范围内合成重复表达；不允许扩大范围或提高确定性。REPLACE 应保留目标规则中仍有效且不受 gap 修改的指导。若 Analysis 与 gap 在关键条件、义务或确定性上冲突，Editor 不自行选择更强表述；返回 UNABLE，由实验记录暴露该链路问题。

### DELETE 的模型与运行时协议

为避免让模型“编写删除内容”，模型只接收需要文本的 ADD/REPLACE 单元，保留它们在完整计划中的原始 `edit_unit_index`，允许索引不连续。DELETE 完全由已验证计划和应用器执行。

- 混合计划：EDITED 必须精确覆盖所有 ADD/REPLACE 索引，不能返回 DELETE 的 text；全部验收通过后再将模型文本和计划内 DELETE 原子应用。
- 纯 DELETE：跳过模型，运行时标记 `APPLIED_DETERMINISTIC`，产生 Candidate 与摘要；不伪造模型 EDITED 响应，不记成 NO_UPDATE。
- 全 NOOP：继续 NO_UPDATE，不产生 Candidate。
- UNABLE 或任何错误：整份计划不应用，包括其中 DELETE；当前 Parent 不变。

模型输出仍为 `{status, reason, edits}`，其中 edits 元素为 `{edit_unit_index, text}`，模型状态仍仅 EDITED/UNABLE。计划、请求、响应、应用结果采用明确的 v18 schema/version；审计分别记录模型生成单元和确定性删除单元，保留被删原文、来源引用、Parent/plan/Candidate 摘要以便复核。

## 8. 验证与实验设计

### 8.1 无模型工程验证

实施时覆盖三类 gap 的枚举/基数/引用关联、过期 Parent 和跨组引用拒绝、三种操作完整映射、同操作传递合并、混合操作冲突、输入顺序无关、纯 DELETE、混合编辑非连续索引、全 NOOP、UNABLE 原子性、CRLF/Unicode/非目标字节保持、全删后的 S0 等价部署。

Simulator 验证包括：所有参试任务的实际 User 请求含相同约束，Parent/Candidate 配置摘要一致；构造“确认待执行动作”“完成后结束”“撤回请求”“合法转人工”交互检查终止语义。单元测试只能证明装配与状态机行为，不能证明 LLM 总能遵守 prompt。

### 8.2 固定输入的语义试验

预先冻结 Evolution 侧诊断样本：渠道规律完整/不完整、缺姓名字段与字段齐全的对照、人数边界、全失败但有支付状态证据、局部修订、应删除与证据不足的删除候选。真实样本和构造契约样本分开统计，不把构造证据加入正式学习。历史输入保留原文；其中旧 Simulator artifact 的解释不计入 v2 核心语义验收，不围绕其反复 patch Prompt。

对相同 group 输入重复 v17/v18 Diagnosis；对相同兼容编辑计划及依据重复 v17/v18 Editor。建议每项 3 次作为小规模诊断性试验，保留全部输出而非择优。DELETE 是新增功能，用 v18 专项样本验证，不能伪称 v17 支持同一计划。

人工离线审计以下项目，报告分母与具体链路：

- 已支持条件/行为关系的保留率；
- 新增无依据执行门槛、扩大适用范围、强化确定性的发生率；
- ADDRESSABLE 是否指出可实际改变的 Agent 决策；
- SHOULD_REMOVE 是否证明删除优于修订；
- NOT_ADDRESSABLE、UNABLE 和有效 gap 的数量，防止通过停止学习掩盖问题。

对比固定输入输出才能观察生成变化；跨轮输入不同不能当作固定输入方差。本项是离线研究评估，不新增在线语义门禁，也不把人工选择的最优输出送入正式演化。

### 8.3 分离 simulator 收益与 learner 收益

已有历史条件为“原 simulator + v17”。新的主要对照设为：

| 条件 | Simulator | Learner | 起点 |
|---|---|---|---|
| B | 修复版，共同冻结 | v17 | S0 |
| C | 与 B 完全相同 | v18 | S0 |

B/C 使用同一 32 Evolution / 41 Monitor 划分、相同任务、四轮上限、模型设置、seed 和 Gate；每轮仍为 32 + 41×2 = 114 次 Agent rollout，单条件最多 456 次，两条件最多 912 次，不含 learner、用户模型调用与预试验。停止规则提前触发时报告实际次数。

历史结果用于背景，B/C 才是修复环境下的 learner 比较。两组各一次 campaign 仍不足以证明稳定优势；资源允许时预先固定额外 seeds 或独立重复次数，对 B/C 对称执行，不能根据成绩决定只补跑哪组。

主报告保留 S、C、CS、VF、四象限和逐任务迁移。辅助审计报告确认同时停止的发生率、执行/未执行/转人工行为及其是否合理、各类 gap/编辑数与拒绝原因；不把“少停止”本身当成功。Monitor 只参与 Gate 和事后报告，不向 Diagnosis/Editor 回流轨迹、任务类别、隐藏机制或逐条规则修正建议。

另外可将 R4 最终 Skill 作为独立 continuation 试验起点，观察 REPLACE/DELETE；需另建配置和结果，不能与从 S0 的主对照混合。v18 从 S0 开始的第一轮可能没有 DELETE 目标，这是正常情况。

Gate 不变：ΔS ≥ 0、ΔC ≥ 0、ΔCS ≥ 0、ΔVF ≤ 0，且至少一项严格改善才 ACCEPT。新方法的设计目标是减少语义漂移并保持有效学习，不能以合规上升、规则更少或 DELETE 出现作为单独有效性证明。

## 9. 实施顺序与产物

1. **Simulator 独立修复**：公共约束、装配测试、实际 prompt 与版本冻结；另存历史兼容配置。
2. **Diagnosis v18**：沿用 v17 结构，扩展 kind 枚举和规则引用基数校验；将第 4–5 节写入通用 prompt，升级 schema、验证 envelope 与审计版本。
3. **Compiler v18**：补全 DELETE、确定性合并/排序、跨操作目标冲突及完整计划复验；Compiler 不接管语义判断。
4. **Editor/Application v18**：通用语义保持 prompt、文本单元子集覆盖、纯删除直通、混合原子应用及新运行时状态贯通。
5. **Pilot 与正式入口**：固定输入试验先检查链路；新建 v18 formal/config/freeze 与对应测试，完成 B/C 冻结后再启动正式模型实验。

实现模块可沿现有 `diagnosis_*_v17.py`、`compiler_*_v17.py`、`editor_*_v17.py`、`formal_v17.py` 的职责分出 v18 入口，未改变的公共能力复用。不要直接修改 v17 行为后仍沿用其版本名，不批量复制与修改无关的模块。必须让 schema、加载器、runtime 状态、冻结文件摘要和正式调度同时识别 v18，而不只修改 prompt 文本。

初次交付仅包含设计与实验依据。第 1–3 步的后续实现记录见下文；已进行三次 Diagnosis 模型调用，尚未实现完整 v18 learner 或生成 v18 Candidate。

## 10. 第 1 步实现与验证

实现文件：

- `src/skill_evolution/user_simulator_v18.py`：独立 `V18UserSimulator`，注册名 `user_simulator_v18`，共享约束版本 `v18-user-confirmation-1`。构造时保存原始 system prompt，并追加统一确认约束；不改写模型回复、不覆盖 `is_stop`、不增加重试。
- `src/skill_evolution/benchmark_runtime_v18.py`：复用现有任务注册、环境与构造组件，独立选择 v18 用户类；保留 S0/learned Skill 装配行为。没有覆盖默认 `user_simulator`，没有全局 monkeypatch，也没有修改 v17 文件或 tau2 源文件。
- `scripts/preflight_v18_simulator.py`：构造全部 73 个任务，核对初始 User state 的实际 system message，保存逐任务 prompt 原文、版本、共享约束摘要、完整 prompt 摘要及汇总文件摘要。不运行 Agent/User 模型，也不读取 `.env`。
- `tests/skill_evolution/test_user_simulator_v18.py`：新增 10 项测试，其中全任务测试逐一构造 73 个任务的 S0、learned Skill 与旧版实例。

无模型预检命令（输出目录必须不存在）：

```bash
python scripts/preflight_v18_simulator.py --output artifacts/v18_simulator_preflight_new
```

当前预检默认只读 v17 已有配置中的模型设置、任务划分及 S0；它不是 v18 正式 campaign 配置。输出 `user_prompts.json` 含 User Scenario 私有信息，只用于 Simulator 审计，禁止传给 learner。`summary.json` 为最后写入的完成标记，包含 prompt 文件摘要；消费快照前应核对摘要。后续正式配置应绑定该摘要，并将快照作为 `UnifiedEnvironmentAdapter(..., frozen_user_prompts=records)` 的参数传入，装配时逐任务验证完整记录，缺失或漂移直接拒绝。当前尚未接入 v18 formal/Monitor 调度及完整依赖冻结。

本次预检产物为 `artifacts/v18_simulator_preflight_001/`，覆盖 32 Evolution + 41 Monitor，模型调用数为 0。新增 10 项测试与 v17 formal/monitor 的 41 项回归测试均通过。测试确认实际生成请求包含约束、两种 Skill 模式使用相同 User prompt、默认旧类和 Agent 可见上下文不变、冻结记录漂移被拒绝。

状态机测试使用模拟模型回复：普通确认后仍有 Agent 执行机会，完成/撤回/转人工/信息不足仍可终止；即使回复违反新 prompt、仍包含“确认 + STOP”，也原样记录并终止。这里证明的是接入和终止语义，不证明真实模型已消除提前 STOP；残余发生率留待后续独立模型试验统计。

## 11. 第 2 步实现与验证

新增独立的 `diagnosis_contract_v18.py`、`diagnosis_references_v18.py` 与 `diagnosis_validation_v18.py`；扩展 SHOULD_REMOVE，保持四顶层字段、五字段 gap 和原有严格验收。输入复用未变化的签名 GroupDiagnosisInput v17.2；输出使用 `V18_VALIDATED_DIAGNOSIS` / `validated_diagnosis_v18.1`，不兼容 v17 Compiler 的输出封装要求。

完整定义与删除证据门槛见 [v18 Diagnosis 契约](V18_DIAGNOSIS_CONTRACT.md)。新旧对应测试共 150 项通过，v17 文件不改动；未接入 v18 Prompt 或模型调用。本步结构与引用校验不证明删除优于修订，也不执行 ADD/REPLACE/DELETE。

## 12. 第 3 步实现与初步语义试验

新增 `diagnosis_prompt_v18.py`（`v18-group-diagnosis-1`）、独立 `diagnosis_v18.py` transport 与固定三组输入的 `scripts/run_v18_diagnosis_pilot.py`。Prompt 覆盖条件关系归纳、候选规律保留、可执行 Addressability、Analysis→Gap 语义保持和删除的更高门槛，不含 benchmark 特例。模型请求使用第 2 步 Schema 与封装，保留一次调用、无修补、无重试的协议。

新旧相关工程测试共 184 项通过；固定 Evolution 输入上三次模型调用均为结构 VALID，但语义检查发现 R2 定价仍新增执行门槛、R3 定价仍把 STOP 后的执行视为可达决策。姓名外观规则未复现，具体价格与人数关系得到保留，但存在指导强度问题。详见 [首次试验报告](V18_DIAGNOSIS_PILOT_REPORT.md)。不将结构 VALID 当作语义验收通过；未生成 Candidate、运行 Monitor 或修改历史 v17。

## 13. Prompt v2 职责边界调整（2026-09-19）

上节是 v1 的历史观察，其中 STOP artifact 的判断不再作为 learner 缺陷或 v2 核心语义验收项；上游 Benchmark/User Simulator 负责提供合理轨迹，Diagnosis 不解析终态或补救运行器异常。

当前 Prompt 为 `v18-group-diagnosis-2`，已移除环境已结束、没有下一回合、恢复已结束交互等专门约束。保留具体行为可修改性的 Addressability，并加强三项 learner 要求：未知不自动生成额外限制或转人工要求；候选规律不强化为普适强规则；Gap 原样保持 Analysis 的条件、范围与 epistemic status，不额外安全化或保守化。

输入/输出 Schema、结构与引用校验均不变；仅更新版本绑定测试，保留已有完整输入、历史回放和新旧版本隔离测试，没有新增 Diagnosis 终态专项测试。Simulator 层已有终止行为测试保留，属于上游职责。历史 v1 请求/响应和 v17 均不修改。本次不运行新的模型试验；Prompt v2 的语义效果仍待验证。

## 14. Prompt v2 固定输入语义 Pilot（2026-09-19）

已对三组历史 Evolution 输入和两个构造开发样本各调用一次。5/5 结构 VALID；在不评分历史 runtime artifact 的正式边界下，核心语义 4/5 通过。三组历史输入的未知→额外门槛与候选→强规则问题明显改善，DELETE 构造样本正确选择 SHOULD_REMOVE；REPLACE 构造样本虽正确选择 NEEDS_REVISION，仍保留了证据未证明必要的 transfer fallback。

完整设置、逐组结论和限制见 [v2 Pilot 报告](V18_DIAGNOSIS_V2_PILOT_REPORT.md)。结果支持继续实现 Compiler DELETE，因为 Compiler 只做确定性映射；本次仍未证明 Diagnosis 稳定性或正式 campaign 效果。正式实验前保留一个可选的小版本 Prompt 修订点：规则修订时，任何继续保留的限制也必须有来源证据支持。

## 15. 第 4 步 Compiler DELETE（2026-09-19）

独立 v18 Compiler 类型、编译、计划验收与审计模块已实现，详见 [Compiler 契约](V18_COMPILER_CONTRACT.md)。确定性映射 MISSING→ADD、NEEDS_REVISION→REPLACE、SHOULD_REMOVE→DELETE；同操作重叠目标传递合并，跨 REPLACE/DELETE 重叠则以 PLAN/MIXED_OPERATION_TARGET_CONFLICT 拒绝整份计划。保持原始 Parent 绑定、完整 gap 覆盖与输入顺序无关性。

新旧相关测试 62 项通过；v2 Pilot 五份输出分别离线编译全部 VALID，共 4 ADD、1 REPLACE、1 DELETE。不同轮次/Parent 不混编，原始诊断不按语义评分筛选或修补。构造输入缺失的运行时 Parent 摘要由已核对 Parent 计算补充，历史文件不改动。v17 保持不动，0 新模型调用、0 Candidate。文本删除与 Editor 混合原子应用留待第 5 步。

## 16. 第 5 步 Editor 与文本应用（2026-09-19）

独立 v18 Editor 契约、输入包、Prompt、应用器和 runner 已实现，详见 [Editor 契约](V18_EDITOR_CONTRACT.md)。运行时保留全计划，模型只接收 ADD/REPLACE 原始索引，DELETE 由程序执行。混合计划先完整验收再应用，UNABLE/错误不应用任何删除；纯 DELETE 跳过模型，返回 APPLIED_DETERMINISTIC 并保存 Candidate。全 NOOP 仍 NO_UPDATE。

Prompt 加入条件/范围/确定性保持、不新增独立义务和冲突时 UNABLE 的约束，不添加 runtime artifact 特判。application.json 分别记录模型单元和确定性删除及原文/来源/摘要。未指定文本逐字保持，允许空或仅标题 Candidate。

相关新旧测试 117 项通过。已有 v2 SHOULD_REMOVE 样本完成零模型删除，移除数字姓名禁令且保留标题空白，产物为 `artifacts/v18_editor_delete_pilot_001`。本次未调用真实 Editor 模型、未运行 Monitor/Gate、未覆盖 Parent 或修改 v17；模型语义效果和正式调度接入仍待后续验证。

## 17. 第 6 步完整调度（2026-09-19）

独立 v18 formal、Monitor 后端、Gate 模块与 freeze/run 脚本已接通；未变化的经验、Grouping 和输入协议复用 v17。正式冻结默认四轮、32 Evolution + 41 Monitor，最多 456 个 Agent rollout；全部 73 个任务的 v18 User prompt 逐任务冻结并在装配时校验。私有 prompt 和 Monitor 数据不进入 learner。

VALID / APPLIED_DETERMINISTIC 都进入 Gate；空或仅标题的删除结果使用基线 Agent，保留 Candidate 文本和摘要。NO_UPDATE / UNABLE 停止并保留 Parent。只有完整 Monitor 的 ACCEPT 晋升。恢复绑定原配置与 manifest，复用已验收产物，归档中断尝试；从已提交轮次重建当前 Skill。详见 [正式调度说明](V18_FORMAL_EXPERIMENT.md)。

本步未调用真实模型、未启动正式 campaign；不修改 Diagnosis 的职责边界，也不以调度规则修补 transfer fallback 语义问题。

验证：532 项相关回归 + 1 项新增后端 checkpoint 测试通过；73 任务预检通过，0 模型调用。全目录测试受旧 v06 browsergym 依赖缺失阻断。记录保存在 `artifacts/v18_formal_integration_001/`。

## 18. Diagnosis 统一聚合边界（2026-09-20）

在 Prompt 修改前冻结统一 rubric 与通用组内混合配对对照。v3.1 存在逐关系判断到 group-level 汇总的歧义，因此最小更新到 v3.2.1：一个合法 gap 足以使组为 ADDRESSABLE，其他分支可 unresolved；全成功/合规组不得仅记录成功配方；负面分支没有替代动作或独立限制依据时不得生成 warning gap。

真实回归 13/13 结构 VALID、0 重试。原六组 6/6 通过，配对对照 2/2 通过。一个既有 negative-only 对照同时含有明确 policy prerequisite，与新统一 rubric 的“policy 可独立支持限制”发生评估冲突。Prompt 不再修改；新调用前将该混杂样本拆成纯负面与明确前置条件两个正交对照，两者均通过。最终有效语义语料 14/14 通过，v3.2.1 达到正式 freeze 门槛；既有正式 freeze 尚未更新。详见 [v3.2.1 回归报告](V18_DIAGNOSIS_V321_AGGREGATION_REPORT.md)。

## 18. Diagnosis Prompt v3.1 通用可学习性边界（2026-09-20）

Prompt 仅重写 Addressability 判定段，将可学习性拆为选择关系证据、执行可行性和输出合法性三步。原六组输入与 rubric 保持不变；另在改 Prompt 前冻结五类通用边界对照。连接内网后 11/11 调用一次完成且 VALID，原六组 5/6、通用边界 5/5 通过。

G03 已不再为缺少映射的行李问题生成 gap，但 G02 仍为 NOT_ADDRESSABLE。比较 v2/v3/v3.1 后确认语义跳转发生在 Analysis → Addressability：v3.1 不接受仅由失败动作的未观察补集推导替代行为。这与通用“动作有限但无选择依据”rubric 一致，却与原 G02 rubric 要求保留反向顺序候选形成评估冲突。本轮按约定停止修改 Prompt；v3.1 不进入正式 freeze。详见 [v3.1 回归报告](V18_DIAGNOSIS_V31_REGRESSION_REPORT.md)。

## 18. 第 7 步单轮端到端 Pilot（2026-09-19）

独立一轮 Pilot 已完成完整真实模型链路，32 个 Evolution 与 41 组 Parent/Candidate Monitor 全部完成，Gate 为 ACCEPT：Success +6、Compliance +7、CS +13、VF 不增加。结果证明完整调度和 Editor 接线可运行，但不以 Gate 通过代替 learner 语义验收，也不根据具体 Monitor 错题定向修改 Prompt。

6 个当前有效 Diagnosis 中，G01/G02/G04/G05 通过，G03 部分通过，G06 失败。主要剩余问题是：行李组在没有可执行额度映射时仍判 ADDRESSABLE；保险组把隐藏覆盖机制转成新的证明义务和默认拒绝。Editor 忠实保留了 Diagnosis 的条件和不确定性，未独立制造这些门槛。正式四轮实验前应先做 Diagnosis Prompt v3 的通用语义修订及固定输入回归。详见 [端到端 Pilot 报告](V18_END_TO_END_PILOT_REPORT.md)。

运行期间还发现并修复了重复恢复进程和旧 Grouping Diagnosis 审计混放问题：新增 campaign 文件锁；被替换的 Grouping 所属 Diagnosis 自动隔离。受并发影响的 Monitor 结果未进入最终 Gate。

## 19. Diagnosis Prompt v3 六组回归（2026-09-20）

修改 Prompt 前冻结端到端 Pilot 的 G01–G06 输入、v2 输出和语义 rubric；冻结和评分均不读取 Monitor 逐题结果。Prompt v3 只增加“ADDRESSABLE 必须有可执行替代行为”和“无法证明不能自动推出核实/拒绝/停止/转人工”两条通用原则，Schema、Compiler、Editor 和 Gate 不变。

6/6 调用结构 VALID、0 重试，语义 4/6 通过。G06 的 proof-or-deny 问题已消除；G03 仍产生没有隐藏映射支持的 basic-economy 行李禁止/澄清 gap；G02 则过度保守地退化为 NOT_ADDRESSABLE，丢失 cedar 局部候选规律。G01/G04/G05 通过。当前 v3 不进入正式四轮，详见 [v3 回归报告](V18_DIAGNOSIS_V3_REGRESSION_REPORT.md)。
