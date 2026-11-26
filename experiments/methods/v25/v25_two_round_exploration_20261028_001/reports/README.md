# V25 探索实验：第一轮完整闭环分析

本报告分析已完成的第一轮，不将第二轮中断冒充为两轮完成。第一轮在 15 个开发任务上由 Parent 10/15 提高到 Candidate 14/15，Gate 接受 Candidate，并完成 Replay → Verifier/Repair → Memory 发布。第二轮已完成 4 个 Parent 任务，随后因 API 账户预算耗尽而中断；用户要求暂不继续第二轮，改为分析第一轮。本目录不会自动恢复运行。

**结论：本轮验证了闭环可以完成，也观察到开发批次内的评分收益；但评分收益、任务要求符合程度、执行效率和历史经验可靠性必须分开判断。** 最值得关注的是 Preconditioner 将“评分允许数值”推进为“即使公式保留失败也可退回数值”的决策；其次是 workflow 更新未减少无效探查。Replay 对主要程序差异的记录较好，Verifier/Repair 修正了一处明确的计数错误，但没有补足公式要求的经验边界。尚未得到历史 Memory 影响下一轮 Preconditioner 的直接证据。

## 1. 冻结条件与实际范围

- Diagnosis v5、Preconditioner v7、Replay Prompt v4、Replay 输入视图 v4，其他模块及方法源码保持冻结。
- 模型 deepseek-v4.1-flash，原内网接口；temperature=1.0、reasoning_effort=medium、thinking enabled、stream=false、请求超时 300 秒。
- Actor 最大输出 49,152 tokens，最多 30 次程序执行，每个程序槽最多 6 次请求，4 workers，程序超时 600 秒，无累计任务时间上限。
- 方法模块基础输出预算 16,384；Diagnosis 32,768、Preconditioner 49,152、Replay 49,152、Verifier 49,152、Repair 32,768。
- 初始 Skill 为原始 224 词版本，Memory 为空。没有引入旧 R05/R06 的 Memory，没有使用最终 Test 进行执行、评分或方法选择。
- 使用原始第一批 15 个 Train 开发任务；第二轮使用原始第二批，但尚未完成。完整配置保留原 400 题元数据以满足原校验器，运行器仅调度前两轮，不运行剩余六轮或最终 Test。
- 这里的 R01/R02 是本次新实验轮次，不是旧实验的 R05/R06。不能将本轮收益作为旧 R05/R06 的直接复现证据。

冻结检查比较原先合同、源码/Prompt 摘要以及本次配置文件 SHA。技术恢复仅变动未完成 Actor 请求的可重试状态，所有原始请求、消耗和恢复前状态均归档，未修改 Prompt 或模型参数。
[冻结协议](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/protocol.json) · [配置](../config/config.json) · [哈希清单](../config/manifest.json) · [离线校验](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/offline_validation.json)

## 2. 第一轮成绩与执行代价

| 指标 | Parent | Candidate |
|---|---:|---:|
| 全对任务 | 10/15（66.67%） | 14/15（93.33%） |
| 全部评分单元格 | 756/825（91.64%） | 822/825（99.64%） |
| 各任务单元格通过率的均值 | 76.61% | 99.64% |
| 实际程序执行数 | 22 | 27 |
| Actor API 请求数 | 25 | 31 |
| Skill 词数（空白分词） | 224 | 843 |

本批新增全对 4 道，hard 和 per-cell 均无退步；不能据此推断历史任务保留或最终 Test 改善。Skill 增至约 3.76 倍，程序执行增加 5 次（22.7%），API 请求增加 6 次（24%）。程序编号包含格式失败时，不能把编号直接当执行次数。

| 任务 | 正确单元格 Parent → Candidate | 核心现象 |
|---|---:|---|
| train:46121 | 0/48 → 48/48 | 公式及缓存注入改为直接写计算值 |
| train:56274 | 0/4 → 4/4 | 按月份取数后直接写值 |
| train:57445 | 0/4 → 4/4 | 查找价格后直接写值 |
| train:51090 | 12/22 → 22/22 | AND 条件改集合匹配，同时改变 Q 列计算量及来源选择 |
| train:398-14 | 53/56 → 53/56 | E9、F5、F8 仍不匹配 |
| 其余 10 道 | 全对 → 全对 | 分数保留，部分执行次数增加 |

