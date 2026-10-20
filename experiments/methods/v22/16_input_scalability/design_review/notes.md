# 输入消费设计的独立复核

本文件只读复核冻结 `experiments/methods/v22/12_contract_alignment/revision` 的 v3 源码；没有修改正式算法、配置或历史材料，没有调用模型或环境。下述源码位置均相对于该 revision。容量数字由主审计原型另行产生，这里不把推测当作测量。

## 已确认事实

| 阶段/关系 | 当前实现与含义 | 源码 |
|---|---|---|
| 分类 | 全部 Parent 有序动作/观察与完整动作集合；Task 别名与实际运行绑定分开。只除共享协议和动作集合重复，未选事件 | `src/skill_evolution/v22/grouped_representation.py:34-97` |
| Diagnosis | 全 Parent、当前 Skill、真实 base protocol/capabilities、全当前动作集合、所有 Parent 来源；没有 Memory | `compact_cycle.py:92-103`; `grouped_update.py:53-77` |
| Fusion | 当前完整 Diagnosis 输入+冻结 Plan+全部当前有效 Memory；一律展开 effective_consumption_payload | `grouped_update.py:91-102,156-181` |
| Editor | 主线再次使用 update_payload(current,effective)，因此完整 Parent 轨迹与全部有效 Memory 跟随。旧 `compact_cycle.editor_input` 的按 Plan basis 筛 Effect 函数不在该主线路由中 | `continual_runner.py:377-380`; `grouped_update.py:174`; `compact_cycle.py:113-116` |
| Replay/Memory | 全 Parent/Candidate、完整有序行动/观察、成败/状态与配对、完整动作集合、Skill、diff、Plan、分组、Editor 映射、全历史 Memory | `compact_learning.py:22-94`; `grouped_update.py:215-258` |
| 当前冗余 | `sources` 为每一步复写 run+step；组定义/成员/哈希同时出现在 grouping 和 group 来源快照；learning 的实际 diff 在顶层与 update_context 重复，组上下文也重复。run 的状态/身份再次出现在 current_run_facts | `compact_learning.py:72-78`; `grouped_representation.py:165-184`; `grouped_update.py:225-253`; `compact_learning_view.py:22-37` |
| 现有历史去重 | 每个历史 context 内的 source 按别名共享；事件去掉大型动作列表和 fingerprint；旧 Finding 解释不再作为有效事实读取；实际更新在 historical_updates 按 context 共享；重复 diff/editor 来源转 pointer | `compact_learning_view.py:70-134`; `effective_memory.py:53-128` |
| 固定 Effect 数仍增长 | replace 继承旧 basis 和未退役 limits，再加新 basis/limits；只去除完全相同记录。basis 数、limits 数、历史 context 数均可随轮数增长 | `effective_memory.py:185-239` |
| 输入上限时机 | 在每次调用前检查外层 compact JSON messages 字符数。learning 在 Candidate 环境执行及 Gate 之后；过大时会留下已经付出的执行成本，不能发表 Memory/新状态 | `continual_runner.py:200-225,397-420` |

## 各阶段最低证据职责与可减少范围

### 分类与 Diagnosis

必须仍看到全部任务而不只失败任务；保留任务请求、运行侧身份、每条路径的观察—行动—反馈顺序、完成性、成功/失败以及真实 Actor 能力。分类不能仅看任务名/结果，Diagnosis 也不能只看最后失败点。最先做完整信息的字典共享、行列编码和程序元数据私有化。是否属于“无损”应由解码后逐字还原检查决定，不能靠压缩前后事件数相等证明。

分类已有 opaque T 别名，决策分组信息本身不是执行事实。将分组中的 shared_basis/decision_problem 文本当作旧轨迹摘要、进而删去原事实，会形成模型推断自我引用。保留分组作为组织坐标，原观察身份仍应独立。

### Fusion

最有价值的改动是区分“有效认识目录”和“历史证据正文”：全部 Effect 的 `id/claim/limits/attribution` 与 claim/limit 的来源上下文需要保留，尤其不能只按 group ID 或任务家族过滤；具体 basis 与 actual edit 只在所选证据闭包中展开。当前 Update 相关的历史作用应能沿 Effect → context → 实际 diff/Editor/Parent 依赖 → event 回到确切来源。

