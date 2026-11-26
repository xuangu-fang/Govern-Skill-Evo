# v28.2：SearchQA Update 级选择性 Skill 自进化设计

设计日期：2026-11-03；实现日期：2026-11-04（Asia/Shanghai）。第 4—5 步已接入独立 v28.2 运行器，交付配置、入口与离线验收；**正式训练和正式 Test 未启动**。实现映射、复现命令和验收边界见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。2026-11-04 完成 Diagnosis / Preconditioner 的 Prompt v2 修订，运行器直接加载本目录当前文本；修订内容、旧文本快照与本轮验收见 [Prompt v2 记录](revisions/prompt_v2/README.md)。

## 1. 设计目标与方法来源

初始实现在 SearchQA v28.1 的 benchmark 实现上迁入 v29.2 的完整新机制，并采用当时 v29.3 的提示词优化和 Editor 输出预算提升。当前 Prompt v2 根据已确认的 SearchQA 设计讨论独立修订 Diagnosis / Preconditioner，不把后续 v29.3 文本作为规范。希望通过可分别决定去留的 Update、明确的修改映射和事件归因，减少整包接受时无收益或有副作用的修改一同进入 Skill；效果属于待验证假设。

| 来源 | 采用内容 | 本地依据 |
|---|---|---|
| SearchQA v28.1 | 数据、Actor、评分、初始化、批次、预算基线、恢复边界；实体/关系、答案边界、参考形式的区别 | [边界说明](../v28_1/README.md)、[实际配置](../../../experiments/configs/v28_1_searchqa_train600_batch30_20261103.json) |
| 初始机制来源：DocVQA v29.2 | 无 Checks、全文调整动作、Update→patch、翻转事件 Replay、选择性 Gate、追加式 Memory、无损共享和引用解析修复 | [当前配置](../../../experiments/configs/v29_2_docvqa_optimization160_references_v4.json)、[源码](../../../src/skill_evolution/v29_2/)、[引用修订说明](../v29_2/execution_reference_boundary.md) |
| 初始提示词来源：DocVQA v29.3 | 保留迁移依据、历史事件/归因/决定区分、适用条件和 Editor 32,768；原按预期成败/去留划分 Update 的标准已由 Prompt v2 撤销 | [说明](../v29_3/README.md)、[Diagnosis](../../../src/skill_evolution/v29_3/prompts/diagnosis.md)、[Preconditioner](../../../src/skill_evolution/v29_3/prompts/preconditioner.md) |

机制来源为初始接线时的 `references_v4`。Prompt v2 从保存的 v28.2 v1 文本原位修订，保留 SearchQA 适配；不根据 Test 题正文、参考答案或逐题结果设计新提示词。

## 2. 相对 v28.1 的方法变化

| 部分 | v28.1 | v28.2 |
|---|---|---|
| Grouping | 组织全批 Parent 的决策问题 | 保留职责与输出，增加新执行共享视图和引用解析 |
| Diagnosis | `goal/updates/checks` | `goal/updates`；所有行为条件进入 Update text；按有证据支持的共同决策问题与修正方向组织，保留完整配合 |
| Preconditioner | `focus/change/to` 与 Update diff、Checks | `target/action/text/reason`；KEEP、完整文本 REPLACE、WITHDRAW；不增加或拆并 ID |
| Editor | 一个整包 patch | 每条 Effective Update 一个 patch；共同定位原始 Parent；联合形成 Candidate、可按 ID 重组 |
| Replay | 全批比较、历史 Knowledge 新增或修订 | 只分析 EM 翻转任务，每题一条事件 Knowledge，关联一个 Update 或 null，不读取/改写历史 Memory |
| Gate | Candidate EM 成功数严格增加才整包 ACCEPT | 根据明确关联的当前翻转事件逐 Update 计算 G/L，只选择 Retain patches |
| Memory | 可替换历史条目 | 按轮追加 Effective Updates、Gate 决定、事件 Knowledge，历史不重写 |
| 发布 | Parent 或完整 Candidate | 可发布 Parent、Candidate 或新的 Selected Skill 组合；保留真实执行来源 |

Stage 顺序：

```text
Parent batch → Grouping → Diagnosis → Preconditioner → Editor
  → Candidate batch → verified pairs → Replay → Gate
  → append Memory + publish Selected Skill → next round
```

