# v19 第 7 步：独立调度、多轮闭环与 Pilot

> 目录整理提示（2026-09-27）：下文旧 Pilot 的命令保留为历史说明，不代表搬迁后可直接 resume。当前产物入口见 [v19 实验索引](../experiments/v19/INDEX.md)，原始路径见 [迁移映射](../experiments/v19/path-map.json)。

日期：2026-09-22。

**工程闭环已接通并通过构造测试。真实 Pilot 首次因内网 DNS 不可用停止；用户连接内网后已在原目录 resume，正在运行。完整实验未启动。**

## 运行入口与轮次顺序

独立入口 `scripts/run_v19_v4.py`，调度实现 `src/skill_evolution/campaign_v19.py`。每轮严格执行：

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

## run / resume 命令

在仓库根目录执行，依赖现有 Python 环境和 `.env` 模型连接配置。默认仅预检，不调用模型。

```bash
# 无模型预检：构造 Evolution/Monitor 的全部环境；每次使用新输出目录
python scripts/run_v19_v4.py --pilot \
  --preflight-output artifacts/v19_campaign_preflight_manual_001

# 新建最多 2 轮真实 Pilot（已有 pilot_001 不应覆盖）
python scripts/run_v19_v4.py --run --pilot \
  --output experiments/v19/pilot/v19_v4_pilot_002

# 当前 Pilot：Diagnosis 输入修复后，使用显式恢复回执继续
python scripts/run_v19_v4.py --run --pilot --resume \
  --output experiments/archive/v19/v19_v4_pilot_001 \
  --diagnosis-recovery experiments/archive/v19/v19_v4_pilot_001/diagnosis_recovery/receipt-contract.json

# 完整实验：由用户自行启动；本次没有执行
python scripts/run_v19_v4.py --run \
  --output experiments/v19/formal/v19_v4_formal_001

# 同一个完整实验的恢复
python scripts/run_v19_v4.py --run --resume \
  --output experiments/v19/formal/v19_v4_formal_001
```

默认 `--max-workers 8`。如果第一次运行指定其他并发数，resume 必须提供同值。mode、轮次上限、任务/seed/runtime、初始 Skill 和源码摘要绑定到 `binding.json`；不能把 Pilot 原地扩成完整实验，也不能悄悄替换配置继续旧运行。启动新配置需要新目录。新建运行默认拒绝已存在目录。

运行时输出阶段名；详细状态见 `<output>/campaign.json`，实际提交事实以 `<output>/memory/head.json` 为准。保留 Skill 原文在 `head.json` 的 `retained_skill`，没有独立的可漂移 `current_skill.md` 权威副本。

## 冻结与 Monitor 边界

v19 只读使用 `experiments/configs/v18_formal_003` 的 benchmark/config/policy/tasks/user prompt/S0。已有 v18 源码及 992 个冻结 manifest 文件保持不变。v19 运行目录保存独立配置、源码摘要与两类运行 manifest；恢复检查当前源码/配置与原绑定一致。

`BenchmarkEvolutionV19` 默认仍只接受 train。新增 `BenchmarkMonitorV19` 使用固定 monitor split 和不同 manifest schema；把它误传入公开 Evolution learner API 会被拒绝。两者共用 v19 的新环境构造逻辑，policy 仅设置于当前环境实例，不全局替换 v18 或 tau2 方法。

Monitor 产物只写入 `round-NN/monitor_private/`，不生成 `learner/pairs.json`。私有执行沿用逐任务轨迹/评分检查点及配对初始状态、policy/tools、实际 user prompt、执行配置核对。完整后只读复用 v18 的纯 `summarize_monitor` Four-Delta 公式：S/C/CS 均不下降、VF 不上升且至少一项改善才 ACCEPT。

对外返回严格的版本绑定回执：COMPLETE、ACCEPT/RETAIN、run/round、两侧 Skill 摘要。分数、转移矩阵、轨迹、私有评分解释不进入 Diagnosis、归因、Memory 学习投影或公开 campaign report。提交后恢复还会重新检查私有 Gate 与 Memory 决策一致，不能通过改写 `campaign.json` 或回执伪造晋升。

这是应用层的信息隔离，不是操作系统级的进程沙箱；可信调度器拥有私有产物读取权限，模型只收到显式学习投影。

## 分组与恢复

新增 `grouping_campaign_v19.py` 复用现有 Grouper Prompt、固定别名映射和最多一次格式/分区修复。v19 用和 Diagnosis 一致的零 SDK 自动重试 transport，并单独保存每次请求/响应检查点；不存在有效分区时不能运行 Diagnosis。

恢复规则：

