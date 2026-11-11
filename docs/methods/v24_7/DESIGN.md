# ALFWorld v24.7 设计稿：从训练轨迹中学出 Actor 能持续执行的搜索规则

v24.7 是本方案的建议版本号。实验从 v24.6 使用的原始 Skill 和空 Memory 开始。目标是让四个模块自己发现、表达、检验并保留一条搜索规则：Actor 在寻找目标时，仅凭当前观察、动作菜单和最近两步，也能在一次搜索落空后继续推进；一旦找到目标，又能及时转入取物、处理和交付。交付成果是第六轮发布的最终 Skill。

## 一、实验依据与判断标准

| 134 道相同 Test | 成功题数 | 环境动作总数 | 全程未拿起任何物体的题数 |
|---|---:|---:|---:|
| v24.6 原版 | 104 | 2,919 | 22 |
| v24.6 换入 v24.1 搜索段落 | 118 | 1,919 | 9 |
| 完整 v24.1 复跑 | 119 | 1,915 | 9 |

混合版只替换通用搜索原则并插入它引用的搜索段落，20 题由败转胜，6 题由胜转败。单次实验支持把搜索段落作为优化对象；它无法区分起点选择、连续推进、退出条件和文字组织各自的贡献。118 和 119 是对照成绩。历史 Skill、上述 Test 轨迹和分数只用于设计复盘与最终比较。正式训练的证据来自原有 57 道优化题。[换段实验](../../../artifacts/methods/v24_6/v24_6_alfworld_v24_1_search_swap_test134_20261108_012501/summary.json) · [v24.6 原版](../../../artifacts/methods/v24_6/v24_6_alfworld_20261108_000609_test134/summary.json) · [v24.1 复跑](../../../experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/results/v24_1_alfworld_retest134_20261107_231217/summary.json)

一次训练检验两个问题。**方法上**，能否追溯一条由本次训练证据产生、实际进入最终 Skill 的规则，并从 Actor 当时能看到的菜单解释它怎样改变下一步。**结果上**，先看 134 题成功数相对 104 的变化，再看搜索失败是否减少。步数是附加收益，以双方都成功的同题配对比较；总步数同时列出，避免把少做任务误判为更高效。

## 二、一轮如何运行

沿用 v24.6 的顺序：Parent 执行本批任务，Diagnosis 提案，Preconditioner 审核，Editor 写入候选，Candidate 在同批独立执行，Replay 对符合条件的配对归因，Gate 逐 ID 选择并发布。下一轮从上轮实际发布的 Skill 开始。第一版的算法改动集中在四份英文系统 prompt；版本注册、合同和入口负责隔离新实验。动态输入、JSON 字段、Memory 和每批 Actor 执行预算沿用 v24.6。[训练入口](../../../src/skill_evolution/v24_6/campaign.py) · [模块交接](../../../src/skill_evolution/v24_2/method.py)

### Diagnosis：把成功轨迹当作可以学习的动作序列

**改动位置**：在现有 prompt 分析成功轨迹的部分加入“发现连续决策”，在形成 Original Update 前加入“回到失败现场检验”。目前模型善于发现绕路；新要求让它也检查那些一路推进、看起来平淡的成功片段。

1. 找到失败轨迹中任务不再推进的决策。在同批轨迹里寻找面临相近选择、后来继续取得进展的片段。有合适证据时，沿着成功路线再看一次：第一次动作没有找到目标以后，Actor 凭什么还能选出下一步？
2. 比较 Parent 在这个菜单里已经规定了什么、还允许哪些竞争动作。若两个位置都符合“去没查过的地方”，就检查成功轨迹有没有揭示一个 Actor 当时可见、可以反复使用的选择依据。后来发现了物体，只能说明执行结果，不能当作先验线索。
3. 在失败轨迹的具体菜单中应用这个选择依据，写出会提高哪个动作的优先级、哪种观察会令它切换或退出。若只支持某一阶段，就限定范围。若提案适用于反复选择，尽量引用展示其持续推进或失效边界的决策点。

**交接**：解释放在 `reason`，执行依据放在 `basis`，Actor 真正需要的行为放在 `updates[].text`。特别注意把用来确定规则边界的成功轨迹引用进 `basis`，Preconditioner 只会收到被引用的完整轨迹。独立可采纳的行为分别给 ID；同一行为的触发与退出放在一起。每轮提案数由证据决定，保留 `no_change`。

建议加入 prompt 的核心措辞：

> A successful sequence can teach a missing decision procedure even when it contains no wasted action. When the evidence permits, follow the sequence through an unsuccessful probe and the following choice. Identify a cue available at both decisions. Apply the proposed preference to a concrete competing choice in another supplied run, and cite the steps that determine its scope.

### Preconditioner：在第一次触发和中后段各尝试应用一次

