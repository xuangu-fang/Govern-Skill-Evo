# v28.5 Prompt 修改与静态审阅

审阅日期：2026-11-04。范围为四份完整 Prompt 与冻结 v28.3 的文本差异、接口兼容和职责一致性。审阅方式为本次逐段自查与本地静态核对；**不是独立模型评审，未调用模型。** 具体机器检查结果见 [design_validation.json](design_validation.json)。

本文保留设计阶段的审阅结论。后续独立实现与软件检查已完成；实验暂停后曾对 Editor 做表达压缩微调，现已按用户要求撤回；Preconditioner 和 Replay 各一段证据一致性修订仍保留，见下文。当前状态见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。

## 暂停后的 Editor 表达压缩微调（已撤回，历史记录）

当前 Editor 已逐字恢复为首次 v28.5 实验的冻结版本，包含撤回后续两处压缩措辞细化；原 v28.5 实施要求保留。以下差异和检查仅作为历史记录，最新撤回核对见 [editor_rollback_validation.json](editor_rollback_validation.json)。两次实验及自动跟进仍暂停。

2026-11-04：仅替换 Editor 的 `Input and implementation scope` 中一段。明确 Effective Update 是行为规格，不必保留其句式；将修订融入相关指导，避免对未改变条件的冗余复述；仅删除既不增加行为要求、也不提供必要执行澄清的解释、示例和保护性重述。改写后仍需保留的旧条件及能消除执行歧义的示例应当保留。保留所有实质触发、动作、范围、强度、例外、优先级及依赖，不授权 Editor 改变行为选择，也不增加字数配额、压缩阶段或模型调用。

该次 Editor 修订未改动其余三份 Prompt、运行代码、配置、patch 合同与输出字段。暂停实验的冻结 Prompt 和归档保留原文，修订用于后续从第一轮开始的新实验，不恢复旧实验。具体差异见 [单段修改](diffs/editor_expression_compression.diff)，当时的离线核对见 [editor_revision_validation.json](editor_revision_validation.json)。未验证模型实际压缩效果。

## 暂停后的证据一致性微调

2026-11-04：Preconditioner 的联合协调审查段落要求新增或收紧条件后回查支持案例。若修订要求排除原案例，或导出的答案与该案例支持的修正目标不一致，应解决不一致或明确缩小声称的覆盖范围。不得继续声称该案例支持修订后的要求，但冻结的 basis 仍保留原提案来源，不删除或重写。

Replay 仅替换 fidelity review 中的相近表述：在称答案变化符合 Update 之前，核实决定性适用条件及相反证据；不能根据 EM 改善或答案形式倒推前提成立。可见证据无法确定时记录未知，证据否定条件或答案违背书面要求时记录不一致；不推断隐藏 Actor 过程，不因条件未知自动要求 null，继续使用原行为关联合同。

两处均不加入具体案例名字、答案或特例规则，不增加模块、字段或模型调用。该次证据一致性修订时，Diagnosis 和当时的 Editor 保持不变，运行配置、Memory、Gate 及归档不变。差异见 [Preconditioner](diffs/preconditioner_evidence_consistency.diff)、[Replay](diffs/replay_evidence_consistency.diff)；该次离线核对见 [evidence_revision_validation.json](evidence_revision_validation.json)。实验仍暂停，尚未验证行为或成绩改善。

## 1. 修改定位

