# SkillAdam：对齐 V25.1 Actor 的独立冻结配置

状态：配置与源码已准备，63 项离线检查通过；未启动训练、正式测试、真实模型请求或自动化。旧 SkillAdam、旧 V25 和 V25.1 均未修改。

主要比较：本目录的新 SkillAdam 与 `experiments/comparisons/v25_v25_1_common_actor_no_review_20261030_001/v25_1`。已取消的新 V25 不会重建；旧 V25、旧 SkillAdam 的已完成结果仅作历史参照。

## 配置与改动范围

| 文件/模块 | 处理 |
|---|---|
| `shared_config.json` | 从旧 SkillAdam 复制，仅实验标识改为 `skilladam_v25_1_actor_aligned`；Actor 参数原本已与 V25.1 相同 |
| `skilladam.json` | 与旧 SkillAdam 逐字一致，优化器配置完全保留 |
| `frozen_workspace/` | 从旧 SkillAdam 冻结副本复制，共 357 个源文件；只有下述 3 个文件改变 |
| Actor `prompts/actor_system.md` | 使用 V25.1 已审阅版本，补充基础执行条件、错误反馈和公式缓存事实 |
| Actor `scoring.py` | 与 V25.1 使用相同的区域解析兼容和四位小数输出 |
| Actor `facts.py` | 接受精确比例或四位小数比例；仍拒绝错误的 hard/count/rate。与此前 SkillAdam 测试精度恢复适配及 V25.1 相同 |
| `evaluation/config.json`、`evaluation/scoring.py` | 与 V25.1 相同的完整 280 题 Test 兼容口径 |

完整源码差异见 `source_changes.patch`。Actor 初始任务模板、错误反馈模板、消息历史、请求实现、执行器均与 V25.1 逐字相同。没有复制 V25.1 的预条件器、Diagnosis、Replay、Gate 或 Verify/Repair 设计到 SkillAdam。

所有原生 SkillAdam 优化器源码、Prompt、桥接逻辑、原生 SDK 传输实现逐字保留。Gate、有效 run_config 与 backend_context 经离线检查，与已完成的旧 SkillAdam checkpoint 一致。

## 保持不变的参数

- Actor 与优化器均为官方 `deepseek-flash`，官方 `https://api.deepseek.com`。未来授权启动时使用仓库原官方凭据，密钥不复制到本目录。
- Actor 输出上限 49152；每生成 slot 最多 6 次请求；程序执行上限 30；请求超时 300 秒、程序超时 600 秒，无累计任务超时；并发 4。
- 环境仍为 `govern-skill-v25-python:rc1`，2g、1 CPU、标准库/openpyxl/pandas；execution-only 历史；不向 Actor 返回评分或参考答案。
- 优化器输出上限 16384，temperature=1.0、reasoning_effort=medium、timeout=300、SDK max_retries=2；原生 patch_attempts=3。保留 Momentum、LLM trajectory compression、96000 上下文限制、原生 main-result Gate、编辑预算等所有原参数。
- 原配置中的 max/min_iterations=15 也保持原值；原有 sequential 数据计划实际覆盖 120 个优化任务、8 批、每批 15 题、1 个 epoch。有效调度与旧 checkpoint 的配置一致，不擅自将这两个参数改成 8。
- 初始 Skill、Train 后 Val 的顺序、测试 280 题均与 V25.1 一致。新实验从初始 Skill、空 Momentum/Tracker 开始，不继承旧最终 Skill、检查点、缓存或已耗尽额度。

旧实验第 6 轮单次 Momentum 的 32768 恢复授权不属于优化器全局配置；本次没有复制该单次覆盖或任何补充重试授权。

`shared_config.json` 内保留的 V25 method/module 字段是旧共享配置格式的一部分，不是 SkillAdam 优化器开关；实际 SkillAdam 只通过原生 runner/backend 运行，参数来自 `skilladam.json`。该文件中的旧 `not_before` 和 `reference_preparation` 也仅保留原配置来源，不表示当前启动计划。没有创建定时任务。

## 评分兼容审计

详见 `offline_checks/scoring_compatibility.json`：

- 120 个训练区域在新旧解析器下完全相同。
- 每个训练任务选取一份已保留的旧输出，使用新旧评分器重新计分，共 120 份。hard、正确/总单元格数及其他诊断差异均为 0；19 份 per-cell 比例仅有四位小数舍入差异。这是旧输出复核，不是新实验成绩。
- `test:60-7` 沿用已审计的工作表名修正；`test:283-32` 支持整列区域并覆盖两份工作簿的最大行；`test:73-45` 将 `BD2:308` 正确解释为 `BD2:BD308`，避免空区域假成功。
- 正式 Test 评分器与旧 SkillAdam 已完成 Test 使用的评分器逐字相同，也与 V25.1 相同。没有改变数值等价规则、公式不自动重算或 data_only 读取规则。

舍入统一会改变部分反馈中的数值表示，但不改变上述历史输出的 hard 判定；不能将其描述为所有反馈字节不变。优化器的配置、提示词和更新策略保持不变。

## 离线验证与冻结

`offline_checks/pytest.log` 和 `pytest.xml`：63 项全部通过，覆盖实际 Actor 消息与 V25.1 一致、冻结导入路径、原生配置和 Gate、SDK 重试、3 次 patch 尝试、输入预算、分数兼容、临时格式纠错、执行历史、预算耗尽、原生接受/拒绝与 Momentum 流程、完成后恢复不重复调用。

测试使用固定假响应、模拟 HTTP 和合成工作簿。测试进程禁止网络连接及外部命令。首次测试中两个测试夹具编写问题已修正，日志保留；未因此修改运行源码或原生方法。离线通过不代表效果提升；未进行在线凭据、API 可用性或 Docker 实际运行检查。

- `frozen_manifest.json`：运行源码、配置、审计工具和离线检查代码的 SHA-256。
- `protected_sources.json`：旧实验及 V25.1 的保护哈希；复查确认均未变化。
- `dataset_manifest.json`：沿用 V25.1 的 800 个输入/答案文件哈希。
- `environment_fingerprint.json`：离线检查使用的解释器和包版本，不包含凭据。
- `offline_checks/report.json`：最终检查结果。

只读复查命令，不启动实验：

```sh
python -B experiments/comparisons/skilladam_v25_1_actor_aligned_20261030_001/verify_bundle.py
```

## 后续运行入口约束

`binding.py` 只提供本目录的原生配置绑定和 runner 构造，不含训练 CLI，也不读取凭据或发请求。后续明确授权后，先运行上述冻结检查与在线环境预检，再使用 `binding.components()` 返回的原生传输工厂，显式注入 `binding.make_runner(..., optimizer=...)`。构造本身不启动训练，只有明确调用 runner.run 才会执行。

不得调用冻结旧桥接文件的默认 CLI：其默认实验路径属于历史准备脚本。不得从仓库当前源码或 V25.1 核心替代原生 SkillAdam。未来运行输出使用本目录独立 `campaign/` 和 `test/`；正式启动前另行准备持久状态与恢复入口，不自动继承旧授权或重跑已完成请求。

训练全部完成且最终 Skill 校验后，测试使用本版 Actor、各自最终 Skill 和共同 Test 兼容配置；测试不更新 Skill/Momentum，不调用优化器。当前未执行这些动作。