train:398-14 的相同评分及错格集合不能证明输出数值完全一致，也不能说明所有规则在该任务上均不起作用。
[逐题成绩与执行次数](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/task_results.csv) · [Gate 决策](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/campaign/rounds/R01/gate/result.json)

## 3. Original Plan → D/S/C → Candidate：哪些变化值得肯定，哪些有问题

| Update | Diagnosis 原意 | Preconditioner 实际动作 | 本轮证据及限制 |
|---|---|---|---|
| u1 答案可读性 | 不重算环境中要有缓存/数值；显式要求公式时保留公式 | D/S 调整，优先直写值；即使应保留公式，缓存验证失败时仍可直接写值；c1 同步弱化 | 3 道评分改善与该策略一致，但任务公式要求被削弱 |
| u2 数值来源 | 从 data_only 副本读取缓存；缺失缓存不应当成真实 0 | KEEP | 多题使用，但没有隔离效果；“缓存 None 就排除该源单元格”仍有适用边界 |
| u3 完整程序 | 同一次程序完成检查、变换及保存；限制 print/raise-only 探查 | KEEP | Candidate 探查成本反而增加，没有实现该行为目标 |
| u4 重新推导聚合 | 不盲用题目已指出有错的公式；同一字段多个候选值按备选条件理解 | KEEP，承认是假设 | train:51090 改善，但同时改变输出量与来源选择，不能单独归因于 AND→OR |

没有 C 方向的调整。四个 Update 涉及不同问题，**本轮没有证据表明“四条 Update”这个数量本身导致坏结果**。需要审查的是每条规则新增了哪些行为、边界是否合理、彼此是否冲突及执行复杂度；不应根据本轮结果机械限制每轮只能更新一条。

Diagnosis 的积极表现是：区分明确观察和 u4 待验证假设，允许多个独立更新，并在 train:398-14 的证据不能区分解释时没有强行制定修复规则。它仍有局部泛化风险：要求“每个答案格非 None”没有排除合法空白；将“聚合结果为 0”直接视为条件不可满足，也可能忽略合法零值、正负抵消及其他筛选条件。本批没有观察到这些条款导致评分退步，不能把风险写成已发生的因果事实。

Preconditioner 对 u1 的调整有现实依据：值评分环境下，缓存注入路径确实多次失败，直接写值更稳。但其推理将“评分没有惩罚”当成了弱化用户要求的依据。Diagnosis 原始 c1 会检查“显式要求的公式是否还在”，Preconditioner 改成“若留下了公式，它是否有可读结果”，从而漏掉“公式被删掉”的情况。这里关键事实原本已在输入中，不属于关键输入缺失；主要是更新决策的优先级及检查条件变化。

Editor 基本忠实落实了调整后的计划，不能将该冲突简单归因于 Editor 擅自扩展。843 词虽然明显增长，但并未直接造成分数下降；本轮能确认的是复杂度和执行效率问题没有随文字增多而自然解决。
[Diagnosis 完整计划](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/campaign/rounds/R01/diagnosis/attempts/001/diagnosis.json) · [Preconditioner 原始 D/S/C](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/campaign/rounds/R01/preconditioner/attempts/001/parsed.json) · [Candidate Skill](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/campaign/rounds/R01/editor/attempts/001/candidate.md)

## 4. 四道改善案例：收益来自哪里

### 4.1 三道公式任务：评分收益明确，不能等同完整满足要求

train:46121 明确要求在 2022 收入区写公式；Parent 的程序写公式并修改 XML 缓存，自己用 data_only 重读时仍输出 None，48 格全错。Candidate 直接写 `cell.value = val`，48 格全对。

train:56274 要求由 D7 财务月份驱动 D9:D12 的 Excel 公式；Candidate 根据当前月份取数并写入常量，4 格全对。train:57445 要求 Pricing 的 E 列公式引用 C/D 并匹配成本；Candidate 写 `cost_cell.value = matched_price`，4 格全对。

