# v19 第 3 步：Candidate 的 Evolution 配对回放

本步提供独立 v19 回放模块：复用生成 Candidate 所用的完整 Parent Evolution 观察，在相同训练任务和执行条件下运行完整 Candidate，产出可供后续归因使用的 ReplayPair。没有修改 v18，也没有接入 edit 归因、持续 Memory、Monitor Gate 或完整 campaign。

## 接口与调用顺序

实现：`src/skill_evolution/evolution_replay_v19.py`；benchmark v4 后端：`src/skill_evolution/evolution_benchmark_v19.py`。

1. `run_parent_evolution(run_id=..., round_id=..., parent_skill=..., backend=..., artifact_dir=...)`：记录当前轮完整 Parent 训练批次。
2. `load_parent_experiences(...)`：校验后将同一批观察转成现有 `CapturedGroupingExperience` 与 `GroupingScope`，供生成 Candidate 的流程使用；本函数不调用 Grouping/Diagnosis 模型。
3. Candidate 生成后，使用第 2 步的 `build_edit_ledger` 建立账本。
4. `run_candidate_replay(ledger, backend=..., parent_dir=..., artifact_dir=..., history=...)`：验证账本、Parent 版本和全量训练产物，再运行 Candidate，返回不可变序列化的 `ReplayBatch`。
5. `load_candidate_replay(...)`：新进程中只读加载，重新从私有证据投影并核对导出结果；不执行轨迹或评分。

运行函数默认 `max_workers=8`，恢复必须显式传 `resume=True`，且使用原输出目录。Parent 与 Candidate 使用不同目录。同一目录有进程锁。历史账本所需的 `history` 必须按第 2 步契约提供。

这些接口已能独立运行，但尚未替换或改动 v18 调度器。旧 v18 轨迹没有本步新增的输入绑定及完成标记，不自动当作可复用的 v19 Parent 导入。

## 配对条件与覆盖范围

- benchmark 后端限定权威 train split 的全部 36 个任务，每个任务一次轨迹；包含成功、失败、合规和违规结果，不允许只选失败任务。Monitor 任务不能通过此后端执行或评分。
- 两侧绑定相同 run/round、任务顺序、seed、冻结 benchmark/config/source 和 Parent/Candidate 原文摘要；Candidate 额外绑定 edit 账本与完整 Parent 批次摘要。
- 在 Candidate 调用模型前，逐题核对数据库初始快照、公开 policy/tools、实际 user simulator prompt、有效执行配置。
- Skill 注入是预期变量：沿用 v18 的 S0/空内容与非空 Skill 部署规则，比较执行配置时仅归一化 agent 包装名称与 Skill 文件路径。
- 数据库快照沿用 v18 的时点：在 `Orchestrator.run()` 初始化之前采集；同时绑定 `task_initial_state` 初始化配方。当前冻结的 36 个训练任务均无 `initial_state`。本步没有声称验证其他 benchmark 的初始化后状态相等。
- 每个任务创建新环境，在该实例上安装冻结 policy，再构造 agent；不全局替换 `Environment.get_policy`。

相同 seed 和配置不意味着外部模型输出完全确定。ReplayPair 记录整份 Skill 改动下的观察差异，本步不把它当作单个 edit 的因果效果。

## 产物与信息边界

每侧私有目录保存 `input.json`、`state.json`，以及 `tasks/T001/` 等逐题目录。逐题保存绑定、初始数据库、公开上下文、实际 simulator prompt、执行配置、轨迹、最终数据库、原始评分和分层完成标记。这些私有文件不能整体传给学习模型。

Candidate 完整完成后才发布 `learner/pairs.json` 与 `learner/validation.json`。学习侧内容包括：

- 匿名 `task_ref`、Parent/Candidate Skill 引用、公开上下文引用。
- 两侧实际观察到的交互事件，以及稳定的事件/监督证据引用。
- Level-0 `success`、`compliant` 标签、两项差值和 CS/CF/VS/VF 状态迁移。
- 全批次配对数、象限与迁移计数、S/C/CS/VF 计数和差值。

不投影真实 task ID、seed、隐藏数据库、私有 simulator prompt 或 evaluator 解释。公开事件中实际观察到的工具参数和结果保留；使用既有信息边界模块校验。本步输出完整 Candidate 级别的配对表现，不生成 edit 效果结论或 ACCEPT/RETAIN。

## 中断恢复与验收

- 已完成轨迹和评分：校验输入及文件摘要后复用，失败标签也视为完成，不重新采样。
- 轨迹完成而评分失败：从 `raw_complete.json` 恢复，只重试评分。
- 轨迹未完成：显式恢复时保留原目录为 `.partial-N`，再执行该任务。
- 任一任务失败：批次为 `INCOMPLETE`，不发布部分 ReplayPair；异常不伪装成任务失败标签。
- 已完成产物被篡改、版本或配对条件不一致：拒绝复用，不自动重跑覆盖。导出恢复也重新核对原始证据，而非仅信任导出文件摘要。

验证结果：本步专项测试与 edit 追踪、v18/v4、经验卡及 Diagnosis 输入回归合计 **141 项通过**。覆盖全量配对、Parent 复用、评分中断恢复、配置错配、错误标签、证据边界、产物篡改和导出恢复。

无模型预检命令（输出目录须不存在）：

```bash
python scripts/preflight_v19_evolution.py --output artifacts/v19_evolution_preflight_003
```

该预检针对 S0、空 Skill、非空 Skill 分别构造 36 个任务环境，核对共 108 个实例的配对条件，模型调用数为 0。记录位于 `artifacts/v19_evolution_preflight_003/preflight.json`；这不是 Candidate 效果实验。真实训练轨迹及后续 edit-level 归因留待后续步骤。
