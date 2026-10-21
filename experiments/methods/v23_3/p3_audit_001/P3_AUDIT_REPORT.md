# V23.3 P3-Audit：首次真实 A/B 决策归因

日期：2026-10-21。对象：`memory_v3_integration_001`。本次只读审计已完成调用，仅新增本报告；不调用模型、不重跑实验、不修改实现、Prompt、Memory 或既有归档。

## 1. 结论与证据边界

**B 全部 Keep 是正常完成的语义决定，不是上传失败、输出截断、Patch 应用失败或编译失败。关键历史没有漏传。最直接可观察的问题是：B 用当前问题仍存在来支持保留原方向，但没有公开解释相关混合历史响应为何不触发调整，并遗漏了 u2 的 Actor 可见性边界。现有记录不能确定唯一根因。**

- **更新粒度**：B 没有实际 Patch，无法验证其修改对象是否比 A 更准确。零修改没有新增承诺，但不能因此计为精准更新。
- **历史响应利用**：A 明确引用 M8、M3、M6，实际改写了 u1/u2；B 最终理由没有 Memory ID、历史来源或实际 Diff 的讨论。前者是可追溯的参与线索，后者是未展示参与，均不等于 Memory 因果效果的证明。
- **策略构造质量**：A 有具体且合理的探索动机，也引入过强覆盖顺序和跨 Update 协调风险；B 保留有依据的精确目标与候选动作要求，同时保留 u2 的未解决边界并存在事实误读。不能宣布任何一组稳定更优。
- 本案例是已用于设计的 R05；没有无 Memory 对照、重复样本或 Replay。不能推断 ALFWorld 成功率、效率、泛化或 Memory v3 的独立收益。

本报告的“模型明示”仅指最终 JSON 的 `reason` / Adjustment 理由；不以内部 reasoning 文本解释心理过程。“审计判断”和“待检验假设”分别表示证据评价和尚未确立的因果解释。

## 2. 实际输入、输出与历史完整性

主要证据入口（下文直接使用 JSON 字段名与完整步骤 ID）：

- [A 实发请求](../memory_v3_integration_001/runs/A/http/001/request.json)、[B 实发请求](../memory_v3_integration_001/runs/B/http/001/request.json)；均逐字段核对冻结请求及 `messages.json`。
- [A 原始 HTTP 响应](../memory_v3_integration_001/runs/A/http/001/http_response.txt)、[B 原始 HTTP 响应](../memory_v3_integration_001/runs/B/http/001/http_response.txt)；最终 content 与 `raw_output.txt`、parsed 一致。
- [完整输入及 Original Plan](../memory_v3_integration_001/config/full_payload.json)、[实际 Memory v3 视图](../memory_v3_integration_001/config/model_input.json)。
- [A 最终回答](../memory_v3_integration_001/runs/A/raw_output.txt)、[B 最终回答](../memory_v3_integration_001/runs/B/raw_output.txt)、[Effective A](../memory_v3_integration_001/runs/A/effective_plan.json)、[Effective B](../memory_v3_integration_001/runs/B/effective_plan.json)。
- [B 实际 Prompt](../memory_v3_integration_001/runs/B/prompt.md)、[原实验协议](../memory_v3_integration_001/PROTOCOL.md)、[冻结配置](../memory_v3_integration_001/config/freeze.json)。

核验结果：

| 项目 | 实测 |
|---|---|
| A/B user content | 逐字符串相等；解码后均等于归档 `model_input.json` |
| 非 Memory 输入 | 与首次 P3-A 原始输入完全相同；Parent、Original、Grouping、当前 runs、command_sets 未变化 |
| 当前证据 | P1/P3/P6/P7/P8/P10，合计 213 步，103 个命令菜单，完整当前轨迹 |
| 模型参数 | 两组同为 deepseek-v4.1-flash；temperature=1、thinking enabled、reasoning_effort=medium、max_tokens=32768、stream=false、timeout=(60,300) |
| 调用 | B 后 A，各 1 次 HTTP、0 重试；均 HTTP 200、finish=stop |
| 结果 | A ready，修改 u1/u2、替换三个 Checks；B ready，`adjustments=[]`、`checks=null` |
| 编译 | 两组归档校验均成功；B Effective 与 Original 整对象相等 |

