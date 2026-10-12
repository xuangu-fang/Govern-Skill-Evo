# 演化回放与修改归因

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [v19 第 3 步：Candidate 的 Evolution 配对回放](#v19-evolution-replay)
- [Pair Attribution v19.2](#v19-pair-attribution)
- [v19 第 4 步：edit-level 效果归因](#v19-edit-attribution)
- [v19 第 2 步：edit 账本与跨轮追踪](#v19-edit-tracking)

<a id="v19-evolution-replay"></a>

## v19 第 3 步：Candidate 的 Evolution 配对回放

本步提供独立 v19 回放模块：复用生成 Candidate 所用的完整 Parent Evolution 观察，在相同训练任务和执行条件下运行完整 Candidate，产出可供后续归因使用的 ReplayPair。没有修改 v18，也没有接入 edit 归因、持续 Memory、Monitor Gate 或完整 campaign。

### 接口与调用顺序

实现：`src/skill_evolution/v19/evolution_replay_v19.py`；benchmark v4 后端：`src/skill_evolution/v19/evolution_benchmark_v19.py`。

1. `run_parent_evolution(run_id=..., round_id=..., parent_skill=..., backend=..., artifact_dir=...)`：记录当前轮完整 Parent 训练批次。
2. `load_parent_experiences(...)`：校验后将同一批观察转成现有 `CapturedGroupingExperience` 与 `GroupingScope`，供生成 Candidate 的流程使用；本函数不调用 Grouping/Diagnosis 模型。
3. Candidate 生成后，使用第 2 步的 `build_edit_ledger` 建立账本。
4. `run_candidate_replay(ledger, backend=..., parent_dir=..., artifact_dir=..., history=...)`：验证账本、Parent 版本和全量训练产物，再运行 Candidate，返回不可变序列化的 `ReplayBatch`。
5. `load_candidate_replay(...)`：新进程中只读加载，重新从私有证据投影并核对导出结果；不执行轨迹或评分。

运行函数默认 `max_workers=8`，恢复必须显式传 `resume=True`，且使用原输出目录。Parent 与 Candidate 使用不同目录。同一目录有进程锁。历史账本所需的 `history` 必须按第 2 步契约提供。

这些接口已能独立运行，但尚未替换或改动 v18 调度器。旧 v18 轨迹没有本步新增的输入绑定及完成标记，不自动当作可复用的 v19 Parent 导入。

### 配对条件与覆盖范围

- benchmark 后端限定权威 train split 的全部 36 个任务，每个任务一次轨迹；包含成功、失败、合规和违规结果，不允许只选失败任务。Monitor 任务不能通过此后端执行或评分。
- 两侧绑定相同 run/round、任务顺序、seed、冻结 benchmark/config/source 和 Parent/Candidate 原文摘要；Candidate 额外绑定 edit 账本与完整 Parent 批次摘要。
- 在 Candidate 调用模型前，逐题核对数据库初始快照、公开 policy/tools、实际 user simulator prompt、有效执行配置。
- Skill 注入是预期变量：沿用 v18 的 S0/空内容与非空 Skill 部署规则，比较执行配置时仅归一化 agent 包装名称与 Skill 文件路径。
- 数据库快照沿用 v18 的时点：在 `Orchestrator.run()` 初始化之前采集；同时绑定 `task_initial_state` 初始化配方。当前冻结的 36 个训练任务均无 `initial_state`。本步没有声称验证其他 benchmark 的初始化后状态相等。
- 每个任务创建新环境，在该实例上安装冻结 policy，再构造 agent；不全局替换 `Environment.get_policy`。

相同 seed 和配置不意味着外部模型输出完全确定。ReplayPair 记录整份 Skill 改动下的观察差异，本步不把它当作单个 edit 的因果效果。

### 产物与信息边界

每侧私有目录保存 `input.json`、`state.json`，以及 `tasks/T001/` 等逐题目录。逐题保存绑定、初始数据库、公开上下文、实际 simulator prompt、执行配置、轨迹、最终数据库、原始评分和分层完成标记。这些私有文件不能整体传给学习模型。

Candidate 完整完成后才发布 `learner/pairs.json` 与 `learner/validation.json`。学习侧内容包括：

- 匿名 `task_ref`、Parent/Candidate Skill 引用、公开上下文引用。
- 两侧实际观察到的交互事件，以及稳定的事件/监督证据引用。
- Level-0 `success`、`compliant` 标签、两项差值和 CS/CF/VS/VF 状态迁移。
- 全批次配对数、象限与迁移计数、S/C/CS/VF 计数和差值。

不投影真实 task ID、seed、隐藏数据库、私有 simulator prompt 或 evaluator 解释。公开事件中实际观察到的工具参数和结果保留；使用既有信息边界模块校验。本步输出完整 Candidate 级别的配对表现，不生成 edit 效果结论或 ACCEPT/RETAIN。

### 中断恢复与验收

- 已完成轨迹和评分：校验输入及文件摘要后复用，失败标签也视为完成，不重新采样。
- 轨迹完成而评分失败：从 `raw_complete.json` 恢复，只重试评分。
- 轨迹未完成：显式恢复时保留原目录为 `.partial-N`，再执行该任务。
- 任一任务失败：批次为 `INCOMPLETE`，不发布部分 ReplayPair；异常不伪装成任务失败标签。
- 已完成产物被篡改、版本或配对条件不一致：拒绝复用，不自动重跑覆盖。导出恢复也重新核对原始证据，而非仅信任导出文件摘要。

验证结果：本步专项测试与 edit 追踪、v18/v4、经验卡及 Diagnosis 输入回归合计 **141 项通过**。覆盖全量配对、Parent 复用、评分中断恢复、配置错配、错误标签、证据边界、产物篡改和导出恢复。

无模型预检命令（输出目录须不存在）：

```bash
python scripts/runs/v19/preflight_v19_evolution.py --output artifacts/methods/v19/v19_evolution_preflight_003
```

该预检针对 S0、空 Skill、非空 Skill 分别构造 36 个任务环境，核对共 108 个实例的配对条件，模型调用数为 0。记录位于 `artifacts/methods/v19/v19_evolution_preflight_003/preflight.json`；这不是 Candidate 效果实验。真实训练轨迹及后续 edit-level 归因留待后续步骤。

<a id="v19-pair-attribution"></a>

## Pair Attribution v19.2

这是独立新版，不修改 `attribution_v19.py` / `attribution_prompt_v19.py` 的单次全局 Attribution，也不改 v18。新实现位于 `src/skill_evolution/v19/attribution_pairs_v19.py`，版本分派位于 `attribution_dispatch_v19.py`。

### 1. 逐 pair 输入和观察

从原有经过账本与 Replay 重验的 learner projection 构造输入；不接受 Monitor 数据。每个请求只包含一对完整 Parent/Candidate 事件、本轮全部 edit 的 before/after、Parent Skill 和这对轨迹的完整公开领域 policy/tools。其他 pair、其他领域 context、edit 的 Diagnosis 来源全文与历史关系不进入模型。

不通过关键词筛选 edit，不丢弃持平 pair，不截断原始事件。`P1` / `C1` 是精确事件引用别名，只在引用字段展开，不替换自由文本。原始 Replay 和原始响应完整保留。

模型输出：

```json
{
  "schema_version": "pair_attribution_response_v19.2",
  "observations": [{
    "status": "ATTRIBUTED",
    "edit_ids": ["EDIT/..."],
    "parent_evidence_refs": ["P2"],
    "candidate_evidence_refs": ["C3"],
    "behavior_comparison": "具体行为比较",
    "reason": "关联依据及必要限制或反证"
  }]
}
```

- `ATTRIBUTED`：必须指定 edit，并引用双侧至少一条 assistant/tool 行为证据。多个 edit 难以分开时作为联合集合。
- `UNATTRIBUTED`：观察到变化，但不能可信关联到 edit；`edit_ids=[]`，仅解释为何不足，不细分原因类别。仍需双侧事件引用。
- 没有相关观察时允许 `observations=[]`。同一个 pair 可以同时保留 ATTRIBUTED 和 UNATTRIBUTED。
- 不让模型输出效果标签、分数、修改建议或后续操作；没有 MORE_CONTEXT。

引用验收只证明结构和来源有效，不证明自然语言关联正确，也不把任务结果变化当成因果效应。

### 2. 逐 pair 保存、预算与恢复

默认并发 2（API 可设 1–8）；单次输入代理预算 32,000，输出上限 24,000，超时 300 秒，SDK 重试 0。输入计数使用 cl100k_base，不能等同网关实际 token。首请求和修复均检查预算，超预算不发送、不截断。

每个 pair 保存 input、initial/request、response、response_complete、result、status。契约失败至多一次修复，原响应、精确错误、修复请求与响应都保存。超时、截断、拒答不进入契约修复，也不转成 UNATTRIBUTED。

单个 pair 失败不会重跑其他 pair；所有 pair 有效后才发布 `attributions.json`，否则整批 INCOMPLETE，不能提交 Memory。`resume=True` 复用已完成响应，并重验输入、Prompt、配置与当前实现摘要；不能混用新旧契约。

无完整响应的调用需显式执行 `archive_uncertain_call(directory, pair_id=..., phase='initial'|'repair')` 后恢复。它保留失败请求和归档 receipt，不替换已完成结果或无限重试无效响应。进程被杀后可先 resume，让不完整调用被识别为 INCOMPLETE；再显式归档。改变协议/预算使用新目录。

完成包使用固定文件清单：input、config、protocol、profile、pair-audit、attributions，以及 validation。`pair-audit.json` 汇集成功调用路径上的原始请求、原响应、修复响应和错误，是 Memory 可独立重验的审计副本；失败尝试继续保存在运行目录。Memory 不必依赖原运行目录存在。

### 3. 确定性聚合、Memory 与调度

按**精确 edit 集合**汇总 ATTRIBUTED 观察，不再调用全局模型。联合证据不转成各成员独立信用。一个集合中同一 pair 的多条观察合成一项 pair 观察，保留 observation IDs，标签只统计一次。

程序按关联 pair 的 success/compliant 两个维度保留正负方向：

| 关联结果 | effect |
|---|---|
| 有正有负，含同一 pair 两维方向冲突 | MIXED |
| 仅正向变化 | BENEFICIAL |
| 仅负向变化 | HARMFUL |
| 有行为关联，但标签均不变 | NO_OBSERVED_EFFECT |
| edit 没有任何可信关联观察 | UNKNOWN |

这些仍是**行为关联范围内的结果标签摘要**，不是隔离单个 edit 后测得的因果效应。无观察不生成 NOT_EXERCISED。UNATTRIBUTED 仅留在 pair 审计结果中，不给 edit 分配效果证据。单独未知记录不会覆盖已有联合记录；只有完全未被关联的 edit 才补 UNKNOWN。

新版不生成 `suggested_followup`。局部比较和理由随 observation 保留；后续如何处理仍由 Memory Review、Fusion、Evidence Review 决定。旧 Memory 的该字段继续可读，检索兼容字段缺省。旧/新归因可在同一 Memory 链上提交、读取、幂等恢复，Gate 与保留 Skill 的原子提交逻辑不变。

新 `campaign_config()` 默认 `attribution_protocol='pair'`；新 CLI 默认 pair：

```bash
# 只做新 campaign 预检，不调用模型
python scripts/runs/v19/run_v19_v4.py --generation-protocol local --attribution-protocol pair --pilot
```

旧版可显式选择 `--attribution-protocol legacy`。原实验脚本若直接导入 `attribution_v19.run_attribution`，仍执行旧版，不会暗中切换。当前 Pilot 的源码/协议绑定未迁移；不能直接拿旧 resume 脚本当成新版调用。

已有经过验证的 ledger、backend、Replay 可按下面调用新版（不会重新 rollout）：

```python
from src.skill_evolution.v19.attribution_pairs_v19 import run_attribution

batch = run_attribution(
    ledger, backend=backend, parent_dir=parent_dir,
    replay_dir=candidate_replay_dir, history=history,
    artifact_dir=new_attribution_dir, max_workers=2,
)
```

当前 Pilot 后续切换时，应先记录源码/协议迁移、验证原账本及双侧 Replay 摘要，使用新的 Attribution 目录。无需重跑 Diagnosis、Editor 或 Replay；三次旧超时尝试保留。本次实现没有启动真实模型或 Monitor/Gate。

### 输入统计与验证范围

两轮现有完整 learner input 的只读统计见 `artifacts/methods/v19/v19_pair_attribution_profile_001/`。第一轮 36 对输入最大 24,287 token；第二轮 36 对最大 20,904；均未超预算。第二轮同口径旧版单次约 31.5 万（仅 user 正文约 28 万），新版单次约 1.21–2.09 万；逐 pair 重复公共上下文使整轮累计输入约 54.2 万，不能声称总 token 成本下降。

工程验证覆盖：完整双侧证据与私有数据隔离、引用角色和状态校验、联合归因不拆功劳、持平/冲突维度/UNKNOWN、一次修复、预算与截断、超时隔离和显式恢复、Memory 新旧混合链与两轮调度。构造测试只验证机制，真实语义质量、实际用量和延迟仍需新 Pilot 检验。

### 汇总 v19.3：行为关联与结果分离

逐 pair 模型协议仍为 attribution_pairs_v19.2；ATTRIBUTED / UNATTRIBUTED
输出契约不变。新确定性汇总为 attribution_batch_v19.3，不生成 effect。
associated_pair_outcome_counts 仅记录关联 pair 的成功/合规变化，不能作为
edit 的有益、有害、混合或无效果结论。不同 edit 集合的统计可能重叠，不可相加为贡献。

unattributed_context 保留相同 pair 的 UNATTRIBUTED 观察、解释及原始引用；
edit_ids 仍为空，不转为 edit 归因。旧 relation 以 legacy_relation 保存作溯源，
不能将 SUPPORT 理解为有效性支持。行为相同或结果不变不证明无作用。
旧 v19.2 汇总仍按旧算法恢复与校验；新算法不覆盖历史文件。

Memory 输入 issue_memory_v19.2 对旧历史作事实投影，去掉效果标签，保留原
attribution_id 用于追溯归档。原 Memory 持久化内容不变。Memory Review 四状态
判断具体行为观察或适用条件；reason 需说明具体支持/反驳什么，不判断 edit 好坏。
Issue Fusion / Evidence Review 继续沿用现有输出契约，局部证据包加载相关未归因
观察的原始证据。旧 issue_memory_v19.1 输入按原方式恢复，不能混用检查点。

离线重新汇总（不提交 Memory、不启动实验）：

```bash
python scripts/migrations/v19/reaggregate_v19_attribution.py --source OLD_ATTRIBUTION --output NEW_ATTRIBUTION
```

新目录保存旧调用审计、事实汇总、完成校验及 semantics-migration.json。
已有输出拒绝覆盖。正式运行已提交的 Memory 与代码绑定不能原地改摘要后 resume；
需另行显式迁移运行绑定和 Memory 消费协议。Gate、Replay 和原始逐 pair 响应保持不变。

<a id="v19-edit-attribution"></a>

## v19 第 4 步：edit-level 效果归因

本步实现归因 Prompt、完整 edit 覆盖、引用和结果方向校验，以及一次调用的可审计运行与恢复接口。输入来自第 2 步账本和第 3 步完整配对回放，输出为 `AttributionRecord`。归因是效果关联假设，不是逐 edit 因果干预结果，也不是 Skill 修改授权。

实现文件：

- `src/skill_evolution/v19/attribution_v19.py`：输入构造、响应验收、运行和落盘恢复。
- `src/skill_evolution/v19/attribution_prompt_v19.py`：版本化归因 Prompt。
- `tests/skill_evolution/v19/test_attribution_v19.py`：构造数据测试，未调用真实模型。

### 输入与边界

`build_attribution_input(ledger, backend=..., parent_dir=..., replay_dir=..., history=())` 首先重新校验账本，调用第 3 步 `load_candidate_replay` 从私有检查点重建并验证学习投影，而非信任任意传入的 ReplayBatch JSON。

模型输入包含本轮全部 EditRecord、精确 Parent/Candidate Skill 文本、全部配对轨迹及其公开上下文、Level-0 监督标签和确定性变化量。只有必要的来源摘要用于绑定；不传整个私有账本源、历史 Gate 决策或运行产物目录。`history` 仅参与账本有效性校验，不直接作为模型输入。edit 中的历史关系仍只是来源事实，不能作为本轮效果证据。

Prompt 要求通读成功、退化和持平配对，不截断轨迹、不仅挑失败样本。模型上下文容量不足导致的调用失败会保留为 INCOMPLETE，不自动缩减输入或补造 UNKNOWN。

### 输出与验收

模型只输出 `attribution_response_v19.1` 的 `records`；程序添加 schema、run/round 和绑定完整输入的 attribution ID，返回 `AttributionBatch`。每条记录遵循第 1 步 AttributionRecord 契约。

- **覆盖**：每个 edit 至少出现在一条记录中。联合 edit_ids 只生成一条联合关联记录，不向各 edit 复制独立功劳；同一 edit 可保留多条不同范围的记录。
- **引用**：逐条解析 pair、角色、事件和两侧 supervision_refs；不允许用 source gap、其他轮次、另一角色事件或最终标签冒充本侧行为证据。
- **证据等级**：OUTCOME_ASSOCIATION 可仅引用标签；BEHAVIOR_SUPPORTED 的每项 SUPPORT 必须引用两侧 assistant/tool 的实际观察事件。用户话语或标签本身不足以满足这一结构条件。
- **方向**：对本条记录 SUPPORT/COUNTEREVIDENCE 中的两项结果维度分别检查，正负并存必须 MIXED；不能用净收益掩盖冲突。BENEFICIAL/HARMFUL 分别要求有正向/负向变化且无反向变化；NO_OBSERVED_EFFECT 要求该关联范围标签持平，允许行为变化。
- **未知和未触发**：UNKNOWN 可无 observations，但须 UNRESOLVED/DEFER；NOT_EXERCISED 必须提供两侧范围证据、适用条件和不确定性，仍为 UNRESOLVED/DEFER。缺少找到的证据不等于没触发。
- **建议**：PRESERVE / REVISE / CONSIDER_REMOVE / RETRY / DEFER 均不执行编辑。DELETE 仍需下一轮独立 Diagnosis 授权；本模块不读取 Monitor 或预测 Gate。

严格拒绝未知字段、缺失字段、重复 JSON key、非 JSON 数值常量、重复记录和未覆盖 edit。所有记录必须给出非空解释、适用范围、不确定性和替代解释。

#### 验收能力的界限

产物明确标记 `validation_scope=STRUCTURE_AND_REFERENCES_ONLY`。程序能验证引用存在、属于正确角色、是否覆盖 edit、已引用结果是否冲突；**不能证明自然语言解释正确，也不能证明模型没有漏掉语义上相关的反证**。相关性、适用条件与跨任务反证识别由 Prompt 约束，后续需要真实数据检验。

同样，程序无法仅凭 assistant 消息可靠判断其是实际沟通行为还是因果自述；Prompt 明确禁止把“我检查过了”等自述当作检查证据。通过结构验收不代表这一语义要求已被自动证明。BEHAVIOR_SUPPORTED 始终是关联证据等级，不代表排除了其他 edit、对话变化或采样随机性。

方向校验当前针对 Level-0 success/compliant 的关联范围。标签持平时可记录行为改善/恶化假设，但 effect 使用 NO_OBSERVED_EFFECT，并在解释中保留行为差异；不将未测得的收益伪装成已测得效果。

### 调用和恢复

```python
from src.skill_evolution.v19.attribution_v19 import run_attribution, load_attribution

batch = run_attribution(
    ledger,
    backend=backend,
    parent_dir=parent_dir,
    replay_dir=candidate_replay_dir,
    artifact_dir=attribution_dir,
    history=history,
)
# 只读重验输入、响应、引用和摘要，不调用模型：
restored = load_attribution(
    ledger, backend=backend, parent_dir=parent_dir,
    replay_dir=candidate_replay_dir, artifact_dir=attribution_dir,
    history=history,
)
```

真实调用只在调用者显式运行 `run_attribution` 时发生。本步未执行上述真实调用。默认模型设置沿用既有编辑阶段的配置风格：deepseek-v4-pro、temperature=0、reasoning_effort=high、24,000 输出 token、300 秒超时、SDK 重试为 0；本步未修改 v18 设置。可注入 `transport(request)` 做无网络测试；生产调度留待第 7 步。

目录保存 `input.json`、`request.json`、`response.json`、`response_complete.json`、`attributions.json` 和 `validation.json`。请求绑定 Prompt 和模型配置，响应完成标记绑定输入/请求/响应摘要。只有最后的 VALID 标记及完整摘要、响应重验都通过，才能读取阶段产物；VALID 仅指上述结构/引用范围。

- 已完整完成：显式 `resume=True` 校验后复用，不调用模型。
- 响应已完成落盘、验收或输出写入中断：显式恢复只重验同一响应。
- 模型拒答、截断、格式错误或引用错误：INCOMPLETE，不能转成有效 UNKNOWN，也不进行自动修复。
- 没有可验证的完整响应：恢复拒绝自动重复调用；若明确要新尝试，使用新审计目录，保留旧记录。
- 输入、Prompt 或已记录响应变化：拒绝复用。摘要是审计一致性检查，不是针对可同时改写所有文件者的数字签名。

本步不提交 Memory、不晋升 Skill、不接入完整 campaign。v19 benchmark 后端绑定 v19 源码版本，新增归因源码后，旧源码版本下的预检/运行不能被当作当前版本产物直接恢复，这是已有来源绑定规则的预期行为。

### 验证

新增 49 项专项测试，覆盖六类效果、联合与分范围记录、反证/维度冲突、UNKNOWN 与失败区分、角色引用、全部 edit 覆盖、空 Candidate DELETE、模型失败、响应恢复、篡改和 Prompt 漂移。连同前序 v19 和相关 v18/v4 回归共 190 项通过。

全部使用构造轨迹和注入 transport，真实模型调用为 0。没有新增消融或多组实验；归因语义质量尚未经过真实模型实验验证。

<a id="v19-edit-tracking"></a>

## v19 第 2 步：edit 账本与跨轮追踪

日期：2026-09-21。状态：第 2 步独立实现；没有接入 v19 运行调度、训练回放、归因模型或持续经验 Memory。

### 1. 实现范围

- `src/skill_evolution/v19/edit_tracking_v19.py`：生成/重验完整 edit 账本、确定性重建 Candidate、核验历史连续性、生成当前规则来源视图。
- `src/skill_evolution/v19/edit_tracking_store_v19.py`：账本与跨轮审计快照的不可覆盖保存、摘要校验、读取后重验。
- `tests/skill_evolution/v19/test_edit_tracking_v19.py`：构造的多轮操作、边界和故障测试。

仅以只读方式复用现有 Compiler / Editor 的纯函数接口和引用解析。v18 文件、Prompt、配置与历史产物不变；模块不调用模型、回放任务或 Monitor。

依据：[第 1 步数据契约](DATA_CONTRACT.md#v19-data-contract-and-flow)。本步实现其中的 EditRecord 与跨轮追踪部分；ReplayPair、AttributionRecord、RoundMemoryRecord、MemoryContext 尚未实现。

### 2. 生成完整账本

入口：

```python
from src.skill_evolution.v19.edit_tracking_v19 import build_edit_ledger

ledger = build_edit_ledger(
    run_id="v19-example",
    editor_input=editor_input,       # 当前已绑定的 EditorInput
    raw_response=raw_response,      # 纯 DELETE 为 None
    candidate_skill=candidate,     # 精确原始文本，包括空字符串
    history=(),                    # 已完成决策的先前轮次，按时间排列
    related_history=(),            # 显式的修改意图关联，可为空
)
```

输入首先经过既有 Compiler 来源/计划检查和 Editor 确定性应用校验。应用结果必须逐字等于给定 Candidate；NO_UPDATE、UNABLE、无效计划或错误文本都不能发布账本。一个合法 Candidate 的所有单元必须完整记录，纯 DELETE 也产生账本。

`EditLedger` 是不可变的序列化输入/输出容器；`.source` 和 `.payload` 每次返回新对象，不向调用方暴露可原地篡改的内部字典。

每条 EditRecord 保存契约要求的操作、原始目标块、实际应用的 after_text、gap 引用、来源证据和历史关系。after_text 包含应用器补齐的末尾 LF；原始模型响应另外保存在输入审计中。段间分隔符按同一应用规则重建，不把它们误标为某条规则的语义内容。

`edit_id` 绑定 run、round、完整计划摘要、Candidate 摘要及原始单元索引。额外绑定 Candidate 摘要是必要的：同一个计划可以被 Editor 表达成不同文本，这些不能共享同一个修改身份。

所有记录再次经 v19 文本拼接重建 Candidate，与既有应用器的结果对照。CRLF、Unicode、非连续目标和非目标原文均保留；不做全文格式化。

### 3. 证据与历史关系

`source_gap_refs` 指向原始 Diagnosis 和 gap_index。`source_evidence_refs` 使用 v19 的 EVIDENCE ID，绑定 run、round、Diagnosis、引用类型和原引用；账本中的 evidence 目录保存解析后的轨迹事件或可见 policy。不会把同名的跨轮局部引用当成同一证据。

完整原始 Diagnosis 输入、来源元数据、原始响应及计划保存在账本输入审计中。读取时重建并重新验证，不能仅信任 `VALID` 或已经落盘的来源摘要。

`related_history` 的输入形式：

```python
related_history = [{
    "edit_unit_index": 0,
    "prior_edit_id": earlier_edit_id,
    "relation": "RETRIES",          # 或 REVISES / REVERTS
    "basis_refs": [earlier_evidence_id],
}]
```

校验同 run、较早轮次、有效单元索引、非空唯一依据及引用归属。依据必须来自这次修改或所关联历史修改的来源证据；不接受 Monitor 引用、任意字符串、同轮/未来 edit 或重复冲突关系。

当前还没有 AttributionRecord，因此本步不接收尚不存在的归因 ID。第 4–6 步接入时，应通过有类型且可解析的归因来源扩展依据目录，不通过放开任意引用绕过验收。

关系只记录修改意图，不证明语义正确、已解决或已经部署，也不授予新的修改范围。即使没有显式关系，已接受修改对已有文本的实际覆盖仍会被结构追踪发现。

### 4. 决策、内容绑定与来源分别表达

```python
from src.skill_evolution.v19.edit_tracking_v19 import DecidedEdits, trace_edit_history

history = (DecidedEdits(ledger, "RETAIN"),)
view = trace_edit_history(history)
```

`DecidedEdits` 是可信调用方传入的已完成整包决策；本层只校验 ACCEPT / RETAIN，不伪造或代替 Monitor 验证。后续调度负责只在 Monitor COMPLETE 后提供真实决策。

历史链校验：轮次不可重复、run 一致、下一轮 Parent 精确等于上一轮保留 Skill；历史绑定摘要包含之前每个账本和决策，不能替换、重排或遗漏先前轮次。首个历史轮次的 Parent 作为本次追踪起点，不假定它必然是空 Skill。

视图逐项报告：

- 原始整包 gate_decision，永久保留 ACCEPT / RETAIN 的事实。
- binding_status：EXACT / PARTIAL / ABSENT / UNRESOLVED。
- 当前可定位的 rule refs、可能位置和结构后继规则。
- 后续实际接受的结构修改（REPLACE / DELETE 等）及显式意图关系；拒绝的意图仍保留，但不改变当前文本来源。

**绑定采用保守的字面规则：**

| 状态 | 实现语义 |
|---|---|
| EXACT | 完整应用文本在当前 Skill 中有唯一的行边界匹配；DELETE 检查原来被删除的目标块 |
| PARTIAL | 完整文本已不在，但仍能唯一匹配其中的完整 Markdown 规则块 |
| ABSENT | 没有完整/部分文字匹配，也没有需要保留为未知的当前结构后继或已接受关联后继 |
| UNRESOLVED | 文本重复、部分匹配有歧义，或内容已改写但存在结构/显式关联后继，无法判定语义保留程度 |

EXACT 是文本事实，不证明原 edit 被部署过。例如被拒绝的修改后来由另一轮重新加入，旧记录可以同时为 gate=RETAIN 和 binding=EXACT；实际 writer 是新 edit。

DELETE 的绑定对象为被删目标，after_text 为空不参与匹配。原内容后来重新出现时可以是 EXACT/PARTIAL，而不能把 DELETE 解释成一条“现存新增规则”。

PARTIAL 当前支持完整规则块的保留；不对改写句子的语义相似度作猜测。单块部分改写但仍有后继时报告 UNRESOLVED，不静默宣告 ABSENT。

### 5. 当前规则的结构来源

结构追踪按照实际接受的修改范围逐段传播：未触及片段保留 writer；ADD 的文本 writer 是本轮 edit；REPLACE 的新文本 writer 是本轮 edit，ancestor 保存被覆盖片段的 edit 来源；DELETE 移除对应片段。

当前每个规则报告 writer_edit_ids、ancestor_edit_ids 和是否含有初始/分隔文本。对于一次合并多个目标的 REPLACE，ancestor 表示结构上的来源集合，不表示每个祖先都对新规则的每个字有贡献，更不是效果归因。

显式 RETRIES / REVISES / REVERTS 单独报告，不凭意图关系伪造结构来源。重复文本的具体来源可由实际写入路径追踪，但历史内容的泛化文字绑定仍保留歧义。

### 6. 保存与恢复

- `save_edit_ledger` / `load_edit_ledger`：保存 input.json、ledger.json、validation.json。只有最后发布的 VALID 标记及摘要一致时才可消费；读取后仍从来源重新计算全部记录。存在历史关联时必须提供同一历史前缀。
- `save_edit_history` / `load_edit_history`：保存含 ACCEPT/RETAIN 的完整有序历史和可重建视图；不依赖进程内对象继续追踪。恢复后核验整条历史并对照视图。
- 所有目标目录要求不存在；写入中断保留未完成产物，不覆盖旧记录，不自动换成有效 UNKNOWN。
- SHA-256 与来源重验防止意外损坏和错绑，不认证恶意调用方重新伪造的整套证据。实际轨迹真实性与 Monitor 决策来源仍由可信运行时保证。

这里的历史快照是审计存档，**不晋升 Skill、不提交未来的 M_t，也不代替第 5/7 步的原子 Memory 提交**。

### 7. 验证

专项命令：

```bash
python -m pytest -q tests/skill_evolution/v19/test_edit_tracking_v19.py
```

39 项专项通过，覆盖三种操作、空 Candidate、原始索引、精确文本、身份稳定性、正反决策、后续修订/重试/撤销、部分保留、重复文本、历史顺序/Parent 绑定、非法关系、篡改、不可覆盖保存、中断重载及新进程恢复。

连同既有 v18 Compiler、Editor 和 v4 调度相关回归共 154 项通过。没有真实模型调用。

另对现有四轮历史产物做只读离线账本重建，输出位于 `artifacts/methods/v19/v19_edit_tracking_001`。这仅验证真实产物上的追踪能力，不是 v19 运行结果，也没有补跑训练或 Monitor。详细统计以该目录 summary.json 为准。

- 逐轮完成 11、2、3、1 个 edit unit 的重建，共 17 个，包含两轮 ACCEPT 和两轮 RETAIN。
- 重建后的当前 Skill 摘要为 `687bdcd051a4e93a75cee6b034582420d0f99fa838043b04dbb5df38aa7daf9d`，与历史实验最终保留文本逐字节一致。
- 当前绑定为 13 EXACT、4 ABSENT。EXACT 包括后来被修订但完整旧文本仍被保留的历史修改，不能把它当成当前规则数量或有效修改数量。
- 原历史目录 2,689 个文件的摘要未变；v18 冻结 manifest 的 992 个文件均匹配。

下一步为第 3 步：训练集 Parent–Candidate 配对回放。本步只提供其所需的精确 edit 和版本身份。
