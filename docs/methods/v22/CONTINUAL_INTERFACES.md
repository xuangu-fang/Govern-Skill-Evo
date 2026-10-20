# V22 共享决策表示与真实 Parent 继承

[返回索引](README.md) · [两轮协议 v2](GROUPED_TWO_ROUND_PROTOCOL.md) · [紧凑接口基础](MINIMAL_INTERFACES.md) · [08 配置](../../../experiments/methods/v22/08_grouped_continual/config/plan.json)

日期：2026-10-15。**本页记录第二步接口实现及其离线合成验证。后续已接通[单主线运行器](CONTINUAL_RUNNER.md)，仍未调用真实模型或执行环境。** 本页代码提供可组合函数，实验命令由后续运行器提供。旧 01—07 的双分支、No Skill／staging 运行器保留原边界，不用它们冒充连续主线。

## 1. 本次落实的研究约定

- Gate 只负责整批版本晋级：完整可比的同批执行中，Candidate 成功率严格高于 Parent 即 ACCEPT，否则 RETAIN。允许整体提升同时存在局部退化；两种 Gate 结果都可以产生有价值的 Memory。
- 严格流式指轮间 Train 不重复；轮内 Parent 与 Candidate 仍在相同任务上各执行一次。没有额外旧任务回归批次，因而不声称测量了上一批任务的跨轮遗忘。
- 08 只保留一条更新主线，不构造、执行或选择 Direct。历史实验原样保留。

两轮任务、预算和停止条件以协议 v2 为准：20 个不同 Train，最多 40 episodes、9 次 Pro。接口可以用少量合成任务验证分支；这不改变真实实验的每轮十任务声明。

## 2. 模型共享什么，程序维护什么

现有模型输出没有新增逐组审查表：Diagnosis 仍输出 `Plan(intent, requirements, watch, open)`；Fusion 输出稀疏要求变更；Editor 输出全文、要求定位与重要例外；学习输出 `findings/open/memory_delta`。触发条件、目标行为、保护范围和相互关系仍写在有用途的正文中。

| 共享对象 | 实现与使用 | 不代表什么 |
|---|---|---|
| 当前 Parent 经验 | `prepare_current` 只导出当前整批、完整 Train 事实与实际 Skill；Diagnosis 不收到 Memory | 当前 Parent 不再固定是 No Skill；也不把历史解释混入当前诊断 |
| 分类输入与冻结分组 | `build_grouping_input` 程序摘要；`freeze_grouping` 绑定输入、Prompt、Parent 与一次分区；`attach_grouping` 复用同一结果 | 不保证分类语义正确，不增加分类复核调用 |
| 决策来源 | `group:<round_id>:<group_id>` 与真实 `P1:step` 共存于 `requirements.basis` | 引用组名不证明缺陷，也不证明历史 Effect 适用 |
| 有效要求 | `update_payload` 绑定当前轮、任务、Parent、分组与实际 Memory；`compile_update` 复用 D/S/C 增量装配 | 不是重建第二套 Plan，也不强制非恒等变换 |
| 实际文本与观察问题 | `realize_editor` 返回 Candidate 快照及合并新 `watch` 的执行 Plan；diff 使用真实 Parent 文本 | 摘录存在不证明语义保持；新增观察问题不能在交接中丢失 |
| 学习来源 | `prepare_grouped_learning` 绑定实际配对、diff、分组与 Gate；`learn_grouped_memory` 校验后产生认识和发布凭据 | Gate 结果不成为每条编辑的质量标签，整体比较不支持单项因果归因 |
| 轮末状态 | 一个不可变记录绑定选定 Skill、有效 Memory、已用任务和结算来源 | 不是复杂状态机，也不包含自动重试或恢复调度 |

分类只发送 `build_grouping_input(...)["model_input"]`：其中有不透明 `T1…` 别名、可见请求／协议／能力、完整有序动作和结果。`bindings` 是程序保存的别名到实际任务、轨迹映射，不能整个发给分类模型。重复动作和非法动作保留；相同动作候选列表去重。摘要不包含 Memory、Candidate、任务类型、gamefile、选题理由、历史成绩、模型推理或 HTTP 包装。

一项要求可以引用多个决策组，但每个所引组须有该组的实际 Parent 事件支持。程序检查来源是否连通，不用字符串模板声称验证了触发条件或行为推理。Candidate 按同一任务继承冻结组，不重新分类；跨组影响可在发现中引用多个组／事件。跨轮同名 `G1` 没有永久语义身份，Fusion 仍须核对条件和编辑依赖。

## 3. 真实 Parent 与 Memory 怎样共同继承

`continual_state.py` 提供以下顺序：

```text
initial_state(campaign)                         # No Skill + []
open_round(published_state, new_train_ids)       # 拒绝轮间重复任务
  → 使用 context.parent 执行与诊断
  → 在同一个 Parent 上构造 Candidate
gate_round(context, candidate, parent_runs, candidate_runs)
  → prepare_grouped_learning → learn_grouped_memory
finish_round(state, context, candidate, gate, memory_after, receipt)
  → write_state(new_path, next_state)
  → 下一轮 read_state → open_round
```

