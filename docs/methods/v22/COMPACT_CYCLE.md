# V22 紧凑接口：真实反馈学习与后续更新构造

[返回索引](README.md) · [接口设计](MINIMAL_INTERFACES.md) · [默认计划](../../../experiments/methods/v22/03_compact_cycle/config/plan_scoped.json) · [真实报告](../../../experiments/methods/v22/03_compact_cycle/reports/REPORT.md)

更新日期：2026-10-14。新路径已实现，并通过独立补充完成真实末尾反馈，最终形成三条操作内认识；Fusion 本轮选择恒等，未展示历史驱动的非恒等更新。真实调用、语义限制与成本见本阶段报告。旧无历史轮次、Editor v1／Replay 首版失败产物及旧校验入口保持原样。

**后续协议状态（2026-10-15）：** [08 共同决策结构与两轮更新](GROUPED_TWO_ROUND_PROTOCOL.md)已完成设计，拟复用本页紧凑学习能力，加入冻结分类、程序 Gate 和实际 Parent 继承。当前修订采用整体成功率严格提升的 Gate、轮间不重复 Train 和单一候选主线；共享接口与真实 Parent 继承正在补齐，Replay → Gate → Memory 的连续运行器仍待接入；本页 03 操作内路径和既有结果继续按原协议解释，不能当作已完成连续发布。

## 1. 本次实现范围

`compact_cycle` 从已有真实 Train 轨迹学习少量作用认识，再让这些认识参与一次后续更新构造及反馈。原 Candidate 仍未采用，因此当前 Parent 明确为 No Skill；两条有效 Parent 执行直接复用，不重复运行或计费。本次不是从已部署 Candidate 开始的持续发布，也没有正式 Gate。

| 环节 | 实际实现 |
|---|---|
| Replay／Memory 初始学习 | 核验旧来源，用完整紧凑轨迹和实际文本形成稀疏发现、未知及认识增量；操作内保存 Memory 快照 |
| Diagnosis | 只输入 Parent 轨迹、基础协议和当前能力，独立形成 Plan；不读取旧 Candidate、历史初稿或已学 Memory |
| Fusion／Compiler | 读取该 Plan 和全部相关的小规模认识；输出要求原→新变更、依据和观察问题增量，程序装配有效 Plan |
| Editor | 按有效 Plan 生成完整 Skill、组级定位和重要例外；只接收要求实际引用的认识，不重放完整历史 |
| 实际执行 | 冻结 Candidate、diff、要求、观察问题和来源；两项固定 Train 任务各执行一次 |
| Replay／Memory 后续学习 | 基于新 Candidate 的实际执行更新操作内认识，继承历史依据及限制；不回写旧预期或部署 Skill |

主路径在 `compact_learning.py`、`compact_update.py`、`compact_cycle.py`；`compact_learning_view.py` 区分当前与历史消费范围，`complete_feedback.py` 提供显式一次末尾反馈补充入口。沿用既有记录式模型客户端和 ALFWorld 执行适配器。没有改写旧 v0／v1 协议或增加独立 Review／总结 Agent。

## 2. 紧凑表示与关键边界

Plan 包含 `intent`、条件化 `requirements`、关键观察 `watch` 和构造阻断 `open`。未验证的收益放观察问题与认识限制，不因效果尚未证明就阻断所有新构造。

来源用 `P1:4`、`C1:7`、`skill:candidate` 等可解析别名；轨迹只保存一次可见正文，完整合法动作列表按内容去重。原始轨迹仍保留，命令列表去重不删合法动作，也不让学习器只看有利片段。旧轮次的紧凑观察问题从冻结材料派生，明确标为重建，不能声称它在旧 Candidate 执行前已经存在。

Fusion 的增量针对完整要求单元：未改项原样继承，被替换单元中仍有效的义务写进新正文，旧来源与新依据共同保留。受影响观察问题有明确去向。允许有理由的恒等；实际要求变化、历史引用与效果证明分别记录。

Editor 的组级摘录只证明可定位到文本。空例外不认证语义保持；有实质偏离则返回上游。本次最多允许一次明确的 Fusion／Editor 构造返工，不把它当作格式修复或反复搜索。

Replay 模型只输出 `findings`、`open` 和 `memory_delta`。相关问题可以共同回应，不要求目标 × 任务矩阵；漏答问题由程序标为未评估，并阻止发布完整反馈。程序核对来源和去向，仍不能证明解释正确。已知未覆盖条件可留下具体限制，不能因任务成功就写成保持。

Memory 保存条件化判断、来源、比较边界、反例和未知；旧依据及限制由程序继承。整包观察不能分摊成独立编辑收益，静态实现限制不能伪装成已观察回归。仅 Parent 事件或未执行要求不足以形成新的编辑响应认识。

## 3. 调用预算与出口

轨迹模型为 `deepseek-v4-flash`，所有自进化语义调用为 `deepseek-v4-pro`。模型分工独立于机制设计；本次同时换模型与接口，不能将稳定性或费用变化单独归因于接口。

常规调用为初始 Replay／Memory、Diagnosis、Fusion、Editor、后续 Replay／Memory，共五次。仅 Editor 明确返回 `needs_revision` 时允许一次上游返工，至多七次。没有自动 JSON 修复或语义重试；传输沿用已有有界客户端，所有尝试计费。

新 Candidate 最多两次环境执行，每次 50 步，无结果导向重跑。无需修改、证据不足、返工仍受阻均可正常停止；格式、引用或模型错误独立记录，不能转成合法恒等或无作用结论。已有有效初始 Memory 可以保留，但失败不能发布最终 Memory 或完整闭环状态。

