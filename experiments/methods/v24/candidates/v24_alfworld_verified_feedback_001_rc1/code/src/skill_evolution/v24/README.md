# V24 ALFWorld 候选基线

候选名称：`v24_alfworld_verified_feedback_001_rc1`。
来源：v23.5 的 `alfworld_verified_feedback_001` 最终配置。
本版本保留自进化方法，简化运行记录，并将 Actor 实现纳入 v24 适配器。

## 方法与边界

Parent → Grouping → Diagnosis → Preconditioner → Editor → Candidate
→ 严格成功数 Gate → Replay → Verifier → 必要时一次 Repair → 发布。
保留 no_change、need_evidence、needs_revision、有限反馈与原恢复规则。
每个方法模块和 Actor 每步最多六次总尝试，首次请求计入。

方法核心不导入旧版方法。`benchmarks/alfworld/` 包含领域证据、完整原文 prompt、
Actor 及其协议资源。`benchmark.py` 显式绑定适配器，工作线程继承绑定。
协议中的旧版本名表示未变的语义契约，不表示执行旧代码。

记录使用普通版本名、文件路径和实际内容。保留任务身份、动作合法性、输出结构、
调用预算和发布流程检查。ALFWorld 记录格式是当前约定；接入 SpreadsheetBench
时再适配结果、恢复和成本统计，不作为本版本的阻塞项。

## 与原基线的差异

模型、任务事实、初始 Skill、prompt 原文、动作协议、预算与更新决策不变。
配置增加 benchmark 绑定，更新方法版本，初始 Skill 仅保存来源和正文。
Actor 使用 v24 内的入口；来源清单与 Skill/执行/请求记录的额外机器标识已移除。
Verifier/Repair 的输入同步简化这部分元数据。因此验收检查行为和任务证据，
并单独列出这些预期差异，不宣称所有输入字节完全相同。

## 离线准备与验收

```bash
python -m src.skill_evolution.v24.evolution audit-baseline
python -m src.skill_evolution.v24.evolution prepare --output artifacts/methods/v24/prepared_new
python scripts/runs/verify_v24_offline.py --output artifacts/methods/v24/offline_new
```

准备及验收目录须为新目录。准备读取历史基线配置和任务数据，不调用模型。
离线验收使用保存记录及模拟响应，禁止网络和真实 Actor 入口。
独立进程重放、故障恢复、配对流程、最终评估与 Actor CLI 都在覆盖范围内。

## 后续真实运行

本次没有启动真实训练或 Test。正式运行需另行明确指令。
正式配置包含六批任务，不能把直接执行 run 当作单轮验证。
小规模验证应使用独立配置，只保留原第一批任务及其 task_items。

```bash
python -m src.skill_evolution.v24.evolution run --campaign /path/to/run/S1 --config /path/to/config/campaign.json
python -m src.skill_evolution.v24.evolution resume --campaign /path/to/run/S1
python -m src.skill_evolution.v24.evolution status --campaign /path/to/run/S1
```

完成训练后，可用 `src.skill_evolution.v24.evaluation`，显式提供 `--root`、
`--experiment`、`--campaign` 评估最终 Skill。Test 不更新 Skill 或 Memory。

Python 调用须使用 `using_benchmark(ALFWorldAdapter())`。旧 Campaign 不直接
用 v24 恢复。最终 Skill 和 Memory 只从正式发布状态读取。

候选材料见 `experiments/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/`。
后续方案见 [NEXT_EXPERIMENTS.md](../../../docs/methods/v24/NEXT_EXPERIMENTS.md)。
