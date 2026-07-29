# τ-bench 中的 Policy 与 Compliance：项目立场说明

版本：2026-07-29  
状态：研究起点；后续应依据代码和实验更新  
上游核验：`sierra-research/tau2-bench` commit `1d244f5dca42944b67a379b44bfeb9f5748f189d`

## 1. 为什么需要这份说明

本项目要研究 Agent 如何从 trajectory 中学习 Skill，同时避免把“成功但违规”的经验固化下来。因此必须先回答：

> τ-bench 是否已经明确定义并评测了“Agent 是否遵守 policy”？

当前结论是：

> **τ-bench 提供了明确的自然语言 domain policy，也提供了明确的 task outcome reward；但它没有提供一个完备、独立、可直接作为人工 gold 的 trajectory-level compliance 定义。**

新版 `tau2-bench` 已经包含 LLM conversation reviewer，能发现一部分 policy violation。它是重要 baseline，但不等同于稳定、可复现、证据完备的 compliance ground truth。

这个区别决定了我们的工程任务：第一阶段不需要从零编造业务 policy，而需要把已有 policy 转换为可引用、可检查、可版本化的 compliance specification，并构建相应 verifier 与人工 gold。

## 2. 先区分三个概念

| 概念 | 含义 | τ-bench 当前支持 |
|---|---|---|
| Domain policy | Agent 应遵守的业务规则、权限、条件和流程 | 有自然语言文档 |
| Task success | 用户目标和目标环境状态是否达成 | 有正式 reward 实现 |
| Policy compliance | Agent 的完整过程是否满足所有适用规则 | 有 LLM review，但没有完备的独立 gold 定义 |

不能因为 Agent 看到了 policy，就认为 benchmark 已经精确测量 compliance；也不能因为 task reward 为 1，就推断 Agent 的过程合规。

## 3. Fact：τ-bench 已经提供自然语言 Policy

Airline 和 Retail 等 domain 都包含 policy 文档，规定：

- 什么条件下允许取消、修改、换货或退款；
- 敏感操作前要核验哪些信息；
- 不同账户、票种或支付方式适用什么规则；
- 哪些请求必须拒绝；
- 什么信息可以向用户披露；
- 哪些工具或操作只在特定条件下允许执行。

官方来源：

