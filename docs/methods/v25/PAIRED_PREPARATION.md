# V25 / SkillAdam 统一配对准备

2026-10-27：补齐新配置默认值，并提供只生成配置和执行本地预检的入口。旧实验配置、原始轨迹、冻结源码和清单不改写；本次不启动训练或 Test。

## 默认共享条件

新配置带 `comparison_profile=execution_only_actor48k_v1`。`baseline.configuration()` 默认生成：

- Actor 并发 4，输出 49152 tokens；API 单次 300 秒，程序单次 600 秒，无累计任务时限。
- `attempt_budget_policy=program_executions_v1`：30 次实际程序执行，每份程序最多 6 次生成请求，重试等待为 2 × 尝试编号秒。
- `actor_history_policy=execution_only_v1`：临时格式修复与正式历史分开，优化证据只展示实际执行；原始请求完整保留。
- 原始 initial Skill、80 Train + 40 Val 原顺序、8 × 15 题、1 epoch、不打乱；Test 不参与优化。
- 相同模型、API、提示词、预览、Docker 镜像、执行限制和评分器；Actor 不接收标准答案或评分纠错反馈。
- V25 的模块额度使用 [TOKEN_BUDGETS.md](TOKEN_BUDGETS.md)；SkillAdam 原生优化器仍为 16384。

V25 新配置校验及 SkillAdam 预检会拒绝该版本标记下的部分升级，例如遗漏历史策略、恢复旧计数、并发 1、任务总时限 600 或旧 token 额度。未标记旧配置仍按原协议读取；这不绕过旧实验的源码冻结检查。

## 配对生成与本地预检

在仓库根目录执行，`--output` 必须是不存在的新目录：

```sh
/tmp/govern-skill-v25-venv/bin/python scripts/runs/prepare_spreadsheetbench_comparison.py \
  --output experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001
```

V25 配置只生成一次。SkillAdam 的 `shared_config.json` 与它完全一致；只为 SkillAdam 绑定新准备目录和证据视图，其 `native` 和 `optimizer_transport` 从既有对照模板原样保留。LLM 压缩、96000 字符阈值、Momentum、自适应编辑预算与原生 Gate 不变。

产物：

- `v25/config/campaign.json`、initial Skill、源码 contract、Docker runtime；数据划分位于 `v25/data`。
- `skilladam/shared_config.json`、`skilladam.json`、initial Skill、文件哈希 manifest。
- 根目录 `alignment.json`、`preflight.json`、README。

配置采用 `reference_preparation` 关联，不需要预先创建真实 campaign。`v25/campaign` 与 `skilladam/campaign` 仅在以后另行授权启动时才创建。准备过程读取数据清单、工作簿元数据和文件哈希，启动临时 Docker 容器检查 Python/库版本，不执行数据集任务，不加载 API 凭据或调用模型。

重复只读检查：

```sh
/tmp/govern-skill-v25-venv/bin/python scripts/runs/prepare_spreadsheetbench_comparison.py \
  --output experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001 --check
```

预检核对共享配置相等、原始 Skill、任务顺序、训练与验证批次、Test 隔离、Actor/证据协议、重试预算、token 额度、源码完整冻结、文件哈希、宿主库版本和 Docker 镜像/运行时。该检查不验证在线 API 可用性。未来启动前必须重新检查；漂移应重新准备新的目录，不能重写旧冻结清单绕过校验。

SkillAdam CLI 现在必须显式传入 `--experiment`，避免默认为旧实验目录；旧配置的 `reference_campaign` 仍支持读取。

Test 中已知的 3 个评分区域元数据问题仍保留在配置中，未自行修正。本次准备的是 120 题训练，未启动最终 Test。

## 测试

`test_comparison_preparation.py` 直接检查未手工修补的默认配置，验证部分升级被拒绝，并用合成任务完整生成两种方法的配置、冻结和预检；检查原生方法参数与旧模板保持不变、无 campaign/请求产物、重复准备和配置漂移被拒绝。运行时替身只用于该单元测试；真实准备仍使用实际 Docker 检查。

2026-10-27 验证完成：V25 全套 245 项测试通过（包含 SkillAdam 接入与配对准备测试）。真实配对目录 `experiments/comparisons/v25_skilladam_execution_only_actor48k_20261027_001` 已生成并通过本地环境预检；两份共享配置的 SHA-256 完全相同，原生方法参数与优化器传输配置均保持原样。无 campaign、Actor 轨迹或模型请求产物。
