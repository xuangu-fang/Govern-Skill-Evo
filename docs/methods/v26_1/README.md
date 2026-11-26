# OfficeQA v26.1 完整设计稿

后续正式训练和评测见[实验归档入口](../../../experiments/methods/v26_1/v26_1_officeqa_train74_roles_20261105_202041/README.md)。

设计日期：2026-11-04，Asia/Shanghai。当前状态：**独立运行链路已实现；真实训练与真实 Test 未启动**。实现与离线验收见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。本目录规定后续独立 v26.1 的方法、四份完整 system Prompt、交接与证据合同、固定实验参数和验收标准。`experiment_plan.json` 是设计参数，不是旧 CLI 可以读取的可执行配置；来源快照中的 Python 文件仅供核对。

目标是在 OfficeQA 原有多轮工具执行条件下，让提案、实际修改、观察事件和采纳决定逐项对应，检验 Update 级选择是否改善最终任务表现。方法沿用 v29.4，不以已有其他 benchmark 的提升作为 OfficeQA 效果保证。

## 阅读入口

| 内容 | 文件 |
|---|---|
| 字段、交接、证据权限、编辑、Gate、Memory、停止与恢复 | [CONTRACTS.md](CONTRACTS.md) |
| 四份独立完整英文 Prompt | [Diagnosis](prompts/diagnosis.md)、[Preconditioner](prompts/preconditioner.md)、[Editor](prompts/editor.md)、[Replay](prompts/replay.md) |
| 数据、模型、预算、重试、Test 与报告口径 | [EXPERIMENT.md](EXPERIMENT.md)、[experiment_plan.json](experiment_plan.json) |
| 后续实现与实验验收矩阵 | [ACCEPTANCE.md](ACCEPTANCE.md)、[acceptance_matrix.json](acceptance_matrix.json) |
| 方法保留与 OfficeQA 适配联合审阅 | [PROMPT_REVIEW.md](PROMPT_REVIEW.md) |
| 来源映射、原文副本与逐模块差异 | [source_map.json](source_map.json)、[baseline/README.md](baseline/README.md)、[diffs](diffs/) |
| 本次设计静态检查结果 | [design_validation.json](design_validation.json) |

## 方法来源与版本关系

v29.4 从 v29.2 删除独立 Grouping，由 Diagnosis 直接比较完整 Parent 批次；其余方法主干仍来自 v29.2。它没有整体继承 v29.3 的额外提示词修订。SearchQA v28.3 和 LMB v27.1 是这一主线的 benchmark 迁移参考，不是新的方法规范来源。

| 来源 | 本稿采用内容 | 不随迁移引入 |
|---|---|---|
| v29.4 Diagnosis／Preconditioner | 全批直接诊断、具体行为增量、完整有条件 Update、D/S/C、KEEP／全文 REPLACE／WITHDRAW | v29.3 或 v28.2 Prompt v2 的额外组织与审查段落 |
| v29.4 沿用的 v29.2 Editor／Replay／Gate／Memory | 每 Update 一个 patch、联合 Candidate、翻转事件、选择性组合、追加 Memory | 逐 Update 独立 Actor、重组后额外验证、整包收益兜底 |
| v28.3／v27.1 迁移合同 | 分离 benchmark 事实与通用方法、原生 EM 数值适配、显式来源与独立版本隔离 | SearchQA 单轮 context、LMB 标签或数学符号解析特例、各自预算 |
| 已完成 v26 正式实验及公共 OfficeQA Actor | 原问题、来源语料、初始页面、工具、评分、正式多轮事实、无标准答案视图、无损编码、请求/工具恢复 | 旧 Grouping、Checks、整包 patch/Gate、历史 Knowledge 改写 |

实际 OfficeQA 基线为 `experiments/campaigns/v26_officeqa_official_train74_epoch1_20261029_230230`。其运行语料是 revision `763a8366abf2a3605c381d53586d844dc60fa756` 的 release；旧文档的 `prepared_v2/corrected_v2` 路径和旧 revision 不作为本稿实验来源。

## 正常闭环

