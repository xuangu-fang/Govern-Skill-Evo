# v18 Diagnosis Prompt v3 六组固定输入回归

日期：2026-09-20。Prompt：`v18-group-diagnosis-3`，Prompt SHA-256 `351cad7c15c3d998fbcf30259c8c254487d1cfa44990f44c962380ffe48b36c9`。

## 冻结与边界

修改 Prompt 前，已将端到端 Pilot 当前有效 G01–G06 的 learner payload、provenance、v2 validated output 和 validation 冻结到 `experiments/configs/v18_diagnosis_pilot_003/`。`cases.json` SHA-256 为 `7a988250d02dea5be1582da152d18c6613133ec4b2f3e36fd7bcf32691026357`；预写语义 rubric SHA-256 为 `261ad5ef144e8be4f6cb611e82d7a65b4920455197e77ba17d6b0f430165b4a4`。

冻结脚本只读取六组 Diagnosis 的 request、provenance、validated output 和 validation，不读取 Monitor 逐题结果、转移矩阵或 Gate delta。v3 输入摘要逐组与冻结 v2 输入一致。Schema、引用验证、Compiler、Editor 和 Gate 未修改。

Prompt 只增加两条通用原则：ADDRESSABLE 必须存在有证据支持且可实际执行的替代行为；无法证明覆盖、允许或适用不能自动产生核实义务、拒绝、停止、禁止或转人工。Prompt 不包含行李、保险、G03、G06 等专项规则。

## 运行结果

六组均一次调用完成，6/6 结构与引用 VALID，0 重试，总计 284,465 tokens。

| 组 | 角色 | 状态 | Gap | 语义评分 |
|---|---|---|---:|---|
| G01 | 非退化 | ADDRESSABLE | 1 | PASS |
| G02 | 非退化 | NOT_ADDRESSABLE | 0 | FAIL |
| G03 | 目标 | ADDRESSABLE | 2 | FAIL |
| G04 | 非退化 | ADDRESSABLE | 1 | PASS |
| G05 | 非退化 | NO_ISSUE | 0 | PASS |
| G06 | 目标 | ADDRESSABLE | 1 | PASS |

总计 4/6 通过；目标样本 1/2 通过；非退化样本 3/4 通过。因此 v3 当前结果不满足正式四轮实验前的语义门槛。

## 目标样本

G06 的问题已消除。v3 不再要求从可见 policy、工具或用户处证明隐藏保险覆盖并在无法证明时拒绝。输出改为一个由直接对照支持的局部经验规则：只覆盖已观察的 work-related 原因变体，以 T005 的合规拒绝和 T021/T026/T030 的非合规取消为依据；完整保险合同继续保持 unresolved。

G03 只部分改善。v3 正确保留人数规律，并把 business-class 行李问题留为 unresolved；但仍针对 basic-economy 的 2/3 件对照生成第二个 gap，要求不要提交 3 件编码并先澄清 allowance/limit。现有 policy、工具和合法交互没有提供隐藏映射，也不能确定正确的替代 tool arguments，因此该 gap 仍以未知机制产生否定性/澄清行为，按预写标准判 FAIL。

## 非退化样本

G01 保留 partner_direct 的局部 fallback 模式，并明确 consolidated 未决；G04 保留 horizon/summit 结算映射；G05 维持 NO_ISSUE，三组通过。

G02 退化。v3 正确指出 cedar 的失败只与 label 相关、没有直接观察到替代写入顺序，但因此整体判 NOT_ADDRESSABLE，删除了 v2 中带明确 tentative 和 context limit 的 cedar 局部执行假设。预写标准要求保留该已有候选规律，因此判 FAIL。这说明新增的“可执行替代行为”原则被模型解释得过窄，产生了整体保守化。

## 结论

v3 的第二条原则对 G06 有效，但第一条原则尚未稳定地区分两类情况：一类是完全缺少替代动作、会迫使 Agent 猜隐藏映射；另一类是存在可尝试的局部行为假设、只是机制和因果尚未完全确认。当前输出一方面在 G03 仍保留不可满足的澄清/禁止 gap，另一方面在 G02 过度删除候选规律。

因此不要启动正式四轮实验，也不要根据 Monitor 个案定向修改 Prompt。下一次小版本应继续只澄清这一通用边界：候选替代行为需要由组内观察或明确可枚举动作空间支持，但不要求替代行为已经在成功轨迹中直接执行；相反，若输出只能说“不要这样做、先澄清隐藏规则”，且没有可用信息源或具体替代动作，则不得生成 gap。应继续用同一六组冻结输入和同一预写 rubric 回归。

完整输出位于 `artifacts/v18_diagnosis_v3_pilot_001/`，人工评分位于其中的 `semantic_assessment.json`。

相关 v17/v18 回归测试 540 项通过。由于 v3 未通过语义门槛，正式 v18 freeze 未用 v3 重建；正式入口会因 `diagnosis_prompt_v18.py` 摘要漂移而拒绝启动，避免未验收 Prompt 被用于四轮实验。
