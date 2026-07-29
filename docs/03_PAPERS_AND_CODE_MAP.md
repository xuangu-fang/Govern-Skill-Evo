# 核心论文与代码地图

版本：2026-07-28  
原则：按研究问题阅读，不按时间堆论文。

## 第一周只读这 6 篇

### 1. τ-bench：理解真实工作流 Agent

**Yao et al., 2024. _τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains._**  
Paper: https://arxiv.org/abs/2406.12045  
Code: https://github.com/sierra-research/tau2-bench

读什么：

- policy、tools、user simulator、database state 和 task 如何组合；
- 为什么 final state reward 不足以完整评价过程；
- pass^k 为什么衡量重复运行可靠性。

读完应输出：τ³ 当前代码里 task → rollout → trajectory → evaluation 的函数路径。

### 2. Trace2Skill：理解从多条轨迹归纳 Skill

**Ni et al., 2026. _Trace2Skill: Distill Trajectory-Local Lessons into Transferable Agent Skills._**  
Paper: https://arxiv.org/abs/2603.25158  
Code: https://github.com/Qwen-Applications/Trace2Skill

读什么：

- 为什么逐条顺序更新容易 overfit；
- parallel local analysis 与 hierarchical consolidation；
- success/error trajectories 各自怎样使用；
- self-create 与 self-deepen；
- transfer 与 OOD 实验。

代码边界：官方代码目前最完整地支持 SpreadsheetBench，并发布 spreadsheet skills；论文中的其他域不一定有同等完整接口。

### 3. SkillOpt：理解受控文本空间优化

**Yang et al., 2026. _SkillOpt: Executive Strategy for Self-Evolving Agent Skills._**  
Paper: https://arxiv.org/abs/2605.23904  
Code: https://github.com/microsoft/SkillOpt

读什么：

- Skill 作为 frozen agent 的 external trainable state；
- bounded add/delete/replace edits；
- held-out validation gate；
- rejected-edit buffer；
- slow/meta update；
- cross-model、cross-harness transfer。

读代码重点：

- `configs/`；
- benchmark adapter；
- trainer；
- reflection / edit application；
- `history.json`、`best_skill.md` 和 step artifacts。

注意：仓库更新很快。当前 PyPI 与 `main` 功能边界不同；研究复现优先 source checkout，并记录 commit。

### 4. AgentPex：理解 outcome 之外的过程违规

**Sharma et al., 2026. _Willful Disobedience: Automatically Detecting Failures in Agentic Traces._**  
Paper: https://arxiv.org/abs/2603.23806

读什么：

- 如何从 system prompt / policy 提取 behavioral rules；
- 如何在 τ² trajectories 上定位程序性 failure；
- 为什么 outcome-only evaluation 漏掉 workflow routing、unsafe tools 和 rule violation；
- 自动 judge 的证据与误差。

这篇与本项目最直接的连接是：Skill learner 需要 process feedback，而不只是 task score。

### 5. MAC-Bench：理解 success/compliance gap

**Zhao et al., 2026. _Beyond Goodhart's Law: A Dynamic Benchmark for Evaluating Compliance in Multi-Agent Systems._**  
Paper: https://arxiv.org/abs/2606.07805

读什么：

- 程序合规与任务目标发生冲突时，Agent 如何取舍；
- Compliance-Weighted Success Rate；
- Machiavellian Gap；
- social-engineering pressure；
- full-trace auditing。

不要直接照搬其多 Agent 包装。我们要研究的是：这种 gap 会不会经 trajectory-to-skill 被固化和传播。

### 6. SkillLearnBench：理解 Skill 学习该怎样评测

**Zhong et al., 2026. _SkillLearnBench: Benchmarking Continual Learning Methods for Agent Skill Generation on Real-World Tasks._**  
Paper: https://arxiv.org/abs/2604.20087  
Code: https://github.com/cxcscmu/SkillLearnBench

读什么：

- 20 个 skill-dependent tasks、15 个 sub-domains、100 个 verified instances；
- skill quality、execution trajectory、task outcome 三层评价；
- one-shot、自反馈、teacher feedback、skill creator baselines；
- 为什么 self-feedback 会产生 recursive drift。

代码注意：Docker 是硬依赖。第一次只 dry-run 1–2 个任务。

---

## 第二周按问题选读

### ToolSandbox：过程中的 milestone 与 minefield

**Lu et al., 2024. _ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities._**  
Paper: https://arxiv.org/abs/2408.04682  
Code: https://github.com/apple/ToolSandbox

价值：

- state dependency；
- intermediate milestones；
- minefields；
- insufficient information；
- trajectory-level dynamic evaluation。

