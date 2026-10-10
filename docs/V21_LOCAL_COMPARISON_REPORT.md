# v21 真实模型局部对照

日期：2026-10-09。材料与预先判定依据见 [小规模验证案例](V21_SMALL_VALIDATION_CASES.md)。

本轮观察到：更新后的双维认识进入了 Fusion/Review，影响了问题组织、修改理由和历史证据读取；但没有证明它改善了最终修改决策。拆单与保障案例的边界判断合理，行李案例仍暴露出关键配对没有跨轮带入、已加载的有利历史没有被充分使用的问题。

## 1. 对照到底比较什么

通过现有 `build_memory_update_input` / `run_memory_update` 和 `run_memory_consumption` Python 入口运行，没有修改运行模块、Prompt 或校验器。模型沿用 `deepseek-v4-pro`，temperature=0、reasoning_effort=high。完整入口按批次运行 Fusion → 每个 PROPOSE 一次 Review → Compiler/Editor；没有另加 Review Agent。

| 项目 | 对照组 | 处理组 |
|---|---|---|
| 消费流程 | 相同的 v21 流程 | 相同的 v21 流程 |
| Memory | 第 3 轮学习档案中的原历史快照：6 个 issue，无新综合认识 | 从同一档案真实更新：8 个 issue，其中 4 个有综合认识 |
| 当前 Parent、Requests、Findings | 冻结的第 4 轮材料 | 完全相同，逐项复验 |
| 可访问的原始档案 | 原事件、轨迹、Policy/工具、配对 | 这些内容逐项相同，增加认识记录与来源关联 |
| 实际 Review 证据 | 由原 Memory 和 Fusion 选择决定 | 由更新后的认识和 Fusion 选择决定，范围发生变化 |

这是**旧历史快照与 Replay 更新后 Memory 的局部诊断对照**，不是 v20 方法与 v21 方法的公平效果实验，也不是只改变一句归因文字的严格消融。issue 数量、认识的新旧和来源关联均有变化；后续 Review 实际读取范围不同，不能把结果差异单独归因于归因文字。只有各一组消费运行，temperature=0 也不代表输出必然可复现。

保留完整七组 batch、39 条 Findings，重点判定三个预先选定案例。Memory 更新选择四个既有提案：三个焦点问题及同轮取消规则修改，并显式加入五组案例配对；沿用默认退化补入和来源闭包，实际加载 19 组配对。没有删除实际 edits 来假造一个更小的历史轮次，也没有调用新 Replay、读取私有评判原因或重做 Current Diagnosis。

## 2. Memory 更新的三次真实调用

| 调用 | 结果 | 总输出预算 / 实际输出 token |
|---|---|---:|
| update | 拒绝：attempt 的 `source_refs` 包含未加载事件编号 `1202` | 24,000 / 18,304 |
| update-retry1 | 相同输入与请求逐字节重跑；拒绝：`finish_reason=length`，24,000 token 全为 reasoning，未形成完整答案 | 24,000 / 24,000 |
| update-48k | 通过原有结构、来源和长度校验 | 48,000 / 18,014 |

第三次只通过已有 transport 注入接口调整这次调用的总输出预算，实际请求另存 `effective-request.json`；未修改默认配置或运行源码。输入、Prompt 和 schema 不变。成功调用实际输出低于原 24,000 上限，因此不能证明提高预算是成功原因，更不能据此声称默认入口已稳定。

**2,000 字符硬性拒绝条件始终保留。** 成功更新的四段综合认识分别为 719、620、623、689 字符；没有截断、人工修改答案或把失败输出继续交给消费端。前两次失败及全部用量均保留。

成功认识保留了这些区分：拆单后的七人任务成功合规，六人任务合规但失败；保障信息不足时转人工可以合规但仍任务失败；已有 trip-type 指引可在执行中观察到，但不能解释全部行李合规问题。它们仍是可修订解释，不是局部修改因果已经得到证明。

## 3. 三个案例的实际判定

