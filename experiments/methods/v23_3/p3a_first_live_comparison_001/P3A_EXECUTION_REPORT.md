# P3-A 执行报告

**取得真实合法的多行 Diagnosis；A/B 均在传输阶段失败，未形成有效配对。** 已按预注册预算结束，不追加模型请求。

## 调用与实际结果

| 阶段 | 逻辑调用 | HTTP 请求 | 自动重试 | 实际结果 | 阶段耗时 |
|---|---:|---:|---:|---|---:|
| V23.3 Diagnosis | 1 | 1 | 0 | HTTP 200，stop，合法 revise | 62.66 秒 |
| A：V23 自由替换 | 1 | 3 | 2 | 3 次 ConnectionError，未收到 HTTP/模型响应 | 45.48 秒 |
| B：V23.3 Patch | 1 | 3 | 2 | 3 次 ConnectionError，未收到 HTTP/模型响应 | 45.50 秒 |
| 合计 | 3 | 7 | 4 | 0 个实际 Effective Plan，0 个有效配对 | 不作为服务端推理时间比较 |

阶段耗时含本地处理；A/B 包含预注册的 5 秒、10 秒重试等待。所有请求保持原 body 与参数，均通过与冻结请求的相等检查。7 是客户端开始的 HTTP 请求数，不保证服务端收到并执行了全部请求。总预算的 9 次是每阶段上限之和，Diagnosis 未用的重试额度不能转移给 A/B。

六次失败均为：

```text
ConnectionError: ('Connection aborted.', TimeoutError('timed out'))
```

单次失败耗时约 10.10—10.16 秒；没有 HTTP 状态码、响应正文、finish_reason、usage 或响应模型。该异常不能确认是服务端上下文拒绝、模型容量不足或策略错误，也不能仅根据约 10 秒耗时断定具体网络根因。

按预注册，它属于无可用模型结果的暂时性连接故障，可使用最多两次技术重试。最后失败后停止，未改变超时、Prompt、Memory、模型参数或重试上限。B 仍按固定顺序执行，没有因 A 失败换案例或输入。

## 固定参数与共同输入

请求模型均为内网 `deepseek-v4.1-flash`，temperature=1、Thinking enabled、reasoning_effort=medium、max_tokens=16384、stream=false，连接/读取超时为 10/300 秒。原始正式 R05 使用官方路由 deepseek-flash；本轮记录该来源差别，只控制本轮 A/B 路由一致。

两组 user content 逐字符串相等，包含相同真实 Original、Parent、P1/P3/P6/P7/P8/P10、G1—G4、103 个 command_sets 和七条真实 Active Memory 的完整 knowledge/sources。system Prompt 为各自既有正式版本，未更改。

消息大小：A 1,629,114 字符 / 1,629,132 UTF-8 字节；B 1,631,947 字符 / 1,631,961 字节。差异来自方法 Prompt。已通过冻结的工程大小检查，但不把字符检查当作服务端上下文接受证明。未裁剪任何输入，未执行容量探测。

## 原始结果及错误归档

- [冻结 Diagnosis 请求](requests/diagnosis.json)、[实际请求及 HTTP 原文](runs/diagnosis/http/001/)、[解析与验证](runs/diagnosis/)、[Diagnosis 门](results/diagnosis_gate.json)。
- [冻结 A 请求](requests/A.json)、[A 三次请求与逐次错误](runs/A/http/)、[A 阶段结果](results/A_execution.json)。
- [冻结 B 请求](requests/B.json)、[B 三次请求与逐次错误](runs/B/http/)、[B 阶段结果](results/B_execution.json)。
- [逐请求汇总](results/execution_summary.json)、[共同输入核查](results/common_input_checks.json)。

A/B 没有模型输出，故不创建虚假的 response、parsed、preconditioner 或 effective_plan 文件。尤其不把缺失 Effective 写成 null：null 会混淆合法 no_change/need_evidence 与技术失败。各组 `validation.json` 标明 transport 阶段无效；这不是 Schema、Patch 或 compiler 拒绝了一份实际输出。

## Token 与费用

唯一已返回 usage 来自 Diagnosis：

| 指标 | 实际返回 |
|---|---:|
| prompt_tokens | 65,593 |
| completion_tokens | 8,815 |
| 其中 reasoning_tokens | 7,951 |
| total_tokens | 74,408 |

reasoning 已在 completion 内，不再相加。六次失败请求的 usage 未返回，不能记作零或用估计替代实际用量。74,408 是已观测用量，不是完整实验费用上限；货币费用未知。

本轮 Editor、Actor、ALFWorld、Candidate Replay、Gate、Memory 更新、完整进化及最终 Test 调用均为 0。
