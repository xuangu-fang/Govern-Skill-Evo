# v24.1 ALFWorld：review_02 / workers 10 / no review

状态：已准备，未启动。离线检查 158/158 通过（v24.1 新增 26 项，原 v24 回归 132 项），无失败或跳过；7340 个原有文件的完整性核对通过。此目录只包含配置、数据快照及离线验证材料，没有 S1 训练目录或新实验结果。

基线：`experiments/methods/v24/alfworld_history_and_plan_v3_no_review_workers10_20261029_001`。

四模块 Prompt 完整采用批准的复审稿；Diagnosis 使用 `revise` / `no_change`。其他方法契约与实验条件保持基线设置，详见 [配置差异](config/provenance/alignment.json)。

| 条件 | 本配置 |
| --- | --- |
| 训练并发 | 10 |
| Verifier / Repair | 关闭，无对应调用预算 |
| 优化数据 | 原 57 题，批次 10、10、10、10、10、7 |
| 初始状态 | 与基线相同的初始 Skill；空 Memory |
| Actor | 原 action-only 协议、50 步、历史长度 2 |
| 重试 | Actor 与自进化模块保留原每次逻辑调用最多 6 次请求 |
| 模型与输出额度 | 与基线完全一致；Preconditioner / Replay 保留 32768，其他默认 16384 |
| Gate | Candidate 成功数严格大于 Parent 才接受 |
| Test | 保留原 134 题清单；未执行，也不自动启动 |

`config/source_config.json` 是基线配置原样副本；`config/campaign.json` 是新配置。逐字段差异仅 7 项：方法版本、四模块 Prompt 版本、适配器版本与 Prompt profile。代码中的 Diagnosis 决策校验同步更新；独立命名空间和输出目录隔离新旧实验。

`config/source_contract.json` 固定当前实现和 Prompt；`config/runtime.json` 已验证与基线运行环境相同。`data/`、`config/budget.json`、初始基线成绩引用均原样复制。基线成绩引用仅供后续对比，不属于 v24.1 的成绩。

[验收报告](results/verification_report.json)和[原始测试明细](../../../../artifacts/methods/v24_1/alfworld_reviewed_no_review_workers10_20261030_001/offline/verification/tests.xml) 是离线检查结果，包含模拟响应和模拟 Actor 的临时测试流程。它们不是训练结果，不能说明 v24.1 的成功率。[来源保留记录](config/provenance/preservation.json) 记录旧 v24、原实验和已批准草案的文件完整性检查。

仅用于再次离线核验（输出目录必须未存在）：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/alfworld/bin/python scripts/runs/v24_1/verify_v24_1_offline.py --output /tmp/v24_1_offline_recheck
```

后续若明确批准启动，应使用 `python -m src.skill_evolution.v24_1 run`、本目录的 `config/campaign.json`，以及独立的 `artifacts/methods/v24_1/alfworld_reviewed_no_review_workers10_20261030_001/S1`。本次未执行该操作。
