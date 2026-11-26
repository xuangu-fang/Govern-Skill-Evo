# V25 当前版本：R05/R06 发布链路实测与两轮实验前置判断

2026-10-28。**已完成两次当前 Replay v4 → Verifier → Repair → 隔离最终 Memory 的真实运行，共 6 次 DeepSeek 调用。工程链路全部完成，但发现一处新的明确行为事实错误被放行并发布，故按阻断处理约定暂未启动两轮连续自进化。**

本次是当前版本的直接模型证据，不是复用旧响应的离线 fixture。没有改 Prompt、方法源码、旧实验或正式 Memory，没有语义重采样，没有 Actor 调用或最终 Test 使用。两轮计划、版本、判读范围及停止条件在调用前保存于 [protocol.json](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/protocol.json)。

## 1. 固定条件与两阶段范围

- Diagnosis v5、Preconditioner v7、Replay Prompt v4、Replay 输入视图 v4，其他模块原样冻结于 [contract.json](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/contract.json)。
- 模型实际均返回 `deepseek-v4.1-flash`；原内网接口、temperature=1、reasoning_effort=medium、thinking enabled、stream=false、timeout=300 秒。Replay/Verifier 输出上限 49,152 tokens，Repair 32,768。
- R05/R06 各自复用原完整 15 对执行事实、原 Skill/Diff/Plan 和原历史 Memory；初始请求只有 system/user，没有旧回答和旧修正反馈。输入视图 v4 的序列化 user 与此前 v3 实验逐字相同，Replay 非消息调用参数相同。
- 两个案例彼此独立：**新版 R05 M9 没有替换 R06 原输入中的旧 M9**。这样保留原事实与历史条件，也避免把独立重放说成连续演化。
- 计划中的两轮训练从原始 initial Skill、空 Memory 开始，沿原 Train 顺序取前两批，每批 15 题、Actor 并发 4、Actor 输出上限 49,152，最多 30 次程序执行，第二轮后强制停止。现有配置验证要求原 8×15 分批，因此只限制运行范围，没有伪装合成数据或更改方法来缩小批次。
- 两轮训练没有启动：没有 `campaign/rounds`，没有 Original Plan/D/S/C/Candidate 新训练产物。不能用旧 R05/R06 的计划和成绩代替这两轮。

## 2. 实际发布结果

| 案例 | Replay 新 Knowledge | Verifier | Repair | 最终隔离发布 |
|---|---:|---|---|---|
| R05 | 7 条，1 entry，revises=[] | 1 条 CONFLICT，6 条 SUPPORTED | 修正 Knowledge 4 的公式类型 | 新 M9；累计 9 entries / 33 Knowledge |
| R06 | 4 条，1 entry，revises=[] | 4 条均 CONFLICT | 修正各条中的 Train/Val 标识 | 新 M10；累计 10 entries / 38 Knowledge |

全部模块首次返回即通过格式/引用校验，没有格式纠错请求、技术重试或语义重采样。修正前后全文见 [publication_outputs.md](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/publication_outputs.md)；每条实际请求、原始响应、usage 和验证结果都保存在 `publication/{R05,R06}/{replay,verifier,repair}/attempts/001/`。

隔离最终 Memory：

- [R05 view](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/publication/R05/memory/view.json)，新 context 为 `publication_v4_R05`。
- [R06 view](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/publication/R06/memory/view.json)，新 context 为 `publication_v4_R06`。

它们可按原生 Memory 契约重读，没有导入原 campaign 或计划中的新训练。

## 3. 有效改善和实际修正

**旧的 R05“16 格都被转换”错误没有在新经验中重现。** 新 Knowledge 1 正确区分 14/16 与 16/16 的评分，明确 Candidate 同时改变文本匹配和数值条件处理，不能隔离是哪一种变化产生收益。这是本次样本的改善，不是稳定效果估计。

Verifier/Repair 也完成了具体纠正：

