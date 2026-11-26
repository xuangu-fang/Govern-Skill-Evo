# Replay 局部修改：单配对同期 B0/B1 初筛

2026-10-28。已完成预定 4 次 DeepSeek 调用，全部首次通过格式与引用校验，无格式修正、技术重试或语义重采样。默认 Replay v3 / 输入视图 v4、Preconditioner v7 未变；未发布 Memory，未运行 Actor、Verifier、完整链路或训练。

结论：**B1 未通过预先固定的初筛标准。** 它更明确地保留了 R06 的双侧物料优先级，但仍没有完整比较回退触发条件，且在因果边界上比本次 B0 更差；R05 则出现比较中有分支区别、Knowledge 又将其概括错误的问题。不建议本轮切换默认或扩大到完整批次。此结论针对本轮筛选，不是稳定效果估计或对模型能力的总体判断。

## 1. 设计与执行

| 输入 | B0 | B1 |
|---|---|---|
| R05：P3/Q3，train:433-47 | 原 B 诊断 prompt，重新调用 | 已审阅的五处局部替换 |
| R06：P15/Q15，val:2768 | 原 B 诊断 prompt，重新调用 | 已审阅的五处局部替换 |

B0/B1 的单配对 user 消息逐字相同；Parent、Diff、Plan、原 Memory、完整目标轨迹、共享消息、评分和原引用不变。system 仅有[既定草案](../../../../../artifacts/methods/v25/analysis/replay_local_revision_proposal_20261028_001/diagnostic.diff)的五处替换，执行背景和其他尾部说明、comparisons + entries 输出约定均不变。请求与[已准备版本](../../replay_local_revision_proposal_20261028_001/reports/README.md)逐字核对，未临场补充目标答案或加强提示。

参数：deepseek-v4.1-flash，max_tokens=49152，temperature=1.0，reasoning_effort=medium，thinking enabled，stream=false，timeout=300 秒，原内网 endpoint。四个请求并发启动，均从仅 system/user 的干净请求开始。人工判读协议未发送给模型。既有技术/格式反馈机制保留，但本次未触发；语义遗漏不触发重试。

- [运行前协议副本](../../../../../artifacts/methods/v25/analysis/replay_local_revision_screen_20261028_001/review_protocol.json)、[冻结清单](../../../../../artifacts/methods/v25/analysis/replay_local_revision_screen_20261028_001/manifest.json)、[最终离线校验](../../../../../artifacts/methods/v25/analysis/replay_local_revision_screen_20261028_001/final_checks.json)。
- [全部比较与 Knowledge 原文](../../../../../artifacts/methods/v25/analysis/replay_local_revision_screen_20261028_001/outputs.md)、[逐项语义评审](../../../../../artifacts/methods/v25/analysis/replay_local_revision_screen_20261028_001/semantic_review.json)、[调用统计](../../../../../artifacts/methods/v25/analysis/replay_local_revision_screen_20261028_001/metrics.json)。
- 原始结果：[B0/R05](../../../../../artifacts/methods/v25/analysis/replay_local_revision_screen_20261028_001/B0/R05/replay/attempts/001/diagnostic.json)、[B1/R05](../../../../../artifacts/methods/v25/analysis/replay_local_revision_screen_20261028_001/B1/R05/replay/attempts/001/diagnostic.json)、[B0/R06](../../../../../artifacts/methods/v25/analysis/replay_local_revision_screen_20261028_001/B0/R06/replay/attempts/001/diagnostic.json)、[B1/R06](../../../../../artifacts/methods/v25/analysis/replay_local_revision_screen_20261028_001/B1/R06/replay/attempts/001/diagnostic.json)。相邻目录保存实际 messages/request/response/input/model_input、校验与耗时。

review_protocol.json 是执行前计划的不可变副本，保留原 planned_not_run 字段；实际完成情况由本报告、各 summary.json 与 final_checks.json 记录，不回写修改草案或旧档案。

## 2. 预定标准的结果

