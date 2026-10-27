# 新版明显事实错误筛查：R01–R03 单次实测

三轮各请求一次，全部正常返回并通过严格输出校验，共覆盖 18/18 条 Knowledge。未自动重试。原先反复截断的 R01 本次正常完成，但本次同时改变了核验目标、Prompt 和输入结构，不能据此确定改善来自哪一个因素，也没有做去重前后的模型对照。

使用已冻结的 `v23_5_obvious_fact_screen_v1` Prompt 和 v2 去重输入。基准答案、判定边界示例和旧输出未发给模型。模型及预算沿用原配置：deepseek-v4.1-flash、medium reasoning、thinking enabled、32768 输出 Token、300 秒超时。

## 实际输出

| 轮次 | 请求次数 | 有效目标 | SUPPORTED | CONFLICT | 请求耗时 |
|---|---:|---:|---:|---:|---:|
| R01 | 1 | 5 | 4 | 1 | 128.042 秒 |
| R02 | 1 | 6 | 5 | 1 | 40.431 秒 |
| R03 | 1 | 7 | 6 | 1 | 163.038 秒 |

三轮并发墙钟时间 163.827 秒。每份响应均 finish_reason=stop，JSON、目标覆盖、原文片段和引用权限校验通过；结构通过不等同语义全部正确。

## 按运行前基准对照

主评价集共 16 条：4 条要求拦截中检出 3 条、漏检 1 条；12 条允许通过项全部通过。TP=3、FN=1、FP=0、TN=12；标签召回率 75%，标签一致率 15/16（93.75%），误拦截为 0/12。3 个 CONFLICT 均命中相应具体问题，并非只返回了正确标签。

| 预先要求检出的问题 | 实际结果 |
|---|---|
| R01 `[0,4]`：Q5:49 被写成 drawer1 | 检出：明确实际动作为 go to shelf 1，并保留其他正确 drawer1 返回例子 |
| R02 `[0,2]`：P6:1/Q6:9 水壶可见性 | 检出：对应观察列出的物品没有 kettle，指出虚构了可见目标的机会 |
| R03 `[0,1]`：Parent 变换模式过度推广 | 检出：用输入内 P3 冷却片段指出 P10 并非唯一例外 |
| R03 `[0,3]`：未找到目标就无法判断搜索规则适用性 | 漏检：返回 SUPPORTED，没有指出其与 Diff 明确触发条件的冲突 |

预先单列的两条 review_only（R01 `[0,3]`、R03 `[0,4]`）均返回 SUPPORTED，仍单列，不进入上述 16 条指标。没有按模型结果改变分组或重写标签。

这里的“允许通过”包含当前证据不足但按新目标不应拦截的条目，不代表全部事实已证实。基准由 Codex 审阅、尚未经人类确认，且建立前已见旧输出，因此是开发集参考。样本很小，不能把 3/3 的拒绝标签正确解释为稳定的 100% precision，也不与旧充分性审计的不同标签口径直接比较。

## 逐条结果

| 轮次 | 位置（零基） | 分组 | 预期 | 模型 |
|---|---|---|---|---|
| R01 | [0,0] | primary | SUPPORTED | SUPPORTED |
| R01 | [0,1] | primary | SUPPORTED | SUPPORTED |
| R01 | [0,2] | primary | SUPPORTED | SUPPORTED |
| R01 | [0,3] | review_only | SUPPORTED | SUPPORTED |
| R01 | [0,4] | primary | CONFLICT | CONFLICT |
| R02 | [0,0] | primary | SUPPORTED | SUPPORTED |
| R02 | [0,1] | primary | SUPPORTED | SUPPORTED |
| R02 | [0,2] | primary | CONFLICT | CONFLICT |
| R02 | [0,3] | primary | SUPPORTED | SUPPORTED |
| R02 | [0,4] | primary | SUPPORTED | SUPPORTED |
| R02 | [0,5] | primary | SUPPORTED | SUPPORTED |
| R03 | [0,0] | primary | SUPPORTED | SUPPORTED |
| R03 | [0,1] | primary | CONFLICT | CONFLICT |
| R03 | [0,2] | primary | SUPPORTED | SUPPORTED |
| R03 | [0,3] | primary | CONFLICT | SUPPORTED |
| R03 | [0,4] | review_only | SUPPORTED | SUPPORTED |
| R03 | [0,5] | primary | SUPPORTED | SUPPORTED |
| R03 | [0,6] | primary | SUPPORTED | SUPPORTED |

## 反馈复核

三条具体反馈均引用真实输入内记录。R01 准确纠正一个事件而没有否定整个长循环经验；R02 限定于对应观察的可见性，没有推断房间内不存在水壶；R03 使用已有冷却片段反驳跨案例概括。

R03 反馈末尾的 neither deposited / nor cycled 仍带有整段运行口吻，而引用展示的是局部连续片段。按本版宽松筛查目标，这记为非阻断性的表述边界备注，不撤销已检出的重要问题，也不新增误判计数。后续若 Repair，应避免把反馈扩展成已经检查全部更早动作。

剩余漏检属于明确规则触发条件的解释问题，而非本次重点的动作或对象抄写错误。该项依然按冻结基准记为漏检，没有因本次模型放行而降低要求。

## 实际成本

| 轮次 | 输入 Token | 输出 Token（含推理） | 其中推理 Token | 合计 |
|---|---:|---:|---:|---:|
| R01 | 20,863 | 17,454 | 17,119 | 38,317 |
| R02 | 48,369 | 9,079 | 8,733 | 57,448 |
| R03 | 54,431 | 20,416 | 20,033 | 74,847 |
| 合计 | 123,663 | 46,949 | 45,885 | 170,612 |

全部数值来自实际 API usage。推理 Token 已包含在输出 Token 内，不重复相加。R02/R03 报告缓存命中为 0，R01 未提供缓存字段，全量缓存命中数未知。内部服务单价未提供，货币成本为 null。此处只统计本次新增的三次 Verifier 请求，不包括历史 Replay 或尚未运行的 Repair。

## 产物与复现

- [三轮状态](../../../../artifacts/methods/v23_5/verifier_fact_screen_run_001/run_summary.json)
- [R01 原始判定](../../../../artifacts/methods/v23_5/verifier_fact_screen_run_001/runs/R01/attempts/001/verifier_output.json)
- [R02 原始判定](../../../../artifacts/methods/v23_5/verifier_fact_screen_run_001/runs/R02/attempts/001/verifier_output.json)
- [R03 原始判定](../../../../artifacts/methods/v23_5/verifier_fact_screen_run_001/runs/R03/attempts/001/verifier_output.json)
- [标签对照与 usage](results/live_comparison.json)；[具体问题审阅](results/live_adjudication.json)
- [运行前协议](LIVE_PROTOCOL.md)；[冻结基准](reference_review.json)

实际 request、原始 HTTP、模型响应、完成状态、usage、输出及校验结果分别归档。原始输入、Prompt、基准和旧实验保持不变。本次没有 Replay、Repair、Actor 调用或 Memory 提交。

新增运行器 3 项和统计器 1 项离线测试通过。以下命令只做复核和重新统计，不请求模型：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v23_5/verifier_fact_screen_001/run_verifier.py verify
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v23_5/verifier_fact_screen_001/compare.py
```
