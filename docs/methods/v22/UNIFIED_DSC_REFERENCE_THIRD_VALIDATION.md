# V22 第三次引用契约真实验证

按用户再次授权，于 2026-10-16 追加一次相同冻结请求。原始材料、Prompt、profile、官方 deepseek-flash 参数和 65,536 输出上限均未改变。前两次档案和报告的哈希检查通过；本次独立保存于 `artifacts/methods/v22/22_reference_consistency/recovery_02`。

## 程序结果

HTTP 200，finish_reason=stop；完整 JSON、生产解析、整个 Replay／Memory 契约均通过。5 条 Findings、3 条 Memory delta、3 条非空退休操作通过既有严格验证，包括 about 对象、当前 refs、Watch 覆盖、Effect 替换、退休字段和证据关联。程序完成了隔离的 Memory 应用及消费视图构建，产物明确标记为 probe / not_published，没有正式发布。

## 语义抽查与限制

契约通过不等于事实判断全部正确。抽查仍发现：

- f5 称 G2 四项任务都在 Parent/Candidate 成功，实际 G2 含 T2（P6/C6，train:0024），两者均失败；只有另外三项双侧成功。
- f2 正确描述 C8 放置第一个物体后去 sidetable 1、tvstand 1，却进一步称匹配“返回原来源为空后”的规则触发。Candidate 没有返回原 sidetable 2，不能用 Parent 的机会代替 Candidate 的机会。

这些是行为解释问题，未导致字段或引用契约失败。本次不修改 Prompt、不修补模型输出，也不声称完整语义正确。三次同条件请求分别截断、来源契约失败、完整契约通过，必须一起保留；不能仅选择第三次宣称模型稳定可靠或算法有因果收益。

## 成本与停止边界

输入 61,095 Token；输出 55,571 Token，其中推理 51,876；缓存命中 60,928；耗时 246.38 秒。按此前归档价格口径估算约 0.447339 元，非账户账单确认。

本次只发送 1 次请求，累计 3 次均有独立授权和原始记录。0 ALFWorld episode，0 正式 Skill/Memory 发布，不继续追加请求或启动流式实验。此次表明该真实材料下模型能够完整满足新引用契约，但仍不足以证明稳定遵从性或学习解释的准确性。

原始证据：`recovery_02/cases/r2_references/{request,response,parsed,result,contract_result}.json`；专项说明：`recovery_02/analysis.json`；旧档案核验：`recovery_02/prior_archive_verification.json`。
