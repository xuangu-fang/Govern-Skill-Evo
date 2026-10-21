# P1-R：Update 文本组织规范

2026-10-20。仅修订 V23.3 设计。正式 Schema 仍为 `id/text/basis`；text 是一个字符串，不是 requirement 数组。Grouping、Memory 及原编译器不变。

## 1. 最终规则

1. **按独立判断拆行。** 若两项要求可依据不同证据分别保留、修改或撤回，尽量分行。例如调度、换类前提、回访限制、完成标准、处理与交付可以有不同支持范围。不要按标点或固定字数切分。
2. **一行包含完整条件和行为选择。** “动作可用时直接处理”应整行表达，不将“动作可用时”与动作拆开。多动作构成一个不可分离的有条件过程时可同处一行；不为增加行数切碎它。
3. **保留作用域与顺序。** 必要时重复“在多实例任务中”“成功处理后”等限定，防止拆行变成全任务禁令或取消先后次序。共用作用域可用清楚的自然语言引用；修改该作用域时必须检查引用它的行。
4. **关联不等于必须同一行。** 若两个完整要求存在必要关联，可分别成行；Preconditioner 在既有 reason 说明“不改另一行会造成什么具体冲突”，用一个 Patch 的多个 Hunk 协调。不新增依赖 ID、role 或执行阶段。
5. **独立行不等于独立依据。** 同一 basis 可涉及多行，但不能自动为每项新承诺背书。新增要求需要自己的问题动机；一行仍可能偷偷含多个约束，必须进行语义评价。
6. **不是最少行/最小 Diff 优化。** 单要求可很长，有理由的大幅改写仍允许；行数、字符数、Hunk 数不代表正确性。

推荐新生成格式：每行以 `- ` 开始，不用 requirement 编号、不嵌套；不按显示宽度硬换行；使用 LF，末尾一个 LF。JSON 使用正常 `\n` 转义，解码后是真实换行。UI 自动折行不是内容换行。此约定指导未来本版 Diagnosis，不是对既有文本的自动修复器。

```json
{
  "id": "u1",
  "text": "- When the required action is currently available, choose it under the task's relevant conditions.\n- After the required processing succeeds, perform the requested delivery.\n",
  "basis": ["P1:1"]
}
```

仅为形式示例，引用必须在真实输入中存在，内容不是已验证策略。

## 2. Diagnosis 与 Preconditioner 的责任

未来 V23.3 Diagnosis 直接输出上述多行字符串；仍基于当前 Parent、Grouping 和执行，**不读取 Memory**。Goal 描述改善目标和必要边界，具体策略放在 Updates。初始策略可以有待修正之处，不要求 Diagnosis 独立求出最优策略。

Preconditioner 先按 P1 决定表确定目标要求、变换方向、可见条件、必要配套和独立探索，再定位原文行并直接写 Hunk。不能先自由重写完整 Update，再反向生成 Patch 给已发生的变化补理由。

“没有理由改变的要求保留”不等于“未选行永久正确”。若另发现旧行有独立错误，可以一并修改，但说明自己的依据；Checks 是观察问题，不能代替缺失的 Actor 操作条件。

本次没有修改任何正式 Prompt，也没有运行 Diagnosis。本版输出组织说明和消息接入属于未来 P2 的小范围工作，不增加拆句模块、一次额外生成或新的长期状态。

## 3. 旧单行文本的兼容

历史 Original 按原字节保留，不能机械按句号/分号拆分。旧单行仍可由原函数处理，但修改其中一句会替换整条原行，不能冒称拥有其他子句的行级保护。

本轮建立三个**人工设计副本**，只替换各 Update 的 text 组织；原 `id/basis/Goal/Checks/decision/reason` 保持。副本补全作用域、展开连接词、去除原步骤编号时尽量维持原含义，保留原有全局 visited、强开门或备用处理等问题，不在表示转换时偷偷修正。

原文、来源、人工表示、随后选择的行为修改分别保存于 [fixtures](fixtures/sources.json)，见[逐例走查](P1R_CASE_WALKTHROUGH.md)。文本外字段一致可由测试证明；语义保真依赖人工对照，不能由结构相等证明。

## 4. 为什么不需要新 Schema

行为行仍是 text 内容，身份仍为 Update ID；行坐标和上下文已经属于 Unified Diff。保留/撤回/多 Update 调整沿用现有 Adjustment，关系由已有 reason 说明。新 requirement ID、operation、anchor_text、replacement_text、role、依赖图都不能额外保证语义支持，也不是本轮必需能力。

新多行表示改善的是可操作粒度。预条件化核心仍是历史实际编辑及其响应如何决定具体变化；需要分别验证表示、决策与真实任务效果。