| 检查项 | B0 | B1 | 判断 |
|---|---|---|---|
| R05 双侧正负动作映射 | 保留 | 保留 | 这项不是 B1 独有改善 |
| R05 Parent 正残差已有跨格延续 | 描述与概括仍不完整 | 比较/行级推断部分呈现，K1 又写成每行首格吸收整笔 | 未满足保留标准 |
| R06 双侧物料优先级 | 明确 Candidate code 优先，Parent name 优先未写清 | 单独比较 Parent name 优先与 Candidate code 优先，进入 K2 | 本样本有改善 |
| R06 完整回退条件 | 缺失 | 写出回退目标，仍缺触发判据对照 | 未满足完整性标准 |
| R06 相同结果的因果边界 | 保留错值及根因未知 | 用同错误坐标排除后缀合并解释 | 未满足推断边界标准 |
| R06 H2:H18 与引用身份 | 正确 | 正确 | 保持 |

四个输出均 revises=[]，没有替换历史 Memory；没有引用已删除的当前执行或编造 15 对当前批次汇总。B0/R05 为 3 observations / 3 Knowledge，B1/R05 为 4/4；B0/R06 为 3/3，B1/R06 为 5/3。条目数只作描述，不作成功标准。

## 3. R06：优先级保留改善，完整条件与因果判断仍失败

### 3.1 确实改善的部分

B0 在比较和 Knowledge 中提到 Candidate 优先 item code，但没有明确对照 Parent 的名称优先。

B1 Observation 2 专门描述：Parent preferred Item name and fell back to Item code；Candidate preferred Item-code match, falling back to Item name。K2 又单独保留了两侧优先级差异。这比只说“两套库存表”或只描述 Candidate 更完整，也没有再次将优先级全部压缩掉。

### 3.2 为什么仍判 partial

预定标准要求比较实际触发条件，而不是仅写“X 优先，Y 备用”：

- Parent 使用 `norm_item(item) or norm_item(icode)`，name 为空才回退 code；name 非空但没有库存匹配时不会尝试 code。
- Candidate 检查 `key_code in stock_by_code`，code 键未命中才尝试 name；因此是否有字段值与是否命中库存表是不同判据。

B1 比较和 K2 都没有明确保留这个区别，也没有把它与可能改变的库存分组条件对齐。这里不是缺少原程序，两个判断都在当次完整输入中。因此不能因为出现两个字段名、优先级和 fallback 字样就评为 complete。

### 3.3 因果边界出现明确倒退

B0 写出：实际值是否不同未知；H12/H13 根因未定；预览没有揭示隐藏行的后缀分布。它没有用等分排除键机制。

B1 Observation 1 和 K1 则写出：

> ... retaining versus truncating the model suffix changed no graded cell and the two failures are not explained by suffix merging ...

即使将 changed no graded cell 理解为“通过/失败状态没变”，后半句仍是无依据的因果排除。两种程序可以在相同坐标写出不同错值，也可以由不同或共同机制导致失败；同一错误集合不能排除后缀处理参与其中。它随后又承认实际输出值不在记录中，这个 caveat 没有修复前面的排除句。

这直接违反 B1 新增的“等分不能排除某机制参与失败”要求。无需推断内部推理：可见比较和 Knowledge 都存在这一错误。

## 4. R05：有效的新推断与错误概括必须分开评价

### 4.1 未满足分支保留标准

B1 Observation 1 至少区分了 addition branch 整笔写首格与 subtraction branch drained cells down to 0。它的行级描述还指出正残差 +242 的 Parent 同时改变 F3 与 E3。

但 K1 又写：

> Parent ... absorbed each row's whole amount in the first non-zero unit cell of its chosen direction ...

这把只属于负残差加法分支的行为扩大成每行；甚至与同一 K1 中的 F3=0、E3=523 两格变化互相矛盾。正负动作映射在 K2 中仍然正确，但不能修复 K1 自身的错误。

B0 也有概括不完整的问题：shared_and_different 写成双方区别包括是否能跨多格，而 Parent 正残差本已能跨格。B1 因而不是从一个完全正确基线退化，但也没有实现其新增的保真检查。

### 4.2 新增的行级推断并非都应判作无依据

B1 使用了已有预览、程序和完整评分坐标，以下推导可核对：

