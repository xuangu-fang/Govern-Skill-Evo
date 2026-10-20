# R04 本地输入容量恢复

本次继续原 `artifacts/methods/v23/v23_alfworld_formal_001/S1`，仅修改本地容量阈值，不创建新 Campaign。

- `max_input_chars`: 1000000 → **4000000**。
- `max_message_utf8_bytes`: 1500000 → **6000000**。
- `max_tokens=16384`、timeout=300、模型与生成参数、Actor 并行度 8、任务顺序、Prompt、Memory 与证据装配全部不变。

## 配置如何生效

通过现有 `resume --recovery config/input_capacity_recovery_r04.json` 入口，新增 `S1/recoveries/002.json`。`contract_changes` 为空：本次没有修改任何生产源码或 Prompt。初始 config、initial_config 和旧恢复记录仍保持原样，运行时按顺序应用容量覆盖。只有这两项阈值变化，其他冻结检查仍执行。

逐一核对 Grouping、Diagnosis、Preconditioner、Editor、Replay：五个阶段均由 `evolution.run_round()` 传入统一 `max_input_chars`，均通过 `_model_stage()` 的公共 UTF-8 字节检查。独立模块 CLI 的缺省值不参与本正式 Campaign；没有在正式调用路径遗漏旧限制。

原 R02 和 R04 的 `preconditioner/attempts/001/error.json` 都保留，均为 `request_invoked=false`。R04 的新尝试从 002 开始。

## 离线与上下文核查

完整 R04 Preconditioner 输入：**1217815 字符、1217849 UTF-8 字节**，包含 6 个 Active MemoryEntry、55 个历史来源。Memory 对象紧凑 JSON 为 **917456 字符**。

使用原有 `read_upstream()`、冻结的轮首 Memory 和 `messages_for()` 重建完整消息。实际新请求与重建结果直接内容比较完全相等。未删减、压缩或筛选历史证据。

