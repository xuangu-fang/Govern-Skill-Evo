# V22 统一 D/S/C 最小实现与离线验证

日期：2026-10-15。对应 [第一步设计](/Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_UPDATE_DESIGN.md)。

本次实现让同一 Update 的构造、变换、落实和响应认识在现有主线上接通。新规则使用 `v22.unified_dsc.v1`；保留原 Plan、Fusion 增量、Editor、Findings 和 Effect 输出 Schema，没有增加模型阶段、审阅调用或自动重试。现有历史配置缺省继续使用 `v22.grouped_update.v1`，以保留旧消息和 Memory 的重建结果。

这是代码与离线机制交接的实现，尚未用真实模型验证新规则的遵从性，也未运行新的 ALFWorld 实验。历史两轮结果不作为此次改动的收益证据。

## 1. 五模块如何围绕同一更新协作

协调规则集中在 [unified_dsc.py](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/unified_dsc.py)，替代新 profile 下原有各阶段规则的组合；旧规则保留供历史重建，不叠加到新 Prompt 中。

| 模块 | 实际修改 | 对更新能力的作用 | 保证边界 |
|---|---|---|---|
| Diagnosis | 将 `intent` 定位为目标与共同保留义务；`requirements` 表达相对 Parent 的可替换策略、可见条件、强度和必要依赖；Watch 针对行为机会与关键预期 | Fusion 获得可调整的行为选择，避免把目标和某条策略锁在一起；仍可提出有价值的原始更新 | 沿用现有字段和当前证据；不要求穷尽条件或独立填写 D/S/C |
| Fusion | 将条件化编辑响应映射到保持、D 替代、S 扩大／收窄、C 联合协调；区分历史贡献和当前能力修正 | 具体说明响应差异如何改变当前选择；历史不足时保留原方案或合理探索，Keep 仍进入 Editor | 引用不证明历史贡献；规则是否被模型正确执行仍需后续验证 |
| Editor | 保持所选策略、条件、义务强度、依赖和有效例外；落实映射进入学习输入 | 选定的变换可与实际 Skill 对照；许可强化、例外丢失等作为一般语义偏离处理 | 文本摘录只证明引用存在；程序不证明策略等价，也不替 Editor 重新规划 |
| Replay | 用有效 Update↔实际修改、机会↔行为、预期↔结果三种比较组织同一次学习 | 将未落实、未遇到、未执行与已执行后的响应区别对待；路径变化也可成为观察对象 | 成功不直接证明具体编辑有效，未测不等于无效或保持 |
| Memory | Effect 保留相关有效要求、Watch 和构造依据；规则要求认识只随受支持的范围修订 | 下一轮看到的是实际编辑及其条件化响应，而非脱离更新的任务总结；允许扩展、限定或撤销旧认识 | 联合归因保留；部分反证的残余条件由语义输出维护，未增加原子限制状态或因果分摊 |

分组继续提供共同决策问题及当前事件来源。新规则明确：同组不充分证明适用，不同组不禁止迁移；关联要求联合调整，组外未评估范围保持未知。分类调用、冻结方式和 Gate 均未改变。

## 2. 补齐的 Update 与实际编辑关联

### 2.1 Editor 到 Replay

[prepare_grouped_learning](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/grouped_update.py:206) 在新 profile 下接收已经保存、归一化后的 Editor 输出。程序先核对：

- 映射摘录及 requirement ID 对应实际有效 Plan；Editor 新增 Watch 与执行 Plan 一致。
- Editor 的 Candidate／无 Candidate 路由与实际版本一致，Candidate 文本完全一致。
- `update_context.editor` 保存 `decision / mappings / issues`，并与 Gate、轨迹、Memory 一起进入原有输入哈希绑定。

新增 `sources.editor` 可供 Findings 引用。学习仍以真实 Skill 和 diff 为准，映射是待比较的落实主张。没有重复复制完整 Candidate 文本，没有额外 Editor 审阅调用。Editor 的实质异常也能沿无 Candidate 路径进入学习；效果未知不因此成为阻断。

### 2.2 Findings 到 Effect

[update_response_sources](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/compact_learning.py:126) 对新 profile 做显式来源关联展开：

