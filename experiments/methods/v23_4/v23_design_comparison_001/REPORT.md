# V23.4 对照 V23：设计差异与首个对照切口

日期：2026-10-22。范围：源码、设计文档与已归档产物的离线比较；本研究尚未调用新 Preconditioner、Editor 或 Actor。基准明确为 **V23**，不是 V23.3。

## 核心判断

V23 已经具有 Diagnosis → Preconditioner ← Memory → Effective Plan → Editor → 配对执行 → Replay/Memory 的流程，并在设计中明确方向、尺度和关联调整。它也允许扩大、加强、探索及撤回，并非只做保守过滤。因此，V23.4 的研究问题应是：**把原有历史响应驱动的更新判断显式化、约束其落实，是否改善了决策和实际行为？** 不能将有无 Memory、有无 Preconditioner 或首次引入 D/S/C 当成本次版本差别。

## 设计与实现的具体差别

| 维度 | V23 | V23.4 | 需要验证的价值与代价 |
|---|---|---|---|
| 历史如何参与判断 | 比较历史编辑、条件、行为响应，输出有依据的必要调整 | 明确先判断方向、范围/强度与协调关系，再形成 change 和 Patch；不是生成修改后贴标签 | 证据是否真正改变决定，而不只是理由更长；单次输出不能证明模型内部顺序 |
| D/S/C 表达 | 设计为 Direction / Scale / Coupling；不输出独立维度字段 | Direction / Scope / Coordination，由 focus/change/reason 联合表达；S 仍涵盖强度，C 仍涵盖依赖/冲突 | 名称变化本身不是新算法；具体决策与保留边界是否更清楚 |
| Keep | 不生成 Adjustment，整体 reason 可解释保留 | 每项 Original Update 必须显式 Keep，并在相关理由中回应重要反例 | 减少无声忽略历史；不能按“改得更多”评价优劣 |
| 修改实现 | to 输出完整替换文本；支持一对一、合并、拆分和撤回 | 对冻结 Original 文本严格应用 Unified Diff，保留原 ID；每项一次综合调整，取消结构拆合 | 是否减少无意漂移；也可能增加 EOF、hunk 等技术失败和表达约束 |
| 意图与落地 | 调整后的完整要求和 reason | change 规定所有实质动作、前提、顺序与保留边界，Patch 双向对应 | 是可核查的语义承诺，不是程序已经证明一致；仍可能产生未声明行为 |
| 决策状态 | 模型输出 ready/no_change/need_evidence 及总 reason | 程序由合法存活 Updates 推导是否交给 Editor；错误明确失败 | 少一个自由决策层，但不再有成功弃权输出；失败不能伪装 Keep |
| 依据与来源 | 模型输出 Adjustment basis；有效 Update 继承当前 basis | reason 中显式引用；程序派生兼容对象，复用旧编译器；保留原始 v2 记录 | 引用存在不等于事实正确、历史可迁移或因果成立 |
| Diagnosis | 自足的行为要求及当前事实依据 | 增加连贯行为粒度、重要正反边界引用、多行表示，Goal 避免绑定未验证策略 | 可能影响初稿质量与下游可见执行，不能混入 Preconditioner 单独贡献 |
| Replay / Memory | 实际 Diff 与配对响应，修订条件化认识 | 强调实际行为变化、未触发/未遵守/遵守未改善，具体正负响应及步骤依据 | 存储 Schema 未变，语义仍有错误；本轮 R05/R06 已留下反例 |
| Memory 模型视图 | entries/sources，步骤引用展开完整来源执行 | 默认沿用已有 v3 压缩视图，也支持完整 entries/sources | 压缩来自既有版本，不是 V23.4 独有创新；比较时必须控制 |
| Editor | 接收 Parent 与 Effective Plan，生成实际 Skill Patch | 复用相同 Editor；近期共享 Prompt 强化了忠实性和章节位置/范围 | 不能把 Editor Prompt 修正的收益单独算给 D/S/C；历史模板与当前模板需分清 |

共同不变的边界：Goal 冻结、当前事实/历史事实区分、非强制修改、允许发展与探索、有效 Update 当前 basis 继承、实际 Diff 进入 Replay、Memory 不直接成为 Actor 指令。V23.4 没有新增审核 Agent、检索器或第二次独立 Transformation 生成。

## 已有 R05 产物能回答什么

[inventory.json](inventory.json) 保存代码/资料 SHA256、历史模板核对与字段比较。

