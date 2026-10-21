# Preconditioner 方法对照

**已获得 A2/B7 两份合法 Effective Plan。** A 首次失败、第二次有效；B 前六次分别因 checks 多余字段、from_note 多余字段、理由引用、理由引用、Diff 原文不匹配、理由引用失败，第七次首次通过原校验。所有输出保留、无人工修补。A 两次与 B 七次生成机会不等，不能当作严格一次采样对照；首次结果两组均失败，恢复后方案质量另行报告。

共同输入通过 generation_input_audit.json 核查：实际 user messages 完全一致，模型参数相同；A 重试与 A 首次正文完全相同，B 七次正文完全相同。Original、Parent、选定 P1/P3/P6、Memory v3 未改变，无纠错提示。系统 Prompt 差异是方法整体干预，不能把差异只归因于 Unified Diff。

| 生成 | 决定/修改 | 原校验结果 | 后续 |
|---|---|---|---|
| A1 | ready，重写 u1/u2 | reason 中 P3/P6 被当历史引用 | 保留失败 |
| A2 | ready，重写 u1/u2 | 有效 Effective | 一次 Editor、六例 Replay |
| B1 | ready，u1 Keep、u2 Patch | Adjustment 多出 checks | 保留失败 |
| B2 | ready，u1/u2 Patch | Adjustment 多出 from_note | 保留失败 |
| B3 | ready，u1 Keep、u2 Patch | 顶层 reason 中 15/P1:20、28/P3:48 被当历史引用 | 无 Effective/Editor/Replay |
| B4 | ready，u1/u2 Patch、替换 Checks | 顶层 reason 中 P3/P6 被当历史引用 | 无 Effective/Editor/Replay |
| B5 | ready，u1/u2 Patch、替换 Checks | 删除行漏掉 Original 列表符号，定位失败 | 无 Effective/Editor/Replay |
| B6 | ready，u1 Keep、u2 Patch | 顶层理由斜杠连写被匹配为历史引用 | 无 Effective/Editor/Replay |
| B7 | ready，u1 Keep、u2 Patch | 原 Patch、完整编译和严格重载通过 | 一次 Editor、六例 Replay |

B3/B4/B6 Patch 原样可通过现有 Patch 引擎，已记录诊断验证；完整编译仍失败。不得把局部 Patch 成功当作方法输出有效。失败不等于 Keep、need_evidence 或策略失败。

## 独立语义评价

A1、A2 与 B1/B2/B3/B4/B5/B6/B7 分别见对应 *_EVALUATION.md；以下比较只限实际文本，不把非法输出当作已执行方法。

A2 修正“所有候选都打开”为只打开关闭容器，显式读取当前候选和近两步信息；新增针对近期重复的不同类别切换策略。当前循环和未覆盖位置提供探索动机，M3/M6 提供旧编辑混合响应线索。但把 Original “all reachable candidate receptacles” 改成 “every distinct receptacle type ... inspected once”，将位置覆盖改成类别覆盖的首轮结束标准；并把不同实例探索收紧为不同类别。二者并非消除不可见历史状态的必需配套，M6 同类遗漏反而限制其依据。它仍要求知道哪些类别已检查，执行条件并未完全局部化。保留精确目标、数量及必要处理/交付的 Goal/Checks，不代表实际 Skill 自动完整实现这些能力。

A2 当前事实存在错误：理由把 P3:6/15/19 说成到 fridge 未开，实际是 cabinet 3 的 open/go 和 cabinet 6 的 go，P3 未到 fridge；提到 P3 countertop 2/3、shelves 和 P6 tvstand 作为漏访候选，但当前初始菜单没有这些位置。见 runs/A_retry_001/current_evidence_fact_audit.json。部分漏访仍真实存在（例如 P3 fridge/diningtable、P6 sidetable 3/sofa/armchairs），不能因为部分动机正确而忽略错误依据。

B3 明确 Keep u1，仅把 u2 前两行收窄成当前空位及近期历史触发，允许不同类别或实例，保留第三行和原位置覆盖终点。其局部修改和依据联系较准确，并有可检验探索；未增加 A2 的类别覆盖终点。但是保留 u1 全局覆盖/打开全部候选及 u2 的 uninspected 条件，仍存在未修正问题。B1/B2 各自还有半预算阈值/类别强排序等额外承诺，不能选取 B3 较好的提案掩盖此前输出。

