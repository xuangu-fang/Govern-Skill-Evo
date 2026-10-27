# P6：逐 Knowledge 语义审查

审查基于首次结构合法的原样提案及冻结的模型可见输入。下文 K1、K2 等仅是报告中的数组位置，不是新增 Knowledge ID。没有修改模型输出，也不因语义问题重采样。

## R05：新增 M10，4 条 Knowledge；暂不采用

本轮 `revises: []`，没有替换 M6/M8 等旧 Memory。旧历史认识没有被删除，但也没有重新校准；因此这轮不能用来证明完整数组替换能够保留或纠正历史。新条目以本轮联合编辑为主题，分为整体、合法动作、搜索、精确对象四条；这在结构上允许，但没有展示预期的跨轮整合。

| 条目 | 支持的内容 | 主要问题 |
|---|---|---|
| K1 | 当前双方均 8/10 成功；pillow/pencil 5→6、apple 14→11 数字正确；强调联合编辑和因果不确定性 | 将三个编辑都称为加入 general non-desklamp procedure，忽略 Admissible Actions 是独立全局章节。作全批 10 Pair 结论却没有引用当前 P3/Q3、P4/Q4、P6/Q6；数字可由输入验证，但自身 Evidence 没覆盖所声明的完整范围 |
| K2 | Q8:39 非法导航、P8:15 非法导航及 soapbar 双方失败正确 | 写 Q7:25 是从 drawer 7 发出非法 `go to drawer 8`，实际该步为合法 `go to drawer 2`，整条 Q7 没有非法命令。又称没有观察到 direct-action fallback 取得进展，漏掉 P8:8 的合法直接开柜及新内容观察 |
| K3 | Candidate 探索 bathtubbasin 1/sinkbasin 2，而 Parent 未到；两个失败任务仍循环；pencil 多一次初始导航正确 | 将 desklamp pillow 的多一步放进非 desklamp 搜索条款响应中，没有注明其在条款范围外；“归因未隔离”并不能代替适用范围判断。该搜索认识也未吸收 apple 的具体搜索改善，K1 仅保留了总步数 |
| K4 | Candidate 仍取、清洗、放置 knife 替代 butterknife，相关动作引用正确；soapbar 任务没有操纵 soapbottle/spraybottle | 将 soapbar 写为 `absent`，轨迹只能说明没找到。两侧初始菜单都有 shelf 1，但都未访问，不能证明全局不存在。称 Parent 同样 abstained，却没有该比较的 Parent soapbar 引用 |

直接反证：

- **Q7:25** 实际 `go to drawer 2`，`action_in_admissible_commands: true`；Q7 全 50 步均为合法命令。这是新增的动作/步号事实错误，不只是引用偏移。
- **P8:8** 当前菜单没有 `go to cabinet 3`，但有 `open cabinet 3`；Parent 合法打开该柜并首次获得柜内观察。这不能证明 Candidate 因新增规则获得收益，但足以否定覆盖全部观测的“没有 direct-action fallback 进展”。
- Actual Diff 的 `## Admissible Actions` 位于通用搜索章节之前，是独立章节；搜索改动则明确受 `no desklamp` 限定。Pillow 是范围外比较。
- 当前 apple 的取物后动作相同：Parent 搜索中绕回 fridge/countertop，Candidate 较早到 diningtable，14→11 的差异在搜索阶段。K1 保留数字，但 K3 没有形成这项有价值的局部认识。

没有再次出现 R03 搬 cup 被写成加热 cup 的错误，但本轮根本没有讨论历史 cup，不能将省略历史当作该错误已修复。M6/M8 的旧历史仍原样活跃，其中旧的强 absence 解释也没有被纠正。成功 butterknife 的独立能力保持比较 P6/Q6 仍没有进入新增知识。

采用判断：四条都存在范围、事实或自身证据不足的问题，整个 M10 暂不发布。有效局部内容仍完整保留在原始结果中。

## R06：M10 → M12（3 条），M7 → M13（2 条）

这轮实际执行了完整数组替换。温变条目首次在本系列候选实验中同时保留了两个重点边界：