[DeepSeek 官方模型表](https://api-docs.deepseek.com/quick_start/pricing/) 本次核查显示 `deepseek-flash`（当前别名指向 DeepSeek-V4.1-Flash-1017）的上下文为 **1M tokens**。本地字符上限与模型 token 上限并不等同；依据之前请求的实际 token/字符比例估计 R04 约 35.7 万输入 tokens，另有最多 16384 输出 tokens。这是经验估计，不是精确分词；服务端实际 usage 将独立记录。新 400 万字符上限不保证所有未来请求都能容纳，若服务端返回上下文超限则按现有规则停止，不能自动扩容。

离线命令：

```bash
/tmp/gse-v23-py313/bin/python experiments/methods/v23/v23_alfworld_formal_001/run_offline_tests.py
```

结果：**568 passed，19 subtests passed**。测试入口禁止外部网络和环境执行。新增 13 项测试覆盖：真实 R04 输入在旧限额下拒绝、新限额下以相同消息通过；五个正式模块的统一限额传递；五个阶段的 6000000 字节边界及多 1 字节拒绝；第二次容量覆盖只更改两项阈值。既有 V23、ALFWorld Adapter、V22 grouped representation 回归全部通过。日志为 `r04_input_capacity_tests.txt`。

## 实际恢复与档案保护

2026-10-19 09:29:59（北京时间）在原路径启动 `resume`，包装进程 PID 6653。命令和运行日志保存为原运行目录的 `resume_002_launch.json`、`resume_002.log`；完成或停止后保存 `resume_002_exit_code.txt`。

恢复前正式状态：`next_round=4`，Parent=`rounds/R02/editor/attempts/002/candidate.md`，Active Memory=`rounds/R03/memory`。R04 已完成的 Parent、Grouping、Diagnosis 均直接复用。

包装进程在内存中保存 2169 个受保护文件的原始字节，结束时直接比对 R01–R03、R04 已完成上游、原配置、原错误和旧恢复记录。覆盖 90871421 字节，不创建备份档案、不增加哈希字段；最终核对结果保存为 `r04_preservation_final.json`。

最终进度、所有请求用量与 Memory 增长将在本报告末尾记录。最终 Test 不在本次执行范围。

## R04 已完成的实际验证

- Preconditioner 恢复 attempt 002 首次成功：输入 **356103 tokens**，输出 11048，合计 367151，推理 9551；实际输入加固定输出预算为 372487 tokens，服务端正常接受并完整返回。
- Editor 首次成功：输入 3187、输出 4498、合计 7685 tokens。
- 10 条 Candidate 完整执行：Parent 7/10、Candidate 6/10，Gate RETAIN。
- Replay 首次成功：输入 1373486 字符；输入 **399561 tokens**、输出 8574、合计 408135，推理 6707。
- Replay 修订 M4→M7、M5→M8，新增 M9；Active 为 M1、M2、M3、M6、M7、M8、M9。
- R04 正式提交后：Parent 仍来自 R02，Active Memory 来自 R04，`next_round=5`。没有提前晋级或部分发布状态。

轮首 Memory 增长（字符统计为整个 `entries + sources` 对象的紧凑 JSON，不是 token）：

| 轮次 | Active 条目 | 历史来源 | Memory 字符 |
|---|---:|---:|---:|
| R01 | 0 | 0 | 27 |
| R02 | 2 | 17 | 133682 |
| R03 | 3 | 38 | 469764 |
| R04 | 6 | 55 | 917456 |
| R05 | 7 | 74 | 1294422 |

来源数量包括历史编辑及完整执行来源。增长来自既定完整证据展开；本次没有改变装配方式。更大的本地阈值不会自动增加发送内容，但允许原本已构造的完整内容进入模型调用。

## 最终结果（2026-10-19 09:51:57 北京时间）

六轮全部完成，进程 exit 0；正式状态为 `next_round=7`。`final_parent()` 已验证六轮提交链并返回 R05 的 Candidate：`S1/rounds/R05/editor/attempts/001/candidate.md`。最终 Active Memory 位于 `S1/rounds/R06/memory`。没有执行 S0/S1 最终 Test。

| 轮次 | 配对数 | Parent 成功 | Candidate 成功 | Gate | 全轮实际 tokens（含失败请求） |
|---|---:|---:|---:|---|---:|
| R01 | 10 | 9 | 10 | ACCEPT | 617417 |
| R02 | 10 | 6 | 7 | ACCEPT | 1148813 |
| R03 | 10 | 7 | 6 | RETAIN | 2004769 |
| R04 | 10 | 7 | 6 | RETAIN | 1975636 |
| R05 | 10 | 7 | 9 | ACCEPT | 1903301 |
| R06 | 7 | 6 | 5 | RETAIN | 1722058 |

57 条优化任务、114 条完整 Episode 全部完成。R04 恢复前已完成的 70 条 Episode 不重复执行；本次新增 44 条 Episode。上述逐轮 Train/Selection 结果用于既定 Gate，不代表独立 Test 或泛化收益。

最终受保护文件直接字节比较：**2169 个文件全部未变**。包括 R01–R03、R04 已完成的 Parent/Grouping/Diagnosis、原配置和两次容量错误。运行结束再次核验所有冻结生产源码／Prompt 与模型参数一致。

### 完整 Memory 与输入增长

| 轮次 | 轮首 Active | 来源数 | Memory 字符 | PC 输入字符 | PC 输入 tokens | Replay 输入字符 | Replay 输入 tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| R01 | 0 | 0 | 27 | 69241 | 19443 | 155901 | 44999 |
| R02 | 2 | 17 | 133682 | 337927 | 99056 | 475927 | 139393 |
| R03 | 3 | 38 | 469764 | 784550 | 230336 | 952060 | 278368 |
| R04 | 6 | 55 | 917456 | 1217815 | 356103 | 1373486 | 399561 |
| R05 | 7 | 74 | 1294422 | 1613177 | 470139 | 1753148 | 510958 |
| R06 | 7 | 62 | 1237277 | 1493400 | 432863 | 1647165 | 476979 |

表中模块 token 为每轮最终有效响应的输入用量；失败重试另计入全量成本。来源按 Active 引用的完整执行展开，不沿修订链自动继承全部旧证据。R06 来源减少来自既定 Replay 修订，而非人工删减或容量筛选；旧条目与来源仍在 Archive。

最终 Active：`M1, M2, M6, M9, M11, M12, M13`，67 个来源，Memory 对象 1298416 字符。

峰值实际输入：R05 Replay，1753148 字符、510958 tokens；加固定输出预算 16384 为 527342 tokens。本次恢复后所有大请求均正常通过本地容量与服务端上下文检查。不能据此保证未来任意 400 万字符请求都适合 1M token 上下文。

### 请求和 Token 消耗

| 范围 | Actor 请求 | 模块请求 | 输入 tokens | 输出 tokens | 总 tokens | 推理 tokens（已含于输出） |
|---|---:|---:|---:|---:|---:|---:|
| 整个当前正式 Campaign | 2571 | 37 | 7956853 | 1415141 | 9371994 | 1198186 |
| 本次 R04 resume 新增 | 1056 | 14 | 4494219 | 450034 | 4944253 | 360580 |

全部请求均有 usage，未知用量为 0；Actor 无步骤请求重试。全 Campaign 30 次逻辑模块成功调用、7 次输出契约失败请求，共 37 次模块 API 请求。另有两次本地容量拒绝，均未发送 API 请求，不计为模型用量。

本次恢复期间仅 R05 Grouping 首次缺少 P6 决策步骤引用，按原规则重试一次成功；两次 messages 内容相同，没有反馈纠错。之前的失败和费用均保留。总用量只覆盖当前正式 S1，包含其此前恢复和失败请求，不混入已授权放弃并删除的更早串行运行；更早运行的外部费用并未因此撤销。

本次只增加 `config/input_capacity_recovery_r04.json`、对应测试及日志／报告，未修改生产源码、Prompt、算法、任务、Memory 结构或装配方式。最终结构化结果与全量失败清单见 `r04_capacity_final_results.json`，档案保护结果见 `r04_preservation_final.json`。