`cycle_complete` 表示来源、构造、两次完整匹配执行及后续反馈已贯通，不表示采用或收益成立。报告另列提供给 Fusion 的认识、变更引用的认识、要求内容变化及原生结果；没有执行初稿 Candidate 对照，不能据此声称变换优于初稿。

## 4. 运行与核验

```bash
conda activate alfworld
python -m src.skill_evolution.v22.compact_cycle run \
  artifacts/methods/v22/no_history_20261014/round \
  --output-dir /path/to/new_compact_cycle --dry-run

python -m src.skill_evolution.v22.compact_cycle run \
  artifacts/methods/v22/no_history_20261014/round \
  --output-dir /path/to/new_compact_cycle

python -m src.skill_evolution.v22.compact_cycle verify /path/to/new_compact_cycle
```

输出目录必须不存在且在原轮次之外。`--dry-run` 不调用模型或环境。`verify` 重建来源输入、模型调用、要求增量、Memory、Candidate／diff、执行比较与费用，不进行语义再评审或网络调用。

```text
plan.json / manifest.json / report.json
inputs/<stage>.json / calls/<stage>.json / outputs/<stage>.json
memory_initial.json / initial_plan.json / effective_plan.json
effective_plan_revision.json               # 仅发生上游返工时
execution_plan.json
candidate/SKILL.md / actual.diff / lineage.json
candidate_runs/<task>/skill_<run>/trajectory.json
memory_final.json                         # 仅后续学习成功时
```

全部操作内状态均留在独立目录。失败原始响应不被人工补写成成功 JSON。原历史费用只作引用，本次新增语义调用、环境请求、HTTP 尝试、已报告用量和未知用量单独汇总。

## 5. 本轮真实链路的判读边界

当前来源仍是两条 No Skill Parent 与旧 Candidate 的真实 Train 执行。初始学习得到的认识包含旧照明完成序列及动作定位限制；结构通过后仍须检查语义。此次模型漏读 Parent 照明第 7 步，把两次非法动作误写为一次，虽然输入完整保留了第 4、7 步。原输出不改写，这条认识不作为已核准事实发布。

Fusion 明确选择恒等，要求与观察问题都未变；Editor 只读取有效要求实际引用的认识，此次未引用任何 Memory，因此不能声称历史改变了 Skill。这个结果既不强制转成失败重试，也不算预条件化收益。独立复核发现其不变理由过度强调未隔离因果：带边界的联合响应仍可支持条件化探索，能否充分利用这类证据是后续核心规则问题。

本轮初始版本将 Memory 完整来源直接用于消费，两个 Effect 的事件／合法动作展开导致 Fusion prompt 达到 26,225 tokens。末尾反馈还发生历史／当前 C2 别名混淆，故补充独立 scoped 视图：历史来源使用 H1:: 等上下文别名，按内容去重、保留语义证据并去掉重复动作列表；当前完整轨迹和机械统计一起输入，原持久 Memory 不变。未来默认 scoped_v1 已用于学习及 Fusion／Editor；旧计划继续重建 legacy 消息。本次真实补充调用验证学习视图，完整新 profile 仅通过离线集成测试，没有重跑整轮。

详细执行、后续 Memory 修订、独立语义复核与累计成本，以本阶段报告和原始产物为准。正式采用与全局 Memory 发布均未进行。

## 6. 本次补充完成与复核

原 `recovery/` 最后反馈因错误引用 C2:8 被拒，保留 error 和原始响应。修复视图后只调用一次 `complete_feedback`，没有新环境执行或新 Candidate；结果 `feedback_ready=true`，最终 Memory 为三条认识。清洁当前七步与旧八步已区分，m2 通过 replace 明确改为 Parent 两次非法动作。照明增加另一成功路径，不能说旧 m1 的历史观察被推翻。

旧限制与纠正说明仍机械并存，m1 一句新旧 Candidate 表述也不够严谨；来源核验并不完成这些语义责任。后续继续处理失效限制的消费及联合观察如何触发具体更新，而非将本次结果视为预条件化收益。

```bash
python -m src.skill_evolution.v22.complete_feedback verify \
  artifacts/methods/v22/compact_cycle_20261014/feedback_completion
```

补充入口只接受已绑定且最终反馈失败的旧 cycle，单独计划规定一次语义调用、零环境执行及累计预算；不自动修复旧 JSON，不覆盖失败。完整启动参数和预算保存在 `experiments/methods/v22/03_compact_cycle/config/plan_feedback_completion.json`。

本次共 7 次语义调用、20 次环境请求、27 次 HTTP，报告 182,439 tokens，另有首次连接错误用量未知。方法测试 167 项、环境测试 35 项通过；最终事实与费用以[报告](../../../experiments/methods/v22/03_compact_cycle/reports/REPORT.md)及其小型结果表为准。Candidate 仍为 staging，当前 Parent 未改变。

## 7. 后续独立消费入口

[FIXED_CONSUMPTION](FIXED_CONSUMPTION.md) 在上述材料之上新增有效认识修订和具体更新规则：显式退役错误旧限制，区分每条认识／限制的上下文，再冻结原完整初稿比较空历史与有效 Memory。仅修订已有认识时使用独立轻量 profile，不重新承担完整 Replay 问题覆盖。新入口及真实状态另存于 [04_fixed_consumption](../../../experiments/methods/v22/04_fixed_consumption/reports/REPORT.md)；本页记录的旧运行、失败、认识快照、消息和费用均未回写。该独立入口尚未替换 `compact_cycle` 的原默认 profile。