- 已完成轨迹复用，评分失败只重试评分；真正未完成的轨迹显式 resume 时归档旧尝试后重跑，不按结果好坏重新采样。
- 已完成分组、Diagnosis、Editor、归因响应重验后复用，不重复调用模型。
- 已提交轮次以 Memory head 恢复，不重新运行学习或提交。head 已更新但 round_result 尚未发布时，可从记忆与已验证 Gate 补回报告。
- 未提交的完整归档不可被下一轮读取；提交前后中断都不会出现 Skill 与 Memory 分离。
- 未完整记录的模型调用、格式/引用失败或不确定响应不在普通 resume 中自动重试。需明确的新尝试安排；不能手工伪造完成标记。本次 DNS 失败发生在 Parent 轨迹执行阶段，可直接使用上述 resume 重试未完成轨迹。
- `campaign.json` 是可重建报告，不是提交依据。版本错配、检查点损坏和私有 Gate 不一致会拒绝继续。

## 多轮工程验证

新增 22 项调度专项测试；与前六步及相关 v18/v4 回归合计 293 项通过。构造测试使用真实的 v19 调度、检查点、Compiler/Editor、账本、归因校验和 Memory 提交代码，仅替换环境行为与模型响应：

- ACCEPT 包中的 MIXED 历史 edit 在下一轮形成 REVISES，保留不确定归因。
- RETAIN 包中的潜在有效方向进入下一轮 RETRIES，旧候选不被当作当前 Skill。
- 在 Candidate、归因、Monitor、提交前/后注入中断；恢复没有重复学习器调用、重复提交或丢失记忆。
- Monitor 评分中断复用已完成轨迹；配对配置不一致阻断 Gate。
- 学习器输入中注入私有标记探针，确认 Monitor 数据未进入学习侧；篡改 Gate 回执及版本漂移会被拒绝。
- NO_UPDATE 提前停止不伪造 Gate/Memory；Pilot 不能改 mode 原地扩展。

这些 ACCEPT/RETAIN、MIXED/UNKNOWN 与修订方向是工程 fixture 预设情形，只证明机制和隔离可运行，不是方法有效性证据。

最终版本无模型预检：`artifacts/v19_campaign_preflight_002/preflight.json`。覆盖 36 个 Evolution 与 45 个 Monitor 任务，各构造 S0、空 Skill、非空 Skill 三种部署，共 **243 个环境实例**，模型调用为 0。

## 真实 Pilot 记录

首次启动遇到公司内网 DNS 不通，恢复网络后从原目录继续。随后少量未完成轨迹及归因超时经过显式恢复，保留原尝试；并非按结果筛选重跑。

截至 Diagnosis 输入修复前：

- round-01 完整完成，Gate ACCEPT，Memory 提交一次。归因记录包含 BENEFICIAL 5、MIXED 2、NO_OBSERVED_EFFECT 1、UNKNOWN 2；它们是有限配对观察下的归因，不证明因果效果。
- round-02 Parent Evolution 完成 36/36，分组完成，分成 8 组。
- 首条 Diagnosis 被网关拒绝：输入长度 1,390,836，超过 1,048,566。原请求 user_prompt 为 3,563,946 个 Python 字符；网关长度与字符数不是同一单位。
- 当前经验、历史轨迹、Memory replay 与引用目录含重复表示，尚未产生 round-02 Candidate，不能宣称真实跨轮纠偏完成。

### Diagnosis 发送表示 v19.2

只改变模型发送投影，签名的 Diagnosis DTO、持久化原始轨迹、Memory 内容和校验规则保持完整：

- 每个观察在 `experiences` 中保留身份、来源轮次、角色、Skill、监督标签和原始 evidence_ref。
- 完整事件正文按内容去重存入 `event_bodies`，通过 `event_body_ref` 读取；引用不是摘要。历史 source_evidence 中的事件也使用同一正文池。
- Memory 的历史 pairs 通过 `experience_ref` 指向这些观察，contexts 通过 context_refs 引用顶层上下文。
- 事件/监督目录用可推导索引表示；返回仍必须使用原始 evidence_ref、supervision_ref，不允许引用正文池编号作为证据。
- 所有归因、支持、反证、不确定性、当前规则绑定和检索选择信息完整保留。无自动裁剪或历史丢弃。

发送前用 `tiktoken` 的 `cl100k_base` 计算包含 system/user/schema 的本地代理 token 数，再预留 25%、24,000 输出 token 和 4,096 封装额度，超过 1,048,566 则本地拒绝，不调用模型。**这是带余量的估计，不是网关的精确 tokenizer，也不保证消除所有网关长度拒绝。** 环境需能加载 tiktoken 及其编码缓存；失败时不绕过检查。

真实 round-02 的 8 组均完成无模型投影及还原核对，首组由 3,563,946 降至 1,457,943 字符；各组代理输入 517,417–570,076 tokens，加余量后的总预算 674,868–740,691。审计见 `artifacts/v19_diagnosis_recovery_001/projection_preflight.json`。

### 显式源码恢复

普通 resume 仍拒绝源码漂移。本次通过 `source_recovery_v19.py` 仅为 Diagnosis 表示修复建立显式回执：

