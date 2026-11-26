# v28.1 Preconditioner 修改说明

日期：2026-11-03。状态：第三步完成，第四步联合审查后明确联合编辑的归因不确定本身不能作为 KEEP 依据，详见 [联合审查报告](PROMPT_REVIEW.md)。核对记录已更新至当前文本；尚未接入运行器，未执行模型调用。

新版唯一编辑位置：[prompts/preconditioner.md](prompts/preconditioner.md)。基线：[baseline/prompts/preconditioner.md](baseline/prompts/preconditioner.md)。逐行对照：[preconditioner.diff](preconditioner.diff)。后续接线使用新版文本，不覆盖 v28 原 Prompt 或历史副本。

## 审核重点

主要修改三节：历史编辑与响应的解释、Direction／Scope／Coordination、每项 Original 的动作选择。其余输入、执行证据、Memory、精确 patch、引用、Checks 契约及输出结构保持原文。

| 维度 | 新版要求 |
|---|---|
| Direction | 区分对象／关系错误、答案边界和参考形式差异；核对相对 Parent／基础协议的决策增量；关系改变不能仅由局部形式纠正推出 |
| Scope | 分开判断方向、适用范围和强度；可见条件需要支持所选对象、关系或粒度；相似题面、主题及单题参考偏好不足以确立迁移 |
| Coordination | 新优先级需要行为依据，不能仅为消除文字冲突而设立；相关旧条款过宽时，在 Original 的指令中明确修订它，避免叠加覆盖规则 |

协调仍限于当前 Original 问题及必要依赖。Preconditioner 的 patch 对象始终是 Original Update 文本；对 Parent 的实际修改由 Editor 完成。禁止新增独立修复、拆并 Update ID 或直接编辑 Parent。

## 判断落实为动作

| 动作 | 必须落实的内容 |
|---|---|
| KEEP | 解释整项提案的实际触发条件、行为和强度为何合理，必要时包括优先级与 fallback；不能只认可主方向或宣称 Memory 没有反例 |
| 修改 | patch 中真正调整条件、行为、优先级或相关条款修订要求；支持的部分在同一 adjustment 中保留；不能只改理由或 Checks |
| 撤回 | 缺少合理迁移依据且无法在原问题内形成有用修正，或与现有能力的冲突无法妥善解决时使用 `to=[]`；解释为何限定修改不足，并处理依赖及 Checks |

不设置撤回比例，不要求每项都修改，不设 Update 数量或 Skill 长度限制。缺少历史、多例证据或事先验证，不自动导致撤回；合理的探索性条件偏好仍被允许。

必要条件必须出现在最终 Update 文本。`change` 描述实质动作，`reason` 解释依据；Editor 不读取 adjustment 的理由，不能期待它将理由中的谨慎措辞转化为行为边界。

## 历史证据如何影响动作

- **收益：** 支持共同条件下尝试某方向，不自动支持扩大范围或提高优先级。
- **退化／反例：** 相关证据支持修正时执行修正；保留时解释原条件已排除该反例、决定答案的条件有实质区别，或联合编辑的归因不确定为何仍允许保留当前提案。不能只写泛泛的不确定声明。
- **未改善：** 区分没有适用机会、可见未采用、可见采用但无改善、采用不可观察；既不能称为成功，也不能一概证明规则无效；不能据此不断重复已有指导。
- **历史不足：** 不自动撤回；没有记载反例也不等于可以扩大适用范围。

## 语义审查

这些是对指令含义的人工审查，不是模型输出测试，也不使用真实 Test 题作为 Prompt 示例或夹具。

| 情形 | 新版要求 |
|---|---|
| 历史支持局部方向，Original 却覆盖整个题型并设最高优先级 | 分别论证范围与优先级，依据不足时在 patch 中收窄或降强度，不能只保留主方向 |
| Original 的边界已经排除一个历史反例 | 可以 KEEP，但说明决定答案的条件差异，避免仅说“不同题目” |
| 观察到相关退化，理由也认为应限制触发条件 | 修改 Update 中的触发条件；只改 reason／Checks 不算落实 |
| 历史未改善，但没有适用机会或采用不可观察 | 不自动判定方向无效，保留不确定性并判断是否存在合理增量 |
| Parent 的宽规则与当前提案冲突 | 在相关 Original 中明确要求修订 Parent 的条款，不能仅无依据地提高新规则优先级 |
| 提案无法获得合理迁移依据，限定后也无有用行为 | 撤回并协调依赖；若全部撤回则按原契约处理空有效计划和 Checks |
| 单例支持一个合理的条件偏好且没有重大冲突 | 可以 KEEP，无需为了展示审核而修改、撤回或要求额外 Actor 调用 |

## 保持不变与核对结果

[preconditioner_checks.json](preconditioner_checks.json) 记录文本核对。下列部分与基线逐字一致：

- 开头职责、SearchQA 执行证据边界、Actor 基础协议与 32,768 预算。
- Knowledge Only 历史视图及 Frozen proposal 输入边界。
- Exact Update patches、Explicit references and Checks、Exact output contract 三节。

因此继续使用 `parent/plan/runs/memory` 输入、`adjustments/checks` 输出，以及 `target/focus/change/reason/to`；KEEP／patch／撤回和 Checks 继承／替换／清空语义不变。没有新增字段、解析器、调用阶段、工具或哈希门槛。

第三步没有修改 Diagnosis；第四步对两个独立 Prompt 做了三处澄清。其他模块、执行代码和正式配置仍未修改。静态核对只确认文本范围与契约保留，不证明真实模型会落实更好的审核，也不替代后续 Effective Plan → Editor 完整离线验收。

两个 Prompt 的联合差异审查已在第四步完成。实际接线、完整离线验收与实验启动仍属于后续步骤。
