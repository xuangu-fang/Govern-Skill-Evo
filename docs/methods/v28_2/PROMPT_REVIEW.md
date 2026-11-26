# v28.2 Prompt v2 审阅

2026-11-04。当前版本：Diagnosis `v28_2_searchqa_diagnosis_v2`、Preconditioner `v28_2_searchqa_preconditioner_v2`。只修订这两个 Prompt 的决策指导，其他模块、接口、预算和输入视图不变。正式训练和 Test 未启动。

本轮以已确认的 SearchQA 方案为依据，不逐字导入后续 v29.3。原设计审阅保存为 [v1 历史快照](revisions/prompt_v2/baseline/PROMPT_REVIEW.md)，其中按预期成败/去留划分 Update 的要求已撤销，不作为当前规范。

## 五组修订

| 修订 | Diagnosis | Preconditioner |
|---|---|---|
| Update 组织 | 按有证据支持的共同决策问题及修正方向组织；任务/Group 不决定边界，相同错误标签不自动合并；保留同一修正的必要配合 | 保持 Original IDs；不新增拆并职责，保留必要协调 |
| 有效增量 | 评估 Parent 的缺失、误导、冲突或难以落实；执行错误不证明指导有缺陷；允许删改、协调及 no_change，不虚构缺口 | 检查 Original 是否针对有依据的问题，不虚构遵循失败，不扫描无关修复 |
| 成功与反例 | 用问题/context 的相关差异细化动作、范围、优先级；单案例仍可支持合理试验，不强制配对验证 | 检查例外是否确实保护相关情形；可扩大/缩小/强化/放宽，不把“必须→优先”当作范围已合理 |
| 附带改变 | 编码、名称、单位、答案范围等变化需相关依据或实施/协调/保护上的必要性；在固定协议内尊重问题要求 | KEEP 覆盖整条；用完整 REPLACE 保留合理方向并修正无依据的附加要求，不为缩小修改而删去必要配合 |
| 证据含义 | 参考接受性不是形式偏好；当前 Candidate 不可见，不提前声称保持/改善 | 明确支持的成功保持只是有限任务级证据，不计作新增改善；缺少 Knowledge/关联不证明保持；`preferring` 改为 `accepting` |

## 保留的 SearchQA 边界

- 完整 question/context 可见；passage 存在不证明 Actor 使用了它，隐藏 reasoning 不可用。
- 区分实体/关系、答案边界和参考形式；局部边界修正不自动成为关系选择规则。
- 原生 EM/F1、冠词/标点归一化、F1=1 不必然 EM=1；不添加别名或评分规则。
- 当前 Diagnosis 为全批 Parent，Preconditioner 为 Plan 直接引用的完整当前 runs 与只读历史视图；没有当前 Candidate 或历史原始记录访问权。
- 历史轮次事件、Update 关联、Gate 决策相互区分；null/未关联不自动等于不相关、无效或保持成功。
- 不要求先证明因果效果，不要求每个覆盖情形有成功样本，不设 Update 数量、撤回比例或 Skill 长度上限。

## 跨模块与版本

Diagnosis 的实施条件进入 Update text，决定边界的成功例/反例进入 basis，reason 不传给 Preconditioner。Preconditioner REPLACE 输出全文，保留 goal、ID、basis 和必要配合；Editor 不接收调整 reason。未新增字段、模块、Knowledge 类别或 Gate 投票信号。

方法仍为 `v28_2_campaign_v1`；两个 Prompt 身份升至 v2，结构合同仍为 v1。当前配置只改变这两个 `method.prompts` 值；旧配置或旧 Prompt 文本不得在新版下恢复，不自动重标记旧响应。

## 验证与局限

本轮离线验收 **274 / 274 全部通过**：v28.2 118 项（含新增 4 项修订测试），SearchQA v28/v28.1 回归 156 项；失败、错误、跳过均为 0。另有 16 项原文/结构范围核对全部通过。网络/子进程访问触发 0，真实模型请求 0，新增正式 v28.2 实验目录 0。

[修订记录](revisions/prompt_v2/README.md) 汇总基线、差异、测试与复现命令；[静态范围核对](revisions/prompt_v2/scope_validation.json) 记录原文/结构比较；[本轮离线报告](revisions/prompt_v2/offline_acceptance.json) 记录实际运行结果。

新增测试检查实际 Prompt 分发、仅两个版本变化、旧配置/旧文本拒绝，以及同一修正的多执行依据和完整 REPLACE 文本能传入 Editor。手写响应只验证合同与传递，不证明模型会合理组织 Update、正确解释证据或提高成功率。不会用 Update 数量、长度、KEEP/Retain 比例作为语义优化成功的替代指标。
