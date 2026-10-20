# V22 一轮无历史更新：Diagnosis、Editor 与候选执行

[返回索引](README.md) · [环境接口](ENVIRONMENT_INTERFACE.md) · [机制设计](DESIGN.md)

更新日期：2026-10-14。本文记录第二阶段的独立无历史路径：从 No Skill 的真实 Train 执行形成 Diagnosis，由 Editor 生成完整 Candidate，再通过既有环境入口执行并核对。此路径中 Fusion 原样传递，Memory 为空；它不提供响应认识学习、预条件化变换、完整 Replay 行为分析、正式 Gate 或持续发布。

该路径的后续扩展见 [Editor 要求保持与 Replay 行为反馈](BEHAVIOR_FEEDBACK.md)：`run_round` 默认 Editor v1，并在候选执行前保存观察说明；旧首轮 v0 产物和原始报告保持不变。独立 Replay 入口已实现，本文所述 `run_round` 未接入响应 Memory、历史变换或正式 Gate。

[最小共享表示与模块接口](MINIMAL_INTERFACES.md)现已形成独立的[紧凑反馈学习与后续更新入口](COMPACT_CYCLE.md)，通过 `compact_learning.py`、`compact_update.py`、`compact_cycle.py` 组织有效 Plan、作用认识、要求变更、组级定位和稀疏反馈。新入口没有改写本文描述的 v0／v1 协议与历史产物。以下调用配置、格式和结果均是原阶段记录，不用于说明紧凑协议的运行结果，也不构成其语义正确性或完整闭环的证明。

## 1. 问题、计划与边界

**Question：** 当前轮真实执行能否形成有来源、条件和保留要求的初步修订，并准确落实为可执行 Skill？

**Hypothesis：** 一次完整 Diagnosis 与一次 Editor 构造，配合程序化来源、要求映射和实际 diff 校验，足以贯通最小更新链。这不预测候选一定提高成功率，也不把无历史直接修订称为预条件化收益。

[运行计划](../../../experiments/methods/v22/01_no_history/config/plan.json)在 Parent 执行前保存。固定任务为 `train:0000`、`train:0012`，分别提供照明和清洁任务的当前轮反馈；不按结果增删或挑选任务。每个 Parent 从 No Skill、全新环境开始，最多 50 步。若生成 Candidate，同一固定快照在原定两项任务各执行一次，不根据第一次结果改写 Candidate 或重跑选择成功结果。

默认请求模型 `deepseek-v4-flash`；沿用环境入口的 thinking、输出上限与采样参数。环境请求槽位上限为四次执行共 200 步，另外最多一次 Diagnosis、一次 Editor；每个请求最多六次既有 HTTP 尝试。没有语义／JSON 自动修复重试，所有原始输出和失败成本保留。

2026-10-14 的首次照明 Parent 在第 29 次模型请求发生 `ReadTimeout`，28 步已执行，因此不是完整任务结果。原计划和失败轨迹保留；在重试前另存[恢复计划](../../../experiments/methods/v22/01_no_history/config/plan_recovery.json)，仅允许这个任务按相同配置重试一次。加上失败尝试，总环境请求槽位上限为 250，Diagnosis／Editor 上限不变。`prior_parent_attempts` 用路径与内容 hash 引用失败尝试，计入成本及核对，但不进入 Diagnosis 的完整任务证据。正常任务失败不触发这一恢复，第二次基础设施失败则停止构造。

上一阶段的两步 `smoke` 轨迹不能作为本阶段 Parent。输入要求 `purpose=learning`、Train、No Skill、完整终止及与计划相同预算；`step_limit` 是完整的有限任务结果，仍不能仅凭这一标签认定 Skill 缺陷。

## 2. 当前证据装配

`evidence.py` 先核验轨迹和用途，再从允许的学习视图形成紧凑证据。每个任务包含实际执行身份、目标所在的初始观察、模型与预算、基础提示词／动作窗口，以及逐步的“动作前观察—合法动作—实际动作—反馈—原生结果”。

不再次用 LLM 总结轨迹；移除重复请求包装和模型冗长推理，保留判断动作所需的可见上下文。完整原始轨迹继续通过路径、run ID、内容 hash 和步骤编号追溯。证据引用使用 `{run_id, step}`，其中 0 指初始观察，正整数指对应决策及后续反馈。