这些程序改善了当前已保存值的可读性和数值结果，但没有提供所要求的公式及其后续响应输入变化的能力。第一轮没有对未来修改输入后的重算行为进行测试。因此应表述为“值评分改善，公式交付要求未保留”，而非“任务被完整解决”。这是已观察到的行为与要求冲突，不是仅凭 Skill 文本猜测。

链条很清楚：Diagnosis 保留公式要求 → Preconditioner 弱化要求并允许数值 fallback → Editor 写入规则 → Candidate 在这三题直接写数值 → 评分提升。因为同一配对也有取数方式变化，而且没有固定 Actor 输出的消融实验，这一链条支持机制解释，但不支持把全部分数增益精确归因于单条规则。

### 4.2 train:51090：不能遗漏“算什么”的变化

Parent 解析已有 SUMIFS 的条件，并向 Q 写 `M-(N+O+P+Q+R)`；Candidate 则直接汇总对应 OV 类型的 Errors 数量，把每行 G:J 用户 ID 作为集合备选值，并利用题目给出的 699 检查用户列选择。结果从 12/22 提高到 22/22。

这既有 AND→OR，也有输出量从“差额”到“OV 汇总”的变化，以及数据列选择的变化。题目同时提到差额、OV 样例及公式，措辞本身存在解释空间；评分支持当前 OV 结果，不应进一步宣称某一种文字解释已被独立证明。Replay 本次确实记录了 wrong-quantity 与 joint intervention，是值得保留的改进。

### 4.3 workflow 更新没有落地为效率改善

| 任务 | Parent 执行数 | Candidate 执行数 | 成绩 |
|---|---:|---:|---|
| train:47766 | 7 | 8 | 全对保持 |
| train:48365 | 1 | 2 | 全对保持 |
| train:50916 | 1 | 2 | 全对保持 |
| train:51090 | 2 | 4 | 12/22 → 22/22 |

这四题解释了全部新增 5 次程序执行。train:47766 中 Parent 6 次、Candidate 7 次执行结束前没有保存工作簿。不能因最终提交成功就说“完整程序要求被遵守”或“探查减少”。也不能从一次对照就认定 u3 导致次数增加；能确认的是这条更新未达成其预设行为检查。

还有一个可见性区别：仅输出到 stdout 的统计不一定返回给 Actor；train:51090 的 Candidate 第 3 条响应只打印内容，收到的反馈仅为输出文件缺失；第 4 条响应把统计放入 Exception，反馈才包含这些内容。分析必须基于实际 feedback，不能把归档里可见的 stdout 都当作 Actor 已掌握的事实。

[train:46121 Candidate 实际程序](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/campaign/rounds/R01/candidate_runs/train_46121/attempts/001/code/001/program.py)

[train:56274 Candidate 实际程序](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/campaign/rounds/R01/candidate_runs/train_56274/attempts/001/code/002/program.py)

[train:57445 Candidate 实际程序](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/campaign/rounds/R01/candidate_runs/train_57445/attempts/001/code/001/program.py)

[train:51090 Candidate 实际程序](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/campaign/rounds/R01/candidate_runs/train_51090/attempts/001/code/005/program.py)

## 5. Replay → Verifier/Repair → 最终 Memory

本轮 Replay 产生 5 个 entry、8 条 Knowledge，最终发布为 M1–M5。Verifier 第一次引用未提供的 `Q11:1`，原校验反馈机制要求重试，第二次输出合法；它发现 1 处事实冲突，Repair 仅修正该条，另外 7 条保持不变。按冻结机制，Repair 后没有第二次语义审查。

| 最终 entry | 内容 | 本轮判断 |
|---|---|---|
| M1，2 条 | 直接写值的三题收益；公式加有效缓存也可能成功 | 程序/成绩比较有依据，保留多因素限制；遗漏任务明确要求公式的边界 |
| M2，2 条 | train:51090 的计算量变化、同字段用户集合匹配及联合干预 | 关键程序差异被捕获；不应把评分结果升级成所有任务语义均已证实 |
| M3，1 条 | workflow 未减少不保存程序，执行成本增加 | 原稿漏计一次程序；Verifier 找到，Repair 修正后发布 |
| M4，2 条 | 本批无评分退步；train:398-14 相同测量结果的边界 | 与评分一致；正确区分“结果指标相同”与“输出值相同” |
| M5，1 条 | data_only 读取策略未获得隔离验证 | 有保留态度；运行器 data_only 评分条件本身不能证明所有输入缓存都可靠或应跳过缺失缓存 |

