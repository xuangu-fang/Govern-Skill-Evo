# V22 ALFWorld 57 项五轮正式持续自进化实验

> 新授权：仅豁免当前R5 Memory完整输入的400000字符限制，保留1M上下文检查，正在从Memory继续，见[容量修订与最终结算](ALFWORLD_57_FIVE_ROUND_RECOVERY_06.md)。

> **最新结算（2026-10-17）：三个R5 Candidate网络故障已归档并恢复成功，114条完整Parent/Candidate episode均已完成。R5为6/9→7/9，Gate ACCEPT；Memory完整消息414275字符超过冻结400000上限，在API调用前停止。完整共同发布仍为4/5轮。** 详见[三任务恢复与当前正式报告](ALFWORLD_57_FIVE_ROUND_RECOVERY_05.md)。

|轮次|Parent|Candidate|Gate|共同发布|
|---|---|---|---|---|
|R1|12/12|12/12|RETAIN|完成|
|R2|10/12|7/12|RETAIN|完成|
|R3|8/12|7/12|RETAIN|完成|
|R4|9/12|9/12|RETAIN|完成|
|R5|6/9|7/9|ACCEPT|Memory容量超限，未发布|

当前正式状态仍为R4 No Skill＋2条Memory，R5 Candidate没有完成正式发布。没有删减历史或放宽容量规则，没有重复调用成功Fusion/Editor；全部中断前缀通过状态及请求体一致性核验后续跑。当前为确定性容量阻碍，同配置重启不能消除。

累计2360次HTTP尝试，输入3461077、输出3461039 Token（其中推理3219026），已报告usage估算约16.55元，另有4笔请求费用未知；Memory此次未发送API。原始失败、成功调用及恢复去重来源全部保留。历史Effect进入实际Fusion理由，但单次连续实验与R5局部改善不能证明预条件化优于无Memory；独立Test未参与。

历史报告：[Editor恢复](ALFWORLD_57_FIVE_ROUND_RECOVERY_01.md)、[R3 Fusion恢复](ALFWORLD_57_FIVE_ROUND_RECOVERY_02.md)、[R4网络恢复与R5原截断](ALFWORLD_57_FIVE_ROUND_RECOVERY_03.md)、[R5 Fusion恢复与三个网络故障](ALFWORLD_57_FIVE_ROUND_RECOVERY_04.md)。以下保留最初冻结、Preflight和首次失败档案，其中历史结果不覆盖上表最新结算。

## 首次运行历史档案

以下保留首次运行记录（2026-10-16，Asia/Shanghai）：**正式实验已真实启动，但未完成五轮：在Round 1 Editor的实现摘录契约失败处按冻结协议停止，完整发布轮数为0/5。** Parent完成12项、12/12成功、171步；未执行Candidate、未产生Gate、未发布Skill或Memory。运行不是Pilot，未追加历史探针或重采样。


## 冻结协议与边界

实验源码与配置：`experiments/methods/v22/23_alfworld57_five_round/`。
正式档案：`artifacts/methods/v22/23_alfworld57_five_round/formal_run/`。

- 算法 `v22.unified_dsc.v6`，输入 `v22.p1_shared_input.v1`，引用 `v22.typed_references.v1`。
- 新运行协议 `v22.alfworld57_five_round.v1`；稀疏 revision 优先加载本次运行适配，算法继承 22，其他源码继承 21。实际加载路径及哈希见 `offline/preflight_summary.json`，完整 132 份源码快照见 `formal_run/runtime_freeze.json`。
- 官方 `https://api.deepseek.com`，Actor 和全部语义阶段均为 `deepseek-flash`，绑定既有 endpoint routing v2；运行期间核对 endpoint 与响应模型，禁止回退。
- 初始 No Skill、空 Memory，无 Stage 0。每轮共同发布有效 Skill／Memory 后，下一轮重新从磁盘读取。
- 任务来自适配器 `skillopt_39_18_134` 的原始 Train 39 项及 Selection（原始 split 为 `val`）18 项。保持原条目、ID、split、游戏文件身份和来源；显式 `development` 用途允许本次优化。顺序为原始 Train Manifest 后接原始 val Manifest，不按表现排序。
- 五轮分组为 12、12、12、12、9；不重复、不替换。R1：train:0000–0011；R2：train:0012–0023；R3：train:0024–0035；R4：train:0036–0038 与 val:0000–0008；R5：val:0009–0017。唯一身份以完整冻结 Manifest 为准，不能仅凭此缩写重建。
- 种子：环境 42、分类 alias 200；不随机打乱任务顺序；沿用调用参数，不额外加入服务端 seed。
- 既往开发接触记录保留在 `config/prior_contact_inventory.json`，至少 43 项有归档开发 episode；另绑定此前明确接触清单，不能把其余项宣称为绝对未接触。旧轨迹、旧 Skill 和旧 Memory 不进入本次学习输入。独立 Test 不参与更新、机制选择或本次任务替换。