完整 Memory 与正式 S1/R05 `round_input.json.memory`、S1/R04 `memory/view.json` 及首次 P3-A 冻结 Memory 完全相等。Active IDs 为 **M1、M2、M3、M6、M7、M8、M9**；没有 M10 或 R06 之后资料。原实验冻结的文件摘要本次逐一校验均一致。

**“进入输入”与“未压缩完整状态”必须区分：**

- 七条 entries 的 knowledge/evidence 逐字段保留；74 个 sources 键全部保留，其中 4 个历史 Parent/Diff/执行背景来源原样保留，70 个历史执行保留 task、initial、outcome 和完整有序动作/反馈 trace。
- 合计 1,716 个历史步骤，其中 **416 步保留显式 before/after 和对应菜单，1,300 步省略完整状态细节**。trace 中的 feedback 是原记录的奖励、结束、合法性、fallback 等字段，不能当作遗漏的 observation。
- M3：39 个引用，覆盖一个 Diff 和 20 个执行；458 步 trace、104 步详细状态。M6：23 个引用，覆盖一个 Diff 和 6 个执行；225 步 trace、61 步详细状态。二者所有数值步骤引用均有详细记录，命令菜单解析后与完整源一致，没有关键引用悬空。
- 全部保留的 trace 动作/feedback、详细步骤 observation、initial/outcome、菜单内容及顺序均与完整 Memory 核对一致。

因此，“M3/M6 没有发送”可排除；“所有历史状态都能逐步检查”不成立。完整动作序列可检查是否执行过某次导航，但不能在状态缺口中推断隐含物品、持物状态或候选动作。材料可用也不证明模型实际读取、比较过它们。

## 3. u1/u2/u3 决策分析

### u1：精确目标与禁止替代

**Original**：三行分别禁止 acquire/clean/cool/heat/place 近似替代物、离开只有非目标物的容器继续搜索、禁止把非目标处理/交付算作进展。第一行使用 `exact noun phrase`。

**当前证据**：P7 请求 butterknife，却在 P7:5 取 knife、:7 清洗、:9 放入 drawer，最终 step_limit。Parent 已有 exact-category/no-substitute 条款。这支持精确类别约束的必要性，也说明既有表述未可靠避免替代；不证明本次尚未执行的 Original 已经失败。

**历史响应**：M3 的 S1_R02/P5:37/42 替代 soapbottle、Q5:19/20/22/24 找到 dishsponge 后清洗交付，是搜索扩展与精确目标联合改变的响应。M8 的 S1_R03/diff、S1_R04/diff 加入明确类别例子及温度动作禁替代；S1_R03/P10:40/41 操作 cup、Q10:36/37 看到 cup 后离开，以及 S1_R04/P1:28/31 取热 cup、Q1 全 trace 未操作 cup，支持“相近规则可能改善避免替代行为”的探索动机，不能孤立证明例子的效果或成功率提升。

**模型明示与决定**：

- B Keep：称该反例说明要求仍必要，“necessary rather than falsified”；承认重复规则的效果未验证，并说 `no executable better formulation is available`。没有讨论 M3/M8。
- A 修改：在 u1 中添加 knife/butterknife、pot/pan、cup/mug 例子，把 container 扩为 container or surface，明确引用 M8；声称例子版本产生预期的避免替代行为。

