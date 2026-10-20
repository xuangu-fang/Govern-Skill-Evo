# V22 统一 D/S/C 五模块契约一致性检查与最小通用修复

2026-10-16。**已完成检查、必要修复与离线验证；没有调用实验模型 API、执行 ALFWorld episode 或恢复实验。**

本次确认四项 A/B 缺口：group 证据集合的模型／程序契约不一致，Fusion 少量合法操作语法未完整表达，Memory 示例的 replace／retire_limits 组合矛盾，以及历史别名在标点冒号前漏加来源限定。前三项对齐已有契约；最后一项修复确定性的来源传递。没有重设计 D/S/C、改变 Gate 或新增审核机制。

新身份为 **`v22.unified_dsc.v3`**，消费视图为 `v22.unified_dsc_view.v3`。修复只存在于[独立 revision 目录][revision]；原工作区源码、冻结 Prompt 和历史实验保持原样。检查点已满足上游材料复用的身份条件，但继续运行仍需另行授权，并建立新的 v3 续行冻结记录。

## 1. 检查材料与证据边界

阅读并对照了 [机制审查][audit]、[统一设计][design]、[最小实现][implementation]、[七次模型验证][validation]、[v2 优化][refinement]，再检查实际源码、输入装配、完整消息、原始响应、验证器及运行器。

[兼容性证据][compat]逐项列出 **21 份归档完整 messages** 的路径、对应 call 中的 `steps[0].messages`，或 09 的 `request.json.messages` 与 call 请求哈希：08 的 10 份阶段记录（包括恢复记录）、09 的 7 份探针、11 两次 Diagnosis 和两份分类记录。恢复过程包含复用消息，21 不代表 21 次独立调用。所有完整消息用修订代码按其原 profile 重建一致；本次不是只搜索 Prompt 模板。

Replay／Memory 全输入还核对了 08 R1、08 R2 恢复学习和 09 `learning_real`：各含 20 个不同 run_id、10 对 Parent/Candidate、实际 Plan、diff、映射及来源；11 尚无 Candidate 或学习输出，不能据其 Diagnosis 停点评价学习是否成功。

以下区分：**A** 已确认契约不一致；**B** 已确认信息或程序交接缺口；**C** 规则和输入已具备但模型判断错误；**D** 任务表现或证据不足。程序检查通过不等于行为语义正确。

## 2. 五模块检查总览

| 模块 | Prompt／输入／输出／程序核对 | 结论与处理 |
|---|---|---|
| Diagnosis | 实际消息包含 Parent、完整执行证据、冻结组映射、能力和基础执行协议；Plan 使用 intent / requirements / watch / open。严格组校验要求集合相等，旧提示只要求“group sources AND Parent events”，形状示例只有事件。 | **A，修复**来源契约。Goal／Update／Watch／Open 概念与原字段兼容，不迁移 Schema。能力边界已有，无需新增任务规则。 |
| Fusion／Compiler | 输入包含同一冻结 Plan、实际 Parent 和历史响应；已有 Keep、replace、withdraw、hold、Watch 迁移及空有效更新出口。增量 `changes.from` 必须非空，`watch_changes.from` 可空，Open 有精确引用范围。 | **A，修复**两类 from 的表达及缺失的 Open 对象语法；**B，补齐**编译后新增事件的来源组。D/S/C 决策原则与操作种类不变。 |
| Editor | 完整有效 Plan、实际 Parent、能力、基础协议及当前证据均进入消息。candidate/no_change/needs_revision 的映射、文本位置、问题与 Watch 约束与验证器对应。 | 未确认独立 A/B 缺口。保持既有方向、条件、强度、关联与例外规则；自然语言语义偏离归 **C**。 |
| Replay | P/C 别名、run_id、skill_id、pairs、逐步动作／观察、command_sets、current_run_facts 明确区分执行侧。Findings 可引用当前事件，about/Watch 可追溯到有效 Update。 | 当前执行侧信息无确认缺口；09 的路径混淆属 **C**。历史投影的别名遗漏属下述跨模块 **B**，一起修复。 |
| Memory | 实际编辑上下文、响应来源、历史身份及条件限制均可保存；replace 与整条 limit 索引退役对应；v2 保存生成时 Hn 映射。 | **A，修复**示例组合；**B，修复**标点边界别名限定。保留 v2 的稳定生成身份与整句残余规则，不增加原子限制状态。 |