| 案例 | 对照组 | 处理组 | 人工判定 |
|---|---|---|---|
| 行李计费 | 与姓名、trip type 合并送审；Review 4 为 NO_EDIT | 与姓名分开；行李 Review 6 为 NO_EDIT，仍未带入 T009 显式配对 | 问题组织有所改善，但关键历史学习与 Review 证据利用不充分；不能判为机制通过 |
| 多人拆单 | Review 9 为 NO_EDIT | Review 5 为 NO_EDIT，加载 T013/T016 等四组历史配对 | 两组均未由任务失败否定拆单、编造失败原因或重复添加人数上限；决定合理，未观察到最终决策改善 |
| 保障条件不明 | Review 8 为 NO_EDIT | Review 3 为 NO_EDIT，加载 T035 等四组历史配对 | 两组均保留知情选择与有条件转人工；处理组明确区分文字覆盖、观察到执行与因果效果，未观察到最终决策改善 |

两组中的 NO_EDIT 都不能自动当成正确。拆单和保障的理由回应了已有条款与证据边界；行李的关键问题在于理由没有充分处理已有观察，而不是必须强制写出一条行李新规则。

### 行李案例：两个不同的问题同时存在

第一，真实更新输入加载了第 3 轮 T009 配对：任务成功保持、合规从 true 变 false。通过校验的 Memory 更新没有引用该配对，也没有把这次 business 两件行李退化形成有对应来源的新认识。处理组行李 Review 的 `pairs` 最终只有 T011、T015，没有 T009。因此，**更新输入的退化覆盖并不保证更新后认识或下一轮 Review 的配对覆盖**。

第二，不能进一步说“Review 根本没有读到零收费的正面例子”。复查实际输入发现，旧来源展开仍带入了一条更早的第 1 轮轨迹：同类 business、两件行李，`nonfree_baggages=0`，标签成功合规；当前第 4 轮轨迹则为 `nonfree_baggages=2`，成功但不合规。Review 理由重点讨论“不合规案例与一个合规案例均全部收费”，没有回应这条零收费正面观察。

两条确实已加载的调用为：

- 早期支持：`CURRENT/ed12295dba0354058acdf02017fda65a198b2cbbd49db08fea5fa9a469cb6c94/T022/R036/R1/E0013`。
- 当前问题：`CURRENT/2d95760687f3791920a05adf0378b3c6b300394c63663330a8fac0d39c50d521/T022/R036/R1/E0012`。

原文、参数、版本与标签已单独抽取到 [证据核查](../artifacts/v21_local_comparison_001/baggage-loaded-comparison.json)。它们来自不同轮次，不能伪装成 T009 的同轮 Parent/Candidate 配对，也不能据此宣称完整内部合同已知。但 Review 应回应这种有条件的历史支持，解释为何仍不足以授权修订，而非仅以合同不可见概括为没有可用条件证据。

### 拆单与保障：读取了历史，不等于已证明增益

处理组拆单 Review 保留了早期六人、七人单笔调用虽然工具成功却不合规的反例，同时没有把一次拆单后任务失败解释为人数规则应删除。它没有编造生日错误的原因；本例两侧用户生日表述不同的混杂仍按预先判定依据保留，不能宣称局部因果已被隔离。

处理组保障 Review 明确将身份查询时序问题排除在所选条件保障 issue 之外，且不因转人工后任务失败而要求猜测保障映射或强制执行。这些判断符合预定边界。但当前 Findings 和 Parent 本身已含足够相关信息，对照组也给出合理 NO_EDIT，所以本轮不支持“新增 Memory 改善了这些决定”的结论。

## 4. 提案、最终修改与成本

Fusion 对照组提出 10 个 PROPOSE，处理组提出 11 个，均未在 Fusion 阶段主动 NO_EDIT。处理组多出独立姓名问题，不能简单把数量增加都视为变差；但大量已有文字覆盖或仅原因未知的方向仍送入 Review，没有观察到减少此类复查的收益。

最终消费结果及全部网关用量见下方完成记录；总 token 包含重复输入、缓存读取和 reasoning，不等于独立证据量或实际金额。失败调用也计入，不将代理 token 估计当作网关实测。

两组均完成现有消费入口并生成候选：对照组 10 个 Review 中 2 个 VERIFIED、8 个 NO_EDIT；处理组 11 个 Review 中 2 个 VERIFIED、9 个 NO_EDIT。两组均新增两条规则，针对同样两个当前问题：地址确认文本不准确、替换航班选择条件自相矛盾。二者都不属于本次三个焦点案例，也未关联历史 Memory issue。候选的顺序、措辞和具体表述不同，不能把这些差异解释成已验证的 Memory 收益。

