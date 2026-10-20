# V22 有效认识修订与固定初稿消费

[返回索引](README.md) · [最小接口](MINIMAL_INTERFACES.md) · [研究设计](DESIGN.md) · [首次计划](../../../experiments/methods/v22/04_fixed_consumption/config/plan.json) · [一次恢复计划](../../../experiments/methods/v22/04_fixed_consumption/config/plan_recovery.json) · [真实运行报告](../../../experiments/methods/v22/04_fixed_consumption/reports/REPORT.md)

更新日期：2026-10-14。状态：**有效 Memory、具体更新规则及固定初稿双分支入口已实现；首次完整学习因输出截断停止，已另行声明一次纯认识修订恢复。** 本页说明机制与边界，恢复进展和最终结果以报告为准，不据实现完成推断已经得到有效认识、非恒等变换或行为收益。

## 1. 这一小步解决什么

本次路径把三个环节连起来：**先修订当前可消费的作用认识，再明确如何据此作更新决定，最后在同一完整初稿上检查认识是否实际进入了更新构造。** 不重新生成一个更弱的 Diagnosis，不用更长的自证表替代更新规则，也不为获得变换而重试。

| 环节 | 已实现的职责 | 代码 |
|---|---|---|
| 有效认识修订 | 重读已有实际反馈，修订 claim，显式退出已被反驳的限制，保留原始来源与未解决的不确定性 | [effective_memory.py](../../../src/skill_evolution/v22/effective_memory.py) |
| 纯认识修订入口 | 在单独恢复计划内只纠正已有认识，不重做完整 Replay，不创建新 Effect | [effective_reconciliation.py](../../../src/skill_evolution/v22/effective_reconciliation.py) |
| 具体更新构造 | 在一次 Fusion 响应内判断适用性、已有覆盖及必要变换；Editor 落实有效方案 | [effective_update.py](../../../src/skill_evolution/v22/effective_update.py) |
| 固定初稿消费 | 冻结完整初稿和当前证据，分别使用空 Memory 与有效 Memory 构造更新，记录来源、调用及真实文本 | [consume_fixed_plan.py](../../../src/skill_evolution/v22/consume_fixed_plan.py) |

这仍是预条件化机制的一次局部检验：Memory 提供更新作用认识；Fusion 决定是否改变方向、尺度或组合；Editor 负责实现这些要求。Memory 本身不是整个方法。

## 2. 有效 Memory：保存历史，也允许修正当前认识

### 2.1 为什么需要 `retire_limits`

只允许追加限制会留下一个问题：即使旧限制含有已被轨迹反驳的事实，后续版本仍自动继承它。再添加一句相反的“纠正说明”，会让旧断言和新认识一起进入 Fusion，系统没有明确表示哪一项仍然有效。

新协议在 `memory_delta` 中增加 `retire_limits`。每个退出操作只指向**被本次替换的旧 Effect 的一个确切限制索引**，并包含理由和本次发现 ID。程序检查版本、索引及发现引用，将旧限制正文、原上下文、退出理由和新依据存入 `retired_limits`，使其退出新版本的活动限制集合。

这是核心状态操作：它改变后续更新器应当消费什么知识，而不只是增加一份解释。它不删除原始轨迹、旧认识快照或退出依据，也不证明模型的反驳判断正确。

默认行为仍然保守：

- 未显式退出的旧限制自动继承；`retire_limits=[]` 是合法常态。
- 未检验范围、单项归因未知和仍成立的反例，不能因为修订 claim 就消失。
- 只有具体旧断言被当前依据反驳时，才提出相应退出；不是清空“不方便”的不确定性。
- 退出错误限制后，新活动限制表达正确范围及剩余未知，不把错误原句作为“纠正备注”重新塞回活动集合。

本次认识修订重读的是已有真实执行；**重读与纠错不增加独立试验次数，也不形成新的行为效果证据。** 认识修订阶段不预先写好 Fusion 应采用的 Skill 改法。

### 2.2 claim 与每条 limit 各自绑定上下文