```text
finding.about / 显式静态 refs
    → 相关 Watch
    → Watch.about 对应的有效 requirements
    → 共同 intent 与 requirements.basis 中的当前来源

Effect.basis.actual_update
    → 实际 Parent/Candidate 身份、比较条件
    → 真实 diff、冻结分组、Gate、Editor 落实映射
```

因此，一条只在 `refs` 引用事件、在 `about` 回应 Watch 的发现，持久化时仍保留它所回应的有效更新文本。多个要求可以共同对应同一 Watch、映射和发现；无关要求不自动复制。

展开只沿已有结构链接，不解析自然语言猜测依赖。`finding.refs` 原样保存，自动附带的构造依据不冒充本次观察证据；历史 Effect ID 也不会被解析为当前执行事件。原始 Plan、Fusion 增量、有效 Plan 和 Editor 输出继续留在冻结轮次档案中，不重复塞入每条 Effect。

### 2.3 Effect 到下一轮 Fusion

[effective_consumption_payload](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/effective_memory.py:38) 为新 profile 提供 `v22.unified_dsc_view.v1`：

- 同一历史 context 的实际更新仅在 `historical_updates[H1]` 展开一次，各 basis 用 `actual_update_ref` 引用。
- 事件、有效要求和 Watch 仍通过 `historical_sources` 及 `H1::` 命名空间访问；当前与历史 ID 分开。
- 同一 diff／Editor 同时作为显式 source 时，消费视图用指向共享更新的路径引用，持久化的原始来源不改写。
- 同一 context 出现冲突实际更新时拒绝装配，不静默选择其中一个。

这些程序改动使新规则有可读取的实际更新依据，并控制关联补齐造成的重复。它们没有把历史成功变成更高置信分数，也没有强制使用某条 Effect。

## 3. 认识修订与合法无更新

复合限制的部分反证仍使用现有 `replace / retire_limits / limits`：若退役的一个自然语言条目含有未被新证据覆盖的部分，必须在新的 active limits 中保留这些残余条件。程序继续存档旧文字、来源和退役理由；不宣称结构校验能证明残余已经语义完整。去掉物体名、具体轨迹后，这一原则仍适用于一般的条件化认识修订。

新 profile 允许 Fusion 合法撤回全部要求，且所有受影响 Watch 仍须有明确去向。Compiler 仍拒绝 ready 带阻断 Open；runner 将完整撤回记为 `no_effective_update`，进入已有无 Candidate 结算路径，跳过 Editor 和 Candidate 执行。有历史时仍可据当前事实修订 Memory，无实际修改就不能制造新编辑效果。

这与 Keep 分开：`changes=[]` 保留非空原始更新并继续 Editor／Replay。格式、网络等技术错误仍不能走上述语义出口。相关接线位于 [Compiler](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/compact_update.py:214)、[runner](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/continual_runner.py:327) 和 [verifier](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/continual_verify.py:211)。

## 4. 版本与调用边界

后续新配置显式设置：

```json
{"update_profile": "v22.unified_dsc.v1"}
```

它是新实验配置的一项选择，不应回写到历史配置。当前 `load_bundle` 仍约束既有两轮协议；新任务选择、实验起点和预算应在下一阶段另行冻结，本次没有创建或启动新实验计划。

[runtime](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/continual_runtime.py:68) 检查 profile，冻结相应 Prompt 和消费视图版本；[verifier](/Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/continual_verify.py:263) 按同一 profile 重建交接和发布结果。缺省或显式旧 profile 保持旧消息、输入元数据及 Memory 应用方式。

模型输出 Schema 常量未改。常规两轮合成主线仍为 4＋5＝9 次语义回调；没有新增阶段。全撤回等已有语义停止路径可以减少调用，不将减少更新次数本身当成改善。

## 5. 离线通用机制验证

新增 [机制测试](/Users/didi/Desktop/Govern-Skill-Evo/tests/skill_evolution/v22/test_unified_dsc_mechanism.py) 和 [主线测试](/Users/didi/Desktop/Govern-Skill-Evo/tests/skill_evolution/v22/test_unified_dsc_runner.py)，分别覆盖 10 项和 8 项验证：

