# 正式实验协议与结果

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [v18 完整调度（第 6 步）](#v18-formal-experiment)
- [v18 单轮端到端 Pilot 报告](#v18-end-to-end-pilot-report)
- [v18 × benchmark v4 正式四轮协议](#v18-benchmark-v4-formal-protocol)
- [v18 × benchmark v4 四轮结果分析](#v18-v4-four-round-analysis)

<a id="v18-formal-experiment"></a>

## v18 完整调度（第 6 步）

2026-09-19。独立入口已实现，v17 文件与行为不修改。当前完成配置冻结、无模型预检与调度测试，尚未启动真实模型 campaign。

### 路径与配置

- `scripts/preparation/v18/freeze_v18_formal.py`：创建新冻结，已有 manifest 时拒绝覆盖。
- `scripts/runs/v18/run_v18_formal.py`：默认只预检，显式 `--run` 才调用模型。
- `src/skill_evolution/v18/formal_v18.py`：Evolution → Grouping → Diagnosis v18 → Compiler v18 → Editor v18 → Monitor → Gate。
- `src/skill_evolution/v18/monitor_benchmark_v18.py` / `monitor_v18.py`：独立 v18 后端与原 Four-Delta 整数计数 Gate。
- `experiments/methods/v18/v18_formal_001/config/`：S0、配置、任务、清理后的 policy、可见上下文、逐任务 User prompt 和依赖文件摘要。

默认 4 轮；32 个 Evolution 任务，41 个 Monitor 任务，seed 200；每任务每角色一次，最多 456 次 Agent rollout。Evolution 与 Monitor 均使用 v18 Simulator 和相同冻结 User prompt。Grouping、经验投影和 Diagnosis 输入封装复用 v17 公共能力；Diagnosis 使用 v18 Prompt v2，Editor 使用 v18 Prompt v1。

`user_prompts.json` 包含私有 User Scenario，只供运行时绑定和审计；不得传给 learner。Monitor 轨迹、标签、二维分布及转移矩阵均留在 `monitor_private`，调度仅消费完成状态及 ACCEPT/RETAIN。

### 状态与恢复

- 全部组 Diagnosis VALID 后才编译；任意失败都不做部分编译。
- Editor VALID 和纯 DELETE 的 APPLIED_DETERMINISTIC 均进入 Monitor。空或仅标题 Candidate 仍保留原文与摘要，使用基线 Agent 装配。
- NO_UPDATE / UNABLE 保留 Parent 并停止；错误标记 INCOMPLETE，不晋升。
- 只有 Monitor COMPLETE 且 Gate ACCEPT 才晋升；RETAIN 继续沿用 Parent。
- `--resume` 要求配置与原冻结 manifest 完全一致。已完成 Evolution 复用；Grouping/Diagnosis 重验后复用；未完成或失败的调用在显式恢复时归档后尝试一次，不自动重试。
- 已完成 Editor 校验 Candidate、Parent 和产物摘要后复用；未完成 Compiler/Editor 归档后从绑定输入重建。Monitor 逐任务校验配置、Skill、seed 和 checkpoint 文件摘要后复用，部分结果归档后重跑。
- campaign 先提交每轮保留摘要，再更新 `current_skill.md`。恢复时从已提交 ACCEPT 记录重建当前 Skill，避免两文件写入中断导致 Parent 丢失。
- 达到轮数上限的已完成运行可以显式增加总轮数；NO_UPDATE / UNABLE 停止的运行不延长。

### 运行

```bash
# 已有冻结时直接预检；不调用模型
python scripts/runs/v18/run_v18_formal.py

# 开始正式四轮实验
python scripts/runs/v18/run_v18_formal.py --run

# 恢复同一实验
python scripts/runs/v18/run_v18_formal.py --run --resume

# 示例：将达到轮数上限的运行延长到六轮
python scripts/runs/v18/run_v18_formal.py --run --resume --total-rounds 6
```

默认输出为 `experiments/v18_formal_001`，可用 `--output` 指定新目录。冻结完成后修改受绑定源码会被拒绝，不能用更新旧 manifest 的方式继续同一实验。

### 验证与限制

73 个任务的实际 orchestrator/User prompt 构造预检通过，模型调用数为 0。测试覆盖完整 learner 接线（模拟模型响应）、真实 Compiler/Editor 的纯 DELETE 与混合操作、空 Candidate 经过真实 Gate、保留/晋升、失败、冻结漂移及中断恢复。

尚未验证真实 Editor 模型的语义保持能力，也未证明四轮学习效果；Diagnosis Pilot 中 transfer fallback 的残留语义问题未在调度或 Compiler 中修补。

验证记录：`artifacts/methods/v18/v18_formal_integration_001/`。v17/v18 相关回归 532 项通过，随后新增 Monitor 后端 checkpoint 篡改/复用测试 1 项通过，合计 533 项。全 `tests/skill_evolution` 收集被旧 v06 测试缺少 `browsergym.experiments` 阻断，未声称全目录通过。

### Benchmark v4 freeze

`experiments/methods/v18/v18_formal_002/config/` 是独立的新 freeze，对应 `phase_v4_day36`。它保留原 64 个 Core 和 9 个 regression guard，并加入 8 个 `JRA-01` 联合任务：36 个 Evolution、45 个 Monitor，默认四轮最多 504 条 Agent rollout。Diagnosis 使用通过固定输入回归的 `v18-group-diagnosis-3.2.1`。

旧 `v18_formal_001` 和 benchmark v3 不做修改。v4 使用独立的 runtime、Monitor adapter、runner 与输出目录：

```bash
python scripts/runs/v18/run_v18_formal_v4.py
python scripts/runs/v18/run_v18_formal_v4.py --run
```

<a id="v18-end-to-end-pilot-report"></a>

## v18 单轮端到端 Pilot 报告

日期：2026-09-19  
输出：`artifacts/methods/v18/pilot/v18_pilot_001/`  
模式：独立 `PILOT`，固定一轮，共用 v18 正式冻结任务、Prompt、模型与 seed 200。

### 结论

完整链路已跑通：32 个 Evolution → Grouping → 6 个 Diagnosis → Compiler → Editor → 41 组 Parent/Candidate Monitor → Four-Delta Gate。最终 campaign 状态为 `COMPLETE`，Gate 决策为 `ACCEPT`。

Pilot 证明 v18 调度、恢复、Compiler/Editor 接线和 Gate 可以在真实模型调用下完成一轮，也证明 Editor 基本能够保持 Diagnosis 的条件、范围和不确定性。但 Diagnosis 仍存在两个属于 learner 的通用语义问题，因此不建议立即启动正式四轮实验。下一步应针对“不可执行的隐藏机制”和“未知机制转新门槛”做 Prompt v3 的最小修订，再用本次固定输入回放验收；不得依据具体 Monitor 错题定向修改 Prompt。

### 运行结果

- 最终有效样本：32 个 Evolution，41 个 Monitor 任务 × Parent/Candidate，共 114 个完成 rollout。
- 当前有效 Grouping：6 组。
- Diagnosis：6/6 VALID；5 组 ADDRESSABLE，1 组 NO_ISSUE；共 6 个 gap，全部为 MISSING。
- Compiler：VALID；6 个 ADD，1 个 NOOP。
- Editor：VALID；1 次有效模型调用；Candidate SHA-256 为 `9c0d780422914696fbf195f162f6c0d8d0e571b790e3402a2201dbca37feab49`。
- 6 个有效 Diagnosis 合计 288,125 tokens；有效 Editor 调用 65,219 tokens。中断、空响应与受并发影响的调用保留在审计目录中，未混入最终 Gate。

Gate 的聚合计数：

| 指标 | Parent | Candidate | Δ |
|---|---:|---:|---:|
| Success | 28 | 34 | +6 |
| Compliant | 34 | 41 | +7 |
| Compliant + Success | 21 | 34 | +13 |
| Violating + Failure | 0 | 0 | 0 |

Candidate 的二维分布为 CS=34、CF=7、VS=0、VF=0。Gate 的 ACCEPT 仅说明聚合结果满足 Four-Delta 条件，不替代 learner 语义验收，也不作为针对具体 Monitor 任务修改 Prompt 的依据。

### learner 语义评估

按 Grouping 的 6 个当前有效组评估：4 组通过，1 组部分通过，1 组失败。

| 组 | 结果 | 说明 |
|---|---|---|
| G01 购买保护 | 通过 | 保留 partner_direct 条件、tentative 状态和 consolidated 未决分支，没有扩成普适规则。 |
| G02 双地址写入 | 通过，带风险 | 将 cedar 与写入顺序保持为局部候选假设，没有扩展到 orbit；替代顺序未被直接观察，但不确定性被保留。 |
| G03 多乘客与行李 | 部分通过 | 乘客数量规律保持为 C002 的候选边界；行李规律只证明“不能全部计为 nonfree”，却没有可执行的免费额度映射。Diagnosis 仍判 ADDRESSABLE，可能迫使 Agent 猜测隐藏合同。 |
| G04 结算渠道 | 通过 | 保留 horizon/summit 条件和 tentative 状态，明确可改变的是首次更新前的总价计算。 |
| G05 全部成功合规 | 通过 | 正确输出 NO_ISSUE，没有因 Parent 为空而制造 gap。 |
| G06 保险取消 | 失败 | 将内部保险覆盖不可见转成“没有可见的明确覆盖证明就拒绝”，新增 verification duty、prohibition 和 stopping outcome，正是 v18 要避免的未知机制→门槛转换。 |

Editor 对 6 个 gap 的改写整体忠实：条件、观察范围和 tentative/未决状态均保留；未发现 Editor 独立新增 transfer fallback 或把候选规律改写为普适确定规则。G06 的强门槛已经存在于 Diagnosis gap，不能归因于 Editor。

### 执行与恢复记录

第一次启动因 VPN 未连接发生模型服务连接错误。VPN 恢复后，Evolution 中一个任务及后续 Grouping、Diagnosis、Monitor 出现若干空响应；调度通过显式恢复复用完成产物，最终补齐全部样本。空响应属于运行完成性问题，没有作为 learner Prompt 证据。

调试期间发现工具等待返回后旧 Python 进程仍运行，造成两个恢复进程并发，并生成了不同 Editor Candidate。绑定校验阻止了不同 Candidate 的 Monitor 结果混用。受影响的 Monitor 目录完整归档为 `monitor_private.concurrent-1`，最终 Gate 使用当前 Editor Candidate 重新完成全部 82 个 Monitor 调用。旧 Grouping 的 Diagnosis 目录已隔离到 `diagnosis.stale-grouping-1`。

调度随后增加了非阻塞 campaign 文件锁，并在未完成 Grouping 被替换时自动隔离其 Diagnosis 目录。相关测试覆盖并发拒绝和旧 Diagnosis 隔离。

### 下一步验收标准

Prompt v3 只处理 learner 的通用转换问题：

1. ADDRESSABLE 必须给出由现有证据和可用信息决定的具体动作；只知道“当前动作错误”但不知道替代动作如何选择时，不应制造要求 Agent 猜测隐藏机制的 gap。
2. 不得把缺少隐藏合同、映射或机制信息改写为新的证明义务、默认拒绝、禁止执行、转人工或停止条件。
3. 如果证据支持一个局部经验结果，应直接保持为带范围与不确定性的候选规律；如果证据不足以决定替代行为，则判 NOT_ADDRESSABLE 或明确不产出执行规则。

使用本次 G03 行李和 G06 保险输入作为固定语义回归，同时保留 G01/G02/G04/G05 作为非退化样本。该回归只评价 Diagnosis/Editor 的语义保持，不使用具体 Monitor 错题或转移结果构造规则。

<a id="v18-benchmark-v4-formal-protocol"></a>

## v18 × benchmark v4 正式四轮协议

2026-09-20。本次仅冻结协议、实现命令行入口并完成无模型验收，不启动真实模型运行。

### 固定设置

新冻结目录：`experiments/methods/v18/v18_formal_003/config`。旧 `v18_formal_001`、`v18_formal_002` 和历史 Pilot 文件原样保留。旧 manifest 不随源码更新而重写，因此旧入口是否仍可启动取决于原有源码绑定。

- Diagnosis：`v18-group-diagnosis-3.2.1`；Editor：`v18-bounded-editor-1`；Grouping：`v17-grouping-2`。
- benchmark：`phase_v4_day36`，共 81 任务，36 Evolution + 45 Monitor；不是旧版 73 任务。
- seed 200，每任务每角色一次；四轮最多 504 个 Agent rollout。
- 原始 S0 起步，不使用任何 Pilot Candidate。模型参数见冻结 `config.json`，源码、配置、实际 Simulator prompt 和协议均由 manifest 绑定。
- `protocol.json` 预先规定指标、分析切片、晋升、停止和恢复原则。实验中不根据结果改 Prompt、改 Gate、挑 seed 或重跑取优。

### 启动与恢复

在仓库根目录执行：

```bash
# 无模型预检
python scripts/runs/v18/run_v18_formal_v4.py

# 启动全新正式四轮
python scripts/runs/v18/run_v18_formal_v4.py --run

# 中断或运行错误后恢复同一个正式实验
python scripts/runs/v18/run_v18_formal_v4.py --run --resume
```

默认输出目录：`artifacts/methods/v18/formal/v18_v4_formal_002`。首次启动要求目录不存在；已有实验必须使用 `--resume`。自定义目录时，启动和恢复传入相同的 `--output`：

```bash
python scripts/runs/v18/run_v18_formal_v4.py --run --output experiments/my_v18_v4_run
python scripts/runs/v18/run_v18_formal_v4.py --run --resume --output experiments/my_v18_v4_run
```

本协议锁定四轮，不允许用 `--total-rounds` 扩展。保留该兼容参数时只允许恢复并指定原四轮上限。可选 `--pilot` 使用独立输出 `experiments/v18_v4_pilot_002`，只运行一轮，不能作为正式运行恢复。

### 停止、晋升及恢复

只有 Monitor COMPLETE 且 Gate ACCEPT 才晋升 Candidate。RETAIN 保留 Parent 并继续；NO_UPDATE / UNABLE 提前结束；运行错误标记 INCOMPLETE，保留审计产物，由用户显式恢复。四轮是上限，不强行补满。

文件锁阻止同目录并发进程。恢复要求配置、运行模式、冻结 manifest 和相关产物绑定一致；已验收的 VALID / APPLIED_DETERMINISTIC Candidate 可复用，空 Candidate 也进入 Monitor。未完成阶段按既定规则归档后恢复；重做 Grouping 时隔离旧 Diagnosis。不能为获取更好的 Gate 结果删除产物后重跑。

### 预先确定的分析

保持原 Four-Delta Gate：全部 45 个 Monitor 任务上，ΔS、ΔC、ΔCS 非负，ΔVF 非正，至少一项严格改善。统计整数计数，并同时报告比例与分母。

每轮报告 Parent/Candidate 的 S、C、CS、VF、四象限计数和配对转移矩阵；分别列出全部 Monitor、Core、回归保护任务、各 family 和联合 family。分层结果用于分析，不另设事后晋升门槛。跨轮 Parent 可能不同，不将不同轮次的配对增益解释为同一 S0 对照。

语义审计记录条件、适用范围、确定性保持及新增无依据义务，不在实验中按 Monitor 错题修改 learner。

局限保留：单 seed；Monitor 已参与 benchmark 开发；JRA-01 原合同结果仍为 HOLD_REPLICATION，v4 的独立准入决定不等于原合同通过。

### 验收记录

产物目录：`artifacts/methods/v18/v18_v4_formal_readiness_001`。包含预检、测试日志、旧冻结逐文件不变检查和新 manifest 摘要。所有本次验收均无真实模型调用。

最终验收：相关回归 572 项通过（含 29 项 v4 专项测试）；81 任务预检通过；旧冻结 16 个文件逐字节不变，S0 与原冻结一致，v17 差异摘要不变。正式输出目录尚未创建。

<a id="v18-v4-four-round-analysis"></a>

## v18 × benchmark v4 四轮结果分析

分析日期：2026-09-21。来源：experiments/v18_v4_formal_002。仅分析现有产物，未修改实验、Prompt、评估器或 Gate，未重跑模型。

### Gate 与总体效果

每轮为45个匹配任务，以下均为当轮 Parent→Candidate 计数。

|轮次|S|C|CS|VF|Gate|
|---|---|---|---|---|---|
|1|34→35|36→43|26→33|1→0|ACCEPT|
|2|35→39|43→43|33→37|0→0|ACCEPT|
|3|40→39|43→43|38→37|0→0|RETAIN|
|4|39→39|43→43|37→37|0→0|RETAIN|

Gate 要求 ΔS/ΔC/ΔCS 非负，ΔVF 非正，至少一个严格改善。第三轮因 S、CS 各降1拒绝；第四轮全部持平、没有严格改善而拒绝。最终保留第二轮 Skill，摘要 687bdcd051a4e93a75cee6b034582420d0f99fa838043b04dbb5df38aa7daf9d。

第一轮 S0 到第二轮 Candidate 的描述性差异为 S +5、C +7、CS +11、VF -1；不是额外独立终评或确定性因果效应。第三轮与第四轮 Parent 都是第二轮 Skill，却分别得到40/38与39/37的 S/CS，说明同 seed 不保证同轨迹或同结果。

### 第一轮：总体接受，同时出现真实局部退化

11 ADD。改进包括储值支付分配、证书不可复用、结算价格与差价比较、局部退换货及地址顺序规律、取消与人数限制。

迁移：CF→CS 6；VS→CS 4；VF→VS 1；CS→CF 3；VS→CF 3。故成功新增7、丢失6，净增1；合规净增7。接受不代表逐任务不退化。

CS→CF：CTRL-AIR-C03、CTRL-AIR-C04、JRA-01-C06。

- 两个 CTRL-AIR 任务：Parent 完成天气原因取消，Candidate 以无法核实内部保险覆盖为由转人工。C03 用户要求三项一起办理，不确认局部方案，导致其余升级和行李操作也未执行。这是核实门槛扩散带来的能力损失。Skill 的保险规则本来限定工作/计划变化，但执行扩展到天气原因。规则在 Diagnosis G4 中已经采用“无法核实则拒绝”的论证；Editor 基本保留了它。不能单独归因于 Editor。
- JRA-01-C06：两侧均正确完成两笔预订且转人工，Candidate 缺少 get_flight_status，cancellation_resolved=false；不是支付分配失败。
- GIR-01-C05/C06、GPC-01-C06：VS→CF，体现局部“成功违规→失败合规”。第一轮 CF 总数仍为10，因为其他 CF 被修复，聚合数掩盖了迁移。

控制任务的 Compliance 默认无 focal rule，因此 C=true 不代表所有业务规则均已检查；控制任务成功下降应单独报告。CTRL-AIR 两个退化在后续轮次持续保留。

### 第二轮：补齐有效转人工的检查，净增四个 CS

1 REPLACE、1 ADD。主要变化：在保险拒绝/转人工前查询航班状态；增加 basic_economy 两件行李的经验限制。

5个 CF→CS：GIR-01-C05、GIR-01-C07、JRA-01-C05、JRA-01-C07、RHP-01-C07。1个 CS→CF：GPC-01-C08。净增 S/CS 各4，C不变，因此接受。

GIR/JRA 四个改善与航班状态检查吻合：Parent 转人工但缺少查询，Candidate 查询后转人工，评估器判为 VERIFIED_TRANSFER/cancellation_resolved。JRA 联合目标允许“两笔预订完成 + 经核实转人工解决取消分支”，不能将它描述为取消退款已执行。GIR 同样不能说是拒绝变为实际取消。

RHP-01-C07 两侧对话有所不同：Parent 在 consolidated 下选择返回；Candidate 根据用户“当前保护 active 则交换”的表述执行 exchange。该轮没有修改零售规则，不能将这一改善直接归因于新增航空规则；Simulator 的条件表达差异也是混杂因素。

GPC-01-C08 退化来自生日漂移：冻结任务和 Parent 用户提供第二人 1992-02-01；Candidate 用户说1992-02-02，Agent 按其输入订票。保留为官方掉分，归因标记 Simulator事实漂移，不事后更改成绩。

### 第三轮：官方拒绝，但唯一掉分不能解释为 Skill 能力下降

2 REPLACE、1 ADD：退款负数比较、五人优先拆分、完整总价后重新确认。

唯一变化 GPC-01-C08：CS→CF。冻结任务要求1992-02-01，Candidate User 首条消息给1992-02-02；Agent 准确沿用用户日期。预订数量、票价180、支付与合规均正常。此轮唯一 Gate 差异受到 Simulator事实漂移污染，不能说“五人拆分”或“再次确认”导致这例失败。

不应据此改成 ACCEPT：即便仅在敏感性分析中移除该配对，其余44任务四象限全相同，仍没有严格改善。

新增拆分规则本身有语义风险：Diagnosis G006 从7人5+2成功、6人3+3失败，推到禁止3+3并使用5+余数。Analysis已承认人数、舱位和隐藏因素可能混杂，Gap仍输出禁止指令。这是可疑归纳，不等于已证明该规则导致 Monitor退化；本次未晋升。

### 第四轮：无测得改善，语义上再次出现负面证据变禁令

1 ADD：consolidated 情况不要套用 partner_direct 的返回动作，但没有给出正确替代动作。45对任务的四象限均不变，所以 Gate 因持平拒绝；不是新增测得退化。

Diagnosis G03 明确认为“不调用返回工具”本身就是可执行修复；其分析同时说明不知道正确替代动作、没有 consolidated exchange/transfer 正例、因果机制不明。这与开发时“纯负面证据不能单独生成 stopping/prohibition gap”的边界有明显张力。问题已在 Diagnosis 形成，Editor保留。tentative字样没有消除命令式禁令的实际效果。该规则未进入最终Skill。

### 联合任务与尚未解决的问题

Monitor各联合family均4任务：第一轮JRA CS 1→2、JSG 2→4；第二轮JRA 2→4、JSG 4→4；第三、四轮两族均维持4/4 CS。这支持联合任务的改善，但只有8个联合Monitor样本、单seed，并非泛化证明；JRA部分成功依赖 VERIFIED_TRANSFER 的操作定义。

最终第二轮Skill在第四轮Parent评估中：37 CS、6 CF、2 VS、0 VF。

- CF：CTRL-AIR-C03/C04（天气取消退化）、GPC-01-C08（本轮用户生日漂移需按轨迹解释）、RAP-01-C05/C08、RHP-01-C05。
- VS：GMB-01-C06/C08。说明两件行李经验规则未消除所有行李分类违规。
- RAP/RHP残留未逐一完成因果归因，不能直接认定某条规则导致。

四轮共15 ADD、3 REPLACE、0 DELETE；后两轮未接受。正式实验没有实证验证DELETE带来收益，也没有删除已晋升的保险门槛。Monitor私有控制任务不会自动成为Diagnosis输入，因而Gate放行的局部伤害可能持续存在。

### 建议

保留原始成绩与全部产物。优先独立审计/修复 Simulator 对任务事实的忠实性（生日、条件语义），不将它变成Diagnosis的新义务。将本轮新语义失败作为开发证据，分别检查证据不足→核实门槛、混杂对照→确定拆分限制、负面关系→禁止动作；不把具体任务名写入Prompt。

后续先做隔离的规则消融验证保险条款与控制退化的关系，再决定方法或Gate是否需要变更。当前Gate只保护整体四个指标，并不保护每个任务或family；若引入控制组单独门槛，应属于下一版预注册协议，不追改本次决定。对需要重复采样确认的边际效果另开实验，不按本轮结果挑选重跑。

可复核逐任务计数：artifacts/methods/v18/v18_v4_four_round_analysis_001/metrics_and_transitions.json。所有主要判断来自四轮 summary、results、Diagnosis、Skill差异及上述关键任务的 simulation/evaluation 文件。
