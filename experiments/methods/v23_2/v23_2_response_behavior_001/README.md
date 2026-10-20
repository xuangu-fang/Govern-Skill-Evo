# R06 固定 Update 的局部 Candidate 行为验证

仅使用 `v23_2_response_alignment_001` 已保存 R06 Effective Plan；原 R06 Parent（R05 保留 Skill）经原 V23 Editor 生成新 Candidate，再使用原 Episode 调度执行 `val:0011`–`val:0017`。Parent 与原 V23 Candidate 的 14 条历史轨迹只读复用。该 val 子集属于正式 57 条优化池，不是最终 134 条 Test。

入口 [run.py](run.py) 只增加局部编排。通过临时替换 Editor 的归档读取依赖，调用既有 V23.2 严格重读器；原 `editor_input`、Prompt、模型调用、JSON 验证与严格 Unified Diff 应用全部保持原样。没有调用 Diagnosis、Preconditioner 或 Replay 模型。技术重试直接复用 `_model_stage`，任务执行直接复用 `_actors` 和 `actor_task`，不调用 Gate 或发布 Parent。

冻结配置见 [plan.json](config/plan.json)，[Effective Plan](config/effective_plan.json) 不做人工修改；原始材料及当前源码在运行前进行哈希与正式冻结核对。唯一已有源码差异为正式 Test 恢复时已授权的 `ChunkedEncodingError` 一行重试修复，沿用现行设置，不新增修复。Actor seed=42、50 步、最近两组历史、最多 8 个任务并行，每步最多三次技术尝试。

执行分为 `prepare`、`editor`、`episodes` 三个阶段。Editor 最多一次逻辑调用、三次技术请求；只有合法非空 Candidate 才执行七条任务。已有产物时拒绝重新启动，出现技术停点须另行明确恢复，不能以重跑入口增加预算。合法语义不理想不重采样，不修改 Patch。

已完成：离线 173 项测试通过；Editor 一次逻辑调用、一次长度截断技术重试后产生 Candidate；七条 Episode 全部完成、无 Actor 技术重试。新 Candidate 5/7、162 步，原 Candidate 5/7、202 步，Parent 6/7、178 步。plate 搜索与两条加热操作有局部改善，apple/book 仍失败，搜索未稳定改善。保留待验证候选，不提升为默认，已停止。

见[完整报告](reports/REPORT.md)、[实际 Diff](reports/actual.diff)、[三组逐步轨迹](reports/TRAJECTORIES.md)。本次不进行正式六轮实验，不写 Memory，不修改当前默认 Prompt。局部随机执行与旧轨迹比较不能证明 Prompt 或单条规则的独立因果收益。