**审计判断**：保留精确目标方向合理，历史也不强制要求修改 u1；但 B 的“没有更好可执行表述”只是最终判断，没有展示为何排除具体化探索。A 提供了一个可执行候选，仍未证明“更好”。A 把 `current wording did not prevent` 用于新 Original，并将 conditioning 禁令说成新增，两者均不准确：实际执行的是 Parent，Original 已包含 clean/cool/heat。`exact noun phrase` 是否应解释为类别而非逐字匹配仍有边界风险，尚无本轮执行证据证明其造成错误。

### u2：搜索调度、同类位置覆盖与有限历史

**Original**：①同类若干次未找到后，先转向至少一个尚未检查的其他类别，再回查旧位置；②包含开放表面；③离开已打开但无目标的容器，选当前候选中的未检查位置，避免循环。

**当前证据**：P3:8–11 回访先前检查的 drawers；P6 前段反复回访后持续扫描大量 drawers，未访问 cabinets；P8 反复回访 cabinets；P10:32 才到 diningtable 找到 apple。支持减少无信息重复和扩大覆盖的动机，不能推出唯一切换时机、全局位置顺序或“每类一次即结束”。

**历史响应及可支持的变换**：

| 历史实际编辑—响应 | 能支持什么 | 不能支持什么 |
|---|---|---|
| M3 / S1_R02/diff 新增开放容器、避免立即回访、精确目标等；Q5:19–24 扩展到 bathtubbasin 并成功，另有循环失败 | 保留覆盖扩展方向；仅重复禁令并未可靠消除循环，可考虑其他可执行表述 | 不能把 bathtubbasin 写成通用优先位置；不能把收益单独归于某一句 |
| M6 / S1_R03/diff 新增近期观察防循环、新位置/预算优先等，并联修改精确目标与温度行为；Q4:12/13/15/17 从 diningtable 取 bread 后完成 | 新位置探索有正向响应线索 | 不证明跨类别切换策略最优，也不证明“多查新位置”总会节省步数 |
| M6 / P2:15/16/18/20 在 countertop 3 找 bread 并成功；Q2 完整 trace 没有访问 countertop 3，反复 countertop 2，最终失败 | 提醒“类别扩展不等于同类别各实例覆盖”；可检验保持同类其他位置机会的策略 | 原历史文本不是当前 Original；不能称当前 Update 已被该配对直接证伪，也不能推出先穷尽所有同类才换类 |
| M6 / Q6:4/10/15 不可用导航；:48 开 cabinet 9 发现 plate，:49 取物，:50 到 fridge 后耗尽预算 | 协调合法动作与有效搜索；反例限制过强效率保证 | 不能把晚找到归因于某单条搜索规则；不是第 49 步才首次观察到 plate |

**模型明示与决定**：

- B Keep：称当前批次 `strongly supports` u2；承认 Parent 防回访规则未阻止循环，u2 的收益只是 hypothesis。没有解释 M6 的正/负响应，也未处理“尚未检查”的信息来源。
- A 修改：明确引用 M3/M6，称重复禁令不可靠、同类位置被漏查；新增同类其他实例覆盖、更多表面、空手少查 inventory、导航不可用则换地点。其说明声称弱化回访禁令，但最终文本仍要求先检查剩余同类及其他类，才返回任何已检查地点。

**尚未处理的问题**：

1. Actor 只有当前状态与最近两对动作前观察/动作，无完整访问集合。B 的“All three … executable”没有与 u2 的 `still-unexamined`、`before rechecking any location` 协调。近期空位置可以识别，任意长历史的未检查/已检查集合不能默认可知。此处存在有依据的条件收窄/局部化动机，**不需先证明某替代调度更优**。A 同样保留并加强了这一全局状态依赖。
2. M6 足以要求认真比较历史混合响应，但并不逻辑强迫 Replace；原 u2 没有明确命令“跳过所有同类其他实例”。B 可以合理 Keep 一种有动机的新假设，前提是说明为何历史反例不直接适用及可执行边界。本次回答没有做到。
3. A 的“导航不在候选则去别处”可能跳过 u3 要求的适当 direct action；P6:20→21、P8:5→6 恰有导航不可用但 direct open 合法的情形。这是必要协调风险，不能直接称为已协调。
4. 两组均没有新增“每个类别采样一次即可结束”的标准；不应把旧研究中的已知风险算作本次实际输出错误。B 没有新增探索，但保留了 Original 本身的跨类/表面探索假设。