但是，不存在一套仅靠通用关键词匹配就能保证挑全自然语言 claim 中关键反例的程序规则。对任意自然语言的 Watch/Update，历史可迁移性、矛盾和未知条件仍需语义判断。若不增加调用/检索动作，可先保持全部 Effect 的关键实际响应闭包、仅去除历史上下文的冗余；若进一步筛选，应称为有覆盖边界的选择原型，不能声称已经不损失 D/S/C 判断能力。只给 claim 目录的模式可以做敏感性/容量下界，不能作为无损方案。

### Editor

其任务是实现有效 Update，不能因压缩而把权威换成 Memory，也不需要重新决定历史是否支持另一策略。v3 已明确 `Memory explains context and limits; it does not authorize another strategy choice`（`unified_dsc.py:114-137`）。因此可以不输入无关全轨迹/全 Memory，至少保留：

1. 完整实际 Parent Skill 与实际 base protocol/capabilities。
2. 完整 effective Plan 的 intent/requirements/watch/open；不摘要删除条件、强度、依赖或保留义务。
3. 每条有效 requirement.basis 的来源闭包：当前 Parent 事件带当时前/后观察和实际可用动作、组定义及重要差异；若 basis 引用 Effect，保留该 Effect 的 claim/全部 limits/作用上下文，正文取支持本次有效 Update 的已绑定材料。
4. 原来源身份/引用不变，映射仍针对相同有效 requirements 和真实 Parent/Candidate 文本。

特别注意 Compiler 对替换 requirement 会自动继承全部原 basis，并加 changes.basis（`compact_update.py:241-245`），因此不能把当前有效 basis 误读成“全部新历史依据”，也不能删掉未改变要求的授权来源。`changes.reason` 不等于新授权，Editor 的规范输入仍是完整有效 Plan。

移除 Editor 无关史料是职责性选择，并非还原原始全消息的无损压缩；合理性来自既有角色边界，需新的可见输入契约与模型语义验证。保留一个外部文件 hash 只能保证可追溯，不能使模型看见文件里的条件。

### Replay/Memory

必须区分 actual Update 实现、Parent/Candidate 两侧机会、行动、反馈、结果，以及没有观察到和执行后无效。每条路径不应因为任务相同就对齐为同一决策机会。候选路径造成某机会不再出现，本身也可能是响应（`unified_dsc.py:148-171`）。

最安全的第一步是用字典/引用完整呈现全事件，再把实际 diff、Editor 映射、Plan/Watch 与事件别名对齐；这可以减少重建关系的冗余但不是自动判定机会。不能把“某动作文本包含 Watch 关键词”当成目标条件成立，也不能由遗漏列表中无该行为推断它未发生。

若仍需实质精简，应明确每个省略片段的实际 run 与 step 范围、原始来源、精简规则及未直接展示字段；禁止从不可见部分作否定推论。即使只压缩完全相同的连续动作/反馈，也需保留次数、时序及动作候选变化，否则重复行为本身、预算消耗、状态未变/变化会丢失。执行记录完全无损可解码的 run-length 编码属于安全表达；挑首尾、导航摘要、关键词事件窗不属于无损。

## 必须作为设计风险写明的边界

