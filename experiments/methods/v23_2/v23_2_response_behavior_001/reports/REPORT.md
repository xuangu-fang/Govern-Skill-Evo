# R06：固定 V23.2 Update 的局部 Candidate 行为验证

日期：2026-10-19。**完成一次逻辑 Editor 调用和七条 Candidate Episode，已停止。新 Candidate 有实际但局部的行为改善：plate 搜索更短，两条 tomato 加热减少插入／门切换；没有提高成功数，也未稳定改善跨类别搜索。**

Parent 为 **6/7、178 步**，原 V23 Candidate 为 **5/7、202 步**，新 V23.2 Candidate 为 **5/7、162 步**。新旧 Candidate 成功集合相同，apple 与 book 均耗尽 50 步。不能将 40 步节省理解为搜索问题已解决，或将差异全部归因于 Preconditioner Prompt。

## 1. 冻结材料与执行边界

- 从 `v23_2_response_alignment_001/R06/attempts/001` 严格重读保存的真实响应，并用既有编译器核对 Effective Plan；没有新 Diagnosis／Preconditioner 调用，也没有人工修改 Update。
- Parent 与正式 R06 Editor 的 Parent 逐字相等，即 R05 正式保留 Skill；没有从原 R06 Candidate 开始编辑。原 Editor system 消息与配置相等，输入仍只有 Parent 与 Effective Plan，共享背景不变。
- 本次使用原七条 `val:0011`–`val:0017`，顺序、task_id、gamefile、初始观察、初始动作候选、环境配置和协议均与历史逐条相等。这是正式 57 条优化池中的 Selection 子集，不是最终 134 条 Test。
- Actor 为 deepseek-flash，temperature=1、Thinking enabled、reasoning_effort=medium、输出上限 16384，seed=42、50 步、最近两组行动前观察与动作。原调度并行上限 8，本次同时启动七条独立 Episode。原有 API 配置和环境依赖版本相等。
- 相对训练冻结源码唯一既有差异为此前正式 Test 恢复已授权的 `ChunkedEncodingError` 重试覆盖；本次只核对该一行差异并沿用，没有改源文件。未读 Test 轨迹作研究证据。

实现仅新增独立实验 [run.py](../run.py) 和只读 [analyze.py](../analyze.py)，没有新执行框架。Editor 的归档读取依赖临时接入既有 V23.2 验证读取器，原 Editor 输入装配、Prompt、输出验证、Patch 应用不变；调用与任务调度分别复用原 `_model_stage`、`_actors`、`actor_task`。未运行 Gate、Replay LLM、Memory 更新或发布正式 Parent。

[冻结来源及调用边界](../config/plan.json) · [实际 Effective Plan](../config/effective_plan.json) · [逐项一致性核验](../results/verification.json) · [162 次 Actor 消息重建核验](../results/actor_checks.json)

## 2. Editor 实际落实与偏差

首次响应 `finish_reason=length`，输出 16384 tokens（全部记为 reasoning），未产生合法完整输出。按原规则技术重试一次，第二次返回合法 Patch；没有语义重采样或人工修补。原严格坐标与上下文应用成功，重读再次应用得到同一 Candidate。

[实际 Skill Diff](actual.diff) · [原始 Patch](../../../../../artifacts/methods/v23_2/v23_2_response_behavior_001/editor/attempts/002/patch.diff) · [Candidate Skill](../../../../../artifacts/methods/v23_2/v23_2_response_behavior_001/editor/attempts/002/candidate.md) · [Editor 原始输出](../../../../../artifacts/methods/v23_2/v23_2_response_behavior_001/editor/attempts/002/raw_output.txt)

| Effective Plan 要求 | 实际 Skill 落实 | 判断 |
|---|---|---|
| u1 持精确目标直接 heat/cool，按需开门，处理后交付 | 新增 Heat/Cool Conditioning 段，包含这些操作与近似类别排除 | 主体忠实；与原 V23 Candidate 的行内写法不同，构成行为比较中的 Editor 实现差异 |
| u2 不先穷尽大类、类内升序、跨类别轮换、优先开放表面再设备 | 替换 General 第 1 条，保留这些要求 | 关键方向／顺序落实，没有偷偷改回旧策略 |
| 部分类别后换类、所有类别采样一次终止、固定顺序保证进度 | 分别保留 `part of a family`、`all plausible families have been sampled once`、`guarantee progress` | 已知风险原样进入 Candidate，没有补丁修复 |
| 精确类别、交付与原有成功行为 | 原 General 第 2–4 条、desklamp 规则及末尾成功行为要求保持 | 没有删除这些正文；未新增清晰的双物体计数步骤，原 Parent 本来也无这一显式步骤 |