来源一次装配后保存为 `evidence.json`，与 `sources.json` 和内容 hash 绑定。Diagnosis／Editor 都只使用这一份执行前证据。候选运行结果不会回填初稿、修改已保存预期，或触发本轮第二个 Candidate。

特别区分两个能力范围：学习器可以检查完整已完成轨迹；执行 Agent 只看到当前观察、合法动作及最近两条前动作观察／动作。Skill 不能假设持久笔记、完整 visited 集合、隐藏对象位置或新增工具。No Skill 仍有基础环境提示词，诊断必须先检查这些既有要求。

## 3. Diagnosis 的首版实现

一次模型调用完成决策片段定位、原因比较、目标与保留行为、条件化策略及边界检查。输出的本地格式为 `v22.diagnosis.v0`，包括：

- `goals`／`preserve`：目标与有效行为，分别引用证据。
- `decision_gaps`：当时可见条件、实际决策与已观察后果。
- `hypotheses`：原因解释、是否可由 Skill 改变、竞争解释和不确定性。
- `proposals`：目标／缺口关联、触发条件、策略、适用范围、保留要求、预期和来源。
- `interactions`／`boundary_checks`：已发现的方向关系与实际／假设边界，不强制制造关系。

合法决定是 `revise`、`no_change` 或 `need_evidence`。后两者正常结束本轮，不调用 Editor；输入、调用或格式错误单独记为技术失败。不能为演示修改而故意弱化初稿，也不能把单次失败解释为已确定因果。

程序检查字段、ID、来源步骤、目标／缺口关联及必要条件。它可以拒绝不存在的引用，不能证明引用在语义上真的支持模型解释。该 schema 是当前最小实现约定，不代表冻结最终更新表示。

## 4. 原样传递与 Editor

将 Diagnosis 的初步方案保存到 `requirements.json`，明确 `mode=identity`，即 \(\widetilde u_t=u_t\)。它没有历史检索、作用信息变换或独立 Fusion 调用。

Editor 在一次调用内检查要求和执行能力、构造完整英文 Skill、检查实际文本边界，并给出逐要求的精确文本映射。输出格式为 `v22.editor.v0`，支持：

| 决定 | 本轮出口 |
|---|---|
| `candidate` | 形成非空且有实际差异的 Skill，全部要求都有对应片段；进入执行 |
| `no_change` | 用 Parent 的真实条款证明要求已满足，保存依据，不生成同义改写 |
| `needs_revision` | 保存受影响要求、限制、反例、替代建议和范围变化；当前最小路径在此停止 |

No Skill 起点下，Candidate 的全部非空白内容必须被至少一项要求的精确文本片段覆盖，包括标题；一项要求可映射多段，多个要求可共用片段。这用于发现无来源新增文本，仍不能自动证明每段都语义正确。

若实现必须改变目标、策略、条件或义务，Editor 输出 `needs_revision`，不会在后台改动 Diagnosis。一般设计允许有界上游反馈，本阶段先保留该停点，不实现多次往返。

## 5. Candidate、实际 diff 与执行

程序将 `candidate_text` 原样写入 `candidate/SKILL.md`，通过环境侧 `load_skill` 获得内容身份。No Skill 在计算文本差异时表示为空字符串，但执行模式仍是明确的 `mode=none`，不创建空文件冒充 Parent Skill。

`actual.diff` 从实际 Parent／Candidate 内容生成，不使用模型声称的 patch。`lineage.json` 保存 Parent 身份、Candidate 全文与 hash、来源、初稿／要求／Editor 内容 hash、真实 diff hash 以及要求映射。Candidate 进入独立 staging 目录，不覆盖默认 Skill。

随后逐项调用既有 `run_task_skill`，使用对应 Parent 的任务、模型、用途及步数预算，固定相同 Candidate。每次执行后核验实际 Skill 与 staging 快照一致，并用 `compare_records` 检查任务、协议、数据、源码、初始可见状态与返回模型。

最终报告列出每项任务的 Parent／Candidate 原生成功、动作数、条件匹配、完整性及成本。两项都完整且条件匹配才标为 `candidate_evaluated`；这表示执行核对完成，不能解读为采用、有效性认证或因果证明。候选执行不完整或条件不匹配为 `evaluation_incomplete`。

