# ALFWorld SkillAdam：保留上游优化器重试

状态：仅创建配置及完成离线验证，未启动训练、真实模型请求或 Test。没有创建 campaign。

基准为 `experiments/baselines/skilladam_current_actor_20261025`，原结果位于 `artifacts/baselines/skilladam/alfworld_current_actor_20261025`。本实验从相同原始 initial Skill 重新开始，不继承旧最终 Skill、Momentum、检查点或人工恢复。旧实验文件不改写。

## 改动范围

| 项目 | 原 ALFWorld 配置 | 本配置 |
| --- | --- | --- |
| 优化器 API 重试 | SDK 重试关闭，外层最多 3 次请求 | 上游 SDK `max_retries=2`，最多 3 次总请求 |
| 训练并发 | 8 | 官方配置 10 |
| 输出截断或解析异常 | 外层可再次请求 | 无额外重采样，交由上游解析及方法逻辑处理 |
| 补丁应用失败 | 原生 `patch_attempts=3` | 保持 3 次，保留原生补丁错误反馈 |
| Momentum / 压缩输出错误 | 无统一结构修复循环 | 不增加修复循环 |

直接调用上游 `create_generation_transport()`；SDK 负责错误分类和退避。未修改上游源码。保留原成功调用缓存和失败调用不得自动重置额度的恢复边界，另存实际 HTTP 尝试以审计 SDK 内部重试。没有新增格式修复 Prompt，也没有手工修改模型输出。

## 保持一致的实验条件

- `actor.json` 仅 workers 从 8 改为 10；初始 Skill、优化清单、三个 split 清单均与原实验逐字一致。
- 39 Train + 18 Selection，共 57 项优化任务；6 轮，批次 10、10、10、10、10、7，顺序不变；134 Test 不参与训练。
- 原 Actor 子进程、动作及轨迹转换、环境和评分：50 步、最近 2 步历史、seed=42；每动作最多 6 次请求及原有动作错误反馈。训练并发改为 10。
- 模型 deepseek-v4.1-flash、medium、temperature=1、输出 16384、读取超时 300 秒、连接超时 10 秒、原 API 地址和 thinking 参数。
- 原生 `native` 整个对象不变：Momentum、LLM 压缩、最近 2 个完整优化迭代、context limit=110000、编辑预算、Gate、同批 baseline/candidate 评估等均保留。
- Stage 0 关闭，自动 Test 关闭。
- 复用原 SkillAdam Python 环境和 Actor Python 环境；没有安装或升级依赖。原依赖清单中 61 个固定版本全部一致。

原代码的 396 个冻结文件仍匹配历史清单，因此直接引用并再次冻结，不复制或修改原源码。预检也核对 191 个 ALFWorld 环境任务文件，以及当前 Actor 的 Python/依赖快照。相关文件变化会使预检失败。

配置 JSON 改变训练并发（8 → 10）、优化器重试策略、移除外层请求次数字段、启用 SDK 重试以及绑定新的输出目录。`patch_attempts` 在 ALFWorld 原本已经是 3，未作修改。

## 离线验证

12 项新测试通过，使用真实 SDK 与内存 HTTP 替身，覆盖：SDK 可重试/不可重试错误、截断与结构错误没有额外修复、原生三次补丁反馈、成功调用缓存和失败不自动重置、离线入口不会启动训练。

原实验的 69 个逻辑调用（57 压缩、6 补丁、6 Momentum）的实际请求体、API 地址及连接/读取超时逐项比对一致。有效原生配置和 Gate 与原实验完成时的 checkpoint 一致；模型上下文仅 workers 改为 10。

2026-10-29 并发修订前文件保存在 `configuration_revisions/001_official_workers/`。`verification.json`、`reaudit.json` 保留为原生重试配置的历史核验记录；当前验证见 `official_settings_verification.json`。旧结果保留证据见 `preserved_results.json`。

SDK 内部失败请求未必计入上游逻辑 usage；物理请求数以新 campaign 的 `model_calls/*/http_request_*.json` 为准，未知 Token 用量不能当作零。

## 只读预检

在仓库根目录执行，不读取密钥、不调用模型、不初始化 ALFWorld 环境：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/skilladam/bin/python scripts/runs/run_skilladam_alfworld_native_retry.py --experiment experiments/baselines/skilladam_alfworld_native_retry_20261029_001 --check
```

后续用户明确要求启动时才使用同一入口的 `--start`；本次未执行。新输出为本目录的 `campaign/`，绝不写入原结果目录。已保存 Gate 的恢复使用 `--start --resume`；未完成的优化器请求或 Actor episode 仍要求单独审查，不能借恢复重置额度。

原 ALFWorld 实验第 3 轮曾有单独授权的重试及 JSON 转义修复，属于旧实验历史，不包含在本实验配置中。