- [Airline policy（核验版本）](https://github.com/sierra-research/tau2-bench/blob/1d244f5dca42944b67a379b44bfeb9f5748f189d/data/tau2/domains/airline/policy.md)
- [Retail policy（核验版本）](https://github.com/sierra-research/tau2-bench/blob/1d244f5dca42944b67a379b44bfeb9f5748f189d/data/tau2/domains/retail/policy.md)
- [τ-bench repository](https://github.com/sierra-research/tau2-bench)

因此，第一阶段应尽可能复用原始 policy，避免改变 Agent 所面对的任务定义，也便于与官方 benchmark 和其他方法比较。

## 4. Fact：官方 Task Reward 主要是 Outcome Evaluation

官方 evaluation 文档说明，Airline、Retail 和 Telecom 默认使用：

```text
reward = DB reward × COMMUNICATE reward
```

它主要检查：

1. 运行结束后的数据库状态是否与目标数据库状态一致；
2. Agent 是否向用户传达了 task 要求的信息。

`evaluation_criteria.actions` 保存的是一条可以完成任务的参考 trajectory。通常情况下，它被用来在干净环境上产生目标数据库状态，并不意味着 Agent 必须逐步复现该路径。

只要 Agent 通过另一条路径得到相同最终状态，它仍可能获得完整 DB reward。Airline、Retail 和 Telecom 默认不使用 `ACTION` 作为 reward gate。

官方来源：

- [Task Schema and Evaluation（核验版本）](https://github.com/sierra-research/tau2-bench/blob/1d244f5dca42944b67a379b44bfeb9f5748f189d/docs/evaluation.md)
- [Task data model（核验版本）](https://github.com/sierra-research/tau2-bench/blob/1d244f5dca42944b67a379b44bfeb9f5748f189d/src/tau2/data_model/tasks.py)
- [Evaluator implementation（核验版本）](https://github.com/sierra-research/tau2-bench/blob/1d244f5dca42944b67a379b44bfeb9f5748f189d/src/tau2/evaluator/evaluator.py)
- [原始 τ-bench 论文](https://arxiv.org/abs/2406.12045)

因此可能出现：

```text
task_success = true
policy_compliance = false
```

例如，Agent 通过不允许的工具顺序或缺少核验的操作达到了正确最终状态。官方 task reward 可以正确评价 outcome，却未必完整评价产生 outcome 的过程。

## 5. Fact：新版有 LLM Conversation Reviewer

当前 `tau2-bench` 提供 `tau2 review`，其 LLM reviewer 会读取：

- domain policy；
- user instructions；
- reference actions；
- natural-language assertions；
- 完整 conversation trajectory。

它可以标记：

- `guideline_violation`；
- `revealed_info_early`；
- `missed_required_action`；
- `wrong_sequence`；
- tool call schema / argument error；
- `critical` 或 `minor` agent error。

其 prompt 允许把“即使任务成功，但违反重要 security/policy requirement”的行为标记为 critical。

官方来源：

- [CLI reference：`tau2 review`（核验版本）](https://github.com/sierra-research/tau2-bench/blob/1d244f5dca42944b67a379b44bfeb9f5748f189d/docs/cli-reference.md)
- [LLM reviewer implementation（核验版本）](https://github.com/sierra-research/tau2-bench/blob/1d244f5dca42944b67a379b44bfeb9f5748f189d/src/tau2/evaluator/review_llm_judge.py)
- [Review data model（核验版本）](https://github.com/sierra-research/tau2-bench/blob/1d244f5dca42944b67a379b44bfeb9f5748f189d/src/tau2/data_model/simulation.py)

这个 reviewer 对本项目很有价值，应作为一个直接 baseline 保存和评测。

## 6. Interpretation：为什么 Reviewer 仍不等于 Compliance Gold

当前 reviewer 至少存在以下研究缺口：

1. 输出中心是通用 conversation error，不是经过形式化定义的独立 compliance score；
2. 判断主要依赖 LLM，可能随模型、prompt 和运行变化；
3. policy 条款通常没有稳定的 rule ID；
4. 没有系统区分 obligation、prohibition、authorization、ordering、evidence 和 escalation；
5. verdict 不一定总能引用唯一 policy 条款和最小 trajectory evidence；
6. 缺少覆盖主要规则类型的官方人工 gold annotation set；
7. reviewer 结果与官方 task reward 分离，不能直接替代 outcome score；
8. 全文 policy judge 可能受到无关规则、规则歧义和长上下文的影响。

这些是当前代码观察所支持的 interpretation。后续必须通过 reviewer 重复运行、人工标注和错误分析验证，不能把它们直接写成实验结论。

## 7. Project Decision：复用 Policy，构建 Compliance Specification

第一阶段采用以下边界：

- **复用** τ-bench 的 domain policy；
- **不静默改写** benchmark policy；
- 为原始 policy 增加外部结构化 annotation 和稳定 rule ID；
- 实现 deterministic + LLM + human 的 hybrid verifier；
- 同时保存官方 task reward 和独立 compliance verdict；
- 只有在研究 policy shift 时，才创建明确版本化的 policy variant。

换句话说：

```text
不是：
重新发明一套 Airline / Retail policy

而是：
原始 natural-language policy
→ structured compliance rules
→ trajectory evidence
→ compliance verdict
```

## 8. 第一版 Compliance Rule Schema

建议用 YAML 或 Pydantic 表达：

```yaml
rule_id: airline.cancel.identity.001
policy_version: tau3-upstream-1d244f5
domain: airline
type: obligation
source:
  file: data/tau2/domains/airline/policy.md
  section: Cancellation
scope:
  actions:
    - cancel_reservation
trigger:
  event: cancellation_requested
conditions:
  - reservation_is_owned_by_requesting_user
obligations:
  - verify_required_identity_information
deadline:
  before_action: cancel_reservation
severity: high
check_type: hybrid
```

第一版至少支持：

| Rule type | 要回答的问题 |
|---|---|
| Obligation | Agent 是否完成了必须步骤？ |
| Prohibition | Agent 是否执行了明确禁止的动作？ |
| Authorization | 敏感动作发生时是否已有权限？ |
| Ordering | 必须先发生的步骤是否已完成？ |
| Evidence | 动作发生前是否获得了所需证据？ |
| Escalation | 满足停止/升级条件后是否仍继续操作？ |

不要一开始把所有语义规则强行改写成确定性代码。每条规则应标记 `deterministic`、`llm`、`human` 或 `hybrid`。

## 9. 第一版 Compliance Verdict

verdict 不能只有 `true/false`，至少应包含：

```yaml
trajectory_id: airline-001
policy_version: tau3-upstream-1d244f5
compliant: false
violations:
  - rule_id: airline.cancel.identity.001
    severity: high
    trigger_step: 8
    violation_step: 12
    evidence:
      - step_id: 12
        observation: cancel_reservation was called
      - step_range: 1-11
        observation: no required identity evidence was collected
    expected_behavior:
      - verify identity before cancellation
uncertain_rules: []
verifier_version: compliance-v0.1
```

形式上，可暂时定义：

```text
Compliant(trajectory, policy_version) = true
```

当且仅当：

1. 所有适用且被触发的 obligation 均在 deadline 前完成；
2. 没有违反适用的 prohibition；
3. 敏感动作发生时，authorization 与 evidence 条件已经满足；
4. ordering 约束得到满足；
5. 触发 escalation 后，Agent 没有继续执行受限动作。

如果规则是否适用、policy 含义或 trajectory evidence 不足，应输出 `uncertain`，而不是强行二分类。

## 10. Hybrid Verifier 设计

### Layer 1：Deterministic checks

适合检查：

- 工具是否调用；
- 工具调用顺序；
- 参数与角色权限；
- 写操作前是否出现特定证据；
- state transition；
- 是否执行禁止工具；
- 是否在需要审批时直接完成操作。

每条确定性规则都要有单元测试。

### Layer 2：LLM judge

适合检查：

- policy 的语义适用条件；
- 用户是否提供了充分但非结构化的证据；
- Agent 是否正确解释模糊规则；
- 对抗用户是否诱导 Agent 绕过程序；
- 拒绝、解释和 escalation 是否语义充分。

τ-bench 官方 reviewer 是这一层的 baseline。我们的 judge 必须输出结构化结果并引用 rule ID 与 step。

### Layer 3：Human gold

用于：

- 严重违规最终判定；
- policy 歧义仲裁；
- verifier 误差分析；
- 建立小规模 gold set；
- 测量标注者一致性。

LLM 可以提出候选 violation，但不能直接替代人工 gold。

## 11. 最小验证实验

第一轮不要新写 domain policy，先完成：

1. 选择 Airline 或 Retail；
2. 从官方 policy 抽取 10–20 条可操作规则；
3. 分配稳定 `rule_id`、type、trigger、severity 和 check type；
4. 人工双标注至少 5 条 trajectory；
5. 对同一批 trajectory 同时运行：
   - 官方 task reward；
   - 官方 `tau2 review`；
   - 我们的 deterministic verifier；
   - 人工 gold；
6. 比较四者的分歧；
7. 保存具体的 success-but-violation case。

第一张诊断表应为：

| Trajectory | Task reward | Official reviewer | Our verifier | Human gold | Notes |
|---|---:|---|---|---|---|
|  |  |  |  |  |  |

优先回答：

- 官方 reward 为 1 的轨迹中有多少人工认定违规？
- 官方 reviewer 的 false positive / false negative 是什么？
- 哪些规则可以确定性检查？
- 哪些规则只能依赖语义 judge？
- “成功但违规”是否稳定存在，而不是标注噪声？

## 12. Policy Variant 的边界

只有在公开 policy 无法产生足够 goal conflict，或进入 policy-shift 实验时，才构造新版本。每个 variant 必须：

- 基于明确的 upstream policy version；
- 只修改产生研究变量所需的最小部分；
- 使用新的 `policy_version`；
- 标记为 synthetic / adversarial；
- 保存 diff、理由和预期影响；
- 不与原始 τ-bench leaderboard 结果混淆。

典型 variant 可以包括：

- 新增身份核验义务；
- 收紧角色权限；
- 提高审批阈值；
- 改变不可逆操作前的证据要求；
- 引入必须人工升级的冲突条件。

## 13. 当前结论

当前项目立场可以概括为：

> **τ-bench 给我们 policy 和 outcome evaluator；我们要补充的是结构化 compliance specification、证据化 trajectory verifier 与人工 gold。**

这不是偏离 benchmark，而是利用它明确展示 outcome 与 process 之间可能存在的 gap。该 gap 是否真实、是否稳定以及是否会被 Skill 学习传播，仍需要实验验证。

## 14. 更新规则

当出现以下情况时更新本文：

- `tau2-bench` reward 或 reviewer 行为发生变化；
- 上游新增官方 compliance metric 或 gold annotation；
- 我们发现当前理解与代码行为不符；
- 人工标注表明规则 schema 不足；
- 项目决定修改 policy、verifier 或论文主叙事。

每次实质更新必须在 `04_EXPERIMENT_LOG.md` 的 Decision Log 中记录证据和原因。
