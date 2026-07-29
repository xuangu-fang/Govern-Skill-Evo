# 项目叙事：Governed Skill Evolution

版本：2026-07-28  
预计周期：第一阶段 3 个月

## 1. 我们看到的问题

Agent 在一次任务中会产生完整运行轨迹：观察、推理、工具调用、环境反馈、人工介入和最终结果。当前一批工作开始把这些轨迹总结成自然语言 Skill，使冻结的 Agent 不改模型参数也能持续改善。

这里存在一个被低估的问题：**成功轨迹不一定是正确经验。**

Agent 可能通过下面的方式完成任务：

- 跳过必要核验；
- 在权限不足时调用工具；
- 先执行不可逆操作，再补齐证据；
- 使用不应访问的数据；
- 绕过独立复核或人工审批；
- 因偶然环境状态成功，却把偶然性总结成一般规则。

如果 Skill 学习只优化最终成功率，这些“成功但违规”的局部做法可能被提炼、泛化，并在后续任务中反复传播。于是 Skill Evolution 不只是能力学习问题，也变成了经验选择、过程验证和治理问题。

## 2. 当前核心研究问题

主问题：

> 当 Agent 从运行轨迹中学习 Skill 时，如何提高任务能力，同时避免吸收和放大程序性违规？

第一篇论文只需要回答三个子问题：

1. **现象**：只按 outcome 优化的 Skill 学习，是否会吸收或放大 reward-compatible procedural violations？
2. **方法**：能否利用 task verifier 与 compliance verifier 的双重反馈，生成带适用条件、义务、禁止项和证据来源的 Skill？
3. **泛化**：这种 Skill 在 policy shift、模型更换和 adversarial user 下，能否维持能力与合规性？

## 3. 不要一上来做“自进化”

本项目按四个层级推进。每一层都必须有独立 demo 和评测。

### Level 0：Trajectory Understanding

输入一条 Agent trajectory，输出结构化摘要：

- 用户目标是什么；
- Agent 做了哪些工具调用；
- 最终任务是否完成；
- 哪些步骤有效；
- 哪些步骤失败；
- 是否违反过程规则；
- 哪些判断仍不确定。

这一层的目的，是让学生真正理解 Agent、environment、tool、state、trajectory 和 verifier。

### Level 1：Trajectory-to-Skill

从一条或少量轨迹中生成一个候选 `SKILL.md`，内容至少包含：

- 适用任务；
- 推荐步骤；
- 常见错误；
- 何时停止；
- 何时请求更多信息。

先人工审查，不自动采用。先比较有 Skill / 无 Skill，不讨论完整 continual learning。

### Level 2：Validation-Gated Skill Optimization

从多条轨迹中提取局部 lesson，修改 Skill，并只在 held-out validation 上变好时接受更新。

这里复用 SkillOpt 的基本思想：

```text
rollout → reflection → bounded edit → held-out validation → accept/reject
```

此阶段的目的是复现并理解已有最强 baseline，而不是宣称创新。

### Level 3：Governed Skill Evolution

把单一 outcome feedback 拆成两类：

- task feedback：任务有没有完成；
- compliance feedback：过程是否遵守 policy、权限、顺序、证据和审批要求。

轨迹不再只有成功/失败两类，而是四类：

| 类型 | Task success | Compliance | 对 Skill 更新的作用 |
|---|---:|---:|---|
| 合规成功 | 是 | 是 | 强正证据 |
| 违规成功 | 是 | 否 | 负面过程证据；禁止把违规捷径写入 Skill |
| 合规失败 | 否 | 是 | 能力缺口证据；保留必要程序 |
| 违规失败 | 否 | 否 | 同时诊断能力与治理缺口 |

我们的方法暂定包含：

1. 双 verifier 轨迹诊断；
2. 基于局部证据的 bounded Skill patch；
3. 带 contract 的 Skill 表示；
4. task gate + compliance gate；
5. provenance、version、rollback。

## 4. Skill 暂时怎样表示