## 执行与容量预算

Actor 最多 8 并发，每 episode 最多 50 步；Parent/Candidate 同任务、同 seed 和环境配置，使用原轨迹验证及配对核验。Gate 只在同批 Candidate 成功数严格大于 Parent 时 ACCEPT，其余合法比较 RETAIN。RETAIN 保留 Parent Skill，但仍按真实编辑、有效 Update 和当前配对执行学习 Memory。无修改或缺证据等合法分支按既有契约结算，不虚构 Candidate 成绩。

五个语义阶段使用 v6，其中 R1 Fusion 也实际调用模型处理空 Memory。合法分支可以按既有机制跳过后续不适用阶段。参数为 temperature=1、thinking enabled、reasoning_effort=medium、stream=false。Actor max_tokens=16384、读取超时300秒；分类／Diagnosis／Fusion／Editor max_tokens=32768，Memory max_tokens=65536，语义读取超时600秒。推理 Token 包含在输出预算中。

每次语义调用前保留完整 messages，并检查 compact JSON 的 400000 Unicode 字符上限；同时用 UTF-8 字节数＋8192 framing Token 余量作为保守输入 Token 上界，加请求输出预算后不得超过1000000。它不是实际分词或计费量。模型上下文依据：[DeepSeek 官方模型说明](https://api-docs.deepseek.com/quick_start/pricing/)（本次启动前核对1M）。不截断输入、不删除历史依据或自动压缩语义内容。

总上限114个episode、5700次Actor逻辑请求、25次语义调用。Actor保留现有最多6次同请求HTTP状态重试；语义重试、episode重跑、输出修复、额外候选均为0。容量、传输、JSON／契约、截断、配对或发布错误耗尽冻结预算后保存当前阶段与费用并停止。成功阶段不会被重跑；本协议没有失败后的自动重启。

历史08 R2的10对轨迹共有474步，若仅按其23.7步/episode均值推算，114条约2702步；任务混合、Skill和模型随机性会改变这一数值。历史Memory既有耗尽65536额度的失败，也有约17k–56k输出的完整响应。上述只用于资源预估，不承诺固定耗时或金额；历史实测源绑定于既有 `budget_evidence.json` 和验证档案。

## 离线 Preflight

最终通过421项继承V22回归、35项Adapter测试、14项引用专项、3项本次五轮合成测试。合成五轮覆盖114个槽位、25次模拟语义阶段、ACCEPT／RETAIN交替、拒绝Candidate后Memory学习、历史Effect进入后续Fusion、共同发布及完整档案核验；技术中断测试确认停止在R2 Fusion，保留R1发布状态，不启动R3。容量超限测试在调用前拒绝。

核对57个原始任务游戏文件、唯一ID及游戏路径、分组顺序、源码实际加载路径、Profile、P1、引用契约和Prompt哈希。正式runtime冻结摘要为 `9a6b7fe69d0fd553312210df8e1d399e0e201bbd5c28587ed2108aa95a2de3f9`。

早期预检目录 `campaign/` 从未启动；新增离线夹具发现容量审计目录创建遗漏，以及开发池学习交接和验证器的两轮协议条件遗漏，均在任何正式调用前修复。其后以最终源码重新创建 `formal_run/` 冻结并通过检查。旧实验及原始失败档案未改写。

离线通过仅证明程序路径、来源及契约可贯通，不证明模型自然语言判断正确，不构成真实ALFWorld成绩。

## 正式结果与准确停点

| 轮次 | 冻结任务数 | Parent成功数/成功率 | Candidate | Gate | 结算状态 |
|---|---:|---|---|---|---|
| R1 | 12 | 12/12，100% | 未执行 | 未产生 | Editor契约失败，未发布 |
| R2 | 12 | 未执行 | 未执行 | 未产生 | 未开始 |
| R3 | 12 | 未执行 | 未执行 | 未产生 | 未开始 |
| R4 | 12 | 未执行 | 未执行 | 未产生 | 未开始 |
| R5 | 9 | 未执行 | 未执行 | 未产生 | 未开始 |

正式开始及结束时间见 `formal_run/report.json`，整次墙钟761.90秒（约12分42秒，包括本次环境与语义阶段）。五轮运行器已启动；**停止原因是技术契约失败，而非Parent全成功或成功率不能增长**。Parent全成功后仍真实执行分类、Diagnosis、Fusion、Editor。此后未启动R2。

| 任务ID | Parent结果 | 步数 | episode墙钟秒 |
|---|---|---:|---:|
| train:0000 | 成功 | 8 | 214.37 |
| train:0001 | 成功 | 4 | 34.30 |
| train:0002 | 成功 | 25 | 552.30 |
| train:0003 | 成功 | 5 | 96.23 |
| train:0004 | 成功 | 13 | 536.75 |
| train:0005 | 成功 | 39 | 281.71 |
| train:0006 | 成功 | 30 | 216.24 |
| train:0007 | 成功 | 12 | 57.78 |
| train:0008 | 成功 | 4 | 8.36 |
| train:0009 | 成功 | 16 | 57.54 |
| train:0010 | 成功 | 8 | 17.57 |
| train:0011 | 成功 | 7 | 29.25 |

### 原始Update、Fusion与Editor

分类生成2个冻结组。Diagnosis原始输出选择`revise`，提出4条Requirement、4个Watch，目标是减少搜索和灯具操作循环并保留原有成功行为。目标、全部原始引用和程序接收后的Plan分别保存在 `raw_outputs/diagnosis.json`、`outputs/diagnosis.json`、`initial_plan.json`；不能只依据摘要重建模型输出。

R1 Fusion真实调用v6，返回`ready`，`changes=[]`、`watch_changes=[]`、`open=[]`，即Keep；有效要求与Diagnosis一致。当前Memory为空，没有历史Effect引用，未发生D/S/C变换。Fusion的理由称当前证据支持原要求、没有显露需变换的冲突，并保留灯具操作顺序的未决替代方案。这些是模型判断，未被Candidate行为验证。不能将本次Keep作为“历史预条件化改善决策”的证据。

Editor完整返回`candidate`、Skill提案、13条实现映射，`issues=[]`、`watch=[]`。生产路径在原有 `normalize_editor → normalize_numbered_spans` 校验中停止，准确错误为：

```text
Citation differs by more than numbered-list formatting.
```

确定性逐项核对定位到第13条映射（`requirement:u4`）：摘录以`Recovery: if the move ...`开头，但Candidate提案实际在另一个Recovery段落的后句写的是`If the move ...`，没有该`Recovery: if`连续片段。因此不是仅列表编号或前导符差异；12条摘录为原文子串，13号不是。原响应HTTP 200、`finish_reason=stop`，严格JSON可解析；失败在Editor输出契约，**不是传输失败、输出截断、容量超限或合法但效果差的Candidate**。

没有改写摘录、修补Candidate、放宽验证器或追加请求。冻结的语义恢复预算为0，故在此保存全部证据并停止。原始提案与差异另作分析副本保存为 `analysis/UNVALIDATED_EDITOR_PROPOSAL.md` 和`.diff`，明确标记未验证；它们不是已经实现和执行的正式Candidate，不写入正式`candidate.json`或状态发布文件。准确映射核查见 `analysis/editor_excerpt_audit.json`。

### 跨轮继承、Replay与Memory

实际最后正式状态仍为 `formal_run/state0.json`：No Skill、Memory `[]`、round_index=0。R1没有 `state.json`，没有Candidate执行、Gate、Replay Findings、Memory delta或Effect发布；R2–R5没有开始。不能将本次缺少Candidate写成RETAIN／no_change，也不能把未完成的Editor输出当成正确修改。

因此，本次真实运行**没有观测到Skill／Memory跨轮继承、历史Effect影响D/S/C、Candidate行为变化或Memory认识修订**。这些路径仅在离线合成测试中通过，不能混用为正式实验结果。没有可评价的本次Memory行为归因，更不存在可以据此声称已修正或已验证的错误归因。

## Token、耗时与稳定性

实际12条Parent episode、171次Actor逻辑请求、4次语义请求，合计175次逻辑请求和175次HTTP尝试。传输失败0、传输重试0、语义／episode恢复0；Editor契约失败1次，其已发生的用量完整计入。全部175次均有原始响应和已报告usage，无缺失轨迹、无未知usage条目。

| 语义阶段 | 输入Token | 输出Token | 其中推理Token | HTTP耗时秒 | 程序结果 |
|---|---:|---:|---:|---:|---|
| classification | 16,409 | 12,788 | 11,639 | 69.64 | 契约通过 |
| diagnosis | 22,029 | 14,179 | 13,011 | 69.94 | 契约通过 |
| fusion | 24,678 | 8,272 | 7,972 | 43.60 | 契约通过 |
| main_editor | 24,073 | 5,710 | 4,444 | 24.69 | Editor摘录契约失败 |

累计输入 **162,137 Token**、输出 **417,127 Token**、总计 **579,264 Token**，其中 **397,673为推理Token**（输出的子集，不重复计费或重复加总）。缓存命中1,024输入Token、未命中161,113。Actor单独输入74,948、输出376,178；四次语义调用输入87,189、输出40,949。

Editor失败调用本身消耗输入24,073、输出5,710，其中推理4,444；HTTP耗时24.69秒。没有恢复成本。上述HTTP耗时不包含所有阶段间文件核验开销；并发episode时长不能简单相加作为墙钟时间。没有查询账户账单，金额记为未知，不能当作免费。详见 `analysis/accounting_and_results.json`，按原生usage保留缓存及推理口径。

四次P1完整消息均通过400000字符限制及上下文保守上界检查，精确测量保存在 `rounds/r1/capacity/*.json`。本次没有运行到历史Memory增长后的输入规模，不能声称已验证五轮最大容量。

## 档案有效性与可复现性

事后运行既有 `continual_runner verify`：`artifact_valid=true`、`campaign_complete=false`、`published_rounds=0`、`incomplete_rounds=1`、`semantic_call_records=4`。这表示保存的档案、冻结快照、调用及确定性状态关系有效，**不表示失败Editor提案通过输出契约**，也不证明模型语义或方法因果收益。

- 配置和唯一任务分配：`experiments/methods/v22/23_alfworld57_five_round/config/{plan,task_manifest,prior_contact_inventory}.json`。
- 固定恢复和预算协议：同目录上级 `PROTOCOL.md`；无Pilot、无新评审Agent、无独立Test参与。
- 源码、Prompt、模型及Schema：`formal_run/runtime_freeze.json` 与`source_snapshot/`、`config_snapshot/`。
- 成功Parent及原始HTTP：`rounds/r1/parent_runs/`。
- 阶段原始数据：`rounds/r1/{inputs,messages,calls,raw_outputs,outputs}/`；raw response body在各call的响应目录中，未改写。
- 分类、Plan、有效Update：`grouping.json`、`initial_plan.json`、`effective_plan.json`；失败前检查点：`effective_freeze.json`及保存的Editor输入／调用／原始响应。技术停止记录：根`report.json`及R1`report.json`。
- 离线结果：`offline/{v22_final,adapter,references,five_round}.log`；事后核验：`verification.json`；统计与摘录核查：`analysis/`。

正式失败成本和全部已成功阶段已保留，没有重建目录刷新调用预算，没有重跑成功阶段，没有因本次摘录错误修改算法或Prompt。旧实验目录均保留。

## 有效现象、退化边界及后续检验

真实观测支持：当前No Skill Actor在本轮12项全部成功；v6/P1/引用路径真实到达Editor，首轮模型Fusion能够合法Keep；完整JSON仍可能因非逐字实现摘录而无法进入Replay。没有Candidate行为数据，不能评价Skill提升或退化，也不能证明五轮持续进化、Memory学习有效或预条件化优于无Memory。

必须区分当前证据直接支持的执行事实、模型的行为解释、历史Effect对具体Fusion更新的作用，以及不能独立归因的联合修改效果。字段／引用契约通过不能写成语义解释完全正确。单条连续实验不能证明历史预条件化优于无Memory方案。

独立Test应使用未参与本次优化的数据；后续消融应在可比预算、任务顺序、初始状态和随机性控制下比较无Memory、历史Memory消费及D/S/C处理，并检查行为触发机会、保留约束、错误归因与后续修订。Selection已进入开发池，不能再作为独立模型选择或泛化结果。
