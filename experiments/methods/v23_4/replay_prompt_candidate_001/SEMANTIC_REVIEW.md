# 候选主 Prompt 001：事实、比较完整性与 Knowledge 可采用性

日期：2026-10-22。审查对象是每轮首次结构合法的原样提案，没有人工改写或语义重采样。所有判断针对冻结模型可见输入；历史缺失状态不能靠完整归档事后补足。以下 M 编号只属于本实验的各轮隔离预览。

**结论：出现了有实质内容的改善，尤其是 R06 对象身份和局部/整体效率的区分，以及 R05 apple 改善的保留；但五条原样提案仍有事实、范围或重要比较缺失问题，不宜直接采用。** 一次输出不能证明候选 Prompt 稳定优于旧版，也不能证明所有要求已被遵循。

## R05

输出为新增 M10、修订 M6 → M11、修订 M8 → M12。

### 明确改善和正确内容

- M11 保留当前 cool apple 的 14→11 步改善，正确描述 Parent 的短循环与 Candidate 到新表面取得 apple；不再把 clean soapbar 的 8→6 称为唯一明确差异。
- 保留 pillow/desklamp 与 pencil/desk 两对各多一步，未再把所有 desklamp 执行称为逐步相同。差异事实正确，但把 pillow 放在搜索条款效应叙述中的范围问题见下。
- 历史两对 cool bread 的正负结果、cool plate 的 38 步成功对 50 步失败及 Candidate 第 49 步取 plate 均可核对。数字和动作在模型可见 trace 或详细窗口中存在。
- M12 的加热 cup 对应 `S1_R04/P1:31`，未把它错写到 R03；pot 的取物、冷却与 Candidate 不操纵 pot 也有历史支持。
- 正确描述 knife 替代 butterknife 仍发生、soapbottle 未被操纵、非法导航没有消失，以及当前 soapbar 和 apple 的精确目标成功行为。

### 阻止原样采用的问题

| 条目 / 问题 | 原文与判断 | 可见事实 |
|---|---|---|
| M10，F05-1：否认实际出现过的回退机会 | “No pair directly exercised the fallback of using a listed direct action when a desired navigation destination was absent” 是过强的全批否定。没有观察到 Candidate 稳定、适当地执行该规则，不等于没有任何 Pair 出现相关行为 | P8:8 的菜单没有 `go to cabinet 3`，有 `open cabinet 3`；Parent 执行后首次得到该柜子的内容。说明这种行为已存在于 Parent，不能算新规则独立收益，但也不能说未观察到。Q8:39 非法导航后 Q8:40 examine 则是另一个低效情境 |
| M10/M12，F05-2：未找到与全局不存在仍混用 | M10 “failing absent-target tasks”；M12 “some absent-target cases”“those absent-target soapbar tasks”。其他句子虽写 “not found”，没有消除这些具体的过强表述 | P8/Q8 均未访问首步菜单可选的 shelf 1；没有全局不存在证明。历史条目中的同类说法也不能直接充当事实 |
| M11，F05-3：范围内外比较未分开 | “It also did not uniformly reduce steps: in an examine-pillow-with-desklamp task ...” 把 pillow 多一步放在该搜索条款没有统一省步的解释中，没有指出此条款不适用 desklamp | Actual Diff 的搜索改动位于 `General Non-Desklamp Retrieval, Cleaning, and Placement`，且限定 no desklamp。P2/Q2 的 5→6 应作为范围外保留行为/探索差异单独说明，不宜作为该搜索条款范围内的反例。这里是范围混用，不断言原文明确宣称了独立因果 |
| M11，F05-4：历史实例描述有歧义 | “in another cool-bread pair with the same room” 未说明 same 相对于哪一侧/哪一对 | R03/P2 的初始场景有 countertop 3、9 个 cabinets；R03/P4 有 diningtable 1、27 个 cabinets，不能说两对是同一房间。若作者只指单个 Pair 内 P/Q 同场景则成立。记录为可误导的歧义，不当作已确定的跨 Pair 身份错误 |

M10 将 P9 的 malformed action 与后续 inventory 的差异写成 possible/local avoidance，强度比直接因果宣称低；但这仍只是同时出现的响应，不能证明 Actor 因合法性预检避免了格式失败。没有把此处额外升级为确定事实错误。

### 比较覆盖与引用

当前 apple 14→11、soapbar 8→6、两项 +1、两个失败案例均进入了 Knowledge，覆盖较上一轮明显更完整。它没有再作“全批全部相同”等未支持的总结，因此未引用 bowl 和两对 mug 的相同执行本身不构成错误；不能要求每条知识变成全批复述。

但 M12 保留精确类别规则的有效能力时，没有讨论当前 P6/Q6 的成功 butterknife 对照：两侧在同时存在 knife 的表面取得正确 butterknife 并成功。这比单纯引用 soapbar/apple 更直接地限制“knife/butterknife 类别区分不可靠”的范围，属于值得保留的重要同类别比较，现有条目没有引用 P6/Q6。

M10 自己未引用 P8:8，不过整份新 Memory 中 M12 引用 P8:6，±2 窗口使 P8:8 的观察和菜单仍在未来视图中。不能误报为该事实已从全部未来 Memory 消失；问题首先在于当前 Knowledge 没有据它修正否定判断。