工程注意：仓库安装说明使用 Python 3.9，内置模型名较旧。适合作为第二环境或借用 evaluator 设计，不适合第一天主环境。

### Continual Harness：理解长期在线 harness 自修改

**Karten et al., 2026. _Continual Harness: Online Adaptation for Self-Improving Foundation Agents._**  
Paper: https://arxiv.org/abs/2605.09998

价值：

- harness 不只包含 Skill，还包括 prompt、sub-agent 和 memory；
- reset-free online adaptation；
- embodied long-horizon partial observability；
- process reward co-learning。

与当前项目的边界：它代表长期方向；三个月项目不要同时修改所有 harness 组件。

### VASO：连接 physical AI 与形式验证

**Yang et al., 2026. _VASO: Formally Verifiable Self-Evolving Skills for Physical AI Agents._**  
Paper: https://arxiv.org/abs/2606.05395

价值：

- skill contract；
- formal interface + planner-facing interface；
- model checking counterexample 作为 skill update feedback；
- 物理 Agent 中安全约束与 Skill 演化的结合。

我们的差异空间：

- 自然语言 policy；
- 角色权限；
- 证据义务；
- 人工审批；
- 规则版本变化；
- 形式规则与语义规则混合。

### SkillHone：保留修改决定历史

**Li and Hu, 2026. _SkillHone: A Harness for Continual Agent Skill Evolution Through Persistent Decision History._**  
Paper: https://arxiv.org/abs/2606.08671

价值：

- 不只保存最终 Skill；
- 保存 diagnosis、revision、evidence、outcome 和 rejected alternatives；
- 与我们的 lineage / audit history 直接相关。

---

## 基础论文：只在概念不清楚时补

### ReAct

**Yao et al., 2022. _ReAct: Synergizing Reasoning and Acting in Language Models._**  
Paper: https://arxiv.org/abs/2210.03629

理解最基本的 reasoning/action/tool/observation loop。

### Reflexion

**Shinn et al., 2023. _Reflexion: Language Agents with Verbal Reinforcement Learning._**  
Paper: https://arxiv.org/abs/2303.11366

理解 verbal feedback 如何进入后续尝试，以及单次反思为什么不等于可验证 Skill。

### ExpeL

**Zhao et al., 2023. _ExpeL: LLM Agents Are Experiential Learners._**  
Paper: https://arxiv.org/abs/2308.10144

理解从多次成功/失败经验中提炼可复用 insight 的早期范式。

---

## 代码仓库的使用优先级

| 优先级 | 仓库 | 第一阶段动作 | 不要做什么 |
|---:|---|---|---|
| 1 | `tau2-bench` | 跑任务、读 trajectory、写 adapter | 立刻 fork 并重写 orchestrator |
| 2 | `SkillOpt` | 跑 zero-API proof、小规模 SearchQA、读 gate | 第一周跑完整昂贵配置 |
| 3 | `Trace2Skill` | 读 analyzer/consolidation，复用 prompt 思路 | 假定所有论文 benchmark 都已完整开放 |
| 4 | `SkillLearnBench` | dry-run，后期跑少量任务 | 第一周全量 20 tasks |
| 5 | `ToolSandbox` | 借 evaluator 思路，后期做第二环境 | 把旧模型枚举适配当主研究任务 |
| 6 | `SkillsBench` | 需要更广泛 skill utility 时再用 | 在 POC 阶段引入 Modal 等额外基础设施 |

SkillsBench 代码：https://github.com/benchflow-ai/skillsbench

---

## 论文阅读输出模板

每篇只写一页，回答：

1. 它优化的对象是什么？
2. 它从哪里得到反馈？
3. 它如何决定接受更新？
4. 它保存了哪些中间证据？
5. 它只看 outcome，还是看 trajectory？
6. 它可能怎样吸收错误经验？
7. 哪部分代码可直接复用？
8. 对我们当前 POC 有什么可证伪假设？

禁止只写摘要翻译。

---

## 当前技术地图

```text
Trajectory generation
  └─ τ³-bench / ToolSandbox

Trajectory diagnosis
  └─ AgentPex / MAC-Bench ideas / our dual verifier

Lesson distillation
  └─ Trace2Skill

Skill optimization
  └─ SkillOpt

Skill-learning evaluation
  └─ SkillLearnBench / SkillsBench

Formal physical constraint
  └─ VASO

Our target gap
  └─ compliance-aware trajectory selection
     + evidence-grounded Skill patch
     + task/compliance dual gate
     + policy shift / rollback / lineage
```

---

## 链接核验状态

以上论文、仓库和主要安装入口已于 2026-07-28 按官方 arXiv 页面与 GitHub README 核验。仓库可能快速变化；实际执行时以当前 checkout 的 README、`--help`、config 和 commit 为准。