**改动位置**：在现有“找到第一个会改变的动作”之后，增加一次局部可执行性检查。只对声称要反复使用的规则检查第二个点。取物或交付等一次性规则仍按原有边界审核。

从引用轨迹里取一个第一次触发点，再取一个继续搜索、切换或取得进展后的点。逐点只用目标、当前观察、菜单和最近两组观察/动作来回答：**Parent 会偏向什么？提案改变什么？如果仍有多个合理动作，它能否缩小选择范围？这个判断需要的事实当时还看得到吗？** 有时多种动作同样合理，规则只需给出有证据的偏好。缺少第二个可用点时，将证据范围说清楚，不能凭缺少样本自动撤回。

| 决定 | 何时使用 |
|---|---|
| `KEEP` | 在适用阶段确实改变可见菜单中的选择；持续使用所需的线索可见，已有成功路线和阶段转换仍成立。 |
| `REPLACE` | 行为目的有依据，但依赖完整访问清单、不可见计数或含糊优先级。当前证据支持用局部线索表达同一目的，或支持收窄适用时机。改写后的完整规则放入 `text`。 |
| `WITHDRAW` | Parent 在相同条件下已经给出同一优先级，或提案所需信息不可见且缺乏同目的、可执行的修正。共享“避免循环”这个目标，本身不足以判定两条规则等价。 |

用成功路线核对退出条件。例如需要两件物体时，第一次取物应当暂时结束搜索并推进交付；已知第二件的位置和仍需重新寻找是两种不同情形。只有提案涉及这些决策时才把相应条件写入有效文本。Memory 用于查相似的触发、退出与归因边界；历史的 `Defer` 不能单独证明相同目的的另一种写法无效。[R05 的撤回理由](../../../artifacts/methods/v24_6/v24_6_alfworld_20261108_000609/rounds/R05/preconditioner/result.json) · [R06 的改写理由](../../../artifacts/methods/v24_6/v24_6_alfworld_20261108_000609/rounds/R06/preconditioner/result.json)

建议加入 prompt 的核心措辞：

> For a recurring preference, also try applying it at a later supplied decision, after the first opportunity has passed. Reconstruct only the Actor-visible context at that point. Explain which available choice the instruction favors and which visible cue supports it. If the proposal relies on unavailable history, look for a supported local reformulation within the same purpose.

### Editor：把有效规则写到实际作决定的位置

**改动位置**：在现有“Write the change where the Actor must choose”部分加入连续规则的组织方式。Editor 收到的是 Parent 和有效 Plan。决定搜索次序的依据必须已经进入有效 Update 的 `text`。

对于覆盖多个连续动作的 update，可以用一个简短的阶段段落表达，在现有通用原则中给出入口。按有效文本实际规定的顺序写出进入条件、下一动作的偏好、一次落空后怎样继续，以及什么变化使任务进入下一阶段。简单的局部动作仍适合直接改原句。段落在多处被引用时，用同一 ID 的独立补丁包含引用和正文，确保单独选中该 ID 也能应用。

编写后做一次语义检查：新旧指令比较的是哪两个选项？例如“新容器优先于已经查过的表面”只规定了新、旧位置之间的优先级；“新容器与新表面谁先”是另一个选择。Plan 明确授权改变后者时，在同一处说明哪条规则生效。Plan 没有授权时，沿用 Parent 对该情形的表述。保留既有 exact-patch、空补丁、阻塞与逐 ID 组合合同。[Editor 合同](../../../src/skill_evolution/v24_6/prompts/editor.md)

建议加入 prompt 的核心措辞：

> When an effective update governs a sequence of decisions, present the sequence where the Actor chooses its next action. A short phase-specific passage may be clearer than a long general principle. Preserve the exact alternatives being compared, the supported continuation after an unsuccessful action, and the specified exit. Introduce only behavior authorized by the effective text.

### Replay：区分“改变了一个动作”和“足以解释整题结果”

**改动位置**：在现有“Follow the choice through the recorded actions”之后，补充阶段边界和竞争解释。只处理程序已筛出的配对，沿用原来的事件方向和步数。

每个事件按三件事实撰写原有的 `knowledge.text`：① 在什么可见条件下，哪条实际 patch 改变了 Parent/Candidate 的动作偏好；② 相关动作在任务进度上造成了什么可见差异；③ 补丁何时应退出，以及此后的偏离是否仍可由它解释。既要追踪失去的进展，也要追踪成功案例里可能碰巧找到目标的情形。能够从两侧执行解释成败或显著步差时关联 ID；中间缺一环或多个补丁无法区分时，记录事实和缺口，使用现有的 `null`。

