# LiveMathematicianBench v27.1 设计稿

状态：**独立 v27.1 链路已实现，离线验收完成；正式六批训练已于 2026-11-04 13:20:25 启动，Test 未启动（Asia/Shanghai）**。本目录保留设计步骤 1–3 的方法、提示词和合同；当前实现、验收记录和操作说明见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。Diagnosis、Preconditioner、Replay 已同步数学符号与执行引用的区分说明；Editor 保持设计稿原文。`experiment_plan.json`、`source_map.json` 和 `design_validation.json` 是设计阶段快照；可执行配置为 [v27_1_lmb53.json](../../../experiments/configs/v27_1_lmb53.json)。

## 1. 审阅入口

| 内容 | 文件 |
|---|---|
| 目标、来源、实验设计与已知局限 | 本文 |
| 完整英文 system Prompts | [Diagnosis](prompts/diagnosis.md)、[Preconditioner](prompts/preconditioner.md)、[Editor](prompts/editor.md)、[Replay](prompts/replay.md) |
| 字段、交接、证据权限、Gate、Memory、恢复和分支 | [CONTRACTS.md](CONTRACTS.md) |
| 各项迁移与提示词联合审阅 | [PROMPT_REVIEW.md](PROMPT_REVIEW.md) |
| 机器可读来源和设计参数；不是可执行配置 | [source_map.json](source_map.json)、[experiment_plan.json](experiment_plan.json) |
| 来源原文快照和对应路径 | [baseline/source_files.json](baseline/source_files.json) |
| 文档静态检查；不代替离线实现验收 | [design_validation.json](design_validation.json) |

四份 Prompt 均已展开为完整文本，包含实际 LMB Actor 基础协议和 65,536 运行边界，没有待替换模板或需要拼接的公共段落。来源快照为本次设计时读取的文本；上游以后变化不自动升级本稿。

## 2. 目标与方法来源

将 v29.4／v28.3 的直接批次 Diagnosis、逐 Update 编辑与选择、翻转事件 Replay 和追加式 Memory 迁入 LMB。待验证假设是：在保留数学任务原执行协议的条件下，使提案、实际修改、观察事件和采纳决定能够逐项对应，减少整包接受时其他修改一同进入 Skill。标签式回答能否提供足够可靠的行为关联，需要真实实验检验。

| 来源 | 采用内容 | 不随迁移改变的边界 |
|---|---|---|
| [v29.4](../v29_4/README.md) | 以 v29.2 为基础删除 Grouping；Diagnosis 直接比较全批；原提案与 D/S/C 方法主体 | 不自动继承 v29.3 额外提示词修订 |
| [v29.2 Gate](../../../src/skill_evolution/v29_2/gate.py)及 Editor/Replay | 无 Checks、完整调整动作、映射 patch、翻转事件、选择性 Gate、追加记忆 | 不恢复旧整包 Gate；不增加独立 Update 执行 |
| [v28.3 合同](../v28_3/CONTRACTS.md) | EM 迁移、四阶段交接、无损共享、引用修复、顺序 Memory ID 和轻量恢复 | 不复制 SearchQA passage、名称偏好、token F1 或 600 秒方法超时 |
| [v27 LMB](../v27/README.md)及当前事实/评分实现 | 原问题与选项、确定性打乱、标签解析、Actor 基础协议、原始字段白名单 | 不改评分、不增加定理/证明草图输入、不开放隐藏推理 |
| [最近完成的 v27 训练](../../../artifacts/methods/v27/v27_main_actor65536_20261102_230306/README.md)及[生效 Test](../../../artifacts/methods/v27/v27_main_actor65536_20261102_230306/test_65536_restart_20261103_v1/README.md) | 训练/Test Actor 均 65,536；原数据、顺序、初始化、六次总尝试 | 不沿用旧 49,152 Test 或混合预算补测，不继承学习产物 |

