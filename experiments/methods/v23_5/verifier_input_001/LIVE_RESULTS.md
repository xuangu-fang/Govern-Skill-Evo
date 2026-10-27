# R01–R03：独立审阅基准与 Verifier 实测

已完成 18 条运行前审阅及 5 次真实请求（含用户授权的两次 R01 补充重试）。R02、R03 的 13 条获得有效输出；R01 三次均耗尽输出预算且正文为空，5 条没有有效核验结果。该执行失败仍未解决，不能将本次描述为全部 18 条核验完成。

18 条 Knowledge 已逐条审阅并在首次模型调用前冻结。审阅者是 Codex，`human_reviewed=false`；这是供人类复核的参考基准，不是已经取得人类确认的金标准。原标签没有根据模型结果修改。见 [逐条审阅表](REFERENCE_REVIEW.md)和 [JSON 基准](results/reference_review.json)。

## 运行边界

只运行独立 Verifier。使用第二阶段冻结的 Prompt 和 messages，模型为原 Replay 使用的 deepseek-v4.1-flash，thinking enabled、reasoning_effort medium、max_tokens 32768。模型看不到参考标签。没有新 Replay、Repair、Actor 调用，没有提交 Memory 或发布 Skill。

首次 R01 因 `finish_reason=length` 失败，最终 content 为空；原协议没有自动重采样。用户明确允许后，单独保存补充重试，不覆盖首次失败。请求的原始 HTTP、usage、输出、完成状态和严格校验结果均保留。

## 评价口径

运行前基准分两层：完整档案下 11 条 SUPPORTED、6 条 CONFLICT、1 条 UNCERTAIN；仅凭实际提取给模型的证据，预期 5 条 SUPPORTED、13 条 CONFLICT。UNCERTAIN 仅是参考审阅的保留项，不改变 Verifier 二分类协议。

CONFLICT 同时包含事实矛盾和证据不足。因此“被拒绝”不自动等于“具体事实错误被抓住”，完整档案正确但缺少相应输入的条目也应单列。无法取得有效模型输出的条目不计算为漏检或正确，单独报告覆盖率。

## 结果摘要

| 轮次 | 目标数 | 请求次数 | 输出有效 | SUPPORTED | CONFLICT |
|---|---:|---:|---|---:|---:|
| R01 | 5 | 3 | 否，三次 length 且 content 为空 | — | — |
| R02 | 6 | 1 | 是 | 5 | 1 |
| R03 | 7 | 1 | 是 | 6 | 1 |

首次调用的轮次有效率为 2/3，补充重试后仍为 2/3；最终目标覆盖为 13/18。全部尝试中有效响应为 2/5。两份有效输出均通过完整覆盖、JSON、枚举、原文摘录及引用权限校验。

| 预先关注的问题 | 本次结果 |
|---|---|
| R01 Q5:49 实际 shelf1，被写成 drawer1 | 无有效响应，未能评价 |
| R02 水壶可见性错误 | 反馈明确命中 |
| R03 Parent 变换模式过度推广 | 反馈明确命中；反馈自身边界另有保留 |

仅对有效输出的 13 条，与冻结的“输入内预期”对照：TP=2、FN=6、FP=0、TN=5。即 8 条参考问题中拒绝了 2 条（25%），5 条证据充分的参考正例全部通过（0/5 误拒），标签一致为 7/13（53.8%）。2/2 拒绝标签符合基准，但样本极小，不能解释成已建立稳定的 100% precision。标签一致也不证明 issue 列举完整或理由全部正确。

按完整档案标签另看：有输出的 4 条参考错误中拒绝 2 条、放行 2 条；8 条档案正确项均通过，1 条档案歧义项通过。档案正确却输入证据不足的 6 条中，3 条没有输出，另外 3 条均被放行。后三条不是事实错误，但不符合当前 Prompt 对证据充分性的要求。完整档案与输入内指标不能混用。

## 已返回的逐条对照

位置为 `[entry_index, knowledge_index]`，从零开始。完整说明见逐条审阅表；UNAVAILABLE 表示没有有效判定。

| 轮次 | 位置 | 完整档案参考 | 输入内预期 | Verifier | 对照 |
|---|---|---|---|---|---|
| R01 | [0,0] | SUPPORTED | CONFLICT | UNAVAILABLE | 未计分 |
| R01 | [0,1] | SUPPORTED | CONFLICT | UNAVAILABLE | 未计分 |
| R01 | [0,2] | SUPPORTED | CONFLICT | UNAVAILABLE | 未计分 |
| R01 | [0,3] | CONFLICT | CONFLICT | UNAVAILABLE | 未计分 |
| R01 | [0,4] | CONFLICT | CONFLICT | UNAVAILABLE | 未计分 |
| R02 | [0,0] | SUPPORTED | CONFLICT | SUPPORTED | FN |
| R02 | [0,1] | CONFLICT | CONFLICT | SUPPORTED | FN |
| R02 | [0,2] | CONFLICT | CONFLICT | CONFLICT | TP |
| R02 | [0,3] | SUPPORTED | SUPPORTED | SUPPORTED | TN |
| R02 | [0,4] | SUPPORTED | SUPPORTED | SUPPORTED | TN |
| R02 | [0,5] | SUPPORTED | SUPPORTED | SUPPORTED | TN |
| R03 | [0,0] | SUPPORTED | CONFLICT | SUPPORTED | FN |
| R03 | [0,1] | CONFLICT | CONFLICT | CONFLICT | TP |
| R03 | [0,2] | SUPPORTED | CONFLICT | SUPPORTED | FN |
| R03 | [0,3] | CONFLICT | CONFLICT | SUPPORTED | FN |
| R03 | [0,4] | UNCERTAIN | CONFLICT | SUPPORTED | FN |
| R03 | [0,5] | SUPPORTED | SUPPORTED | SUPPORTED | TN |
| R03 | [0,6] | SUPPORTED | SUPPORTED | SUPPORTED | TN |