1. **归档可追溯不等于模型证据覆盖。** 当前 COMMON 明确来源经 supplied content 解析，不能推测隐藏文件（`compact_update.py:35-40`）。完整原始材料留磁盘不自动弥补模型输入删除事实。
2. **基于任意自然语言 Watch 的关键事件选择不可能仅靠现有类型保证完整。** Watch 可能询问未执行选择、跨阶段依赖、未预料副作用。没有新的语义工具、循环或结构化条件，纯确定性选择能保证的只是显式 refs 的闭包，不能保证全部相关事件。
3. **全有效 Effect 目录仍有规模下界。** 即使 basis 正文归档，全部 claim/limits 的字符总量仍可增长；不限新 Effect/limits 的系统不能同时保证无限轮、全部认知可见、固定输入上限。应对本次五轮给可测容量结论，不能宣称已经解决无限历史。
4. **来源校验需要跟可见性协调。** 原 `_sources` / `validate_learning` 主要验证 alias 存在及 Watch 路由（`compact_update.py:148-163`; `compact_learning.py:277-300`）。若消费视图只列 alias 不展示正文，而仍在原 payload 上接受全部 refs，结构通过不能证明模型依据可见事实。未来需校验输出引用落在本次可见来源闭包，或者明确区分 index-only 来源不可支持行为事实；不能悄悄让模型使用未展示外部证据。
5. **完整动作集合的顺序也需按原记录还原。** 如用 command 字符串词典+set/差分引用，必须证明每步的集合内容与顺序都能恢复；不能把无序集合相等当作逐字相等。数字 ID 不一定减少服务 tokenizer 的 Token，容量测试必须分开字符与 Token。
6. **只保留静态 Plan basis 不足以取代 Replay 全比较。** basis 是事前选择，真实新反例/跨组副作用可能发生于未引用轨迹。Editor 可以缩到授权实现范围，学习不能机械继承相同裁剪。
7. **历史反例不能用“最新一条”替代。** 作用范围可能依赖旧 Parent 的保留策略、旧 Candidate 的未采用状态、不同条件上的相反结果。current grouping 只属本轮，不能跨轮当适用性硬边界。

## 五轮 Train+Selection 的独立兼容问题

本机 `benchmarks/alfworld/editions/skillopt_39_18_134` 当前确为 train 39、val 18、test 134。用户拟合并的 57 项能用于离线容量情境，但**当前 v3 正式运行器不能直接执行该研究协议**：

- `src/adapters/alfworld/skill_runtime.py:67-76` 只允许 learning/train 与 selection/val，且 learning_allowed 仅 Train；`verify_skill_run.py:152-164` 的 learning_feedback 拒绝不可学习材料。
- `compact_learning.py:60-61`、`grouped_representation.py:70-71`、`continual_state.py:121`、`continual_runner.py:278-280` 均约束 Train 学习来源。
- `continual_runtime.py:92-119,167-183` 限制每批 1—10 项，并固定两轮、相同 tasks_per_round、Train manifest，正常九次语义调用；12+12+12+12+9 需要新运行协议和预算加载规则。

这不是 D/S/C 算法的容量缺陷。将 Selection 用于学习本身是新的实验数据使用边界，需明确将这 18 项列为新增 development/learning pool，并保留原 val/selection 身份和访问政策变更记录，不能改 task ID 或伪装成原 Train；使用后也不能再把这 18 项当未使用的 Selection 评估。未来允许时，应按新独立协议适配 Adapter 的用途语义及三处消费校验，而非本次直接修改。这也意味着即使压力原型小于 300,000 字符，也不能交付“57项现在可直接启动”的结论。

## 最小落地建议（仅设计）

1. 新增单独 evidence-view/profile 身份：保留 v3 payload/validator/persistent Memory 与原实验可重建，新增消费投影与对应 Prompt 的解引用/覆盖说明，不改输出 Schema、Gate 或正常调用数。
2. 先实现可逆无损表示：共享 exact command/observation 文本、消除重复 update/group/source 元数据，只保留必要可见身份；原 payload 为唯一 canonical source。解码逐事件比对并验证 source closure。
3. 单独 Editor 职责视图，不再默认发送全部 Current/History；所有完整有效 Plan 及授权来源闭包保留，不能只传 requirement.text。
4. Fusion/学习先保留全部当前行为证据与全部有效认知的必要历史响应；不预设关键词检索正确。只有实测不足再评估有覆盖边界的证据选择，并报告质量风险和新验证需求。
5. 真实调用前按实得消息预算检查；容量预检应同时包含 batch、50步、独特观察/大型动作集合、Effect增长、固定Effect basis/limits增长、矛盾历史。超限必须显式失败，不能静默截断或输出伪Keep。
6. 回归关注：完整解码、合法引用、Parent/Candidate身份、实际更新链、反例/未知全文保留、历史版本兼容、实际输入与新profile冻结。离线检查不证明模型同等理解紧凑表示。