- 原 `binding.json` 不改写；保存原源码和替换源码的全部摘要，校验允许变更范围。执行 backend 的 prepare/evaluate/_make_manifest/preflight AST 必须不变。
- 原回放执行 manifest 保留身份，实际替换源码独立绑定在恢复回执中；配置、split、seed、Gate、Memory 语义不可借此改变。
- round-01 和 round-02 已完成 Parent/Grouping 文件逐一绑定摘要，原 Memory head 及其后续提交链必须连续。
- 被明确拒绝且没有响应的 generation 整目录保存在 `diagnosis_recovery/failed_generation`。若已经有响应或后续请求，则拒绝使用此恢复。
- 恢复回执写入与归档之间的中断可继续；未来源码漂移、历史文件变化或执行配置变化仍拒绝。

恢复命令：

```bash
python scripts/run_v19_v4.py --run --pilot --resume \
  --output experiments/archive/v19/v19_v4_pilot_001 \
  --diagnosis-recovery experiments/archive/v19/v19_v4_pilot_001/diagnosis_recovery/receipt-contract.json
```

完整实验未启动。修复后的 Pilot 实际进度和跨轮观察以 `campaign.json`、提交的 Memory 和生成账本为准；工程构造测试不能替代真实结果。

### Diagnosis 契约提示 v19.3 与第二次显式恢复

v19.2 首条请求已被网关正常处理：实际输入 530,664 tokens，完整返回。随后本地校验发现：当前 8 条经验全部成功，但历史 72 条中有 29 条失败或违规，模型仍选择 NO_ISSUE；9 个历史 edit 返回 10 条 review，其中一项重复。原始响应保存在 `diagnosis_recovery/contract_rejected_generation`，不改写或自动修正。

v19.3 只修订 v19 的提示和发送投影元数据：替换继承提示中可能混淆范围的状态说明，统一为全部当前及选入历史观察；显式给出监督计数和 NO_ISSUE 的允许条件，以及唯一的 `expected_edit_ids` 清单。历史失败不等于当前失败，也不强制修改 Skill；缺乏可支持的当前修改时使用 NOT_ADDRESSABLE，并逐项解释 DEFER。review 单位是 edit，不是 attribution。

原校验器、Compiler、Editor、Gate、Memory、回放语义均未放宽。新增回归复现 NO_ISSUE 范围错误及重复 review，并验证正确无修改结论可通过。第二次恢复保留初次回执和源码，新增链式回执 `receipt-contract.json`，只允许提示及恢复审计代码变化；拒绝归档后续或已接受的 group。

本 Pilot 后续恢复使用：

```bash
python scripts/run_v19_v4.py --run --pilot --resume \
  --output experiments/archive/v19/v19_v4_pilot_001 \
  --diagnosis-recovery experiments/archive/v19/v19_v4_pilot_001/diagnosis_recovery/receipt-contract.json
```

8 组新请求均完成无模型还原核对、预算与审阅清单检查，见 `artifacts/v19_diagnosis_contract_recovery_001/preflight.json`；992 个 v18 冻结文件保持不变。

### Diagnosis v19.4：引用类型与整批恢复

v19.3 的第 0–2 组通过本地校验，第 3 组完整返回，但 `memory_review.evidence_refs` 混入政策引用，触发 `MemoryRejected`。v19.4 明确逐字段引用类型并提供正反例：Diagnosis analysis/gap 可保留政策依据，Memory review 只记录原始事件引用。校验仍严格拒绝政策引用，并报告 review 索引、edit ID 和非法引用；不自动删除或替换模型输出。

`prepare_diagnosis_batch(output, previous_receipt, source_before, batch_id, reason)` 是显式整批恢复 API：重新校验已有连续响应前缀，要求末条是本地契约拒绝、前面均有效，且没有 Editor/Candidate/后续阶段；拒绝未完成 transport、混合 prompt 或无失败批次。整个 generation 连同有效响应归档，记录每组校验状态、全部文件摘要、上一回执和旧源码快照。新 generation 从第 0 组开始统一使用新 prompt，绝不拼接旧版本的有效响应。归档后中断通过 pending receipt 恢复，普通 resume 不自动创建新批次。

此次新回执：`diagnosis_recovery/receipt-batch-references-001.json`。后续 resume 使用：

```bash
python scripts/run_v19_v4.py --run --pilot --resume \
  --output experiments/archive/v19/v19_v4_pilot_001 \
  --diagnosis-recovery experiments/archive/v19/v19_v4_pilot_001/diagnosis_recovery/receipt-batch-references-001.json
```

已完成的 Parent、Grouping、round-01 Memory 不重跑、不改写。前三条旧有效 Diagnosis 保留作审计记录，不作为新批次结果复用。整批重生成增加模型调用成本，须与原 Pilot 轨迹数量上限区分。

### 新批次 v19.5 协议

v19.5 的每组 Diagnosis 允许最多一次完整留痕的本地契约修复，详见 `V19_MEMORY_GENERATION.md`。已完成且通过的初次结果不产生修复调用；第一次无效且完整的模型输出交由模型修复一次，再次失败即停止。transport 异常不属于此修复协议。新 generation/input.json 显式绑定单次修复协议，旧批次不能普通 resume 原地升级。本次协议实现没有迁移或启动旧 Pilot，以上旧版恢复命令不能直接用于更新后的源码。