## R06

输出为修订 M10 → M12（搜索）、M7 → M13（温变）。编号顺序与上一轮新视图实验不同，应按 revises 比较关系。

### 明确改善和正确内容

- 当前 cool tomato 身份正确，不再写成 bread；18→10 的总步数也正确。
- 冷 plate 既写出 Parent 开门、Candidate 关闭状态直接冷却，也保留 Candidate 额外 cabinet 探索使总步数为 9 而非 8。这次不是靠省略整项结果避开旧错误，而是真正保留了局部收益与整体开销的不同方向；未明确数字分解 +2/−1 不算错误。
- 当前 heat tomato 的 39→8、8→7，以及历史 cool pot、hot apple、heat egg、hot potato、heat tomato 的总步数均与记录一致。
- 两条均把当前 heat apple 写为未找到，而非确定全局不存在；搜索条目末尾 “absent or not discovered” 仍偏泛，但没有像上轮那样明确断言本次 apple 不存在。
- 搜索条目保留 book 修复前仍长时间循环、creditcard 起点/搜索顺序不固定和联合编辑限制。未把一次成功等同于可靠防循环。
- 相关引用覆盖本轮全部 14 条执行，且 Q1 的 cabinet 探索细节进入未来完整 1–9 步窗口，优于上轮仅保留 4–9 的状态窗口。

### 阻止原样采用的问题

| 条目 / 问题 | 原文与判断 | 可见事实 |
|---|---|---|
| M12，F06-1：空与没有目标混用 | “already-open empty drawers, shelves, and the desk” 将 shelf 等概括为空 | Q6:31 shelf 1 上有 box/houseplant/pencils；Q6:32 shelf 2 有 alarmclock/pen，只是没有 book。应按可见内容及目标匹配判断，不能把无目标改写为物理空；未来窗口也保留这些状态 |
| M13，F06-2：遗漏直接限制温变收益解释的零差异比较 | 写 Candidate cool tomato 10 对 Parent 18，并归入 “current pairs repeat the pattern”，最终概括 “robust local reduction”；末尾“总步数不全归温变”未具体交代该对的温变行为相同 | P2:15 和 Q2:7 都直接冷却已持有 tomato，两侧取得 tomato 后的动作序列完全相同。八步差异发生在搜索；该对保留的是正确温变能力，并未观察到新增温变局部节省。缺少这项比较，使结论对“取得目标”条件的概括偏宽 |
| M13，F06-3：历史重要退化被压缩为未触发 | 历史 heat plate 与 hot mug 一起概括为 target could not be located、no opportunity、step-limit failure，未说明 heat plate 的两侧结果不同 | `S1_R04/P2` 第 4 步取得 plate，第 11 步加热，13 步成功；Q2 未取 plate，50 步失败。原 M7 明确保留了 13 成功对 50 失败。本次仍引用双方，却在替换 Knowledge 中丢失这个重要比较。应明确未触发只指 Candidate；也不能反向把它当作温变规则直接导致的退化 |

历史五个温变成功例的总步数真实，不意味着差额全部由省去家电操作构成；例如历史 cool pot 的 Parent 主要是在冷却前多一次开门，并非每个历史例都有插入/开关循环。将它们统一概括成一种强度相同的机制，应保留各自实际差异。这是概括边界问题，不能用历史旧 Knowledge 的 “robust” 一词自动豁免复核。

## 原样采用判断

| 隔离条目 | 判断依据 | 状态 |
|---|---|---|
| R05 M10 | 全批否定回退机会与实际 P8:8 冲突，并有 absent-target 表述 | 暂不采用 |
| R05 M11 | 重要改善被保留，但 desklamp 范围未区分、历史场景表述歧义 | 暂不采用 |
| R05 M12 | 多项条件性遵循事实成立，但未找到/不存在混用，相关成功 butterknife 比较缺失 | 暂不采用 |
| R06 M12 | 主要搜索比较成立，但将非空无目标表面概括为空 | 暂不采用 |
| R06 M13 | 温变事实与 plate 局部/整体解释改善，但零局部收益对照和历史退化保留不充分 | 暂不采用 |

“暂不采用”不等于整条知识没有价值，也不是结构错误。没有为得到更好文字追加调用、人工补引用或修改结果。候选 Prompt 原文、所有原始输出和预览均保留，供下一步判断如何提高已有要求的实际遵循。

## 复核材料

- [冻结候选主 Prompt](candidate_prompt.md)、[比较不变量](config/comparison.json)、[事实断言数据](FACT_CHECKS.json)、[只读事实脚本](review_facts.py)。
- R05：[原始提案](runs/R05_replay/attempt_001/parsed.json)、[模型输入](../../../../artifacts/methods/v23_4/replay_prompt_candidate_001/config/R05/model_input.json)、[Memory 审计](cases/R05/results/MEMORY_AUDIT.json)。
- R06：[原始提案](runs/R06_replay/attempt_001/parsed.json)、[模型输入](../../../../artifacts/methods/v23_4/replay_prompt_candidate_001/config/R06/model_input.json)、[Memory 审计](cases/R06/results/MEMORY_AUDIT.json)。
