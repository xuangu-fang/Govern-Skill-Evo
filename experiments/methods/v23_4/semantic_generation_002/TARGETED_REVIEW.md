# R06 两项语义问题的定向核查

范围：仅核查 u2 的 change—Patch 对应及 Goal / Check 一致性。未调用模型、执行 Actor、修改 Prompt/校验器或修补原始结果。事实摘录和来源 SHA256 见 [TARGETED_REVIEW_EVIDENCE.json](TARGETED_REVIEW_EVIDENCE.json)；该文件是已有归档的提取，不是新执行证据。

结论：两项问题均成立，但责任层次不同。第一项是 Preconditioner 在 Patch 中新增未声明的动作顺序；第二项同时涉及旧 Diagnosis 将实现条件写进冻结 Goal、Preconditioner 未处理该边界及未同步可替换的 Check。编译器没有篡改文本，Editor 传递了上游问题。

## 1 “放入后取回”在哪里产生

| 环节 | 实际内容 | 判断 |
|---|---|---|
| Original u2 | 若持有目标时 conditioning action 不可用，`place the target inside once and perform the action` | 已有 insertion fallback，但未要求先取回再执行 |
| Adjustment.change | 当前命令优先；开门重查后再考虑 `a single insertion fallback` | 没有声明新增取回动作及顺序 |
| Adjustment.reason | 描述旧执行取回后加热，并明确 insertion fallback 的必要性尚未由样例确立 | 描述历史动作不等于决定把它加入新的 fallback |
| to.patch / Effective u2 | `place the target inside once and then take it back once and perform the action while holding` | 新增固定的放入→取回→持有执行顺序，首次出现于 Preconditioner Patch |
| Candidate / actual.diff | 同样写入放入→取回→执行 | Editor 落实 Effective u2，没有自行发明此动作 |

[原始输出](runs/R06_pc/attempt_001/parsed.json)与[最终 Candidate](runs/R06_editor/attempt_001/candidate.md)可直接对照。对冻结 Original 独立应用 Patch，结果逐字等于 Effective u2；Editor 请求中的 Plan 等于该 Effective Plan；actual.diff 重应用可还原 Candidate。不存在适配层插入动作或读错 Plan 的迹象。

### 为什么不是实现细节

取回会改变持有状态、动作顺序和步数，属于行为选择，不能把它隐含在“单次插入”里。现有 [Preconditioner Prompt](../../../../src/skill_evolution/v23_4/preconditioner_prompt.md) 已要求 Patch 每个实质行为变化由 change 覆盖，并禁止在措辞实现时引入未声明顺序。因此这是已有规则的生成遵循问题，不是 JSON 缺字段或缺少单独的审核 Agent。

### 为什么历史取回成功不能证明这个 fallback

- P4:5 / P5:4：微波炉关闭、Actor 已持有 tomato，before 菜单已提供 heat。
- P4:6 / P5:5：微波炉打开，heat 仍可用，但 Actor 将 tomato 放入。
- 放入后，当前菜单不再包含 heat；P4:19 / P5:14 取回后，P4:20 / P5:15 的菜单重新提供 heat，随后加热成功。

观察支持的是：**目标已被放入时，取回后恢复原先已有的持有加热机会。** 新 fallback 的触发却是：**目标已经持有、家电已经打开，heat 仍不可用。** 材料没有证明这时先放入再取回能创造新的可行动作。这是触发条件迁移缺口，不是证明该策略在所有环境中必然无效。

Original 同时要求持有加热和插入 fallback，本身已有待澄清的状态关系。新增取回可能在文本上补齐“持有”条件，但不能据此推断模型内部动机，也不能绕过 change 的明确决定与依据要求。仅在 reason 中承认 insertion fallback 未验证，仍不等于声明取回动作。

处理方向：先判断 fallback 的具体必要性、触发条件与状态变化。如果保留为探索，须在 change 中明确所选行为和顺序，并解释动机与未知；若没有合理动机，不应为了补齐流程而新增动作。不能只补一句事后理由，也不能机械删除“取回”后就宣称剩余 fallback 已被证明有效。

## 2 关闭状态加热与 Goal / Check 的关系

### 行为方向有证据，冲突来自 Plan 的表达与约束

实际任务 P4/P5 要求加热 tomato 并放入 fridge，没有要求加热时打开 microwave。当前 before 菜单 C50 / C57 已列出关闭状态下的 heat；模型实际可见的历史 S1_R04/Q3:5、S1_R04/Q4:5 则明确记录关闭状态下持有目标直接加热成功，两条历史执行最终也成功。前者证明候选动作可用，后者提供实际成功观察，不能混为同一种证据。

