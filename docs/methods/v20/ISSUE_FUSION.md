# 问题融合

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [v20 第 3 步：直接消费问题 Memory 的 Issue Fusion](#v20-issue-fusion)

<a id="v20-issue-fusion"></a>

## v20 第 3 步：直接消费问题 Memory 的 Issue Fusion

日期：2026-10-04。此步实现 v20 的只读 Issue Fusion 输入与响应边界，独立于 v19 的 Fusion 和 Historical Review。

### 做什么

`build_issue_fusion_input` 同时接收当前轮 `CurrentFindings`、v20 问题 Memory 和当前 Parent Skill。模型视图只展开：

- 当前 Findings 的稳定引用、问题类型、简短陈述、适用范围、维度和不确定性；
- 每个问题的 `problem`；
- 每个尝试的 `approach`、`assessment` 和派生的当前规则绑定；
- 当前 Parent 的完整规则引用目录。

Memory 中累计的 `source_refs`、`edit_refs`、原始轨迹和 raw response 不进入 Fusion prompt。它们仍保留在 Memory 或完整档案中，由下一步局部 Evidence Review 按选中的问题/尝试重新打开。

### 三种入口

1. 当前 `OBSERVED_PROBLEM` 可形成新的问题，或与一个已有 Memory 问题合并。
2. 已有问题可以在当前 Findings 出现时被重新选中；历史尝试的当前规则绑定只有在调用方提供、且能验证到当前 Parent 的 edit history 时才推导。缺少历史时显示 `UNRESOLVED`，不推导为 `ABSENT`。
3. 没有当前失败时，已有问题仍可作为 history-only 议题被选中，继续进入局部核验。

响应只能选择 `PROPOSE` 或 `NO_EDIT`。它保留稳定的 `memory_issue_refs` 和 `memory_attempt_refs`，另由程序分配本次请求的 `proposal_id` / `proposal_issue_id`，避免把一次请求的提案身份当成跨轮 Memory 身份。Fusion 不写 Memory、不产生 gap、编辑计划、Candidate Skill 或 VERIFIED 结论。

每个当前 `OBSERVED_PROBLEM` 必须在一个 issue 中明确处置；其它 Findings 可以支持多个 issue，也可以带理由放入 `unassociated_findings`。未被本轮选中的历史问题不要求重新生成结论，也不会被删除或标记为已解决。

### 接口与验证

实现位于：

- `src/skill_evolution/v20/issue_fusion_v20.py`
- `src/skill_evolution/v20/issue_fusion_prompt_v20.py`
- `tests/skill_evolution/v20/test_issue_fusion_v20.py`

请求使用 `ISSUE_FUSION_INPUT_V20/<sha256>`；响应使用 `PROPOSAL_V20/<sha256>`。Prompt 可以使用请求内短别名 `F01`、`I01`、`A01`、`R01`，校验时恢复为稳定引用；别名只在本次请求内有效。

测试覆盖 compact Memory、当前问题与 history-only、已部署方案的未解析绑定、稳定 ID 与提案 ID 分离、问题覆盖、尝试归属、规则引用和别名越界。此步没有模型调用、Evidence Review、Memory 写入或多轮调度。

### 第 4 步：局部 Evidence Review 与修改生成

第 4 步新增 `evidence_review_v20.py` 与 `local_generation_v20.py`。Fusion 的每个 `PROPOSE` 会绑定一个局部输入：问题下的全部 attempts、显式 source/edit 依赖、涉及的原始事件、同一 trajectory 的完整事件、当前规则和可见工具/政策。未选中的问题、无关 trajectory 和隐藏评测信息不会进入该输入。

Evidence Review 仍只返回 `VERIFIED` 或 `NO_EDIT`。`VERIFIED` 必须给出一个有界的 `MISSING`、`NEEDS_REVISION` 或 `SHOULD_REMOVE` gap；引用必须来自已加载原始事件，已知 counterevidence 不能省略。历史 attempt 是审阅上下文，不是自动授权；重试旧方案时必须在审阅理由中回应已有限制。

修改生成复用既有确定性 target/splice 规则，但使用独立的 v20 plan 和 editor packet。所有 PROPOSE 必须完成局部 Review 后才能编译；同目标同操作合并并保留全部 proposal 来源，REPLACE 与 DELETE 冲突直接停止。纯 DELETE 由程序确定性执行，不调用 Editor；Editor 返回 `UNABLE` 或网络/结构失败时不产生 Candidate。

该步骤不提交 Memory、不执行 Gate/Monitor、不承担多轮恢复。它只产生可验证的 Candidate 阶段产物，供第 5 步原子闭环接入。

### 第 5 步：多轮闭环与离线验证

第 5 步新增 `campaign_v20.py`、`offline_v20.py` 和 `scripts/runs/v20/run_v20_offline.py`。campaign 使用独立的 v20 campaign head，逐轮绑定 Parent、Memory head、Generation audit、Gate 回执和 retained Skill。Candidate Evolution、Attribution、Monitor 由受信 `post_generation` 回调接入；它们的私有数据不会进入问题 Memory。

提交采用可恢复的两阶段标记：先计算并提交问题 Memory revision，再发布 retained Skill 与 campaign head；进程在中间退出时，下一次 `resume=True` 只验证 pending marker、Memory ref 和 Skill digest 并完成发布。Memory 更新为空时不会凭空增加 revision，但轮次仍保留在 campaign head 中。

离线验证只读现有 v19 JSON/JSON.GZ 产物。无法从 v19 可靠得到局部 edit 归属时，转换只保存问题记录、保留空 attempts；不会把整包结果或历史摘要伪造成 v20 的 attempt，也不会声称离线转换是 v20 实验成绩。命令示例：

```bash
python scripts/runs/v20/run_v20_offline.py \
  --artifact path/to/v19-artifact.json.gz \
  --run-id offline-v20 \
  --output offline-report.json
```

### 第 6 步：独立 Pilot 与匹配对照实验

第 6 步新增 `pilot_v20.py` 与 `comparison_v20.py`，先把工程可运行性和机制有效性拆成两个边界清晰的阶段。

`run_v20_pilot` 在独立目录中创建 v20 Pilot binding、任务 manifest 和 campaign 子目录。Pilot 默认只跑 1 轮（最多允许 2 轮），绑定初始 Skill、任务集合、模型和 seed；恢复时这些绑定必须完全一致。Pilot 的输出只接受数值型、面向学习侧的指标，并明确标注 `ENGINEERING_PILOT_OBSERVATION_NOT_MECHANISM_EFFECTIVENESS`。它用于确认 v20 闭环能独立启动、提交、恢复和产出报告，不把 v19 四轮结果当作 v20 成绩。

`run_v20_comparison` 使用同一份排序后的任务 manifest 和 seed，分别调用 `v20_memory` 与 `no_memory` 条件。两种条件拥有独立输出目录；每个任务必须提供相同名称的数值指标，程序计算逐任务差值、均值、胜/平/负，并将报告边界固定为 `MATCHED_OBSERVATIONAL_COMPARISON_NOT_CAUSAL_PROOF`。条件回调可以保留私有 Monitor/Gate 资料，但比较报告只保存状态、公开任务指标和可选 artifact 引用。

实现和测试：

- `src/skill_evolution/v20/pilot_v20.py`
- `src/skill_evolution/v20/comparison_v20.py`
- `tests/skill_evolution/v20/test_pilot_v20.py`

本步仍不引入每轮预算、压缩或信息损失检查；长期 token 控制继续由简明问题 Memory、局部消费和完整证据留档的边界承担。Pilot 通过后才允许启动匹配对照；对照结果仍需结合任务级分布和重复运行解释，不能仅凭一次均值变化宣称因果有效。

### 第 7 步（当前）：冻结 Pilot、Benchmark 适配与无模型预检

第 7 步冻结配置于 `experiments/methods/v20/v20_pilot_001/config/config.json`：复用 benchmark v4 的固定文件和 seed=200，Evolution 使用 train 36 个任务，私有 Monitor/Gate 使用 monitor 45 个任务，Pilot 最多 2 轮、最多 8 个 worker。配置保存 benchmark config、manifest 和初始 Skill 的 SHA-256；这些文件任一漂移都会在适配器初始化时停止。

`benchmark_adapter_v20.py` 是 v20 唯一的真实 Benchmark 接线层。它复用 `BenchmarkEvolutionV19` 的冻结环境准备/评估接口和 `BenchmarkMonitorV19` 的私有 Gate 接口，但只向 learner 暴露 train split；monitor split 只能通过 `run_private_gate` 进入私有目录。适配器同时生成排序固定的 Pilot task manifest，供后续 Pilot binding 使用。

无模型预检命令：

```bash
PYTHONPATH=src python scripts/runs/v20/run_v20_preflight.py \
  --output artifacts/methods/v20/v20_pilot_001_preflight
```

预检为每个 split、每个冻结 Skill 构造真实环境和部署配置，但不执行 Orchestrator rollout，报告中的 `model_calls` 必须为 0。输出包括 `preflight.json`、Evolution 预检、私有 Monitor 预检和完整 adapter manifest；报告边界固定为 `NO_MODEL_ROLLOUTS_NO_MECHANISM_RESULT`。预检通过后才允许接入真实模型 transport 和启动 Pilot。

本次实际预检产物位于 `artifacts/methods/v20/v20_pilot_001_preflight/preflight.json`：Evolution 36 个任务、108 个准备实例；private Monitor 45 个任务、135 个准备实例；总 `model_calls=0`。这只证明冻结环境和边界可以被构造，不代表 v20 机制效果或 Pilot 成功。

### 第 7 步（接线）：真实 round factory、post-generation 与统一入口

`runtime_v20.py` 现在把真实阶段串成一个 v20 round：Parent Evolution 使用冻结 train split，随后运行 grouping、current discovery、v20 Issue Fusion、局部 Evidence Review/Editor，并将 `GenerationInput` 交给 v20 campaign。所有当前发现和 Fusion 请求都使用可恢复的 call 目录。

Candidate 生成后，`post_generation` 通过适配器在 train split 重放 Candidate，生成结构性 local attribution（效果保持 `UNRESOLVED`），再在 monitor split 私下执行 Parent/Candidate Gate，并把公开的 Candidate 摘要、attribution 和 Gate 回执与问题 Memory 增量更新分开。默认 Memory mapper 只保存生成 edit 的问题归属、尝试描述和来源引用，不把 Monitor 私有结果写入 Memory；需要更严格语义映射时可显式注入 `memory_update` 回调。

统一入口为 `scripts/runs/v20/run_v20.py`：

```bash
PYTHONPATH=src python scripts/runs/v20/run_v20.py run \
  --output artifacts/methods/v20/v20_pilot_001

PYTHONPATH=src python scripts/runs/v20/run_v20.py resume \
  --output artifacts/methods/v20/v20_pilot_001
```

入口只接受冻结配置，`run` 拒绝覆盖已有目录，`resume` 校验 campaign binding 后继续未完成阶段。本次只完成接线和构造测试，没有执行上述真实模型命令。