**不是完全无偏差的机械转写。** 替换搜索段时，Parent 的 `Do not repeatedly check inventory while carrying nothing` 被省略；Effective Plan 未要求撤销该既有约束。新 Skill 还补充 microwave/stoveburners/fridge 的设备举例，其中 stoveburners 并非 u1 明示例子，本次没有任务验证该扩展。搜索触发写为 `If it is not visible`，没有保留 u2 的 `in the initial observation` 限定；更接近 Parent 的持续搜索写法，但不能认定与 Plan 范围严格等价。温度独立章节和 General 的清洗／交付条款需要 Actor 组合执行。

这些偏差全部记录，没有为了“忠实”而人工改 Patch。本次七条新轨迹没有 inventory 动作，因此没有观察到遗漏该句的实际副作用；也没有观察到设备举例误用。后面的结果反映的是这份真实 Editor 产物。

## 3. 七条任务结果

“失败”均为正常 50 步耗尽，非技术错误；成功均由环境 won 标记确认。

| task_id／任务 | Parent | V23 Candidate | V23.2 Candidate | 新相对 Parent／旧 Candidate 步数变化 |
|---|---:|---:|---:|---:|
| val:0011 冷 plate → countertop | 成功 40 | 成功 39 | **成功 7** | −33 / −32 |
| val:0012 冷 tomato → microwave | 成功 14 | 成功 10 | 成功 10 | −4 / 0 |
| val:0013 热 apple → diningtable | 失败 50 | 失败 50 | 失败 50 | 0 / 0 |
| val:0014 热 tomato → fridge | 成功 22 | 成功 13 | **成功 9** | −13 / −4 |
| val:0015 热 tomato → fridge | 成功 18 | 成功 12 | **成功 8** | −10 / −4 |
| val:0016 两本 book → desk | 成功 24 | 失败 50 | **失败 50** | +26 / 0 |
| val:0017 两张 creditcard → safe | 成功 10 | 成功 28 | 成功 28 | +18 / 0 |
| 合计 | **6/7，178** | **5/7，202** | **5/7，162** | **−16 / −40** |

新相对 Parent：**0 修复、1 退化（book）**，其余五条共同成功、一条共同失败。新相对原 Candidate：**0 修复、0 退化**，五条共同成功、两条共同失败。共同成功的五条相对旧 Candidate 节省 40 步，其中 plate 贡献 32 步，两条加热各 4 步；不是因为新执行提前放弃而节省失败任务步数。

全部 21 条轨迹的实际动作、动作后观察及原始档案链接见 [TRAJECTORIES.md](TRAJECTORIES.md)，结构化表见 [comparison.json](../results/comparison.json)。下文 P/Q/N 分别指 Parent／原 Candidate／新 Candidate，编号为实际 step。

## 4. 搜索行为：局部改善与未解决部分

### plate：确有到达目标的实际改善