这些事实支持“命令已可用时无需一律先开门”的条件化方向；它们不证明所有温度任务或环境都能如此，也不能完全归为 Memory 的独有价值，因为当前事实已提供相关线索。

但 Original Goal 要求 `perform one conditioning action on the exact held target at the open appliance`。在本轮冻结契约下，open 是写入 Goal 的明确条件，不能由 Preconditioner 静默按无关措辞处理。Effective u2 要求命令可用时即使关闭也立即执行，因此与该条件不一致。

### Goal 冻结，Checks 不冻结

Goal 由旧编译器原样继承，Preconditioner 无权编辑。Checks 则可以 null 保留或完整替换。本次输出已经返回完整 Checks 数组，却在 c2 中继续要求 `at the open appliance`。所以应分别归因：

1. **旧 Diagnosis 的目标表述问题。** 将缺乏必要性证据的开门实现条件写入了不可调整的 Goal。
2. **Preconditioner 的边界处理问题。** 选择了与冻结 Goal 冲突的变换，没有明确处理冲突。
3. **Preconditioner 的检查项同步问题。** 有权替换 c2，也实际重写了它，却保留与新 Update 不一致的打开状态要求。

仅修 c2 不能解决冻结 Goal；仅让 Goal 文字保持不变也不能证明语义遵守。与此同时，这不意味着整个 Original Goal 无解：保留打开状态、减少不必要插入和反复开关，仍是与其相容的改进方向。不能把某个所选策略不相容夸大成“任何合法 Plan 都无法形成”。

### 不是简单补一句 Diagnosis 提示即可

核对了这次旧生成实际使用的[归档 Prompt](../../../../artifacts/methods/v23_2/v23_2_diagnosis_construction_001/R06/attempts/001/prompt.md)：第 98 行已经要求将实现选择放在 Updates，使 Goal 在策略替换或撤回后仍适用；第 104 行明确指出成功序列不证明每一步必要。故不能声称旧版缺少这一规则。

当前 [V23.4 Diagnosis Prompt](../../../../src/skill_evolution/v23_4/diagnosis_prompt.md) 第 56 行及第 109 行也已表达相同边界。这里确认的是旧输出没有遵守已有要求，尚未证明新版 Diagnosis 会重复该错误，也没有证明重复加长 Prompt 可以消除问题。

若要探索免开门策略，应在一个明确的新上游 Plan 中，使 Goal 表述任务结果、减少无效动作和必要保留能力，把开门等条件放入可修改 Updates，再生成一致的 Checks。不能偷偷修改本轮归档 Goal，也无需因此赋予 Preconditioner 任意改 Goal 的权限。本轮不生成或替换这个新 Plan。

## 3 Editor 与程序校验的责任边界

对第一个问题，Editor 看不到 change/reason，因此不能要求它发现 change—Patch 越界。它实际忠实地落实了含有额外动作的 Effective u2。

对第二个问题，Editor 能看到完整 Goal、Updates、Checks，因此矛盾在其输入内可见；它继续产出 Candidate，说明这次也没有识别并报告该冲突。按照已有 Editor 阻断规则，应指出无法同时忠实实现的要求，而不是自行决定放宽 Goal 或改变 Update。问题源头仍在上游，不以重新设计 Editor 来替代修正。

结构校验检查引用存在性、Patch 精确应用、Goal 文本继承和 Check 关联，不声称能判断自然语言策略是否一致。本次没有发现编译错误，也不建议加入针对“open/closed”或“take back”的硬编码语义规则。

## 4 后续建议与本次验证边界

- 保留这次输出为真实语义失败案例；不修补后重标成功，不以技术重启重采样。
- 优先把已有双向对应规则落到本例的 fallback 决策核查，并验证新的 Diagnosis 是否真的将实现条件留在 Updates 中。现有规则已覆盖核心要求，先不重复扩写 Prompt。
- Goal/Plan 若需重新生成，应作为新输入版本记录；继续第五步时仍保留本次失败事实，不能把修正输入后的通过当作原案例通过。

本次完成归档重解析、源码冻结核验、Update Patch 编译、Editor Effective Plan 输入核对、actual.diff 还原，以及当前/可见历史事实和实际旧 Prompt 的核对。没有额外 API 或 Actor 调用，没有修改生产实现；语义判断为当前同一分析者的人工核查，不是独立盲评或自动保证。
