# V23.3 P1：最小 Patch 与编译集成

前提见 [P0 审计](V23_3_EDITOR_PATCH_AUDIT.md)。复用 `v23.editor.apply_patch`，不修改 V23、不移植 P3-C2 协议、不新增 Patch 引擎。

## 1. 单一选择

原 Adjustment 外壳 `from/to/basis/reason` 和顶层 `decision/reason/adjustments/checks` 保留。模型侧 `to` 项的 **`text` 改为 Editor 已有的 `patch` 字符串**；确定性程序应用后恢复 `text`，再调用原编译器。模型不能同时交 patch 和最终 text。

为什么需要这一处适配：V23 编译器严格只接受 `id/text`，Editor 的 `patch/reason` 又没有 Update ID 和多 Update 来源。原 `from/to` 已解决身份、撤回和编译语义，复用它比另建 `edits/update_id/operation/role/anchor` 更小。文件路径不承担 Update 身份。

P2 最小支持范围：

- 每项 `from` 恰好一个 Original ID；`to` 为空表示整项撤回，或一个 `{id: 原ID, patch: 非空Diff}` 表示替换。
- 每个 Original ID 最多被消费一次；同一 Update 的多处修改放入一个多 Hunk Patch。多个 Update 各一项 Adjustment，同一冻结 Original 上独立应用，全部成功后一次编译。
- Keep 不输出对应 Adjustment；完全 Keep=`ready, adjustments:[], checks:null`。
- `no_change` 必须显式撤回所有 Updates 且 `checks:[]`；它不是 Keep。
- `need_evidence` 仍要求 `adjustments:[], checks:null`。Update 的 `patch:null/""` 不再复用 Editor 状态含义，而是拒绝；不存在第二套停点协议。

本阶段不支持新 ID、合并/拆分 Update 的结构重排。这是轻量适配器的明确子集，**不是 V23 编译器失去这项能力**。R04/R05/R06 的必要行为修改可在原 text 内重写、删除子句、插入要求或跨多项协调，无一要求重排 ID；不能为了概念形式增加多源文本拼接规则。未来若案例确需结构拆合，应记录为适配器能力缺口，再设计兼容方案；不得伪装成 need_evidence 或回退自由 text。

## 2. 最小示例

以下仅演示格式，假设 Original `u1.text` 精确为 `"Old guidance.\n"`；不是案例策略或运行结果。

```json
{
  "decision": "ready",
  "reason": "The current evidence supports changing this requirement.",
  "adjustments": [
    {
      "from": ["u1"],
      "to": [
        {
          "id": "u1",
          "patch": "--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1 +1 @@\n-Old guidance.\n+Revised guidance.\n"
        }
      ],
      "basis": ["P1:1"],
      "reason": "Explain the specific edit-response relationship and its limits."
    }
  ],
  "checks": null
}
```

程序将 `to[0]` 转为 `{"id":"u1","text":"Revised guidance.\n"}`，其他字段不改。`P1:1` 必须真实存在于输入；示例不授权造引用。真实单行无 LF 文本需标准 EOF 标记，不自动规范化。

虚拟 `SKILL.md` 文件头无需更名为 `UPDATE.md`，函数只处理字符串，不读写该文件。实际目标来自 `from` 绑定的 Original text。无需 SHA-256、额外 old_text、专用锚点或路径映射。

## 3. 确定性边界

拟议 `normalize_update_patches(result, payload)`：

```text
check exact top-level / adjustment / replacement keys and container types
validate source IDs, singleton cardinality, retained IDs and no repeated sources
copy result to an in-memory normalized result
for each adjustment:
    if to == []: preserve withdrawal
    else:
        source = payload.plan.updates[from[0]].text
        require nonempty, non-whitespace patch string
        text = v23.editor.apply_patch(source, patch)
        replace {id,patch} with {id,text}
effective = v23.preconditioner.compile_effective_plan(normalized, payload)
publish normalized + effective only after all operations succeed
```

返回值可以是函数内部二元组，无需新增模型 Schema。程序不根据 reason 的措辞补写规则、迁移 Checks、重试 Patch 或重排 Hunk。