Replay 先于 Gate，因为 Gate 使用 Replay 的 Update 关联。没有逐 Update 的额外 Actor 执行，没有重组后的额外训练验证，没有补答、Verifier/Repair 或额外模型审查阶段。各种短路分支见 [合同](CONTRACTS.md)。

## 3. 当前 Prompt 设计

1. **Update 组织**：按当前证据支持的决策问题及修正方向组织。同一修正的动作、条件、例外、优先级和必要依赖保持完整；任务或 Group 不决定边界，相同错误标签不自动合并不同修正。不按预期成功/失败、保留/撤回拆分，不固定数量。
2. **有效决策增量**：评估 Parent 是否缺失、误导、冲突或难以落实；执行错误本身不证明指导有缺陷，遵循情况可以未知。不为提案虚构缺口；可修改、删除或协调原指导，没有合理修正时允许 no_change。
3. **成功与反例**：用于识别哪些问题/context 差异影响动作、范围或优先级，而不只列出例外。不强制正反配对案例或每种情形的成功验证；单案例可以支持合理试验。把“必须”改为“优先”不能消除无依据的适用范围。
4. **附带改变**：名称、编码、单位、答案范围等额外变化需要相关依据，或是实施修正、解决冲突、保持有效行为所必需。在固定协议内尊重问题的具体输出要求；主方向合理不自动支持整条 KEEP，REPLACE 保留合理方向和必要配合。
5. **证据解释**：多种参考形式被接受不表示一种更优；明确支持的实际成功保持只提供有限的任务级证据，不计作新增改善。缺少 Knowledge/关联不证明保持成功；当前未执行的提案不能声称已改善或保持表现。

保留既有历史事件、Update 关联与 Gate 决策区分，以及 Actor 可见适用条件审查。Editor 预算仍为 32,768，Diagnosis / Preconditioner 各 65,536；本次未改变其他模块、接口或预算。

## 4. SearchQA 固定边界

| 项目 | v28.2 设计值 |
|---|---|
| 数据与顺序 | 沿用 v28.1：原 Train 400 + Validation 200 合成优化池 600；实际配置中的 20×30 批次，单遍、不打乱、不增删；合并后有效 split 仍为 train |
| 初始化 | 原 [initial Skill](../../../experiments/configs/v28_searchqa_initial_skill.md)，104 字符（含换行）；空 Memory `{"rounds":[]}`；不继承任何旧最终 Skill、Memory 或执行缓存，不运行 Stage0 |
| Actor | 同一 `deepseek-flash`、thinking enabled、reasoning_effort medium、temperature 1.0；同一完整 question/context、基础协议、单轮无工具 |
| 评分 | 原答案提取和 SearchQA 归一化；EM、counter-based token F1；不新增别名、参考答案或评分反馈 |
| 选择信号 | 以 EM 的 0→1 / 1→0 替代 DocVQA hard 翻转；F1 不影响事件资格、G/L 或决定 |
| 并发 | Train / Test = 15 / 15 |
| 最终评估设计 | 同一 1,400 题和顺序，仅评估完成 20 轮后最终 Selected Skill；不用 Test 选择 checkpoint |
| 输入保护 | 4,000,000 字符、6,000,000 UTF-8 字节；无 `context_window_tokens`；不截断证据、不设 Skill 字符数上限 |
| 运行范围 | 本次不启动训练/Test、不创建监督器或自动化；未来启动时再落实运行控制，旧实验的自动恢复授权不作为本实验已启用策略 |

评分语义以 [本地评分实现](../../../src/skill_evolution/v28/benchmarks/searchqa/scoring.py) 和 [原生归一化实现](../../../external/SkillAdam/skilladam/benchmarks/searchqa/evaluation.py) 为准。EM=1 推出 F1=1，反向不成立；仅词序不同也可能 F1=1、EM=0。冠词和标点按原评分器归一化，不能照搬 DocVQA 中“删除冠词导致得分翻转”的示例。完整 context 是直接可见文本；Actor 是否实际使用某段内容和内部推理过程仍不可观测。

| 调用 | max_tokens | 请求超时 |
|---|---:|---:|
| Actor | 32,768 | 300 秒 |
| Grouping | 32,768 | 600 秒 |
| Diagnosis | 65,536 | 600 秒 |
| Preconditioner | 65,536 | 600 秒 |
| Editor | **32,768** | 600 秒 |
| Replay | 65,536 | 600 秒 |

