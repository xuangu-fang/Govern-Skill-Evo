# v18 Diagnosis Prompt v2 固定输入语义 Pilot

日期：2026-09-19。Prompt：`v18-group-diagnosis-2`，SHA-256 `263598dd617827b9c972acf57dbca81664882c76c5ab1431b11d9813d26f5ff8`。

## 目的与边界

本次只验证 v2 的 learner 语义转换：未知是否变成额外义务、候选经验是否被强化、Analysis 的条件/范围/epistemic status 是否在 Gap 中保持。历史 benchmark/runtime 终止 artifact 原样保留，但其解释不参与评分，也不围绕它修改 Prompt。

输入共 5 组：R2 g5、R2 g3、R3 g6 三组历史 Evolution learner payload，以及两个独立构造开发样本。历史输入逐文件摘要绑定并复验原 v17 请求和响应，v2 收到的 payload 与历史输入一致；不运行 Agent、User、Grouping、Compiler、Editor 或 Monitor。构造样本及人工 rubric 固定于 [constructed_cases.json](../experiments/configs/v18_diagnosis_pilot_002/constructed_cases.json)，明确标为开发样本，不进入正式学习，也不与真实 Evolution 指标混算。

入口为 `scripts/run_v18_diagnosis_v2_pilot.py`，产物位于 [v2 pilot 目录](../artifacts/v18_diagnosis_v2_pilot_001)。每组 deepseek-v4-pro 一次调用，temperature=0、reasoning_effort=high、24,000 completion tokens、300 秒 timeout、SDK/application retries=0。没有输出修补、选择或重跑。

## 运行结果

| 输入 | 来源 | VALID | Gap | 核心语义评估 |
|---|---|---|---|---|
| R2 g5 | 历史定价 | 是 | 1 MISSING | PASS |
| R2 g3 | 历史订票/人数/姓名 | 是 | 1 MISSING | PASS |
| R3 g6 | 历史定价 | 是 | 2 MISSING | PASS；历史终止 artifact 排除评分 |
| constructed-needs-revision | 构造开发样本 | 是 | 1 NEEDS_REVISION | PARTIAL_FAIL |
| constructed-should-remove | 构造开发样本 | 是 | 1 SHOULD_REMOVE | PASS |

5/5 通过结构与引用验收，产生 6 个 gap。Provider 报告总计 220,888 tokens；这是 token 使用量，不是费用估算。逐组调用耗时和 usage 见 `summary.json`，原始请求、响应及验收结果位于各组目录。

按预先确定的核心标准：

- 未新增无依据义务：4/5 通过；
- 候选经验没有强化为普适强规则：5/5 通过；
- 条件、适用范围和 epistemic status 得到保持：5/5 通过。

完整人工评分保存在 [semantic_assessment.json](../artifacts/v18_diagnosis_v2_pilot_001/semantic_assessment.json)。结构 VALID 不参与替代语义判断。

## 历史输入观察

R2 g5 从 v1 的两个 gap 收敛为一个定价 gap。Analysis 和 Gap 都保留 horizon 使用原预订价、summit 在已观察案例中对应当前可用价的关系，并明确这是工具契约未声明的候选经验。v1 中“接受实际金额可能不同，否则转人工”的 summit guard 没有再次出现。

R2 g3 保留 5 人单订合规、6 人单订不合规、7 人拆 4+3 合规的对照，但不再把它写成已证明的普适“每单最多 5 人”。Gap 明确 exact numeric boundary 未知。T024 仍留在 Analysis，没有生成姓名外观审查；行李机制不完整也没有生成额外规则。

R3 g6 的定价 gap 保留同一渠道条件和经验确定性。原始输出另有“确认后调用更新工具”的 gap；它关联旧 Simulator artifact，按正式职责边界不计入 v2 核心评分，也不作为继续 patch Prompt 的依据。原始输出未删除或改写。

## 操作边界观察

`constructed-should-remove` 正确选择 SHOULD_REMOVE。它引用整块当前规则，说明数字姓名禁令与可见 policy 冲突、两条成功工具结果否定其核心方向、缩小数字范围也无依据，并保留真正有效的 exact supplied fields 与确认要求，没有换成另一种姓名外观检查。

`constructed-needs-revision` 正确选择 NEEDS_REVISION，并保留“使用当前流程的成功 lookup 作为库存核对”的有效核心，去掉了必须做第二次独立核实的要求。但 Gap 仍声明：没有成功 lookup 或 lookup 返回 unavailable 时应转人工。来源 Analysis、policy 和轨迹没有证明转人工是必要动作，因此它保留了一个无依据 escalation obligation。该项按核心标准记为 PARTIAL_FAIL；不因操作类型正确而判为通过。

## 结论

v2 对三组历史 learner 问题有明显改善，并能在两个构造样本中区分 REPLACE 与 DELETE 的意图。但现有保守条款可能在 NEEDS_REVISION 时被缩小范围后继续保留，即使证据只支持删除该条款而不支持它在剩余条件下仍有必要。这说明语义保持仍有一个明确残留点。

本次结果支持继续实现确定性的 Compiler DELETE：Compiler 不应承担这项语义判断，只映射已验收 gap。同时，在进入正式 v18 campaign 前应决定是否用一个小版本 Prompt 调整来约束“修订时，目标规则中保留的限制也必须有证据支持”；若调整，应升级 Prompt 版本并只做定向回归，不能修改或择优重跑本次输出。

一次调用和两个构造开发样本不能证明稳定性或总体成功率。本次没有 Candidate、Monitor 或 Gate 结果。