一条新 claim 可能来自本次反馈，但它仍继承来自更早反馈的限制。因此，持久状态分别记录 `claim_context_id` 与逐条对应的 `limit_contexts`，不能把整条认识粗略绑定到其全部历史。

旧记录若只有唯一来源上下文，可恢复该上下文；若混合多个上下文且没有明确元数据，则保留未知。消费视图用 `H1::`、`H2::` 等别名指向各自历史，无法确定的引用标为 `history_unknown::`，不冒充当前 `P1`／`C1` 事件。

`effective_consumption_payload` 生成只读消费视图：保留活动 claim、活动 limits、实际更新与比较条件、原始事件和静态来源；保留 Effect ID 供后续变更引用。历史来源去重，重复的大型动作列表不反复输入；被省略的动作列表不能被推断为完整可见。

旧 `basis.finding.observation` 等模型解释不再作为活动认识重复输入，消费视图只保留其 `finding_id` 定位和相应原始来源。已退出限制也不进入活动视图。**旧解释留档不等于旧解释仍是真实事实。** 完整持久 Memory 与原始输入保持不变，验证及状态写入仍基于完整输入。

### 2.3 完整学习与本次纯认识修订分开

首次计划未指定 `memory_profile`，按 `full_v1` 重建原消息：执行完整的 Replay／Memory 联合后处理，仍需回应原 watch 问题，可形成有来源的新认识或修订既有认识。

已确认首次调用返回 `finish_reason=length`：prompt 为 26,990 token，completion 为 16,384 token，其中 completion 全部为 reasoning，正文为空，总计 43,374 token。该调用未形成有效 Memory，也未进入 `construct`。原调用、失败状态及成本保持不变，不能提取部分推理补成通过产物。

[独立恢复计划](../../../experiments/methods/v22/04_fixed_consumption/config/plan_recovery.json) 使用 `memory_profile="revision_only_v1"`，将这一次调用限定为**纠正或限定已有认识**：

- 每个认识增量必须替换已有 Effect；不能新建无历史来源的 Effect，未需修订时允许空增量。
- 不重新回答整套 Replay watch；消费视图的 watch 为空，也移除相应 watch 来源别名。完整原始初稿和执行前问题仍保存在绑定输入中，后续两个构造分支继续使用原完整初稿。
- 当前所有事件、动作、观察、身份、状态和比较条件保留。去掉重复的 `command_sets` 及其列表引用，保留已记录的 `action_in_admissible_commands` 标志；该标志不提供完整合法动作列表，不能据此推测未展示的命令或反事实合法性。
- 保留原始 Skill、diff、认识依据与适用限制；`retire_limits` 的确切定位、当前发现依据和未退出限制继承规则不变。

这改变了本次认识修订的任务边界，没有放宽旧完整 Replay 的核验规则，也没有把原失败包装成“没有变化”。新 profile 独立保存输入、消息、输出与失败；旧 `full_v1` 消息仍按原规则重建。纯认识修订如果也失败，按本次计划停止，不继续追加恢复。

## 3. Fusion：让机制复杂度用于具体更新决定

新的 Fusion 提示要求在**同一次响应**中完成以下判断，不对应四次 LLM 调用，也不要求输出逐项分析表。

| 判断 | 要回答的决策问题 |
|---|---|
| 对齐适用认识 | 这条响应认识涉及当前哪项要求的可见条件、策略、义务范围或协调关系？相关 Parent 依赖和执行条件是否匹配？ |
| 检查已有覆盖 | 初稿是否已经处理这个问题？若已处理，剩余偏差究竟在哪里？ |
| 构造必要变换 | 是否需要更换策略或顺序，改变义务强度／条件／范围，或协调重复、冲突、依赖的要求？ |
| 保留观察去向 | 什么实际观察会反驳这次决定？哪些有效行为可能受影响，需要继续观察？ |

有界探索不需要先获得已经隔离的单项因果效应。具体机制证据与可见条件能够支持试探性构造时，可以提出带范围和观察问题的修订；但不能将其写成已证实的作用规律。

两类容易误用的材料需要区别处理：

