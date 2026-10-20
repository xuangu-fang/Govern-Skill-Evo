# V23 有 Memory 的 Preconditioner 对照验证报告

日期：2026-10-18。状态：两次真实调用均合法，真实 Memory 被消费并产生两项 Adjustment；存在能力条件、因果措辞和策略外推问题，未验证后续行为收益。

## 1. 固定当前问题和比较边界

本地已有可直接冻结的 V23 Diagnosis 来自 `v23_prompt_alignment_001`，没有发现独立后续任务的合法 V23 Diagnosis 档案。本次因此复用其 Parent=null、四条 Parent／93 步、两组、原始 3 项 Update／3 项 Check，与 `v23_preconditioner_001` 使用同一当前问题。

Memory 来自刚完成的 `v23_replay_memory_001`：四条真实 Candidate 的 133 步配对执行，经唯一一次 Replay 形成 M1／M2／M3。这是**同批证据回看与更新构造验证**，不是独立跨轮泛化。未重跑 Grouping、Diagnosis 或 Editor，也未执行本次新 Effective Plan。

## 2. 严格对照与来源

两侧均使用本次同一份更新后的 [Preconditioner Prompt](../../../../../src/skill_evolution/v23/preconditioner_prompt.md)、相同 Actor 背景、Parent、当前事实、Grouping、Diagnosis Plan 和生成参数。模型数据输入除 memory 外完全相同，已作程序精确比较。

- 空侧：`memory={"entries":[],"sources":{}}`，新调用一次。未拿历史旧 Prompt 的 Keep 充当匹配对照。
- 实侧：实际 Active 的 M1／M2／M3，加它们引用的 9 个共享来源（1 份历史编辑及执行背景、8 条完整历史执行）；没有旧版失效认识，没有人工合成 Memory。

完整共同输入和两份快照见 [原始产物目录](../../../../../artifacts/methods/v23/v23_preconditioner_with_memory_001/)。历史条目全文与事实核查见 [报告 A](../../v23_replay_memory_001/reports/REPORT.md)。

M1 记录搜索指导下重复循环仍存在、局部覆盖增加和长柜子搜索；M2 记录同一缺失动作仍被发出；M3 记录清洁子流程保持但没有改善证据。每条来源都能还原到真实 Diff、初始状态、全执行步骤和当时动作菜单。当前 `P1` 与历史 `v23_replay_memory_001_R1/P1` 在命名空间上区分，即使来源重合也不合并执行身份。

## 3. 两侧真实输出

### 空 Memory

```json
{
  "decision": "ready",
  "reason": "The original Updates are consistent with the recorded P1-P4 behavior and Actor capabilities: u1 addresses the repeated-location search failure in P2 while preserving P3's successful expansion to a non-kitchen receptacle; u2 captures the successful acquire-clean-place dependency sequence in P1, P3, and P4; and u3 directly addresses the inadmissible-action failure in P4:5. No supplied Memory entry or current evidence justifies changing or withdrawing any Update or Check.",
  "adjustments": [],
  "checks": null
}
```

### 真实 Memory

