# V25 小规模完整闭环核验：前置审计报告

日期：2026-10-28。**归档工程衔接通过，最终 Memory 的事实准确性检查未通过。按“核验通过后再运行两轮”的条件，停在前置核验，没有启动新的连续自进化。** 本次 API 调用、Actor 执行和最终 Test 使用均为 0；未修改 Prompt、方法源码或历史 Memory。

这不是当前 Replay v4 的模型效果失败报告。被复用的真实闭环来自旧版 campaign；当前 v4 只有此前的离线安装检查，不能把复用旧响应的 fixture 当成 v4 模型输出。发现的明确事实错误足以使本次历史 Memory 准确性检查不通过，但不能据此断言新版本必然失败，或要求所有经验都获得完整因果证明。

## 1. 固定版本与范围

当前版本和全部方法/基准实现文件的哈希保存在 [method_freeze.json](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_preflight_20261028_001/method_freeze.json)：

| 模块 | 固定版本 |
|---|---|
| Diagnosis | `v25_diagnosis_evidence_scoped_updates_v5` |
| Preconditioner | `v25_preconditioner_evidence_decision_boundaries_v7` |
| Replay Prompt | `v25_replay_decision_fidelity_v4` |
| Replay 输入视图 | `v25_replay_pairs_knowledge_only_v4` |
| Verifier/Repair | `obvious_fact_verifier_targeted_repair_v1`，现有正文和实现保持原样 |
| 其他模块 | 完整 method 配置和文件哈希冻结，未修改 |

审计来源为 `artifacts/methods/v25/v25_skilladam_execution_only_actor48k_20261027_001_v25/campaign`。其实际历史配置是 Diagnosis v4、Preconditioner v6、Replay Prompt v1 / 输入视图 v1；按归档版本重读，没有改写版本标签或恢复该 campaign。历史任务全部属于 Train/Val 开发池；没有读取最终 Test 的模型输出、成绩或标准答案工作簿。

本次只在这个报告目录保存重建结果。历史归档和生产源码的修改前/后哈希一致；没有将审计副本发布到 campaign。

## 2. 完整传递过程核验

| 路径 | 实际结果 |
|---|---|
| R05/R06 Actor → Replay | 共 60 份 Parent/Candidate 原始记录重建成功，与实际 Replay bundle 一致；原生读取同时核对消息、版本、响应、解析和引用 |
| Replay → Verifier | 按真实选中 attempt 重建输入及消息，重读原 verdict；R05 使用第 2 次格式有效输出，R06 使用第 1 次 |
| Verifier → Repair | R05 8 个目标、1 个 CONFLICT，执行一次定向 Repair；R06 4 个目标、0 个 CONFLICT，没有 Repair |
| Repair/放行 → Memory | 复用前一轮 Memory，在报告目录重新 commit；完整 commit、active 索引和 Memory view 与原归档完全相同 |
| R05 Memory → R06 Preconditioner | M1–M9、34 条 Knowledge 完整进入实际模型输入，文字、顺序和 evidence 一致 |
| R06 Memory → R07 | R07 Diagnosis 返回 `no_change`；没有 Preconditioner 调用，Memory 状态保持不变 |
| R06 Memory → R08 Preconditioner | M1–M10、38 条 Knowledge 完整进入实际模型输入；这是 R06 发布后下一次真实 Preconditioner 消费 |
| 时间和引用 | 历史引用均来自消费轮次以前的 context；原生 Memory 校验验证引用可解析和提交谱系，未发现未来证据泄漏 |

检查脚本：[audit.py](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_preflight_20261028_001/audit.py)；机器结果：[structural_audit.json](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_preflight_20261028_001/structural_audit.json)。这些检查证明记录与传递一致，不证明每条自然语言结论为真。

## 3. 阻止本次前置核验通过的具体问题

**F1：明确反例已在 Verifier 输入中，但错误仍被放行并进入后续 Memory。**