- R05 Knowledge 4 原称 Q11 在 E、P 两列都写 VLOOKUP；Verifier 从代码指出 E 为 VLOOKUP、P 为 ROUND，Repair 修复该描述，保留其余经验。
- R06 将 `val:560-12`、`val:80-42`、`val:2768` 错写为 Train，Verifier 找出相关错误，Repair 在全部四条相关 Knowledge 中改正。

这些结果说明，审查器能发现明确错误，修正补丁能被准确应用。不能把“仍有漏检”概括为整个 Verifier/Repair 没有作用。

## 4. 这次真正的阻断点：新的错误行为经验被发布

R05 最终 Knowledge 6 将三个任务统称为：

> Label-matching tasks Parent already solved with lowercase substring or exact-key matching stayed solved with Candidate's casefolded, whitespace-normalized versions ... train:30930 (P9/Q9 ...).

但 `train:30930` 的实际两份程序都是**数值标记与正数计数**：

- Parent：将 B 转成数值，判断 `b_val == 1.0`；统计两个标记之间 A 列大于 0 的值。
- Candidate：`to_number`、`is_one`、`is_positive`，用容差识别数值 1，再统计正数。
- 两者没有该经验所称的 label 匹配、子串匹配或 case-folded 文本归一化实现。两侧 65/65 成功是真的，归纳成“这项文本匹配能力得到保持”是错误的行为事实。

这不只是没有隔离因果，也不是缺少隐藏数据；它误述已提供程序的操作，给历史经验附加了不存在的能力支持。其他两个例子可能仍支持局部文本经验，不能使这一个例子的错误自动成立。现有 Verifier 自身要求检查错误事件描述，即使同一经验还有其他支持案例。

证据链已逐项复核，见 [blocking_evidence.md](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/blocking_evidence.md)：

1. P9/Q9 两份完整程序都在 **Verifier 当次实际输入**的 `source_records.P9:1/Q9:1.record.executed_code` 中。
2. Verifier 对 `{entry_index:0, knowledge_index:6}` 返回 `SUPPORTED`。
3. Repair 只获准修改 Knowledge 4；Knowledge 6 的文本与 Replay 原输出逐字一致。
4. 该条实际进入隔离 Memory 的新 M9，原生重读通过。

因此可定位为**Replay 错误概括 + Verifier 对已见事实漏检**。Repair 没有擅自修改未授权条目，Memory 也没有传输失真。本次没有 Preconditioner 调用，不能声称这个错误已经导致某轮更新或成绩退步。

该问题符合调用前协议中的“明确、重要的新事实错误在发布后仍存在”，所以没有放行两轮训练。判读不是要求经验完美，也没有把所有未验证假设和遗漏都当作阻断。

## 5. 其他保留问题，单独记录而不混成阻断理由

| 项目 | 当前结果 | 判断 |
|---|---|---|
| R05 正负残差与动作反转 | 新 Knowledge 2 仍没有明确对照，首格吸收描述缺少清晰的分支限定 | 关键比较与概括风险；不是本次单独停止理由 |
| R05 边界读取 | 文本仍称实际读取 min/max，并强调 single-clause alignment | 需要区分程序路径、局部可推断的边界激活与全局归因；不能因为没日志就否定一切合理推断 |
| R06 name/code 选择规则 | 最终 Knowledge 2 仍未保留“name 非空即用”与“code 库存键命中才优先”的区别 | 重要条件遗漏，未被 Verifier 补充 |
| R06 因果排除 | 同一 Knowledge 仍说共享两格错误不由 suffix-key 选择解释 | 相同评分/错误坐标不能支持该排除；后面的根因未知没有修复前面的强断言 |
| R06 继承的旧 M9 | 原输入中的旧“all 16 graded cells”经验仍在最终历史中 | 来自原历史且 revises=[]，不是当前 v4 新生成的回归；必须与新的 R05 M9 区分 |