```json
{
  "decision": "ready",
  "reason": "The successful acquire-clean-place workflow (u2) is compatible with the recorded successes and is preserved unchanged. The search update (u1) is revised because the historical Skill containing the same search guidance still cycled, missed the listed bathtubbasin, and caused a costly all-cabinet sweep before reaching a plausible surface. The admissible-action update (u3) is strengthened because its prior abstract wording did not prevent an absent numeric-sweep action. Checks are updated to match the revised behavioral requirements.",
  "adjustments": [
    {
      "from": [
        "u1"
      ],
      "to": [
        {
          "id": "u1",
          "text": "When locating a target object, do not repeatedly cycle among the same few locations. Use the current admissible location list, which enumerates all reachable receptacles, to plan the search: first check locations that plausibly hold the target type (for example the fridge or a countertop for food, a stoveburner for cookware, or a sinkbasin or bathtubbasin for a sponge or cloth), then move through other distinct receptacle classes, including outlying or non-kitchen ones such as a bathtubbasin, cart, or toilet when listed, before inspecting any location a second time. Do not spend many consecutive steps exhausting a single class such as all cabinets or all shelves; after a few instances of one class, switch to a different unchecked class. After checking a location and observing that the target is absent, prefer an unchecked admissible location over returning to a previously checked one, and avoid the location named in the immediately preceding observation or action when another unexamined admissible location exists, unless a new observation indicates the target may now be there."
        }
      ],
      "basis": [
        "M1",
        "G2",
        "P2:5",
        "P2:11"
      ],
      "reason": "M1 records that this exact search guidance (deterministic name/number sweep plus class expansion) did not stop cycling, never reached the listed bathtubbasin, and in a many-cabinet scene produced a long cabinet sweep before a plausible stoveburner surface. P2 shows the repetitive A-B-A pattern the Update targets. Replacing the bare numeric/class sweep with an admissible-list plan that prioritizes plausible locations and interleaves classes directly addresses both the missed non-kitchen receptacle and the costly same-class sweep."
    },
    {
      "from": [
        "u3"
      ],
      "to": [
        {
          "id": "u3",
          "text": "Before emitting an action, verify that its exact text appears in the current admissible action list. Only select actions that are listed. If you intend to continue a numeric sweep and the next numbered instance is absent from the list (for example 'go to stoveburner 3' when only stoveburner 2 and stoveburner 4 are listed), skip to the next listed instance instead of issuing the absent action. If any intended location or action is absent, do not issue it and expect progress; choose an available alternative, such as another listed location or a currently available examine or open action, and continue the plan from there."
        }
      ],
      "basis": [
        "M2",
        "P4:5",
        "P4:6"
      ],
      "reason": "M2 documents that the earlier admissibility wording did not prevent the exact absent action 'go to stoveburner 3' in this task; both the Parent (P4:5) and the guided Candidate issued it before correcting to the listed stoveburner 4. An explicit pre-action exact-text check with a numeric-skip rule is a justified strengthening of the same requirement."
    }
  ],
  "checks": [
    {
      "id": "c1",
      "update_ids": [
        "u1"
      ],
      "question": "When the target is not found at first, does the agent use the full admissible location list, prioritize plausible locations for the target type, and cover distinct receptacle classes — including non-kitchen or outlying receptacles — before repeating a location or spending many consecutive steps on a single class?"
    },
    {
      "id": "c2",
      "update_ids": [
        "u2"
      ],
      "question": "After acquiring the target, does the agent clean it at the appropriate cleaning fixture before delivery and open a closed destination before placing it?"
    },
    {
      "id": "c3",
      "update_ids": [
        "u3"
      ],
      "question": "At each step, does the agent choose an action whose exact text appears in the current admissible list, and when the next instance of a numeric sequence is absent does it skip to a listed instance rather than issuing the absent action?"
    }
  ]
}
```

原始输出保持原样，完整对照和程序生成的两个 Effective Plan 见 [comparison.json](../results/comparison.json)。

## 4. 更新变化与语义核查

| 对象 | 空 Memory | 真实 Memory | 核查 |
|---|---|---|---|
| decision | ready | ready | 均为合法更新继续状态 |
| u1 | Keep | 由 M1 支持的“按目标类型优先搜索＋切换搜索类别”替换确定性编号／类别扫描 | 历史确有循环、未到浴盆和长柜子搜索，调整动机有依据；具体替代策略尚未经过执行验证 |
| u2 | Keep | Keep | 保留 acquire-clean-place 条件及例外，符合 M3 所记录的局部保持；不等于已经证明该 Update 必需 |
| u3 | Keep | 由 M2 支持的动作输出前精确文本检查＋跳过缺失编号 | 历史确有两侧同一非法动作，具有可观察条件和具体策略；与基础协议仍有重复，尚不能证明加重文字就会改变执行 |
| Checks | 全部继承 | 整体替换 c1/c2/c3 | c1、c3 对应新要求；c2 保持原问题。所有 update_ids 有效 |

真实侧不是只在 basis 列出 M ID：u1 的理由使用 M1 中两种搜索问题，u3 的理由使用 M2 中合法性指导未阻止相同缺失编号动作的事实。方向／范围／强度与组合关系由自然语言更新表达，没有增加 D/S/C 字段。

但真实侧存在以下明确限制：