这是共享函数的交接示意；任务调度、调用存档、预算检查和异常停点现由后续[运行器](CONTINUAL_RUNNER.md)负责。当前协议不提供自动恢复。

ACCEPT 选择 Candidate，RETAIN 选择原 Parent；两者都继承有效学习后的 Memory，合法空增量可以保持原认识。首次 RETAIN 后第二轮仍从 No Skill 开始是有效结果，不能为展示非空继承而强制采用。

状态保存 Skill 的实际文本与内容 hash。`materialize_skill` 将这个快照精确写成下一轮 Actor 的 `--skill-file`，不重新读取可能已变的旧路径；No Skill 返回 `None`，省略 Skill 注入。`prepare_evidence(..., parent_skill=...)` 支持实际 Parent；旧调用不提供参数时仍要求 No Skill。非空 Parent 的 diff 标识为 `parent/SKILL.md`，不再误写为 `parent/NoSkill`。

`finish_round` 必须同时拿到匹配当前轮、Gate、前后 Memory、学习输入输出的 receipt。缺少凭据、学习校验失败或来源错配均不产生下一状态。`write_state` 原子创建并拒绝覆盖已有文件，发布失败则下一轮不能读取一个半成品。这些 hash 用于发现来源混接／内容变动，不是对模型判断的认证或加密签名。

## 4. Gate 与反馈学习的边界

Gate 为 `v22.continual_gate.v1`，规则为 `v22.native_success_improvement.v1`。完整同批时分母相同，直接比较成功数量即可，不能用组平均分、回归数量或效率作额外否决／破同分。

例如合成测试中 Parent 为 `1/3`，Candidate 为 `2/3`，其中原成功任务变失败、另两个失败变成功：Gate 必须 ACCEPT，Memory 仍保存那项退化的观察与限制。另一个 `1/3 → 1/3` 的合成轮次必须 RETAIN，即使某个局部行为改善。**这些数字只是代码测试输入，不是 ALFWorld 实验结果。**

技术中断、漏项、重复轨迹、错误 Skill 或不可比条件会使 Gate 校验失败，不生成普通 RETAIN。正常步数耗尽仍是完整任务失败。合法无候选用 `candidate=None` 和空 Candidate 记录得到 `RETAIN / no_change`；Candidate 成绩为缺席而不是实测持平。缺证据／待修订原因须留在其上游产物，不被 no_change 抹掉；技术错误不能进入这个语义出口。

准备学习包时重算 Gate，确认它来自该批真实记录；包整体再绑定，发学习请求及应用结果前都检查未被拼接替换。学习沿用有效认识与限制退役规则，程序在 Effect 的已有 `basis.actual_update.update_context` 中附加本轮冻结分组、实际 diff 和 Gate 档案。旧 Effect 和旧消息协议不迁移；没有此附加字段的历史记录仍按原约定解释。

无 Candidate 的当前观察可以修订已有 Effect，但不能新建声称本轮编辑产生行为效果的认识。空历史无修改时允许程序形成合法空增量，不增加模型调用。有修改时，局部正负认识无论 ACCEPT／RETAIN 都保留联合更新的归因限制；不能由 Gate 标签自动推导 Effect 正负。

## 5. 已完成验证与下一步

新增 29 项离线测试，V22 方法测试共 **281 项通过**。覆盖了完整分区和隐藏字段排除、分组／Parent／输入篡改、跨组来源、整体提升伴随退化、持平与下降、无候选、学习缺失／错配、严格流式和文件不覆盖。

另有一条完整合成接口验证：R1 从 No Skill 构造并采用 Skill，保存带分组与 Gate 的 Effect；R2 读取文件中的实际状态、注入继承 Skill、独立形成初稿，Fusion 引用该 Effect 改变要求，Editor 在非空 Parent 上修订，Replay 后持平 RETAIN，但 Memory 继续更新。此处 Fusion 和结果由测试夹具提供，只证明信息可达和程序交接，不能证明模型会作合理变换或实际行为改善。

后续[单主线运行器](CONTINUAL_RUNNER.md)已串联本页接口，保存固定 Prompt／模型调用及各阶段产物，核对十任务全批、调用次数、输入体积、执行前冻结与异常停点。新增 30 项测试，V22 共 311 项离线测试通过；08 的 `implementation_ready` 已为 `true`。下一步是按冻结协议开展真实执行；当前没有开始两轮实验，也没有得到新的机制效果结论。

实现文件：[`grouped_representation.py`](../../../src/skill_evolution/v22/grouped_representation.py)、[`grouped_update.py`](../../../src/skill_evolution/v22/grouped_update.py)、[`continual_state.py`](../../../src/skill_evolution/v22/continual_state.py)。