能力核对依据：[COMMON][common]明确 Actor 只有当前观察、合法动作和最近两对观察／动作，没有全局 visited、持久笔记或完整历史；[实际输入装配][diagnosis-input]传入 capabilities、base_protocol、runs、command_sets。已有规则要求可见条件与可执行动作。提出不可用控制、把未知条件当成已知等结果，不能据此自动认定执行器缺少新能力。

## 3. 确认缺口与最小修复

### 3.1 A：group 来源集合与模型可见契约不一致

实际 Schema **没有 `basis.groups` 字段**；`requirements[].basis` 是扁平来源列表。原 [validate_grouped_plan][old-group-check] 要求：

`basis 中的当前组集合 == basis 所引当前 Parent 事件对应的组集合`，且集合非空。

因此 group 的程序含义是**完整证据来源坐标**，并不承担 Update 的主要适用组或行为适用范围。其依据来自冻结事件—任务—组映射，而适用范围仍由 requirement.text 的条件和语义表达。

[11 第一次失败][diag1]中 u2 引用的事件来自 G1/G2/G3，却只写 G3；[第二次失败][diag2]中四项要求都只有事件。两次均为完整合法 JSON。其实际 System 没写集合相等规则，共用 Plan 示例的 basis 又只有 `P1:4`。这既不能归结为网络中断，也不能只归结为模型没有遵守一个已完整表达的规则。

选择确定性补全而非要求模型再计算集合：[v3 规则][aligned-rules]说明引用真实 Parent 事件、程序补齐其来源组，显式组必须有同一 basis 中的事件支持；[程序][new-group-check]只在 v3 的 Diagnosis 接受和 ready Fusion 编译路径中启用补全。

具体边界：

- 先检查已有引用、冻结映射和 Parent 事件；仅向 basis 加入可确定的缺失组，顺序稳定。
- 不删事件，不移除无依据的显式组，不改 Goal、策略、条件、Watch 或 Open。无事件、未知来源、不存在的事件、无事件支持的显式组仍拒绝。
- 补全之后继续满足原集合相等条件；旧 profile 不补全，维持原拒绝结果。
- 原模型 JSON 保存在 raw_outputs；接受后的 Plan 单独归档。既有 runner/verifier 已支持这种 raw／accepted 区分，无需增加字段或语义调用。
- Fusion 合并原 basis 与 change.basis 后也补全，避免只修 Diagnosis、却在新的跨组当前证据上再次失败。[两个入口][new-routing]

离线重放两份失败输出：第一次仅为 u2 加 G1/G2；第二次依次补 G1、G1/G2/G3、G2、G1，均通过 v3。其他内容逐值未变。**这仅证实来源缺口可机械消除，不认证更新策略；没有将旧失败输出升级为正式 Plan。**

### 3.2 A：Fusion 合法操作语法表达不全

[旧规则][old-fusion]末尾使用泛称 `from=[] adds a question`，但[Compiler][compiler]只允许 `watch_changes.from=[]`；`changes.from` 必须非空。实际 Fusion 输出形状只给 `open:[]`，08/09 输入 Plan.open 也为空，完整消息没有给新增 Open 项的 `{about, reason}` 结构，而 [_open][open-check]要求其 about 引用有效 requirement、Watch 或 intent。

v3 替换原操作段，明确两条路径以及 Open 结构／引用范围，说明撤回后保留目标观察应使用 `about:["intent"]`。未增加操作标签或放宽 Compiler。已有 Keep、D 替代、S 扩大／收窄、C 联合调整、withdraw／hold 和有界探索继续合法。08 失败 Fusion 的任意新增要求及错误嵌套字段仍不会通过；本次不是以历史错误全部通过为目标。

### 3.3 A：Memory append 示例与 retirement 验证冲突

[旧 EFFECTIVE_SHAPE][old-memory-shape]继承 `replace:[]`，却附带非空 retire_limits；[验证器][retire-check]要求 retirement.effect_id 同时属于本 delta.replace。v3 把该 append 示例改为 `retire_limits:[]`，完整的替换／退役字段继续由已有学习规则说明。模型输出字段集合、应用粒度、正常替换能力均未改变。

形状包含枚举选项和示意引用，本来不是可直接提交的固定数据。本次测试解析**实际装配消息**中的各阶段示例，把枚举和来源占位符落到通用合成输入，再送入验证器；没有为示例额外修改业务语义。