- 历史 V23 S1/R05 的 Preconditioner 模板与当前 V23 模板注入相同执行背景后完全一致；该历史输出对两项 Original Update 全部 Keep。
- 当前 V23.4 R05 使用重新生成并已冻结的三项 Original Update：u1/u3 Keep，u2 做 S 调整，弱化必须先换不同类别的硬顺序，并限制防循环判断所依赖的观察范围。
- 两份输入的 Parent 和原始 Memory 相同，**Original Plan、选入的 runs、command_sets 和过滤后的 grouping 不同**。历史 V23 选 P6/P7/P8/P9/P10，当前 V23.4 选 P1/P3/P6/P7/P8/P10。历史结果与本轮结果不能构成受控方法比较。
- 本轮两组 Actor 都是 8/10，共同成功任务 52 → 49 步；它比较的是 Parent 与本次 Candidate，并没有执行一个输入相同的 V23 Candidate。
- R06 的修复同样只支持该 Candidate 在本批中的表现，不证明 V23 做不到，也不能直接归为 V23.4 相对 V23 的收益。

## 建议先做一个固定输入的 Preconditioner 对照

先回答“同一份更新，V23 与 V23.4 会如何利用同一历史做决定”，再付出 Actor 成本。

1. 从 R05 开始，使用 `semantic_generation_006/config/cases/R05.json` 的同一 Parent、Original Plan、当前事实、Grouping 和原 Memory。明确这份 Plan 是共享实验刺激，不声称由 V23 原始 Diagnosis 生成。第二个案例可选择 R06 当前已审查 Plan，以相同方式冻结。
2. 两侧固定模型、推理/输出预算、技术重试上限、执行背景和输入视图。首选两侧均用完整 entries/sources：V23 原生支持，V23.4 也支持。这样不会将 v3 压缩差别混入 PC 比较。若采用共同 v3 视图，必须标为统一输入适配的 V23，不能冒充未经适配的原始端到端方法。
3. 仅各调用一次逻辑 Preconditioner，使用各自原生输出契约和校验器；保留所有技术失败，选择首个合法输出。V23 合法 need_evidence 单独报告，不强制变成 Keep。两侧不要求同格式、同修改数量或同 focus 标签。
4. 并列阅读 Original → 决定/理由 → Effective Update，检查历史事实是否正确、是否与当前条件可比、重要反例如何处理、必要行为是否保留、探索是否被错误称为已验证，以及 V23.4 change/Patch 是否一致。V23 没有 focus/change 字段，按其实际要求和理由评价同类行为决定。
5. 若出现有实质意义的 Effective Plan 差异，再用**同一冻结 Editor Prompt**各生成 Candidate，核对实际 Diff。之后再比较 Parent / V23 Candidate / V23.4 Candidate 的同任务执行。相同文本的 Skill 不因来源不同而重复执行来制造差别；不同文本仍按预定策略运行，不能只挑看起来好的输出。

这验证的是 **V23 与 V23.4 的 Preconditioner 设计包**（决策规范、输出协议及其落实方式）。它不能单独区分更详尽 Prompt、显式 Keep、D/S/C 决策规则和严格 Patch 各自的贡献。已有当前 V23.4 结果采用 v3 视图；若选择完整视图的对照，两侧须按新冻结条件运行，不能静默复用旧侧。

## 暂不扩大的部分

完整版本比较涉及 Diagnosis、Memory 视图、Editor 模板、Replay 维护和跨轮积累，回答的是另一层问题。先不把这些变量同时放开，也不立即进行全套消融。

后续同结构有/无 Memory 能检验历史信息的边际价值，但不是 V23 基线本身；Diagnosis → Editor 是“未经预条件化的 Original”辅助臂，也不等于 V23。当前 R05/R06 Replay 候选仅在隔离副本中保存，不进入此对照的共享 Memory。

待首个固定输入对照完成后，再决定是否值得扩大到真实执行、多次采样和跨轮演化；不从 Prompt 更明确直接推出 Skill 持续改善。

## 主要依据

- [V23 Preconditioner 设计](../../../../docs/methods/v23/PRECONDITIONER_DESIGN.md)
- [V23 Prompt](../../../../src/skill_evolution/v23/preconditioner_prompt.md)
- [V23.4 决策规则](../../../../docs/methods/v23_4/DSC_DECISION_RULES.md)
- [V23.4 Prompt](../../../../src/skill_evolution/v23_4/preconditioner_prompt.md)
- [R05 原始与有效更新审查](../semantic_generation_006/SEMANTIC_REVIEW.md)
- [R05 当前实际执行](../r05_actor_comparison_001/REPORT.md)
- [本轮 Replay / Memory](../r05_replay_memory_001/REPORT.md)