R03 的 `train:0025` 可作为审阅例：早查餐桌与新增优先级吻合，随后一再返回已查餐桌却超出“一次检查”的范围。Replay 需要解释后续延误与补丁的联系。同样，早查餐桌后恰好成功的题也要经过这项检查。这个例子的验收点是对称地解释证据，具体投哪个 ID 由本次轨迹决定。[R03 原归因](../../../artifacts/methods/v24_6/v24_6_alfworld_20261108_000609/rounds/R03/replay/result.json)

建议加入 prompt 的核心措辞：

> Mark the point where the changed preference should cease to apply. If decisive progress or delay occurs later, explain the observed link to the earlier choice. When the record supports a local change but leaves its connection to the scored outcome unresolved, preserve the event and record the missing link using the existing null attribution. Apply the same standard to gains and losses.

## 三、Gate、Memory 与跨轮保留

复用 v24.6 的逐 ID 计票。只有成功收益票时 `Retain`，只有成功退步票时 `Reject`，两者同时出现时 `Defer`。没有成败票时，至少一票效率增益且零票效率损失才 `Retain`。效率票要求双方成功且步差至少 10。未归因事件留在 Memory，对各 ID 计零票。实际发布的文本由所保留的补丁重新应用到 Parent 得到。[Gate 实现](../../../src/skill_evolution/v24_6/gate.py)

“保留一套规则”要检查到最后一轮。某条规则本轮 `Retain` 后会成为下一轮 Parent 的一部分。后续 update 若修改同一段，Preconditioner 核对它改变了原有规则的哪个选择；Editor 在修改范围之外保留有效的继续和退出条件。复盘时逐轮对照 `selected.md` 和 `publication.json`，检查最终文本还能否指导同类决策。仅在某一轮得到 `Retain` 不能代替这项检查。

## 四、落地与一次性验证

1. **建立新版本。** 从 v24.6 的四份完整 prompt 派生 v24.7，在对应位置合并上述指令，保留 Editor 内嵌的三段 Actor 模板以及四份 JSON 输出契约。使用独立版本标识、prompt 路径和训练目录，合同冻结实际加载的四份 prompt 与复用的 Gate。现有 v24.6 结果可继续复核。
2. **离线核对。** 复用现有夹具核验编辑模板、逐 ID 补丁、Gate 边界、Memory 和断点恢复。用已有训练片段走查三种语义情况：首步可用但中途需要不可见历史的规则；与 Parent 同目的、却能改变具体选择的规则；符合新优先级的首步之后出现归因不明的结果。结构校验能发现接线错误，真正的提案质量要看正式运行产物。[现有离线验证](../../../scripts/runs/v24_6/verify_v24_6_offline.py)
3. **正式训练一次。** 从共同初始 Skill 和空 Memory 开始，同一 Actor、同一 50 步上限，按 10、10、10、10、10、7 题跑完六轮。用现有 `diagnosis/result.json`、`preconditioner/result.json`、编辑补丁、`gate.json`（如产生）和发布记录追踪每个相关 update。一次跟踪表可在训练结束后从归档整理，流程里无需新增模型调用。
4. **最终测试一次。** 用实际发布的最终 Skill 在既有 134 题上各跑一次。对齐任务 ID 和环境文件，复用已有 v24.6、换段版、v24.1 的成绩。先报成功数与逐题由败转胜／由胜转败，再报整题未取物数、双方共同成功题的平均步数和全批总步数。按搜索相关任务类型定位得失。该套 Test 已用于历史比较，结果作为同基准回归证据；冻结方案后再看本次成绩。

## 五、如何据结果决定下一步

| 观察到的情况 | 优先检查 |
|---|---|
| 有成功和失败轨迹，但提案仍只说“避免重复” | Diagnosis 是否提取了成功路线中的连续决策，并把决定边界的轨迹放进了 basis。 |
| 有效的局部选择在审核时被判重复，或被改成全局访问清单 | 对照 Preconditioner 在同一菜单上给出的 Parent 与提案动作，检查中后段使用了哪些可见线索。 |
| 有效 Plan 可执行，Candidate 却缺少继续或退出条件 | 逐句对照 Editor 的有效文本、实际 diff 与单独应用后的 Skill。 |
| Candidate 有改善也有退步，被 Gate 暂缓 | 核对 Replay 对两侧动作与后果的解释。若正负归因都成立，接受该轮暂缓，并记录真实适用边界。 |
| 最终 Skill 保留了规则，但成功数没有改善 | 回到成败翻转的题，区分 Actor 未执行、规则在该场景不合适、失败发生在取物后的情形。若只有步数改善，单独记录效率收益。 |

对本次实验最有价值的结论是：**哪条规则来自哪些训练决策、通过哪一轮写入、后续是否仍被保留，以及它在同题上实际改变了哪些结果。** 这些证据足以决定下一版应改提案、审核、表达还是归因。
