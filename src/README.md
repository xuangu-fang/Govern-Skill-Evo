# `src` 源码目录

本目录保存项目自己实现的代码。第三方 benchmark 位于 `external/`，实验产物位于 `experiments/`，二者不应与这里的实现代码混在一起。

如果只是想找到某项功能，可以先看下面的“目录说明”；如果要运行 Autonomous GSE，再阅读“正式演化流程”。命令和代码中使用的英文名称会保留，正文则说明它们的实际作用。

## 目录说明

| 目录 | 作用 |
|---|---|
| `adapters/` | 将外部系统的数据和运行方式接入本项目。`tau2/`中包含τ³结果到统一轨迹的转换器，以及本地 Skill Agent 补丁。 |
| `policies/` | 保存带版本号的规则，以及校验规则时需要的背景信息。 |
| `trajectory/` | 定义统一的任务交互记录格式，并提供旧格式迁移工具。 |
| `verifiers/` | 判断任务是否成功、执行过程是否合规，并输出判断依据。 |
| `learners/` | 从任务交互记录中总结经验，生成第一个候选 Skill，或小幅修改已接受的 Skill。 |
| `skill_evolution/` | 负责分批、生成候选版本、比较评测结果、决定是否接受，以及正式运行前的完整性检查。 |


## 基础校验流程

下面的图展示：不同来源的任务记录如何先转成统一格式，再分别判断“任务是否完成”和“过程是否合规”。图中的英文名称是代码里的正式对象名。

```text
τ³ results.json
    ↓ adapters/tau2/tau2_to_common.py
TrajectoryDataset
    ├──→ verifiers/task_verifier.py
    │       └── TaskVerdictDataset
    ├──→ Semantic rule handlers
    │       + PolicyRuleSet + VerificationContext
    │       └── Saved judgments
    │
    └──→ Process Verifier输入

TrajectoryDataset + PolicyRuleSet + VerificationContext + Saved judgments
    ↓ verifiers/process_verifier.py
CheckerRegistry
    ├── Deterministic handlers
    └── Semantic handlers
    ↓
ProcessVerdictDataset
```

## Autonomous GSE 正式演化流程

Autonomous GSE v0.1 会把训练任务分成三批。每一步使用当前已接受版本完成一批任务，根据本批经验提出候选版本，再通过固定评测决定是否接受：

```text
已锁定的实验配置 + 明确的无 Skill 起点 S0 + 固定任务分批表
    ↓ autonomous_gse_runtime.py
计算下一步状态
    ↓
完成训练任务 → 整理受规则约束的经验 → 提出候选 Skill
    ↓
重新运行选择评测 → 按演化门槛判断 → 接受候选版本或保留当前版本
```

状态计算、候选格式检查和正式任务运行彼此分开。正式入口在调用浏览器、模型或数据库前，会通过 `autonomous_gse_freeze.py` 核对冻结记录以及所有登记文件，防止使用到被意外修改的输入。

常用命令如下：

```bash
# 只读查看冻结执行计划
conda run -n stwebagentbench python -m \
  src.skill_evolution.autonomous_gse_benchmark_runtime plan

# 重新运行18个S0选择评测任务，并保存初始评测基准
conda run -n stwebagentbench python -m \
  src.skill_evolution.autonomous_gse_benchmark_runtime initial-checkpoint

# 只读查看当前正式文件和运行状态
conda run -n stwebagentbench python -m \
  src.skill_evolution.autonomous_gse_benchmark_runtime status

# 仅在状态为READY_TO_RUN时执行三个正式步骤，并写入实验报告
conda run -n stwebagentbench python -m \
  src.skill_evolution.autonomous_gse_benchmark_runtime run
```

`rollout` 是程序内部使用的子进程入口，不是日常人工命令。`run` 不会自动补做缺失的 S0 评测基准，也不能自动从中断处继续；遇到中断时应先查看 `status`，不要直接重跑。

## 使用约定

- 所有命令都从项目根目录运行，例如`python -m src.verifiers.task_verifier`。
- 数据转换程序不得编造源数据中不存在的状态；无法恢复的字段应保留为 `None`。
- 校验结果必须包含可追踪的证据，并指向对应的交互步骤。
- Human Gold 指人工审核后确认的标准答案，不能用模型输出自动覆盖。

更详细的说明见：

- [`trajectory/README.md`](trajectory/README.md)
- [`verifiers/README.md`](verifiers/README.md)
- [`adapters/tau2/README.md`](adapters/tau2/README.md)
