# SpreadsheetBench 上的 SkillAdam

SkillAdam 使用自己的优化器、Gate、Momentum 和检查点。实验按 Actor 和反馈配置归属。[十一条训练或准备记录及二十九次完整评测](../../../../experiments/methods/skilladam/spreadsheetbench/README.md)

| 配置 | 维护位置与用途 |
|---|---|
| 共享 Actor | [运行入口](../../../../scripts/runs/skilladam/spreadsheetbench/shared_actor/run_skilladam_spreadsheetbench_aligned.py) 使用 v25 的 SpreadsheetBench 执行环境。 |
| 原生重试 | [运行入口](../../../../scripts/runs/skilladam/spreadsheetbench/native_retry/run_skilladam_spreadsheetbench_native_retry.py) 使用保留的历史 Actor、SDK 重试和原生补丁重试；本配置仅准备。 |
| 上游 Actor 提示词 | [准备期实现](../../../../src/skill_evolution/skilladam/spreadsheetbench/upstream_actor/prepared/actor_runtime) 和 [实际运行实现](../../../../src/skill_evolution/skilladam/spreadsheetbench/upstream_actor/scheduled/actor_runtime) 分别保留各自的 Actor、资源和相邻桥接模块。 |
| 对齐 Actor | [配置绑定](../../../../src/skill_evolution/skilladam/spreadsheetbench/aligned_actor/binding.py) 组合本配置的 Actor、评分器和原生优化器。 |
| 逐步轨迹反馈 | [运行入口](../../../../scripts/runs/skilladam/spreadsheetbench/trajectory_feedback/run_spreadsheetbench_skilladam_v25_5_feedback.py) 读取对齐配置，将当前训练轨迹传给原生摘要阶段；训练输出和评测单独记录。 |

四份独立快照中的上游 Python 包，每份 281 个文件，与[仓库内的 SkillAdam 上游包](../../../../src/skill_evolution/skilladam/upstream/skilladam)逐文件一致。维护入口共用这份包，Actor 使用各自的模块路径。[请求缓存](../../../../src/skill_evolution/skilladam/spreadsheetbench/aligned_actor/native_cache.py)由对齐调度和逐步反馈共同调用。

## 离线验收

从仓库根目录运行。前两条核对精选材料和可导入的配置。第三条增加对历史检查点和 8,120 条测试轨迹的核对。

```sh
python scripts/runs/skilladam/spreadsheetbench/verify_bundle.py
python scripts/runs/skilladam/spreadsheetbench/trajectory_feedback/run_spreadsheetbench_skilladam_v25_5_feedback.py preflight
python scripts/runs/skilladam/spreadsheetbench/verify_bundle.py --archive
```

[对齐配置测试](../../../../tests/skill_evolution/skilladam/spreadsheetbench/aligned_actor/offline_suite)使用合成工作簿和模拟 HTTP；[逐步反馈专项验收](../../../../scripts/verification/skilladam/spreadsheetbench/trajectory_feedback/verify_spreadsheetbench_skilladam_v25_5_feedback.py)读取归档的训练轨迹。原生重试入口的 `--prepare --experiment <新目录>` 可在本地 Docker 环境准备新输入。
