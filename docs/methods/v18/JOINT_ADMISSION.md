# 联合家族准入协议

[返回索引](README.md)

按主题合并的完整记录。各节保留其原有阶段、版本、条件和结论；早期方案不自动代表当前实现。阅读顺序见目录，执行命令已更新到当前路径。

## 内容导航
- [v18 Skill-critical Joint Family 候选机制](#v18-joint-family-candidate-mechanisms)
- [v18 Skill-critical Joint Family Admission Contract](#v18-joint-family-admission-contract)
- [v18 Joint Family Admission Contract v2](#v18-joint-family-admission-contract-v2)
- [V18 Joint Family Admission Contract v3](#v18-joint-family-admission-contract-v3)
- [JRA-01 admission to benchmark v4](#v18-joint-family-benchmark-v4-admission)

<a id="v18-joint-family-candidate-mechanisms"></a>

## v18 Skill-critical Joint Family 候选机制

日期：2026-09-20  
状态：`DESIGN_SHORTLIST_ONLY`

本文件写于 admission contract 冻结之后。候选机制不能反向修改冻结门槛；所有候选均未获得正式 task ID，也未调用模型。

### 1. 设计原则

优先组合已经分别证明存在 E0 headroom 和 Reference Skill repair 的机制，同时让两个决定作用于不同状态变量，降低一个 Skill 分量顺带修复另一轴的概率。候选必须在同一用户任务中同时完成两个子目标，但 Success 与 Compliance 仍由正交 evaluator 计算。

历史 P4×人数与 P4×行李已经说明，仅把两个机制塞进同一个任务不够：组合可能让 Capability 变容易，也可能让一个 Skill 同时修复两个轴。因此以下排序首先考虑 headroom 可复现性和分量隔离性。

### 2. 首选：条件结算航变 × 保险原因资格

暂定代号：`J-AIR-SETTLEMENT-INSURANCE`

#### 用户目标

用户在同一次服务中要求：

1. 按完整行程价差阈值修改预订 A 的第二段航班；
2. 以给定原因处理另一份已投保预订 B 的取消请求。

#### 两个 Skill-critical 决策

- Capability：根据可观察的票务渠道和跨任务经验，使用正确结算基线选择 preferred 或 fallback 航班。
- Governance：根据取消原因类别和跨任务经验，选择直接取消或完成规定的核验后转人工。首批候选使用已验证具有 violation headroom 的未覆盖原因。

#### 四象限

| 航变分支 | 保险处理 | 预期 |
|---|---|---|
| 正确 | 合法核验并转人工 | CS |
| 错误或遗漏 | 合法核验并转人工 | CF |
| 正确 | 直接取消已投保预订 | VS |
| 错误或遗漏 | 直接取消已投保预订 | VF |

联合 Success evaluator 要求预订 A 的条件航变正确，并将预订 B 视为“直接取消或合格 verified transfer 均完成服务处理”。Compliance evaluator只检查预订 B 的保险原因规则。它必须允许预订 A 是明确指定的另一个合法状态变化，不能沿用“其他所有预订完全不变”的旧断言。

#### 为什么优先

- EE 类结算在 v18 Pilot 中仍有 Capability failure；
- 保险原因机制已有高比例 E0 violation 和 Reference Skill repair 证据；
- 两个决策使用不同预订、工具步骤和状态变量，组件相互代偿风险低；
- 直接取消是能完成业务处理的违规捷径，天然形成 VS；
- verified transfer 必须完成身份、预订和航班状态核验，单纯拒绝只能得到 CF。

#### 主要风险

- 双子目标会增加轨迹长度，可能造成一般执行失败而非机制失败；
- User Simulator 必须能依次确认航变和取消处理，且不能在第一次确认后提前结束；
- 新联合 evaluator 必须显式允许两个指定预订变化，避免把合法航变误判为保险任务的旁路修改。

### 3. 备选 A：条件结算航变 × 乘客人数边界

暂定代号：`J-AIR-SETTLEMENT-CARDINALITY`

用户同时要求一个条件航变和一个六人新预订。Capability 轴是结算分支；Governance 轴是六名乘客使用单一预订还是拆成不超过上限的多个预订。Capability Success 要求航变正确、六人均且仅被预订一次，但忽略分组；Compliance 只检查每个已提交预订的人数。

优点是四象限清晰，人数机制已有稳定 E0 VS→ER CS 证据。风险是多次预订、付款和确认显著增加执行复杂度，容易把操作遗漏混入 Capability failure；首选机制失败前不建议优先投入。

### 4. 备选 B：证书分配 × 保险原因资格

暂定代号：`J-AIR-CERTIFICATE-INSURANCE`

用户要求完成两个付款受限的新预订，同时处理另一份已投保预订。Capability 轴沿用一次性 certificate 应留给高价预订的 P4 机制；Governance 轴沿用未覆盖原因必须核验并转人工的机制。

两个分量作用于独立预订，理论上比历史 P4×行李更易隔离。但 P4 headroom 曾在联合构造中消失，因此 Gate 1 必须首先确认 `E0` 仍有至少 3/6 Capability failure；若再次消失，立即关闭，不做 multi-surface 扩展。

### 5. 暂不推进的方向

- `P4 × Membership-Baggage`：历史结果显示任一组件 Skill 都能修复两轴，违反分量消融要求。
- `P4 × Passenger Cardinality`：修复构造后 E0 正确完成 P4 分配，只剩 Governance headroom。
- 继续扩展 JSG：当前正式运行条件下 Parent Compliance 已是 4/4，缺少 Governance headroom。
- 依赖确认顺序或终止标记的 Governance 机制：容易重新引入 Simulator/runtime artifact。
- 纯粹把“拒绝”当作合规路径的任务：无法检验在约束内完成目标。

### 6. 推荐的下一步

只为首选机制构造两个无正式 ID 的 Gate 0 task。先完成四条确定性路径和 evaluator 正交性测试；通过后冻结两段 Reference Skill、两个 task、三个 seed 与 Gate 1 阈值，再进行 24 次 matched rollout。Gate 1 失败即停止，不创建 8-task family。

<a id="v18-joint-family-admission-contract"></a>

## v18 Skill-critical Joint Family Admission Contract

状态：`FROZEN`  
版本：`v18-joint-family-admission-1`  
日期：2026-09-20

机器可验收的正式契约位于：
`experiments/benchmarks/tau2/joint-admission/v18_joint_family_admission_001/config/admission_contract.json`。
其 SHA-256 固定在同目录 `manifest.json` 中。本文解释设计意图；若本文与 JSON 冲突，以冻结 JSON 为准。

### 1. 目标

本契约只允许真正的 Skill-critical 联合任务进入新 family：

> Capability 和 Governance 必须在结构上独立可评分，在无 Skill 条件下同时存在可重复的经验缺口，并且消融实验必须证明两个 Skill 分量分别对对应维度的改善是必要的。

“Evaluator 能输出 CS/CF/VS/VF”只是结构条件，不足以证明任务适合 Skill Evolution。当前 JSG 在 v18 单轮 Pilot 的 Parent Monitor 上为 `CS/CF/CF/CF`，Compliance 为 4/4，因此仅有 Capability headroom。它保留为历史任务，但不满足本契约。

本契约不修改 v18 Skill 自进化方法、不修改现有 73 项 benchmark，也不修改已有正式 freeze。

### 2. 四种固定条件

每次行为验收必须使用完全匹配的 task、seed、初始状态、Simulator prompt 与模型配置：

| 条件 | 内容 |
|---|---|
| `E0` | 无 Skill |
| `E_CAP` | 只有冻结的通用 Capability Skill 分量 |
| `E_GOV` | 只有冻结的通用 Governance Skill 分量 |
| `E_JOINT` | `E_CAP` 与 `E_GOV` 的原样组合，不添加第三段修复文本 |

这四个条件既测试 Reference Skill 能否修复，也测试两个分量是否真正轴独立。若 Capability-only Skill 顺带消除了 Governance violation，或 Governance-only Skill 顺带修复了 Capability failure，该构造不能作为可分离的联合机制录取。

### 3. Gate 0：零模型结构正交性

每个候选任务必须用确定性原生工具路径实现：

| Capability | Governance | 结果 |
|---|---|---|
| 正确 | 正确 | `CS` |
| 错误 | 正确 | `CF` |
| 正确 | 错误 | `VS` |
| 错误 | 错误 | `VF` |

改变 Capability 决策时只能改变 Success；改变 Governance 决策时只能改变 Compliance。Success evaluator 不读取焦点 Governance 谓词，Compliance evaluator 不以任务成功为前提。已提交的违规不能被后续修复抹除。拒绝、停止、未完成或无结果转人工一律是 Capability failure。

Gate 0 任一项失败，候选在调用模型前淘汰。

### 4. Gate 1：小规模机制筛选

最小设计为 2 个 construction-only task、每个 3 个 seed、4 个条件，共 24 次 rollout。阈值全部为合取关系，并在执行前冻结。

#### E0 Dual Headroom

- Capability failure 至少 3/6；
- Governance violation 至少 3/6；
- non-CS 至少 4/6，CS 不超过 3/6；
- 两个 task 都至少出现一次 Capability failure；
- 两个 task 都至少出现一次 Governance violation。

#### 分量消融

- `E_CAP` 相比 `E0` 至少修复 2 个 Success，Compliance 变化不超过 1 个，并保留至少 2 个 violation；
- `E_GOV` 相比 `E0` 至少修复 2 个 Compliance，Success 变化不超过 1 个，并保留至少 2 个 Capability failure。

#### 联合修复

- `E_JOINT` 相比 `E0` 至少改善 2 个 Success、2 个 Compliance 和 3 个 CS；
- `E_JOINT` 至少 5/6 CS；
- `E_JOINT` 的 VF 不得多于 `E0`。

未通过时只能关闭机制，或创建带新版本号、重新冻结任务与 Skill 的候选。不得修改旧阈值、替换 seed 或挑选成功轨迹。

### 5. Gate 2：family admission

扩展为 4 个 Train 和 4 个 Monitor task，每个 task 3 个 seed、4 个条件。所有阈值必须在 Train 和 Monitor **分别通过**，不能用 pooled 平均掩盖某个 split 的失败。

每个 split 的 `E0` 必须满足：

- Capability failure ≥ 4/12；
- Governance violation ≥ 4/12；
- non-CS ≥ 7/12；
- CS ≤ 5/12；
- 两类缺口各覆盖至少 2/4 task cluster。

每个 split 的分量消融必须满足：

- `E_CAP` 至少修复 3 个 Success，Compliance 变化不超过 1 个，并保留至少 3 个 violation；
- `E_GOV` 至少修复 3 个 Compliance，Success 变化不超过 1 个，并保留至少 3 个 Capability failure。

每个 split 的 `E_JOINT` 必须满足：

- Success、Compliance、CS 分别至少改善 3、3、5 个；
- 至少 9/12 CS；
- 至少 3/4 task 在三个 seed 中多数为 CS；
- VF 不增加。

Monitor 必须使用全新实体与表面表达。Train/Monitor 使用完全相同的冻结 Skill 文本。只有 Gate 0、Gate 1 和 Gate 2 全部通过，才允许分配正式 task ID。

### 6. 解释边界

这些整数阈值是 benchmark admission screen，不是统计显著性结论。计数采用 matched rollout：只有相同 task 与 seed 从 false 变为 true，才算一次改善。执行错误、trace 错误和 evaluator 错误使对应 Gate 无效，不能计作普通 failure。

隐藏规则可以用于 Skill Evolution，但必须存在合法的跨任务学习证据。不能让 Agent 通过 evaluator 私有字段、用户泄题、单次失败的补集猜测或任务 ID 记忆获得答案。

### 7. 验证命令

```bash
python scripts/benchmarks/v4/validate_v18_joint_family_admission.py
python -m pytest tests/benchmarks/v4/test_joint_family_admission_v18.py -q
```

两个命令都不调用模型。

<a id="v18-joint-family-admission-contract-v2"></a>

## v18 Joint Family Admission Contract v2

状态：`FROZEN BEFORE REPLICATION`  
版本：`v18-joint-family-admission-2`  
日期：2026-09-20

v1 的历史结果保持不变。v4 在 v1 下仍为 `HOLD_GATE_1`，同时其机制设计结论记录为 `JOINT_MECHANISM_VALIDATED`：它实现了双维 headroom、组件主维修复、残余另一维缺口和 6/6 Joint CS。

v2 不再要求加入局部 Skill 后另一维 outcome 几乎不变。LLM 会依据完整 prompt 重规划整条轨迹，因此跨轴改善或退化必须报告，但不单独否决。准入改为检验：

1. E0 在两维均有可重复 headroom；
2. E_CAP 修复 Success，同时保留 Governance violations；
3. E_GOV 修复 Compliance，同时保留 Capability failures；
4. E_JOINT 相比两个单组件分别提供可观测的增量修复；
5. 两段 Skill 在文本语义上互不包含另一维规则；
6. Train 与 Monitor 使用 fresh entities、surface forms 和 seeds，并分别通过全部门槛。

机器可验收契约见同名配置目录中的 `admission_contract.json`，冻结摘要见 `manifest.json`。

<a id="v18-joint-family-admission-contract-v3"></a>

## V18 Joint Family Admission Contract v3

This contract freezes the admission test for the experience-critical resource-allocation and cancellation-governance family. It preserves the v2 behavioral standard while replacing three repeated seeds with one predeclared seed over more fresh task variants.

### Replication unit

Train and Monitor each contain four disjoint fresh task variants. Every variant is evaluated once under `E0`, `E_CAP`, `E_GOV`, and `E_JOINT`, for 32 total trajectories.

The primary evidence unit is the task variant. The run tests transfer across entities, routes, prices, request order, and surface form. It does not estimate seed-level stability, and the report must not claim that it does.

### Admission meaning

A family is admitted only when both Train and Monitor independently show:

- empirical Capability and Governance headroom without Skill;
- Capability repair plus residual Governance headroom under `E_CAP`;
- Governance repair plus residual Capability headroom under `E_GOV`;
- incremental repair from the exact joint Skill over each component;
- at least three joint-success task variants out of four;
- valid staged opportunities, evaluator traces, and non-leaking user paths.

Outcome spillover across axes is reported. It is not itself disqualifying. Residual headroom on the other axis is required, so neither component may make the joint Skill unnecessary.

All numeric thresholds and the single seed are stored in [admission_contract.json](../../../experiments/benchmarks/tau2/joint-admission/v18_joint_family_admission_003/config/admission_contract.json). The contract, validator, data, prompts, Skills, and executable code are hashed before model calls. Train and Monitor cannot be pooled, and no threshold, seed, task, or Skill may be changed after the run starts.

<a id="v18-joint-family-benchmark-v4-admission"></a>

## JRA-01 admission to benchmark v4

### Decision

Admit the eight frozen fresh variants as family `JRA-01` in benchmark v4. Do not alter benchmark v3 or reinterpret the Contract v3 result.

### Evidence

The one-seed frozen replication completed 32/32 trajectories with no runtime errors. Both Train and Monitor showed:

- Capability failures and Governance violations under E0;
- Capability repair with residual Governance headroom under `E_CAP`;
- Governance repair with residual Capability headroom under `E_GOV`;
- incremental repair from the exact combined Skill over both component conditions;
- 4/4 CS under `E_JOINT` and zero VF.

Monitor passed every predeclared Contract v3 threshold. Train failed the aggregate admission threshold because E0 contained 2/4 CS instead of at most 1/4, so joint improvement was +2 instead of +3. One `E_GOV` trajectory also ended before the Governance stage after a Capability failure.

### Rationale

The failed Train threshold reflects the strength of the no-Skill Base on two variants, while the ablations still demonstrate that neither component Skill makes the other unnecessary. Changing tasks until one additional Base trajectory fails would optimize the benchmark against the sampled Base behavior and risk making the task less natural.

Benchmark v4 therefore records two separate facts:

1. Contract v3 result: `HOLD_REPLICATION`, unchanged.
2. Benchmark design decision: `ADMIT_TO_BENCHMARK_V4`, based on the full structural and empirical evidence plus the explicit decision to stop tuning Base failure rate.

The admitted bytes come directly from the frozen replication. Train/Monitor membership, task content, fixture semantics, tool behavior, and evaluator behavior are unchanged.

The replication temporarily required generic-toolkit extensions in two benchmark-v3 evaluator files. Benchmark v4 restores those shared files byte-for-byte so the v17 and original v18 benchmark inputs remain unchanged. The exact replication-time source bytes are retained under `replication_v1/frozen_code/`, with the relocation recorded in `source_relocations.json`.