| 编号 | Prompt 定位 | 替换内容与目的 | 保留边界 |
|---|---|---|---|
| D1 | Diagnosis 开头、Examine current evidence 最后一段 | 当前证据提出行为修正；Parent 保留为背景，取消全面 Parent 审计义务 | 不屏蔽 Parent，不把失败等同于缺规则，不允许泛泛建议 |
| D2 | Construct complete, scoped Updates 中 Goal 与协调段落 | Original 是完整行为提案，整体整合交给 Preconditioner；删掉要求 Diagnosis 决定所有旧规则修订方式的重叠职责 | 自己的提案不能相互矛盾；必要行为依赖与有依据的条件仍需明确 |
| D3 | Evidence、reason 字段说明 | 保留材料性条件及成功/反例引用，避免关键证据只留在 reason | Plan 引用筛选、basis 格式与 no_change 合同不变 |
| P1 | Preconditioner 开头、Frozen proposal and available input | 把 Original 作为进入当前 Skill 的修改来分析，检查远处相关旧规则及实际行为增量 | 不新增 Diagnosis，不扩大到无关全篇重写 |
| P2 | Decide Direction Scope and Coordination | Parent 覆盖/交互与相关 Memory 联合决定 D/S/C；允许必要整合，减少无依据的保护清单 | 不以短字数、少列表项或操作比例为目标，不牺牲有效区别 |
| P3 | Choose one complete adjustment for every Original | KEEP 必须认可完整协调；reason 中的兼容条件必须进入 REPLACE text | 不要求为展示作用而 REPLACE，无相关历史也可 KEEP |
| P4 | D/S/C 的联合审查段落 | 检查存活 Updates 的共同含义，防止旧冲突残留及跨 ID 偷渡修复 | ID/Goal/basis 冻结；不声称任意子集都有效，不改变 Gate |
| E1 | Editor Input and implementation scope | 精确落实替代/限定/整合/删除；减少通则和保护清单复述 | 只实施 Effective Update，不自行选择新行为 |
| E2 | 同节最后一段 | 本次调用内检查实施造成的重复与冲突；关键策略缺失按原 blocker 合同处理 | 不新增 Reviewer，保留全部 patch 定位、映射和组合规则 |
| R1 | Replay Relate each EM transition to actual behavior | 先比较完整可见差异，区分行为关联与得分解释 | 仍只处理 EM 翻转，不要求独立因果证明 |
| R2 | 同节归一化段落 | 核对标点/空格变化，避免错误解释；使用准确行为描述 | 评分器不变，不擅自扩展 reference 或重算新评分 |
| R3 | Self-contained event Knowledge、fidelity review | 条件与结论限于当前事件，使用具体限制，不用模板化免责声明掩盖遗漏 | Knowledge 字段、关联方式及 Memory 范围不变 |
| R4 | 输出形状示例 | 不仅凭 reference 匹配称 qualifier 为题目必需或 Parent 语义正确 | 仍为形状示例，不加入真实训练答案 |

全部变更见 [Diagnosis diff](diffs/diagnosis_from_v28_3.diff)、[Preconditioner diff](diffs/preconditioner_from_v28_3.diff)、[Editor diff](diffs/editor_from_v28_3.diff)、[Replay diff](diffs/replay_from_v28_3.diff)。D/P 中的视图名变更仅隔离版本身份，现已完成运行绑定。

## 2. 职责冲突检查

### Diagnosis 到 Preconditioner

Diagnosis 不需要写完整编辑计划，但必须写清具体行为、当前条件和重要保护边界。不能把“减轻 Parent 审计”理解为“允许提案自身含糊”。旧的要求 Diagnosis 全面指定 Parent 修订/整合方式的段落已替换；没有在尾部附加相反职责。reason 不下传的事实仍明确，因此相关材料性证据必须进入 text/basis。

### Parent 与 Memory 的关系

Preconditioner 先辨别现有覆盖及待改变行为，再用相关历史调整。历史 Retain 不证明旧规则仍存在；当前 Parent 是现状依据。相关 Memory 支持或反驳只在报告条件范围内成立。原历史证据权限、联合执行不确定性和 null 关联解释全部保留；本次不新增历史事件类别或额外利用流程。

### KEEP 与 REPLACE

“主方向合理”不能单独支持 KEEP；若兼容性需要新限定，应将限定写入完整 REPLACE。对原本充分协调的提案仍允许 KEEP，不设修改率要求。REPLACE 可定位旧指导而不复制大段 Parent；不能仅写“同前，加一个例外”。因此完整性与简洁性不冲突。

### 整合与映射

