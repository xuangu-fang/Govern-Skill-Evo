# V22 统一 D/S/C：通用性复核与最小必要优化

对应 [统一设计][design]、[v1 实现][implementation]、[七次模型验证][validation]。本次只做源码／归档复核、最小实现和离线验证；**实验模型调用 0 次，新增 ALFWorld episode 0 次，正式 Skill／Memory 发布 0 次**。独立证据保存在 [10 复核目录][archive]。

## 1. 结论与取舍

**本次保留 v1 的五模块行为规则，只修正跨轮历史引用身份，并用 `v22.unified_dsc.v2` 标识新的消费语义。** 现有机制已经具备原始条件化 Update、响应驱动 D/S/C 决定、忠实落实和条件化认识修订的规则及必要信息通路。七次探针显示模型没有稳定遵循这些规则，但不足以证明还缺少另一套通用决策规则。

真正需要修改的是：模型把消费视图中的临时 `H1::` 等标签写进持久化认识后，程序没有保存该标签在**生成时**对应的历史 context。之后 Effect 替换或排序改变可能使同一标签指向另一轮执行。这会改变 Fusion 实际读到的“什么更新在什么条件下产生什么响应”，属于来源正确性问题，能够用轻量程序修正。

完整 V22 离线回归 **358 项通过**，其中新增 13 项。旧 profile 的消息可原样重建，旧实验材料未改。本次没有证明 Editor 漂移、范围误判或行为机会混淆已经消失，也没有证明 Skill 成功率提高。

## 2. 从统一算法判断必要性

审查对象仍是同一条关系：

```text
原始 Update → 历史响应条件比较 → 有效 Update → 实际 Skill diff
           → 当前行为机会／实际行动／结果 → 条件化 Effect → 下一轮 Update
```

来源身份的作用是维持这条关系中的证据指向，不替模型决定历史适用性。共同决策组继续帮助组织可比较问题；同组不是适用证明，跨组不是迁移禁令。

| 复核问题 | 现有机制与真实验证依据 | 分类和本次决定 |
|---|---|---|
| Diagnosis 混合 Goal 与策略，提出能力不可支持或范围过宽的更新 | [规则 30–42][diagnosis-rules] 已区分目标与可替换策略、可见条件、实际能力，并用 Watch 容纳未证实收益；09 §3 有违反规则的真实输出 | **已有原则未充分遵循。** 不新增动作专用禁令，不把效果未知升级为阻断 |
| Fusion 历史贡献不清、范围推广过强，是否应强制改向／引用／Keep | [规则 58–96][fusion-rules] 已覆盖合理 Keep、D 替代、S 双向调整、C 协调、当前证据修正与有界探索；09 §4.2 有具体 S/C 响应利用，§4.3 同初稿无历史也产生相近决定 | **有能力也有遵循及归因不确定性。** 不强制非恒等变换，不要求历史必须提供新增贡献 |
| Editor 将未选定的恢复分支补成义务 | [规则 115–135][editor-rules] 已要求保持方向、条件、强度、依赖及例外，并禁止独立重规划；09 §5 的有效 Plan 与 Candidate 可直接对比 | **落实规则存在，单次输出偏离。** 不叠加同义约束，也不新增自动语义审核／拒绝阶段 |
| Replay／Memory 混用两条路径的机会，将未验证条件写成事实 | [规则 148–178][learning-rules] 已提供机会、行动、结果及路径变化的比较；输入具有配对轨迹、实际 diff、Editor 和有效 Plan；09 §6.1 仍有错误 | **语义归纳失误，未发现缺少通用输入。** 不制造逐任务机会矩阵或逐编辑因果归因 |
| 复合限制可能过度退役 | [规则 182–210][revision-rules] 已允许扩大、限定或推翻认识，要求部分反证保留未测残余；09 §6.2 没有重演旧错误，但也没有充分测试同一复合条目的部分退役 | **已有能力，验证覆盖有限。** 保留自然语言 claim／limits 及现有退休接口，不拆成原子状态体系 |
| 持久化认识中的 `Hn::` 随下一次装配变义 | v1 虽要求持久化避免临时标签，09 实际学习仍写入；[归档重排复现][compatibility] 能确定性改变其指向 | **程序来源关联缺口。实施修正。** 保存生成时的身份，再按消费时命名空间投影 |
| 一次 Fusion 输出 JSON 无效 | 09 §4.4 为 HTTP 200、正常结束、非截断的无效 JSON；结果被保留且未进入 Compiler | **单次格式失败。** 不新增重试、修复调用或输出 Schema；不将其解释为方向失效 |