四份 Prompt 的直接适配底稿为 v28.3；方法的规范来源仍是 v29.4 的 Diagnosis/Preconditioner 和其沿用的 v29.2 Editor/Replay。两组来源原文均保存，分别生成差异以便审阅。没有将 v28.2 Prompt v2 的五组方法修订整体引入。

## 3. 相对现有 v27 的方法变化

| 部分 | v27 | v27.1 设计 |
|---|---|---|
| Grouping | 独立模型阶段 | 删除，不生成替代分类报告、Group ID 或调用槽 |
| Diagnosis | 全批执行 + Grouping；goal/updates/checks | 全批直接分析；goal/updates；条件与保护边界进入 Update text |
| Preconditioner | Update diff、旧调整字段与 Checks | KEEP／全文 REPLACE／WITHDRAW，保持原 ID 和 basis |
| Editor | 整包 patch | 每 Update 一个 patch，共同定位原始 Parent |
| Replay | 全批比较、可修订历史 Knowledge | 只看当前 EM 翻转；每题一条事件；关联一个 Update 或 null；不读取历史 |
| Gate | Candidate 成功数严格增加才整包 ACCEPT | 逐 Update 计算关联 G/L，只组合 Retain patches |
| Memory | 旧 entries/sources 和历史修订 | 按轮追加 Effective Updates、决定、事件，历史不改写 |
| 发布 Skill | Parent 或 Candidate | Parent、Candidate 或本轮尚未执行的新组合 |
| 运行 | 旧版来源/历史校验路径 | 当前轮完整校验，已发布检查点轻量读取；明确新版本隔离 |
| Editor 预算 | 16,384 | 32,768；因此是整体方案比较，不是纯方法单因素实验 |

```text
Parent batch → Diagnosis → Preconditioner → Editor
  → Candidate batch → verified EM-transition pairs → Replay → Gate
  → append Memory + publish Selected Skill → next round
```

Diagnosis 原先也能看完整批次；删除的是前置模型解释层，不是首次开放完整证据。保留有依据的单案例提案、必要联合动作、多 Update 和 no_change；不固定 Update 数量、不按预期 Gate 去留拆分。无 Stage0、新 Verifier/Repair、Knowledge 审查、逐 Update 独立 Actor 调用、重组后额外训练验证或新因果归因器。

## 4. LMB 的证据与任务适配

Actor 看到固定协议、当前 Skill、完整题干和五个呈现选项。方法事实视图看到当前普通响应、解析标签及对应选项文本、训练评分和映射后的正确标签/文本；不附加独立定理、证明草图、论文或其他原始元数据。题干/选项自身包含的数学内容当然保留。Test 内容不得进入训练链路。

问题和选项可直接核对；标签式普通响应不展示计算、排除、检验量词或证明过程。Diagnosis 可根据可见的题目要求与选项差异提出合理假设；Replay 可根据具体的选项内容变化建立有限行为关联，但不能把标签翻转本身当作某条规则被遵循的证明。若多个 Updates 无法区分或关联不足，记录 null。

任务适配区分数学选项选择、题目要求的结论强度/完整性、标签映射和提交格式；这些是分析角度，不是新字段或强制分类流程。非参考选项未必是数学假命题，可能只缺少题目要求的条件或刻画。不能将“最强”“最长”“更熟悉”变成无条件选择偏好，也不根据本次 Test 的具体题目或答案制定规则。

基础协议要求恰好一个 `answer` 元素，内容为单个大写 A–E 标签，元素外无文字、无嵌套元素。保持原解析器的容错行为及 EM：**格式要求、记录的 format_compliant 和评分正确不是同一件事**。现有 format_compliant 未完整检查元素外文字，不把它升级为新的严格校验器。LMB 的 f1 等于 em，不存在额外部分分或 F1-only 事件。精确规则见合同第 2 节。

## 5. 模块职责与传递