人工判读和启动决定见 [publication_assessment.json](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/publication_assessment.json)。本次只有每例一次样本，不能将表现差异稳定归因于 Prompt，也不能由此认定模型能力是唯一原因。

## 6. 输入规模与 API 成本

| 案例/模块 | Prompt tokens | Completion tokens（含推理） | 请求耗时秒 |
|---|---:|---:|---:|
| R05 Replay | 82,400 | 25,143 | 165.32 |
| R05 Verifier | 261,394 | 31,615 | 205.99 |
| R05 Repair | 204,945 | 6,811 | 46.57 |
| R06 Replay | 96,799 | 17,176 | 120.38 |
| R06 Verifier | 57,244 | 31,169 | 205.12 |
| R06 Repair | 57,323 | 3,064 | 17.44 |
| **合计** | **760,105** | **114,978** | 并发执行，不把各请求耗时相加当墙钟时间 |

共 **875,083 tokens**；其中 reasoning tokens 107,904，属于 completion，不重复相加。6 次请求 usage 全部已知。内网计费单价未提供，不能可靠换算货币金额。Actor、完整训练和 Test 新增调用均为 0。

值得后续定位的是：R05 Verifier 输入为 Replay 的约 3.17 倍，Repair 也超过 20 万 prompt tokens；一个公式类型问题的定向修正仍接收很大的原证据包。当前只确认输入规模与遗漏同时存在，**没有证据证明长上下文就是漏检原因**，也没有据此修改输入组织或 Prompt。

## 7. 当前是否可以进入正式实验

- **工程上**：当前 Replay、Verifier、Repair、Memory 发布及归档重读衔接成功。
- **经验质量上**：当前版本仍能将已提供程序直接反驳的能力描述发布到 Memory，事实验收未通过。
- **两轮连续自进化**：未开始；Diagnosis v5、Preconditioner v7 的当前连续调用效果没有新增证据，不以发布链路成功替代它们的验证。
- **正式多轮及有无历史预条件化消融**：尚不能宣布条件齐备。原始执行事实与最终经验之间的问题已经定位到当前输出，应先明确处理这一发布质量问题；不能直接把一份含明确错误的经验当作“可靠历史”来解释预条件化收益。

本次没有继续设计新 Prompt。若下一步研究这次漏检，最直接的对象是 R05 Knowledge 6、当次 Verifier 输入和原 verdict，区分局部核对能力与完整上下文中的目标选择；这属于后续诊断，不在本次追加调用。已经准备的两轮入口保留，但 [publication_assessment.json](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/publication_assessment.json) 的 `start_two_rounds=false` 防止误启动。

## 8. 复现与文件保护

- [run.py](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/run.py)：调用前准备、两次隔离发布及两轮限定入口；使用原有 retry、审查、Memory commit 和 campaign 实现。
- [manifest.json](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/manifest.json)：输入、运行脚本、配置、协议及原 Memory 哈希；[runtime.json](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/runtime.json) 固定 Docker 运行环境。
- [records.json](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/records.json)：所有已执行模块、原始/最终经验、错误次数及 API 成本；`rounds=[]` 明示没有训练轮次。
- [offline_validation.json](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/offline_validation.json)：两份真实归档原生重读，实际审查输入、最终提交、历史谱系、非消息调用参数核对通过；生产方法及原 campaign 的 5,036 个受保护归档文件未变。
- [campaign_summary.json](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/campaign_summary.json)：明确记录训练未开始及阻断项。

离线复核，不调用模型、不执行 Actor：

```sh
/tmp/govern-skill-v25-venv/bin/python artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/verify_saved.py
/tmp/govern-skill-v25-venv/bin/python artifacts/methods/v25/analysis/v25_closed_loop_live_20261028_001/summarize.py
```

真实请求已保存；不要把再次调用模型当作确定性复现。若经后续决定继续两轮实验，应保留本次原始否决记录与依据，显式记录新的放行决定，不改写本报告为“全部通过”。