## 已确认发现与漏检

- R02 `[0,2]` 明确指出 P6:1/Q6:9 的观察未显示 kettle，候选动作也无 take kettle；命中水壶可见性问题。还指出 Q8 与 Parent 的覆盖范围比较缺少足够的 Parent 过程。
- R03 `[0,1]` 使用 P3:4–6 冷却实例指出“除 train:0029 外所有 Parent 都先放入设备并开关门”的概括不成立。
- R02 `[0,1]` 放行了 Parent first went to countertop1；完整档案的 P9:1 实际为 fridge1。但首步未提供给 Verifier，因此其可期待的发现是“first 缺少支持”，不能要求它猜出隐藏动作。
- R03 `[0,3]` 放行了“未找到对象，所以无法判断搜索规则适用性”；实际 Diff 将未找到目标列为搜索规则的适用条件。
- 全程一致、从未访问、从未放入设备、全部动作合法等陈述，常被凭部分步骤放行。R02 `[0,0]`、R03 `[0,0]`、`[0,2]`、`[0,4]` 均涉及这类问题。

R03 `[0,1]` 的拒绝方向正确，但反馈自己的 “only once / never performed” 也有超出片段的风险：最终任务失败不能单独证明此前没有成功变换对象。完整档案吻合某个事实，不等于 Verifier 已获得足够证据。此项作为反馈质量问题单独保留，不能把整条 CONFLICT 标签正确等同于 reason 全部可靠。

## 实际消耗

| 请求 | 输入 Token | 输出 Token（含推理） | 其中推理 Token | 总 Token | 单次耗时（秒） |
|---|---:|---:|---:|---:|---:|
| R01 第 1 次 | 23,925 | 32,768 | 32,768 | 56,693 | 214.192 |
| R02 | 64,808 | 20,177 | 19,528 | 84,985 | 154.956 |
| R03 | 82,125 | 32,485 | 32,093 | 114,610 | 199.214 |
| R01 第 2 次 | 23,925 | 32,768 | 32,768 | 56,693 | 225.491 |
| R01 第 3 次 | 23,925 | 32,768 | 32,768 | 56,693 | 218.738 |
| 合计 | 218,708 | 150,966 | 149,925 | 369,674 | — |

全部数字来自 API usage，包含三次失败请求。149,925 个 reasoning Token 已包含在输出 Token 中，不能再次相加。已知缓存输入合计 51,200 Token，R03 未报告该字段，因此全量缓存命中数未知；缺失不能当零。内部服务单价未提供，货币费用为 null。首次三轮并发约 214.9 秒，两次单轮重试各约 226.2 / 219.5 秒；逐次请求耗时不能作为并发墙钟时间相加。

本阶段只新增 Verifier 请求，未新增 Replay/Repair；这里是本次离线实验的全部新增 API 消耗，不能据此宣称完整 Replay→Verifier→Repair 流程的总成本或节省比例。

## 判断与下一步

该机制已经在有效返回的两轮中抓住两个具体已知问题，也暴露出两类独立缺陷：R01 无法在现有推理/输出预算内交付，以及对“证据不充分”的放行偏多。现阶段不能据此批准自动进入正式 Memory，也没有检验 Repair 的修正成功率。

后续最小改进应分别实验：调整 R01 推理/输出预算以解决交付，再针对全程一致、never/only/all 和规则适用性制作小型 Prompt 回归对照。对真实但证据不足的条目，可要求 Replay 引用相应终态或必要连续片段；不必扩展为全任务反例搜索。本次没有更改 Prompt、证据提取规则或模型配置来追求好看的结果。

## 产物与验证

- [原始三轮运行](../../../../artifacts/methods/v23_5/verifier_run_001/run_summary.json)
- [R01 第一次补充重试](../../../../artifacts/methods/v23_5/verifier_run_001_retry_R01_001/run_summary.json)
- [R01 第二次补充重试](../../../../artifacts/methods/v23_5/verifier_run_001_retry_R01_002/run_summary.json)
- [累计对照 JSON](../../../../artifacts/methods/v23_5/verifier_run_001_evaluation/comparison.json)
- [反馈与分歧审阅](../../../../artifacts/methods/v23_5/verifier_run_001_evaluation/adjudication.json)
- [执行协议及授权补充](LIVE_PROTOCOL.md)
- [运行器](run_verifier.py)与[指标统计](compare_verifier.py)

新增 11 项离线测试通过：覆盖截断不误算成功、断点不重复请求、传输重试边界、失败费用计入、补充重试合并、重复有效结果拒绝、缺失 usage 不当零。测试没有调用模型；输入、Prompt、候选、基准和原始来源另行检查哈希。

## 只读复核和重新统计

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v23_5/verifier_input_001/run_verifier.py verify
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python experiments/methods/v23_5/verifier_input_001/compare_verifier.py --supplemental artifacts/methods/v23_5/verifier_run_001_retry_R01_001 --supplemental artifacts/methods/v23_5/verifier_run_001_retry_R01_002 --report-dir artifacts/methods/v23_5/verifier_run_001_evaluation
```

以上命令不请求模型。首次比较保留在原始运行目录，累计比较单独保存，不覆盖首次失败。任何后续 Prompt 或配置变更都应建新版本，保留这次基准和失败成本。
