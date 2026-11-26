# SpreadsheetBench SkillAdam：保留上游优化器重试

状态：仅准备及离线验证，未启动训练、模型请求或 Test。没有创建 campaign。

本实验以 `experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001/skilladam` 为基准，从相同的原始 initial Skill 开始；不继承其训练结果、最终 Skill、Momentum、检查点或额外恢复额度。旧实验配置和结果全部保留。

## 方法配置变更

| 项目 | 原对齐实验 | 本实验 |
| --- | --- | --- |
| API 重试 | SDK 关闭，接入层最多 6 次请求 | 上游 SDK `max_retries=2`，最多 3 次请求 |
| 最大／最小迭代数 | 8／8 | 官方配置 15／15 |
| 补丁应用失败 | 原生 `patch_attempts=1`，接入层负责修复 | 原生 `patch_attempts=3`，沿用上游补丁应用错误反馈 |
| 截断及结构错误 | 接入层统一校验、重采样或附加修复反馈 | 不增加此循环，交给上游解析和方法逻辑 |

直接使用本地上游版本 `b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1` 的 `create_generation_transport()` 和原生结果解析；不修改上游源码。新启动器只保留 DeepSeek thinking 参数适配和无密钥的请求归档。SDK 自行决定哪些请求错误可重试及其退避方式。

三个补丁尝试与 SDK 请求重试分别计数，不是统一的三次或六次总预算。JSON 解析失败不等同于“补丁无法应用”；是否进入原生补丁重试由上游决定，没有额外兜底修复。

## 保持一致的条件

- `shared_config.json` 与原训练配置逐字一致；`initial_skill.md` 逐字一致。
- 原 80 Train + 40 Val，顺序不变，8 × 15 批，Test 不参与训练。
- Actor 仍为 deepseek-v4.1-flash、medium、输出 49152、并发 4、30 次实际执行、每份程序 6 次请求、无整题累计时限；API 300 秒、程序 600 秒。
- 优化器仍为相同模型/API、medium、16384 输出、temperature=1；读取超时 300 秒、连接超时 10 秒。
- `execution_only_v1` 历史与证据、轨迹压缩、96000 字符上下文阈值、Momentum、编辑预算、Gate、同批 baseline/candidate 评估及其他原生参数均不变。
- Stage 0 关闭，自动 Test 关闭。

`frozen_workspace/` 保存原训练 contract 中的完整源码及原接入层、上游 SkillAdam 源码。Actor、事实转换和评分器使用该快照，避免当前仓库后续评分修复及 Prompt 更新混入本实验。它保留的是旧训练评分条件，不声称已使用后续完整 280 题测试的评分兼容修复。

旧 Python 环境缺少 OpenAI SDK，因此新建 `/tmp/govern-skill-skilladam-native-venv`；Python 版本及旧 Actor 依赖版本保持一致，新增 OpenAI SDK 2.54.0 与依赖。完整依赖见 `requirements.lock`，文件与运行时冻结见 `manifest.json`，差异见 `alignment.json`。

## 只读预检

在仓库根目录执行（不需要 API 密钥，不启动实验）：

```sh
PYTHONDONTWRITEBYTECODE=1 /tmp/govern-skill-skilladam-native-venv/bin/python scripts/runs/run_skilladam_spreadsheetbench_native_retry.py --experiment experiments/baselines/skilladam_spreadsheetbench_native_retry_actor48k_20261029_001 --check
```

预检核验冻结文件、数据、初始 Skill、任务顺序、Python 依赖和 Docker 镜像/运行时；Docker 仅检查库版本，不执行数据集程序。不会验证在线 API 可用性。

后续经用户要求启动时才使用同一入口的 `--start`，并显式提供与冻结地址一致的 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY`。已存在 campaign 时拒绝重复启动；异常恢复需单独检查上游检查点，不自动重置失败请求或重写旧结果。不要使用旧 aligned 启动器启动本配置。

原生 usage 统计沿用上游行为，可能不包含 SDK 内部失败请求；实际 HTTP 请求数可由 `campaign/model_calls/*/http_request_*.json` 独立核查。没有服务端用量的失败请求不得算作零 Token。

## 验证

专项测试使用真实 SDK 与内存模拟 HTTP，验证网络重试、不可重试错误、截断/结构失败无额外修复、原生三次补丁应用反馈、参数保留及新旧配置差异。结果见 `verification.json`；所有模型响应均为测试替身。

复核时发现新传输层遗漏了原有优化器输入容量检查，已在发送前恢复 `max_input_chars` 和 `max_message_utf8_bytes` 两项限制；未改变重试机制。修订前清单和启动器保存在 `configuration_revisions/001_restore_input_capacity/`，本实验仍未启动。

此前复核共 15 项测试通过，并比对了旧实验的 136 个逻辑请求。`verification.json` 和 `reaudit.json` 保留为恢复原生重试时的历史记录。当前参数修订的验证结果见 `official_settings_verification.json`。

2026-10-29 修订：最大／最小迭代数从 8／8 改为官方的 15／15，其余配置不变。顺序采样仍只遍历 120 个任务一次，共 8 批，不会补足 15 批。修订前配置、启动器、测试及报告保存在 `configuration_revisions/002_official_iterations/`。

这里的“一致”指实验条件，不表示实现逐字相同：优化器传输改用 SDK，额外安装其依赖，并改用独立 HTTP 请求审计；恢复/缓存行为也按新入口说明处理。旧实验曾单独授权的额外恢复额度不继承到新实验。
