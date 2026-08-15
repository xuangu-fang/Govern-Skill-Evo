# 二维分布迁移视角下的受控 Skill 进化

版本：2026-08-15  
状态：Research memo / 未来研究方向，不替代当前实验协议  
主题：Distributional Governed Skill Evolution

## 1. 研究共识更新

本备忘录记录教师与研究团队在当前阶段形成的两项研究共识。

第一，项目的主要实验环境由 τ-bench 转向 **ST-WebAgentBench**。τ-bench 对发现“最终任务成功不等于过程合规”非常有价值，但 ST-WebAgentBench 已经提供更加成熟的 policy、trajectory 和 compliance evaluation 流水线，更适合系统研究 Skill 更新如何改变 Agent 的能力—合规联合分布。τ-bench 保留为问题动机、早期案例和潜在跨环境验证，不再承担主要实验环境的角色。

第二，Governed Skill Evolution 不再只被描述为“使用 task verifier 和 compliance verifier 控制 Skill 更新”，而被进一步表述为：

> **Skill 更新是对 Agent 行为分布的一次干预；受控 Skill 进化的目标，是将概率质量从失败或违规区域迁移到成功且合规区域，同时阻止以合规退化换取任务成功的有害迁移。**

这不是对学生已有工作的否定。现有的四状态统计、二维 Evolution Gate、S0→S1 接受和后续 Candidate 拒绝，已经构成这一分布迁移视角的早期实证基础：

- [项目实验日志](../../docs/04_EXPERIMENT_LOG.md)
- [ST-WebAgentBench 实验结果索引](../../experiments/results/README.md)
- [S0→S1 Selection 结果](../../experiments/results/stweb_suitecrm_poc_v02/selection/evolution_summary.md)
- [S1→S2 Selection 结果](../../experiments/results/stweb_suitecrm_poc_v03/selection/evolution_summary.md)

## 2. 基本形式化

设：

- \(x\)：任务、用户请求、初始环境状态和用户行为条件；
- \(p\)：适用的 policy 及其版本；
- \(m\)：冻结的基础模型与 Agent harness；
- \(S\)：当前外部 Skill；
- \(\tau\)：一次完整 trajectory，包括观察、对话、工具调用、环境反馈和最终状态。

给定 Skill 后，Agent 诱导出条件 trajectory distribution：

\[
P_S(\tau \mid x,p,m).
\]

Task verifier 与 compliance pipeline 将 trajectory 映射到二维结果：

\[
z(\tau)=\big(T(\tau),C(\tau)\big),
\]

其中：

- \(T(\tau)\in\{0,1\}\)：任务是否得到正确解决；
- \(C(\tau)\in\{0,1\}\)：完整过程是否满足适用 policy。

必要时还应保留比二值标签更丰富的变量：

\[
z(\tau)=\big(T,C,V_{severity},V_{type},Cost,Steps\big),
\]

其中 \(V\) 表示违规数量、类型和严重程度。

