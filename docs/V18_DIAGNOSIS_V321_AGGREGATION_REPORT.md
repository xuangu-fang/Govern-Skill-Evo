# v18 Diagnosis 统一聚合边界回归

日期：2026-09-20。最终测试 Prompt：`v18-group-diagnosis-3.2.1`，SHA-256 `24d04f4ed6f8b7542633f7aea8f0745bbba1cd26fbd7be76cd436cddfa6bcfd6`。

## 预先冻结的统一 rubric

在修改 Prompt 前，新建 `experiments/configs/v18_diagnosis_pilot_005/`，冻结统一三态语义、逐关系判断后汇总的 group-level 规则，以及一对通用聚合对照。rubric SHA-256 为 `46543c046f046942d1bcfaa93cf209e05795e3eebaae605e41e593b28652b37a`。没有使用 Monitor 逐题结果或 Gate 转移数据。

统一规则要求：先独立判断组内可分离的经验关系；至少一个合法 gap 即为 ADDRESSABLE；unresolved 分支不移除合法 gap；排除一个动作不等于支持其补集；所有 Success/Compliance 都为真时不得仅因 Parent 未记录成功配方而制造 gap。

配对对照包含相同的可学习关系。第二个输入只增加一个没有替代依据的独立失败分支。两份输出应保留相同局部 gap 的条件、动作、范围和不确定性，新增失败只能进入 unresolved。

## Prompt 审查与最小修改

v3.1 已写有“混合组中不可学习问题不移除其他 gap”，但 ADDRESSABLE 仍以整组 observed problem 为中心，没有明确逐关系判断再汇总，也没有说明正向局部规律是否必须修复另一个失败分支。因此更新为 v3.2。

v3.2 首轮 13/13 结构 VALID、0 重试、362,211 tokens。配对对照通过，但 G02 仍为 NOT_ADDRESSABLE，G05 又把全成功/合规行为写成新规则；通用 stable-relation 还为没有替代动作的失败另建 warning gap。基于同一冻结 rubric，v3.2.1 仅澄清三点：全成功/合规组使用 NO_ISSUE；有问题的混合组可以保存不修复另一 unresolved 分支的正向局部规律；只有失败且没有独立限制依据的分支不能生成 warning gap。

Prompt 不包含 cedar、行李、保险、coverage、组编号或其他领域专项规则。Schema、引用校验、Compiler、Editor 和 Gate 均未修改。

## v3.2.1 真实模型结果

13/13 调用一次完成且结构、引用 VALID，0 重试，总计 350,037 tokens。

- 原六组 6/6 通过。G02 只生成观察到的正向局部顺序 gap，失败分支 unresolved；G05 为 NO_ISSUE。
- 聚合配对 2/2 通过。两份输出各有一个同范围、同动作、同有限确定性的局部 gap；新增 unresolved 分支没有产生额外 gap。
- 既有五类通用边界中四类通过。

完整评分见 `artifacts/v18_diagnosis_v321_pilot_002/semantic_assessment.json`。

## 尚未解决的 rubric 冲突

既有 `boundary-negative-only` 预设 NOT_ADDRESSABLE，但输入的 visible policy 同时规定只有在 applicable setting 已知时才调用工具，并明确没有来源提供该值。统一 rubric 又规定明确 visible policy 可以独立支持限制。v3.2.1 因而生成“不猜参数、不调用”的局部 gap，同时把正确替代值留在 unresolved。

这不是继续增删 Prompt 措辞可以一致解决的问题：若服从旧样本标签，会破坏“明确 policy 可支持限制”；若服从统一证据规则，就必须修订该旧对照的输入或 rubric。为避免让 Prompt 迎合混杂样本，先将其记为 `RUBRIC_CONFLICT`，不据此修改 Prompt。

## 冲突裁定与最终结论

随后在新调用前冻结 `experiments/configs/v18_diagnosis_pilot_006/`，将混杂样本拆成轨迹和工具完全相同、只改变 visible policy 的两个正交对照：纯 negative-only 不含独立限制依据；explicit-prerequisite 明确要求仅在用户提供参数时执行，并规定缺失时的响应。

Prompt 保持 v3.2.1 不变。两组均一次 VALID、0 重试、合计 17,890 tokens：纯负面组为 NOT_ADDRESSABLE、0 gap；明确前置条件组为 ADDRESSABLE、1 个窄限制 gap，替代参数保持 unresolved。评分见 `artifacts/v18_diagnosis_v321_boundary_resolution_002/semantic_assessment.json`。

最终有效语义语料为 14/14 通过：原六组 6/6，保留的旧通用边界 4/4，替换后的正交边界 2/2，聚合配对 2/2。Prompt v3.2.1 达到进入正式 freeze 的语义门槛。旧 `boundary-negative-only` 保留为历史审计，但因同时测试负面证据和明确 policy prerequisite，不再计入最终通过率。

本步不更新已有正式四轮 freeze，也不启动正式实验；现有入口继续因 Prompt 摘要漂移而拒绝运行。下一步应创建新的、不可覆盖的正式 freeze，并完成无模型预检后再启动四轮实验。

相关 v17/v18、历史 Pilot 与新增聚合/边界裁定测试共 550 项通过。v17 差异摘要与本步开始时一致。现有正式入口已实测因 `diagnosis_prompt_v18.py` 摘要漂移而拒绝启动。

本步实际进行了 28 次模型调用、0 重试，合计 730,138 tokens：v3.2 13 次、v3.2.1 13 次、边界裁定 2 次。所有失败与中间版本产物均保留，未覆盖历史审计。