本阶段仅报告原生结果与可核对轨迹，不自动生成编辑效果归因或行为响应 Memory。同任务 Train 回放不测泛化，正式采用规则尚未建立。

## 6. 产物、调用与停止

```text
round/
  plan.json / parent.json / sources.json / evidence.json
  calls/diagnosis.json / calls/editor.json
  diagnosis.json / requirements.json / editor.json
  candidate/SKILL.md / actual.diff / lineage.json
  candidate_runs/<task>/skill_<run>/trajectory.json
  report.json
```

未到达的阶段不创建虚假产物。模型请求先保存，原始响应、HTTP 尝试和未知 usage 保留。无效 JSON、错误引用、映射缺失、截断输出和环境故障均保留真实失败，不能转为 `no_change`。本轮不自动重试语义输出，不覆盖已有运行目录；已完成原始轨迹可继续用于离线分析。

成本包括当前轮 Parent 执行、恢复计划明确列出的失败 Parent 尝试、Diagnosis／Editor、Candidate 执行和已记录 HTTP 重试，分别统计环境请求、语义调用、HTTP 尝试、已报告 tokens 与未知次数。没有调用的模块不产生占位成本，模型调用数不按逻辑子步骤倍增。

## 7. 运行与核验

在项目根目录使用已有 `alfworld` 环境。先按固定计划各运行一次 Parent：

```bash
conda activate alfworld
python -m src.adapters.alfworld.run_task_skill \
  --purpose learning --task-id train:0000 --max-steps 50 --output-root /path/to/new_parent_0000
python -m src.adapters.alfworld.run_task_skill \
  --purpose learning --task-id train:0012 --max-steps 50 --output-root /path/to/new_parent_0012

# 路径换成实际 trajectory.json，顺序须与计划一致；run-dir 必须不存在
python -m src.skill_evolution.v22.run_round \
  --parent-trajectories /path/to/parent_0000/trajectory.json /path/to/parent_0012/trajectory.json \
  --run-dir /path/to/new_round --dry-run
python -m src.skill_evolution.v22.run_round \
  --parent-trajectories /path/to/parent_0000/trajectory.json /path/to/parent_0012/trajectory.json \
  --run-dir /path/to/new_round

# 离线检查来源、调用输入／输出、要求、实际diff和配对结果
python -m src.skill_evolution.v22.verify_round /path/to/new_round
```

`--dry-run` 不加载凭据、调用模型或写产物。源码与执行协议应在 Parent 之前固定；Parent 后若修改执行适配器，条件核验会报告差异，不能用同一任务 ID 掩盖版本变化。

本次恢复运行额外传入 `--plan experiments/methods/v22/01_no_history/config/plan_recovery.json`，Parent 输入为照明任务的唯一恢复执行与清洁任务的首次执行。恢复计划是这次基础设施异常的显式记录，不是自动挑选更好结果的机制。

下一阶段应在这一可核对路径上联合接入 Fusion 的实际变换与 Memory 的反馈学习。当前两次更新语义调用是最小路径的约定，不是整个 V22 永久固定的调用次数。

## 8. 2026-10-14 实际验证

本轮已经完成，`candidate_evaluated`，离线核验通过。有效 No Skill Parent 在照明／清洁任务分别成功于 28／7 步；同一 Candidate 分别成功于 7／8 步，已记录执行条件匹配。Diagnosis 与 Editor 各调用一次，未人工改写候选，Candidate 仍为 staging。

含首次超时 Parent，共 79 次环境请求与 2 次更新调用，已报告 285,828 tokens，另有 1 次未知用量；Diagnosis／Editor 合计 63,985 tokens，两次调用仍有明显成本。61 项方法测试与 35 项既有环境测试通过。

完整产物、成本、失败恢复、具体行为观察和语义风险见[本轮报告](../../../experiments/methods/v22/01_no_history/reports/REPORT.md)。照明流程仍有从单条成功序列过度概括的风险，Editor 对回退条件的落实也需要语义复核；结构核验与两项成功不能替代这些判断。后续先补足行为观察和要求保持的检查，再联合接入 Memory／Fusion。
