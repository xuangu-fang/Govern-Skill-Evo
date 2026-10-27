# `(60, 300)` 真实重跑结果

**两组传输均成功；两组模型均因 completion 预算耗尽而未产生最终内容。** 没有获得实际 Update、Patch 或 Effective Plan，仍不构成有效语义对照。

本次是用户授权的新重跑：只调用 A/B，复用上一轮真实 Diagnosis。旧归档完整保留；只调整实验传输配置，不修改正式生成器、Prompt、模型或采样参数。

## HTTP 实测

| 指标 | A：自由替换 | B：Patch |
|---|---:|---:|
| 实际 HTTP 请求数 | 1 | 1 |
| 自动重试 | 0 | 0 |
| 正文编码后字节数 | 1,629,326 | 1,632,149 |
| Content-Length | 1,629,326 | 1,632,149 |
| 传给 HTTP 层的 timeout | `(60, 300)` | `(60, 300)` |
| 正文发送时 socket timeout | 60.0 秒 | 60.0 秒 |
| HTTP 状态 | 200 | 200 |
| 单次 HTTP 耗时 | 111.80 秒 | 116.99 秒 |
| 完整阶段耗时 | 111.90 秒 | 117.13 秒 |
| 响应模型 | deepseek-v4.1-flash | deepseek-v4.1-flash |
| finish_reason | length | length |
| 最终 content 字符数 | 0 | 0 |

字节数来自 requests PreparedRequest 的实际编码 body，不是格式化 request.json 文件大小。HTTP audit 记录只保存发送块长度、时间、socket timeout，不保存认证头。完整原始 HTTP 响应、模型 envelope 和最终空内容均照实保存。

本机 urllib3 的调用顺序是设置 connect_timeout → `conn.request`（含正文发送）→ 设置 read_timeout → 读取响应；因此 `(60, 300)` 的第一项也作用于请求发送阶段。它不是独立 write_timeout，也不是 60 秒总耗时。两组均记录正文发送时 socket 为 60 秒，随后收到 HTTP 200，表明本次不再被旧 10 秒传输条件阻断。上一轮没有完整堆栈，本报告不追补不存在的旧栈证据。

## 新的失败阶段

本次网络传输和 HTTP 响应解码均成功。阶段在检查 finish_reason 时停止，没有进入模型 JSON 解析、Patch 应用或 compiler；不能标记为非法 JSON、Patch 定位错误、Keep 或策略质量失败。

两组服务端返回的 16,384 completion tokens 均计为 reasoning，最终 content 为空。遵守既有预注册：截断不技术重试，不增大 max_tokens，不把内部 reasoning 当作正式 Update，也不人工补出 JSON。阶段完整异常堆栈分别在：

- [A traceback](runs/A/traceback.txt)
- [B traceback](runs/B/traceback.txt)

异常是本地完整性门的 `AssertionError: Model response did not finish normally`，不是新的网络超时。HTTP 成功所以没有 HTTP 层异常堆栈；若传输异常，入口会另存每次请求的 traceback。

## 参数与费用

仍为 temperature=1、Thinking enabled、reasoning_effort=medium、max_tokens=16384、stream=false，读取超时 300 秒。A/B 请求 body 与上一轮分别完全相同，user message 在两组之间完全相同，没有裁剪 Memory。

| usage | A | B | 本次合计 |
|---|---:|---:|---:|
| prompt_tokens | 474,697 | 475,369 | 950,066 |
| completion_tokens | 16,384 | 16,384 | 32,768 |
| 其中 reasoning_tokens | 16,384 | 16,384 | 32,768 |
| total_tokens | 491,081 | 491,753 | 982,834 |

reasoning 已包含在 completion 内，不重复计费或加总。货币费用未返回，记未知。表内仅为本次两次请求，不重复计入上一轮 Diagnosis，也不猜测旧失败请求的用量。

## 归档

- [A 实际请求](../../../../artifacts/methods/v23_3/p3a_transport_retry_001/runs/A/http/001/request.json)、[发送事件](../../../../artifacts/methods/v23_3/p3a_transport_retry_001/runs/A/http/001/send_events.json)、[HTTP 原文](../../../../artifacts/methods/v23_3/p3a_transport_retry_001/runs/A/http/001/http_response.txt)、[模型 envelope](runs/A/response.json)。
- [B 实际请求](../../../../artifacts/methods/v23_3/p3a_transport_retry_001/runs/B/http/001/request.json)、[发送事件](../../../../artifacts/methods/v23_3/p3a_transport_retry_001/runs/B/http/001/send_events.json)、[HTTP 原文](../../../../artifacts/methods/v23_3/p3a_transport_retry_001/runs/B/http/001/http_response.txt)、[模型 envelope](runs/B/response.json)。
- [实际超时配置](config/transport.json)、[完整执行汇总](results/execution_summary.json)、[三项离线检查](../../../../artifacts/methods/v23_3/p3a_transport_retry_001/results/offline_tests.log)。

没有创建虚假 parsed/Effective 文件或以 null 冒充合法停点。没有调用 Diagnosis、Editor、Actor、Replay、Gate、Memory 更新或完整进化。
