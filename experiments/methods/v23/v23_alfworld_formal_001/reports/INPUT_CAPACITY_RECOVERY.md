# 正式 S1：R02 输入容量恢复

本次为原 `v23_alfworld_formal_001/S1` 的明确授权恢复，不创建新 Campaign。原 R02 Preconditioner 的 `attempts/001/error.json` 保留，`request_invoked=false`；没有把该次本地拒绝记为 API 请求。

## 配置与边界

所有调度模型阶段共用 `max_input_chars=1000000`、`max_message_utf8_bytes=1500000`。旧内部字段 `max_input_bytes` 仍兼容；两个名称同时存在但数值不同则拒绝。

初始 `config.json`、`initial_config.json` 与轮次冻结输入保持原样。实际容量通过 `S1/recoveries/001.json` 中的显式覆盖生效。提案保存在 `config/input_capacity_recovery.json`，记录本次调度适配源码的准确修改前后内容；仅允许该适配，其他模块／Actor 源码和 Prompt 仍要求与冻结内容完全一致。容量恢复不能夹带模型参数修改；其他冻结配置修改仍会报错。

模型 `deepseek-flash`、输出 `max_tokens=16384`、timeout=300、temperature=1、Thinking enabled、reasoning_effort=medium、stream=false 均未改变。Actor 并行度 8、每任务 50 步、六轮官方顺序、Gate、完整 Memory 证据均未改变。容量覆盖也应用于后续轮次的 Replay 等阶段；不自动扩大预算或截断输入。

## 上下文核查

[DeepSeek 官方模型说明](https://api-docs.deepseek.com/quick_start/pricing/) 本次读取标明 `deepseek-flash` 对应 DeepSeek-V4.1-Flash-1017，context length 为 1M tokens。模型别名与请求参数保持原值，并未自行改为其他模型。

通过现有 `read_upstream()`、冻结轮首 Memory 和 `messages_for()` 重建 R02 请求：**337927 字符，337945 UTF-8 字节**。新请求 messages 与重建完整原输入逐项相等，没有筛选或压缩。

字符数不是 token 数。R01 Preconditioner 实际为 69241 字符／19443 输入 tokens，Replay 为 155901 字符／44999 输入 tokens；按这两份实际材料估算 R02 约 94891–97539 输入 tokens，仅为经验估计。最终以服务端 usage 为准，不将估计视为 tokenizer 精确结果。本地 100 万字符／150 万字节上限也不保证所有未来请求必然满足服务端上下文；服务端上下文错误将保留并按既有规则停止。

## 代码与离线验证

- `src/skill_evolution/v23/evolution.py`：容量字段兼容、统一消息字节检查、显式容量恢复记录与覆盖。
- `tests/skill_evolution/v23/test_capacity_recovery.py`：13 项新增测试，覆盖恢复复用、真实完整 R02 输入、非法容量、字段冲突、拒绝夹带 Prompt／Actor／模型参数／冻结配置修改，以及准确源码授权。
- `prepare.py`：历史开发接触统计排除本正式实验自身；否则启动后的轨迹会污染启动前统计。冻结数据与统计文件未改写。

命令：`/tmp/gse-v23-py313/bin/python experiments/methods/v23/v23_alfworld_formal_001/run_offline_tests.py`。

最终 **555 passed，19 subtests passed**，网络连接和环境子进程被离线测试入口禁止。范围覆盖全部 V23、ALFWorld Adapter、V22 grouped representation 回归。首次检查的两个准备脚本失败及修复后的通过日志分别保存在 `input_capacity_tests.txt` 和 `input_capacity_tests_final.txt`，没有删除失败记录。

## 实际恢复

使用原目录执行 `resume --recovery .../config/input_capacity_recovery.json`，新进程 PID 35884，启动于 2026-10-19 01:57:02 左右（北京时间）。实际命令、UTC 时间与进程信息保存在原运行目录旁的 `resume_001_launch.json`；日志为 `resume_001.log`，退出后写 `resume_001_exit_code.txt`。原 launch、campaign log 与原 exit code 均保留。

启动后直接内容核对 **706 个原档案文件全部不变**，包括 R01、R02 已完成 Parent/Grouping/Diagnosis、原容量错误、原配置和轮次输入。没有重复成功阶段的模型／Actor 请求。R02 Preconditioner 新请求保存在 `attempts/002`，继续沿用历史 attempt 编号。

R01 已完成：Parent 9/10，Candidate 10/10，Gate ACCEPT；正式 Parent 为 R01 Candidate，Active Memory 为 M1、M2。恢复开始时正式状态仍为 `next_round=2`，Parent 与 Memory 都指向 R01 已发布产物。后续仅按正常原子轮次提交推进。

实时状态及后续恢复结果见本报告末尾更新与原 Campaign 档案。本任务不运行最终 Test，不承诺六轮一定完成；合法语义停点或技术重试耗尽时按原规则停止。

## 恢复后服务端验证（2026-10-19 01:59 北京时间）

R02 Preconditioner 已成功通过，进入 Editor。服务端实际记录输入 **99056 tokens**，加输出预算 16384 共 115440，低于官方标明的 1M 上下文。本地新容量与服务端实际接收均已验证。

恢复后的 attempt 002 返回了不可用的历史引用，契约校验失败，原始响应和 usage 已保存；它实际消耗 113452 tokens（其中输入 99056、输出 14396、推理 13900）。按既有规则、不改变消息或参数自动重试后，attempt 003 成功，结果 ready，0 项 Adjustment。成功请求 usage：`{'prompt_tokens': 99056, 'completion_tokens': 8623, 'total_tokens': 107679, 'prompt_tokens_details': {'cached_tokens': 98816}, 'completion_tokens_details': {'reasoning_tokens': 8352}, 'prompt_cache_hit_tokens': 98816, 'prompt_cache_miss_tokens': 240}`。没有追加纠错反馈或修补模型输出。旧 attempt 001 的容量错误仍保留。

## 交付时实际进度（2026-10-19 02:00 北京时间）

R02 Editor 首次因 `Truncated hunk` 契约失败，按既有规则原请求重试一次；attempt 002 补丁严格应用成功。错误与响应均保留。随后进入 Candidate Execution，实际观察到 4 个独立 Actor 子进程同时执行。

六轮进度：R01 已完成并 ACCEPT；R02 Preconditioner、Editor 已完成，Candidate 执行中；R03–R06 尚未开始。Campaign 在原目录后台继续运行，未宣称六轮已完成。正式 Parent/Memory 仍为 R01 状态，等待本轮 Gate、Replay/Memory 完成后统一发布。若后续达到合法停点或技术重试耗尽，原程序停止，不额外增加容量或重试。
