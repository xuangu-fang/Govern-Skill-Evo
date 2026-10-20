# V23.2：问题集中性与最小能力说明验证

日期：2026-10-19。**集中性成立，但本次不采纳为第一项改进的优先候选，问题继续标记为未解决。** R03 用尽原有三次技术尝试后停止，没有合法 Effective Plan；R06 返回合法结果，仍有中断后的搜索进度恢复问题，并新增过窄的回源条件。已完成两次逻辑调用并停止，没有后续 Prompt 补丁或语义重采样。

## 1. 先核查，再决定调用

调用前只读 13 份历史 Plan（4 份 Original、9 份 Effective），覆盖 V23 R03/R05/R06、第一轮 V23.2 三组固定材料及 R05 串联、第二轮 R03/R06。完整分类在[集中性核查](CONCENTRATION.md)，原文及来源在 [audit_corpus.json](../results/audit_corpus.json)。分类与报告已纳入调用前的 `implementation.json`，没有根据新输出调整计数。

| 去重的信息需求 | 代表性实际文本 | 判定 |
|---|---|---|
| H1 全执行的位置访问／检查集合 | R03 u1 `continue searching uninspected receptacles`；第一轮 R03 u3 `revisit a location only after exhausting the listed candidate receptacles` | 两步窗口与动作候选不提供完整访问集合；单类／全候选穷尽与未检查位置合并计数 |
| H2 累计类别采样／完成状态 | R06 `genuinely uninspected family`；第二轮 R03 `If the cabinets, fridge, and countertops have been checked` | 当前菜单列出类别，但不列出累计完成情况 |
| H3 跨类别回返时的剩余实例游标 | 两轮 R06 `return to ... remaining receptacles ... only after ... families have been sampled` | 当前类别／编号不能自动恢复离开的其他类别各自进度 |
| H4 当前状态到历史的错误推断 | 第二轮 R03 `because a closed receptacle has not yet been searched` | 关闭不等于未搜索；同轮 C34 有 `close cabinet 2`，已搜索容器可再关闭 |

共 **4 类已确认信息可执行性缺陷，4 类与历史进度有关（100%）**；H1/H2 在多个轮次及串联复现，9 份最终 Plan 中 8 份含明确 H 类问题。同一要求跨版本重复不增加缺陷数。另保留 5 组其他语义问题（过早停止、无依据阈值、操作条件不明、过强动作限制、策略顺序依据／冲突）及 2 项范围不确定问题，不统归历史进度。4/4 是这批材料的去重类别比例，不是所有语义错误比例或独立样本发生率。即便合并 H1–H3，仍为 2/2；达到预设约 2/3 且跨材料复现的门槛。

## 2. 唯一模板变量与继承关系

基准是正式 V23 `S1/contract.json` 保存的模板，不是 Git HEAD。Diagnosis 和 Preconditioner 原文件分别逐字核对一致；本次通过既有 V23.2 局部入口显式选择原 V23 模板，只覆盖独立配置中的共享能力说明。**未叠加第一、第二轮 V23.2 的可执行性检查规则；本次也未调用 Diagnosis。** 原始模板哈希与核对结果见 [prompt_checks.json](../results/prompt_checks.json)。

原句：

> It cannot access the full execution history, write persistent notes, or inspect hidden evaluator state.

替换为：

> The Actor has no persistent record of search progress and cannot access the full execution history, write persistent notes, or inspect hidden evaluator state. Current action candidates and object states do not by themselves reveal which locations or categories were previously visited or exhausted. Such progress can only be used when supported by currently available information.

保留原来的完整历史／持久笔记／隐藏状态限制，避免澄清时意外削弱原要求。前一句“当前观察、动作候选、最近两组行动前观察／动作”以及全部 Actor 模板、步数信息均不变。没有具体搜索策略、示例、额外字段或新章节。[精确 Diff](../config/context.diff)仅有这处替换。

[适配差异](../config/adapter.diff)只为既有 `messages_for`、`run_stage`、`load_attempt` 增加可选 `context_path` 并传递；默认仍读取原配置。输入装配、JSON 契约、Effective Plan 编译、技术错误判定均复用 V23。实验入口复用前两轮固定材料核验与归档工具，不复制框架，不改 Actor 或 Orchestrator。

## 3. 四版本最终文本比较

Actor 能力依据是原 `execution_context.md` 和实际 `actor_prompt.render_messages`：当前观察、当前动作候选、`history[-2:]` 两组行动前记录，模板中的当前步数；没有完整访问日志。动作菜单中的 `go to` 或容器当前开闭状态本身不是访问标记。下表不依据 `unvisited` 等关键词判错；固定顺序能从当前可见位置恢复下一步时，可以执行。

