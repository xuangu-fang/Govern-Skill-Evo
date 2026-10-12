# v17 正式多轮实验

冻结目录：`experiments/methods/v17/v17_formal_001/config`。入口：`scripts/runs/v17/run_v17_formal.py`。
历史 v16、pilot 轨迹和 policy 不改动，也不用于正式学习。

## 固定协议

- 73 个原有任务，32 train（Evolution）/41 monitor，分割不变。
- S0 为原始空 Skill。最多 3 轮，每轮使用同一组任务、seed 200。
- 轨迹生成沿用 v16 的 8 线程并行：Evolution 任务和 Monitor 的 Parent/Candidate 调用使用独立环境、独立产物目录，汇总保持固定任务顺序。已完成 Evolution 任务在 resume 时复用；并行任务出错不生成部分学习输入，其他已完成任务仍落盘。
- Evolution 每任务 1 rollout；Monitor 每任务每个角色 1 rollout，Parent/Candidate 都重新运行，不缓存 Parent。
- Agent/User 使用已有 deepseek-v4-flash 配置；Grouping 使用固定 alias seed 200、temperature 0、v17-grouping-2；Diagnosis v7、Editor v1 使用 deepseek-v4-pro、temperature 0。
- 每轮重新 Grouping/Diagnosis/Compiler/Editor。只有 Gate ACCEPT 才更新 current_skill.md。RETAIN 后下一轮仍使用 Parent。
- 四个 Δ 使用完整 matched Monitor 的整数计数判断；不使用 bootstrap。
- 最多 342 次 Agent rollout，不包括 Grouper/Diagnosis/Editor 调用。相同 seed 并不保证远端模型逐字复现。

## Policy 清理

两个领域都只移除了 “make one tool call at a time” 子句，保留了工具调用与用户回复不同时发生的独立约束，以及所有其他业务 policy。
清理后的实际 policy 保存于冻结目录，正式进程在创建 Agent 之前替换 Environment.get_policy 的返回值；读取到非冻结原始 policy 时拒绝运行。替换只在正式执行作用域内生效。S0 和 learned Skill 都使用同一份清理后 policy，Diagnosis 引用实际可见文本，不额外注入 pilot 排除说明。
原有确定性 evaluator 按治理条件评判，不增加 multi-tool-call 目标。

## 冻结与数据边界

config.json 明确正式调度参数；其中 base_config 是原始模型构建配置，原有 planned_rollouts 等历史元数据不参与正式调度。manifest.json 绑定源代码、构建全部环境时读取的数据、任务/划分、policy、工具上下文、空 Skill。运行前和每轮开始核对这些实验文件，漂移即停止。Python 和主要模型 SDK 版本仅记录用于审计，不要求运行环境版本一致。任务内容在 tasks.json 留存快照，运行时仍读取已绑定原文件，因此须保留当前仓库。冻结不能锁定模型供应商背后的服务版本。

Evolution 的原始数据库和 evaluator 详情写入 evolution_private；learner 只接收现有 learner-safe 边界产生的经验与二值监督。Monitor 数据只写入 monitor_private，不回流至下一轮 Diagnosis。

## 失败及停止

- Diagnosis/Editor 不重试、不修补；某个 Diagnosis 拒绝后完成其他组的独立调用，但不做部分编译。
- Grouping 保留现有的一次格式修复机制。Agent/User 保留已有配置的空回复重试；不重跑整条失败 trajectory。
- 无编辑计划（NO_UPDATE）或 Editor UNABLE：保留 Parent，提前停止。
- 编译/校验/传输失败或 Monitor 不完整：标为 INCOMPLETE，停止，不提升 Candidate。
- Evolution 中断后可使用 `--run --resume --output 原输出目录` 续跑。复用完整轨迹和评估，不按结果筛选；若仅缺评估则本地补评估；不完整的任务产物归档后从该任务初始状态重新执行。已经生成有效 Candidate 时，也支持直接续跑 Monitor，复用完整的 Parent/Candidate 轨迹，未完成任务重新执行。Grouping 中断时归档未完成调用并重新分组；完整分组结果校验后直接复用。Diagnosis 的 VALID 组重新校验后复用；REJECTED 或未完成组归档至 group.attempt-N 后重新请求一次，全部 VALID 后才编译。每次显式 resume 只补跑一次，不在失败后循环重试。Compiler/Editor 自身调用中断的恢复暂不支持。失败产物保留供检查。
- 所有轮结束或提前正常停止后查看 campaign.json；每轮 Monitor 的 summary.json 包含四象限和迁移统计。

## 用户启动

```bash
cd /Users/didi/Desktop/Govern-Skill-Evo && python -u scripts/runs/v17/run_v17_formal.py --run --output artifacts/methods/v17/formal/v17_formal_001
```

省略 `--run` 只做无模型预检。使用当前已安装依赖、可读取项目 `.env` 的 Python。输出目录必须不存在。

本次实现仅执行单元测试和无模型预检，并验证两个领域在 S0/learned Skill 下实际构造的 Agent policy 与冻结上下文相同；未启动正式 rollout。

## 第四轮扩展

前三轮完成后，显式使用 `--run --resume --total-rounds 4 --output artifacts/methods/v17/formal/v17_formal_001` 扩展一轮。保留原三轮配置和结果，在 resume_history.json 记录新轮数及原状态。第四轮从 current_skill.md（已验证与第三轮保留摘要一致）开始，重新生成 Evolution；若再中断，继续使用相同的 `--total-rounds 4` 命令。其他学习协议与 Gate 不变，不应用离线分析提出的 prompt 修改。