### 3.4 B：历史别名在标点冒号前漏加命名空间

真实 08 m3 被 09 消费时包含 `C4 and C5: C4 stayed ...`。v2 投影得到 `H1::C4 and C5: H1::C4 stayed ...`，留下裸 C5；规则却把裸 P/C 别名保留给当前执行。原因是 [_rewrite][old-rewrite] 的结束边界 `(?![\w:])` 把标点冒号也排除了。该缺口会影响 Fusion 对历史条件的判断，不能仅算模型引用失误。

v3 在[消费投影][new-rewrite]中，仅对**已知来源别名及由已有事件键确定的运行别名**补全标点边界；完整事件 `C5:4`、已有 `H1::`、未知别名和命名空间后缀不混改。v1/v2 默认行为原样保留。[新路由][new-memory]将此开关同时用于初始历史投影及最终 claim/limit 投影，并继续保存 v2 的生成时映射。

真实材料复核得到 `H1::C4 and H1::C5:`；原 Memory、事件快照、当前 runs/pairs 均未改。[compat.historical_alias_counterexample][compat]保留 Effect ID、原文、前后投影和哈希。这里没有生成新的行为认识，只消除了来源歧义。

## 4. 不修改的事项与原因

| 问题 | 类型 | 证据及决定 |
|---|---|---|
| Editor 把未知分支强化为强制验证 | C | 09 [有效 Plan][editor-plan]只选择特定条件，[模型输出][editor-output]自行强化；实际规则已要求保持策略、触发条件、义务强度、例外并禁止独立策略选择。[Editor 规则][editor-rules]保留。文本 excerpt 校验不等于语义等价，不新增审核 Agent。 |
| Replay 把 Parent 机会说成 Candidate 机会 | C | 09 learning_real 的 P6/C6 有不同 run_id/skill_id 和配对轨迹；完整输入与[学习规则][learning-rules]已经要求分别核对机会、行动、结果。不添加逐任务机会矩阵。 |
| 将不同条件下的成功合并成更宽结论 | C | 09 的 C8/C10 解释超出各自执行条件，真实来源可区分，规则已有条件边界要求。不将它变成对象或动作专用规则。 |
| 复合限制被整体退役 | C/D | 08 曾出现的问题，在现行规则中已有“整句退役时重述未测试／仍成立残余”。[学习规则][limits-rules]与[应用逻辑][apply-memory]同为整条字符串粒度；可自然表达“已验证部分改变，未验证部分保留”。09 没有充分覆盖同一分支，不引入原子限制状态。 |
| 没有历史非恒等变换或当前证据独立修正 | 非缺陷 | 现行 Fusion 明确允许 Keep、有限历史和当前能力修正；没有历史增量依据时应如实区分，不强制引用或变换。 |
| unavailable control、长期状态假设、个别执行不佳 | C/D | 实际能力边界已给出，单次输出违规不能证明需要扩展 Actor 或增加拦截器。本次保留观察。 |

通过项也有实质依据：[来源闭包][response-sources]把 Findings→Watch→requirements→intent／当前构造来源相连；[学习装配][learning-binding]绑定有效 Plan、真实 Editor 映射、Candidate 文本、实际 diff、配对执行和 Gate；[稳定身份][stable-identity]依据 claim/limit 的生成上下文重投影 Hn。此次未发现必须另建一套 D/S/C 字段或逐编辑因果归因机制的证据。

## 5. 版本、变更范围与复杂度

为使当前 11 的原 `check_runtime` 继续通过，没有在原 src 上直接改动。独立 revision 初始复制 1,063 个源码／测试／配置文件；benchmark 用指向原目录的软链接，仅只读使用，保留 manifest.resolve() 身份；没有复制凭据。

实际代码差异只有：

| 文件（均在 revision） | 改动作用 |
|---|---|
| contract_alignment.py（新增） | v3 身份、替换后的来源／Fusion 契约文字、合法 append 示例。 |
| grouped_representation.py | 可选确定性补齐来源组；默认保持旧验证。 |
| grouped_update.py | v3 opt-in，Diagnosis／编译后补齐，按 profile 装配规则。 |
| compact_learning_view.py | 可选修正已知历史别名的标点边界。 |
| effective_memory.py | v3 投影及稳定生成身份路由，独立 view 版本。 |
| continual_runtime.py | 允许明确选择 v3 的原流式协议；旧计划不自动升级。 |