| 阶段 | 真实调用数 | 输入 token | 输出 token（含 reasoning） | 合计 |
|---|---:|---:|---:|---:|
| Memory 首次，拒绝 | 1 | 162,789 | 18,304 | 181,093 |
| Memory 同请求重跑，拒绝 | 1 | 162,789 | 24,000 | 186,789 |
| Memory 48k 配置，通过 | 1 | 162,789 | 18,014 | 180,803 |
| 对照组 Fusion/Review/Editor | 12 | 430,099 | 85,631 | 515,730 |
| 处理组 Fusion/Review/Editor | 13 | 521,558 | 74,660 | 596,218 |
| **全部** | **28** | **1,440,024** | **220,609** | **1,660,633** |

输出中 reasoning 共 203,262 token；输入统计含 376,832 个缓存读取 token。以上是响应 usage 的总和，不是费用。处理组消费总 token 比对照组高约 15.6%，另需承担 Memory 更新成本；本轮没有成本下降证据。虽然人工重点仅有三例，原入口仍处理完整七组并按 Fusion 提案逐项 Review，这也是本次局部验证调用量偏大的实际原因，后续小规模验证应在保留合法 batch 与证据边界的前提下进一步控制范围。

成功 Memory 原始响应已重新通过现有 validator，两组 generation audit 均通过现有恢复校验，候选文本与差异已保存；全部运行源码和冻结来源哈希与启动前相同。详见 [验证记录](../artifacts/v21_local_comparison_001/verification.json)、[对照候选差异](../artifacts/v21_local_comparison_001/control/candidate.diff)和[处理候选差异](../artifacts/v21_local_comparison_001/treatment/candidate.diff)。这些检查确认工程与来源一致性，不代替上述人工语义判定。

## 5. 对下一步的约束

本轮支持继续采用现有轻量结构，不支持立刻增加 Agent、分类表、重复 Review 或强制逐 edit 归因，也没有依据放宽 2,000 字符限制。

优先处理已经观察到的两个环节：一是修改后退化在形成认识时被遗漏、导致下一轮缺少显式配对；二是 Review 对已加载的有利历史与反例回应不足。应先围绕行李案例做最小补强并复验，区分来源装配和语义使用，不能只加一句“考虑双维”便声称修复。

Fusion 是否应将“当前已覆盖、没有具体新缺口”的方向直接 NO_EDIT，可作为第二优先级检查；现有 Review 的保守否决仍有价值。默认真实调用还出现一次引用失败和一次输出耗尽，应单独检查稳定性；不能把结构失败混为方法语义失败。

在这些局部问题有明确处理结果前，本轮不足以作为“语义验证全部通过、可直接进入完整 v21 调度实验”的依据。所有候选仅为本地生成产物，未 Replay 验证，也未发布为活动 Skill/Memory。

## 6. 可复查产物

- [协议与源码/输入哈希](../artifacts/v21_local_comparison_001/protocol.json)：记录实际 Git HEAD；工作区已有未提交变更，因此另冻结源码哈希。
- [逐调用用量、两组决策与输入一致性](../artifacts/v21_local_comparison_001/comparison.json)。
- [焦点 Review 的实际历史配对范围](../artifacts/v21_local_comparison_001/focal-evidence-coverage.json)。
- [第一次拒绝](../artifacts/v21_local_comparison_001/update/validation-failure.json)、[第二次拒绝](../artifacts/v21_local_comparison_001/update-retry1/validation-failure.json)、[通过校验的更新](../artifacts/v21_local_comparison_001/update-48k/complete.json)。
- [对照组 generation audit](../artifacts/v21_local_comparison_001/control/generation/generation-audit.json)。
- [处理组 generation audit](../artifacts/v21_local_comparison_001/treatment/generation/generation-audit.json)。
- [本地入口调用脚本](../artifacts/v21_local_comparison_001/run_phase.py)、[用量汇总脚本](../artifacts/v21_local_comparison_001/summarize.py)。这些脚本与大体积原始产物保存在 Git 忽略的 `artifacts/`；本报告保留在文档目录。