[val:0011](TRAJECTORIES.md#val0011)：P 在 cabinets 中多次重复，P34 才到 countertop 2；Q1–17 连续检查 cabinet 1–9，之后仍回访，Q33 到 countertop 2。N1–3 直接 countertop 1→countertop 2→take plate，N5 cool，N7 正确交付。

新策略的开放表面优先与这次较早找到目标相符。但这不证明已改善“全面覆盖”：因为更早找到目标，N 实际访问的搜索位置更少。它证明此任务不再支付长时间 cabinet 扫描成本，没有证明任意目标分布下的优势。

### apple：跨类别往返依然是重复循环

[val:0013](TRAJECTORIES.md#val0013)：N2 已看到 fridge 无 apple，N4 cabinet 1 为空，N6 cabinet 2 为空；随后反复 fridge／countertop／cabinet。N26 新到 diningtable 1，N42 才到 cabinet 3，最后 N48–50 又回 cabinet 2、countertop 1/2，50 步未取物。

对旧 Q，N 的不同到访位置从 11 降至 7，重复到访从 33 增至 41。类别切换不等于新位置覆盖；相同几类间往返仍可形成循环。未观察到“所有类别采样完毕后停止”，也不能断言目标实际位于某个未查位置——这些轨迹均未找到 apple，不借用环境隐藏答案补造目标位置。

### book：少扫连续 drawers，没有救回漏查 bed

[val:0016](TRAJECTORIES.md#val0016)：P17 到 bed 1，观察到 book 1、book 2，P18–24 顺序搬运成功。Q 全程未到 bed，50 步失败。N4–9 检查 drawer 1–3 后切回 shelf，N10–34 多次重复 shelf 1/2、desk 1、drawer 1–3；N35 到 sidetable，N39–40 才首次检查 drawer 4，此后继续回访，仍没有到 bed 1，50 步失败。

N 相比 Q 同类连续到访长度下降，但搜索位置覆盖更少、重复更多。bed 1 从初始房间说明就可见，目标位置由同 task 的 P 实际观察确认。**漏查确已发生，未证实由“类别采样一次”终止条件导致**：N 没有提前终止，也没有在文本上声称全部完成后放弃，反而持续行动到上限。不得把相对 Parent 的退化全部归因于新终止句；旧 Q 已存在同一失败。

### creditcard：早取第一张，第二张仍长时间扫描单类

[val:0017](TRAJECTORIES.md#val0017)：N2 在 desk 1 同时看到 creditcard 2 和 3，N3 取 2，N6 放入 safe。接着 N7–25 连续检查 drawer 1–10（N19 直接 open drawer 7，动作属于当步候选且环境正常执行），N26 取 drawer 10 的 creditcard 4，N28 完成第二次交付。

原 Q 是先扫 drawer 1–10 找第一张，再到 desk 找第二张；新 N 只是将长扫描移到第二张搜索，最终同为 28 步。P 回到仍有卡的 desk，10 步完成。N 保留了两张不同实例的交付，但没有稳定利用此前的剩余目标信息，也没有始终遵守“不耗尽大类”。不能只统计第一次 take 之前的搜索，就误报 creditcard 搜索全面改善。

### 辅助计数的定义与限制

统计首次 `take` 之前的 `go to`；若无 take 则统计整条轨迹。重复数=go-to 总数−不同位置数；同类连续长度按位置名称类型计算，忽略其间 open 等动作，不是连续环境步数，不等于所有重复均无效。开放表面的种类没有人为合并成一个家庭，未把 look/open 当作 go-to；因此需结合上面的原动作判断。

| task | P：位置／重复／最长同类 | Q：位置／重复／最长同类 | N：位置／重复／最长同类 |
|---|---:|---:|---:|
| plate | 11 / 15 / 18 | 13 / 10 / 10 | 2 / 0 / 2 |
| apple | 6 / 41 / 2 | 11 / 33 / 4 | 7 / 41 / 2 |
| book | 7 / 7 / 3 | 10 / 34 / 6 | 8 / 38 / 4 |

apple、book 多次返回明确没有目标的相同位置，观察内容未带来目标或状态变化；其无收益重复有逐步观察支持，不只依赖上述数量。

## 5. 其他行为与此前风险

- **温度操作有实际改善。** val:0014 的 Q5–10 是 open→insert→close→open→take→heat；N5–6 只 open→heat，然后交付。val:0015 同样由 Q5–10 的六步处理变为 N5–6 的两步。plate N5 可闭门直接 cool。仍有 N 在 heat 已可用时先 open 的额外动作，尚未完全遵守“仅动作不可用才开门”；本次没有反复开关门或插入／取出循环。
- **不能把温度改善独立归功于新 Preconditioner。** u1 在本次响应对齐实验中为 Keep，与原 R06 Original/V23 Effective 要求相同；这次 Editor 将其变成独立章节，原 Editor 写在通用第 3 条，Actor 又重新采样。文本组织和随机性均是混杂因素。搜索 plate 的改善与 u2 更相关，但同样不是因果隔离实验。
- **精确目标要求没有被整体破坏。** 成功轨迹操作对应 plate、tomato、creditcard；apple、book 失败轨迹也没有用可见的近似／无关物体完成替代。七条材料不能全面检验 knife/butterknife 等细粒度排除，也未测试 desklamp、clean 分支。
- **双物体能力局部保留。** creditcard 实际将两个不同实例放入 safe，未在第一次放置后停止；book 失败发生在首次目标获取前，不能用它证明“已经找到目标后不能搬两次”。
- **类别采样终止风险尚未被行为证实。** 两条失败都是 step_limit，全部 50 步仍是导航／开容器；没有提前环境结束，也没有转为持续 look/inventory 的放弃动作。成功任务均完成必要处理与交付。风险句仍在 Skill 中，不能据此证明安全；但本次没有支持“它导致提前停止”的直接证据。
- **已观察的残留或较差表现。** apple/book 相对旧 Q 的不同位置更少、重复更多，creditcard 第二张继续大类扫描。它们是本次实际表现，不是只停留在自然语言风险；未证明是新规则独立造成。Editor 遗漏 inventory 约束没有在本次触发（N 全部 0 次 inventory）。

## 6. 离线、调用成本与历史保护

网络禁用的相关离线验证：**173 passed in 6.40s**，覆盖 V23.2 入口、原 Editor 严格 Patch／合法停止、V23 调度及 Actor Episode／有限重试；新增归档桥接测试确认原输入与失败机制保留。[完整输出](offline_tests.txt)

| 阶段 | 实际请求 | 输入 tokens | 输出 tokens | 总 tokens | 阶段耗时 |
|---|---:|---:|---:|---:|---:|
| Editor（1 次逻辑调用） | 2（1 次长度截断技术重试） | 6,382 | 21,380 | 27,762 | 89.33 s |
| Candidate Actor（7 Episode） | 162（0 重试） | 268,410 | 39,377 | 307,787 | 111.96 s |
| 合计 | **164** | **274,792** | **60,757** | **335,549** | **201.29 s 阶段计时合计** |

Editor 首次 19,575 tokens、第二次 8,187，失败输出亦计入成本；reasoning 共 48,575 tokens，属于输出子集，不重复相加。未知 usage=0，无 Actor 技术停点，162 个动作全部在当步候选中。阶段间包含人工只读检查，首次 Editor 启动至全部 Episode 完成为约 285.11 秒；并行 Episode 的 111.96 秒是阶段墙钟时间，不是七个 Episode 耗时相加。

[总成本](../results/cost.json) · [Editor 成本](../results/editor_cost.json) · [Actor 成本](../results/actor_cost.json) · [Editor 状态](../../../../../artifacts/methods/v23_2/v23_2_response_behavior_001/editor_status.json) · [Episode 状态](../../../../../artifacts/methods/v23_2/v23_2_response_behavior_001/episodes_status.json)

冻结保护的 **11,558 个文件**集合与 SHA-256 在运行前后及最终检查均一致，覆盖 V23 正式训练／Test／Skill／Memory、旧 V23.2 实验和模块源码。所有新响应、失败尝试、实际 Patch、Candidate、Actor 原始响应及轨迹独立归档；逐项验证原始响应哈希、用量、七条初始状态，以及全部 162 个 Actor 消息的原协议重建。[保护核验](../results/protection.json)

## 7. 是否保留候选

**建议保留当前 Prompt 及产物作为待验证研究候选；本次不提供提升为正式默认或进入完整六轮的充分证据。** 它并非只改善自然语言：plate 的搜索与温度操作确实出现局部行为改善。但关键搜索困难没有被稳定解决，成功数与旧 Candidate 相同、低于 Parent；apple/book 覆盖还更窄，creditcard 长扫描仍在。更不能以同样未改变的 u1 的行为进步，单独证明历史响应支持范围 Prompt 的收益。

本实验为一次 Editor 加一次随机 Actor 执行，与历史保存输出比较，没有重复试验或隔离 Editor 表达的对照。结论限于这七条开发材料的观察，不是独立泛化验证，也不是单条 Update 的因果证明。

**已完成并停止。** 未更改任何 Prompt／Effective Plan／Patch，未调用 Diagnosis、Preconditioner、Replay、Memory 或 Gate，未重跑 Parent/旧 Candidate，未使用最终 Test，未发布新 Parent或启动六轮实验。后续是否开展完整实验等待用户决定。
