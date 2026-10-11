# v21 Fusion 的提案依据

日期：2026-10-10。对应真实模型局部对照后的优化第 3 步，接续[Evidence Review 证据比较](V21_EVIDENCE_COMPARISON.md)。

原实验两组 Fusion 分别提出 10、11 个 PROPOSE，没有在 Fusion 阶段主动 NO_EDIT。其中部分方向已描述当前行为符合已有条款，却仍主要以失败原因不明、希望再查历史为由送审。本步收紧提案依据，不以减少提案数量或提高 VERIFIED 比例作为唯一目标。

## 实现

只修改 `memory_consumption_v21.build_issue_fusion_request` 的 v21 专属提示，版本由 `issue-fusion-v21.3` 升为 `issue-fusion-v21.4`。在原有 `issue_statement`、`reason` 和引用字段中要求：

- **PROPOSE 要有具体依据。** 当前 Findings 或历史认识应支持一个与当前 Parent 有关的可能行为缺陷，以及供 Review 核查的有限修订方向。说明来源、适用条件、当前条款覆盖，及成功与合规证据中的支持、反例和未知如何约束方向。
- **已有规则要说明剩余缺口。** 不能因为任务失败重复添加已有规则，也不能因为已有文字就断言执行正确。应指出材料支持的行为偏差、条件遗漏或歧义；缺少指导时可说明遗漏，不编造规则目标。
- **复查愿望不等于修改依据。** 若只有问题重现、不明结果标签、想多看历史或复述已有指导，没有具体受支持的剩余缺陷，应 NO_EDIT 并说明限制。原因尚未证明不自动排除提案；有依据的条件性假设可说明什么比较会支持或反驳它，由 Review 检查。
- **不丢问题、不强求修改。** 每个 OBSERVED_PROBLEM 仍必须归入且只归入一个 issue，包括 NO_EDIT。不得用 unassociated_findings 隐藏问题。NO_EDIT 只是本轮不改，不删除 Memory 或宣称问题已解决。

历史独立提案继续允许，前提是具体历史问题仍与当前条款相关。未解析的 edit binding 不代表旧行为已经不存在。Fusion 仍只读取精简 Findings、认识和当前规则，不能声称重读过原始事件；证据复核与修改授权继续由 Review 完成。提示不包含行李、拆单或保障案例的预期答案，不要求预先写出最终 Skill 或证明修改因果。

不增加 schema 字段、规则式语义拦截、状态分类、Agent、额外 Review 或逐 edit 分析。Memory 更新及 2,000 字符限制不变，Review 保持 v21.5，v20 默认提示不变。

## 固定输入预检

复用原实验 control/treatment 的 Fusion 输入，在历史目录外生成 `artifacts/v21_fusion_proposal_basis/prompt-preflight.json`。新旧 user payload、input_ref、引用映射和响应 schema 完全相同；系统提示只增加提案依据要求。原始输入和实验结果未改写。

| 原实验输入 | 当前 Findings / Memory issues | 原代理 token | 新代理 token |
|---|---:|---:|---:|
| control | 39 / 6 | 13,240 | 13,626 |
| treatment | 39 / 8 | 13,363 | 13,749 |

每次增加 386 个 `cl100k_base` 代理 token，不是网关实际计费量。另用固定行李 Review 输入确认其完整请求与本步开始前一致，避免共享提示意外改变 Review。

## 验收与边界

新增受控测试从真实消费入口注入 Fusion 的 NO_EDIT 响应，检查问题引用和理由保留、引用别名正确还原、不触发 Review/Editor、不生成候选、不修改 Memory，以及 generation audit 可复验。构造响应只验证通路，不证明模型会合理拒绝提案。相关 v21/v20/Replay 回归共 **212 项通过**（60.76 秒），`git diff --check` 通过。既有测试继续检查 PROPOSE → Review → Editor、纯历史/纯当前提案、来源绑定及已知反例。

后续按既定第 4 步做分阶段真实模型复验：固定 Fusion 输入只换其提示，检查是否把泛泛复查改为有依据的方向或具体 NO_EDIT；已有条款覆盖时是否回应剩余行为问题；是否合理使用双维历史而未泛化单例。无需机械要求三例变成 NO_EDIT，也不要求提案数量下降。Review 提示的效果应继续在固定 Review 输入上单独比较，不能将 Fusion 改选证据后的结果视为纯 Review 提示对照。

本步没有真实模型调用、Replay 或活动 Skill/Memory 发布；是否改善真实提案质量和成本仍待验证。
