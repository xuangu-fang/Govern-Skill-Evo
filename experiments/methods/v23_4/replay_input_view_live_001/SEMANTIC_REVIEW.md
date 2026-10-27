# R05 / R06 新输入视图 Replay 语义核对

日期：2026-10-22。对象为各轮首次结构合法的原始输出；没有人工改写提案、语义重采样或发布正式 Memory。下面的 M 编号仅指本实验各自隔离预览，与旧实验同名编号不可混用。

**结论：新视图可运行、输入 token 明显减少，但四条原样提案仍不宜直接采用。两轮均保留了缺乏依据的“目标不存在”判断，并出现其他事实概括错误。**

## R05：新增 M10，修订 M8 → M11

### 保留或改善的内容

- M10 正确识别实际 Diff 的三项改动及范围：独立的 Admissible Actions、non-desklamp 搜索、精确类别要求；没有把未实施的 Plan 当作事实。
- 正确记录两组均 8/10、两个任务均到 50 步上限；正确识别非法导航仍发生、knife 替代 butterknife 仍发生，以及 soapbottle/spraybottle 未被操纵。
- M11 将 R03 “Parent took a cup” 与 R04 “Parent took cup 2 and heated it” 分开。模型可见的 R03/P10 完整动作序列没有 heat；R04/P1:31 为 `heat cup 2 with microwave 1`。相关取物和加热状态在输入详细窗口中可见。本次没有重复旧输出的跨轮加热误写。
- 本次没有把 Q2 的 desklamp 绕行归因于非 desklamp 搜索条款；它只讨论适用范围内的 Q5 桌面搜索。旧错误未重复，但本次没有充分讨论 Q2，因此不能称为已完成该案例的正确归因。
- 明确保留共同编辑的归因限制；P9 的格式失败没有被轻率当作新条款收益。

### 阻止直接采用的问题

| 问题 | 原文定位 | 模型实际可见的反证或证据边界 |
|---|---|---|
| F05-1：将未找到推为全局不存在 | M10 “two tasks whose exact target was absent”“failed because no soapbar existed”；M11 “the exact soapbar was absent” | P8/Q8 完整轨迹都没访问 shelf 1，但两侧首步菜单均有 `go to shelf 1`。只能说在执行预算和已访问位置中未找到，不能断言不存在；历史 M8 也含类似过强措辞，不能以旧 knowledge 代替事实 |
| F05-2：遗漏明确效率差异，却作排他性总结 | M10 “The only clear step difference was in a clean-soapbar task” | pairs 已直接给出 P10/Q10 为 14→11，P2/Q2 与 P5/Q5 均为 5→6。P10 在第 9 步取 apple，Q10 在第 6 步取 apple；取物后的五个动作完全相同，三步差异来自此前搜索。没有充分依据把 soapbar 称为唯一明确差异 |
| F05-3：过度概括 desklamp 配对相同 | M10 “the simple desklamp-inspection ... pairs were step-for-step identical” | Bowl 的 P1/Q1 相同，但 pillow 的 P2/Q2 为 5→6，Q2 先去 desk 再返回 bed 搜索。若只指 P1，必须明确限定，不能把两项 desklamp 任务一概描述为逐步相同 |

这些错误不能用当前轨迹压缩来解释：当前完整动作、状态和结果原样保留，pairs 中已有确定性步数。输入格式说明也已明确禁止由未找到推断全局缺失，但本次未可靠遵循。

### 后续 evidence 覆盖

M10 的当前证据比旧提案更广，包含 P5/Q5、P9/Q9 等。但两条新条目都没有引用本轮 P2/Q2、P3/Q3、P4/Q4。后续压缩 Memory 不能仅凭本轮证据集合独立复核十对任务的全局总结与所有“逐步相同”判断。原始完整归档仍保存，这不是事实被删除，也不是结构失败；是 knowledge 的陈述范围超出其随附来源覆盖。

## R06：修订 M7 → M12，M10 → M13

### 保留或改善的内容

