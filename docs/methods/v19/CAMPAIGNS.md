# 实验组织、恢复与运行维护

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [v19 第 7 步：独立调度、多轮闭环与 Pilot](#v19-campaign)
- [v19 职责拆分第 3 步：独立闭环与 Pilot](#v19-separated-campaign)
- [v19 职责拆分：第 1 步数据契约与独立阶段](#v19-separated-discovery-review)
- [v19 统一 run / resume](#v19-run-resume)

<a id="v19-campaign"></a>

## v19 第 7 步：独立调度、多轮闭环与 Pilot

> 目录整理提示（2026-09-27）：下文旧 Pilot 的命令保留为历史说明，不代表搬迁后可直接 resume。当前产物入口见 [v19 实验索引](../../../experiments/methods/v19/README.md)，原始路径见 [迁移映射](../../../experiments/methods/canonical-paths.json)。

日期：2026-09-22。

**工程闭环已接通并通过构造测试。真实 Pilot 首次因内网 DNS 不可用停止；用户连接内网后已在原目录 resume，正在运行。完整实验未启动。**

### 运行入口与轮次顺序

独立入口 `scripts/runs/v19/run_v19_v4.py`，调度实现 `src/skill_evolution/v19/campaign_v19.py`。每轮严格执行：

```text
Parent Evolution（全部 36 题）
→ 当前经验全量分组
→ Memory 检索 + Diagnosis → Compiler → Editor
→ Candidate Evolution（同一 36 题配对）
→ edit-level 归因
→ 私有 Monitor（全部 45 题 × Parent/Candidate）与 Four-Delta Gate
→ 原子提交完整 Memory 与保留 Skill
→ 下一轮
```

Pilot 最多 2 轮；完整运行最多 4 轮。两者沿用 benchmark v4 固定任务划分和 seed=200，不筛题、不减少成功样本、不引入多组对照。每个任务每个角色一次执行；完整一轮最多 162 条 Agent 轨迹，Pilot 两轮最多 324 条，完整四轮最多 648 条。这不是模型请求数：每条轨迹可包含多次 Agent/User 调用，另外还有评分和学习器调用。

NO_UPDATE 或 UNABLE 提前结束，保留已提交记忆，不伪造新 Candidate、Gate 或记忆轮次。任何执行、评分、引用或版本错误会使阶段 INCOMPLETE 并阻断晋升。

### run / resume 命令

在仓库根目录执行，依赖现有 Python 环境和 `.env` 模型连接配置。默认仅预检，不调用模型。

```bash
# 无模型预检：构造 Evolution/Monitor 的全部环境；每次使用新输出目录
python scripts/runs/v19/run_v19_v4.py --pilot \
  --preflight-output artifacts/v19_campaign_preflight_manual_001

# 新建最多 2 轮真实 Pilot（已有 pilot_001 不应覆盖）
python scripts/runs/v19/run_v19_v4.py --run --pilot \
  --output artifacts/methods/v19/pilot/v19_v4_pilot_002

# 当前 Pilot：Diagnosis 输入修复后，使用显式恢复回执继续
python scripts/runs/v19/run_v19_v4.py --run --pilot --resume \
  --output artifacts/methods/v19/archive/legacy/v19_v4_pilot_001 \
  --diagnosis-recovery artifacts/methods/v19/archive/legacy/v19_v4_pilot_001/diagnosis_recovery/receipt-contract.json

# 完整实验：由用户自行启动；本次没有执行
python scripts/runs/v19/run_v19_v4.py --run \
  --output artifacts/methods/v19/formal/v19_v4_formal_001

# 同一个完整实验的恢复
python scripts/runs/v19/run_v19_v4.py --run --resume \
  --output artifacts/methods/v19/formal/v19_v4_formal_001
```

默认 `--max-workers 8`。如果第一次运行指定其他并发数，resume 必须提供同值。mode、轮次上限、任务/seed/runtime、初始 Skill 和源码摘要绑定到 `binding.json`；不能把 Pilot 原地扩成完整实验，也不能悄悄替换配置继续旧运行。启动新配置需要新目录。新建运行默认拒绝已存在目录。

运行时输出阶段名；详细状态见 `<output>/campaign.json`，实际提交事实以 `<output>/memory/head.json` 为准。保留 Skill 原文在 `head.json` 的 `retained_skill`，没有独立的可漂移 `current_skill.md` 权威副本。

### 冻结与 Monitor 边界

v19 只读使用 `experiments/methods/v18/v18_formal_003/config` 的 benchmark/config/policy/tasks/user prompt/S0。已有 v18 源码及 992 个冻结 manifest 文件保持不变。v19 运行目录保存独立配置、源码摘要与两类运行 manifest；恢复检查当前源码/配置与原绑定一致。

`BenchmarkEvolutionV19` 默认仍只接受 train。新增 `BenchmarkMonitorV19` 使用固定 monitor split 和不同 manifest schema；把它误传入公开 Evolution learner API 会被拒绝。两者共用 v19 的新环境构造逻辑，policy 仅设置于当前环境实例，不全局替换 v18 或 tau2 方法。

Monitor 产物只写入 `round-NN/monitor_private/`，不生成 `learner/pairs.json`。私有执行沿用逐任务轨迹/评分检查点及配对初始状态、policy/tools、实际 user prompt、执行配置核对。完整后只读复用 v18 的纯 `summarize_monitor` Four-Delta 公式：S/C/CS 均不下降、VF 不上升且至少一项改善才 ACCEPT。

对外返回严格的版本绑定回执：COMPLETE、ACCEPT/RETAIN、run/round、两侧 Skill 摘要。分数、转移矩阵、轨迹、私有评分解释不进入 Diagnosis、归因、Memory 学习投影或公开 campaign report。提交后恢复还会重新检查私有 Gate 与 Memory 决策一致，不能通过改写 `campaign.json` 或回执伪造晋升。

这是应用层的信息隔离，不是操作系统级的进程沙箱；可信调度器拥有私有产物读取权限，模型只收到显式学习投影。

### 分组与恢复

新增 `grouping_campaign_v19.py` 复用现有 Grouper Prompt、固定别名映射和最多一次格式/分区修复。v19 用和 Diagnosis 一致的零 SDK 自动重试 transport，并单独保存每次请求/响应检查点；不存在有效分区时不能运行 Diagnosis。

恢复规则：

- 已完成轨迹复用，评分失败只重试评分；真正未完成的轨迹显式 resume 时归档旧尝试后重跑，不按结果好坏重新采样。
- 已完成分组、Diagnosis、Editor、归因响应重验后复用，不重复调用模型。
- 已提交轮次以 Memory head 恢复，不重新运行学习或提交。head 已更新但 round_result 尚未发布时，可从记忆与已验证 Gate 补回报告。
- 未提交的完整归档不可被下一轮读取；提交前后中断都不会出现 Skill 与 Memory 分离。
- 未完整记录的模型调用、格式/引用失败或不确定响应不在普通 resume 中自动重试。需明确的新尝试安排；不能手工伪造完成标记。本次 DNS 失败发生在 Parent 轨迹执行阶段，可直接使用上述 resume 重试未完成轨迹。
- `campaign.json` 是可重建报告，不是提交依据。版本错配、检查点损坏和私有 Gate 不一致会拒绝继续。

### 多轮工程验证

新增 22 项调度专项测试；与前六步及相关 v18/v4 回归合计 293 项通过。构造测试使用真实的 v19 调度、检查点、Compiler/Editor、账本、归因校验和 Memory 提交代码，仅替换环境行为与模型响应：

- ACCEPT 包中的 MIXED 历史 edit 在下一轮形成 REVISES，保留不确定归因。
- RETAIN 包中的潜在有效方向进入下一轮 RETRIES，旧候选不被当作当前 Skill。
- 在 Candidate、归因、Monitor、提交前/后注入中断；恢复没有重复学习器调用、重复提交或丢失记忆。
- Monitor 评分中断复用已完成轨迹；配对配置不一致阻断 Gate。
- 学习器输入中注入私有标记探针，确认 Monitor 数据未进入学习侧；篡改 Gate 回执及版本漂移会被拒绝。
- NO_UPDATE 提前停止不伪造 Gate/Memory；Pilot 不能改 mode 原地扩展。

这些 ACCEPT/RETAIN、MIXED/UNKNOWN 与修订方向是工程 fixture 预设情形，只证明机制和隔离可运行，不是方法有效性证据。

最终版本无模型预检：`artifacts/methods/v19/v19_campaign_preflight_002/preflight.json`。覆盖 36 个 Evolution 与 45 个 Monitor 任务，各构造 S0、空 Skill、非空 Skill 三种部署，共 **243 个环境实例**，模型调用为 0。

### 真实 Pilot 记录

首次启动遇到公司内网 DNS 不通，恢复网络后从原目录继续。随后少量未完成轨迹及归因超时经过显式恢复，保留原尝试；并非按结果筛选重跑。

截至 Diagnosis 输入修复前：

- round-01 完整完成，Gate ACCEPT，Memory 提交一次。归因记录包含 BENEFICIAL 5、MIXED 2、NO_OBSERVED_EFFECT 1、UNKNOWN 2；它们是有限配对观察下的归因，不证明因果效果。
- round-02 Parent Evolution 完成 36/36，分组完成，分成 8 组。
- 首条 Diagnosis 被网关拒绝：输入长度 1,390,836，超过 1,048,566。原请求 user_prompt 为 3,563,946 个 Python 字符；网关长度与字符数不是同一单位。
- 当前经验、历史轨迹、Memory replay 与引用目录含重复表示，尚未产生 round-02 Candidate，不能宣称真实跨轮纠偏完成。

#### Diagnosis 发送表示 v19.2

只改变模型发送投影，签名的 Diagnosis DTO、持久化原始轨迹、Memory 内容和校验规则保持完整：

- 每个观察在 `experiences` 中保留身份、来源轮次、角色、Skill、监督标签和原始 evidence_ref。
- 完整事件正文按内容去重存入 `event_bodies`，通过 `event_body_ref` 读取；引用不是摘要。历史 source_evidence 中的事件也使用同一正文池。
- Memory 的历史 pairs 通过 `experience_ref` 指向这些观察，contexts 通过 context_refs 引用顶层上下文。
- 事件/监督目录用可推导索引表示；返回仍必须使用原始 evidence_ref、supervision_ref，不允许引用正文池编号作为证据。
- 所有归因、支持、反证、不确定性、当前规则绑定和检索选择信息完整保留。无自动裁剪或历史丢弃。

发送前用 `tiktoken` 的 `cl100k_base` 计算包含 system/user/schema 的本地代理 token 数，再预留 25%、24,000 输出 token 和 4,096 封装额度，超过 1,048,566 则本地拒绝，不调用模型。**这是带余量的估计，不是网关的精确 tokenizer，也不保证消除所有网关长度拒绝。** 环境需能加载 tiktoken 及其编码缓存；失败时不绕过检查。

真实 round-02 的 8 组均完成无模型投影及还原核对，首组由 3,563,946 降至 1,457,943 字符；各组代理输入 517,417–570,076 tokens，加余量后的总预算 674,868–740,691。审计见 `artifacts/methods/v19/v19_diagnosis_recovery_001/projection_preflight.json`。

#### 显式源码恢复

普通 resume 仍拒绝源码漂移。本次通过 `source_recovery_v19.py` 仅为 Diagnosis 表示修复建立显式回执：

- 原 `binding.json` 不改写；保存原源码和替换源码的全部摘要，校验允许变更范围。执行 backend 的 prepare/evaluate/_make_manifest/preflight AST 必须不变。
- 原回放执行 manifest 保留身份，实际替换源码独立绑定在恢复回执中；配置、split、seed、Gate、Memory 语义不可借此改变。
- round-01 和 round-02 已完成 Parent/Grouping 文件逐一绑定摘要，原 Memory head 及其后续提交链必须连续。
- 被明确拒绝且没有响应的 generation 整目录保存在 `diagnosis_recovery/failed_generation`。若已经有响应或后续请求，则拒绝使用此恢复。
- 恢复回执写入与归档之间的中断可继续；未来源码漂移、历史文件变化或执行配置变化仍拒绝。

恢复命令：

```bash
python scripts/runs/v19/run_v19_v4.py --run --pilot --resume \
  --output artifacts/methods/v19/archive/legacy/v19_v4_pilot_001 \
  --diagnosis-recovery artifacts/methods/v19/archive/legacy/v19_v4_pilot_001/diagnosis_recovery/receipt-contract.json
```

完整实验未启动。修复后的 Pilot 实际进度和跨轮观察以 `campaign.json`、提交的 Memory 和生成账本为准；工程构造测试不能替代真实结果。

#### Diagnosis 契约提示 v19.3 与第二次显式恢复

v19.2 首条请求已被网关正常处理：实际输入 530,664 tokens，完整返回。随后本地校验发现：当前 8 条经验全部成功，但历史 72 条中有 29 条失败或违规，模型仍选择 NO_ISSUE；9 个历史 edit 返回 10 条 review，其中一项重复。原始响应保存在 `diagnosis_recovery/contract_rejected_generation`，不改写或自动修正。

v19.3 只修订 v19 的提示和发送投影元数据：替换继承提示中可能混淆范围的状态说明，统一为全部当前及选入历史观察；显式给出监督计数和 NO_ISSUE 的允许条件，以及唯一的 `expected_edit_ids` 清单。历史失败不等于当前失败，也不强制修改 Skill；缺乏可支持的当前修改时使用 NOT_ADDRESSABLE，并逐项解释 DEFER。review 单位是 edit，不是 attribution。

原校验器、Compiler、Editor、Gate、Memory、回放语义均未放宽。新增回归复现 NO_ISSUE 范围错误及重复 review，并验证正确无修改结论可通过。第二次恢复保留初次回执和源码，新增链式回执 `receipt-contract.json`，只允许提示及恢复审计代码变化；拒绝归档后续或已接受的 group。

本 Pilot 后续恢复使用：

```bash
python scripts/runs/v19/run_v19_v4.py --run --pilot --resume \
  --output artifacts/methods/v19/archive/legacy/v19_v4_pilot_001 \
  --diagnosis-recovery artifacts/methods/v19/archive/legacy/v19_v4_pilot_001/diagnosis_recovery/receipt-contract.json
```

8 组新请求均完成无模型还原核对、预算与审阅清单检查，见 `artifacts/methods/v19/v19_diagnosis_contract_recovery_001/preflight.json`；992 个 v18 冻结文件保持不变。

#### Diagnosis v19.4：引用类型与整批恢复

v19.3 的第 0–2 组通过本地校验，第 3 组完整返回，但 `memory_review.evidence_refs` 混入政策引用，触发 `MemoryRejected`。v19.4 明确逐字段引用类型并提供正反例：Diagnosis analysis/gap 可保留政策依据，Memory review 只记录原始事件引用。校验仍严格拒绝政策引用，并报告 review 索引、edit ID 和非法引用；不自动删除或替换模型输出。

`prepare_diagnosis_batch(output, previous_receipt, source_before, batch_id, reason)` 是显式整批恢复 API：重新校验已有连续响应前缀，要求末条是本地契约拒绝、前面均有效，且没有 Editor/Candidate/后续阶段；拒绝未完成 transport、混合 prompt 或无失败批次。整个 generation 连同有效响应归档，记录每组校验状态、全部文件摘要、上一回执和旧源码快照。新 generation 从第 0 组开始统一使用新 prompt，绝不拼接旧版本的有效响应。归档后中断通过 pending receipt 恢复，普通 resume 不自动创建新批次。

此次新回执：`diagnosis_recovery/receipt-batch-references-001.json`。后续 resume 使用：

```bash
python scripts/runs/v19/run_v19_v4.py --run --pilot --resume \
  --output artifacts/methods/v19/archive/legacy/v19_v4_pilot_001 \
  --diagnosis-recovery artifacts/methods/v19/archive/legacy/v19_v4_pilot_001/diagnosis_recovery/receipt-batch-references-001.json
```

已完成的 Parent、Grouping、round-01 Memory 不重跑、不改写。前三条旧有效 Diagnosis 保留作审计记录，不作为新批次结果复用。整批重生成增加模型调用成本，须与原 Pilot 轨迹数量上限区分。

#### 新批次 v19.5 协议

v19.5 的每组 Diagnosis 允许最多一次完整留痕的本地契约修复，详见 `V19_MEMORY_GENERATION.md`。已完成且通过的初次结果不产生修复调用；第一次无效且完整的模型输出交由模型修复一次，再次失败即停止。transport 异常不属于此修复协议。新 generation/input.json 显式绑定单次修复协议，旧批次不能普通 resume 原地升级。本次协议实现没有迁移或启动旧 Pilot，以上旧版恢复命令不能直接用于更新后的源码。

<a id="v19-separated-campaign"></a>

## v19 职责拆分第 3 步：独立闭环与 Pilot

> 目录整理提示（2026-09-27）：下文旧 Pilot 的命令保留为历史说明，不代表搬迁后可直接 resume。当前产物入口见 [v19 实验索引](../../../experiments/methods/v19/README.md)，原始路径见 [迁移映射](../../../experiments/methods/canonical-paths.json)。

日期：2026-09-24。

新 CLI 默认 `--generation-protocol separated`，在新目录执行：

```text
Parent Evolution → 当前经验分组 → Current Diagnosis → Current Findings
→ Memory Review → Historical Reviews
→ Reconciliation → 确定性 Compiler → Editor
→ Candidate Evolution → edit-level Attribution → 私有 Monitor/Gate
→ 原子提交 Memory/保留 Skill → 下一轮
```

原 v18、原 Pilot 不改写。Python `campaign_config` 保留 legacy 默认以兼容已有调用；新 CLI 显式选择 separated。协议写入 campaign binding，不能把旧目录原地改成新协议。

### run / resume

```bash
# 新流程无模型预检
python scripts/runs/v19/run_v19_v4.py --pilot \
  --preflight-output artifacts/v19_separated_preflight_manual_001

# 最多两轮独立 Pilot：输出目录必须尚不存在
python scripts/runs/v19/run_v19_v4.py --run --pilot \
  --output artifacts/methods/v19/pilot/v19_v4_separated_pilot_002

# 同一 Pilot 原配置恢复
python scripts/runs/v19/run_v19_v4.py --run --pilot --resume \
  --output artifacts/methods/v19/pilot/v19_v4_separated_pilot_002

# 完整实验仅提供命令，由用户自行启动；本次未启动
python scripts/runs/v19/run_v19_v4.py --run \
  --output artifacts/methods/v19/formal/v19_v4_separated_formal_001

python scripts/runs/v19/run_v19_v4.py --run --resume \
  --output artifacts/methods/v19/formal/v19_v4_separated_formal_001
```

默认并发 8，Pilot 最多 2 轮（与原 Pilot 同一 Evolution 36 / Monitor 45 划分，最多 324 条 rollout）；正式最多 4 轮。若首次指定不同并发，resume 保持相同值。NO_UPDATE/UNABLE 提前结束，不为了跑满轮数制造 Candidate。

### 检查点和一次修复

`generation/` 保存：

- input.json：Parent、Memory head、当前完整分组输入、协议和 v19 源文件摘要。
- current-NNN/：当前 Diagnosis 请求、完整响应标记；对应 current-NNN-findings.json。
- memory-review-input.json、memory-review/、historical-reviews.json。
- reconciliation-input.json、reconciliation/、reconciliation-result.json。
- editor/、generation.json、validation.json。

每个 Current Diagnosis、Memory Review、Reconciliation 和 Editor 调用在本地契约失败时最多允许一次 `-repair-001` 修复，保存原响应、精确拒绝、修复请求和修复响应。仍失败则停止，resume 不产生第三次调用。网络异常、未完成响应、拒答、截断或发送前超预算不属于契约修复；不自动补引用、删除证据或改变结论。

完成响应重验后复用。没有完成响应标记的请求保持不确定，普通 resume 不会悄悄重发；需要明确归档失败尝试后继续。协议、源码、Parent/Memory 或输入改变都会拒绝恢复。空历史不请求 Memory Review 模型；空 findings 加空历史不请求 Reconciliation/Editor。

### 持久化及跨轮来源

新 edit ledger 的可选 generation_audit 保存完整 Current 输入/发现、Memory Review 输入/输出、Reconciliation 输出；其 SHA-256 进入 ledger payload。旧 ledger 无该字段，继续按旧契约验证。恢复新 ledger 时从原始响应重验全部新阶段，重建相同 Compiler/Editor 来源；source snapshots 仅保留提案涉及的完整轨迹，完整审阅证据仍在 generation_audit 中。

Memory 仍通过既有原子提交保存 ledger_input、回放、归因及 Gate 回执。load/retrieve 额外暴露 generation_reviews：历史审阅状态、Current Findings 和全部决策，不覆盖旧记录。不传入 Monitor 轨迹、分数、评分理由。NO_UPDATE/UNABLE 的审阅记录保留在阶段目录，不伪造 Memory 提交。

跨轮链首先由 HR→HO→edit 和 RC→CF/HR 明确保存。仅有结构化关系可核对时，再产生原有关系标签：绑定当前内容的替换为 REVISES，删除为 REVERTS；对未部署内容重新 ADD 为 RETRIES；恢复已删除内容为 REVERTS；重试未生效删除为 RETRIES。仅提供背景、没有匹配目标的历史 review 不强行建立这些 mutation links。标签表达声明来源和结构化动作之间的关系，不证明语义恢复或因果改善。

最后一轮原子提交已完成但 round_result/campaign 报告尚未发布时，resume 从已验证 Memory/Gate 重建报告，避免重复提交或因 INCOMPLETE 报告无法收尾。

### 发送表示

`evidence_projection_v19` 按内容对事件正文和长文本建立引用，原事件 evidence_ref 不变；发送前自动无损还原并核对摘要。模型通过 event_bodies/text_bodies 读取完整内容。原始请求 DTO、证据和审阅输出按原文持久化；不做摘要截断，不按当前组路由历史。发送前沿用带余量的 token 预算检查，超限停止而非删减证据。

### 工程与真实观察边界

工程 fixture 验证两轮 ACCEPT→REVISES、RETAIN→RETRIES、MIXED/NOT_COVERED 保存、阶段中断、末轮提交后恢复、审阅/账本篡改拒绝、一次修复、无完成响应不重发、空发现无虚假提交、Monitor 隔离和无损发送表示。预设状态只验证机制，不是方法有效性的证据。

无模型预检：`artifacts/methods/v19/v19_separated_preflight_001/preflight.json`，243 个环境实例，模型调用 0。真实 Pilot 进展另行记录，不能将工程 fixture 结果当成真实纠偏效果。

最终工程验证：`tests/skill_evolution/*v19.py` **331 项通过**（含 14 项新闭环专项）。992 个 v18 冻结文件哈希一致。真实 Pilot 已在 `artifacts/methods/v19/pilot/benchmark_v4_rounds_01_02/campaign` 启动；启动信息在 `artifacts/methods/v19/v19_separated_pilot_001_process.json`，独立日志在 `artifacts/methods/v19/v19_separated_pilot_001.launch.log`。启动成功不等于 Pilot 完成，须以实际状态为准。

<a id="v19-separated-discovery-review"></a>

## v19 职责拆分：第 1 步数据契约与独立阶段

日期：2026-09-24。

本步完成 Current Diagnosis 与 Memory Review 的输入构造、严格响应 schema、本地校验、不可变 DTO、稳定来源 ID、独立 Prompt 和工程测试。没有实现 Reconciliation、模型调用/修复与阶段检查点、多轮新调度或新的真实 Pilot；这些在后两步接入。v18 和已完成 Pilot 保持不变。

### 阶段边界

```text
当前 Parent Evolution + 当前 Parent Skill + 当前分组
  → Current Diagnosis
  → Current Findings ──────────────────────────────┐
                                                 │
历史 Memory + Current Findings + 全部当前证据索引  │
  → Memory Review → Historical Reviews ────────────┤
                                                 ↓
                                  后续 Reconciliation（未实现）
```

新接口不调用 Memory Router，也不将历史 edit 分配给当前 Diagnosis 组。旧的 `memory_diagnosis_v19.py`、路由和生成入口暂时保留，用于现有产物验证和旧流程兼容。`run_v19_v4.py` 尚未切换到新流程，不应将运行旧入口当作本次拆分的真实验证。第 3 步统一接入时再切换；不提前拼接到缺少 Reconciliation 的旧 Compiler 路径。

### 1. Current Diagnosis

入口：`current_diagnosis_v19.build_current_diagnosis_inputs`。

显式传入 run_id、round_id、parent_skill、Evolution backend、完成的 Parent 目录和已绑定分组。不传入 Memory store。复用现有 learner-safe 当前轨迹投影、全量分组校验和 v18 policy/rule 引用索引；不复用旧 Diagnosis 的 gap 输出。

输出每组一个 `CurrentDiagnosisInput`，仅包含当前 Skill、当前组轨迹、可见 policy/tools、Level-0 监督和组织性分组提示。事件采用 run/round 作用域的 CURRENT 引用，附带原始轨迹身份、Parent Skill 身份及来源轮次。私有 Monitor 和 evaluator 内容不进入接口。

模型响应 schema：

```json
{
  "schema_version": "current_findings_response_v19.1",
  "summary": "对当前组的分析总结，也可解释没有充分 finding 的原因",
  "findings": [{
    "kind": "OBSERVED_PROBLEM",
    "statement": "可见条件、行为及观察结果",
    "applicability": "适用范围",
    "dimensions": ["SUCCESS"],
    "evidence_refs": ["CURRENT/.../E0001"],
    "supervision_refs": [],
    "policy_refs": [],
    "related_rule_refs": [],
    "uncertainty": ["可能的采样波动或其他解释"]
  }]
}
```

- kind：`OBSERVED_PROBLEM / EFFECTIVE_BEHAVIOR / COUNTEREVIDENCE / UNCERTAINTY`。不要求凑齐四种，不强迫成功观察生成 gap，允许 findings=[]。
- dimensions：SUCCESS / COMPLIANCE，至少一项。
- 每条 finding 必须有当前事件引用；policy、supervision、rule 分字段校验。监督引用必须属于所引轨迹，policy 必须属于所引事件的上下文。
- 不接受 Evidence Status、历史关系、Review Decision、Skill Gap、编辑操作或 Skill 正文等额外字段。
- 校验后由运行时生成 `CF/<hash(input_ref + finding)>`，保存 input_ref、batch、group_id 和精确原响应。相同输入及相同 finding 得到相同 ID，改变内容或来源则改变 ID。不让模型自行命名。
- DTO 用冻结 dataclass 保存规范 JSON；读取 payload 返回独立副本。Memory Review 构造前逐条从原响应重新校验，篡改、旧轮混入、重复组、漏组或漏响应都拒绝。

`Current Finding` 记录当前发现，不决定是否修改。没有历史关系的 finding 将来可直接进入 Reconciliation，不必构造 Evidence Status，也不默认等于 MISSING。

### 2. Memory Review

入口：`historical_review_v19.build_memory_review_input`。

输入为已校验的完整 Current Findings 批次及请求，以及已提交的 Memory。校验运行身份、当前 Parent、Evolution manifest、Memory head；不能审阅已提交为历史的“当前轮”。本步检索全部已提交历史，不使用按当前组路由或静默丢弃历史的预算裁剪。

可见内容包括：

- 全部 Current Findings（不可改写）；
- 当前原始事件索引、轨迹身份、上下文和监督，涵盖未出现在 Findings 中的事件；
- 完整历史 Memory，包括原 paired replay、支持与反证、归因不确定性、来源及当前绑定；
- 明确的 historical_objects 审阅清单。

`resolve_current_evidence(request, refs)` 按精确引用返回只读的当前原始事件和对应上下文。当前 Prompt 以全量事件索引提供这些材料，不假装已经实现动态工具检索。调用前使用既有 token 预算检查，超限停止，不截断原始证据；大规模分批执行和恢复属于后续调度工作。

#### 历史对象

本步直接适配已有归因存储：一个对象是 `(edit_id, attribution_id)`，稳定 ID 为 `HO/<hash(identity)>`。它携带该归因的 interpretation、applicability、effect、uncertainty、alternative_explanations 和当前规则绑定。

同一 edit 的两个历史判断有两个对象；共同归因保留 joint_edit_ids 和同一 attribution_id，不能被当成独立证据。Review 必须覆盖全部对象，但不得因此将同一原始 pair/event 重复计为多份支持。没有添加自由生成的新历史 issue 或新的归因；将来的 issue 演进由后续持久化协议处理。

已有 interpretation 可能包含复合判断；MIXED 应解释分别支持和反对的部分。结构校验不能证明自然语言判断已经原子化或语义正确。

#### 响应

```json
{
  "schema_version": "historical_review_response_v19.1",
  "reviews": [{
    "historical_object_id": "HO/...",
    "evidence_status": "NOT_COVERED",
    "supporting_current_refs": [],
    "contradicting_current_refs": [],
    "context_current_refs": [],
    "current_finding_refs": [],
    "historical_evidence_refs": [],
    "coverage_reason": "NO_RELEVANT_OBSERVATION",
    "reason": "本轮未观察到足够相关的行为",
    "uncertainty": ["不能由未覆盖推断历史问题已解决"]
  }]
}
```

| Evidence Status | 结构要求 |
|---|---|
| SUPPORTED | 有 supporting_current_refs，无 contradicting_current_refs |
| CONTRADICTED | 有 contradicting_current_refs，无 supporting_current_refs |
| MIXED | 两类引用都有，解释支持与反证各自的含义 |
| NOT_COVERED | 两类引用都没有，必须说明覆盖不足原因 |

NOT_COVERED 的 coverage_reason：

- NO_RELEVANT_OBSERVATION：没有相关当前事件引用。
- INSUFFICIENT_EVIDENCE：有 context_current_refs，说明为什么尚不能形成支持或反驳。

其他三种状态的 coverage_reason 为 ASSESSED。

支持、反证、上下文引用只接受当前原始事件，不接受历史事件、policy、rule、监督或 finding ID。current_finding_refs 可为空；如有，每条链接必须与该 review 共享至少一条当前事件。历史引用独立保存，必须属于对象对应的完整原始 pairs；无 observations 的历史判断保留其原轮完整回放供核查。

每个历史对象恰好一个 review，未知、重复或遗漏对象都拒绝。校验后分配 `HR/<hash(input_ref + review)>`，保存精确原响应与输入绑定。Memory Review 不接受 PROPOSE/KEEP/DEFER、mutation kind、操作或改写后的 findings。

空 Memory 的 historical_objects 和 reviews 均为空；已有 Current Findings 不受影响。Current Findings 为空时，历史审阅仍可查看全部当前事件，不能把没有 finding 当作没有新证据。

### 下一步的兼容接口

Reconciliation 将独立接收 CurrentFindings 与 HistoricalReviews，来源至少一侧非空，并逐项做 PROPOSE/KEEP/DEFER。只有 PROPOSE 产生 v18 风格的 MISSING/NEEDS_REVISION/SHOULD_REMOVE；Compiler 再映射为 ADD/REPLACE/DELETE。本步不提前确定这两层的响应 schema，也不自动把 evidence status 映射到编辑动作。

### 验证边界

本地校验保证 schema、引用类型/范围、来源绑定和历史覆盖，不保证因果归因、语义蕴含或模型真正重视当前证据。工程 fixture 的支持/反驳状态是预设输入，仅验证机制；尚无新流程真实模型效果结论。

测试：`python -m pytest tests/skill_evolution/v19/test_separated_review_v19.py -q`。

本步最终验证：新增专项测试 27 项；`tests/skill_evolution/*v19.py` 全量 **293 项通过**。语法编译和 diff 空白检查通过；v18 冻结 manifest 的 **992 个文件全部哈希一致**。未运行真实模型或 Pilot。

<a id="v19-run-resume"></a>

## v19 统一 run / resume

正式入口：`scripts/runs/v19/run_v19.py`。仅服务于新入口创建的当前版本实验；不自动迁移旧 Pilot。

### 启动新实验

在项目根目录执行：

```bash
python scripts/runs/v19/run_v19.py run \
  --config experiments/methods/v19/v19_run/config/pilot.json \
  --output artifacts/methods/v19/pilot/v19_unified_pilot_001
```

`run` 会调用真实模型，输出目录必须不存在。Pilot 是固定 Evolution / Monitor 切分上的最多 **2 轮**，不是减少任务数量。正式实验配置为 `experiments/methods/v19/v19_run/config/formal.json`，最多 **4 轮**；输出应放入 `artifacts/methods/v19/formal/<新名称>`。

JSON 配置只包含 `mode`（pilot/formal）与 `max_workers`（1–32，Replay/Monitor 并发）。Attribution 并发沿用 2。当前协议固定：

Parent Evolution → Current Diagnosis → 逐 edit Memory Review → Issue Fusion → 逐提案 Evidence Review → Compiler / Editor → Candidate Replay → Attribution v19.2 → Monitor / Gate → Memory。

模型配置、预算、契约、Four-Delta Gate 不因统一入口而调整。初始 Skill、任务及配置仍来自冻结 benchmark v4。连接环境从 `.env` 读取，不写入运行绑定。

### 恢复

```bash
python scripts/runs/v19/run_v19.py resume \
  --output artifacts/methods/v19/pilot/v19_unified_pilot_001
```

无需重新提供配置。配置和 run_id 从 `binding.json` 读取，源码、初始 Skill、任务及运行 manifest 必须一致；变化时停止并要求迁移。已有锁禁止同一实验并发运行。

- 完成且校验通过的结果复用；已提交 Memory 按权威 head 恢复，不重复提交。
- Replay / Monitor 使用原有逐任务检查点；已完成轨迹不因评估失败而重跑。
- 模型调用发生 `APITimeoutError` / `APIConnectionError` / `TimeoutError` / `ConnectionError` 且无响应时，resume 自动归档该调用，再请求一次。失败再出现则仍停止/记录 INCOMPLETE，不无限循环。
- 进程中断留下请求、但既无响应也无完成标记时，同样保留并重新请求；无法保证远端没有执行过该请求。
- 每个 Diagnosis 分组、历史 edit、Evidence Review 提案、Attribution pair 独立恢复，不重新生成已完成单元。
- 契约修复仍最多一次：若这唯一一次修复本身网络超时，恢复它，不额外增加修复轮数。
- 完整响应截断、拒答、最终契约失败、输入超预算不会被自动清除或盲目重试；需要检查原因。
- 已保存响应但缺完成标记属于检查点异常，停止检查，不直接重发。鉴权等非网络失败也不会自动归档重试。

自动归档位置：`<实验>/recovery/<唯一编号>/`，保存 `receipt.json`（原相对路径、失败类型、文件摘要）与 `call/` 原始调用。归档在各阶段目录之外，不污染阶段完成摘要，也不进入 learner 输入。

### 范围与状态

该入口在前台运行，日志输出到终端；可自行重定向日志。`campaign.json` 记录已完成/失败阶段，细粒度进度见各阶段检查点，提交状态以 `memory/head.json` 为准。

历史两轮 Pilot 经过协议变化及目录迁移，不能直接用此 resume。旧入口及历史实现保留；未使用统一入口的调用依然维持原来显式处理失败尝试的行为。

本次仅实现入口与恢复，并使用构造模型响应进行工程测试，未启动真实实验。当前 Pilot 迁移、第三轮启动均不在此次执行范围内。

### 离线重启：复用 round-01 Current Diagnosis，重建 Memory

使用 `scripts/migrations/v19/migrate_v19_memory_restart.py --source OLD --archive ARCHIVE --output NEW`。
该命令不读取 `.env`、不调用模型，只使用本地冻结 benchmark 和已有完整响应。
必须先停止 OLD 的运行进程，ARCHIVE、NEW 必须不存在，三个目录不能互相包含。

它逐文件 SHA-256 核验整份旧运行副本，保留 OLD 不动；在 NEW 中仅导入第一轮
Parent Evolution、Grouping、Current Diagnosis（含相关调用/修复/失败记录）。
旧两轮结果、旧 Memory 和日志只进入整体归档，不进入新 Memory。
归档只覆盖 OLD 目录内文件；外部终端重定向日志需要另行保留。

迁移检查执行配置、冻结数据、任务/seed、上游代码摘要、原始请求/响应完成标记及
Findings 本地契约。任何缺失或不兼容都会停止，不能自动调用模型补齐。
NEW 的 Memory revision 为 0。第一轮 Memory Review 生成空结果，不调用模型。
resume 会校验并复用上游，然后首次调用模型的阶段是 Issue Fusion。

NEW 沿用 OLD 的内部 run_id 和执行清单标识，以保持证据引用不变。它是一个不同输出
目录中的显式实验分支，并非另取 run_id 后伪造旧模型响应。migration.json 记录来源、
归档全文件摘要、复用文件摘要、时间、旧绑定、实际新代码和执行清单以及 Memory 协议。
新 binding 绑定迁移记录摘要。恢复时同时检查当前代码、运行配置、复用文件及归档。
历史清单保留用于证据身份；实际执行代码版本以迁移记录和新 binding 为准。

迁移准备使用独立 `.pending-*` 目录，核验后发布。已有目标一律拒绝覆盖，迁移失败
保留临时目录供检查；不要把半成品当作可 resume 运行。恢复启动失败若涉及网络，使用
普通 resume；若提示代码漂移或证据改变，先调查，不能修改摘要绕过校验。

```bash
cd /Users/didi/Desktop/Govern-Skill-Evo
/Users/didi/miniforge3/bin/python scripts/migrations/v19/migrate_v19_memory_restart.py \
  --source artifacts/methods/v19/formal/v19_memory_formal_001 \
  --archive artifacts/methods/v19/archive/legacy/v19_memory_formal_001_before_issue_memory \
  --output artifacts/methods/v19/formal/v19_memory_formal_002

/Users/didi/miniforge3/bin/python scripts/runs/v19/run_v19.py resume \
  --output artifacts/methods/v19/formal/v19_memory_formal_002
```

正式配置继承旧运行，仍最多运行四轮（可能按已有 NO_UPDATE/UNABLE 机制提前停止）。
原始运行、归档、新运行及临时目录均已被现有 `.gitignore` 规则覆盖。

### 第一轮已提交后迁移 Attribution → Memory 语义

`migrate_v19_attribution_memory.py` 适用于：统一 local/pair 运行，恰好提交一轮，
第二轮尚未进入 generation。必须停止旧进程；三个路径互不包含，目标不存在。

```bash
cd /Users/didi/Desktop/Govern-Skill-Evo
/Users/didi/miniforge3/bin/python scripts/migrations/v19/migrate_v19_attribution_memory.py \
  --source artifacts/methods/v19/formal/v19_memory_formal_002 \
  --archive artifacts/methods/v19/archive/legacy/v19_memory_formal_002_before_attribution_facts \
  --output artifacts/methods/v19/formal/v19_memory_formal_003

/Users/didi/miniforge3/bin/python scripts/runs/v19/run_v19.py resume \
  --output artifacts/methods/v19/formal/v19_memory_formal_003
```

迁移命令不调用模型：复制核验整个旧目录；复用第一轮逐 pair 完整响应生成
attribution_batch_v19.3；通过正式 commit_round_memory 重建 revision 1 及哈希引用链。
使用原始 ledger、Parent/Candidate Replay 和重新校验的 Monitor Gate，验证保留 Skill
不变。旧 Memory、旧汇总和此前 migration.json 都保存在整个归档中。

第二轮 Parent 必须完整且与保留 Skill、原执行清单一致。已完成 Grouping 原样验证；
未完成 Grouping 的完整响应保留，没有响应的中断/网络失败请求在新目录 recovery 中
归档；存在部分响应或非网络失败时拒绝自动迁移。恢复后按普通检查点流程继续。
若第二轮尚无产物，恢复从其 Parent 开始。存在第二轮 generation 时拒绝此入口，
避免悄悄丢弃已生成的 Current Diagnosis 或消费旧 Memory 的下游产物。

新目录保留来源 run_id 和执行清单身份，实际新源码、旧/新 Memory head、第一轮新
record、归档/复用文件摘要及协议写入新 migration.json，并由 binding 绑定。
恢复检查归档、第一轮不可变文件及 Memory 第一条提交。后续网络失败仍使用同一 resume。
正式配置继承旧运行，最多四轮；不重跑第一轮，第二轮开始使用 issue_memory_v19.2。
迁移失败的 .pending 目录保留供检查，已有目标禁止覆盖。外部日志不在源目录内的，
不属于整体目录归档范围。