- **M13/K2：历史 heat plate** 明确 Parent 在 countertop 3 取得 plate、加热、13 步成功，而 Candidate 未到该表面、50 步失败、没有温变机会。引用包括 `S1_R04/P2:4/:11/:13` 与 `S1_R04/Q2:50`。没有用“未触发”抹去两侧差异，也未把搜索失败直接归因于温变条款。
- **M13/K1：当前 cool tomato** 明确两侧都在打开的 fridge 对持有 tomato 直接冷却；18→10 主要是搜索差异。核对取物后序列完全相同，故本对没有新增局部温变收益。文字虽未写数字“0”，已表达支持该边界的双方动作，没有再把八步都记为温变收益。

| 条目 | 核对结果 | 原样采用判断 |
|---|---|---|
| M12/K1，扩展搜索 | book 50 失败→40 成功、cool tomato 18→10；历史 R05 butterknife 与 soapbar 两个修复均保留，动作、步号、身份和结果相符；明确联合编辑与单次执行限制 | 本次定向核对未发现阻断项。Book 在第 33 步才到 bed，不代表此前可靠防循环；本条本身没有宣称防循环可靠 |
| M12/K2，持续循环与效率退化 | 当前 heat apple 双方 50 失败；历史 butterknife 双方失败、cool apple 38→46 的不利效率差异均保留 | **暂不采用**：写历史 butterknife `no exact butterknife was present`，证据只支持未找到。初始菜单存在 cabinet 18 等未探索位置，不能从失败推出全局不存在 |
| M12/K3，多实例能力保持 | creditcard Parent 先检查 drawers 1–8、24 步成功；Candidate 先到 desk、9 步成功，依次完成两个实例；明确首步选择和独立归因限制 | 本次定向核对未发现阻断项；这是观察到的能力保持及搜索差异，不是多实例机制的新独立效果 |
| M13/K1，温变局部响应 | 当前 heat tomato 39→8、8→7；cool plate 局部省开门但总步数 8→9；cool tomato 无新增局部温变收益；历史 pot 18→11、apple 35→9、egg 40→15、potato 14→7、tomato 21→7 均核对相符 | 本次定向核对未发现阻断项。仍是一条 1,947 字符、容纳九个比较的较长 Knowledge，粒度问题未完全消失；各例门操作差异没有被统一改写为同一种动作循环 |
| M13/K2，未取得目标与机会差异 | 当前 apple 双方未取得目标；历史 heat plate 不对称比较完整；R04 mug 的 Parent 取得 cup 与双方失败、R03 mug Candidate 不操纵 cup 均有依据 | 本次定向核对未发现阻断项。没有把 R03 搬 cup 写成加热 cup，也未声称本轮能证明目标不存在 |

M13/K2 对 R04 mug 仅保留 Parent 取得 cup，未重新陈述其加热及 Candidate 不加热的完整比较；该比较仍在未修订的 M11 及其历史 `S1_R04/P1:31` Evidence 中，不能误称已从整份 Active Memory 消失。M12 保留旧 M10 的两项修复、失败及 apple 效率退化，但未复述其原全批 7/10→9/10 汇总；本报告不宣称每个历史句子都被完整保留，也不把未重复汇总自动视为事实错误。

本轮 M12 整项因 K2 的过强判断暂不采用。M13 的两条认识在本次定向审查中未发现阻断项，但没有因此自动发布，也不能据一次成功输出认定未来可以可靠自动采用。旧的其他活跃 Memory 未被全面重新校准。

## 对多 Knowledge 设计的实际结论

1. **重要历史比较可以被单独保留。** R06 的 heat plate 与温变成功案例分到不同 Knowledge；零新增局部收益也获得明确说明。这是本次真实观察到的改善。
2. **结构本身不能保证历史校准。** R05 只新增条目，没有修订旧认识；两轮仍有过强 absence 结论，R05 还出现了不存在的非法动作。这些都不是 JSON 校验能够解决的。
3. **粒度仍不稳定。** R05 四条较短，但缺少历史整合、范围外比较不清楚；R06 五条覆盖更多重要历史，仍有一条集中九个温变比较。不能只用 Knowledge 数量或长度评判学习质量。
4. **本次不构成消融或稳定性证明。** 对照旧输出时，主 Prompt、表示与随机采样共同变化；每个案例只有一个合法输出。不能把 R06 改善单独归因于数组结构，也不能推断自动采用率。

可重放的事实断言见 [FACT_CHECKS.json](FACT_CHECKS.json) 与 [review_facts.py](review_facts.py)；完整原样提案见 [R05](runs/R05_replay/attempt_002/parsed.json) / [R06](runs/R06_replay/attempt_001/parsed.json)。
