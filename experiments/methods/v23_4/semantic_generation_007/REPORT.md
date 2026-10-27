# R05 Editor：章节位置与适用范围最小修订验证

2026-10-22（Asia/Shanghai）。

**完成指定 Prompt 修改和一次 Editor 生成。首次结构通过，1 次 HTTP、0 次重试。此次 u3 不再位于 non-desklamp 章节内，u1/u2 的行为要求也得到落实；本次定向文本审查通过。** 未重新执行 Diagnosis 或 Preconditioner，未运行 Actor/Replay，未写入 Memory。

## 唯一 Prompt 修改

在共享 `src/skill_evolution/v23/editor_prompt.md` 原第 40 行 Scope 保留要求之后，逐字加入用户指定文本：

> A rule's scope depends on both its wording and its placement within the Skill, including section headings and nesting. Preserve each Effective Update's intended scope by choosing an appropriate location or making minimal structural adjustments when necessary.

本轮仅修改这一处生产文件；没有改变 JSON 契约、Editor 算法或添加审核调用。该文件也是 V23.4 Editor 使用的共享 Prompt，因此并非仅对 R05 注入的特例。

修改前先验证 study 006 全部冻结来源，并保存 [旧 Prompt](baseline_sources/src/skill_evolution/v23/editor_prompt.md)。新冻结要求源码差异严格等于上述插入；旧实验及其冻结记录未覆盖。

## 输入与调用

- Parent 与 Effective Plan 原样复用 study 006；重解析其选中 Preconditioner 响应并重新运行确定性校验/编译，无新模型调用。
- Editor material 与旧轮完全相等，user message 字符串完全相等。只有 system message 增加指定文字，没有加入人工审查内容或期望输出。
- 同一模型、路由、采样和输出预算。一个 Editor 逻辑阶段，沿用最多三次技术重启授权，实际没有触发。
- 输入 14,382 字符；API 报告 **2,884 prompt tokens + 6,410 completion tokens = 9,294 tokens**。耗时 32.870 秒，费用未知。
- 独立实验适配器调用现有生产函数；不声称验证了生产持久化加载器的完整链路。

## 逐 Update 核对

| Update | 新 Candidate 的实现 | 结论 |
|---|---|---|
| u3：合法动作与直接动作回退 | 第 22 行新增 `## Admissible Actions`，第 24–25 行逐字保留完整 Effective u3；第 27 行才开始 `## General Non-Desklamp…`，第 29 行的非 desklamp 引导语只在该后一章节内 | 旧问题未再出现：u3 是无任务类型限定的独立同级章节，不再受 non-desklamp 章节的局部引导语限制 |
| u1：精确对象、禁止替代 | 第 32 行保留 acquire/clean/cool/heat/place 全部行为；未见精确对象时不操纵相关类别替代物；离开仅有不匹配对象的容器并继续寻找；不将替代物处理视为进展 | 三项要求均落实；原有 soapbottle/dishsponge 示例保留，没有新增未经授权的对象规则 |
| u2：搜索扩展与近期防循环 | 第 31 行保留开放表面、选择未检查候选、优先未尝试类型、按当前/近期观察避免回查、离开已见无目标的容器、不重复短循环 | 基本忠实：没有恢复“必须不同类型”的硬要求，也没有加入旧结果的“两次”阈值；未凭章节位置改写搜索范围 |

u2 的“目标尚未找到”条件在搜索步骤起首 `If it is not visible` 及末尾 `Continue until the exact target is found` 的上下文中保留。句子顺序虽有调整，未发现新增先决动作或独立的强制顺序。

原 Parent 的“所有 plausible candidates 检查一次”完成边界、打开已到达的关闭容器、避免空手 inventory 检查仍被保留。这些是原有行为，不是本轮 Editor 额外制定的策略。

原 desklamp procedure/constraints 的文本完全未变；清洗和直接放置步骤及末尾保留条款也完全未变。新增通用 u3 位于 desklamp constraints 之后、非 desklamp procedure 之前，没有修改同处、开灯或完成行为。

## 验证结果与限制

- 相关离线测试 **144 passed**：V23 Editor、Prompt alignment、V23.4 Editor directional review。
- 归档审计确认仅一个模型阶段、一次请求、首次合法选中；原始响应与 parsed/result 一致。
- Editor 作者 Patch 严格应用成功；规范化实际 Diff 独立应用 Parent 后完全重建 Candidate。
- 程序核对 u3 两行与 Effective Update 逐字相等，位于独立同级章节；前面的原 desklamp 文本和后面的清洗/放置尾部未变。
- 完整 Skill 的语义判断仍由人工审查完成；文本位置检查不能证明 Actor 一定正确执行。原文件总标题仍为 `Desklamp-Conditioned Inspection`，沿用其包含多个同级用途章节的既有组织。本次确认的是 u3 已解除 non-desklamp 的局部章节限制，不宣称所有模型对整份文档的解释都得到保证。
- 一次生成成功说明这次输出满足定向要求，不证明新增 Prompt 文字稳定消除了此类错误。study 006 Preconditioner 理由中的事实/归因问题仍保留，不因 Editor 修正而被改标通过。

## 产物

- [原始 Editor 输出](runs/R05_editor/attempt_001/parsed.json)
- [冻结 Effective Plan](handoff/effective_plan.json)
- [Candidate](handoff/candidate.md)
- [实际 Skill Diff](handoff/actual.diff)
- [调用审计](AUDIT.json) / [交接核对](HANDOFF_AUDIT.json)
- [输入冻结](config/freeze.json) / [结果快照冻结](handoff/freeze.json)

离线复核命令（不调用模型）：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/tau2/bin/python -m experiments.methods.v23_4.semantic_generation_007.run audit
```