**明确事实错误的处理链：** Replay 写 train:51090 只有 2 个不保存的程序；实际为 3 个（2 次 execution_error、1 次 output_file_error），第 4 次执行才提交。Verifier 根据已提供的执行历史及 outcome 指出冲突，Repair 改为 3 个。最终 Memory 没有保留这个计数错误，因此不能说它继续污染了下一轮。

**边界遗漏的处理链：** M1 正确记录直接值输出与分数改善，却未写出这三题的公式要求未满足；Verifier 判 SUPPORTED，Repair 不改，最终发布。它是“事实基本正确，但经验限定不足”的案例。SUPPORTED 表示当前审查认为陈述受证据支持，不等于规则已完全符合任务要求、经验可以无条件推广。

本轮未见需要把这些不同问题统一归为“模型能力弱”或“整个模块设计错误”的依据。对计数错误，审查链起了作用；对任务要求和评分目标的冲突，当前决策及经验表达没有充分保留边界。二者需要不同处理。

**历史传播限制：** 第二轮 `round_input.memory` 与第一轮正式发布的 Memory 完全一致，时间顺序和证据引用加载通过离线核验。但第二轮停在 Parent 执行阶段，Preconditioner 尚未运行；所以目前只能确认历史被传入下一轮状态，不能声称 M1 被引用、造成某个 D/S/C 调整或导致第二轮任务变化。第一轮 Preconditioner 的 Memory 为空，其 u1 决策不能归因于历史污染。
[原始 Replay](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/campaign/rounds/R01/replay/attempts/001/replay.json) · [有效 Verifier 输出](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/campaign/rounds/R01/verifier/attempts/002/verifier.json) · [审查策略及结果](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/campaign/rounds/R01/knowledge_review/result.json) · [Repair 后最终提案](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/campaign/rounds/R01/knowledge_review/candidate.json) · [正式 Memory](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/campaign/rounds/R01/memory/view.json) · [第二轮实际输入](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/campaign/rounds/R02/round_input.json)

## 6. 成本与技术中断

| 范围 | API 请求 | 已知 prompt tokens | 已知 completion tokens | 已知 total tokens |
|---|---:|---:|---:|---:|
| R01（完整） | 64：56 Actor + 8 方法模块 | 1,694,682 | 854,479 | 2,549,161 |
| R02（未完成，含恢复和诊断） | 16 Actor | 22,411 | 104,764 | 127,175 |
| 本目录合计 | 80 | 1,717,093 | 959,243 | 2,676,336 |

R01 usage 全部已保存。R02 的 8 个 HTTP 400 没有返回 usage，不能按零成本补齐；以上是已知 token 总量。reasoning tokens 已包含在 completion 中，不能再次相加。本次统计不包含之前的 R05/R06 独立发布实验。没有经核实的内网单价，不计算本次金额。

R01 Actor 合计 928,017 tokens；方法模块合计 1,621,144 tokens。模块分解：

| 模块 | 请求数 | total tokens |
|---|---:|---:|

| grouping | 1 | 188,990 |

| diagnosis | 1 | 209,287 |

| preconditioner | 1 | 197,622 |

| editor | 1 | 19,992 |

| replay | 1 | 317,328 |

| verifier | 2 | 530,182 |

| repair | 1 | 157,743 |


第二轮首次 3 个请求报 HTTP 400；用户授权后重新开放这 3 个尚未完成请求，保留全部请求记录和预算，重启又有 4 个请求报 400。随后对 train:165-23 做了 1 次完全相同参数的诊断请求，仍计入该任务原有 6 次预算，拿到错误正文 `budget_exceeded`：账户累计费用约 1000.224，预算 1000，额度包余额 0。该金额是账户累计值，币种/计费口径未确认，不能视为本实验花费。

原 Actor transport 只存非 2xx 状态码，不保存响应正文，导致最初不能判断 400 原因；本次没有改生产 transport，只由隔离诊断脚本保存了一次错误正文。技术观测能力不足与模型学习质量是两个不同问题。

