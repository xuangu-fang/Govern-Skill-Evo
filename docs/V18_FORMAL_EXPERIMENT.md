# v18 完整调度（第 6 步）

2026-09-19。独立入口已实现，v17 文件与行为不修改。当前完成配置冻结、无模型预检与调度测试，尚未启动真实模型 campaign。

## 路径与配置

- `scripts/freeze_v18_formal.py`：创建新冻结，已有 manifest 时拒绝覆盖。
- `scripts/run_v18_formal.py`：默认只预检，显式 `--run` 才调用模型。
- `src/skill_evolution/formal_v18.py`：Evolution → Grouping → Diagnosis v18 → Compiler v18 → Editor v18 → Monitor → Gate。
- `src/skill_evolution/monitor_benchmark_v18.py` / `monitor_v18.py`：独立 v18 后端与原 Four-Delta 整数计数 Gate。
- `experiments/configs/v18_formal_001/`：S0、配置、任务、清理后的 policy、可见上下文、逐任务 User prompt 和依赖文件摘要。

默认 4 轮；32 个 Evolution 任务，41 个 Monitor 任务，seed 200；每任务每角色一次，最多 456 次 Agent rollout。Evolution 与 Monitor 均使用 v18 Simulator 和相同冻结 User prompt。Grouping、经验投影和 Diagnosis 输入封装复用 v17 公共能力；Diagnosis 使用 v18 Prompt v2，Editor 使用 v18 Prompt v1。

`user_prompts.json` 包含私有 User Scenario，只供运行时绑定和审计；不得传给 learner。Monitor 轨迹、标签、二维分布及转移矩阵均留在 `monitor_private`，调度仅消费完成状态及 ACCEPT/RETAIN。

## 状态与恢复

- 全部组 Diagnosis VALID 后才编译；任意失败都不做部分编译。
- Editor VALID 和纯 DELETE 的 APPLIED_DETERMINISTIC 均进入 Monitor。空或仅标题 Candidate 仍保留原文与摘要，使用基线 Agent 装配。
- NO_UPDATE / UNABLE 保留 Parent 并停止；错误标记 INCOMPLETE，不晋升。
- 只有 Monitor COMPLETE 且 Gate ACCEPT 才晋升；RETAIN 继续沿用 Parent。
- `--resume` 要求配置与原冻结 manifest 完全一致。已完成 Evolution 复用；Grouping/Diagnosis 重验后复用；未完成或失败的调用在显式恢复时归档后尝试一次，不自动重试。
- 已完成 Editor 校验 Candidate、Parent 和产物摘要后复用；未完成 Compiler/Editor 归档后从绑定输入重建。Monitor 逐任务校验配置、Skill、seed 和 checkpoint 文件摘要后复用，部分结果归档后重跑。
- campaign 先提交每轮保留摘要，再更新 `current_skill.md`。恢复时从已提交 ACCEPT 记录重建当前 Skill，避免两文件写入中断导致 Parent 丢失。
- 达到轮数上限的已完成运行可以显式增加总轮数；NO_UPDATE / UNABLE 停止的运行不延长。

## 运行

```bash
# 已有冻结时直接预检；不调用模型
python scripts/run_v18_formal.py

# 开始正式四轮实验
python scripts/run_v18_formal.py --run

# 恢复同一实验
python scripts/run_v18_formal.py --run --resume

# 示例：将达到轮数上限的运行延长到六轮
python scripts/run_v18_formal.py --run --resume --total-rounds 6
```

默认输出为 `experiments/v18_formal_001`，可用 `--output` 指定新目录。冻结完成后修改受绑定源码会被拒绝，不能用更新旧 manifest 的方式继续同一实验。

## 验证与限制

73 个任务的实际 orchestrator/User prompt 构造预检通过，模型调用数为 0。测试覆盖完整 learner 接线（模拟模型响应）、真实 Compiler/Editor 的纯 DELETE 与混合操作、空 Candidate 经过真实 Gate、保留/晋升、失败、冻结漂移及中断恢复。

尚未验证真实 Editor 模型的语义保持能力，也未证明四轮学习效果；Diagnosis Pilot 中 transfer fallback 的残留语义问题未在调度或 Compiler 中修补。

验证记录：`artifacts/v18_formal_integration_001/`。v17/v18 相关回归 532 项通过，随后新增 Monitor 后端 checkpoint 篡改/复用测试 1 项通过，合计 533 项。全 `tests/skill_evolution` 收集被旧 v06 测试缺少 `browsergym.experiments` 阻断，未声称全目录通过。

## Benchmark v4 freeze

`experiments/configs/v18_formal_002/` 是独立的新 freeze，对应 `phase_v4_day36`。它保留原 64 个 Core 和 9 个 regression guard，并加入 8 个 `JRA-01` 联合任务：36 个 Evolution、45 个 Monitor，默认四轮最多 504 条 Agent rollout。Diagnosis 使用通过固定输入回归的 `v18-group-diagnosis-3.2.1`。

旧 `v18_formal_001` 和 benchmark v3 不做修改。v4 使用独立的 runtime、Monitor adapter、runner 与输出目录：

```bash
python scripts/run_v18_formal_v4.py
python scripts/run_v18_formal_v4.py --run
```