### u3：候选动作检查与 direct action

**Original**：只发当前候选中的导航/操作；导航缺失但适当 direct action 可用时使用后者，否则选其他有效动作。

**当前证据**：实查 P1:4、P6:20、P8:5 的 before 菜单均不含所发导航，结果 Nothing happens；P6:20/21 的菜单包含 `open drawer 5`，P8:5/6 包含 `open cabinet 3`，随后直接打开成功。

**相关历史**：M6 / S1_R03/Q6 的重复不可用导航支持类似问题确实反复出现；M7 的“已合法可用的温度动作不必先插入物体”只能作为不同任务阶段的条件类比，不能替代当前开门证据，也不要求强制给所有任务新增温度条款。

**模型明示与决定**：B 据上述当前反例及 P8:6 成功 direct open 保留；A 也称 u3 well grounded 并保留，但改写 c3。两组对该项都未给出历史 ID 支持的变换链。

**审计判断**：Keep 有充分当前依据，不应为显示 Memory 参与而强行改写。仍未验证 Actor 是否遵从、所有 direct action 是否“appropriate”；A 在 u2 新增的导航分支与该项可能冲突。B 用 P10 成功及当前无多实例任务解释不另加温度/数量要求，只能说明本轮缺少必需增补的依据，不能证明这些能力永远不需要指导，也不等于删除旧 Skill 要求。

## 4. 事实错误与归因错误分层

| 记录中的说法 | 原始记录 | 分类与影响 |
|---|---|---|
| B：P8 从未检查 bathtubbasin 1 | P8:2 已到达并观察为空；未访问 shelf 1 / toilet 1 的部分成立 | **模型对已有当前证据误读**。削弱该具体覆盖论据，不消除整体循环事实；与历史压缩缺失无关 |
| B：P6:6/10/16 反复 reopen drawer 1/2 | 三步均为 `go to drawer 1`，其后观察为已打开 | 动作/对象叙述错误；支持回访，不支持这三步重新开门 |
| B：P3 的 drawers 1–4 都在 :2–6 打开 | :2/:4 open drawer 1/2；:5/:6 导航并看到 drawer 3/4 表面 | 把不同位置类型/动作合并；回访判断仍成立 |
| A：历史给出 `this exact clause` 的直接响应 | S1_R02/03 的 Diff 与新 Original u2 不同；当时也改了其他条款 | **模型归因过强**；属于近似策略的联合编辑反馈 |
| A：M8 表明显式例子产生预期避免替代效果 | 例子、搜索、温度等同时变动；未隔离例子的作用 | 有关联证据，无单条因果证明 |
| M8 knowledge：目标“absent”或不可达 | 轨迹可支持未找到，不能证明所有隐藏位置没有目标 | **输入知识的过强表述**，原样进入 v3；Prompt 要求以来源修正，不应继承为全局事实 |
| M6 knowledge：到第 49 步才到达 plate | Q6:48 已打开并看见，:49 是取物 | 历史摘要步骤措辞不准；详细证据完整可纠正，不是投影丢失 |

研究者也须避免三种误归因：把 B 不引用历史当作完全未读历史；把零修改当作准确修改；把 A/B 差别全归于 Unified Diff。当前两臂同时不同的是决策 Prompt 和输出契约，且各只一个随机样本。M6 配对初始观察一致、已检查位置有重合内容，但不要仅凭未访问位置的轨迹推断所有隐藏内容都已被双方观察验证。

## 5. 全部 Keep 的可能原因：证据强弱