允许整合相关旧 Skill 规则，但不允许合并 Update IDs。必要相关修改由对应 Update 负责，不能把两个独立修复偷放进一个 patch。新增文字并非一律禁止；当存在真实新行为时可以新增。现有 Gate 可能只保留部分 patches，因此不得将未来共同保留当作既定事实；不引入依赖图或保证所有组合均可执行。

### Editor 的实施边界

检查实际改动后的含义属于实施自查；发现上游未决定的关键行为优先级，不能自行补策略。相关旧规则定位与删改应落实；无关历史问题不扩大授权范围。原本已有 patch=null 和 patch="" 语义，适配沿用而不增加新分支。

### Replay 的解释边界

多特征变化需要完整记录，不自动禁止与一个 Update 建立明确行为连接。Knowledge 可以说“删除类别词与 u1 相符”，同时说明“还改变分词，所以不能仅用删除类别词解释全部分数变化”。保持关联与因果限制的区别，避免新 Prompt 变成要求严格独立因果证明的门槛。

## 3. 历史观察与修改依据

以下仅引用训练归档；未将案例题目、答案或 ID 注入生产 Prompt。

| 历史观察 | 归档来源 | 对应设计要求 |
|---|---|---|
| v28.4 R14 u3：reason 声称保护虚构人物列表分支，正文没有明确处理重叠范围 | [Preconditioner](../../../experiments/campaigns/v28_4_searchqa600_batch30_20261104_180344/rounds/R14/preconditioner/attempts/001/parsed.json) | 协调条件进入 text |
| v28.4 R17 u1：已经要求修订类别/后缀指导，Editor 仍新增平行段落 | [Editor](../../../experiments/campaigns/v28_4_searchqa600_batch30_20261104_180344/rounds/R17/editor/attempts/001/parsed.json) | 旧文字实际被修改 |
| v28.4 R19 u4：要求修订标题完整性规则，patch 只新增副标题规则 | [Editor](../../../experiments/campaigns/v28_4_searchqa600_batch30_20261104_180344/rounds/R19/editor/attempts/002/parsed.json) | 落实替代要求并检查整体含义 |
| v28.3 R09 u1：结合敬称保留收益、题目已给称谓省略收益和中间名退化，形成有差别的修正 | [Preconditioner](../../../experiments/campaigns/v28_3_searchqa600_batch30_20261104_022828/rounds/R09/preconditioner/attempts/002/parsed.json) | 保持已有的历史预条件能力 |
| v28.3 R03 P11：high-pressure job → high pressure，同时改变类别词和分词 | [Replay](../../../experiments/campaigns/v28_3_searchqa600_batch30_20261104_022828/rounds/R03/replay/attempts/002/parsed.json) | 不遗漏同时变化 |
| v28.3 R15：Justice → Treasury 被概括为 answer-boundary change，实际改变所选部门 | [Replay](../../../experiments/campaigns/v28_3_searchqa600_batch30_20261104_022828/rounds/R15/replay/attempts/001/parsed.json) | 行为描述准确 |

这些观察支持设计修改的依据，不是新 Prompt 已解决问题的证据。不将单次改善当成稳定泛化效果；后续直接通过真实训练和测试观察新版本表现。

## 4. 本次静态结论与未验证项

已完成：逐段职责检查；完整 Prompt 取代片段草案；冻结快照与 diff；输出字段、证据权限、Actor 协议、历史 Memory 说明、patch 合同保留核对。精确文件检查由 [design_validation.json](design_validation.json) 记录。按用户调整，不保留独立验收场景或训练前固定输入模型对照。

未完成也未声称完成：模型是否按 KEEP 标准判断、是否会正确整合旧规则、Editor 是否忠实实施、Replay 事实质量提升幅度、训练成功率、最终 Skill 长度与 Test 效果、预条件机制独立收益及文献层面的新颖性证明。

完整 Prompt 的公共证据/运行说明仍保留 v28.3 原文。本次不顺带重构公共 Prompt 模板；各模块文本增量记录在静态报告中，但 Prompt 字符数不是 Skill 质量或模型行为的验收标准。
