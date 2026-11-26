# V25 官方 DeepSeek 连续训练

2026-10-28 20:38（Asia/Shanghai）启动。用户授权新建连续训练；旧内网两轮探索实验及其第二轮中断现场保留，不续接旧 Skill、Memory 或执行结果。当前状态以 `process.json`、`campaign/state.json` 和各轮 `progress.json` 为准；本说明记录启动配置，不代表训练已经完成。

## 冻结方案

- 官方接口 `https://api.deepseek.com`，Actor 和全部方法模块统一使用 `deepseek-flash`。
- Diagnosis v5；Preconditioner v7；Replay Prompt v4；Replay 输入视图 v4。Editor、Verifier/Repair、Gate 及其余方法源码与旧探索实验完全一致。
- 原始 initial Skill（224 个空白分词），空 Memory。
- 120 个优化任务：原顺序 80 Train + 40 Val，1 epoch，8 轮 × 15 题。Val 已参与优化，不能当作独立验证集。
- 最终 280 Test 不执行、不用于训练决策；完整配置保留其元数据以符合原数据清单格式。
- temperature=1.0、reasoning_effort=medium、thinking enabled、stream=false、请求超时 300 秒。
- Actor max_tokens=49152，30 次程序执行预算，每个程序槽至多 6 次 API 请求；4 workers；程序超时 600 秒；无累计任务超时。
- 方法输出预算：Grouping/Editor 16384，Diagnosis/Repair 32768，Preconditioner/Replay/Verifier 49152。
- 原生格式反馈、重试预算和 ACCEPT/RETAIN/no_change 规则不变；不因发现普通经验表述错误另加停止门槛，不进行语义重采样。原生接口、合同或语义阻断会保存并停止。

## 路由适配与可比性

新配置从 `experiments/methods/v25/v25_two_round_exploration_20261028_001/config/config.json` 复制，仅更换 Actor/模块的 endpoint 和 model，并移除硬编码内网端点的可选 `comparison_profile` 标签。该标签的非路由约束没有放弃：`run.py:check_config` 将路由显式规范回原值后调用原 `validate_latest_configuration`，并断言除上述记录的路由及标签适配外，整个配置与原配置完全相同。

未修改生产方法源码、Prompt 或验证器。`contract.json` 保存完整源码合同，`manifest.json` 冻结配置、运行脚本和运行环境；正式运行沿用原生 `evolution.run_campaign`。`route_change.json` 记录适配及原配置 SHA。凭据只在被 Git 忽略的本地 `.env` 中，实验产物不保存密钥。

这是一项新的官方接口实验，不能将与旧内网结果的差异全部归因于方法改进。后续性能比较应以相同官方接口下的 initial Skill 为基准。本启动不额外调度独立 baseline 或最终 Test。

## 启动前检查

- 方法源码/Prompt 与旧探索实验合同一致；Docker 镜像及 runtime 快照一致。
- 配置与任务批次离线校验通过，8 × 15 个优化任务不含 Test。
- 一次独立兼容性请求通过：HTTP 200，response model `deepseek-flash`，finish_reason `stop`；49,152 输出上限及原有调用参数被接受。
- 预检使用 41 prompt + 35 completion = 76 tokens（其中 reasoning 32，已包含在 completion 中）。只发送固定 READY 请求，未发送任务数据，不进入任何训练证据或 Memory；费用与训练分开记录。
- 后台进程使用 `caffeinate -i` 避免运行期间因空闲休眠中断。启动信息见 `launch.json`，日志见 `run.log`。

## 归档与观察项

每轮原生保存 Original Plan、D/S/C 及编译后计划、Candidate Skill、Parent/Candidate 任务轨迹与成绩、Gate、原始 Replay、Verifier/Repair、最终 Memory 及下一轮实际输入；全部请求及 usage 保留。

继续观察：

1. 历史经验是否实际改变下一轮 Preconditioner 的更新，而不只是出现在输入里。
2. 评分收益是否伴随公式要求或其他任务要求被弱化。
3. workflow 更新是否减少不保存工作簿的探查和调用消耗。
4. 事实错误或限定遗漏如何经过审查、发布，并影响后续行为；区分可见、引用、决策影响与因果验证。
5. Skill 长度、任务退步和成本如何随轮次变化。

这些观察项不会被人工注入模型或用于途中调 Prompt。有无历史预条件化消融及最终 Test 评估未在本次运行器中调度。

## 状态与后续复核

只读状态命令（不调用模型）：

```sh
cd /Users/didi/Desktop/Govern-Skill-Evo
/tmp/govern-skill-v25-venv/bin/python scripts/runs/v25/v25_full120_official_d5_p7_r4_view4_actor48k_w4_20261028_001/run.py status
```

`campaign/rounds/Rxx/progress.json` 显示当前阶段；`campaign/state.json` 只在完整发布后推进。`process.json` 表示进程的运行/停止/完成状态；退出时 `result.json` 保存结果或错误及训练成本，成功完成八轮后导出 `retained_skill.md`。进程异常被系统强制终止时还需结合 PID 是否存活检查，不能仅相信旧的 running 标记。

遇到阻断保留现场，不删除失败请求、重置预算或换 Prompt。`run.py resume` 仅用于已明确解决阻断后的原生恢复，不能绕过不可重试或语义失败。模型温度为 1.0，重新采样不保证结果逐字复现。

## 追加重试授权：R04 Grouping

用户在获知原 6 次预算耗尽后明确要求“继续重试”。本次仅将 R04 Grouping 总预算从 6 次扩展为 12 次，保留 attempts/001–006，从 007 继续。其余阶段预算、源码、Prompt、输入、验证器、错误反馈和最终 Test 禁用保持不变。这是原冻结重试预算的显式例外，不能视为完全未变的原始协议运行。授权和恢复前快照见 `recovery_r04_grouping_extra6_001/`，机器可读声明见 `campaign/amendments/r04_grouping_extra6_001.json`。使用该目录的 `run.py resume` 恢复；原始入口不支持该例外。

## R04 校验器误报修复与首次输出重新验收

用户确认采用第 1 次原始输出。恢复入口 `recovery_r04_cell_range_001/run.py` 在本次训练进程中加载 A1 单元格区域引用解析修复；例如 `G2:P18` 不再产生执行引用 P18，裸 P18 和未知步骤仍按原规则拒绝。原生产源码和 Prompt 快照未改动，修复是明确归档的运行期校验例外。

第 1 次原始输出和全部原始文件保持不变，原错误记录作为历史保留。其原始响应经完整原生流程重新校验，验收文件保存在 `campaign/rounds/R04/grouping/attempts/001/recovered/`，本轮 `grouping/result.json` 仅选择该结果；未增加 Grouping API 调用。第 2–12 次文件完整移至 `campaign/audit/r04_grouping_not_selected_002_012/`，标为不采用，仍计入累计 API 用量。旧停止记录归档到恢复目录，原追加预算声明仅作历史记录；本入口使用原始每阶段 6 次预算。

22 项针对性测试、38 项现有流程测试通过，归档前后 cost_summary 完全一致。授权、文件 SHA、完整复验报告和恢复日志均在 `recovery_r04_cell_range_001/`。后续恢复请使用该目录的 `run.py resume`，原入口和此前追加预算入口不再适用。最终 Test 仍不执行。
