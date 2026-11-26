# Replay 小规模诊断：显式比较是否减少重要程序差异遗漏

2026-10-28。已完成 4 次实际 DeepSeek 调用，每个条件一次；全部首次返回有效格式，无格式修正或 API 技术重试。没有修改生产代码、默认 prompt、原实验档案或发布 Memory，没有运行 Actor、Verifier、完整链路或训练。

结论：不改 prompt 的同期基线本次已识别 R05 的正负残差动作反转；显式比较组也识别了它。因此不能将这项改善归因于新增比较产物。R06 两组仍只部分保留物料匹配差异；B 的可见比较记录本身就没有完成选择优先级和回退条件的对照，没有观察到“完整提取、仅在最终 Knowledge 丢失”的模式。比较产物提高了可检查性，但本次不足以证明其提高学习质量。

## 1. 设计、控制与可复核性

| 条件 | 实际输入 | Prompt 与输出 | 调用数 |
|---|---|---|---:|
| A | 原始完整 v4，15 对 runs，原 Parent / Diff / Plan / Memory | 原版 Replay v3，输出 entries | R05、R06 各 1 |
| B | 与 A 的序列化 user 消息逐字相同 | v3 判断要求保留；统一调整输出约定，先 comparisons 后 entries | R05、R06 各 1 |

来源：[上一轮 v3 实验](../../replay_v3_deepseek_r05_r06_clean_20261028_001/reports/README.md)。A 的两条初始消息与相应历史 v3 请求完全相同。B 不点名目标配对，不提示残差反转、物料优先级，不缩减其他配对、Diff 或 Memory；只把既有相关配对比较要求的结果变成可见产物，未要求每对产生固定数量的差异。B 的字段是 condition、parent_behavior、candidate_behavior、shared_and_different、observed_and_unknown、evidence。它是供审阅的证据产物，不要求公开内部推理。

调用参数保持原值：deepseek-v4.1-flash；max_tokens=49152；temperature=1.0；reasoning_effort=medium；thinking enabled；stream=false；timeout=300 秒；内网原 endpoint。初始请求仅 system/user，无旧回答和修正反馈。语义遗漏不触发重试，若格式错误则沿用原有有界反馈机制。B 的 entries 仍通过原生 Replay validator；诊断 envelope 由隔离的结构与引用 validator 校验，不冒充原生 Replay archive。

- [运行前固定的人工判读标准](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/review_criteria.json)：未发送给模型。
- [诊断 prompt](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/diagnostic_learning_prompt.md)、[相对 v3 的差异](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/prompt.diff)。B system 多 1,072 字符，实际 prompt tokens 多 147。
- [输入和源文件冻结清单](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/manifest.json)、[离线校验](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/offline_checks.json)、[最终校验](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/final_checks.json)。
- [完整 Knowledge 输出](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/outputs.md)、[完整比较记录](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/comparisons.md)、[人工语义评审](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/semantic_review.json)。
- A 原生归档：[R05](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/A/R05/replay/attempts/001/replay.json)、[R06](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/A/R06/replay/attempts/001/replay.json)。
- B 诊断归档：[R05](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/B/R05/replay/attempts/001/diagnostic.json)、[R06](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/B/R06/replay/attempts/001/diagnostic.json)。各目录保留 request、response、messages、input、model_input、校验与耗时记录。

## 2. 核心结果

| 检查项 | A：原版 v3 同期基线 | B：可见比较 | B：最终 Knowledge |
|---|---|---|---|
| R05 正负残差对应动作反转 | 明确写出两侧映射 | 识别相反映射 | 保留反转与非隔离归因，映射细节比 A 少 |
| R05 Parent 已有跨格延续 | 概括为整笔放第一格，遗漏正残差分支 | parent_behavior 写出正残差逐格减；shared_and_different 又泛化成一格即停 | 第一格即停正确限定为负残差，但未保留 Parent 正残差延续 |
| R05 上下限是否实际读到 | 将成功读取当成事实 | 同样过强 | 同样过强，未保留 0/∞ 回退的不确定性 |
| R06 name/code 优先级及回退条件 | 提到 Candidate 优先 code；无完整 Parent 对照 | 提到 Parent name-or-code、Candidate 两张表；没有比较命中条件与优先级 | 提到 Candidate code-then-name；仍缺 Parent 优先级和回退条件 |
| R06 答案范围 | H2:H18 正确 | 错写 H2:H17 | 错误继续进入 Knowledge |
| R06 等分与等输出的区别 | 因果未定，但夹杂未经证实的两表分隔符实例 | 明确不推出相同工作簿 | 保留此边界 |

