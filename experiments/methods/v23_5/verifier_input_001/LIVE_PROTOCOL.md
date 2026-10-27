# 第三阶段：独立审阅基准与真实核验

本次仅运行 Verifier，不运行 Replay、Repair、Actor，不修改正式 Memory 或 Skill。

## 先冻结审阅，再运行模型

`results/reference_review.json` 覆盖全部 18 条 Knowledge，在任何本次真实 Verifier 响应产生前完成。审阅者是 Codex 主助手，不是人类标注员；`human_reviewed=false`。它是待用户复核的独立审阅基准，不冒充已经完成的人工金标准。此前对已知错误的讨论可见，因此也不声称对已知案例盲法。

审阅直接核对完整动作过程、结果、相关原始观察/候选及实际冻结 source_records，分别记录：

- `archive_assessment`：完整档案下的陈述质量。SUPPORTED 11 条、CONFLICT 6 条、UNCERTAIN 1 条；不确定项从完整档案准确率指标中排除。这不是新增 Verifier 输出类别。
- `expected_verdict_given_input`：仅凭实际提供的材料，按已冻结 Prompt 应返回的判定。CONFLICT 13 条、SUPPORTED 5 条。
- 每条说明依据、档案证据位置及实际已提供的证据。程序性事实定位辅助审阅，但不是另一个 LLM 的判定结果。

这一区分防止把真实但缺少终态/全程证据的陈述被拒绝，混同于事实错误检出或纯粹误判。模型只收到第二阶段已冻结的 messages，不会收到审阅标签、说明或已知案例答案。运行前复制基准并冻结 SHA-256；运行后不覆盖原标签，任何修订须另外记录。

## 模型配置与请求边界

沿用三轮原 Replay 的同一配置：deepseek-v4.1-flash、max_tokens=32768、temperature=1.0、reasoning_effort=medium、thinking enabled、timeout=300 秒、非流式请求，通过现有 grouping.live_generator 调用已配置服务。完整配置冻结在运行目录 protocol.json；凭据只从现有环境/.env 读取，不写入产物。

每轮取得一份完整响应，三轮独立并发。仅 HTTP 401/408/429/5xx 或传输异常可以原样重试，含首次最多三次；schema 失败、长度截断、语义判定不理想均不重新采样。保存原始 HTTP、实际请求、usage、响应、输出和校验结果。中断且请求结果未知时不自动重发，避免重复计费；已有完成响应不重复请求。

本次固定上限三次是离线实验的传输重试预算，不改变生产配置的请求额度。

## 预先确定的评价口径

- 报告请求完成、结构合法率和逐条判定；结构失败不冒充有效输出。
- 相对提供输入的预先标签，统计 TP/FN/FP/TN、CONFLICT precision/recall、正确项误拒。
- 另报完整档案下已知错误条目的拒绝率；单纯拒绝不能算发现了具体错误。
- 对三个预先列出的已知问题检查反馈是否明确命中错误内容；给每项保留原 issue 和判读说明。
- 对完整档案正确但输入证据不足的条目，单独统计被拒绝情况。
- 保留对照分歧和基准自身歧义，不能根据模型结果偷偷改写预先标签。
- 汇总全部尝试的 API 输入、输出、推理、缓存 Token 和耗时；缺失 usage 为未知，不按零计。未掌握内部服务价格时金额为 null，不臆造费用。

一次小样本实验只能用于判断机制是否值得继续，不能据此声称稳定准确率、修复效果或下游任务收益。

运行入口：`run_verifier.py prepare` 冻结协议与基准；`run_verifier.py run` 发起真实请求；`run_verifier.py verify` 只重验冻结内容。产物位于 `artifacts/methods/v23_5/verifier_run_001/`。

## 运行后的用户授权补充

首轮 R01 返回 `finish_reason=length`，原协议下记录为失败且没有自动重新采样。用户获知后明确回复“可以重试”。据此单独创建 `artifacts/methods/v23_5/verifier_run_001_retry_R01_001/`，在调用前记录授权和来源失败，只重试 R01；Prompt、输入、原审阅标签和模型配置保持一致。首次三轮结果及失败记录继续保留。汇总同时列出首次结果与补充重试，并计入所有尝试的 Token；不把重试成功追溯改写成首次成功。

第一次补充重试同样因长度上限失败。用户再次明确要求“继续重试”，据此创建 `artifacts/methods/v23_5/verifier_run_001_retry_R01_002/`；同样只运行 R01，保持原配置和输入不变，单独归档，不覆盖前两次响应。
