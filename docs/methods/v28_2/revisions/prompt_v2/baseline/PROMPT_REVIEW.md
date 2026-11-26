# v28.2 第 1—3 步联合审阅

> 历史审阅记录：以下保留第 1—3 步交付时的状态与结论。第 4—5 步实现及离线验收见 [IMPLEMENTATION.md](IMPLEMENTATION.md)；五份提示词原文未改变。

日期：2026-11-03（Asia/Shanghai）。范围：设计、合同、五份提示词及其来源差异。完成文本审阅和本地静态核对，尚未实现或执行 v28.2。此次没有真实模型响应、训练或 Test 结果；不据此声称新提示词已改善判断。

## 1. 资源与继承关系

| 模块 | 新机制文本依据 | SearchQA 适配依据 | 差异 |
|---|---|---|---|
| [Grouping](prompts/grouping.md) | 当前 v29.2 的全批组织职责、共享输入、引用列表 | v28 Grouping 的 context/实体/关系/限定条件比较 | [方法来源差异](diffs/grouping_from_method.diff) |
| [Diagnosis](prompts/diagnosis.md) | 当前 v29.3 的无 Checks、行为粒度、迁移理由、完整条件 | v28.1 的实体/关系、答案边界、参考形式与决策增量分析 | [方法来源差异](diffs/diagnosis_from_method.diff)、[v28.1 差异](diffs/diagnosis_from_v28_1.diff) |
| [Preconditioner](prompts/preconditioner.md) | 当前 v29.3 的历史准确性、Scope、全文动作和编译 | v28.1 的方向/范围/强度区分、优先级理由和相关旧规则修订 | [方法来源差异](diffs/preconditioner_from_method.diff)、[v28.1 差异](diffs/preconditioner_from_v28_1.diff) |
| [Editor](prompts/editor.md) | 当前 v29.2 的一 Update 一 patch、共同定位及选择性组合 | SearchQA 基础协议、question/context 输入与单轮约束 | [方法来源差异](diffs/editor_from_method.diff) |
| [Replay](prompts/replay.md) | 当前 v29.2 的一翻转事件一 Knowledge、唯一关联或 null | SearchQA EM/F1、完整 context、实体/关系与回答边界 | [方法来源差异](diffs/replay_from_method.diff) |

完整来源路径和原 Prompt 版本见 [source_map.json](source_map.json)。差异用于审阅，不是运行时 patch；提示词当前只存在于本目录，没有同时复制到 src。

## 2. v29.3 优化核对

| 优化 | 审阅结论 |
|---|---|
| 能分别决定去留的行为用不同 Update | Diagnosis 原文保留；不把每行或每句话当作独立 Update |
| 依赖、例外、优先级与行为保持完整 | Diagnosis 保留；Preconditioner 撤回时协调剩余要求；Editor 不偷改策略 |
| 多个独立 Update 可同轮联合测试 | 保留当前 v29.3 措辞；没有恢复早期“共同测试理由”要求，也不因联合测试合并 ID |
| 迁移关系而非类别/词语/长度相似 | Diagnosis 的理由与 Update 边界分工保留；增加 SearchQA 的实体/关系/粒度判别 |
| 轮次事件、Update 关联、Gate 决定区分 | Preconditioner 的 Historical Memory by round 段落与当前 v29.3 逐字一致 |
| null 关联仍可能有相关内容 | 保留适用条件/保护风险的比较价值，不转写为某条 Update 的已归因收益/伤害 |
| 非空关联不等于因果证明或强证据保证 | 保留“Replay 已记录的归因判断”，要求结合正文依据和限制判断 |
| 没有关联或 Defer 不等于未改善 | 只有历史内容实际报告非改善/退化，才作为该类比较前提 |
| Scope 的例外应能区分相邻情形 | 保留；将可用输入适配为 question/context/自身回答，不要求问题必须出现 full/exact |
| 保留合理探索 | 不要求每个覆盖情形都有成功样本，不设撤回比例/Update 数量/Skill 长度上限 |
| Editor 预算提升 | 设计值为 32,768；SearchQA Diagnosis/Preconditioner 原有 65,536 不降低 |

## 3. 跨模块传递审阅