| 候选解释 | 支持证据 | 限制 / 当前判断 |
|---|---|---|
| 将必要方向成立作为保留具体表述的主要理由 | B 明说 grounded/executable/compatible；u1 necessary rather than falsified，u2 效果作为 hypothesis 保留 | **最直接的公开决策依据**。对 u1/u3 可合理，但不足以回答 u2 的可见性边界；不等于已经查明内部决策过程 |
| 相关历史未被充分转化为公开决策依据 | B 不讨论 M3/M6，A 在相同 user 输入中明确引用并修改 | **可观察的论证缺口**。无法区分没读、读后认为适用性弱、未写出、或其他原因 |
| Preserve/Keep 与精确 Patch 约束提高了修改门槛 | B Prompt §3 Keep 要求无纠正/探索动机；§4 保留无理由改变的其他要求；§5 要精确 hunks，无修复/回退；Keep 无须生成 patch | **设计层面的可能压力**。没有实际构造失败或“因 Diff 太难而 Keep”的声明，不能认定根因 |
| 全 Keep 分支缺少逐 Update 的历史适用性记录 | §6 要解释历史编辑/响应；但输出结构只强制 Adjustment 的 basis/reason，`adjustments=[]` 可只给总 reason | 可审计性弱于有调整分支，结构校验不能保证历史比较已完成；**不是允许忽略历史**，更不是已证实致因 |
| 大上下文使检索、比较不充分 | 每组约 28 万实际输入 tokens；B 存在可直接核查的当前事实错误 | 负担与误读并存，**因果未确立**。无法排除一般推理/摘要错误或随机性 |
| M3/M6 缺失、技术失败或输出预算耗尽 | 实发输入完整保留关键历史；stop、合法 Keep、编译成功，B completion 14,107 < 32,768 | **现有记录不支持**这些解释 |

不能将 Prompt 简化成“必须已有成功证明才允许修改”：§3 Replace 明确允许 mixed responses 下的新可执行假设，并写明 `Unknown optimal strategy permits exploration`；同时明确不优化少行、小改动或自动保守。§4 要求投影到 Actor 实际可见信息，§5 允许合理的全文替换。因此，当前更像是某些要求未在最终论证中落实，而非规则明文禁止探索。u2 修改也不需要 merge/split，不能归咎于结构操作受限。

三方面主要问题是：**当前证据理解**有具体事实误读和可见性检查遗漏；**历史响应利用**缺少 B 的可追溯适用性判断，A 则存在过强因果措辞；**Patch 构造**没有真实修改样本，尚无法判断表达能力或格式负担，工程通过只覆盖了 Keep 路径。

## 6. Memory v3 构成与成本补充

服务端实际 usage：

| 指标 | A | B |
|---|---:|---:|
| HTTP 正文字节 | 961,087 | 963,910 |
| prompt_tokens | 277,951 | 278,659 |
| completion_tokens | 17,369 | 14,107 |
| 其中 reasoning_tokens | 16,116 | 13,365 |
| total_tokens | 295,320 | 292,766 |

合计 **588,086 tokens**；reasoning 已含在 completion 中，不重复计费。货币费用未知。与早先失败尝试相比，本实验同时改变 Memory 表示和输出上限，不能把成功生成单独归因于 Memory v3。

共同 user JSON 为 861,549 UTF-8 字节。Memory 包含 7 条知识、4 份编辑来源、70 个执行、1,716 步 trace、416 步详细状态及 265 个共享历史菜单（合计 8,144 个菜单内命令项，非全局唯一命令数）。

没有该内网模型的精确分项 tokenizer/服务端分项 usage；下表是**离线本地 o200k_base 代理计数**，不是 DeepSeek 实际分项费用。方法：对实际 payload 的各子树用 `json.dumps(ensure_ascii=False,separators=(',',':'))` 序列化后本地编码；无联网、无模型调用。对子树重新包装会重复少量键，边界分词也不同，因此各行不强行相加当作总量。