完整 Original Plan、各版本 Adjustment/reason 和 Effective Plan 均在[四版本全文](OUTPUTS.md)及 [comparison.json](../results/comparison.json)。本次失败响应全部单列，未人工修改或编译成正式 Plan。

| 更新 | 原始 V23 最终文本 | 第一轮 V23.2 | 第二轮 V23.2 | 本次仅能力说明 |
|---|---|---|---|---|
| R03 u1 | Keep：`continue searching uninspected receptacles`，没有全局集合的恢复依据 | 相同 Keep | 相同 Keep | **无合法最终 Plan，无法判定消除**。001/003 原始响应均未调整 u1，003 reason 称 `u1 remains supported and executable`；这是未通过契约的草稿倾向，不能充作最终结果 |
| R03 u2 | 按当前 admissible 温度动作直接处理；无需全局搜索进度 | 加入 `move the target in only when required, then take it back`，备用流程依据不足 | Keep 原始先开门要求，存在冗余动作风险，但不是历史进度缺陷 | 无合法最终 Plan。003 草稿恢复按 admissible 动作直接处理，仅为草稿观察 |
| R03 u3 | `uninspected drawers`、`unvisited listed location` 仍需历史集合 | 增加全部候选穷尽后才准回访 | 删除该回访门槛，但新增类别完成条件及“关闭即未搜索”的错误推断 | 无合法最终 Plan。001 草稿仍有 `not-yet-inspected` 与 `already checked`；003 草稿改用当前／两次观察，不再要求累计类别完成，但不能据此宣布通过 |
| R06 u1 | 保留直接温度动作、精确目标等局部要求 | 保留 | 保留 | **逐字 Keep**，没有删掉这项可执行策略 |
| R06 u2 | 类内升序后切换 `genuinely uninspected family`，全局类别状态未落实 | 最多两个空位置后换类，其他类采样后回到剩余实例，最终全部检查一次 | `after a small run` 后换类，仍要求其他类采样完成后恢复剩余实例 | 改为固定轮转，消除两处旧切换措辞；但要求 `resume the same fixed sweep`，放置后的游标恢复仍未落实；并将回源限定为 `only if the last observation still shows another exact instance there` |

R03 无最终 Plan 属于技术停点，不记作语义成功，也不能把这个停点本身证明为能力澄清无效。001、003 的 `P5/P10`、`P8/P10` 是并列当前执行引用，被现有历史引用正则当成带斜线历史引用而拒绝；不是已证实的虚构历史。002 是无效 JSON。没有为获得可比结果修复解析器或手工选取草稿。

## 4. R06：真正改变的内容与仍未解决的问题

**局部改善。** 原来的“最多两个”／“一小段”后换到未访问类别，以及“所有其他类已采样才返回”不再出现。新文要求 `interleave families in repeated rounds`，并给出类别优先次序。这使一个**连续、无中断、顺序完整且位置可观察**的扫描前缀有机会从当前类别和编号推算下一项；不能因存在轮转或 `unchecked` 一词就断言整个策略不可执行。当前开闭状态足以支持是否执行开门，不应误算成历史能力。

**没有证明完整流程可执行。** u2 同时要求 `check the first unchecked member of each family ... then the second unchecked member of each`、`all plausible listed receptacles have been checked once`，并在取物和放置后要求 `otherwise resume the same fixed sweep for the next instance`。离开扫描去取物／移动／放置之后，当前位置是目的地；两步记录不能一般性保留原扫描的轮次、类别游标和未检查集合。文本既没有界定如何从目的地恢复原扫描游标，也没有说明回源分支之后如何恢复。“固定顺序”可以解决连续下一步，却不能自动解决中断续行；`memory-independent` 只是模型自述。全局穷尽条件在完整可恢复的固定遍历中可能成立，本次完整多实例流程没有建立该前提，因此不能判为已消除历史进度依赖。

**新增回源限制过窄，并有真实反证。** `after placing one, return to the most recent source only if the last observation still shows another exact instance there` 把允许回源绑定到“最后一次观察仍显示源处另一实例”。保存的 M9 原始来源 `S1_R04/Q9` 中，第 5 步放置后的观察是 `You move the saltshaker 2 to the sidetable 1.`，不显示 cabinet 中另一实例；第 6 步仍成功返回 cabinet 1，第 7 步取得另一个 saltshaker。相同模式见 `S1_R04/Q6:30–32`。即便将“last observation”宽解成最近两步记录，在 Q9 第 6 步前可见的 Q9:4、Q9:5 行动前观察也没有源处剩余物体清单。新条件会排除已有成功回源路径，却把 Actor 推向需要恢复全局游标的备用流程。这里核查的是文本限制与真实可见输入的冲突，不假称已实测新 Skill 退化。[证据摘录](../results/return_source_evidence.json)保留实际 before/action/after。

