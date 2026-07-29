# Governed Skill Evolution

> 让 Agent 从运行经验中学习，同时不把违规捷径、偶然成功和错误归因固化成 Skill。

本项目由教师与学生共同建设，目标是研究一种**可控、可验证、可追溯的 Skill 自进化 Agent 框架**。当前仓库处于研究启动阶段：我们首先验证问题是否真实存在，再逐步实现方法，而不是一开始就搭建庞大的“自进化系统”。

## 我们到底要研究什么

Tool-using Agent 在完成任务时会产生完整轨迹，包括对话、推理、工具调用、环境反馈和最终结果。现有方法可以把这些轨迹总结为可复用的 Skill，但“任务成功”并不等于“过程正确”。

一个 Agent 可能在成功完成任务的同时：

- 跳过身份核验或必要证据；
- 越权调用工具或访问数据；
- 先做不可逆操作，再补齐审批；
- 在用户催促下绕过流程；
- 因偶然环境状态成功，却总结出错误的一般规则。

因此，本项目的核心研究问题是：

> 当 Agent 从轨迹中学习 Skill 时，如何提高任务能力，同时避免吸收和放大程序性违规？

我们的初步思路是把评价拆成两个维度：

1. **Task verifier**：任务是否完成、最终状态是否正确；
2. **Compliance verifier**：过程是否满足 policy、权限、顺序、证据和审批要求。

候选 Skill 不会自动进入生产版本，而要经过证据追踪、受限修改、held-out validation、task gate 和 compliance gate，最终被接受、拒绝或隔离。

## 研究路线

项目按四个可以独立演示和评测的层级推进：

| 层级 | 目标 | 关键产物 |
|---|---|---|
| Level 0 | 理解并结构化 Agent 轨迹 | trajectory summary 与人工审计 |
| Level 1 | 从少量轨迹生成候选 Skill | 可人工检查的 `SKILL.md` |
| Level 2 | 在验证集上受控优化 Skill | bounded patch 与 accept/reject 记录 |
| Level 3 | 引入过程治理 | 双 verifier、双 gate、provenance 与 rollback |

第一阶段主要使用：