当前 R02 已完成的 4 题（46646、105-24、414-20、40892）均全对；4 题技术中断，7 题未开始。未完成任务不计为评分失败。用户已要求暂不运行第二轮。恢复记录、原状态与全部 API 消耗都保留，不能通过删除请求或清空预算重新开始。
[API 成本明细](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/api_costs.csv) · [首次恢复记录](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/recovery_001/authorization.json) · [同参数诊断记录](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/recovery_002_diagnostic/authorization.json)

## 7. 当前优先级与尚不能下的结论

1. **优先审查评分目标与任务要求的边界。** 直接写值在允许数值交付的任务上有明确价值，不需要禁止这种泛化；但“题目要求公式仍可用值替代”的更新应单独审查。证据不是不够，主要是 Preconditioner 如何使用“评分通过”的事实，以及检查条件被怎样弱化。当前不改 Prompt。
2. **把 workflow 的行为结果与总分分开看。** u3 的检查已有明确负面结果：探查成本没下降。后续若优化，应先分析具体程序为何仍探查、可见反馈是否足以支持一次完成，而不是继续叠加“必须完整”的同义措辞。
3. **保留 Replay 的有效部分，针对遗漏补足限定。** 这轮能记录 wrong-quantity、联合干预、同分不等于同输出，Verifier/Repair 也能修复计数错误，不支持继续整体推翻 Prompt。应重点检查评分收益经验是否遗漏任务要求、非计分目标与适用条件。
4. **避免把单轮结果升级为历史预条件化有效。** 目前第一轮无历史，第二轮尚无 D/S/C 或 Candidate；有无历史 Memory 的消融仍没有直接结果。未来应保持同一 Original Plan 与当前证据，仅改变 Memory，分别检查更新变化及任务表现。

本轮已支持开展后续受控研究的工程基础：完成了一次原生闭环，Gate、Memory 发布、下轮状态传递和归档可重载。但连续两轮衔接尚未完整验证，正式长程训练的持续收益与退步控制也未验证。无需以“所有自然语言完全无误”为恢复实验的条件；同时也不能用 14/15 的单批成绩宣称方法已稳定有效。

## 8. 复核与复现

下列命令只读取归档、验证合同并导出报告，不调用模型：

```sh
cd /Users/didi/Desktop/Govern-Skill-Evo
/tmp/govern-skill-v25-venv/bin/python artifacts/methods/v25/v25_two_round_exploration_20261028_001/summarize.py --validate
/tmp/govern-skill-v25-venv/bin/python artifacts/methods/v25/v25_two_round_exploration_20261028_001/verify_checkpoint.py
/tmp/govern-skill-v25-venv/bin/python artifacts/methods/v25/v25_two_round_exploration_20261028_001/export_tables.py
/tmp/govern-skill-v25-venv/bin/python artifacts/methods/v25/v25_two_round_exploration_20261028_001/build_report.py
```

离线核验通过：冻结文件不变；R01 的 30 条 Actor 记录及 R02 已完成的 4 条记录符合合同；重算 Gate 一致；Verifier/Repair 的最终结果与 Memory commit 完全一致；证据历史顺序及 R02 父 Skill/Memory 继承一致；没有 R03 或最终 Test 执行。这些是结构与一致性检查，不声称验证了所有自然语言经验的真实性。

`verify.py` 是预备的“两轮完成”校验器，当前不应运行或将它的目标状态误报为已达成。`verify_checkpoint.py` 专门校验当前实际完成的断点。恢复模型运行需要用户再次要求，并先恢复 API 额度；保留原任务槽剩余请求预算和完成结果，不直接复跑一次性恢复脚本。

复现的是冻结条件、任务次序与归档处理，不承诺 temperature=1.0 的模型重新采样会逐字重复结果。
[所有实际计划、D/S/C、Candidate 与经验全文](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/outputs.md) · [机器可读记录](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/records.json) · [当前保留 Skill](../results/retained_skill.md) · [范围与结论状态](../../../../../artifacts/methods/v25/v25_two_round_exploration_20261028_001/assessment.json)