| 已有输入与程序 | 可以确定的 Parent 行为 | 结合评分可确定的关系 |
|---|---|---|
| Row 3 residual=242，F3=215，E3=550，C3=250；Parent 从 F 向左减至 0 | F3=0，剩余 27 从 E3 减去，E3=523；C3 保持 250 | C3 出现在错误列表，故预期 C3 不等于 250 |
| Row 2 residual=-145，B2=282，E2=550，F2=215；Parent 首格加 145 | B2=427；E2/F2 保持原值 | E2/F2 都错，故预期值也改变了 unit5 一侧 |
| Rows 4/5 residual=50/124，F=215 | F4=165，F5=91；B4/B5 仍为 282 | B/F 错而 C/D/E 通过，与 Candidate 正残差从 unit1 加的结果一致 |

本次只做了标量算术和完整错误列表核对，没有执行 Actor 程序或打开工作簿。

由 Candidate 完整通过和其确定程序逻辑，还能对局部边界激活形成更强的间接支持：

- Row 3 的 Candidate 必须改变 C3；若 unit1 上限是无限大，+242 会全被 B3 吸收，不会改变 C3，因此该行的 unit1 有限上限实际起了作用。
- Row 2 的 Candidate 必须改变 E2；若 unit5 下限为 0，215 足以吸收 145 的减量，就不会继续到 E2，因此该行的 unit5 下限不是默认 0。

这修正了此前“一律无法从当前记录判断边界激活”的过宽说法：结合代码、预览与评分，可以建立局部推断，不必机械要求新增日志。它仍不提供精确边界值，也不证明所有列的边界均正确，更不揭示参考工作簿生成过程或隔离 Skill 条款的因果贡献。

B1 称“expected workbook itself used per-column limits”容易混淆目标结果与目标生成过程，应收窄为上述可检验的局部行为关系。其对“动态列定位 enable 读取边界”的表述也不应当作必要性证明：已知列位置同样可以读取边界，动态定位只是该 Candidate 的实现路径。

### 4.3 有价值的边界处理

B1 区分了“代码会跳过零值”和“本次确实遇到零值”：预览 rows 2–5 没有零 unit 值，后续行不可见，因此没有演绎出零值排除已被实际测试。这是具体的证据边界改善，但不足以抵消 K1 的分支概括错误。

## 5. 资源与解释限制

| 条件 | Prompt tokens | Completion tokens（含 reasoning） | 最终正文空白分词 | 耗时秒 |
|---|---:|---:|---:|---:|
| B0/R05 | 24,044 | 9,987 | 740 | 63.5 |
| B1/R05 | 24,291 | 26,056 | 1,590 | 180.4 |
| B0/R06 | 31,238 | 15,821 | 1,027 | 125.7 |
| B1/R06 | 31,485 | 14,356 | 1,001 | 97.3 |

B1 实际输入增加 247 tokens。R05 写得更长并给出更多逐行推断，但核心保留错误仍存在；R06 优先级更清楚，因果边界却比 B0 差。无法用总字数、观察条数或推理预算解释为质量改善。缓存、服务延迟及抽样不同，不从单次耗时推断稳定速度差异。

每个条件仅一次、temperature=1；结果不证明草案总体必然更差，也不证明模型无法执行这些要求。可以确定的是：本轮没有满足已经写好的最低筛选条件，不能在看到部分亮点后临时降低标准。

## 6. 决策

根据预先固定的标准：

- R06 完整选择与回退条件：未满足。
- R06 正确的评分/因果边界：未满足。
- R05 Knowledge 保持正确分支事实：未满足。

因此保留 B1 为研究草案，生产默认保持不变，本轮不进入完整批次验证。没有进行额外语义重跑、修改 prompt 后补跑或将输出发布到 Memory。

本轮暴露的关键是“新增要求未可靠落实为具体核对”：R05 同一 Knowledge 内可以同时写对行级动作又写错全局概括；R06 明知没有实际值仍排除某种失败机制。下一阶段应优先研究如何核验这些具体结论与证据是否相符，保留有效的条件推断，避免继续把更多提醒和更长输出当作已解决问题。

离线复核与导出，不调用模型：

```sh
/Users/didi/miniforge3/envs/spreadsheetbench/bin/python artifacts/methods/v25/analysis/replay_local_revision_screen_20261028_001/summarize.py
```