| 输入组成 | 本地代理 tokens（约） |
|---|---:|
| 历史完整动作/feedback trace | 85,117 |
| 历史共享命令菜单 | 52,833 |
| 历史显式 before/after 详细步骤 | 40,762 |
| 历史任务、初始状态、outcome、窗口等其他元数据 | 19,661 |
| 历史 Parent/Diff/执行背景 | 9,873 |
| 七条 Memory entries | 4,519 |
| 当前完整 runs | 27,221 |
| 当前 command_sets | 26,901 |
| 当前 Parent / Plan / Grouping | 669 / 639 / 1,302 |

整个 Memory 子树为 212,299 个 o200k 代理 tokens；完整消息文本 A/B 为 271,488 / 272,146，Memory 约占 78%。cl100k_base 交叉计算分别为 Memory 209,995、完整消息 268,461 / 269,111，规模判断一致。**主要负担来自历史动作/反馈、菜单和状态，不是七条 knowledge 本身**；当前轨迹和菜单也是显著来源。本轮不据此调整窗口或压缩算法，也不把输入规模当成 Keep 的已证实原因。

## 7. 尚不能确认与下一项实验

现有记录无法确认：B 实际读到了哪些历史；未写出历史比较是省略解释还是未完成比较；精确 Patch 要求是否抑制了本来可提出的方案；新 wording 能否改变 Actor；更换表示、减少输入或提高预算各自有多少独立贡献。没有 Patch 的 B 也不能证明会正确构造大幅修改。

**优先建议一项“固定 B 决策规则，仅改变输出表示”的小规模配对实验**，先分离本次 A/B 中混在一起的决策 Prompt 与编辑格式，不急于修改整个机制或做 Replay。

- **固定**：本次唯一 Original、完整共同 user payload（含 Memory v3）、证据顺序、Actor 背景、B 的历史响应/可见性/探索/必要协调规则、模型及全部生成参数；不增添理想策略、事实纠错提示或新的证据摘要。
- **唯一主动变量**：同一 B 决策规则下输出 `to.patch` 或完整 `to.text`。只在独立实验变体中替换直接涉及格式和渲染流程的说明/示例，其他决策措辞逐字不变；两臂均限定相同的单 Update 修改能力，复用原编译器。正式 Prompt 和旧结果不改。
- **预注册**：建议固定 3 对、共 6 次新逻辑调用，交替顺序、全部保留，不因 Keep 或不理想追加采样；开始前另行冻结协议。旧 B 只作背景，不替代一个新配对样本。
- **评价**：技术有效性单列；主要看是否准确处理当前事实、u2 可见性、M3/M6 正负响应的适用边界，是否保留必要行为及避免新增无据排序/禁令。允许合理 Keep，不能以“改得更多”或 Memory ID 数量为成功标准；由评价者区分有证据的纠正与未验证探索。
- **解释**：若文本臂更常形成有依据、可执行且协调的方案，而 Patch 臂反复遗漏这些问题，才有“输出构造约束影响决策”的初步线索；若两臂均出现同样遗漏，应优先研究证据到决策的环节。两臂都 Keep 仍须评价 Keep 理由，不能机械判失败。少量随机样本仍不足以确立稳定因果效应，更不证明任务收益。

## 8. 保护与停止

审计起点 HEAD：`daa2068498fe94f89d2be0c4e743fea1c63a8341`。已有 `docs/04_EXPERIMENT_LOG.md` 修改及 V23.3 未跟踪目录保留。只新增独立 `p3_audit_001/P3_AUDIT_REPORT.md`，没有改写被审计实验中的既有评价或报告。

最终检查：既有 `src/tests/experiments/artifacts/docs` 文件清单的大小与纳秒修改时间、tracked Git diff 与审计起点一致；原实验冻结摘要一致。本次未执行模型、Editor、Actor、Replay、Gate 或 Memory 更新，未启动上述建议实验。完成后停止。