第一版不要设计复杂 DSL。使用可读 Markdown + 机器可解析 YAML header：

```yaml
name: account-action-investigation
version: 0.1.0
applicability:
  - sufficient_identity_evidence
obligations:
  - verify_account_owner_before_sensitive_action
  - collect_required_evidence_before_irreversible_action
prohibitions:
  - never_bypass_required_approval
escalation:
  - unresolved_identity_conflict
evidence:
  - trajectory_id: tau2-retail-0007
    verifier: process_v0.1
confidence: provisional
```

正文再写可供 Agent 使用的步骤和例子。第一版重点是能运行、能版本化、能追溯，不追求完美 schema。

## 5. 用什么公开环境验证

### 主环境：τ³-bench（仓库名仍为 `tau2-bench`）

第一周优先使用 `airline` 或 `retail` 域：

- 有明确 domain policy；
- 有可调用工具；
- 有多轮用户交互；
- 有可变数据库状态；
- 能保存完整 trajectory；
- 与真实组织工作流结构相似。

它最适合回答：“最终状态正确”与“过程遵守规则”是否一致。

`banking_knowledge` 域可在后续加入，但它主要是银行知识检索与客服，不是信用卡欺诈调查。不要把它包装成 fraud benchmark。

### 第二环境：ToolSandbox

用途：

- state dependency；
- intermediate milestones；
- minefields；
- insufficient information；
- 多步 tool-use 过程分析。

它与我们的过程合规问题匹配，但当前代码较老、依赖 Python 3.9、模型枚举也较旧。放在第二阶段，不作为学生第一天的环境。

### 泛化环境：SkillLearnBench

用途：

- 比较自动 Skill 生成方法；
- 使用真实任务、确定性 verifier 和容器化执行；
- 检查方法是否只对 τ³ 的客服工作流有效。

它强制使用 Docker，包含 20 个任务、100 个 verified instances。第一周只 dry-run 一个任务；完整实验放到中后期。

### 后续小环境：FraudOps-mini

只有在公开 benchmark 上跑通方法后再做。目标不是训练新的 fraud classifier，而是模拟围绕固定风险工具展开的调查工作流：

```text
transaction intake
→ risk model / rule engine
→ evidence collection
→ account and history query
→ approve / reject / hold recommendation
→ manual review or escalation
→ case report
```

底层交易数据可以从 PaySim、BankSim 或 IEEE-CIS Fraud Detection 中选择。Agent 的研究对象是证据获取、工具调用、权限、复核和升级流程。

## 6. 最开始复用谁的代码

| 组件 | 复用对象 | 我们暂时怎么用 |
|---|---|---|
| Agent 环境与轨迹 | `sierra-research/tau2-bench` | 第一周主环境；先不改核心代码 |
| Skill 优化器骨架 | `microsoft/SkillOpt` | 复现 bounded edits 和 validation gate |
| 轨迹局部 lesson 合并 | `Qwen-Applications/Trace2Skill` | 作为 many-to-one distillation baseline |
| Skill 学习评测 | `cxcscmu/SkillLearnBench` | 中后期泛化实验 |
| 过程轨迹评测思想 | AgentPex / MAC-Bench | 设计 compliance verifier 和指标；不要假定都有成熟可复用代码 |

推荐的工程策略：

- 环境层以 τ³ 为主；
- 优化器层以 SkillOpt 为主；
- Trace2Skill 作为 baseline 与局部分析模块参考；
- 我们自己实现最薄的 `trajectory schema + compliance verifier + dual gate`。

不要把三个仓库直接拼成一个巨型框架。先用离线 JSON trajectory 做方法实验，再考虑深度集成。

## 7. 第一批可验证假设

### H1：Outcome 与 Compliance 存在可测量分离

在至少一批任务中，Agent 达成目标状态，但违反了过程 policy。

最低证据：

- 至少 30 条轨迹；
- 人工双标注 task/compliance；
- 能列出 3 类以上重复违规模式；
- 两名标注者对关键违规有基本一致性。