- [`tau2-bench`](https://github.com/sierra-research/tau2-bench)：产生带 policy、工具调用和状态变化的真实工作流轨迹；
- [`SkillOpt`](https://github.com/microsoft/SkillOpt)：理解 bounded edit 与 validation gate；
- [`Trace2Skill`](https://github.com/Qwen-Applications/Trace2Skill)：参考多轨迹局部 lesson 提取与合并；
- SkillLearnBench、ToolSandbox：用于后续泛化和过程评测。

我们暂时不做复杂多 Agent 组织自演化、端到端训练、真实支付系统接入，也不同时优化 Skill、memory、工具和角色。第一篇工作的关键是先证明：**成功轨迹可能教给 Skill 错误的经验，而且这种影响可以被测量和治理。**

## 第一次 meeting 要达成什么

第一次 meeting 结束时，学生应该能回答：

1. Agent、environment、tool、state、trajectory、policy 和 verifier 分别是什么；
2. 为什么只看最终成功率可能漏掉过程违规；
3. trajectory 如何变成候选 Skill；
4. 为什么候选 Skill 需要 validation gate、来源记录和回滚；
5. 前三天要交付哪些可检查的 artifact。

建议 meeting 按下面的顺序进行：

1. 用一个“成功但跳过身份核验”的例子说明问题；
2. 讲解 task success / compliance 四象限；
3. 介绍 Level 0–3 的研究路线；
4. 展示十天 POC 闭环；
5. 分配 Day 0–3 的任务和交付物；
6. 约定实验记录与 Git 协作方式。

## 学生从哪里开始

请按顺序阅读，不要先自行重构框架：

1. [`docs/00_README_FIRST.md`](docs/00_README_FIRST.md)：启动规则、前三天目标和安全底线；
2. [`docs/01_PROJECT_NARRATIVE.md`](docs/01_PROJECT_NARRATIVE.md)：完整研究问题、假设、边界和 Go / No-Go 条件；
3. [`docs/05_TAU_BENCH_POLICY_COMPLIANCE.md`](docs/05_TAU_BENCH_POLICY_COMPLIANCE.md)：理解 τ-bench 已有什么 policy、缺什么 compliance 定义；
4. [`docs/02_HANDS_ON_TODO.md`](docs/02_HANDS_ON_TODO.md)：10 天 POC 的逐日任务；
5. [`docs/03_PAPERS_AND_CODE_MAP.md`](docs/03_PAPERS_AND_CODE_MAP.md)：第一周必读论文及代码定位；
6. [`docs/04_EXPERIMENT_LOG.md`](docs/04_EXPERIMENT_LOG.md)：从安装开始持续填写的实验记录模板；
7. [`CONTRIBUTING.md`](CONTRIBUTING.md)：Git、实验和协作约定。

完整导航参见 [`docs/README.md`](docs/README.md)。

第一周论文阅读只要求完成文献地图中列出的 6 篇。每篇输出一页问题导向笔记，不做摘要翻译，重点回答：优化什么、反馈来自哪里、怎样接受更新、保存哪些证据，以及它可能怎样学到错误经验。

## 学生的第一阶段任务

### Meeting 后 24 小时内

- 完成 `00_README_FIRST`、`01_PROJECT_NARRATIVE` 和 `05_TAU_BENCH_POLICY_COMPLIANCE` 的阅读；
- 检查 `git`、`uv`、Python 与 Docker 环境；
- 在实验日志中填写 Environment 和 Current Snapshot；
- 用自己的话写出当前核心假设与一个可能推翻它的结果；
- 提交一个只包含环境记录和阅读问题的 PR。

### 前三天

- 跑出一条真实的 `tau2-bench` tool-using trajectory；
- 人工审计至少 5 条轨迹的 task success 与 policy compliance；
- 写一份不超过 800 字的人工 Skill；
- 完成有 Skill / 无 Skill 的最小对照；
- 保存命令、模型、代码 commit、原始轨迹和 artifact 路径。

前三天如果没有拿到这四类可检查产物，就先排查环境、任务和轨迹，不继续堆框架。

### 第十天

完成最小研究闭环：

```text
τ³ tasks
→ agent trajectories
→ task/process diagnosis
→ outcome-only candidate Skill
→ held-out rerun
→ success/compliance change report
```

报告必须展示 Skill 来自哪些轨迹、修改了什么，以及 task success 和 compliance 分别如何变化。

## 预期目录

```text
.
├── README.md
├── CONTRIBUTING.md
├── docs/                  # 研究叙事、路线、论文地图、实验日志
├── external/              # 第三方仓库；默认不提交
├── skills/                # 人工与自动生成的 Skill 版本
├── src/
│   ├── adapters/          # 第三方环境的薄适配层
│   ├── trajectory/        # 统一轨迹 schema 与转换
│   ├── verifiers/         # task/process verifier
│   └── skill_evolution/   # lesson、patch、gate 与 lineage
├── experiments/
│   ├── configs/
│   ├── manifests/
│   └── reports/
└── tests/
```

第三方仓库放在 `external/`，不要复制大量外部代码到 `src/`。原始业务数据、密钥、`.env`、大体积轨迹和生成输出不得提交。

## 研究与安全底线

- 区分 **Fact、Hypothesis、Decision**，研究设计变化必须记录在 Decision Log；
- 不用最新一次成功运行覆盖旧结果；
- API key 只放在 `.env` 或秘密管理系统；
- 不向外部模型发送内部业务数据、个人信息或未脱敏轨迹；
- 第一阶段关闭候选 Skill 的自动采用；
- task/process verdict 必须引用 policy 规则和具体 trajectory step；
- 严重违规由人工复核，LLM judge 不直接充当 gold label；
- 所有实验记录代码 commit、配置、模型完整 ID、数据 manifest 和结果路径。

## 当前状态

当前版本是研究起点，不是最终框架。近期唯一优先级是跑通公开环境、理解真实轨迹，并验证 success/compliance gap 是否稳定存在。

如果 H1/H2 无法成立，我们将依据证据转向可审计的 trajectory diagnosis 与 Skill provenance，而不是强行维持“违规传播”的论文叙事。