四个输出都只新增一个条目，revises=[]；没有替换历史条目，因此这次没有历史替换完整性结论。A/R05、B/R05 均 7 条 Knowledge；A/R06 为 5 条，B/R06 为 6 条。B 分别输出 9 对、8 对相关比较，符合沿用相关性筛选的实验约定，并非遗漏必填的全 15 对表格。

## 3. R05：可以识别差异，但条件限定仍容易丢失

人工核对依据：[Parent P3](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/R05_evidence.md#p31)、[Candidate Q3](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/R05_evidence.md#q31)。原程序为：

| 条件 | Parent | Candidate |
|---|---|---|
| residual < 0 | 左到右找到首个非零格，整笔加上，不检查上限 | 右到左按下限逐格减 |
| residual > 0 | 右到左按固定下限 0 逐格减，可继续到下一格 | 左到右按上限逐格加 |

历史 v3 输出未保留这项反转。本次 A/R05 E1/K4 已明确写出 Candidate 正加负减、Parent 相反，并承认符号映射不是条款所规定的变化。由此可排除“这份输入下原版 v3 必然无法识别”的强判断。A 称其可能是 dominant contributor，仍是未经贡献拆分的假设，不是已确定的主要根因。

B/R05 P3/Q3 的 observed_and_unknown 和 E1/K4 同样保留反转及联合变化。这一项没有出现“可见比较识别、Knowledge 丢失”。但 B 的同一比较记录内部出现更有定位价值的问题：

1. parent_behavior 已写出正残差会 drains unit5..unit1 down to 0。
2. shared_and_different 却概括成 one cell then stop vs multi-column continuation。
3. 这个概括把仅适用于 Parent 负残差分支的行为扩大到整个 Parent 程序。

这说明字段存在并不保证条件对齐；局部摘要仍会丢掉自己刚写出的分支限定。B 的 condition 也是“带约束调整整行残差”的任务说明，没有按正、负残差拆成不同决策条件。

两组仍将 Candidate 读取实际边界作为确定事实。程序包含未找到边界时的 0/∞ 回退；预览没有相关约束行，运行没有报告实际边界，评分通过不能独立证明走过哪条边界读取分支。识别反转不缺事实，确认边界激活和分离贡献仍缺事实。

## 4. R06：比较产物已经不完整，不只是最终压缩

人工核对依据：[Parent P15](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/R06_evidence.md#p151)、[Candidate Q15](../../../../../artifacts/methods/v25/analysis/replay_v3_deepseek_r05_r06_clean_20261028_001/R06_evidence.md#q151)。

- Parent：库存与订单都先取 name，name 为空才取 code。name 非空但没命中库存时，不尝试 code。
- Candidate：建立 code/name 两个库存表；订单先查 code 键，键不存在才查 name；实际命中的键用于分组和 FIFO 库存消耗。
- 因而差异包含池的构造、键的选择优先级和回退触发条件，不只是订单号是否带后缀。

A/R06 E1/K4 本次补充了 Candidate looked stock up by item code and by item name, preferring the code key，但没有对照 Parent 的 name 优先，也没有写出“name 是否为空”和“code 键是否命中”的回退差别，判为部分识别。

B 的 parent_behavior 提到 name-or-code，candidate_behavior 提到按 code/name 建表；到 shared_and_different 却将两侧合并为 order plus item，并把 distinguishing difference 指向是否保留客户型号后缀，还明确联系到 Identifier-Keying clause。优先级和回退条件没有在这份比较中形成完整关系。最终 E1/K4 虽补出 code-then-name，仍未补齐 Parent 对照。

因此，本次观察到的是“比较内部的抽象已经抹平重要区别”，没有观察到完整对照先出现、再只在 Knowledge 阶段消失。不能据此推断模型内部究竟有没有完整理解；能定位的是可见产物在哪一层已经不足。

两侧评分都是 15/17，错 H12/H13。B 正确强调等分和同错误坐标不等于相同工作簿；但把答案范围错写为 H2:H17，且这个错误从比较进入 Knowledge。原输入、Candidate 循环上界及正确评分分母对应 H2:H18。结构校验通过不是事实准确校验通过，本实验没有调用 Verifier 修正这些错误。

## 5. 其他观察与限制

- 正向信号：B/R05 的 P1/Q1 比较和 E1/K2 保留了 Candidate 更广的数值解析，包括括号负数；A 未保留这项竞争差异。B/R06 的 P1/Q1 也明确保留是否实际触发分隔符归一化未知。这些是具体改善，不是稳定收益估计。
- 新的或残留概括问题：A/R06 E1/K3 断言三张源表名都已在目标出现、Parent 没追加任何行；原 Parent stdout 为空，有限预览不足以支持这个断言。B 保留 Q14 自报 appended=3998 的来源，但又把 Jack 的 provenance 扩展到目标 rows 2–3999，有限预览同样不能支持整段都有该值。
- 四个请求均有原始事实、相同调用参数、干净初始消息。不存在模型拿到我们上一轮答案或人工目标清单的因素。
- 每个条件只有一次，temperature=1.0；存在抽样差异。A 与历史相同输入的不同输出已直接显示这种不稳定。没有隔离 Diff/Plan 的因果作用，没有测试 Memory 移除或单配对上下文，也没有更换模型。
- B 改变了输出结构与写作负担，不能当成对原版内部思维的直接观测，更不能由 B 的成功倒推 A 原本已知道。

## 6. 资源与执行过程

| 条件 | Prompt tokens | Completion tokens（含 reasoning） | 最终正文词数（空白分词） | 耗时秒 |
|---|---:|---:|---:|---:|
| A/R05 | 82,153 | 30,581 | 856 | 184.1 |
| B/R05 | 82,300 | 29,396 | 2,342 | 202.8 |
| A/R06 | 96,552 | 21,675 | 855 | 157.8 |
| B/R06 | 96,699 | 37,053 | 2,636 | 264.1 |

详见 [metrics.json](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/metrics.json)。B 增加可见正文，但总 completion 的变化不一致；R05 降低、R06 升高。各请求缓存命中不同、后台并发和服务延迟未控制，不能用单次耗时估计稳定成本或速度差异。

启动时默认 Python 缺 openpyxl，改用已有 spreadsheetbench 环境。初版 B 包装器重复执行 timeline 投影，两个 B 作业都在调用 API 前失败（request_invoked=false）。保留在 B/R05 和 B/R06 的 pre_request_failure/。随后新增隔离修正版包装器，保留初版脚本和原冻结清单；只跳过已完成的投影，实际发送消息与预先冻结 B 请求完全相同。见 [修正记录](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/wrapper_correction.json)、[修正版脚本](../../../../../artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/run_diagnostic_fixed.py)。没有因此增加 API 调用或更改实验条件。A 原生加载验证通过；B 按隔离 contract 复核，不能直接用生产 load_replay 加载其额外 envelope。

复核与重新导出（不调用模型）：

```sh
/Users/didi/miniforge3/envs/spreadsheetbench/bin/python artifacts/methods/v25/analysis/replay_comparison_diagnostic_20261028_001/summarize.py
```

## 7. 原因判断与下一步

已支持：关键程序可见；原版有时能够识别重要竞争差异；R06 比较仍停留在任务/条款层面的粗粒度概括；R05 存在将单一分支扩成全程序的条件丢失；显式字段不足以自动避免这些问题。

待验证：Diff/Plan 是否使解释过早围绕修改条款收敛；全批次长上下文是否使细粒度比较不稳定；模型在较小上下文是否仍不能稳定完成这些语义对照。当前结果不支持把原因全部归为模型弱、Memory 错误引导或最终压缩。

不建议立即把 B 设为默认或据此编写更长的 Replay prompt。下一项更有区分力的小实验是单配对上下文消融：沿用本次 B 判断和输出约定，分别只保留目标配对的当轮 pairs/runs，保留对应完整共享输入、Parent、Diff、Plan 和原 Memory；不提示目标差异，不先修改比较规则。它只检验减少其他当轮轨迹是否让条件对照更完整，单次仍不证明稳定收益。若缩小上下文仍出现相同的“item 泛化”或分支条件丢失，再优先局部调整比较单位和依赖链追踪；若明显改善，优先考虑配对级比较与批次经验整合的分工。需要比较识别率时，再做匹配的重复样本。

以上下一步仅为建议，本轮未执行。默认 Replay 仍为 v3 / 输入视图 v4，Preconditioner 仍为 v7。
