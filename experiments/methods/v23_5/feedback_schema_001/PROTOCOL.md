# Schema 定位反馈验证 001

复用 feedback_smoke_001 中 schema 案例的同一份历史失败正文、同一当前 Prompt 和 Knowledge Only 事实。该正文的四项 Adjustment 均缺少 `to`。仅重新生成诊断，明确列出四个数组下标、Update ID 和缺失字段；不修改失败正文。

历史失败作为第 1 次尝试导入新目录，并标注来源，不记作本轮 API 请求。调用未经修改的生产 `feedback_retry.run_stage`，总上限仍为三次，因此本轮最多新增两次请求。下一次内容失败替换最近反馈；技术错误保留当前请求，截断不作为格式反馈，复用缓存不增加请求额度。取得完整有效输出即停止。

配置：deepseek-v4.1-flash，max_tokens=32,768，temperature=1.0，reasoning_effort=medium，thinking enabled，timeout=300 秒。读取原有路由和鉴权；实际请求和原始响应完整留档，不归档密钥。

因为历史输入来自 V23.4，本实验用小型评估适配器对接冻结材料，调用生产解析、输出校验、反馈构造和重试调度；不伪造 V23.5 上游 lineage。输出保存后重新解析和完整校验，重载异常不进入内容反馈。实验不运行 Actor，不发布 Skill 或 Memory，不改写原六次请求记录。

首要观察：是否一次补齐所有缺失 `to`，是否重复相同 schema 错误，以及有界续试能否通过完整校验。后续错误可能原已存在，不能自动视为反馈新增。单个历史案例不能证明整体成功率改善；本轮没有增加新的原样对照组。

运行：`PYTHONPATH=. python -u experiments/methods/v23_5/feedback_schema_001/run.py run`
