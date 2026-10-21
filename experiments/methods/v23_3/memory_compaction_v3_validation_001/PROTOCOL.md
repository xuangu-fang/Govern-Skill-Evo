# Memory v3：完整 trace 来源 ID 与评分引用契约

仅在新实验目录执行。保持 v2 的 active entries、source 集合、命令池、显式 before/after、±2 窗口、动作、反馈、结果及遗漏范围。只将完整 trace 中的局部 step ID 改为带历史来源的完整 ID，与 detailed_steps 一致。不增加预计算答案或检索/选择 LLM。

## 离线门

对 R04/R05/R06/P3A_A/P3A_B 检查：每条完整 trace ID 全局唯一、所属 source 正确，与 detailed_steps 对齐；逆向去掉历史前缀后，全部视图与 v2 一致，再验证原始轨迹。加入同名 Q6:26 跨历史来源回归检查，以及 wrong-source、动作反馈改变等拒绝测试。比较输入 token 开销，A/B user 输入须一致。

仍使用原 R05 11 项和 R06 14 项事实。whole_trace 和 action_order 的题目明确要求原样返回完整 trace ID，其参考答案同步添加来源前缀；其余答案不变。operation_precondition 只将文字版本号 v2 改为 v3。地址归一化后参考事实与旧答案相等。

保留严格字段/类型/值评分，不接受缺少来源的局部步骤 ID，不自动给错误来源补前缀。题目和参考答案在调用前冻结，参考答案不进入请求。

## 实际验证预算

离线通过后，R05、R06 各一次，最多 2 次逻辑调用 / 2 次 HTTP；无重试、无补采样。两例独立，不因第一例失败跳过第二例。

保持原内网 deepseek-v4.1-flash、temperature=1、thinking enabled、reasoning_effort=medium、max_tokens=16384、stream=false、timeout=(60,300)。冻结请求、实现、协议、格式说明和参考答案；实际 HTTP、发送超时、最终输出、usage、评分与异常（若有）归档。

两例都正常结束且逐题全对才通过。失败不事后放宽评分。该结果只覆盖已知开发案例，不构成稳定性或生产策略效果证明。

本轮没有生产 Patch 生成、Editor、Actor、Replay、Memory commit 或正式接入。完成两次检查与报告后停止。