R05 最终 M9 `knowledge[1]` 写道 Candidate “converting all 16 graded cells”。实际当次预览明确包含 `E2=American Express`；Q1 程序只有在 E 列包含归一化后的 `Georgia Its Tax` 时才修改该单元格。因此 E2 不进入修改分支，16/16 是评分正确数，不能描述为 16 格全被转换。

完整证据链：

1. Replay 草稿包含该句，最终发布文本也保留该句，见 [最终经验](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_preflight_20261028_001/evidence.md#r05-entries0knowledge1)。
2. Verifier 实际拿到 Q1 完整代码及包含 E2 的初始任务预览，见 [代码与实际输入](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_preflight_20261028_001/evidence.md#r05-verifier-原始证据-q11)。无需读取隐藏行、标准答案或新增运行即可找到反例。
3. Verifier 对 `{entry_index:0, knowledge_index:1}` 返回 `SUPPORTED`，见 [原 verdict](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_preflight_20261028_001/evidence.md#r05-verifier-最终响应)。
4. 该轮 Repair 仅处理 `knowledge[7]` 的 unmatched 行描述，不包含这个目标；未授权条目原样保留。
5. M9 发布后完整进入 R06 请求；R06 `revises=[]`，仅审查 4 条新经验，M9 保留到 R08 的实际请求。

这不是关键事实缺失、存储丢失或历史时序错误。可观察的问题是一次明确事实漏检，加上“未被修订的旧经验不重新审查”的现有覆盖边界。仅凭这个样本无法区分模型抽样波动、注意力分配和 Prompt 本身的相对贡献，也不能证明它已造成某次 Candidate 退步。

本次据此停止的原因是用户要求先检查最终经验的事实准确性；并非因为存在任何假设或措辞不够完美。**它阻止把旧 Memory 当作已通过事实核验的输入；不是证明从空 Memory 启动新版本必然无法运行。** 当前 v4 能否降低这种错误仍未实测。

## 4. 其他发现与有效环节

| 编号 | 发现 | 判断 |
|---|---|---|
| F2 | M9 文本经验把 E10/E11 判错写成原值未改，并使用“clear single-clause improvement”；实际两行值不可见，数值解析及不可解析值处置也改变 | 观察和归因过强；允许保留修复假设，不能升级为已观察事件。不是本次单独阻断依据 |
| F3 | M9 数值经验未明确对照正负残差对应动作的整体反转 | 重要竞争解释遗漏；不是引文或存储故障。局部边界激活可以从程序、预览和评分作间接推断，不应一律要求新增日志 |
| F4 | R05 Verifier 指出双方 unmatched 都写 `#N/A`，Repair 删除“处理不同”的错误描述，同时保留空白归一化差异和归因未知 | 审查修正实际有效；不能把修正前草稿错误继续算作最终 Memory 错误 |
| F5 | R06 M10 省略 Parent 名称非空即使用、Candidate code 库存键命中才优先使用的选择差异 | 重要条件遗漏。其“changed no graded cell”可解释为评分状态没变，不直接判成明确输出值错误；仍保留共享失败根因未知 |
| F6 | R06 未修订 M9，因此新一轮 Verifier 没有重新审查其旧错误 | 符合当前目标选择规则，是历史错误持续存在的机制，不是 Repair 越权或漏执行 |

逐项判断见 [semantic_review.json](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_preflight_20261028_001/semantic_review.json)，原文、实际代码和 verdict 见 [evidence.md](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_preflight_20261028_001/evidence.md)。这是有明确范围的人工证据审查，不是对全部 38 条历史 Knowledge 的穷尽因果审计。

## 5. 每轮记录与成本

**以下均为旧 R05/R06 的真实归档数据，不是当前 v4 新实验成绩。** Original Plan、原始 D/S/C 调整、编译结果、完整 Candidate Skill、逐题 Parent/Candidate 结果和 Memory 更新已统一导出到 [historical_round_records.json](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_preflight_20261028_001/historical_round_records.json)，并在结构报告中保留原始文件位置。

| 历史轮次 | D/S/C 变换概况 | 成绩（hard 成功任务） | hard 退步 | Memory |
|---|---|---|---|---|
| R05 | u1/u2 KEEP；u3 标记 D/S/C 调整 | 12/15 → 15/15，ACCEPT | 0 | 新增 M9，8 条；Repair 修改其中 1 条 |
| R06 | u1/u2/u3 均标记 S 调整 | 11/15 → 13/15，ACCEPT | 0 | 新增 M10，4 条；无 Repair，M9 原样保留 |

这些成绩说明旧轮次在各自开发批次的表现，不能证明 Memory 或 Preconditioner 的因果收益，也不能替代当前版本两轮实验。

| 成本口径 | 历史 R05 | 历史 R06 | 本次新增 |
|---|---:|---:|---:|
| Actor HTTP 请求 | 38 | 38 | 0 |
| 方法模块 HTTP 请求 | 9 | 14 | 0 |
| 程序执行 | 31 | 31 | 0 |
| 已知 prompt tokens | 559,309 | 691,738 | 0 |
| 已知 completion tokens（含推理） | 667,149 | 762,122 | 0 |
| usage 未知的请求 | 4 | 8 | 0 |

历史成本采用现有 `cost_summary`，包括失败请求；未知 usage 不补为 0，因此已知 tokens 是不完整统计。没有可靠的内网计费单价，不虚构历史金额。本次没有 API 请求，因此新增 API 成本为 0。

## 6. 当前是否具备下一阶段条件

| 判断项 | 结论 |
|---|---|
| 模块工程衔接 | 已有实际归档重建通过；当前源码的离线发布/修复/恢复分支检查通过 |
| 旧最终 Memory 可当作已核验事实使用 | 不通过：F1 是明确错误并持续进入后续输入 |
| 当前固定版本的两轮真实闭环 | 未开始；不能用旧归档或离线替身冒充完成 |
| 正式连续多轮实验 | 当前证据尚不足以放行，不能宣称“已具备”；也不能从旧版漏检推断 v4 必然失败 |
| 有无历史预条件化消融 | 工程上可准备，但尚未执行；需要明确使用哪一份已记录质量边界的 Memory，固定同一 Original Plan，避免把历史内容质量和利用能力混为一谈 |

**建议接下来仍固定现有方法，先在隔离目录复用 R05/R06 的原始执行事实，运行当前 Replay v4 → 现有 Verifier/Repair，检查实际最终产物，再决定启动两轮。** 这一步不必重跑 Actor，不必修 Prompt，也不将旧错误直接迁入新实验。其目的只是在当前版本上补齐发布后经验的直接证据，不以所有遗留问题必须全部解决为准。若继续出现明确错误，保留实际审查输入与 verdict 定位；不通过语义重采样挑选成功结果。

这项新的模型调用尚未执行。当前记录为 [decision.json](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_preflight_20261028_001/decision.json)：`stopped_at_archive_factual_acceptance`，不是两轮完成，也不是当前 v4 效果判负。

## 7. 可复现方式

归档校验只读源目录，在本报告 `reconstructed_memory/` 内进行可重复提交重建，并禁止网络及生产 generator。它核对 method freeze、原归档哈希、实际输入/响应、提交谱系及后续模型请求；手工语义结论单独保存，避免把结构断言包装成自动事实判真。

```sh
/tmp/govern-skill-v25-venv/bin/python artifacts/methods/v25/analysis/v25_closed_loop_preflight_20261028_001/audit.py

/tmp/govern-skill-v25-venv/bin/python -m pytest -q \
  tests/skill_evolution/v25/test_pipeline.py \
  -k 'full_flow or branches or publication_resume'
```

结果：**10 passed、2 deselected**，7.10 秒；覆盖离线完整衔接、定向 Repair、RETAIN、no_change、格式重试和发布前/后恢复。使用合成替身，无真实模型调用；排除了该文件的两个 evaluation 测试。日志见 [pytest.log](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_preflight_20261028_001/pytest.log)，机器结果见 [pytest.xml](../../../../../artifacts/methods/v25/analysis/v25_closed_loop_preflight_20261028_001/pytest.xml)。这不能替代用户要求的两轮真实开发任务自进化。