**其他语义边界。** 固定轮转与详细类别优先次序是比原更新更复杂的替代策略。P1/P2/P5 在开放表面找到目标可支持优先考虑表面，但不足以证明整套固定次序和所有剩余电器后置都适用。`all plausible ... checked once` 的终止条件与保留预算要求在旧版已存在，不误报为本次新加过早停止；本次也没有新设数值预算阈值。多实例精确计数目标有原 Goal 和 M9 依据，本身不能自动判成不可观察。温度动作 u1、精确类别和完成数量目标均得到保留。未发现新“关闭即未访问”的推断。

## 5. 离线验证与文件保护

- 禁用网络连接和环境子进程，运行 V23、V23.2、ALFWorld Adapter 及分组表示回归：**600 passed，19 subtests passed，18.53 秒**。[完整输出](offline_tests.txt)。
- 新增最小测试验证两种原始模板逐字等于正式契约、系统消息只有一次能力句替换、user 消息不变、显式上下文档案可重读及 Keep 编译不变；省略对应上下文应严格拒绝。其余既有测试覆盖 Diagnosis／Adjustments／Effective Plan、Editor 输入交接和 Memory 接口。
- 调用后核对所有 4 次请求的完整保存输入、user 消息和模型配置与正式材料一致；system 消息精确等于原消息的一次字符串替换。所有技术重试消息相同。R06 从原响应重解析并重新确定性编译，与归档最终 Plan 一致；R03 不存在伪造的 `effective_plan.json`。[核验结果](../results/verification.json)。
- **10,307 个保护文件逐字节比较全部不变**，覆盖 V23 源码／正式训练及 Test／配置、两轮旧 V23.2 实验配置及产物、旧 V23.2 模板。[保护结果](../results/protection.json)。本次分类／模板／适配实现与调用前冻结快照相等。

## 6. 调用、技术失败和成本

两次逻辑调用，共 4 次 HTTP 请求（R03 三次、R06 一次），2 次技术重试，3 个无效响应；无语义重采样。模型 `deepseek-flash`，temperature=1，Thinking enabled、reasoning_effort=medium、max_tokens=16384、timeout=300，均沿用旧配置。容量 R03 784,827 字符／784,845 字节，R06 1,493,677／1,493,691，均未超限；没有压缩输入。

| 请求 | 状态／停点 | Prompt tokens | Completion tokens | Total tokens | 耗时 |
|---|---|---:|---:|---:|---:|
| R03 001 | 历史引用契约失败：`P5/P10` | 230,379 | 7,374 | 237,753 | 38.50 s |
| R03 002 | JSON 解析失败，line 17 column 5 | 230,379 | 6,554 | 236,933 | 32.97 s |
| R03 003 | 历史引用契约失败：`P8/P10`；达到技术上限 | 230,379 | 16,300 | 246,679 | 84.26 s |
| R06 001 | 合法 ready；u2 调整，u1 Keep | 432,906 | 12,733 | 445,639 | 74.57 s |
| 合计 | 2 逻辑／4 HTTP | **1,124,043** | **42,961** | **1,167,004** | **230.30 s 请求计时** |

总实验耗时 **239.17 秒**（含重试等待、核验及归档）；reasoning tokens **38,375**，属于 completion 子集，不重复相加；未知 usage=0。缓存命中 prompt tokens=462,592，是 prompt 子集。所有响应 finish_reason 均为 stop，R03 第三次虽接近输出上限，但没有发生截断。实际元数据见 [attempts.json](../results/attempts.json)、[summary.json](../results/summary.json)，原始 HTTP／模型内容在独立 [artifacts](../../../../../artifacts/methods/v23_2/v23_2_capability_001/) 中，失败草稿全文也收入 OUTPUTS。

## 7. 候选决策与停止

**不确定为优先候选，不叠加此前失败 Prompt。** 历史材料支持问题主要集中于搜索进度，但当前结果没有满足“两组均明确改善且无明显新语义问题”：R03 技术停点使合法最终输出缺失；R06 虽改善连续扫描描述，完整进度恢复和回源限制仍未通过。

第一项问题保持未解决，本次方案作为独立研究证据保存。前两轮失败模板与输出继续保留，不能回退成“已验证的最终方案”。没有改 Memory、Replay、Editor、Gate、Actor 或 Orchestrator；没有运行 Candidate、环境任务或正式六轮实验。两组调用后不再优化 Prompt，也不进入历史反例约束阶段。此结论只针对单次固定材料的更新语义及技术可用性，不证明澄清能力边界没有潜在作用，不是严格因果检验，更不代表 ALFWorld 成功率变化。