- M12 正确描述实际温变条款和持有精确目标、动作可用时的触发条件。P4:36 晚加热与 Q4:6 直接加热、39→8 步及 P5/Q5 的开门差异均可核对；它明确不把总差额全部归因于温变。
- 未再写 P4/Q4 在同一步取得 tomato。但也没有明确写出实际第 3/4 步，只能记为旧错误未重复。
- 冷 plate 描述改为 Parent 开门后冷却、Candidate 关闭冰箱直接冷却，没有重复“局部行为未省步”的判断。不过本次省略了整项 8→9 的比较，也没有完整表达“搜索多两步、温变少一步、净增一步”；不能宣称已验证模型掌握了完整分解。
- M13 更明确承认书任务 Candidate 仍长时间循环才在 Q6:33 到 bed，防循环条款并非可靠遵循；信用卡 24→9 可能来自起点/搜索顺序，并非防循环已生效。这些边界比旧输出更清楚。

### 阻止直接采用的问题

| 问题 | 原文定位 | 模型实际可见的反证或证据边界 |
|---|---|---|
| F06-1：当前任务对象误写 | M13 “In a cool-bread pair ... taking the bread ... 18 ... 10 steps” | P2/Q2 的 task 都是 `put a cool tomato in microwave.`；P2:13/Q2:5 取 tomato 1，P2:15/Q2:7 冷却 tomato 1，最后放入 microwave。所引 Q2:4 的下一步、完整轨迹和配对汇总均支持 tomato，没有 bread。这是新输出的事实错误，不是历史 Pair 缺失 |
| F06-2：无依据的全局不存在 | M12 “the target was absent”；M13 “did not overcome an absent target” | P3/Q3 未取得 apple，均 50 步失败；但菜单中大量候选位置没有访问，例如 cabinet 3–10、diningtable 1/2。可确认未取得目标、温变没有触发，不能确认 apple 全局不存在 |
| F06-3：物理空与无目标混用 | M13 “already-open empty drawers/shelves” | Q6:31 的 shelf 1 有 box/houseplant/pencils，Q6:32 的 shelf 2 有 alarmclock/pen。这些位置没有所求 book，不等于 empty；该措辞应限定为没有目标的已访问位置。属于条件描述精度问题，严重性低于对象误写 |

M12 的“associated with ... fewer steps”也需要保留局部/总体限制。冷 plate 是局部温变省一步、总体多一步，不能把这句话外推为每个已取得目标的任务总步数都下降。本次较旧输出少了一项明确错误，但并未形成全面准确的效率解释。

### 后续 evidence 覆盖

两条提案合计覆盖本轮全部 14 条执行。温变关键状态和动作窗口保留；Q1 的新详细窗口为 4–9，额外 cabinet 搜索的 1–2 步仍仅保留动作/反馈序列。Q3 的新详细窗口仅为 48–50，中途柜子内容不能由这些末尾状态反推。Q6 的详细窗口包含 31–36，因此 shelf 非空的反证在未来 v3 视图中仍可见。

本次没有更改 evidence、知识文本或动态扩展窗口。完整动作序列可支持动作顺序与有无某动作，不能替代缺失步骤的观察/菜单。

## 对新机制的判断

本次证明输入视图可以通过真实接口，原样提案能够经过引用校验、隔离提交、重载、Preconditioner 投影和未来 Replay Pair 恢复。模型也出现了部分更准确的历史分轮与行为边界描述。

它没有证明知识可靠性已达到可自动采用的程度。两轮都是每种视图一次输出，格式说明、信息组织和历史压缩一起变化，不能分离各项改动贡献；输出内容和覆盖也不同，不能用“没有重复某句错误”直接计算准确率提高。

建议保留当前输入机制和所有原始结果，将本轮偏差作为下一步设计依据；本轮不追加模型调用，不修写 Memory 后冒充模型原输出，不新增审核 Agent。

## 可复核材料

- [事实核对数据](FACT_CHECKS.json)；[只读核对脚本](review_facts.py)。断言仅验证具体事实，不自动判定自然语言知识正确。
- R05：[原始提案](runs/R05_replay/attempt_001/parsed.json)、[模型可见输入](../../../../artifacts/methods/v23_4/replay_input_view_live_001/config/R05/model_input.json)、[Memory 审计](cases/R05/results/MEMORY_AUDIT.json)。
- R06：[原始提案](runs/R06_replay/attempt_001/parsed.json)、[模型可见输入](../../../../artifacts/methods/v23_4/replay_input_view_live_001/config/R06/model_input.json)、[Memory 审计](cases/R06/results/MEMORY_AUDIT.json)。