这里的“不修改”不等于问题无害。它表示当前证据不足以支持新增机制的净收益。尤其不能因为模型一次没遵循已有条件约束，就让 Diagnosis 更容易放弃、Fusion 更倾向 Keep、Editor 更频繁返回 needs_revision。

也不扩张已有 [Findings 来源展开][source-closure]：只沿显式 Watch、requirement 和 basis 关联。仅指向旧 Effect 的观察，不能自动关联当前所有编辑；这种补全会制造不存在的更新归因。

## 3. 实际修改及其算法作用

### 3.1 学习时保存引用的生成身份

新增 [memory_identity.py][identity-code]。在 v2 应用合法学习输出时，从 `claim / limits / finding.observation / retire_limits.reason` 中收集显式 `Hn::` 标签，查询本次实际消费视图的 `historical_contexts`，保存：

```text
Effect.basis.actual_update.reference_contexts
    生成时 Hn → 原有稳定 context_id
```

同一学习调用使用同一张映射，写入该调用新增的 basis，随现有 basis 继承。只存实际提及且能够解析的标签；原始模型输出、claim、limits、finding 和 retirement reason 不改写。没有要求模型输出新字段。

claim 和每条继承 limit 已有各自生成 context；新映射利用这些身份区分“旧限制的文字”和“本轮新解释的文字”。这使部分退役、继承以及多轮合并后仍能解释各自的历史引用。保存 finding／reason 所需的映射也便于归档复核；它们并未重新成为 active 消费视图中的事实。

代码入口：[apply_effective_memory][memory-apply]。该改动影响的是后续响应学习和 Fusion 的证据来源，不增加 D/S/C 决策类别。

### 3.2 消费时重新投影，不猜测缺失来源

[effective_consumption_payload][memory-view] 按文字的生成 context 找到上述映射，再将稳定 context 投影为本次视图的 `H1/H2/...`。之后才执行原有裸 `P/C` 等引用限定，避免把跨轮引用当成本轮来源。重映射一次完成，避免 H1→H2→H1 的级联替换。

- 旧 Memory 没有生成映射、引用标签未知或目标 context 不在本次视图时，显式引用投影为已有的 `history_unknown::`，不按当前序号或 basis 排列猜测。
- unknown 不导致学习或整个 Update 自动拒绝，仍可依据当前证据和其他可解析历史继续更新。
- 同一生成 context 出现相互冲突的程序映射才拒绝装配，避免静默采用错误身份；这不是对一般行为不确定性的新增阻断。
- 只处理认识文字中的显式历史标签；真实 Skill、diff、动作及观察里的同名文字不作为待改写引用。原始来源快照不改写。
- 程序映射从模型消费视图中移除，模型仍使用已有 `historical_contexts / historical_sources / historical_updates`，不需要理解第二套命名规则。

**能力边界：**映射能固定作者所用标签对应哪份历史，不能证明作者正确描述了那次执行，也不能修复混用行为机会、遗漏条件或不当归因。它不解析任意自然语言中的隐含引用。

### 3.3 显式 profile 与运行身份

[grouped_update.py][profile-code] 接入 `v22.unified_dsc.v2`，复用 v1 所有五模块规则、输出形状、Compiler 和 Editor 路由；System 只替换 profile 行。[runtime][runtime-code] 冻结 `v22.unified_dsc_view.v2`，[verifier][verify-code] 核对 profile 与消费视图身份一致。

以后独立新配置可选择：

```json
{"update_profile": "v22.unified_dsc.v2"}
```

