# 新版筛查：单次三轮运行协议

使用已冻结的 `v23_5_obvious_fact_screen_v1` Prompt、v2 去重输入和运行前参考基准。模型只接收已冻结 messages；不发送基准、判定边界中的示例、人工审阅说明或旧版输出。

沿用原 Replay/Verifier 模型配置：deepseek-v4.1-flash，temperature=1.0，reasoning_effort=medium，thinking enabled，max_tokens=32768，timeout=300 秒，非流式。三轮独立并发，各只请求一次；无自动传输、截断、格式或语义重试。完成的调用不因重复执行脚本而重发；中断且结果未知也不自动重复请求。

先报告有效响应和目标覆盖，再按预先基准计算 primary 集 16 条（4 条应拦截、12 条允许通过）的标签对照。两条 review_only 无论输出如何都单列。逐项判断 4 个 required_findings 是否被具体反馈命中；仅 CONFLICT 标签一致不代表命中了目标错误。记录额外问题、错误理由及基准分歧，不根据输出改写冻结标签。

保存实际 request、原始 HTTP、usage、完成状态、正文和严格校验结果；计入所有尝试的输入、输出及推理 Token。未知 usage 不按零算；没有内部单价时不估算货币费用。没有有效输出的条目不算检出、漏检或正确。

本次是新目标的开发集实测。基准由 Codex 审阅、未由人类确认，且已见过旧输出；不是盲评。目标和输入结构均已改变，不将与旧版的数值差异归因于去重或 Prompt 单一因素，也不对旧输出重新评分。

不运行 Replay、Repair、Actor，不提交 Memory，不发布 Skill。运行产物独立存放于 `artifacts/methods/v23_5/verifier_fact_screen_run_001/`，不覆盖旧实验。
