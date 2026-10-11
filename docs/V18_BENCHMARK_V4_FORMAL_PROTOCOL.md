# v18 × benchmark v4 正式四轮协议

2026-09-20。本次仅冻结协议、实现命令行入口并完成无模型验收，不启动真实模型运行。

## 固定设置

新冻结目录：`experiments/configs/v18_formal_003`。旧 `v18_formal_001`、`v18_formal_002` 和历史 Pilot 文件原样保留。旧 manifest 不随源码更新而重写，因此旧入口是否仍可启动取决于原有源码绑定。

- Diagnosis：`v18-group-diagnosis-3.2.1`；Editor：`v18-bounded-editor-1`；Grouping：`v17-grouping-2`。
- benchmark：`phase_v4_day36`，共 81 任务，36 Evolution + 45 Monitor；不是旧版 73 任务。
- seed 200，每任务每角色一次；四轮最多 504 个 Agent rollout。
- 原始 S0 起步，不使用任何 Pilot Candidate。模型参数见冻结 `config.json`，源码、配置、实际 Simulator prompt 和协议均由 manifest 绑定。
- `protocol.json` 预先规定指标、分析切片、晋升、停止和恢复原则。实验中不根据结果改 Prompt、改 Gate、挑 seed 或重跑取优。

## 启动与恢复

在仓库根目录执行：

```bash
# 无模型预检
python scripts/run_v18_formal_v4.py

# 启动全新正式四轮
python scripts/run_v18_formal_v4.py --run

# 中断或运行错误后恢复同一个正式实验
python scripts/run_v18_formal_v4.py --run --resume
```

默认输出目录：`experiments/v18_v4_formal_002`。首次启动要求目录不存在；已有实验必须使用 `--resume`。自定义目录时，启动和恢复传入相同的 `--output`：

```bash
python scripts/run_v18_formal_v4.py --run --output experiments/my_v18_v4_run
python scripts/run_v18_formal_v4.py --run --resume --output experiments/my_v18_v4_run
```

本协议锁定四轮，不允许用 `--total-rounds` 扩展。保留该兼容参数时只允许恢复并指定原四轮上限。可选 `--pilot` 使用独立输出 `experiments/v18_v4_pilot_002`，只运行一轮，不能作为正式运行恢复。

## 停止、晋升及恢复

只有 Monitor COMPLETE 且 Gate ACCEPT 才晋升 Candidate。RETAIN 保留 Parent 并继续；NO_UPDATE / UNABLE 提前结束；运行错误标记 INCOMPLETE，保留审计产物，由用户显式恢复。四轮是上限，不强行补满。

文件锁阻止同目录并发进程。恢复要求配置、运行模式、冻结 manifest 和相关产物绑定一致；已验收的 VALID / APPLIED_DETERMINISTIC Candidate 可复用，空 Candidate 也进入 Monitor。未完成阶段按既定规则归档后恢复；重做 Grouping 时隔离旧 Diagnosis。不能为获取更好的 Gate 结果删除产物后重跑。

## 预先确定的分析

保持原 Four-Delta Gate：全部 45 个 Monitor 任务上，ΔS、ΔC、ΔCS 非负，ΔVF 非正，至少一项严格改善。统计整数计数，并同时报告比例与分母。

每轮报告 Parent/Candidate 的 S、C、CS、VF、四象限计数和配对转移矩阵；分别列出全部 Monitor、Core、回归保护任务、各 family 和联合 family。分层结果用于分析，不另设事后晋升门槛。跨轮 Parent 可能不同，不将不同轮次的配对增益解释为同一 S0 对照。

语义审计记录条件、适用范围、确定性保持及新增无依据义务，不在实验中按 Monitor 错题修改 learner。

局限保留：单 seed；Monitor 已参与 benchmark 开发；JRA-01 原合同结果仍为 HOLD_REPLICATION，v4 的独立准入决定不等于原合同通过。

## 验收记录

产物目录：`artifacts/v18_v4_formal_readiness_001`。包含预检、测试日志、旧冻结逐文件不变检查和新 manifest 摘要。所有本次验收均无真实模型调用。

最终验收：相关回归 572 项通过（含 29 项 v4 专项测试）；81 任务预检通过；旧冻结 16 个文件逐字节不变，S0 与原冻结一致，v17 差异摘要不变。正式输出目录尚未创建。