本次没有改历史配置、缺省 profile、任务清单、调用预算、运行器主流程或 Gate。`v22.grouped_update.v1` 与 `v22.unified_dsc.v1` 保持原有消息和应用行为；v2 可读取旧 Memory，但无法仅凭旧持久化文本恢复遗失的 H 标签生成关系，因此只对这些无法绑定的引用保留来源未知。

这不是五个模块分别增加机制：Diagnosis 原始 Update 与 Editor 落实方式未变，改动集中在 **Memory 写入 → 后续 Fusion／Editor／学习消费** 的共同来源通路。

## 4. 真实归档复现与兼容性证据

[只读重建脚本][compat-script] 使用 09 `learning_real` 的原始匹配输入、原始响应和 validation-only staged Memory，未生成任何新模型结果或执行轨迹：

1. 原始视图中 H1 是 R1，H2 是 09 学习 context。新 claim 同时提到当前 C7 与历史 `H1::C7`，两者对应不同执行。
2. 仅将四条 Effect 重排为索引 `[2, 0, 1, 3]`，v1 的 H1 变为 09 context，H2 变为 R1；claim 的 `H1::C7` 字面不变，因而指向错误历史。这是**基于真实产物的确定性反例**，不是声称正式第三轮已经发生误读。
3. v2 直接读取这份没有映射的旧 staged Memory，将该引用标为 `history_unknown::C7`，不编造丢失关系。
4. 将同一归档响应通过 v2 纯函数重新应用，保存原输入中 H1→R1 的映射后，再作相同重排，消费文字正确变为 `H2::C7`，而持久化原文未变。这只是身份修正验证，不是 v2 模型学习成功，更没有重新发布 Memory。

结果见 [compatibility.json][compatibility]：

| 检查 | 结果 |
|---|---|
| 08 旧 grouped profile 消息重建 | 10 份 messages 对象及各条消息文本完全相同，包括恢复阶段 |
| 09 unified v1 消息重建 | 7 份完全相同 |
| 两种旧 profile 的冻结 System 模板 | 与修改前快照相同 |
| 五模块规则文件、输出 Schema、旧输入／结果／报告／配置 | 基线哈希未变 |
| 1,263 个修改前文件核对 | 仅 4 个预定源码文件变化：effective_memory、grouped_update、continual_runtime、continual_verify；其余不变 |

另新增 identity 模块、两个测试文件、本报告和独立复核档案。没有覆盖先前三份设计／实施／验证报告。

## 5. 离线验证与成本

完整命令与 [日志][test-log]：

```sh
/Users/didi/miniforge3/envs/alfworld/bin/python -m unittest discover -s tests/skill_evolution/v22 -t . -q
```

结果：**358 tests，61.806 秒，OK**；修改前基线为 345 项通过。新增测试均使用合成数据或预先编写的输出，不调用实验模型和环境。

| 新增测试 | 内容与证明边界 |
|---|---|
| [7 项来源测试][identity-tests] | 两／三 context 重排、各 limit 生成身份、部分退役、finding／reason 共用映射、未知来源可继续学习、冲突拒绝、无级联改名、原始证据与输入不变、元数据不进入模型视图 |
| [6 项作用链测试][flow-tests] | Keep／有界探索可生成 Candidate；预设 D 替代、S 扩大／收窄、C 联合协调可编译落实；未触发／未执行可留 Open；预设部分修订可扩大认识并保留残余；v1/v2 System 除身份相同；两轮合成主线及 verifier 通过 |

两轮合成主线保持 **9 次语义回调**：2 分类、2 Diagnosis、1 Fusion、2 Editor、2 学习；空历史仍为程序恒等。40 条执行记录由测试回调合成，**不是 ALFWorld episode**。有效要求、Watch、Editor、diff、Effect 和下一轮历史视图的关联均被检查。

上述测试证明结构能够传递这些决定；例如预先写出的“残余未测”文本通过测试，不代表程序能够判断任意模型文本是否完整保留了残余，也不代表模型会自行正确决定扩大尺度。

成本与进化能力影响：