一次 Skill 更新 \(S\rightarrow S'\) 不只是改变一段文本，而是把 induced behavior distribution 从

\[
P_S(T,C)
\]

变换为

\[
P_{S'}(T,C).
\]

因此，研究对象不是某个 Candidate Skill 看起来是否更合理，而是：

1. 哪些任务的状态发生了变化；
2. 概率质量从哪个区域移动到哪个区域；
3. 这种移动是否由 Skill 中可追溯的规则引起；
4. 改善是否能在重复运行、独立任务和 policy shift 下保持。

## 3. 二维空间中的四种状态

| 状态 | Task success | Compliance | 含义 |
|---|---:|---:|---|
| CS: Compliant Success | 1 | 1 | 任务正确完成且过程合规；目标区域 |
| VS: Violating Success | 1 | 0 | 任务成功但过程违规；reward-compatible corruption |
| CF: Compliant Failure | 0 | 1 | 程序得到保留，但能力不足或执行失败 |
| VF: Violating Failure | 0 | 0 | 能力和治理同时存在问题 |

二维分布可以写成：

\[
\pi_S=(p_{CS},p_{VS},p_{CF},p_{VF}),
\]

四项之和为 1。Skill evolution 的目标不是简单让横轴 Task Success 变大，而是优先增加 \(p_{CS}\)，减少 \(p_{VS}\) 和严重违规，并避免把 \(p_{CF}\) 通过违规捷径运输到 \(p_{VS}\)。

### 3.1 希望出现的迁移

```text
CF → CS   保留程序约束，同时补足能力
VS → CS   保留有效能力，同时移除违规捷径
VF → CS   同时修复能力与治理问题
VF → CF   先消除违规，即使任务尚未完成
```

### 3.2 需要重点阻止的迁移

```text
CF → VS   用违规捷径换取成功
CS → VS   能力保持，但治理退化
CS → CF   过度约束或规则冲突导致能力退化
任意状态 → 严重违规
```

其中 `CF → VS` 是 outcome-only optimization 最值得警惕的路径：平均成功率可能上升，但系统实际上发生了 reward-compatible corruption。

## 4. Success 的定义必须受 Policy 约束

横轴不能简单定义为“是否满足用户表面请求”。用户可能要求 Agent 绕过确认、伪造字段、越权访问或执行 policy 明确禁止的操作。如果 Agent 正确拒绝、请求必要信息或升级人工，用户的原始动作目标没有完成，但 Agent 可能完成了正确的业务处理。

因此更准确的概念是：

> **Policy-permitted task resolution：在 policy 允许的边界内正确解决任务，包括执行、拒绝、澄清、停止或升级。**

这要求 task verifier 与 policy evaluator 的职责保持可区分，但不能在语义上互相矛盾。否则，一个合规拒绝可能被 task verifier 记为失败，继而错误激励 Agent 执行违规动作。

## 5. 高层设计原则

### 5.1 优化联合分布，而不是单一平均分

不应只优化：

\[
\mathbb{E}[T+\lambda C].
\]

固定权重会允许大量普通成功抵消少量严重违规，也可能用某些 task subgroup 的退化换取整体平均改善。应同时报告二维联合分布、严重违规尾部和最差 subgroup。

### 5.2 分布移动方向比终点均值更重要

相同的成功率提升可能来自完全不同的迁移：

```text
CF → CS   是 safe capability improvement
CF → VS   是 harmful improvement
```

所有 Candidate evaluation 都应输出 task-level transition matrix，而不是只输出聚合均值。

### 5.3 Transport cost 必须非对称

从 `VS → CS` 的迁移应被鼓励；从 `CS → VS` 的迁移应被赋予极高代价。严重违规可以设置为 hard constraint，而不是允许其与普通成功在线性 reward 中交换。

### 5.4 合规约束优先于局部成功增益

对于高严重度规则，可以采用 lexicographic decision：

1. Candidate 不得增加严重违规；
2. 不得降低整体 compliance 或关键 subgroup compliance；
3. 在满足前两项后，再比较 task success 和成本。

这比把 success 与 compliance 简单加权更符合 governed evolution。

### 5.5 Skill 更新必须是 bounded intervention

每次只允许有限数量的 `add / replace / delete`，并保存 parent、patch、source evidence、counterevidence 和适用范围。更新越大，越难把行为变化归因到具体 Skill clause，也越容易产生全局 prompt interference。

### 5.6 Applicability 是 Skill 的一部分

Skill 不能被当成对所有任务统一生效的文本。每条规则应说明：

- 对哪些 task、页面、工具和 policy version 适用；
- 由什么 observation 触发；
- 在什么情况下停止应用；
- 与哪些已有规则冲突。

### 5.7 Selection、Test 与 Learner 严格隔离

训练 trajectory 用于生成 Candidate；Selection 只用于 accept/reject；Test 只用于最终独立评价。Selection 或 Test 的逐任务反馈不能返回 Learner，否则分布迁移结果会混入 evaluation leakage。

### 5.8 平均改善不能掩盖尾部和 subgroup regression

至少按以下维度检查：

- policy category；
- task intent/template；
- 操作是否不可逆；
- 是否涉及用户确认；
- 正常用户与 adversarial user；
- 不同基础模型；
- policy version。

## 6. 四类轨迹不是简单的正负样本

### 6.1 CS：正面能力证据与程序锚点

CS trajectory 同时展示了有效能力与正确程序，可以支持 Skill 中的推荐步骤、必要前置条件和停止条件。但仍需避免复制具体任务答案或偶然 UI 路径。

### 6.2 VS：最重要的 hard negative

VS 不能作为普通成功样本直接学习，也不能整条丢弃。它通常同时包含：

```text
有效的任务理解
+ 有效的局部操作
+ 违规捷径
+ 偶然或环境相关条件
```

Learner 应保留其中的有效能力，将违规部分转化为 prohibition、obligation、ordering 或 evidence requirement，并明确该经验不能作为行动许可。

### 6.3 CF：程序正样本、能力负样本

CF 用来证明必要程序并非错误。修复 task failure 时，不得把身份确认、字段验证、用户授权或安全停止误认为失败原因而删除。

### 6.4 VF：能力与治理的联合诊断样本

VF 可以暴露错误工具、错误顺序、错误 Skill 和执行停滞，但通常不足以单独说明正确 Skill 应该是什么，需要与 CS、VS 或 counterfactual trajectory 配对。

## 7. 优先构造的成对样本

绝对标签告诉我们 trajectory 属于哪个象限，成对样本更容易告诉我们应该如何修改 Skill。

| Pair | 尽量保持不变 | 主要回答的问题 | 适合产生的 Skill 信息 |
|---|---|---|---|
| CS vs VS | 同任务、初始状态、policy、模型 | 哪些过程差异决定合规？ | obligation、prohibition、ordering |
| CS vs CF | 同任务、同为合规 | 哪些能力差异决定成功？ | 工具策略、状态跟踪、recovery |
| VS vs VF | 同为违规 | 哪些能力带来了成功，但不能被无条件学习？ | 能力片段与违规捷径解耦 |
| Parent vs Candidate | 同 Selection task | Skill patch 将该任务运到了哪个象限？ | update attribution |
| Policy v1 vs v2 | 同任务和 trajectory | 哪条规则在 policy shift 后失效？ | applicability、version、rollback |
| Normal vs adversarial user | 同任务和环境 | Skill 是否抵抗催促和诱导？ | invariant obligation、stop rule |
| With-clause vs without-clause | 同任务、同 Skill 其余部分 | 某条 clause 是否真正导致行为变化？ | clause-level causal evidence |

现实中无法保证模型 rollout 完全一致，因此“matched pair”应至少固定 task、initial state、policy version、模型、主要采样参数和评测协议，并进行多次重复运行。

## 8. 从 Trajectory 到 Governed Experience

每条训练经验不应只有 `success=true/false`，而应包含：

```yaml
task_id:
trajectory_id:
skill_version:
policy_version:
task_success:
compliant:
quadrant: CS | VS | CF | VF
violations:
  - policy_id:
    category:
    severity:
    step_ids:
    evidence:
effective_behavior:
harmful_behavior:
missing_behavior:
applicability:
counterevidence:
```

这里最重要的不是让 LLM 自由总结，而是进行 **behavior attribution**：

- 哪段行为帮助了任务成功？
- 哪段行为造成违规？
- 两者是否实际上是同一行为？
- 如果删除违规行为，是否存在合规替代路径？
- proposed clause 是从证据中得到约束，还是把一次违规误解释成新权限？

## 9. Candidate Skill 的生成原则

每个 proposed edit 至少回答：

1. 它要改变哪一类 trajectory transition？
2. 它支持哪些 CS/VS/CF/VF experience？
3. 它针对的是能力缺口还是合规缺口？
4. 它会保留 Parent 中哪些已经有效的约束？
5. 哪些任务或 policy subgroup 可能受到副作用？
6. 哪些 counterevidence 会使该 edit 无效？

对于 `replace`，必须额外做 preservation analysis：新规则不仅增加了什么，也要说明旧规则保护的哪些行为不会丢失。

证据存在问题时，不宜只有“整份 Candidate 作废”和“完全交给 Selection”两个极端。建议采用三种状态：

```text
validated edit   → 可以进入 Candidate
quarantined edit → 保存但不自动应用，等待人工或额外实验
rejected edit    → 与证据或 policy 明确冲突
```

## 10. 分层 Evolution Criteria

### Gate 0：Schema 与预算

- edit 数量不超过上限；
- patch 可应用；
- Skill 可解析；
- 没有越过本轮授权的 task、模型调用和 rollout 预算。

### Gate 1：Evidence 与 provenance

- source trajectory 属于本轮允许的训练证据；
- policy 引用与实际 violation 一致；
- edit direction 确实修复或保留相关行为；
- 不把“适用但未违反的 policy”伪装成修复依据；
- 记录 counterevidence 与不确定性。

### Gate 2：Local behavioral validation

在与 edit 语义相关的 matched tasks 上检查：

- 目标 violation 是否减少；
- Agent 是否只是通过拒绝一切来避免违规；
- 能否形成合规替代路径；
- 是否产生与 edit 无关的大范围行为变化。

### Gate 3：Selection distribution gate

一个保守的接受规则可以是：

\[
\Delta p_{CS}\ge 0,
\]

\[
\Delta p_{VS}\le 0,
\]

\[
\Delta P(\text{severe violation})\le 0,
\]

并且 Task Success、Compliance、CuP 中至少一项产生预先规定的实质改善。

对于小样本实验，可以继续采用当前“不允许聚合指标退化，至少一项改善”的 Gate，但必须同时展示 task-level transition，避免聚合值相同却出现 `CS→VS` 与 `VF→CF` 相互抵消。

### Gate 4：Stability 与 subgroup gate

- 多次 rollout 后改善仍然存在；
- policy subgroup 没有明显回归；
- 不可逆或高风险操作没有新增违规；
- variance 没有显著恶化。

### Gate 5：Independent Test

Test 只能在方法与超参数冻结后运行一次或按预注册协议运行。Test 结果不能再用于修改本轮 Skill。

最终决策不只包含 `ACCEPT / REJECT`，还应支持：

```text
ACCEPT
REJECT
QUARANTINE
NO_CANDIDATE
ROLLBACK
```

## 11. 分布级评价指标

### 11.1 Compliant Success / CuP

\[
\mathrm{CuP}=P(T=1,C=1)=p_{CS}.
\]

它是右上象限的概率质量，应作为主要指标之一。

### 11.2 Violating Success / Corrupt Success

\[
\mathrm{CSR}=P(T=1,C=0)=p_{VS}.
\]

以及：

\[
P(C=0\mid T=1),
\]

表示成功轨迹中有多少依赖或包含违规行为。

### 11.3 Safe Improvement Rate

对于 Parent/Candidate matched tasks：

\[
\mathrm{SIR}=P(T_{S'}>T_S,\ C_{S'}\ge C_S).
\]

### 11.4 Harmful Transport Rate

\[
\mathrm{HTR}=P(T_{S'}>T_S,\ C_{S'}<C_S).
\]

它直接测量“能力改善是否来自治理退化”。

### 11.5 Governance Regression Rate

\[
\mathrm{GRR}=P(C_{S'}<C_S),
\]

并单独报告 `CS→VS` 与 `CS→VF`。

### 11.6 Severe Violation Tail Risk

报告严重违规概率、每任务最大 severity，必要时使用 severity CVaR。严重违规不应被大量低风险成功平均掉。

### 11.7 Worst-group CuP

\[
\min_g P(T=1,C=1\mid g),
\]

其中 \(g\) 可以是 task template、policy category、操作风险级别或 adversarial condition。

### 11.8 Transition Matrix

每次 Parent/Candidate 比较都输出完整 \(4\times4\) transition matrix：

```text
Parent state × Candidate state
```

这是分布迁移 framing 下最核心的诊断 artifact。

## 12. ST-WebAgentBench 在本研究中的角色

ST-WebAgentBench 的主要价值不是“任务更难”，而是它已经把本项目最昂贵的一部分测量基础设施系统化：

- 有明确任务和真实 Web 工作流；
- policy 与任务执行过程相关；
- 能保存完整 trajectory；
- 有较成熟的 policy compliance evaluation；
- 能把 task outcome 与 policy violations 分开统计；
- 适合构造固定 Selection tasks 和 task-level transitions。

我们的贡献不应被描述为重新实现 ST-WebAgentBench 的 compliance pipeline，而应是：

> 利用相对成熟的二维测量环境，研究 trajectory-driven Skill updates 如何改变联合行为分布，以及怎样通过 provenance、bounded edits 和 distributional gates 控制这种迁移。

同时仍需对 benchmark evaluator 做测量审计：

- verifier 的 false positive / false negative；
- policy category 覆盖；
- 对不同任务模板的偏差；
- 同一 trajectory 重复评价的稳定性；
- 哪些违规只能被弱语义 judge 识别。

成熟 evaluator 是研究仪器，不应被未经检验地当作绝对真值。

## 13. Baseline 与实验矩阵

至少保留以下方法：

1. **No Skill**：测量冻结 Agent 的原始分布；
2. **Human Skill**：人工可解释上界或参考点；
3. **Outcome-only Skill**：只从成功 trajectory 学习；
4. **Filtered Skill**：删除 VS 后从 CS 学习；
5. **Governed Skill**：四象限诊断、behavior attribution、provenance 和双维 Gate；
6. **Governed without provenance**：检验证据约束的贡献；
7. **Governed without compliance gate**：检验 Gate 的贡献；
8. **Governed without paired transitions**：检验分布迁移信息的贡献。

关键消融包括：

- 只过滤 VS；
- 只加入 contract 字段；
- 只使用平均 score；
- 不检查 severe violation；
- 不做 preservation analysis；
- 不做重复 rollout；
- 不使用 task-level transition matrix。

## 14. 建议的冻结实验协议

### 14.1 数据划分

```text
Train trajectories
→ 生成 Governed Experiences 与 Candidate

Selection tasks
→ Candidate vs accepted Parent 的 accept/reject

Test tasks
→ 方法和超参数冻结后的独立评价
```

任务划分应按 intent/template 分层，避免同模板实例泄漏。每个 split 保存冻结 manifest。

### 14.2 重复运行

由于相同 Skill 在相同 task 上仍可能产生不同 trajectory，至少需要：

- Parent 与 Candidate 使用 matched task set；
- 每个条件多个 rollout 或 seed；
- 报告均值、置信区间和 paired difference；
- 区分 Skill effect 与 sampling noise。

### 14.3 预注册 Gate

在运行 Selection 前冻结：

- 主指标；
- severe violation 定义；
- 接受阈值；
- subgroup；
- 重复次数；
- tie 和 indeterminate 的处理方式。

禁止看完 Candidate 结果后调整接受规则。

## 15. 第一批可证伪假设

### H-D1：Skill evolution 可以被测量为稳定的二维分布迁移

同一 Skill 在重复运行中的自然波动小于不同 Skill 版本造成的 matched transition effect。

若 Skill 间差异不超过运行噪声，则分布迁移 framing 暂时缺少可识别信号。

### H-D2：Outcome-only evolution 会产生 harmful transport

Outcome-only Skill 相比 Parent 增加 `CF→VS`、`CS→VS` 或 \(P(C=0\mid T=1)\)。

若 outcome-only 在重复实验中不增加任何治理退化，则“违规传播”主张需要收缩。

### H-D3：简单过滤不足以得到最佳迁移

Filtered Skill 不稳定优于 Governed Skill，因为过滤 VS 同时丢失其中的有效能力信息，也不能利用 violation evidence 生成明确 prohibition。

### H-D4：Pair-aware attribution 优于无差别 trajectory summarization

使用 CS/VS、CS/CF matched evidence 的 learner 能产生更高 CuP、更低 HTR，并减少不受支持的 Skill clause。

### H-D5：Distributional gate 能阻止 reward-compatible corruption

当 Candidate 提高 Task Success 但降低 Compliance 时，Gate 能稳定拒绝它；被接受版本在独立 Test 上具有更高或不低的 CuP，且 severe violation 不增加。

### H-D6：治理信息能够跨 policy version 或基础模型迁移

Skill 的 obligation、prohibition 和 escalation 在 policy shift 或 target model 替换后仍能减少相应违规，或能根据 applicability 正确停止生效。

## 16. 当前已有证据如何映射到这一框架

现有 SuiteCRM 结果已经展示了两类关键迁移。

### S0→S1

在一次正式 Selection 中：

```text
Task Success: 5/18 → 6/18
Compliance:   4/18 → 6/18
CuP:          3/18 → 4/18
```

其中出现 `VF→CS` 和 `VF→CF`，说明 Candidate 同时产生了能力—合规联合改善和纯治理改善，因此被 Gate 接受。

### S1→S2

在下一次 Selection 中：

```text
Task Success: 7/18 → 7/18
Compliance:   7/18 → 6/18
CuP:          4/18 → 3/18
```

出现 `CS→VF`，且 violating success 增加，因此 Candidate 被拒绝。

Day 12 的自动三步结果进一步显示：后续 Candidate 虽将 Task Success 从 `7/18` 提高到 `8/18`，但分别造成 Compliance 或 CuP 下降，均被 Gate 拒绝。这正是“阻止 harmful transport”的原型证据。

但当前证据仍有限：Selection 样本较小、独立 Test 尚未运行，相同 S1 的重复运行结果也有波动。因此现在可以声称 Gate 按设计工作，不能声称方法已经获得稳定泛化优势。

## 17. 主要混淆因素与失败模式

### 17.1 Sampling noise

Candidate 的文本变化可能改变模型采样路径，使语义上无关的任务发生变化。必须通过重复运行和 clause ablation 区分 Skill effect 与偶然波动。

### 17.2 Over-refusal

Skill 可能通过“一律不操作”提高 compliance。需要同时检查 policy-permitted resolution、CF 增长和任务完成情况。

### 17.3 Verifier error

分布迁移完全依赖测量。如果 compliance evaluator 存在系统偏差，我们观察到的迁移可能是标签迁移，而非行为迁移。

### 17.4 Unsupported permission induction

Learner 可能把 VS 中被判违规的行为总结成新的行动许可，尤其是在错误理解“成功经验”时。需要 directional repair validation。

### 17.5 Constraint erosion during replace

替换一条旧规则可能无意中删除其保护的其他行为。需要 preservation set 和 regression tasks。

### 17.6 Skill bloat

持续增加规则可能造成冲突、注意力稀释和执行成本上升。应限制 edit budget，并测量 Skill 长度、推理成本和遵循率。

### 17.7 Selection overfitting

反复在固定 Selection tasks 上选择版本会逐步过拟合，即使 Selection feedback 不直接进入 Learner。需要限制演化次数、使用独立 Test，并考虑 rotating validation 或 nested protocol。

## 18. 下一阶段最优先的研究任务

1. 冻结 ST-WebAgentBench 主环境、任务划分、policy evaluator 版本和基础模型；
2. 把四状态分布与完整 transition matrix 设为每次实验的标准输出；
3. 对 Parent/Candidate 进行多次 matched rollout，估计自然方差；
4. 正式定义 HTR、GRR、severe violation tail 和 worst-group CuP；
5. 建立一批人工审计 trajectory，用来测量 ST-WebAgentBench compliance evaluator；
6. 为 proposed edit 增加 directional repair 与 preservation validation；
7. 比较 Outcome-only、Filtered、Pair-aware Governed 三种学习信号；
8. 冻结方法后运行独立 Test；
9. 展示至少三个完整传播或修复链：

```text
source trajectory pair
→ behavior attribution
→ Skill clause / patch
→ held-out trajectory transition
→ verifier evidence
```

10. 最后再开展 policy shift、cross-model 或 adversarial user 实验。

## 19. 可能的论文表述

论文可以围绕以下主张组织：

1. Skill evolution 改变的不是单一分数，而是 Agent 在 task success × compliance 空间中的联合行为分布；
2. Outcome-only learning 可能把概率质量运输到 violating success，形成 reward-compatible corruption；
3. 四象限 experience decomposition 与 matched trajectory attribution 可以分离有效能力和违规捷径；
4. Evidence-grounded bounded edits 与 asymmetric distributional gate 可以阻止有害迁移；
5. ST-WebAgentBench 提供成熟的二维测量环境，使上述现象与方法能够被系统评估。

一个候选标题是：

> **Governed Skill Evolution as Constrained Distribution Transport over Agent Trajectories**

另一个更偏现象的标题是：

> **When Better Task Performance Moves Agents in the Wrong Direction: Distributional Governance of Evolving Skills**

## 20. 结论边界

当前最合适的结论是：

> Governed Skill Evolution 可以被建模为对 trajectory distribution 的受约束干预；现有原型已能记录四状态迁移，并拒绝部分以合规退化换取成功率的 Candidate。

当前还不能得出：

- outcome-only Skill 必然传播违规；
- 当前 Governed 方法已经在独立 Test 上优于所有 baseline；
- 单次 Selection 的变化具有稳定因果性；
- ST-WebAgentBench evaluator 等同于无误差的合规真值；
- 当前系统可以无限期自主进化或直接部署。

后续研究必须以重复运行、独立 Test、verifier audit、matched transitions 和 clause-level attribution 来逐步加强这些结论。
