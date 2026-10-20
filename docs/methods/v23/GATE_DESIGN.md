# V23 Gate 设计与实现

Gate 根据同一批经核验任务的环境成功数量，确定是否采用 Candidate。它不调用模型，不评价 Skill 文本，不学习 Memory，也不直接提交下一轮状态。

## 输入与判定

```json
{"pairs":[{"task_id":"train:0012","parent":{"run_id":"parent-execution-id","success":true},"candidate":{"run_id":"candidate-execution-id","success":false}}]}
```

`run_id` 使用原始执行档案的真实身份。冻结任务清单作为程序参数与来源保存，不增加模型输入或核心结果字段。配对必须非空，任务及执行身份不重复，两侧任务集合都必须完整等于冻结清单。`success` 只接受布尔值，来自经过核验的环境反馈，不能来自模型自评。

唯一判定规则：Candidate 成功数严格大于 Parent 则 `ACCEPT`，否则 `RETAIN`。步数、修复、退化、Memory 和文本质量均不参与决定。即使部分任务退化，只要净成功数增加，仍然 ACCEPT。

正式输出严格四字段：

```json
{"decision":"RETAIN","parent_success":3,"candidate_success":2,"compared":4}
```

## 来源核验与技术停点

`build_gate()` 复用 `facts.build_facts()` 重建执行事实、核对每步实际 Prompt、行动前后连续性及真实终止反馈；复用从 Replay 原样提取的 `verify_pair()` 核验任务、split、Actor 模型、backend、执行协议、版本、环境 game/manifest 哈希及初始观察与菜单。执行实现不同必须有覆盖双方源码哈希的既有显式核验记录，不能默许差异。两侧执行 Skill 必须等于冻结的实际 Parent/Candidate，Skill 身份哈希也需有效。

`success` 必须有实际环境获胜反馈；`environment_ended` 必须有正常终止且未获胜的反馈；`step_limit` 必须真实执行到预算且未成功。后两者计 false。`error/interrupted/unknown/running/starting`、缺失文件、无法核验的身份、技术错误标记均导致异常，不计为普通失败。冻结任务不能排除。

当前 `assemble_gate()` 适配已有 Replay 配对归档：读取 `input.json` 中原始轨迹路径和 Editor 来源，重新装配并比较已保存配对事实，再生成 Gate 输入。不依赖 Replay 模型输出是否成功，也不读取学习后的 Active Memory。通过 Editor 的现有读取器检查实际 Diff、Candidate 及上游来源，不进行 Skill 语义分析。

该档案适配入口保留原始训练批次来源约束。未来独立 Validation 批次可直接调用通用 `build_gate()`，传入冻结的 Skill 和任务清单；无需伪造训练来源或将 Validation 写入 Replay。

## 接口、保存与复用

- `decide_gate(payload, frozen_tasks)`：已核验输入的纯函数，仅计数。
- `build_gate(parent_records, candidate_records, frozen_tasks, *, parent_skill, candidate_skill, implementation_review=None)`：原始执行核验与标准化，返回 `input/audit`。
- `assemble_gate(replay_directory, tasks_file)`：现有真实配对档案入口。任务文件为独立 JSON 数组，或冻结实验 plan 的 `candidate_tasks`。
- `run_gate(replay_directory, tasks_file, output_directory)`：保存或复用。
- `load_gate(directory)`：重新核验来源、输入、规则和四字段结果，返回档案封装，其中 `result` 为正式 Gate 输出。

`gate.json` 一次原子写入 input、audit、冻结任务、来源文件路径及 SHA-256、规则、四字段结果和创建时间。原始轨迹不重复复制。相同来源与输入复用保存结果，不再次调用 `decide_gate()`；读取仍检查计数与规则一致性，这些校验不会被省略。来源、规则或结果冲突明确报错，不能覆盖旧有效结果。异常另存 `failure.json`，不产生第三种 Gate 决策。调用返回的 `reused` 是程序运行信息，不属于 Gate 四字段结果。当前接口为单调度者串行归档，未实现并发调度提交。

```bash
python -m src.skill_evolution.v23.gate \
  --replay-directory artifacts/methods/v23/v23_replay_memory_001/replay \
  --tasks-file experiments/methods/v23/v23_gate_001/config/tasks.json \
  --output-directory artifacts/methods/v23/v23_gate_001/live
```

## 与学习及未来调度的边界

Gate 不加入 Replay 七字段输入，不向 MemoryEntry 添加接受状态。Replay 更新后的 Active Memory 在 ACCEPT 或 RETAIN 下均可保留。未来调度在 ACCEPT 时选择 Candidate，在 RETAIN 时选择 Parent，独立使用 Replay 已提交的 Active Memory；本模块不实现这些状态更新。

后续已确认的[模块串联方案](EVOLUTION_ORCHESTRATION_DESIGN.md)调整了此前独立 Validation 的建议：每轮 Gate 与 Replay 使用同一批经过核验的 Train 配对，不设置独立 Validation；Test 保留用于最终独立评价，不进入演化。Gate 仅表示当前训练批次上的晋级判定，不能解释为独立验证收益。该调整不改变 Gate 计数规则，也不改写既有实验记录。未来若另行配置独立 Validation，其轨迹不得自动进入 Replay 或 Memory，仍不能替代最终 Test。

本次 [真实档案验证](../../../experiments/methods/v23/v23_gate_001/reports/REPORT.md) 使用既有四组 Train 对照，只验证工程功能与数据交接，不是独立 Validation 或 Skill 晋级收益实验。无新增模型请求、环境执行或正式 Parent 更新。