| 通用性质 | 离线验证内容 |
|---|---|
| 保持与探索能力 | Keep 保留原始 Update，仍能落实 Candidate；未触发 Watch 可留学习 Open，不产生负面 Effect |
| D/S/C 表达与编译 | 预设替代策略、S 双向调整、跨组联合要求，保持 Goal、未变要求、来源合并与 Watch 去向 |
| 同一更新的作用链 | 有效要求、实际映射、diff、发现、Effect，以及下一轮 Fusion 消费保持关联 |
| 局部认识修订 | 部分限制退役后保留预设未测试残余；旧证据及各自历史 context 不丢失 |
| 实际落实绑定 | 拒绝映射摘录、Candidate 文本、Editor Watch 或已绑定输入被替换；归一化 no_change 和 needs_revision 正确传递 |
| 去重与版本兼容 | 历史公共更新只展开一次；历史／当前别名分离；旧 profile 兼容；模型输出形状相同；未知 profile 拒绝 |
| 无有效更新 | 全撤回保留观察去向，跳过 Editor／Candidate，保留真实无编辑语义和适用的 Memory 学习 |

这些案例的 Plan、变换和解释均预先给定。它们验证程序能表示、传递和保持这些决定，**不证明模型会自行作出正确 D/S/C 判断**。没有以 Prompt 关键词存在替代语义验证，也没有围绕旧任务成功率调参。

完整离线回归命令：

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python -m unittest discover -s tests/skill_evolution/v22 -t . -q
```

使用已有 Python 环境中的合成回调和临时目录，不加载游戏执行、不调用实验模型 API。最终结果见本文件末尾的交付核对。

## 6. 成本检查与未验证边界

以下是对两轮旧输入的只读内存投影比较：新版本仅增加 profile、已有 Editor 元数据及新的去重视图，没有生成新语义输出或回写 Memory。单位为 Unicode 字符，不是实际 Token 账单。

| 阶段 | 旧 System | 新 System | 旧用户输入 | 新用户输入 |
|---|---:|---:|---:|---:|
| R1 Diagnosis | 4,742 | 4,609 | 160,478 | 160,516 |
| R1 Editor | 4,968 | 4,743 | 166,833 | 166,890 |
| R1 Replay/Memory | 7,214 | 6,785 | 263,628 | 266,133 |
| R2 Diagnosis | 4,742 | 4,609 | 150,867 | 150,905 |
| R2 Fusion | 7,757 | 7,624 | 222,018 | 192,596 |
| R2 Editor | 4,968 | 4,743 | 222,337 | 192,915 |
| R2 Replay/Memory | 7,214 | 6,785 | 356,496 | 328,918 |

新 System 没有因层层追加规则而增长。R1 学习因收到实际映射增加约 2,500 个输入字符；R2 历史公共材料去重抵消了这一开销。此比较使用原正式 Memory，不能预测新版本多轮来源展开后的总长度；真实输出 Token、耗时、稳定性、进化质量和历史贡献仍需下一阶段冻结的新 Train 实验衡量。

本次没有增加独立 Agent、D/S/C 自证字段、逐条件状态机、任务专用规则、Actor 能力或 Gate 约束。尤其没有把“代码链条已接通”写成“历史响应已带来额外收益”。

## 7. 交付核对

- 完整 V22 离线回归：**345 项通过**；新增机制与主线验证共 **18 项**，并在消费引用说明调整后定向复核。
- 两轮历史及恢复记录中，9 份可由旧接口重建的 Diagnosis／Fusion／Editor／学习消息与存档完全一致。
- 本轮基线覆盖 1,156 个文件，其中历史产物、实验配置及既有 V22 文档共 1,079 个，内容均未改变，无文件删除。修改范围为 8 个现有源码文件，新增协调规则、两份测试和本说明。
- 原模型输出 Schema、现有状态与 Gate 契约未改。新输入关联和消费投影通过显式 profile 区分；旧配置没有自动切换。
- 所有执行均为离线读取、纯函数装配和合成回归。未运行新 ALFWorld episode，未调用实验模型 API，也未重新发布 Skill／Memory。