| 能保证 | 不能保证 |
|---|---|
| ID 确实属于冻结 Original；精确行坐标/上下文/换行；多 Hunk 应用；不发布部分结果 | 某 ID 内选择了正确的语义对象，引用内容真正支持新要求 |
| 未被 Patch 改动的行、未消费 Update 不变；Goal 由原编译器复制 | 单行替换内部无附带承诺，或者旧文本本来正确 |
| 合法 Adjustment 结构/引用、Checks 无悬空 ID、正常停点 | 自然语言跨 Update 一致性、配套必要性、Actor 可观测性、成功率 |

保持实例快照和现有持久化逐项相等检查，不设计新哈希协议。仅靠补丁上下文也不证明整份 Plan 未变；重载必须先核对冻结上游输入，再重做转换与编译。

## 4. 归档与 Editor 入口：必须处理的真实耦合

V23 `load_preconditioner` 要求 `response.content` 解析结果等于 `parsed.json` 与 `preconditioner.json`，且按 V23 Prompt 重建消息。V23.3 的模型响应含 Patch，正式 Adjustment 含 text，二者不相等。**不能篡改 raw response，不能伪造 V23 请求让旧加载器通过。**

P2 最小方案：

1. `v23_3.preconditioner.run_preconditioner/load_preconditioner` 保存并验证本版 Prompt、冻结 input、response/raw/parsed；`parsed.json` 保持模型 Patch 原貌。`preconditioner.json` 保存转换后的正式 Adjustment，`effective_plan.json` 保存原编译结果。只有本版 loader 理解这一派生关系。
2. loader 重载时从 raw 重新解析 Patch → normalize → compile，逐项比较派生文件与输入；不要把磁盘上的正式 Adjustment 当新的模型真值。
3. 新建本版薄 Editor 入口，从上述 loader 获得 saved handoff；调用原 `editor_input/messages_for/validate_editor/actual_diff` 等函数，使用原 Editor Prompt、输出契约和归档布局。此入口只替换上游读取与衔接，不能通过全局 monkeypatch V23 loader 实现。
4. 原 `editor.run_editor` 在函数开头硬编码调用 V23 loader，没有 loader 参数。因此不能原样调用整段 runner；薄入口需保留必要的调用/保存流程。不要把这个实际工作隐藏为“只改 Prompt”。
5. Editor 保存的 `upstream.json` 含规范化 `preconditioner`、Original 和 `effective_plan`。原 `editor.load_editor` 通过原 compiler 重验这一 handoff，并重算 Skill Patch；它本身不重新加载 Preconditioner 目录，因此现有 Replay `build_replay/load_editor` 的数据接口可复用。**跨阶段恢复时本版协调入口仍须先重载 V23.3 Preconditioner，并用 `expected_preconditioner` 核对 Editor 上游**，否则无法验证 Patch 原始响应到 handoff 的派生链。

Editor 模型输入和策略职责保持不变；“入口适配”不等于把策略审核移到 Editor。P2 不接管完整 `evolution.run_round`，不新增真实执行入口；以后接入闭环时再显式路由本版 loader/runner，正式 V23 默认链不动。

## 5. P2 最小函数与验收范围

| 拟议位置/函数 | 必须完成的责任 |
|---|---|
| `v23_3/update_patch.py::normalize_update_patches` | 选择精确原 text，调用原 apply_patch，构造原 Adjustment，调用原 compiler；不实现新 Diff 解析器 |
| `v23_3/preconditioner.py::messages_for` | 复用 `preconditioner_input/render_prompt`，换成本设计的单次决策与输出契约；不加 Memory 检索调用 |
| 同文件 `run_preconditioner/load_preconditioner` | 一次生成的注入式入口、原始/派生文件分离、重载一致性；先用离线固定响应测试 |
| `v23_3/editor.py::run_editor` 薄适配 | 上述加载边界；复用原 Editor 核心与归档契约，不改模型输入 |
| `tests/skill_evolution/v23_3/` | 真实单行/多行 Update、跨 Update、撤回/Keep/停点、失败不发布、Checks、原始响应与派生文件、Editor 纯交接；语义风险应能结构通过 |

不新增通用保存框架、响应模型、依赖图、审核器或自动 Prompt 修复器。P2 是未来实现范围，本次只设计，尚无这些 Python 文件。
