# 请求、重试与成本

原协议与所有授权变更分别保留，见 PARALLEL_AMENDMENT.md、RESAMPLING_AMENDMENT.md、B_GENERATION3_AMENDMENT.md 至 B_GENERATION7_AMENDMENT.md。技术重试与收到输出后的追加生成分开统计。

实际逻辑调用 438：上游 13、Actor 425。实际 POST 441，journal 尝试 441，HTTP 429 共 2。授权后上游上限 13、Episode 上限 18、Actor 上限 900 均未超出。

Diagnosis 首次 HTTP 401 无模型输出，经用户授权同请求恢复，第二次 HTTP 成功，仍只有一份有效 Diagnosis。A 首次引用格式失败，A2 首次有效；B1–B6 依次为多余 checks、多余 from_note、理由引用、理由引用、Patch 原文匹配、理由引用失败；B7 首次有效。每次语义生成追加均有用户单独授权，不是技术重试。Editor A/B 各一次有效。没有响应修补、纠错提示、策略择优或失败预算重置。

| 上游调用 | HTTP | HTTP 发送至归档完成秒 | input | completion | total |
|---|---|---:|---:|---:|---:|
| grouping #1 | 200 | 30.30 | 35722 | 3513 | 39235 |
| diagnosis #1 | 401 | 14.51 | 未知 | 未知 | 未知 |
| diagnosis #2 | 200 | 73.63 | 37119 | 9202 | 46321 |
| A #1 | 200 | 125.68 | 245432 | 16922 | 262354 |
| B #1 | 200 | 97.57 | 246104 | 14369 | 260473 |
| A_retry_001 #1 | 200 | 63.06 | 245468 | 7147 | 252615 |
| B_retry_001 #1 | 200 | 94.07 | 246140 | 16287 | 262427 |
| Editor_A #1 | 200 | 84.50 | 2935 | 13776 | 16711 |
| B_retry_002 #1 | 200 | 116.29 | 246140 | 22946 | 269086 |
| B_retry_003 #1 | 200 | 158.65 | 246140 | 27231 | 273371 |
| B_retry_004 #1 | 200 | 106.42 | 246140 | 15233 | 261373 |
| B_retry_005 #1 | 200 | 72.86 | 246140 | 7763 | 253903 |
| B_retry_006 #1 | 200 | 166.14 | 246104 | 21474 | 267578 |
| Editor_B #1 | 200 | 36.81 | 2945 | 6843 | 9788 |

已知服务 usage：input 2,845,046、completion 361,154、total 3,206,200。reasoning 307,903 已包含在 completion，不重复计算。3 次尝试没有 usage，不能假定零费用；货币价格未知。缓存 input 是 input 子集，不另加。

累计 journal wait_seconds=2268.340，包含正常节流与排队，不全是故障退避。Actor 实测峰值并发 4；配置四并发、共享至少 3 秒节流，timeout=[60,300]。Parent 前三例在更早串行阶段，其余与 Candidate 使用用户授权并行；保留时间与实际并发差异为限制。

所有 A/B 追加实际正文与各自首次完全相同，两组 user payload 和参数完全相同。服务回报同正文 prompt_tokens 有 36 的差异，保留原 usage，不推断人为裁剪；服务端原因未知。请求字节数、模型、finish_reason、超时、耗时在 upstream_cost_audit.json 和各原始 journal。

每次失败响应、traceback 和解析结果保留。B3/B4/B6 的 Patch 可应用但完整编译失败；B5 在 Patch 应用阶段失败，不能混同。无真实 429 时，不宣称恢复逻辑获本轮限流验证；离线合成测试单列。Actor 格式/非法动作不因策略效果不佳追加生成。

## Actual 429 recovery evidence

| Logical call | HTTP sequence | Backoff | Recorded wait including queue | Environment actions / HTTP attempts |
|---|---|---|---:|---|
| episodes/B/P4/calls/step_06 | 429 -> 200 | 15s minimum; shared queue adds wait | 42.775s | 7 / 8 |
| episodes/B/P2/calls/step_06 | 429 -> 200 | 15s minimum; shared queue adds wait | 82.524s | 9 / 10 |

Both errors had no Retry-After header; the preset first backoff was 15 seconds. Both resumed within attempt 2. Two consecutive 429 responses activated the persistent single-request limit; no manual reset or additional episode was used. See B_429_recovery_audit.json.

B/P6 step 36 contains multiple action tags, with whitespace in the first tag. The unchanged first-tag extractor produced an empty action and Nothing happens. The offline key-action summary needed an empty-token guard; only analyze.py in this experiment was adjusted, with its prior version preserved. Raw responses, trajectories, Actor protocol and runtime stayed unchanged. See analysis_empty_action_fix.json and B_actor_empty_action_audit.json.
