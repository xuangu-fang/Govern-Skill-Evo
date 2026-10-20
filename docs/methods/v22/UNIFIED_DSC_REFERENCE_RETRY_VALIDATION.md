# V22 引用契约第二次真实验证

按用户追加授权，于 2026-10-16 使用完全相同的冻结请求再调用一次。未更改 profile、Prompt、08 R2 配对证据、官方 deepseek-flash 参数或 65,536 输出上限。首次失败及原报告保持原样。本次独立保存于 `artifacts/methods/v22/22_reference_consistency/recovery_01`。

## 结果

HTTP 200，finish_reason=stop；完整 JSON 和生产解析通过，**整体契约失败**：`Finding has missing/invalid sources.`

- 所有 Findings.about / open.about 引用合法；没有把 group/event 当作评价对象。
- 唯一未知 refs 是 f5 中的历史 Effect `72086ed83fd32507d9c006cd54312074e694e26b035d51d63c3c7ed1ecde9684:m3`。它可以属于 about，但不是当前 sources 中的执行证据，不能直接放入 Findings.refs。
- 4 条非空 retire_limits 的精确字段、类型、Effect/replace、ACTIVE index 和 Finding 关联专项检查通过；由于整体契约已失败，不能将此视为整份 Memory 通过。
- 未修改原始输出、移除非法 ref、绕过校验或发布 Memory。未因这个结果扩大算法修复。

这是模型把评价对象当作证据来源的问题；本次没有证据表明存在标准引用名称冲突。字段合法性也不证明限制退役或行为解释的语义正确，本次不据此宣布统一机制已通过完整真实验证。

## 消耗与边界

| 输入 Token | 输出 Token | 其中推理 Token | 缓存命中 | 耗时 |
|---:|---:|---:|---:|---:|
| 61095 | 29392 | 26251 | 60928 | 148.18 秒 |

按此前归档价格口径估算本次约 0.237907 元，不是账单确认。完整原请求、HTTP 响应、usage、解析 JSON、失败信息和专项分析均保留。此次 1 次请求；连同首次截断共 2 次。0 ALFWorld episode，0 正式 Skill/Memory 发布，不追加第三次。

来源：`recovery_01/cases/r2_references/result.json`、`parsed.json`、`response.json`、`recovery_01/analysis.json`。旧结果哈希核验见 `prior_archive_verification.json`。