| 模块 | 能看到的输入 | 不能依赖的信息 |
|---|---|---|
| Diagnosis | 完整 Parent、全批当前 Parent runs、共享消息 | 历史 Memory、Candidate、Group、隐藏推理 |
| Preconditioner | Parent、冻结 Original Plan、Plan 直接引用的完整当前执行、历史 Memory | Diagnosis reason、未选执行、历史原始执行、Candidate |
| Editor | Parent、goal、Update id/text | basis、runs、Memory、上游 reason、参考答案 |
| Replay | Parent、actual diff、有效 goal/id/text、映射 patches、翻转 pairs/runs、共享消息 | 历史 Memory、basis、上游 reasons、未翻转执行、Gate 决定 |
| Gate / Memory | 当前已验证程序记录 | 不调用模型补做判断，不把未归因事件强分配给 Update |

Preconditioner 沿用扫描**整个 Plan 的 goal/text/basis**中的合法直接执行引用，Diagnosis reason 不参与筛选；关键支持、成功例和反例仍应进入对应 basis。实施条件必须经过有效 Update text 传到 Editor，不能只留在解释中。

## 6. 拟固定实验设计

这些值用于本稿审阅，尚未写入 `experiments/configs`。完整 ID 顺序保存于 [experiment_plan.json](experiment_plan.json)，只含成员/调度而非题目或答案。

| 项目 | v27.1 设计值 |
|---|---|
| 内容 revision | `6f53c5ff7227633ea954b2847cd590314d582047` |
| 优化池 | 原 SkillAdam 成员视图：35 Train + 18 Selection = 53；effective split=train，保留 source_split |
| 批次 | 原 `10/10/10/10/10/3`，单遍、固定顺序，不重新采样或打乱任务 |
| Test | 原 124 题及顺序；不是 prepared_v1 的 125 题视图 |
| 选项 | 原每题 seed=42 + task ID 的确定性置换，呈现为 A–E；不改变标签映射 |
| 初始化 | [原初始 Skill](baseline/lmb/initial_skill.md)、空 Memory `{"rounds":[]}`；不继承任何最终 Skill、Memory、缓存或旧响应 |
| 模型 | deepseek-flash，direct HTTP，thinking enabled，reasoning_effort=medium，temperature=1.0 |
| 并发 | Train 上限 20、Test 16，沿用 LMB；六批内有效并发不超过当前批大小 |
| 输入保护 | 4,000,000 字符 / 6,000,000 UTF-8 字节；不设 context_window_tokens、不截断证据、不设 Skill 字符上限 |
| Test 选择 | 六轮完成后仅评估最终 Selected Skill；不按 Test 选 checkpoint，不补测，不自动增加预算 |
| 执行入口 | 未来采用显式 train/test/resume；训练结束本身不自动运行 Test |
| 设计阶段范围 | 只交付设计；后续实现及离线验收记录见 IMPLEMENTATION.md，真实实验尚未启动 |

| 调用 | max_tokens | timeout_seconds | connect_timeout_seconds |
|---|---:|---:|---|
| Actor：训练与 Test | 65,536 | 300 | 10 |
| Diagnosis | 32,768 | 300 | 沿用 LMB 方法传输配置，不引入新参数 |
| Preconditioner | 32,768 | 300 | 同上 |
| Editor | 32,768 | 300 | 同上 |
| Replay | 32,768 | 300 | 同上 |

删除 Grouping 的额度不转移给其他模块。max_tokens 包括供应商计入的推理 token，不等于普通文本长度或输入上下文容量。

Actor 的首次、技术错误及 length 共用最多六次总尝试，无隐藏 SDK 重试；间隔 1×尝试序号秒。方法调用的技术错误、length、输出解析/校验失败共用六次总额度，间隔 2×尝试序号秒，输出纠错只带最近一次普通输出和错误。正常 stop 答错/格式不合规不补答；合法语义 no_change、KEEP、WITHDRAW、null 不重采样。恢复不重置额度，耗尽不补零分。首版不设外层自动重启或技术错误免计政策。

## 7. 对照与解释范围