- **另一条成功路径：** 在确实适用且执行可核对的条件内，它可以挑战过强的必要性要求，支持将相应义务改成条件化或可选；不能据此把这条替代路径编成新的通用必经步骤。
- **事实计数纠正：** 修正步数、动作次数或事件描述，不自动识别编辑效果，也不自动支持加强动作过滤、增加必做检查或给某一编辑分配收益。

恒等决定仍然合法。`changes=[]` 的理由应具体说明初稿如何覆盖相关决策，或缺少哪项适用性／机制依据；不能在已有具体材料可分析时，仅以“因果尚未证明”结束判断。反过来，也不能为了展示 Memory 价值而强制任何要求发生变化。

## 4. 保持紧凑输出与真实落实边界

Fusion 与 Editor 继续复用原 `FUSION_SHAPE`、`EDITOR_SHAPE` 及 `apply_fusion`／`validate_editor`，没有加入方向、尺度、关联的逐维自证字段。

Fusion 的 `intent` 不变。每项替换交付完整的新要求，保留仍有效的条件、局部保留行为、恢复、依赖和停止义务；不能用新增的一句话覆盖原整组要求，也不能以“其他保持”让程序猜测继承。未涉及要求原样继承；受影响的观察问题必须有明确去向。若需要改变目标、存在不可落实的条件或未解决冲突，返回 `needs_revision`。

Editor 接收装配后的完整有效 Plan，只消费要求依据实际引用的 Memory 及其必要限制。它可以调整等价表达与位置，不能自行恢复失效认识、加强义务、放宽条件或改选策略。重要例外集中报告，存在阻断时返回 `needs_revision`，不发布偷偷删掉部分要求的 Candidate。

组级文本定位保留，字符覆盖和六维自证不恢复。`issues=[]` 只表示未报告例外；摘录存在、要求 ID 覆盖和来源合法都不证明语义保持。行为收益尚未验证，也不自动成为构造阻断，应保留在观察问题或认识限制中。

## 5. 固定完整初稿的两个消费分支

入口从已核验的反馈完成产物及其来源 cycle 读取完整 `initial_plan.json` 和当时的 `inputs/diagnosis.json`。初稿包含全部 intent、requirements、watch 和 open；不重新调用 Diagnosis、不删除难处理的要求，也不根据分支结果调整初稿。

| 分支 | Fusion 输入 | 后续 |
|---|---|---|
| `current` | 同一完整初稿、同一当前 Parent 证据、空 Memory | Fusion 就绪且无阻断时，最多一次 Editor |
| `history` | 同一完整初稿、同一当前 Parent 证据、此次修订后的有效 Memory | 相同规则和就绪条件，最多一次 Editor |

两分支使用相同的 Fusion／Editor 方法，唯一人为改变的输入是 Memory；分支互不读取对方输出。实际有效方案可能因 Fusion 决定而不同，Editor 收到的要求也随之不同。

恒等 Fusion 仍可进入 Editor，因为将初稿落实为 Skill 与是否发生预条件化变换是不同问题。`no_change`、`needs_revision` 或技术失败则按各自含义停止相应路径，不要求每个分支都产出 Candidate。本次没有构造返工或按结果重试；一分支的技术失败不阻止独立分支完成，但整体会保留未完成状态。

这是**局部构造对照**。它可以检查相关认识是否改变具体要求、有效要求是否进入文本，以及两分支是否得到不同构造决定。它不是“同信息、不同更新机制”的收益对照：`history` 得到了额外历史认识，且每分支只有一次语义样本。当前证据本身也可能支持相同改变。仅有历史引用、不同措辞或不同 Candidate，不能证明历史独有贡献、预条件化优势或执行收益。

## 6. 入口、预算与产物

每个 operation 最多调用 **5 次 `deepseek-v4-pro`**：1 次学习／认识修订、2 次 Fusion、最多 2 次满足条件的 Editor。本次首次 operation 实际在第 1 次调用失败；另行声明的恢复最多再调用 5 次，**包含首次失败的累计预算最多 6 次语义调用，只允许这一次恢复**。不是失败后重复申请一套新预算。

