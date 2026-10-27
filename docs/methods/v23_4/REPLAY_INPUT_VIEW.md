# V23.4 Replay 模型输入视图契约

版本：`v23_4_replay_pairs_memory_v3_v1`。日期：2026-10-22。

以实际 Skill 编辑为对象，以当前 Parent/Candidate 配对执行为主要证据，以历史 Memory 为参考，进行一次模型学习，直接输出 Memory 更新提案。本次只改变确定性的模型输入组织，不新增学习阶段、语义审核、动态窗口或 Actor 调用。

## 完整事实与模型视图

完整 bundle / 原始 Memory / 不可变历史归档保持原 Schema。单独生成并保存 `model_input.json`；七个顶层字段仍为 `parent / diff / plan / command_sets / runs / pairs / memory`。JSON 字段展示顺序可以将 pairs 放在 runs 前。

- parent、实际 diff、Effective Plan 和当前 command_sets 原样保留。
- 不加入 Original Plan、Preconditioner 决策或预期 Patch。
- 当前 runs 按已核验 pairs 的顺序交错排列，两侧时间线独立；完整 run 对象内容不变。
- pairs 提供当前任务身份与各侧结果；只在这里新增统计，不改 run Schema。

```json
{
  "parent": "P4",
  "candidate": "Q4",
  "task_id": "val:0014",
  "parent_result": {"status": "success", "success": true, "steps": 39},
  "candidate_result": {"status": "success", "success": true, "steps": 8}
}
```

以上为 R06 的任务级示例，不是独立规则收益。task_id 来自 bundle 的已核验 pair_audit，并核对双方 source 的 task_id/ref 与 pairs 一致。每条当前执行恰好出现一次，不从编号、任务文字或数组位置猜配对。

steps 等于完整事实中已执行动作的数量，包含无效/空动作；HTTP 重试和未执行请求不计入。success/status 直接复制 outcome，技术中断保留 success=null。不同步号不代表不同条件，同步号不代表相同机会。

## 历史 Memory

原样调用现有 `memory_view.compact_memory`；不修改 ±2 数字引用窗口、未定位来源回退、初始状态、完整 trace、反馈、菜单去重或省略区间。保留 entries 及历史 Parent/实际 Diff/执行背景。每条 trace 使用全限定历史步骤 ID。

仅在 Replay 模型视图的 memory 中追加：

- `pairs`：数组，每项为 context、完整 parent 引用、完整 candidate 引用；只包含真实归档声明且两侧来源均已进入视图的 Pair。
- `unpaired_runs`：当前历史来源中没有可见完整 Pair 的执行引用，含单侧来源或配对档案不可用；不暗示这些执行没有真实 counterpart。

```json
{
  "pairs": [
    {"context": "S1_R03", "parent": "S1_R03/P10", "candidate": "S1_R03/Q10"}
  ],
  "unpaired_runs": []
}
```

不展开其他历史执行，不复制轨迹，不生成历史步骤级对齐或新的 Pair evidence ID。Pair 索引是关系元数据，不替代行为证据。原有 Memory v3 format 标识继续描述底层投影；外层 Replay input_view 版本标识以上扩展，其他 Preconditioner 调用不受影响。

## 历史 Pair 的可信来源

`history_pair_sources(memory_directory, memory)` 先核对目录加载结果与指定 Memory 快照相同，再为每个历史 context 提供不可变 archive 文件绝对路径和 SHA256。投影时核对哈希、context 身份、归档 payload、所用历史编辑/执行/菜单与完整 Memory 一致，再读取原 pairs。

该旁路清单不属于业务 payload 或 Memory 存储 Schema，单独冻结为 `history_pair_sources.json`。重载直接核验清单中的不可变文件，不依赖之后可能改变的 Active 索引。

非空历史必须明确提供每个 context 的来源。确实不可获得的 context 可显式设为 null，其执行进入 unpaired_runs；不能静默猜配对。缺清单项、哈希变化、源内容不一致或非法 Pair 是技术错误。空 Memory 使用空清单。

## 模型消息、输出与校验

System 保留现有 Replay 主体及执行背景，追加原 Memory v3 格式说明和本视图说明。旧 knowledge 是待修订认识；未展示的详细状态不能推断。当前七字段事实不做语义摘要，不生成编辑归因或阶段划分。

输出仍为 `entries[{revises, knowledge, evidence}]`，空 entries 合法。现有 validate_entries 针对完整事实检查引用和修订；当前及历史步骤身份保持稳定。窗口外 trace 中可见的动作仍可引用，但不支持未展示的观察/菜单断言。结构通过不证明事实解释或归因成立。

Replay 不自动提交 Memory，也不决定 Gate。保持一次 generate 调用；失败明确记录，不转成空提案或 Keep。

## 版本与归档

新请求默认使用本视图；保留显式 `entries_sources` 旧视图。run.json 记录 input_view；旧归档没有此字段时只按旧视图读取，不静默迁移。两种视图不能互相复用运行目录。基础 Replay prompt_version 保持不变，新增视图版本管理格式说明和投影。

新归档保存完整 input.json、history_pair_sources.json、model_input.json、messages.json、实际 System prompt 与原始输出。load_replay 重建模型视图并逐项核对。原始 Memory commit 继续接收完整 bundle，不接收压缩后的模型视图。

生产 400000 字符默认预算保持；超过预算必须明确失败，不能裁剪当前轨迹。R05/R06 新视图仍超出默认预算，后续真实实验需显式冻结预算。本阶段不调用真实模型。

## 离线验收

验证当前 Pair 覆盖/身份/次序、完整轨迹字节等价内容、真实动作计数与中断；历史 v3 与既有实现完全一致、全限定引用、菜单正确；来源缺失/单侧/哈希变化/错误配对；模型视图篡改与版本误用拒绝；完整 Memory 提交/重载/幂等及后续 PC 投影兼容。R05/R06 使用完整冻结输入离线投影，不改旧档案、不执行新模型。
