# P3-B 执行报告

**两次授权请求均已发出，零自动重试。A读取超时，B合法完成，因此没有形成有效的A/B输出对照。不能把A缺失结果当作Keep、no_change或无Memory语义失败。**

## 冻结及授权

使用P3-A请求原件；Original是 `v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001/diagnosis.json`。未修改Goal、Updates、basis、Checks或重新运行Diagnosis。

发送前核验P3-A freeze、input_manifest、全部source哈希、当轮Active、唯一Memory变量；实际HTTP发送前再次核验正文与完整request文件SHA256。A空Memory，B为M1/M2/M3/M6/M7/M8/M9及sources；两组仍只有P1/P3/P6/P7/P8/P10、G1–G4与原103候选表。未加入M10或P2/P4完整当前轨迹。

用户本次明确授权直接执行，确认内网别名与此前模型对应，不需再查上下文容量。该授权单独记录于 [authorization.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/config/authorization.json)；未覆盖P3-A原先的待确认状态。本次没有额外容量探测或路由探测调用。

| 项目 | A | B |
|---|---|---|
| 请求模型 | deepseek-v4.1-flash | deepseek-v4.1-flash |
| response_model | 未收到 | deepseek-v4.1-flash |
| 开始UTC | 2026-10-20T07:50:26.994618+00:00 | 2026-10-20T07:55:27.389901+00:00 |
| 结束UTC | 2026-10-20T07:55:27.339458+00:00 | 2026-10-20T07:56:24.888716+00:00 |
| 耗时 | 300.341秒 | 57.498秒 |
| HTTP请求尝试 | 1 | 1 |
| 自动重试 | 0 | 0 |
| 状态 | transport ReadTimeout | HTTP 200 / ready / stop |
| parsed / Effective | 不可得，没有生成 | 原解析、Schema、编译通过 |

Endpoint为冻结的 `http://llm-proxy.intra.xiaojukeji.com/chat/completions`；temperature=1、thinking=enabled、reasoning_effort=medium、stream=false、max_tokens=16384、read timeout=300秒、connect timeout=10秒。两组均未更改参数。

## 发送与失败处理

仅在新的P3-B目录增加最小包装器 [run_once.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/run_once.py)，复用 `grouping.live_generator`、原JSON解析器和 `compile_effective_plan`。没有运行 `local.run_stage` 的自动三次重试循环。包装器持久化一次性execution_claim；重复运行会拒绝，不能通过重启偷偷重采样。

HTTP Session的adapter重试总数为0，禁止redirect，内网Session不继承外部代理；每次post前核对完整请求、timeout、body及调用计数。实际请求文件与P3-A原件字节哈希一致，见 [preflight](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/config/preflight.json)、[A发送记录](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/runs/A/dispatch.json)、[B发送记录](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/runs/B/dispatch.json)。

A的错误原文：`Read timed out. (read timeout=300)`。它没有返回HTTP状态、响应正文、finish_reason或usage，不能伪造这些文件。客户端超时不说明服务端未计算或未计费，亦不证明容量超限、模型拒绝或共同配置错误。按预注册的单组独立失败规则继续B；B在57.5秒合法返回。不据此解释A超时的根因。

B完整原始HTTP正文保存于 [http_response.txt](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/runs/B/http_response.txt)，包含服务返回内容；[response.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/runs/B/response.json)、[raw_output.txt](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/runs/B/raw_output.txt)、[parsed.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/runs/B/parsed.json) 与 [effective_plan.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/runs/B/effective_plan.json) 可追溯。A仅保存已发送请求、dispatch、时间、错误及“响应/usage不可得”记录，没有伪造响应或Effective。

## 实测用量

| 用量 | A | B |
|---|---|---:|
| input tokens | 未返回，未知 | 474,757 |
| output tokens | 未返回，未知 | 5,270 |
| 其中reasoning tokens | 未返回，未知 | 4,751 |
| total tokens | 未返回，未知 | 480,027 |
| cached input tokens | 未返回 | API未提供，不按0处理 |

B的4,751 reasoning tokens已包含于5,270 output，不重复加总。已知用量小计480,027；**两组实验总Token未知**，不能把A按0加总。没有可靠货币账单，未估算费用。两请求耗时合计357.839秒；这不是服务端总计算时长。

## 编译核验与保护

B同时调整一次u1，u2原样Keep；无拆分、合并或撤回。Goal原样，checks=null使c1–c3原样保留。所有替代text逐字进入Effective，u2逐字不变；重编译与保存结果相同。Effective u1的basis按原程序保留Original来源，M6/M3/M8引用位于Adjustment.basis而非Effective.basis；这是原编译契约，不是证据被漏传。

Preconditioner reason不自动成为Actor指令；本次不调用Editor。结构合法不能证明新的策略合理。

保护结果见 [protection.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/results/protection.json)；仅新增本p3b_results目录，正式V23、旧V23.2、P0–P3-A、Memory、Parent、Campaign和Test保持原样。Test仅哈希保护，没有用于分析。新增逻辑调用2、HTTP尝试2、自动重试0；Editor/Actor/Replay/Gate/Memory/Diagnosis/环境调用均0。