1. **因果措辞过强。** 总 reason 使用“caused a costly all-cabinet sweep”；M1 原本只记录伴随关系并保留随机性和联合编辑限制，不能被消费成已证明因果。实际也不是所有柜子均被检查。
2. **有限历史问题没有解决。** 新 u1 仍要求在任何位置第二次访问前覆盖其他类别、选择 unchecked 位置／类别，并判断一个类别已经检查了几个实例。Actor 仅有最近两组历史，缺乏完整搜索记忆。输出没有给出足够的可执行进度表示。
3. **动作菜单被过度解释。** “current admissible location list enumerates all reachable receptacles”超出了输入契约；它是当前动作候选，不能一般化为完整环境可达性清单或已检查状态表。
4. **新增策略是待验证假设。** 按食物／厨具／海绵等类型优先选择地点、检查少数实例后换类别，并未由独立对照验证；示例与本批环境吻合，存在同批回看过拟合风险。历史问题可以支持重新考虑策略，但不能直接证明新策略有效。
5. **u3 的实例细节与重复。** 精确检查和跳过不存在的编号是可执行候选策略，但示例直接沿用 stoveburner 3，文本可迁移性仍应审视；它没有解决基础协议已要求合法动作却未遵循的根本原因。
6. **空侧也有判断不足。** 它称原始 Updates 与 Actor 能力一致，仍未处理 u1 的完整访问历史依赖；空侧 Keep 不是一个已证明合理的参考答案。

M3 本轮没有在 Adjustment basis 中被显式引用，因而不能声称 u2 的保留一定由 M3 导致。它与原有成功事实和 M3 内容相容即可。

## 5. 确定性编译与复用

两侧都保留原 Goal、3 项 Update 和 3 项 Check；真实侧按原位置替换 u1/u3，u2 原样保留。Update 的 basis 仍继承原 Diagnosis 来源；M1／M2 只保存在 Adjustment basis 中，没有被程序混入 Effective Update 的 basis。

两侧的模型原始文本、解析、契约验证、Adjustments 和 Effective Plan 全部保存。再次调用运行接口读取相同目录时，禁止网络的生成器未被调用，结果相同。旧 Grouping、Diagnosis、Preconditioner 及 Editor 成功／失败档案的字节哈希与运行前一致。

运行前离线回归为 432 项与 19 个子测试；运行后另加两项实际产物只读交接测试，最终为 **434 项测试与 19 个子测试通过**，见 [final_tests.txt](../../../../../artifacts/methods/v23/v23_replay_memory_001/final_tests.txt)。结构验证不判断上述自然语言策略是否正确，也未引入第二个模型审核。

## 6. 调用与消耗

两侧模型均为 deepseek-flash，temperature=1、thinking enabled、reasoning_effort=medium、stream=false，max_tokens=16,384、timeout=300。环境 seed=42 只属于 Actor 环境；这两次模型请求未设可复现 seed，不能把随机采样差异完全归因于 Memory。

| 侧别 | 输入 Token | 输出 Token（含推理） | 推理 Token | 总 Token | 秒 |
|---|---:|---:|---:|---:|---:|
| empty | 24972 | 1851 | 1735 | 26823 | 10.415 |
| real | 78647 | 10300 | 9395 | 88947 | 47.893 |

空侧输入 88,806 字符，实侧 271,890 字符，均低于调用前冻结的 300,000 字符／400,000 UTF-8 字节上限，没有截断 Memory 或轨迹。实际缓存命中和全部 usage 在 [summary.json](../results/summary.json) 与原始响应中；API 未提供货币账单金额。本阶段没有技术失败或重采样，每侧恰好一次调用。

## 7. 结论与未验证事项

真实 Active Memory 已被成功消费，并观察到引用历史编辑—行为响应的非恒等更新构造：M1→u1、M2→u3。**调整动机有事实依据，不代表调整后的全部策略、条件和强度都已合理或有效。** 能力不匹配、因果措辞和策略外推是本次保留的问题。

本次没有执行这份 Effective Plan，没有验证任务成功率改善，也没有验证跨轮认识修订或独立任务泛化。完整持续闭环仍缺少 Gate／一致状态推进及后续行为验证；已实现的 Memory 工程维护不等于其长期学习质量已经得到证明。