五个方法模块沿用 v28.1 的 DeepSeek endpoint、模型、thinking、reasoning_effort、temperature。Actor 连接超时 10 秒，SDK 重试为 0；技术错误与 length 共用六次总尝试，等待 1×尝试序号秒。方法阶段最多六次总尝试，等待 2×尝试序号秒，沿用已有技术错误分类和解析反馈流程。正常 stop 的错误答案不重采样；合法语义停止不重新抽样；恢复不重置尝试额度；耗尽不补零分。

预算来源以 batch30 的实际 v28.1 配置为准，不使用 v28 源模板中的 49,152 Actor 默认值，也不把 DocVQA 的 32,768 Diagnosis/Preconditioner 预算覆盖到 SearchQA。

## 5. 版本与恢复边界

方法名 `v28_2_campaign_v1`；Diagnosis / Preconditioner 提示词分别为 `v28_2_searchqa_diagnosis_v2` / `v28_2_searchqa_preconditioner_v2`，其余三个 Prompt 仍为 `_v1`；stage、输入视图及输出合同版本不变。完整标识和字段见 [CONTRACTS.md](CONTRACTS.md)，由独立 v28.2 运行器识别。

保留 SearchQA Actor/scorer profile，但旧 `v28_searchqa_em_strict_increase_v1` 不再作为 v28.2 方法 Gate。v28.2 Actor 归档使用新 Gate provenance，旧整包 Gate 的适配入口显式拒绝调用；原 SearchQA Actor/scorer 不变。

v28.2 采用独立目录、配置与恢复入口。恢复校验实际配置值、Prompt 原文、方法/合同版本、输入、任务顺序、执行 Skills、响应对应关系及已消费额度，不以源码/配置/数据 SHA256 或哈希清单作为门槛。Memory 持久化也不直接照搬 v29.2 的摘要型 HEAD；使用顺序提交标识、原文/结构比较、来源重算及原子发布，详见合同。旧版本文件和历史归档不改写。Prompt v1 配置与归档不能在当前 v2 绑定下继续执行；不自动迁移或重标记旧响应。

## 6. 提示词与审阅

五份文件均为完整英文 system Prompt，含准确的原 Actor 基础协议和 32,768 Actor 运行说明；没有待展开模板或依赖其他提示词才能理解的占位内容。

- [Grouping](prompts/grouping.md)
- [Diagnosis](prompts/diagnosis.md)
- [Preconditioner](prompts/preconditioner.md)
- [Editor](prompts/editor.md)
- [Replay](prompts/replay.md)

[PROMPT_REVIEW.md](PROMPT_REVIEW.md) 记录当前五组修订与保留边界；[source_map.json](source_map.json) 记录当前版本和历史来源；[design_validation.json](design_validation.json) 保留初始设计静态检查。根目录 `diffs/` 对应初始 v1 导入差异；[本轮差异](revisions/prompt_v2/diffs/) 对应 v1 → v2，不覆盖历史来源记录。

## 7. 解释边界和实现验收

Replay 的关联不是独立因果实验；Gate 可以选择收益不确定的行为关联，也可能因无法归因而 Defer 有效修改。新方法有意不把 EM 不变的回答变化写成 Replay 事件。不能把没有事件/关联解释成已证实无收益。

所有 Updates 联合执行一次，重组后的 Selected Skill 可能从未执行。patch 可定位、可组合只证明文本结构可用，不证明行为独立或必要依赖已由程序识别。必要依赖应在 Diagnosis 的完整 Update 中表达，Preconditioner/Editor 保持其语义；程序不增加依赖求解器或自动修复。重组结构非法时停止并保留记录，不退回旧整包 Gate、不静默丢弃问题 patch。

此前 v28.1 文档已说明该 Test 集曾用于设计分析。未来同集比较属于探索性复评；本设计仍禁止把 Test 内容送入优化链路。新版本同时改变机制、提示词和 Editor 预算，结果只能先解释为整体方案比较。

第 4—5 步离线验收覆盖：无 Checks 合同；每条动作及撤回依赖；patch 组合/冲突/子集；EM 翻转/无翻转/F1-only/null 关联；G/L 全分支；追加历史和无事件轮；原子发布与恢复；跨版本拒绝；完整 SearchQA 输入、原评分和最终 Test。可执行验收及日志见 [IMPLEMENTATION.md](IMPLEMENTATION.md)；原 design_validation.json 仅记录设计阶段静态检查。离线测试不证明模型判断或测试成绩改善。