## 历史响应与归因边界

M3 的一般非灯具流程联合编辑曾伴随扩大覆盖、精确目标处理和交付成功，也残留循环；M6 混合响应含覆盖改善、同类实例遗漏和重复。它们支持重新考虑搜索调度、限制“原反重复条款必能解决”的推断，不能证明某种新换类排序或固定阈值最优。当前 Parent 已足以支持减少循环与扩展漏访，历史提供额外限制与旧策略未稳定奏效的线索。

两组真实理由引用了这些编辑后响应，但没有无 Memory 消融，不能确认历史的因果增量。模型把观察到的循环/遗漏归因为不能跟踪全局访问集合，仍是解释假设，Actor 协议限制本身可核查，失败唯一原因不可确认。

前六次阶段结论：只有 A 能进入行为评估，B3 等局部提案不是有效方案。第七次授权后首次获得 B 合法 Effective，以下新增评价与最终 Replay 报告取代“B 整体无有效输出”的运行状态结论，前六次失败仍保留。

## 第四次授权追加的语义结果

B4 提出强制容器/非容器交替与两次近期观察触发换类，探索具体但无证据证明强制顺序合理。它把初始不可见扩展为尚未取得、将 inspected 改成 visited，仍要求全局已访状态；按 cabinet 名称归为关闭容器与当前开放表面反馈不符。P3:48 被说成 empty，实有 dishsponge 2；缺目标不等于空。详见 B_FOURTH_ATTEMPT_EVALUATION.md。四次提案并非一致地减少附带承诺，不能挑较窄的 B3 作为方法代表。

## 第五次授权追加

B5 的真实 Diff 无法原样应用，尚未到完整编译。提案尝试早期表面搜索及两步窗口触发，但仍保留全局未访问集合、弱化频率主张不实质、两次同类后必须换类等问题，见 B_FIFTH_ATTEMPT_EVALUATION.md。不能将定位失败修补后当成原模型有效输出。

## 第六次授权追加

B6 仅改 u2，局部避访/A-B-A 探索有明确动机，但当前或近期出现过任意位置一律避开可能过强，且“当前列表识别剩余未测位置”仍无法提供全局已访状态。Patch 原样可应用，理由引用被原编译器拒绝；见 B_SIXTH_ATTEMPT_EVALUATION.md。

## 第七次首个有效方案：独立评价与 A2 比较

B7 保留 u1，调整 u2 第一/三行，第二行原样；当前/前一观察触发、备选存在时禁止回访、允许未检查的关闭容器作为跳出选择。完整独立 Replay 前评价见 B_SEVENTH_ATTEMPT_EVALUATION.md。A2 是自由替换，B7 是完整通过的真实 Patch；两组都提出具体策略，B7 并非全部 Keep。

| 维度 | A2 | B7 |
|---|---|---|
| 目标/方向 | 重构 u1/u2，强调换类别 | u1 Keep，改 u2 局部触发与退出选择 |
| 完成边界 | 把位置覆盖改成类别覆盖的首轮终点 | 保留 Original 位置级检查与多目标数量 |
| 关联边界 | 必须不同类别可能排除同类新实例 | 允许未检查关闭容器；原 c1 却仍偏向换表面/设备 |
| 未解决要求 | 类别状态仍非局部可知 | untried/未见内容/完整首轮仍依赖全局状态；u1 打开所有候选未修 |
| 当前事实 | P3 fridge/不存在位置等错误 | P3:48 被误称空，实际有非目标 dishsponge |
| 历史使用 | M3/M6 调度动机，但终点/排序过推 | M3/M6/M9 旧条款混合响应，备选防非法动作因果仍未证实 |
| 结构结果 | 第二次首次有效 | 第七次首次有效 |

B7 相对 A2 避免了一个明确的附带变化（类别一次首轮终点），也保留同类实例探索选择，具有更合适边界的局部线索；但条件局部化不完整、Keep 遗留问题和 Checks 张力仍在。不能据此宣称整体策略更优或 Memory 有因果增量，更不能忽略六次结构失败的成本。实际 Skill/行为另见 EDITOR_REPORT.md 和 REPLAY_REPORT.md。
