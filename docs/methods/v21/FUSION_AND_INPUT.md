# 融合依据与输入优化

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [v21 Fusion 的提案依据](#v21-fusion-proposal-basis)
- [v21 输入优化：短引用与无损内容复用](#v21-input-optimization)

<a id="v21-fusion-proposal-basis"></a>

## v21 Fusion 的提案依据

日期：2026-10-10。对应真实模型局部对照后的优化第 3 步，接续[Evidence Review 证据比较](EVIDENCE.md#v21-evidence-comparison)。

原实验两组 Fusion 分别提出 10、11 个 PROPOSE，没有在 Fusion 阶段主动 NO_EDIT。其中部分方向已描述当前行为符合已有条款，却仍主要以失败原因不明、希望再查历史为由送审。本步收紧提案依据，不以减少提案数量或提高 VERIFIED 比例作为唯一目标。

### 实现

只修改 `memory_consumption_v21.build_issue_fusion_request` 的 v21 专属提示，版本由 `issue-fusion-v21.3` 升为 `issue-fusion-v21.4`。在原有 `issue_statement`、`reason` 和引用字段中要求：

- **PROPOSE 要有具体依据。** 当前 Findings 或历史认识应支持一个与当前 Parent 有关的可能行为缺陷，以及供 Review 核查的有限修订方向。说明来源、适用条件、当前条款覆盖，及成功与合规证据中的支持、反例和未知如何约束方向。
- **已有规则要说明剩余缺口。** 不能因为任务失败重复添加已有规则，也不能因为已有文字就断言执行正确。应指出材料支持的行为偏差、条件遗漏或歧义；缺少指导时可说明遗漏，不编造规则目标。
- **复查愿望不等于修改依据。** 若只有问题重现、不明结果标签、想多看历史或复述已有指导，没有具体受支持的剩余缺陷，应 NO_EDIT 并说明限制。原因尚未证明不自动排除提案；有依据的条件性假设可说明什么比较会支持或反驳它，由 Review 检查。
- **不丢问题、不强求修改。** 每个 OBSERVED_PROBLEM 仍必须归入且只归入一个 issue，包括 NO_EDIT。不得用 unassociated_findings 隐藏问题。NO_EDIT 只是本轮不改，不删除 Memory 或宣称问题已解决。

历史独立提案继续允许，前提是具体历史问题仍与当前条款相关。未解析的 edit binding 不代表旧行为已经不存在。Fusion 仍只读取精简 Findings、认识和当前规则，不能声称重读过原始事件；证据复核与修改授权继续由 Review 完成。提示不包含行李、拆单或保障案例的预期答案，不要求预先写出最终 Skill 或证明修改因果。

不增加 schema 字段、规则式语义拦截、状态分类、Agent、额外 Review 或逐 edit 分析。Memory 更新及 2,000 字符限制不变，Review 保持 v21.5，v20 默认提示不变。

### 固定输入预检

复用原实验 control/treatment 的 Fusion 输入，在历史目录外生成 `artifacts/methods/v21/v21_fusion_proposal_basis/prompt-preflight.json`。新旧 user payload、input_ref、引用映射和响应 schema 完全相同；系统提示只增加提案依据要求。原始输入和实验结果未改写。

| 原实验输入 | 当前 Findings / Memory issues | 原代理 token | 新代理 token |
|---|---:|---:|---:|
| control | 39 / 6 | 13,240 | 13,626 |
| treatment | 39 / 8 | 13,363 | 13,749 |

每次增加 386 个 `cl100k_base` 代理 token，不是网关实际计费量。另用固定行李 Review 输入确认其完整请求与本步开始前一致，避免共享提示意外改变 Review。

### 验收与边界

新增受控测试从真实消费入口注入 Fusion 的 NO_EDIT 响应，检查问题引用和理由保留、引用别名正确还原、不触发 Review/Editor、不生成候选、不修改 Memory，以及 generation audit 可复验。构造响应只验证通路，不证明模型会合理拒绝提案。相关 v21/v20/Replay 回归共 **212 项通过**（60.76 秒），`git diff --check` 通过。既有测试继续检查 PROPOSE → Review → Editor、纯历史/纯当前提案、来源绑定及已知反例。

后续按既定第 4 步做分阶段真实模型复验：固定 Fusion 输入只换其提示，检查是否把泛泛复查改为有依据的方向或具体 NO_EDIT；已有条款覆盖时是否回应剩余行为问题；是否合理使用双维历史而未泛化单例。无需机械要求三例变成 NO_EDIT，也不要求提案数量下降。Review 提示的效果应继续在固定 Review 输入上单独比较，不能将 Fusion 改选证据后的结果视为纯 Review 提示对照。

本步没有真实模型调用、Replay 或活动 Skill/Memory 发布；是否改善真实提案质量和成本仍待验证。

<a id="v21-input-optimization"></a>

## v21 输入优化：短引用与无损内容复用

日期：2026-10-09。状态：已接入 Memory 更新和 Evidence Review，完成同批证据预检及 157 项相关回归。没有调用真实模型、重新 rollout 或发布活动 head。

后续[新增退化覆盖](REGRESSION.md#v21-regression-coverage)已扩大 Memory 默认输入：9 组配对、675 个事件、99,405 个代理 token。本文表格保留原 6 组配对范围的同输入优化结果；当前扩大覆盖后的数字不能作为同范围压缩比较。

再加入 [issue 边界](MEMORY.md#v21-issue-boundaries)后，当前 Memory 输入为 99,761 个代理 token，原始证据数量不变；Memory/Fusion/Review Prompt 为 v21.4/v21.2/v21.3。

后续 [当前认识与历史消费](MEMORY.md#v21-current-understanding)已接通：当前预检默认保存为 `artifacts/methods/v21/v21_current_understanding/report.json`。旧真实产物缺少新综合认识，仍完整读取，不能声称这组预检已实现摘要压缩；当前 Memory/Fusion/Review Prompt 为 v21.5/v21.3/v21.4。

### 1. 优化结果

下表沿用第 3/4 步预检的相同证据和选择范围。统计口径为 cl100k_base 代理输入 token，包含提示与响应 schema，不是网关实测用量，也不含输出预留。不同阶段使用的 fixture 不构成同一轮实际运行，不能相加声称 campaign 成本。

| 阶段 | 优化前 | 优化后 | 变化 |
|---|---:|---:|---|
| Memory 更新：3 个历史问题、6 组配对、539 个事件 | 238,240 | **84,051** | 减少 **64.7%** |
| Fusion：简明 Memory、当前 Findings、Parent 规则 | 13,020 | **13,020** | 保持不变，继续使用已有短引用 |
| 历史 Review 1：240 个事件 | 79,475 | **46,875** | 减少 41.0% |
| 历史 Review 2：63 个事件 | 40,704 | **22,431** | 减少 44.9% |
| 历史 Review 3：272 个事件 | 107,958 | **61,025** | 减少 43.5% |
| 历史 Review 4：68 个事件 | 38,899 | **20,625** | 减少 47.0% |
| 历史 Review 5：266 个事件 | 105,317 | **55,370** | 减少 47.4% |
| 历史 Review 6：96 个事件 | 47,378 | **28,351** | 减少 40.2% |
| 合并当前 Findings 的离线构造示例：735 个事件 | 259,416 | **140,454** | 减少 45.9%；仍不作为正式提案组织方式 |

六个历史 Review 合计由 419,731 降到 234,677，减少约 44.1%。这只是这六个构造请求的代理 token 合计，不是经过 v21 语义更新后的真实多轮成本。

测量报告：[report.json](../../../artifacts/methods/v21/v21_input_optimization/report.json)。此前 step-3/4 预检报告保留为优化前基线；本目录中的早期 `check.json`、`final.json` 是中间测量，以 `report.json` 为本次最终结果。

### 2. 改动集中在模型输入表示

新增 [evidence_wire_v21.py](../../../src/skill_evolution/v21/evidence_wire_v21.py)，在送入模型前执行确定性转换：

1. **缩短结构化引用。** 事件、轨迹、来源、问题/尝试、编辑目标和版本标识使用请求内的短引用。原始 ID 的完整反向映射保存在本地请求审计中，不放进模型消息；响应引用先还原，再由原来的身份、类型和编辑权限校验处理。
2. **复用相同正文与数据。** 沿用 v19 的事件正文/长文本复用，并对完全相同、重复出现的较长 JSON 数据建立共享正文。工具返回、参数和公共工具定义保持原样，只复用逐字一致的内容；不生成摘要，也不作语义合并。
3. **去掉重复事件包装。** 事件目录的键已是事件引用，不再在同一条记录中再次重复该引用及多余包装。每个事件仍关联自己的轨迹、顺序和精确正文；正文相同不代表两次运行是同一次观察。

公共材料中每行重复的 policy digest、规则的 Parent digest 等也使用短引用。版本相等关系保留，不能从短编号推断版本优劣或先后。

自然语言、policy 正文、工具参数和工具返回中的字符串不按 ID 做全局替换。例如工具数据恰好包含 `source_refs`、`ref` 等属性名，或正文出现与某个事件 ID 相同的文本，也不将它们当作证据结构改写。短编号避开输入中已经存在的字面值。共享正文的指针不是可引用的原始事件。

### 3. 此次保留证据范围的原因

本次没有裁切事件、截断工具返回、删除另一维反证，或减少问题尝试目录。所有预检包都满足：

```text
expand(模型输入, 本地引用映射) == 原始规范证据包
```

检查覆盖事件正文、两个结果标签、版本/轮次、配对、来源记录、反证、policy/tools 和当前 Parent 编辑目标。规范档案及其内容引用不因这次优化改变。

检查发现，除原始内容外，长引用、重复哈希及数据包装占用了大量输入。消除这些冗余已显著减小请求，因此本次先采用无损优化，不为了达到预设 token 数而引入尚未验证的轨迹裁切策略，也没有增加证据筛选 Agent、分批语义调用或第二遍 Review。

**这不表示 84k 更新或 61k Review 已经是理想规模。** 实际旧来源仍按既有关系展开，跨轮持续增长的问题没有被宣称解决。后续应先用真实 Pilot 检查短引用/共享正文的可读性、推理质量与调用成本。如果剩余原始内容确实成为瓶颈，再围绕当前判断设计必要事件片段，并单独验证前置条件、行为顺序、配对两侧和已知反证不会丢失。合并全部当前 Findings 的大包继续只用于离线装配测试。

### 4. 接口、恢复与兼容

- 此次优化将 `build_memory_update_request` 升为 `memory_update_v21.2`；后续退化覆盖已升为 `memory_update_v21.3`。`run_memory_update` 自动还原模型返回的短引用；直接校验短引用响应时使用 `validate_memory_update(raw, request=..., wire=True)`。离线的完整原始引用响应保持兼容。
- v21 Evidence Review Prompt 升为 `evidence-review-v21.2`，通过输入对象的 `normalize_response` 在现有校验前还原引用；Compiler/Editor 接收的仍是原始引用。
- v20 的默认 `normalize_response` 原样返回响应，v20 Prompt、运行路径和默认行为不变。
- `reference_map` 属于本地请求元数据。现有 transport 仅发送 system/user 消息和响应 schema，不发送反向映射。请求、模型原始响应和规范化结果均保留在原有审计位置。
- 已有规范 Memory、证据档案和生成来源不需要迁移。旧 Prompt 的未完成调用检查点不能假装以新 Prompt 恢复；请求一致性检查会拒绝，应使用新的独立目录。相同新版请求的显式恢复复用已完成响应，不重复调用。
- 仍在转换后执行预算检查。超预算就停止，不自动删掉反证或截断材料后发送。

### 5. 可复现验证

在仓库根目录运行，只读取既有预检与历史产物，不创建模型或 benchmark 调用：

```bash
/Users/didi/miniforge3/envs/tau2/bin/python scripts/runs/v21/preflight_v21_input_budget.py
```

当前默认产物为 `artifacts/methods/v21/v21_current_understanding/report.json`，原输入优化、退化覆盖和 issue 边界报告均保留；相同报告可重跑，不同内容拒绝覆盖，需指定新的 `--output`。脚本重建旧选择作只读比较，记录新的 Memory input_ref 和范围变化，核对退化配对及双侧事件完整性、各 Review 的事件/配对/反证数量及来源边界，并检查每个新请求能够完整还原。

新增 [16 项输入表示测试](../../../tests/skill_evolution/v21/test_evidence_wire_v21.py)，连同已有 Memory 更新、消费、Replay 和 v20 回归共 **157 项通过**。覆盖：逐项还原、重复内容、字面值碰撞、数据/标签/映射篡改、循环正文拒绝、真实短引用响应到 Memory/Editor 的通路、错误类型引用拒绝、反证不可遗漏以及恢复不重复调用。

没有实测模型效果，因此不声称共享内容表示一定改善模型理解，也不由代理 token 降幅直接推算费用或时延收益。真实双维学习效果、跨轮增长及质量—成本取舍仍需 Pilot 验证。
