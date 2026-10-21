# Preconditioner 方法对照

**未获得完整有效 A/B 对照。** A 首次因引用格式失败，经一次授权追加后成功；B 六次分别因多余字段 checks、多余字段 from_note、理由引用格式、再次理由引用格式、Diff 删除文本不匹配、再次理由引用格式被原校验拒绝。所有真实输出保留，无手动修补。用户授权改变了原一次生成预算：A 两次、B 六次机会不等，不能据本轮比较稳定方法优越性。

共同输入通过 generation_input_audit.json 核查：实际 user messages 完全一致，模型参数相同；A 重试与 A 首次正文完全相同，B 六次正文完全相同。Original、Parent、选定 P1/P3/P6、Memory v3 未改变，无纠错提示。系统 Prompt 差异是方法整体干预，不能把差异只归因于 Unified Diff。

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

B3/B4/B6 Patch 原样可通过现有 Patch 引擎，已记录诊断验证；完整编译仍失败。不得把局部 Patch 成功当作方法输出有效。失败不等于 Keep、need_evidence 或策略失败。

## 独立语义评价

A1、A2 与 B1/B2/B3/B4/B5/B6 分别见对应 *_EVALUATION.md；以下比较只限实际文本，不把非法输出当作已执行方法。

A2 修正“所有候选都打开”为只打开关闭容器，显式读取当前候选和近两步信息；新增针对近期重复的不同类别切换策略。当前循环和未覆盖位置提供探索动机，M3/M6 提供旧编辑混合响应线索。但把 Original “all reachable candidate receptacles” 改成 “every distinct receptacle type ... inspected once”，将位置覆盖改成类别覆盖的首轮结束标准；并把不同实例探索收紧为不同类别。二者并非消除不可见历史状态的必需配套，M6 同类遗漏反而限制其依据。它仍要求知道哪些类别已检查，执行条件并未完全局部化。保留精确目标、数量及必要处理/交付的 Goal/Checks，不代表实际 Skill 自动完整实现这些能力。

A2 当前事实存在错误：理由把 P3:6/15/19 说成到 fridge 未开，实际是 cabinet 3 的 open/go 和 cabinet 6 的 go，P3 未到 fridge；提到 P3 countertop 2/3、shelves 和 P6 tvstand 作为漏访候选，但当前初始菜单没有这些位置。见 runs/A_retry_001/current_evidence_fact_audit.json。部分漏访仍真实存在（例如 P3 fridge/diningtable、P6 sidetable 3/sofa/armchairs），不能因为部分动机正确而忽略错误依据。

B3 明确 Keep u1，仅把 u2 前两行收窄成当前空位及近期历史触发，允许不同类别或实例，保留第三行和原位置覆盖终点。其局部修改和依据联系较准确，并有可检验探索；未增加 A2 的类别覆盖终点。但是保留 u1 全局覆盖/打开全部候选及 u2 的 uninspected 条件，仍存在未修正问题。B1/B2 各自还有半预算阈值/类别强排序等额外承诺，不能选取 B3 较好的提案掩盖此前输出。

## 历史响应与归因边界

M3 的一般非灯具流程联合编辑曾伴随扩大覆盖、精确目标处理和交付成功，也残留循环；M6 混合响应含覆盖改善、同类实例遗漏和重复。它们支持重新考虑搜索调度、限制“原反重复条款必能解决”的推断，不能证明某种新换类排序或固定阈值最优。当前 Parent 已足以支持减少循环与扩展漏访，历史提供额外限制与旧策略未稳定奏效的线索。

两组真实理由引用了这些编辑后响应，但没有无 Memory 消融，不能确认历史的因果增量。模型把观察到的循环/遗漏归因为不能跟踪全局访问集合，仍是解释假设，Actor 协议限制本身可核查，失败唯一原因不可确认。

更新粒度：B3 在提案层面定位 u2 两行，A2 整段重构；此差异不是质量指标本身。策略质量：B3 保留原位置覆盖边界的局部线索值得后续检验，但 B 整体契约失败、样本机会不等，不能宣布 B 优于 A。行为收益：本轮只能评估 A 对 Parent，不能比较 B。

## 第四次授权追加的语义结果

B4 提出强制容器/非容器交替与两次近期观察触发换类，探索具体但无证据证明强制顺序合理。它把初始不可见扩展为尚未取得、将 inspected 改成 visited，仍要求全局已访状态；按 cabinet 名称归为关闭容器与当前开放表面反馈不符。P3:48 被说成 empty，实有 dishsponge 2；缺目标不等于空。详见 B_FOURTH_ATTEMPT_EVALUATION.md。四次提案并非一致地减少附带承诺，不能挑较窄的 B3 作为方法代表。

## 第五次授权追加

B5 的真实 Diff 无法原样应用，尚未到完整编译。提案尝试早期表面搜索及两步窗口触发，但仍保留全局未访问集合、弱化频率主张不实质、两次同类后必须换类等问题，见 B_FIFTH_ATTEMPT_EVALUATION.md。不能将定位失败修补后当成原模型有效输出。

## 第六次授权追加

B6 仅改 u2，局部避访/A-B-A 探索有明确动机，但当前或近期出现过任意位置一律避开可能过强，且“当前列表识别剩余未测位置”仍无法提供全局已访状态。Patch 原样可应用，理由引用被原编译器拒绝；见 B_SIXTH_ATTEMPT_EVALUATION.md。