另新增 3 个通用测试文件。**没有新增模型输出字段、调用、独立 Agent、复杂状态或语义门禁；没有改 Actor、Gate、任务、主流程和旧 profile 的消息。** 补齐 provenance 不推断适用性，也不增加保守阻断；无依据的显式引用仍需拒绝。

相同 09 归档输入分别按 v2/v3 离线装配，完整消息序列化字符变化如下。这里包含 JSON 转义，不是实际 Token 计费或新模型结果。

| 阶段 | v2 字符 | v3 字符 | 增量 |
|---|---:|---:|---:|
| Diagnosis | 172,086 | 172,518 | +432 |
| Fusion | 219,628 | 220,383 | +755 |
| Editor | 24,274 | 24,706 | +432 |
| Replay／Memory | 369,114 | 369,373 | +259 |

11 同一 Diagnosis 为 120,552→120,984 字符。新增成本主要是契约表达；没有额外推理轮次。真实 Token、遵从性、是否影响更新积极性仍须后续模型验证，不能由字符数推断。

## 6. 离线验证与历史兼容

最终结果：**V22 397 项通过，ALFWorld Adapter 35 项通过**。V22 当前基线已经包含流式准备等测试，共 376 项；本次新增 21 项，因此不是在早先 358 项上只增加 21 项。[完整日志][tests-final]、[Adapter 日志][adapter-tests]

新增测试覆盖：单组／联合／跨组来源，补齐幂等及原输出不变，未知／无事件／无依据显式组仍拒绝，旧 profile 拒绝行为，Fusion 引入跨组事件，实际消息的 Diagnosis／Fusion／Editor／Memory 示例，Keep／有界探索，D 替代、S 双向调整、C 协调，撤回与 Watch 迁移，未触发／未执行可以保留未知，部分认识修订可扩大支持范围并保留残余，历史 Hn 重排与标点边界，以及两轮**合成回调**的 raw→accepted→Editor→diff→Findings→Effect→下一轮链条及 verifier。

合成回调不是模型调用或环境 episode。它只能验证表达能力、来源及程序交接，不能证明模型会正确选择策略、忠实编辑、正确归因或提高成功率。

历史检查结果：2,040 个原文件哈希全部未变；21 份旧完整消息重建一致；3 份 11 runtime freeze 仍通过；9 个 Actor Python 文件、git HEAD 和 benchmark 实路径一致；旧 08/09/11 产物没有覆盖。[复核脚本][compat-script]、[冻结与差异记录][freeze]

