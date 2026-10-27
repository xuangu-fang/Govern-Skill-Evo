# R05 当前版本生成：语义审查

2026-10-22。审查首次结构有效的 Preconditioner 和 Editor 输出。以下为人工审查，不是新增自动审核模块；未修改模型输出，也未因语义问题重采样。

**结论：Original 可复用，两阶段结构及交接通过；Preconditioner 理由有事实与推断问题，Editor 的 u3 范围实现未通过忠实性检查。** 当前 Candidate 不能直接标为忠实实现全部 Effective Updates。

## Preconditioner 的实际决定

| Update | 决定 | 核对 |
|---|---|---|
| u1 精确目标、禁止替代 | KEEP | 原文和 basis 完整保留。理由回应“禁止替代并不自动创造成功”的历史限制；保持该方向合理，但不能把联合编辑下的找物成功独立归因于此规则 |
| u2 搜索扩展 | S | 将不同类型扩展的硬要求改为未尝试类型的优先偏好；保留开放表面，并将防回访措辞改为当前/近期可见状态和短循环。未再加入旧结果的“两次”阈值 |
| u3 合法动作与直接动作回退 | KEEP | Original 的通用规则完整保留，没有限定为非 desklamp。理由中的事实错误与过强结论不构成对原文的修改 |

u2 的 Patch 对应 `change` 中的调整，未发现 Patch 独自加入额外动作、前提或顺序。其 D/S/C 作用可从具体强度与近期条件变化中辨认，并非只有 `focus: ["S"]` 标签。不过，模型文字不能证明其内部先进行了 D/S/C 决策，执行有效性仍未知。

## 理由中的明确问题

| 编号 | 原输出声称 | 可复核的实际证据 | 判断 |
|---|---|---|---|
| P1 | u2 reason：P8 中 “the shelf and countertop are never visited” | P8:7、P8:13、P8:20 均为 `go to countertop 1`；确实没有访问 shelf | 明确事实错误，不能把“某些位置仍未探索”概括为“从未访问 countertop” |
| P2 | u3 reason：三个无效导航 “each was followed by an admissible direct action on the same receptacle” | P6:20→21、P8:5→6 支持该描述；P1:4 的无效 `go to shelf 2` 后，P1:5 是 `go to desk 1`，没有同一 shelf 的直接动作 | 把两个正例推广到三个。P1 仍支持动作合法性检查，但不支持该回退序列 |
| P3 | u3 reason：“therefore cannot regress the successful completions” | 当前原始轨迹没有执行待验证的完整 Update，Memory 也没有隔离出该要求的无退化因果效果 | 结论过强；最多支持保留该提案的动机，不能保证没有退化 |

以上问题均保留在原始响应；没有把 `reason` 改成更正确的版本，也没有用它触发技术重试。

## 需要保留的解释边界

- **同类位置并非在 Original 中被明确禁止。** Original 要求在回查已看位置前至少扩展到另一类型，并未全面禁止检查同类中的新位置。因此 u2 更准确的变化是放松跨类型的硬要求、改成类型偏好，而不是已证实“解除原本禁止同类新位置的限制”。这种探索可以验证，但不能把错误的限制解释当作已证实收益。
- “当前/近期可见”减少了反回访要求对长历史的依赖，但文本仍含 `still-unexamined` 和 `a type you have not yet tried`。不能宣称已彻底解决两步历史窗口下的全局搜索记忆问题。
- 三个理由引用了 M3/M6/M8 等 Memory ID，却没有提供具体历史 Diff/step 引用。结构允许其解析，但未充分落实 Prompt 对具体历史编辑/行为主张的引用要求；人工仍可回查源。不能仅凭出现 Memory ID 就判定历史归因充分。
- 当前来源支持搜索循环与非法动作问题，以及历史响应混合的总体描述。新规则的独立贡献、同类搜索偏好和短循环条件的效果尚待实际执行。
- `checks: null` 保留 Original Checks；c2 仍偏向不同类型的硬要求。按既定范围，记录这项覆盖差异，不因此重新设计 Checks 或判为技术失败。

## Editor 四项核对

| 审查点 | 结果 | 说明 |
|---|---|---|
| 输入是否为最终 Effective Plan | 通过 | 归档的 Editor material/messages 与程序从选中 PC 编译出的输入逐字段相等；没有改用 Original Plan |
| 是否忠实落实 Update | **u3 范围未通过** | Candidate 第 22 行是非 desklamp 章节，第 24 行限定其用途，第 26 行才新增完整 u3。Editor reason 也明确称三个 Updates 都在 non-desklamp procedure 内实现；Effective u3 未授权这项范围缩小 |
| 是否增加未支持的重要策略 | 未发现新的主要策略 | u1/u2 的要求基本对应；原有“所有 plausible candidates 检查一次”的完成边界来自 Parent，并非 Editor 本次新增。章节位置造成的范围变化单独计为实现偏差 |
| 是否保存真实 Diff | 通过 | 作者 Patch 严格应用后得到 Candidate；规范化实际 Diff 再次应用同一 Parent 完全重建 Candidate，并冻结 SHA256 |

u3 的 Original basis 包括 desklamp 的 P1:4 以及普通任务的 P6/P8。Goal 要保留 desklamp 成功行为，并不意味着通用合法性检查必须排除 desklamp。Actor 基础协议本身已经要求选择 admissible action，这部分可以避免重复，但它没有完整表达 u3 的“导航不可用时选择适当直接动作”回退规则；不能据此认为本次章节范围缩小已经获得充分覆盖。

与 study 001 旧 R05 相比，范围问题在当前 Editor 输出中再次出现。这是同一开发案例的重复观察，不是另一个独立任务上的普遍性证据。本次不据此修改 Editor Prompt 或新建审核 Agent。

## 产物与状态

- [原始 Preconditioner](runs/R05_pc/attempt_001/parsed.json)
- [Effective Plan](handoff/effective_plan.json)
- [原始 Editor](runs/R05_editor/attempt_001/parsed.json)
- [Candidate](handoff/candidate.md) / [真实 Diff](handoff/actual.diff)
- [冻结原始输入](../../../../artifacts/methods/v23_4/semantic_generation_006/config/cases/R05.json)

本次生成与核查工作已完成。Candidate 原样保留，Actor 尚未运行；不将本结果宣传为完整语义通过或效果提升。