- 无额外模型调用、重试、审查 Agent、模型输出字段或新停止路径；未追加行为 Prompt。合法 Keep 仍传递非空 Update，探索仍可形成 Candidate。
- 在 09 真实学习输入的离线装配比较中，v1/v2 消息均为 **335,703 个 Unicode 字符**。这是字符统计，不是新 Token 账单，也不保证任意输入 Token 完全相同。
- 同一归档响应的紧凑 JSON Memory 存储增加 **285 字节**。实际增量随所引用 context 和 basis 数量变化；映射不进入模型输入。学习应用时增加一次只读消费视图构造及短标签解析，没有外部服务成本。
- 旧无映射引用变成较长的 `history_unknown::`，可能略增输入长度，也可能让模型降低对该局部历史的信赖。这是显式表达来源缺失，不是把整条认识判无效；不会由程序强制 Keep 或拒绝 Candidate。实际模型是否过度谨慎仍待观察。

## 6. 进入新流式实验的判断

**已具备进入另行冻结的小规模、新 Train 流式研究实验的基本机制与程序条件；不等于已通过端到端模型语义可靠性验证，更不等于可宣称预条件化提高成功率。**

09 报告曾基于语义反例建议暂停直接转入正式新实验。本次重新按“是否缺少必要机制、修补是否值得代价”判断：身份缺口已修正，其余反例有对应现行规则和输入，尚不足以据此新增强制门槛。继续把零语义错误当作实验前置条件，会推动针对旧探针反复调 Prompt；本次不这样做。这个判断变化来自证据分类和实验门槛的重新评估，**不是这些模型错误已经被修好**。

后续仍需真实模型／新环境证据回答：

- 同一 Update 的目标、策略和可见条件能否跨 Diagnosis、Fusion、Editor 保持一致；已有的落实漂移与不当范围推广发生多频繁。
- 历史响应是否具体改变合理的 D/S/C 决定，包含有依据的 Keep 和扩大尺度；不能用引用数量或非恒等比例代替这一判断。
- 路径改变后的机会、实际行动、任务结果和未测范围是否被正确学习；联合响应有价值，但不应伪装为单项因果收益。
- v2 的来源未知提示是否影响探索能力，合法 Candidate 产生率、无必要阻断、Token 和无效输出情况如何。
- 新任务上的收益、退化、稳定性，以及随后无历史对照的差异；旧 7/10→8/10 和本次离线通过不能替代这些证据。

新实验仍需要独立确定新任务、起始 Skill／Memory、请求预算及失败处理并冻结配置。现有 loader 仍沿用既有两轮协议，本次未扩大实验范围。这属于实验准备，不是已确认的 D/S/C 通用算法缺口。本次到代码、离线验证和报告为止，不启动实验，也不自动进入下一轮 Prompt 优化。

[design]: /Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_UPDATE_DESIGN.md
[implementation]: /Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_IMPLEMENTATION.md
[validation]: /Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_MODEL_VALIDATION.md
[archive]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/10_unified_dsc_refinement_20261015
[diagnosis-rules]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/unified_dsc.py:30
[fusion-rules]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/unified_dsc.py:58
[editor-rules]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/unified_dsc.py:115
[learning-rules]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/unified_dsc.py:148
[revision-rules]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/unified_dsc.py:182
[source-closure]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/compact_learning.py:126
[identity-code]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/memory_identity.py:17
[memory-apply]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/effective_memory.py:183
[memory-view]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/effective_memory.py:49
[profile-code]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/grouped_update.py:48
[runtime-code]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/continual_runtime.py:236
[verify-code]: /Users/didi/Desktop/Govern-Skill-Evo/src/skill_evolution/v22/continual_verify.py:268
[compat-script]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/10_unified_dsc_refinement_20261015/check_compatibility.py
[compatibility]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/10_unified_dsc_refinement_20261015/compatibility.json
[test-log]: /Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v22/10_unified_dsc_refinement_20261015/regression.log
[identity-tests]: /Users/didi/Desktop/Govern-Skill-Evo/tests/skill_evolution/v22/test_memory_identity.py
[flow-tests]: /Users/didi/Desktop/Govern-Skill-Evo/tests/skill_evolution/v22/test_dsc_refinement_flow.py
