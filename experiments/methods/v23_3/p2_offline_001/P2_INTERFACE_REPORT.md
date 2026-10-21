# V23.3 P2 接口报告

## 实际数据链

```text
V23 load_grouping
  → V23.3 Diagnosis（原 diagnosis_input / validate_diagnosis）
  → Original {goal, updates:[{id,text,basis}], checks}
  → 原 preconditioner_input + 冻结 Memory {entries,sources}
  → 一次 Preconditioner generate：{decision,reason,adjustments,checks}
       adjustment = {from:[原ID], to:[{id:原ID,patch:Unified Diff}] 或 [], basis,reason}
  → normalize_update_patches：原 editor.apply_patch(Original.text, patch)
  → 原格式 adjustment.to:[{id,text}]
  → 原 compile_effective_plan
  → Effective Plan 或合法停点
  → V23.3 Editor 入口 + 原 editor_input/messages_for
  → 一次 Editor generate：原 {patch,reason}
  → 原 validate_editor/apply_patch/actual_diff
  → Candidate Skill 或 Editor 自身停点
```

Diagnosis 输入只有当前 Parent/Grouping/执行及背景，不含 Memory。多行只是 `text` 字符串组织方式；不增加 Schema 字段，不修改已有单行记录。

Update Patch 的虚拟 `SKILL.md` 文件头沿用原引擎，实际目标是 `from` ID 对应的 Original text。Editor Skill Patch 的目标才是完整 Parent Skill；两种 Patch 不混用。

## 函数与恢复

| 本版函数 | 输入/输出及保证 |
|---|---|
| `normalize_update_patches(result, payload)` | 返回 `(normalized, effective_plan)`；先校验单源/同 ID/不重复消费，所有 Patch 和编译成功才返回；不改输入 |
| `diagnosis.messages_for/run_diagnosis/load_diagnosis` | 独立 Prompt；原 Plan Schema；按记录 Grouping 路径核对输入，再重新解析响应 |
| `preconditioner.messages_for/run_preconditioner/load_preconditioner` | 原证据选择和 Memory 契约；本版 Diagnosis loader；raw→patch→text→compile 重算 |
| `editor.run_editor/load_editor` | 本版 Preconditioner loader 先验证 raw 血缘，再用原 Editor 消息、校验与 archive loader |

runner 均接收已有 `generate(messages,directory)`，没有新模型请求框架。本次注入 Fake；未来可注入已有请求适配器，但本轮没有创建真实请求。HTTP 原始响应如由原请求适配器写入，归其原有逻辑保存；本次 Fake 只有明确标记的模型响应 envelope，不虚构 HTTP 文件。

调用配置须与 generator 配置一致。已有输出目录只重载，不能触发第二次生成。实际大体积冻结输入显式使用 `max_input_chars=4000000`；默认仍为 100000，不自动截断。

## 原始与派生文件

| 文件 | 真值/派生关系 |
|---|---|
| `input.json`, `messages.json`, `prompt.md`, `run.json` | 冻结输入、当前版本消息和调用元数据；与上游和本版 Prompt 重建结果比较 |
| `response.json`, `raw_output.txt` | 原 generator 返回及原 content，字节保留；不能用规范化结果覆盖 |
| Preconditioner `parsed.json` | 原 content 解析的 **Patch 形式**，与原始响应一致 |
| `preconditioner.json` | 程序派生的原格式 Adjustment，含应用后 `text` |
| `effective_plan.json` | 原 compiler 的结果，合法停点为 null |
| `validation.json` | 只有验证成功才为 valid；技术错误记录类型与信息 |
| Editor `upstream.json` | 原始 Diagnosis/Parent/Memory + 规范化 Adjustment + Effective，重新与本版 loader 比较 |
| Editor `parsed.json` / `editor.json` | 原 Editor 模型对象，两者均应等于响应解析结果 |
| `patch.diff`, `candidate.md`, `actual.diff` | 原 Editor 应用与 diff 规则；无 Candidate 的合法停点不保存 Candidate/diff |

新 Preconditioner loader 不要求 `parsed.json == preconditioner.json`，而要求后者等于重新应用前者的结果。旧 loader 会拒绝本版 Prompt/派生关系，不伪造旧请求来绕过它。

恢复验证会沿归档的路径读取真实上游；迁移目录需要保留可用路径，本轮没有设计可搬迁归档协议或哈希体系。文件相等与来源核对用于一致性，不是抵抗全面协同篡改的密码学证明。

## 决策和程序责任

Preconditioner 负责选择方向、范围、强度、配套与独立探索，并把执行条件写入 Update。程序只负责精确应用、基本冲突/引用检查、全部编译、未改项/Goal 保留、原始与派生一致性。

不支持的结构合并/拆分/新 ID 直接作为技术契约错误拒绝，不转成 `need_evidence`。对旧实现绑定 Goal 的语义冲突，仍由模型按 Prompt 判断；编译成功不意味着 Goal 合理。

Checks 只检查存在的 Update IDs，不证明问题可观测；basis 只验证引用路由，不证明证据支持。修改行内部的无据承诺、必要配套是否真实必要、模型策略是否有效，都需要后续语义与执行评价。