```text
完整 Parent 批次执行
  → Diagnosis：parent + 全批正式 runs
  → Preconditioner：parent + Original Plan + 引用的完整 runs + Memory
  → Editor：parent + goal + Update id/text → 每 Update patch
  → 完整 Candidate 同批独立执行
  → 验证全部配对，再选择 EM 翻转任务
  → Replay：每个翻转任务一个事件，关联一个 Update 或 null
  → Gate：逐 Update 计算 G/L，只组合 Retain patches
  → 追加 Memory + 原子发布 Selected Skill → 下一轮 Parent
```

四个模型模块之外的配对、评分、选择、Memory 提交均为确定性程序职责。没有替代 Grouping 的分类报告、Group ID、Checks、新 Verifier/Repair 或 Stage0。旧 v26 虽保留七模块接口，但正式配置 `knowledge_review=disabled_v1`，本次不应被描述为取消了当时实际启用的两次审查调用。

## OfficeQA 必须保持的边界

1. 方法模块仅获得问题、实际初始消息、普通 assistant 内容、工具调用/返回、最终答案和 EM/F1。标准答案只由评分器访问；不得复制其他 benchmark 的 `reference_answers` 或正确选项字段。
2. `attempts` 表示被接受的模型轮次；正式请求历史与包含临时纠错的 HTTP 请求审计不同。同一响应的所有工具调用先于该响应的任何工具返回；不能倒置证据时序。
3. 工具仅为本地 glob/read/grep；最多24模型轮，最终回答占一轮；每轮六次总请求，不是整题六次。不新增程序执行工具、在线搜索或评分反馈补答。
4. 允许分析可见的检索行为、表格/字段选择、时期与财年口径、单位与操作数、计算陈述及提交形式；这些是任务解释，不是新增分类 schema。工具文本能证明返回内容，不能证明原扫描件正确或 Actor 内部理解。
5. 沿用 OfficeQA 全轨迹无损编码和原生评分。EM 翻转驱动事件；F1、检索成本或回答变化本身不投票。编码不摘要、不截断、不扩展引用权限。

## 固定实验选择

优化池为原 Train 50 + Validation 24，原顺序 `10/10/10/10/10/10/10/4` 单遍；Test 为原172题。使用原887字符初始 Skill 和空 Memory，不继承最终 Skill、历史 Memory、请求或执行缓存。Actor 默认32,768，训练 UID0007 两侧65,536；Test 全部32,768。四方法模块各32,768，超时300秒，Train/Test workers均4。Editor 从旧16,384提高，属于明确实验变量。

首次、技术错误、length 和可纠正结构错误共享每调用六次总额度；保留 OfficeQA Actor 与方法传输各自原错误分类，不用另一个 benchmark 的策略覆盖。无外层自动重启、无技术错误免计、无补测、无自动预算提升。训练与 Test 独立启动；本次没有授权或执行任一阶段。详细配置与可比性见 [EXPERIMENT.md](EXPERIMENT.md)。

## 结果解释与主要风险

DocVQA v29.2 为326/374，v29.4为323/374；SearchQA v28.3比v28.1多13/1400题。LMB v27.1在本次来源读取时尚无完整训练/Test汇总。这些记录支持方法来源与实验问题，不证明 OfficeQA 将提高，也不能单独识别删除 Grouping 的效果。

SearchQA v28.3 训练12个退化事件中11个没有 Update 关联，20轮有10轮 Selected 是本轮未执行的新组合。迁移时保留 null 的真实含义，报告未归因退化和新组合比例，不把它们解释为噪声或无风险。本稿不增加整包否决或重新执行来改变 v29.4 方法。

OfficeQA 每批最多10题、末批4题，单事件支持稀疏；更多可见工具行为是否提高关联可靠性仍是待检验假设。必要依赖须在完整 Update 中表达，patch 可组合不等于行为独立。持续失败、持续成功和 F1-only 变化不进入 Replay，但 Diagnosis 仍看完整批次。

独立实现与离线验证记录见 [IMPLEMENTATION.md](IMPLEMENTATION.md)；后续真实训练和独立 Test 仍须分别启动。离线合同正确、自然语言判断可靠和最终效果改善是三个不同验收结论。