离线重现命令（必须在 revision 目录）：

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python -m unittest discover -s tests/skill_evolution/v22 -t . -q
/Users/didi/miniforge3/envs/alfworld/bin/python -m unittest discover -s tests/adapters/alfworld -t . -q
```

## 7. 独立续行方案：仍未执行

[续行提案][continuation]记录新旧边界和预算，**不是执行授权，也不是已冻结的 live recovery wrapper**。

可复用八条 Parent、原分类完整输入／输出及冻结分组。逐条轨迹和原始响应核验通过，v3 不改变 Actor、分类 Prompt、分类输入或 bindings；Diagnosis 的证据输入仅 profile 身份变化。原 round 为 `campaign-290ad7cd3967e387:r1`，state SHA 为 `4b424dafa58a366100873df6e4fcf1d70315f7c3578bd9dd8f9b70d3e08c7d85`。

授权后的顺序应为：

1. 在独立续行档案中记录原 checkpoint、拷贝哈希、两次失败成本与 v2→v3 边界；保持原 round/state 和事件身份，按 v3 重新冻结源码、配置和完整消息。
2. 八条完整 Parent 与一次有效分类不重跑。**重新调用 Diagnosis**，不把本次离线补齐的旧失败输出当作新 profile 正式结果。
3. 第一轮空 Memory 仍走程序恒等；随后 Editor、Candidate Replay、Gate、学习和共同发布。第二轮读取实际已发布状态，保留严格 Gate 和原任务。
4. 原技术失败处理不变，无效输出不冒充 Keep/RETAIN；再需恢复时保留失败并报告新增预算，不自动重试。

| 未来新增上限（需另行授权） | 数量 |
|---|---:|
| Pro | 8：R1 Diagnosis/Editor/学习 3；R2 分类/Diagnosis/Fusion/Editor/学习 5 |
| episode | 24：R1 Candidate 8，R2 Parent/Candidate 各 8 |
| Actor 逻辑请求 | 1,200，50 步／episode、并行最多 8 |
| HTTP 尝试 | 7,208，Actor 原传输策略最多 6；Pro 单次 |
| Pro 输出预算总和 | 327,680，普通阶段 32,768，学习 65,536 |

模型、temperature、thinking/reasoning、timeout、Actor 输出上限等沿用原冻结配置；不因本次改契约追加语义重试。合法无更新时实际调用可以更少。

两次失败 Diagnosis 已知合计：输入 **71,936**、输出 **17,729**、总 **89,665 Token**；reasoning **16,402** 为输出子集。货币费用因代理费率未知而不估造。包括中断及其他调用的全程已知累计仍为输入 193,983、输出 117,910、总 311,893；三次原在途 Actor 请求消耗未知，不能计零。[既有恢复报告][recovery-report]

**首轮 Parent 为 8/8，因此严格成功数改善 Gate 下该轮 Candidate 不可能 ACCEPT。** 这不要求修改任务或 Gate，也不阻止 RETAIN 学到局部响应；第二轮应继承实际发布的 No Skill 与有效 Memory（若有），不能假称继承了已接受 Candidate。若合法无更新导致没有新 Effect，则也应如实保留空历史，不制造历史预条件化。

结论：已识别的确定性契约缺口已处理，具备在新协议边界下复用检查点、另行授权续行的基本条件。剩余的 Editor 语义忠实性、Replay 条件归纳、合理探索及历史响应对 D/S/C 的真实作用，是后续实验需观察的不确定性；本次没有证据支持继续叠加机制，也没有证明 Skill 成功率或预条件化收益提高。

[revision]: /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/12_contract_alignment/revision
[audit]: /Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/DSC_MECHANISM_AUDIT.md
[design]: /Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_UPDATE_DESIGN.md
[implementation]: /Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_IMPLEMENTATION.md
[validation]: /Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_MODEL_VALIDATION.md
[refinement]: /Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_REFINEMENT.md
[compat]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/12_contract_alignment_20261016/compatibility_checkpoint.json
[compat-script]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/12_contract_alignment_20261016/verify_compatibility_checkpoint.py
[common]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/compact_update.py:35
[diagnosis-input]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/compact_cycle.py:97
[old-group-check]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/grouped_representation.py:188
[diag1]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_recovery1_live_20261016/rounds/r1/raw_outputs/diagnosis.json
[diag2]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/11_unified_dsc_stream_recovery2_live_20261016/rounds/r1/raw_outputs/diagnosis.json
[aligned-rules]: /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/12_contract_alignment/revision/src/skill_evolution/v22/contract_alignment.py:17
[new-group-check]: /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/12_contract_alignment/revision/src/skill_evolution/v22/grouped_representation.py:188
[new-routing]: /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/12_contract_alignment/revision/src/skill_evolution/v22/grouped_update.py:80
[old-fusion]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/unified_dsc.py:98
[compiler]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/compact_update.py:214
[open-check]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/compact_update.py:177
[old-memory-shape]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/effective_memory.py:23
[retire-check]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/effective_memory.py:167
[old-rewrite]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/compact_learning_view.py:44
[new-rewrite]: /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/12_contract_alignment/revision/src/skill_evolution/v22/compact_learning_view.py:44
[new-memory]: /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/12_contract_alignment/revision/src/skill_evolution/v22/effective_memory.py:63
[editor-plan]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/cases/editor_frozen/realization.json
[editor-output]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/09_unified_dsc_model_validation_20261015/cases/editor_frozen/parsed.json
[editor-rules]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/unified_dsc.py:115
[learning-rules]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/unified_dsc.py:148
[limits-rules]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/unified_dsc.py:198
[apply-memory]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/effective_memory.py:199
[response-sources]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/compact_learning.py:126
[learning-binding]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/grouped_update.py:215
[stable-identity]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/memory_identity.py:17
[tests-final]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/12_contract_alignment_20261016/v22_tests_final.log
[adapter-tests]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/12_contract_alignment_20261016/adapter_tests.log
[freeze]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/12_contract_alignment_20261016/revision_freeze.json
[continuation]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/12_contract_alignment_20261016/continuation_proposal.json
[recovery-report]: /Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_STREAM_RECOVERY2_RESULTS.md
