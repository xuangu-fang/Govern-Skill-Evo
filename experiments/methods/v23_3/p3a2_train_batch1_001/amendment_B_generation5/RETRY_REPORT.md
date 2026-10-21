# 请求、重试与成本

原协议保留；并发与追加生成授权见 PARALLEL_AMENDMENT.md、RESAMPLING_AMENDMENT.md、B_GENERATION3_AMENDMENT.md、B_GENERATION4_AMENDMENT.md。技术重试与收到输出后的追加生成分开统计。

实际逻辑调用 300：上游 9、Actor 291。实际 POST 301，journal 尝试 301，HTTP 429 共 0。授权后上游上限 10、Episode 上限 18、Actor 上限 900 均未超出。

Diagnosis 首次 HTTP 401 Authentication Error，无模型内容；用户明确授权保持请求恢复，第二次 HTTP 成功，仍仅一个有效 Diagnosis。A1/B1/B2/B3/B4 都收到真实输出而后契约失败；A2、B2、B3、B4 是分别授权的新生成，不是技术重试。没有格式修补、纠错 Prompt、策略择优或失败预算重置。B4 之后停止该分支。

| 上游调用 | HTTP 状态 | 耗时秒（请求起止） | input | completion | total |
|---|---|---:|---:|---:|---:|
| grouping #1 | 200 | 30.40 | 35722 | 3513 | 39235 |
| diagnosis #1 | 401 | 14.58 | 未知 | 未知 | 未知 |
| diagnosis #2 | 200 | 73.74 | 37119 | 9202 | 46321 |
| A #1 | 200 | 125.79 | 245432 | 16922 | 262354 |
| A_retry_001 #1 | 200 | 63.16 | 245468 | 7147 | 252615 |
| B #1 | 200 | 97.68 | 246104 | 14369 | 260473 |
| B_retry_001 #1 | 200 | 94.19 | 246140 | 16287 | 262427 |
| B_retry_002 #1 | 200 | 116.41 | 246140 | 22946 | 269086 |
| Editor_A #1 | 200 | 84.61 | 2935 | 13776 | 16711 |
| B_retry_003 #1 | 200 | 158.77 | 246140 | 27231 | 273371 |

已知服务 usage：input 1,913,208、completion 255,023、total 2,168,231。其中 reasoning 221,146 已包含在 completion，不重复相加。1 次尝试缺 usage，不能假定零费用；货币单价/总价未知。缓存 tokens 是 input 子集，不另加。

journal 累计 wait_seconds=1268.802，包含正常节流/排队，不能全部称为故障退避。实际 Actor POST 峰值并发 4；请求配置四并发、共享至少 3 秒节流、timeout=[60,300]。HTTP 尝试的响应头、正文、异常堆栈及状态均在各 call/step journal。

A2/B2 与各自首次正文完全相同，但服务回报 prompt_tokens 各相差 36；原样记录，不能反推人为更改输入，服务内部计数原因未知。真实请求字节数、超时、finish_reason、响应模型汇总见 upstream_cost_audit.json；完整正文见各 request.json。

没有 429 不代表恢复逻辑已被本轮真实限流验证；技术包装器的合成离线测试单列。P6 A 第 13 步动作格式错误产生无效动作，是收到模型输出后的执行问题，不重试。B 编译失败是工程契约失败，不计为 ALFWorld 策略失败。