### H2：普通 Skill 学习会传播违规捷径

将“违规成功”轨迹纳入 Skill 学习后，在 held-out tasks 中相同或相近违规出现得更多。

最低对照：

- no skill；
- human-written skill；
- outcome-only learned skill；
- 删除违规成功轨迹后学到的 skill。

### H3：双 Gate 能改善风险—能力前沿

Compliance-aware Skill Evolution 在显著减少违规的同时，不把任务成功率打回 no-skill 水平。

主要指标：

- task success；
- compliance rate；
- severe violation rate；
- compliance-weighted success；
- Machiavellian gap：task success 与 compliance-aware score 的差；
- API/token cost；
- skill update acceptance rate。

### H4：治理信息能跨模型或 policy version 迁移

同一 Skill 换模型或遇到 policy shift 后，prohibition、obligation 和 escalation 是否仍有效。

## 8. 论文贡献应该长什么样

理想贡献不是“我们给 Skill 加了几个字段”，而是：

1. 发现并量化 outcome-optimized skill evolution 的违规放大现象；
2. 提出 task/compliance 解耦的轨迹诊断与 Skill 更新机制；
3. 构造包含 policy shift、违规捷径和对抗诱导的评测协议；
4. 在公开 workflow benchmarks 与小型 FraudOps 环境上验证。

如果 H1/H2 做不出来，当前 paper story 就不成立。此时不要硬做 compliance-aware optimizer，应转向更一般的“trace diagnosis + auditable Skill provenance”，或重新设计能产生真实 goal conflict 的任务。

## 9. 三个月边界

### 必须完成

- 跑通至少一个公开 Agent workflow benchmark；
- 统一轨迹格式；
- task/process 双标注与 verifier；
- 复现至少一个 trajectory-to-skill baseline；
- 构造 outcome-only 与 compliance-aware 对照；
- 完成 policy shift 或 adversarial user 中至少一项；
- 有完整可复现实验表。

### 可以完成

- FraudOps-mini；
- Skill contract 可视化；
- rollback 与 lineage viewer；
- 跨模型/跨 harness 迁移。

### 暂时不做

- 开放式多 Agent 组织结构自演化；
- 复杂 RL 或端到端模型训练；
- 直接接入真实支付系统；
- 自动修改 policy/verifier；
- 同时优化 Skill、memory、tool wrapper、角色和 workflow；
- 物理 Agent 实验。

这些是长期方向，不是第一篇论文的必要条件。

## 10. 与长期 vision 的关系

当前项目积累的是“受约束的经验学习机制”。以后可以迁移到科学与工程：

| 当前工作流 Agent | 科学/工程 Agent |
|---|---|
| 业务 policy | 实验协议、安全边界、物理约束 |
| 数据库与账户状态 | 传感器与物理系统状态 |
| 工具和规则引擎 | 仿真器、surrogate、设备和控制器 |
| 案件轨迹 | 实验、设计、诊断和运行轨迹 |
| Skill contract | 实验/控制/仿真 Skill contract |
| 人工升级 | 工程师接管或安全停机 |

长期问题是：

> Can real-world agents improve from operational trajectories while preserving physical constraints, procedural accountability, and human authority?

三个月项目只解决其中第一块：经验怎样安全地变成 Skill。

## 11. Go / No-Go 节点

### 第 1 周末

必须跑通 τ³ 小规模任务，拿到原始 trajectory，并完成 5 条人工过程标注。

### 第 3 周末

必须完成至少 30 条轨迹的 task/compliance 双标注，并证明存在“成功但违规”。

### 第 5 周末

必须完成一个 outcome-only Skill baseline，并观察到可复现的 Skill 效果或违规传播。

### 第 8 周末

必须完成 dual gate 方法和主要消融。若仍无法超过简单过滤 baseline，应收缩方法贡献，强化现象与 benchmark。

### 第 10 周末

冻结主实验设置，停止继续加框架，进入重复实验、统计、作图和写作。