新增环境执行为 **0**，不部署 Candidate、不修改活动 Skill，不从两个分支中择优采用。每个 operation 分别记录 HTTP 尝试、失败调用、实际已报 token 和未知用量；汇总本次工作时必须计入首次失败，不能只报恢复成本。更早复用的执行和学习保留来源，不重复计入本次增量。

入口分成三步，便于先查看有效认识，再决定是否继续消费。以下展示本次独立恢复对应的命令，必须显式指定 `plan_recovery.json`；这是恢复首次创建时的入口说明，不是授权再次运行。已有输出目录不能覆盖，`construct` 也不能重复执行。

```bash
python -m src.skill_evolution.v22.consume_fixed_plan learn \
  artifacts/methods/v22/compact_cycle_20261014/feedback_completion \
  --output-dir artifacts/methods/v22/fixed_consumption_20261014/recovery \
  --plan experiments/methods/v22/04_fixed_consumption/config/plan_recovery.json

python -m src.skill_evolution.v22.consume_fixed_plan construct \
  artifacts/methods/v22/fixed_consumption_20261014/recovery

python -m src.skill_evolution.v22.consume_fixed_plan verify \
  artifacts/methods/v22/fixed_consumption_20261014/recovery
```

`learn` 成功时保存 `memory_effective.json` 并进入 `memory_ready`；应先查看活动认识是否仍含已识别的事实错误，不手改模型输出。`construct` 只允许从有效 `memory_ready` 继续一次。`verify` 离线重建来源、输入、消息、增量、文本与成本，不发起模型或环境调用，也不提供语义认证。

主要产物包括：冻结的 `current.json` 与 `initial_plan.json`、完整 `inputs/`、真实 `calls/` 与验证后的 `outputs/`、有效 Memory、各分支有效 Plan，以及合法 Candidate 的 `SKILL.md`、实际 diff 和 lineage。`consumption_checked` 表示两分支形成了合法构造结果，包含合法停止；不表示两者都产生 Candidate，更不表示行为检验通过。

首次计划见 [plan.json](../../../experiments/methods/v22/04_fixed_consumption/config/plan.json)，唯一恢复计划见 [plan_recovery.json](../../../experiments/methods/v22/04_fixed_consumption/config/plan_recovery.json)。真实调用状态、观察及限制集中记录于 [04_fixed_consumption/reports/REPORT.md](../../../experiments/methods/v22/04_fixed_consumption/reports/REPORT.md)。旧协议、旧提示、失败响应、Memory 快照和实验结论继续按各自版本保留；本页不回填或改写它们。

## 7. 完全相同的继承问题：独立离线去重

本次两个 Editor 都原样重复了有效 Plan 的观察问题，被原增量接口拒绝。新增 [editor_watch_reconciliation.py](../../../src/skill_evolution/v22/editor_watch_reconciliation.py)：只有同 ID、完整对象逐字段相同的继承问题才从 Editor 增量中去重；同 ID 任何变化仍拒绝，新问题与全部其他字段继续按原契约验证。继承问题仍在有效 Plan 中，Candidate 文本、映射、更新决定及认识不变。这项确定性处理不需要模型再解释一次相同内容。

按[离线处理约定](../../../experiments/methods/v22/04_fixed_consumption/config/offline_normalization.json)重建原始调用与输入后，两分支各形成独立派生候选，保存实际 diff、原调用 hash 和归一化版本。源操作继续是 `comparison_incomplete`，不是回填原运行成功；新候选都是 staging、未执行，归一化也不解决 u6 的完成／恢复语义问题。

```bash
python -m src.skill_evolution.v22.editor_watch_reconciliation recover \
  artifacts/methods/v22/fixed_consumption_20261014/recovery current \
  --output-dir artifacts/methods/v22/fixed_consumption_20261014/new_offline_current

python -m src.skill_evolution.v22.editor_watch_reconciliation verify \
  artifacts/methods/v22/fixed_consumption_20261014/new_offline_current
```

历史分支使用 `history` 和另一个新目录。入口不调用模型或环境，不执行语义修复，也未隐式接入原运行器；不能拿这种等价去重掩盖实质条件变化或抹掉失败费用。