1. **Grouping → Diagnosis**：均使用当前完整 Parent 批次；不因为 Replay 只看 EM 翻转而提前过滤成功例或无翻转例。Grouping 仅组织证据。
2. **Diagnosis → Preconditioner**：没有 Checks；传递冻结 Plan 和其直接引用的完整 runs，不传 Diagnosis reason 或 Grouping 描述。scope-defining 支持、成功例和反例写入 basis，行为条件进入 text。
3. **Preconditioner → Editor**：只传完整 Parent 与 Effective Plan 的 goal、Update id/text；不传 basis、Memory 或 adjustment reason。因此 REPLACE 必须是完整行为文本，不能把关键条件留在 reason。
4. **Editor → Candidate**：一 Update 一 patch；同一原始 Parent 定位；任一 null 停止完整构造；全空 patch 不制造 Candidate。共同执行没有变为逐 Update 消融。
5. **Candidate → Replay**：完整配对验证后才筛选 EM 翻转，保留原 P/Q ID；F1-only、答案文字变化但 EM 不变均不产生事件。无翻转由程序跳过模型并产生空结果。
6. **Replay → Gate**：每题仅一条 Knowledge，只能关联一个非空 patch 的 Update 或 null；Gate 从真实 pair 的 EM 方向计数，不信任正文自报的“收益数”。历史和 F1 不投票。
7. **Gate → Memory/下一轮**：只合成 Retain patches；所有 Effective Updates 的决定和全部事件（包括 null）入历史。新组合不能继承完整 Candidate 分数；下一轮 Parent 为实际 Selected Skill。
8. **Memory → Preconditioner**：按轮保留完整历史 Effective Update 文本及决定。无事件轮仍可被看见；不提供历史 raw context/runs；不允许用旧报告中的 P/Q 引用取回原记录。

## 4. 本轮已处理的迁移问题

| 问题 | 已落实的处理 |
|---|---|
| 机械替换 benchmark 名会留下图片不可见假设 | 四个读证据模块明确：完整当前 context 可见；可以核对文本，不能由此推断 Actor 已使用该内容；历史 raw context 仍不可见 |
| DocVQA “删除冠词→得分翻转”例子不适用于 SearchQA | Replay 改成合成的“补回问题要求且 context 支持的限定成分”例子；本地原生 scorer 核对冠词去除本身不会改变 EM |
| 旧整包 Gate 文字易混入公共背景 | 四个读证据模块全部改为 EM 翻转与 Update 选择，去除严格总成功数提升规则；合同明确混合 G/L 为 Defer |
| DocVQA hard 严格整数验证会拒绝合法 EM 浮点 | 合同明确支持实际原生 0.0/1.0，拒绝 bool；G/L 仍是整数计数 |
| v28 源模板可能出现 49,152 Actor 预算 | 所有五份 Prompt 使用 v28.1 batch30 的 32,768；base protocol 与实际 SearchQA 文件逐字比较 |
| v29.2 摘要型 Memory HEAD 与无哈希边界冲突 | 设计顺序提交 ID、原文/结构校验、来源重算和同一 HEAD 原子发布；后续需专门实现及恢复测试 |
| 字符 patch 能组合不代表行为依赖被验证 | 合同和设计说明明确程序的结构能力边界；没有增加自动依赖求解、自动修复或额外 Actor 调用 |
| 引用修复可能被误解成放宽证据范围 | 合同保留普通标签/正式引用区别与 slash 列表规则；每个模块、每条事件仍单独检查权限 |

## 5. 静态检查与解释范围

检查结果见 [design_validation.json](design_validation.json)。检查包括五份 Prompt 的准确 base protocol、Actor 预算、旧 benchmark 残留、输出 JSON 字段、输入字段、关键继承段落、共享/引用说明、差异文件、文档链接、原配置预算/初始化和保存的任务 ID 顺序。

直接比较确认：

- Diagnosis 的五段 v29.3 关键迁移/粒度/联合测试/格式说明逐字保留。
- Preconditioner 当前 v29.3 的历史解释段落及全文动作编译段落逐字保留。
- Editor 当前 v29.2 的 patch 格式和 Update 映射/组合主体段落逐字保留。
- v28.1 配置批次与其保存的 schedule 一致：20×30、600 个唯一优化 ID；保存的 Test 顺序含 1,400 个唯一 ID，且与优化 ID 无交集。未读取 Test 题正文或参考答案。
- 使用本地现有 scorer 和两组合成字符串核对：删除冠词本身不造成 EM 翻转；词序变化可保持 F1=1 而 EM=0。原生 EM 返回 float。

本轮执行的是文档静态核对与现有纯评分函数的小型语义核对，**不是 v28.2 离线运行验收**。未调用新 Gate、Memory、恢复或训练链路；这些代码尚不存在。JSON 例子仅验证形状，不冒充完整跨阶段执行证据。

## 6. 给后续实现的明确交接

可以以本目录作为第 4 步的输入。运行接线时必须落实 [CONTRACTS.md](CONTRACTS.md) 的字段、状态分支、身份检查和发布语义，并直接引用本目录提示词；实现任何偏离时先同步合同与文本，再验证。

优先验证最容易改变方法含义的边界：mixed G/L 不取净收益、null 事件不投票、F1-only 不入 Replay、没有事件不代表无效、空 patch 与 null patch 不混淆、Selected Skill 不继承未发生的执行成绩、必要条件不会只停留在 reason。其后验证无哈希恢复与原子发布、请求额度，以及 SearchQA 原 Actor/评分/数据行为。

本次交付不启动第 4 步实现，不创建可运行配置、campaign 或监督任务。