主要历史对照为最近完成的 v27 65,536 训练及完整 65,536 Test：**52/124，41.94%**。来源：[Test 汇总](../../../artifacts/methods/v27/v27_main_actor65536_20261102_230306/test_65536_restart_20261103_v1/standard_test_summary.json)。该历史结果可复用作探索性对照，不宣称控制了跨时间模型服务与随机采样变化。

旧 **59/124** 使用不同训练预算及混合预算补测，仅作历史背景。[SkillAdam 45/124](../../../experiments/methods/skilladam/lmb/lmb53_actor65536_20261103_115844/README.md)虽然 Actor 为 65,536，但 Test 技术错误免计额度，不能称为严格同重试政策对照。本稿不重新运行或修补这些基线。

DocVQA 的 v29.2 为 326/374，v29.4 为 323/374；SearchQA v28.3 相对 v28.1 从 1174/1400 到 1187/1400。这说明版本并非单调改善，也不能单凭现有结果归因于删除 Grouping。依据：[DocVQA 比较](../../../experiments/comparisons/v29_3_revised_docvqa_20261104_003026/comparison.md)、[v29.4 汇总](../../../experiments/evaluations/v29_4_docvqa_test374_editor32768_20261104_015530/summary.json)、[SearchQA 分析](../../../experiments/analysis/v28_3_vs_v28_1_20261104/analysis.json)。

首版完整实验应报告：最终 EM、完整覆盖、逐轮配对增益/退化、提案及调整、Retain/Reject/Defer、未归因正负事件、每个 Retain 的支持题数、Selected 执行来源、Skill 长度、物理请求与各类重试、输入/输出/推理 token、耗时。训练中不同轮使用不同 Skill，不能把累计 Parent/Candidate 成功数称为最终固定 Skill 的训练准确率；推理 token 已计入输出时不重复相加。

此 Test 已有多轮历史结果并参与版本讨论；本稿只用汇总和协议确定设计，不把 Test 实例编入提示词。未来同集评估应表述为开发背景下的探索性复评，而非全新盲测。重复运行、新 held-out 数据或额外消融属于后续独立实验，不包含在当前设计交付中。

## 8. 关键局限与后续验收

- 标签回答可能使大量翻转无法明确归因；null 必须保留，不为让 Gate 有票而强制关联。无关联不等于无效果、无风险或纯噪声。
- 未归因退化进入 Memory，但不计任何 Update 的 L；没有整包风险否决或净收益兜底。应在报告中展示其数量，不暗示已被因果排除。
- 每批最多 10 题，末批只有 3 题；单题支持很稀疏，Retain 只是当前选择结果，不证明稳定泛化。
- Updates 联合执行一次；patch 可组合不证明行为独立。必要依赖应在提案中保持完整，程序不增加依赖求解器。
- 重组 Selected 可能从未在该轮执行；下一轮 Parent 或最终 Test 才提供真实成绩。未翻转任务（包括持续失败及错误选项之间变化）不进入 Replay Knowledge；Diagnosis 仍看完整批次。
- 引用修复沿用现有明确语法和权限；静态合法性不验证归因真实性，不通过放宽证据权限减少重试。

实现验收覆盖数据/映射与评分一致、四阶段接线、证据白名单与无损还原、patch 与所有 Gate 分支、无事件记录、原子发布/恢复、六次额度及跨版本隔离。可用合成 53/124 调度检查覆盖，不把它说成真实数学效果验证。

本稿的待审阅选择是方法来源、65,536 Actor／32,768 四模块预算、六次总尝试无补测、现有归因/Gate 以及轻量顺序提交设计。没有尚未填写的占位参数。本次授权已完成独立实现和离线验收；下一步是审阅实现与验收结果，再决定是否开展真实实验。

## 当前正式训练

[本次运行](../../../artifacts/methods/v27_1/v27_1_lmb53_20261104_132025/README.md)按冻结配置进行六批训练；完成后先汇总最终 Selected Skill，不自动启动 Test。
