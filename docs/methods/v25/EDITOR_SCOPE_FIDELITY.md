# Editor 条件与强度保留：最小澄清

2026-10-27，Editor Prompt 升级为 `v25_editor_scope_fidelity_v2`。
只在既有“保留策略、条件、范围、强度”等要求后增加一句：

> Do not turn an illustrative observation or conditional option into a default or mandatory rule unless the Effective Plan explicitly requires that change.

不重写 Prompt，不增加逐条审查流程、输出字段、语义检查器或模型调用。
Editor 继续忠实实现 Effective Plan，不接管 Diagnosis 或 Preconditioner 的策略判断。
新增句之外的正文、输出契约及输入均保持原样。旧 `v25_editor_v1` 模板单独保留，
旧归档重载使用原版本；不修改已有 campaign 的冻结条件或结果。

## 固定案例

材料位于 `tests/skill_evolution/v25/fixtures/editor_scope/`。

- **R05 反例**：原始 `_007` R05 Editor 输入中的 u3 提及某个已观察数值查询
  返回 0；原输出将其写成数值答案列无匹配时默认填 0。检查条件和建议强度是否保留，
  不据此断言其他 Editor 输出普遍有问题。
- **正例**：复制同一输入，仅将对应条款明确改为数值无匹配默认填 0，并同步相关
  Check，保留任务要求或列语义需要空白时的例外。这是人工构造的对照，不是真实
  训练结果；Editor 应落实这个明确默认规则，不能一律弱化成可选建议。

原始 input、messages、Editor 输出和 background 按字节复制，并记录源路径和
SHA-256。正例输入和条件保留版参考输出均单独标明为人工构造。
`cases.json` 的判据及参考输出只供评估者，不进入模型输入。

离线测试检查快照哈希、案例定位、输入差异、预设补丁的精确应用和归档重载。
原来的问题输出仍能通过结构校验；本次没有偷偷新增语义拒绝规则。
这些测试不证明新 Prompt 能使模型正确处理案例，语义效果标记为 `not_run`。
未来若单独获准重放，反例使用完整原始用户消息，只替换 Editor 正文；正例使用
单独的 positive_input，同样保持执行上下文。不得注入判据或参考输出。

## 版本与配置

后续 8 批 × 15 题模板同步新 Editor 版本。Diagnosis、Preconditioner、Replay、
Verifier、Repair、Actor、Gate 及其参数均不因本次修复改变。
本次不调用模型，不启动训练，也不重置任何已归档预算。

## 本次离线结果

V25 离线测试 208 项通过（未运行 `test_executor.py` 的 Docker 执行器专项测试）。
已核对正文恰好增加上述一句、文档镜像一致、后续配置版本一致、R05 快照与原归档
哈希一致，并只读重载 `_007` R05 的旧 Editor 完整归档链。未调用模型或启动训练，
案例的模型语义效果仍为 `not_run`。
