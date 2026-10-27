# V23.4 Editor 最小定向审查

日期：2026-10-21（Asia/Shanghai）。范围仅为 Effective Plan → Editor → Candidate / actual Diff → Replay，不重新设计 Editor，不增加审核 Agent、输出字段或额外调用。

结论：输入和实际 Diff 交接可确认；现有 Prompt 已覆盖忠实实现与禁止额外策略的要求，未发现本范围内需要立即修改的接口或 Prompt 缺口。**真实 Editor 模型是否遵守这些要求仍未验证。** 本次只增加定向离线材料和报告，不把人工注入的正确输出当作模型能力证据。

## 1 四项核对

| 审查点 | 代码与 Prompt 依据 | 本次结论 |
|---|---|---|
| ① 输入是否正确 | [editor_input](../../../src/skill_evolution/v23/editor.py) 重编译核对后返回 parent / saved.effective_plan；[V23.4 Editor](../../../src/skill_evolution/v23_4/editor.py) 使用该输入及消息函数 | 确认使用最终 Effective Plan。Original Plan 保存在上游归档中供重算，但不进入 Editor 的模型请求；Memory、Adjustment 和 Preconditioner Patch 也不进入请求 |
| ② 修改是否忠实 | [Editor Prompt](../../../src/skill_evolution/v23/editor_prompt.md) 第 1、2、4 节要求保留条件、范围、强度、依赖、例外，修正冲突 Parent 指导，不允许静默撤回或换策略；不能忠实实现时返回 null | 要求已明确，三个合成正例可准确写入 Skill。但 `validate_editor` 只检查格式与 Patch 可应用性，不能证明真实生成忠实 |
| ③ 是否加入额外策略 | 同一 Prompt 明确不重新考虑行为策略、不增加要求、不把 Checks 变成指令，只做必要修改并保留无关有效指导 | 要求已明确；结构程序仍会接受额外的全局禁止、结束门槛或许可升级为强制。不能把结构通过当作策略授权 |
| ④ 是否保存真实 Diff | Editor 先 apply_patch 得到 candidate.md，再由 Parent/Candidate 生成 actual.diff；加载器重算两者。[Replay 装配](../../../src/skill_evolution/v23/replay.py) 使用 saved.actual_diff，并验证执行记录的 Skill 与 Candidate 一致；[新版 Replay](../../../src/skill_evolution/v23_4/replay.py) 再核对上游 | 确认 Replay 使用真实 Skill 修改，非 Preconditioner 的 Update 文本 Patch；替换 actual.diff 的篡改被拒绝 |

Original 中的旧要求可能仍然存在于 Parent，Editor 必须看到它以消除冲突。这不等于 Editor 被提供 Original Plan，也不要求盲目删除所有与旧要求相似的文字。

## 2 定向离线材料

[test_editor_directional_review.py](../../../tests/skill_evolution/v23_4/test_editor_directional_review.py) 为每个案例构建真实归档结构：合成 Grouping/Diagnosis、v2 Adjustment、编译后 Effective Plan、人工注入的 Editor 响应、Candidate，以及合成记录构成的 Replay 输入。不存在真实模型或 Actor 执行。

三个正例均包含一个被撤回的独立 Original Update：`Search every category before stopping.`。该要求不在 Parent，也不在 Effective Plan，因此没有理由由 Editor 加回。

| 正例 | 有效要求 → 最终 Skill 的核对 | 保留边界 |
|---|---|---|
| D/S 重构回访限制 | 用“无新信息/无任务进展时避免重复搜索”替换 Parent 的全局回访禁止，同时允许当前任务需要的返回 | 不保留旧的总括禁止，不加 exhaustive-search 结束门槛 |
| S 扩大许可 | A 不可用时，允许使用当前可见且满足信息要求的替代来源 | 保留适用性检查，许可不变成强制先用 B |
| S/C 协调恢复 | 修复后重查当前前提并在就绪时重试，同时把无条件放弃改成前提仍未满足时不重复 | 两项要求共同落实，保留无关的精确目标识别指导 |

这些正例的 Skill 表达接近 Update 原文，是为了隔离本次边界；不据此要求所有 Editor 都逐字复制 Update，也不限制合理的重组、合并或同义改写。

另构造六个反例，并逐项按 Effective Plan 和现有 Prompt 判为语义不忠实：

1. 恢复已被重构的全局回访禁止。
2. 加回已撤回、且 Parent 未包含的“搜索所有类别后才能结束”。
3. 追加新条件规则，却保留冲突的旧 Parent 禁令。
4. 把替代来源的使用许可改成强制先用 B。
5. 把重新确认前提就绪改成修复后立即重试，遗漏必要依赖。
6. 删除无关且应保留的精确目标识别指导。

六个反例均能通过现有格式/Patch 检查并得到 `editor_status=candidate`。测试有意记录这个结果，以明确**结构有效不是语义忠实，也不是 Candidate 已接纳**。它们不是本次观察到的模型错误，不能据此报告真实错误率。

即使 Editor 实现错了，actual.diff 仍必须如实记录错误修改，Replay 不应把它替换为理想中的有效要求。本次反例也核对了该性质。

## 3 撤回含义与最小后续检查

撤回一个 Original Update 表示取消本轮提议，不自动删除 Parent 中同类指导。若某个已有 Parent 限制必须移除，这一行为改变应写入存活 Effective Update；不能让 Editor 根据看不到的撤回理由猜测应删除什么。

因此，本次不建议为了防止“恢复旧要求”而给 Editor 再传 Original、Memory 或一份撤回清单。保持最终 Effective Plan 为实现依据，并确保它已经完整包含实际需要改变的条件与保留边界。

在后续获准进行少量真实生成时，优先使用以上三种情形，对最终 Candidate 和 actual.diff 做同样的逐项语义抽查。观察是否遗漏依赖、加强许可、保留冲突或新增限制；不要只看返回码、Patch 可应用性或 Editor 自述理由。这是尚未完成的生成遵循验证，不是新增流水线或审核 Agent。

## 4 验证结果与范围

本次新增检查：**9 passed**（3 个完整正例交接 + 6 个明确语义反例），耗时约 0.9 秒。未重复报告前四步测试总数为本轮执行结果。

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m pytest -q \
  tests/skill_evolution/v23_4/test_editor_directional_review.py
```

未改 Editor 生产代码、Prompt、Schema、D/S/C 算法或 Memory；未运行真实模型、Actor 或第五步。dlinter 技能仅核对了使用范围和辅助脚本帮助：它提供远端增量代码扫描，不能替代本次语义审查。本轮未创建远端扫描任务、未上传代码，也没有 dlinter 扫描结果；本报告为本地源码路径核对、人工构造材料的语义走查和离线验证记录。
