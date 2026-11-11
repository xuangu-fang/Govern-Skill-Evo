# ALFWorld SkillAdam：官方 deepseek-flash 优化器

状态：仅准备新配置，离线核验完成；未启动训练、真实模型请求、ALFWorld episode 或 Test，没有创建 campaign。

基于 2026-10-29 的 `skilladam_alfworld_native_retry_20261029_001`。旧配置、旧入口和旧实验结果保留。

## 唯一实验变量

优化器（轨迹压缩、Skill 补丁生成、Momentum 更新）由内网 `deepseek-v4.1-flash` 切换为官方 `deepseek-flash`，地址为 `https://api.deepseek.com`。

为使该设置实际生效，使用独立入口 `scripts/runs/run_skilladam_alfworld_official_optimizer.py`。旧入口将优化器路由绑定到 Actor，不能用于此配置。新入口读取 optimizer_transport 的模型和地址，不修改 Actor 路由。

官方优化器凭证使用独立环境变量 `ALFWORLD_OPTIMIZER_KEY`；Actor 保留原有 `.env` / `OPENAI_API_KEY` 内网凭证流程。凭证值不写入配置。本次未读取或验证真实密钥。未来启动前需提供官方凭证。

输出目录独立为本目录的 `campaign/`；不继承历史 checkpoint、最终 Skill 或 Momentum。

## 保持不变

- `actor.json` 与 10 月 29 日准备版逐字一致：内网 `deepseek-v4.1-flash`，workers=10、50 步、最近 2 步历史、每动作最多 6 次请求；Prompt、环境、工具、评分和输出限制不变。
- 优化器输出 16384、temperature=1、thinking enabled、medium、读取超时 300 秒、连接超时 10 秒、SDK 重试 2 次、patch_attempts=3。
- `native` 对象完全不变：57 个优化任务，6 轮，批次 10/10/10/10/10/7、same_batch、seed=42、顺序采样、历史 2 轮、上下文 110000、编辑预算和 Gate 均不变。
- 初始 Skill、优化任务清单和三个 split 文件逐字一致；Momentum 开启，Stage0 关闭，训练期间不运行 Test。
- Actor / 优化器 Python 环境与依赖不变。旧 SDK 重试、成功缓存及失败调用不得静默重置的恢复规则不变。

## 离线验证

13 项测试通过：用真实 SDK 配合内存 HTTP 替身核对官方地址、模型、独立凭证、重试与缓存；重放历史 69 条逻辑请求，除模型与地址外请求内容一致。所有网络交互均为模拟，未调用真实服务。

测试文件：`tests/adapters/alfworld/test_skilladam_official_optimizer.py`。
`manifest.json` 固定源配置、源代码、环境依赖和新入口；`source_files.json` 记录旧准备版文件哈希；`verification.json` 保存核验结论。

## 只读预检

在仓库根目录执行，默认及 `--check` 均只预检，不读取密钥或初始化任务环境：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/skilladam/bin/python scripts/runs/run_skilladam_alfworld_official_optimizer.py --experiment experiments/baselines/skilladam_alfworld_official_optimizer_deepseek_flash_20261030_001 --check
```

只有未来明确要求训练时才使用该独立入口的 `--start`。本次未执行启动。
