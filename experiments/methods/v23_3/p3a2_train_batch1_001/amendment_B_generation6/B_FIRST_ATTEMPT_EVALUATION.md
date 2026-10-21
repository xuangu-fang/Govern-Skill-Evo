# B 首次输出独立评价（未通过契约）

真实输出为 ready，u1 Keep，u2 提供三行替换的 Unified Diff，并改写根级 Checks。但 Adjustment 内另出现 `checks:null`，原 normalize_update_patches 在字段检查阶段报 `Adjustment: unexpected fields`。未删除字段或修补后继续编译；没有该次输出的有效 Effective Plan。存在真实 Patch 文本不等于成功应用 Patch。

模型明确理由：旧 u2 的 whole-run empty、second pass、run-of-steps 触发依赖全局状态，而 Actor 只有当前观察、候选、步数和最近两对历史；M3/M6 的 anti-cycle/step-priority 响应混合且未稳定破循环。模型声称改为可见局部触发，且把过半预算触发新类别标为未验证假设，不声称收益已证实。

可支持的部分：当前循环和历史未可靠执行提供收窄全局触发的动机；用最近两对信息避免立即往返可执行性更明确。新半预算规则具体可检验，不能因为未有历史成功就自动判错，但历史不证明该阈值最优或可靠。

未解决的问题：

- u1 Keep 仍保留所有 reachable 候选首次覆盖、所需目标数及“open it”泛化，不因 u2 局部化而自动变得可执行。
- u2 第一行要求从 current observation 的其他 receptacles 选择，具体反馈可能只描述当前位置；菜单与当前观察应区分，存在可选范围过窄风险。
- 第二行仍含“where possible, a receptacle type you have not yet inspected”，没有完整全局账本，不能宣称所有全局条件都已消除。
- 半预算是新探索而非历史证明；对晚发现目标/多实例交付的实际效果未知。
- 根级 c2 删除了 Original 的多实例数量明确检查，可能削弱评价覆盖；Goal/u1 中的数量要求并未随之消失。

B 所称“sole success in the batch (P1)”需按实际 Preconditioner 当前证据选择解读：它仅看到 P1/P3/P6，确实只有 P1 成功；不能转述为整个六任务 Parent 仅一条成功。

当前只能评价原始提案，不能把这些变化归为已实施 Skill 或行为收益。第一次契约失败继续保留，即使用户授权第二次生成恢复成功也不得隐去。
