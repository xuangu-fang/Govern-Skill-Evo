# V22 失败 Train 上的同信息 Direct／Conditioned 对照

日期：2026-10-15。已完成两条失败 Train、共享 Diagnosis、两侧构造及冻结后的 **18 次独立 Selection 执行尝试**。Direct 成功 **4/6**，Conditioned **3/6**；No Skill 为 **2 成功、2 失败、2 次连接中断（未知）**。本次未展示 Conditioned 成功率优势，也未出现可追溯的历史响应驱动要求变换。原始 Conditioned 定位错误完整保留；独立、零模型调用的格式处理只分段引用，候选原文未改，未采用候选或学习 Selection。

## 问题与范围

**Question：** 使用 No Skill 失败的 Train 反馈，已有同信息 Direct／Conditioned 流程能否形成可执行修复，并在冻结后的独立任务上观察实际效果？**Hypothesis：** 当前失败提供具体修复目标；依据行为响应调整方向、尺度和关联，可能比普通历史辅助修订更合理。保持、无收益及回归都是合法结果，不强迫历史引起非恒等变换。

本次收敛到失败修复，没有继续扩展 Diagnosis 的效率优化、成功程序提炼或更新价值判断。Diagnosis、Memory 快照、Direct／Conditioned 提示、Editor、紧凑输出形状和执行参数与 05 相同。原 05 的三条成功 Train、`no_change` 与未执行 Selection 状态保留。

[原协议](../config/plan.json)在新执行前保存。方法和执行参数不变，研究问题与采样说明收敛为失败修复，Train 选择改为既有 No Skill 失败任务，episode 上限由 21 调整为 20。历史来源只用于选题；当前学习输入是两项各一次新的、可核对的 No Skill 回放，不人工改写旧轨迹身份，也不看到新结果后换题。

## 选题及真实失败反馈

旧六类原生 No Skill 检查有两项完整失败，全部按 ID 顺序选入：`train:0021` 冷却 Bread 后放到 CounterTop，`train:0034` 将两件 CD 放到 Drawer。旧记录均为 50 步上限结束；由于缺少当前固定 Skill 入口的完整身份字段，本次各复跑一次，两个新结果全部保留。选择依据及 hash 见[来源清单](../results/selection_provenance.json)。这是有意的失败任务开发采样，不是无偏 Train 成功率估计。

| 新 No Skill Train | 原生结果 | 步数 | 列表外动作 | 可观察问题 |
|---|---|---:|---:|---|
| `train:0021` | `step_limit`，失败 | 50 | 0 | 在多个位置反复搜索，37 次导航；未找到 Bread，也未开始取物、冷却或交付 |
| `train:0034` | `step_limit`，失败 | 50 | 2 | 第 33 步交付第一件 CD；第 44 步取得第二件，第 50 步却放回 dresser；第 31、46 步尝试在已持物时再取物未产生效果 |

Actor 仅有当前观察、合法动作与最近两组动作前观察／动作，没有全局访问记录。第一件 CD 的交付与较早位置观察会移出后续可见输入；因此不能把所有重复搜索解释为“模型明知已访问仍故意忽略”，也不能声称局部避重规则已解决长周期搜索。具体动作是否可用以当时记录为准，不从两次非法动作推出所有状态只有一个物品容量。

## 从共同初稿到两份候选

一次独立 Diagnosis 返回 `revise`，形成共同 intent 和两个要求：u1 根据当前及两步短历史切换无信息的搜索候选；u2 将已持有所需对象转移到命名目的地，逐件交付多对象，避免撤销进展。两项 watch 保留必要重访、合法来源放置等边界，初稿 `open=[]`。

两个 proposal 的用户证据消息逐字相同，读取同一认真初稿、当前 Train、完整有效 Memory；系统修订策略不同。两侧随后使用相同 Editor 提示，各一次 proposal 和一次 Editor。Direct 可以正常做条件化和协调，并非被限制为照抄。互不读取对方输出；调用上限相等不代表实际 token 或计算量相等。

| 项目 | Direct | Conditioned |
|---|---|---|
| 要求变换 | u1→u3、u2→u4；增加离开候选前的容器检查，明确剩余目标及最后交付 | `changes=[]`，保留 u1/u2；仅增加两步历史之外仍可能循环的观察问题 |
| 变换依据 | 只有当前 Train 来源 | 未提出要求变更 |
| Memory effect ID | 无 | 无 |
| 原始 Editor | Candidate，通过结构校验 | 完整 Candidate 原文已生成，一处引用定位失败，原分支为 `error` |

**本轮没有观察到可明确追溯的“历史响应 → 实际要求变换”。** Memory 已提供不等于被有效消费；Conditioned 的恒等是合法决策，但不能用它证明历史驱动的非恒等预条件化收益。即使候选分数不同，也仍是一次包含 Editor 实现差异的提示策略对照。

离线语义复核还发现：Direct 理由把 P1:19 当成未打开柜门，实际是柜面为空且后续列表没有 `open cabinet 4`，这一理由没有轨迹支持。两组保留绝对的禁止放回来源，以及含糊的朝目的地准备／处理要求，未明确解决合法来源交付和冷却等必要前置步骤。Direct u4 未逐字保留初稿“每件交付后再取下一件”，但仍有持物向目标转移的一般规则，不能仅凭改写就断言行为丢失。Conditioned Editor 另加入非目标物禁取、禁止把所持目标放回已完成的中间位置、导航／检查优先等细节，文本差异不能全部归于 proposal。上述判断未用于补改候选；结构通过不等于语义正确。

## 引用定位失败与独立冻结

原始构造目录为 `artifacts/methods/v22/failure_trial_20261015/run/`，状态保持 `frozen`，其中 Conditioned 分支保持 `error: mapping.excerpt: not found on declared side`。其第三条引用连续写出了第 6 条规则和第 7 条第一句，省略两者之间的换行及 `7. ` 编号；所有语义文字都存在，但不是一个连续子串。

在任何 Selection 执行之前，另存[格式处理协议](../config/span_reconciliation.json)，新增独立 `editor_span_reconciliation`／`reconciled_selection` 入口。只在唯一匹配且间隔仅为换行、数字列表标记时，将该引用拆成精确原文片段；片段以空格连接必须等于原引用。缺字、改义、歧义、其他结构错误一律不修复。两侧应用同一函数，Direct 映射 2→2，Conditioned 3→4；Candidate 文本、要求 ID 和其他字段均不变。

这是原协议“仅允许继承 watch 去重”的**显式、评价前修订**，不是原操作已成功的回填。原始 raw、错误、候选、输入、费用和冻结记录保持不变。派生目录 `artifacts/methods/v22/failure_trial_20261015/reconciled_selection/` 保存新的来源绑定、精确文本、定位及冻结；修复零模型调用、零 Train 重跑。它不认证行为语义，也没有人工改写 Skill。

## 独立 Selection 与解释边界

沿用 05 中预选但尚未运行的六个任务：`val:0001/0005/0007/0011/0014/0017`，覆盖灯光观察、普通搬运、清洁、冷却、加热和双物体。Selection 不按 No Skill 失败筛选。每项用 No Skill、Direct、Conditioned 各执行一次，共 18 个 episode；轮换各任务执行条件顺序，最多三个 Actor 并发。每个 episode 独立重置环境，最多 50 步。

冻结之后不再调用 Diagnosis、Memory、proposal 或 Editor，不修改要求或候选，不依据结果重跑或换题。所有候选保持 staging，未采用、未发布全局 Memory。Test 没有被读取或执行。若今后这些 Selection 结果用于方法开发，它们即成为已使用材料，不能继续称作独立验证样本。

本次预算没有额外安排两份候选在 `train:0021/0034` 上复跑。因此，它回答失败反馈能否支持当前构造及新任务上的表现，不直接证明原来的两项 Train 失败已被修复。

完整结果如下，括号内为实际执行步数；失败均为 50 步上限结束。未知是模型请求连接中断，不是任务失败，也不填作零分。

| Selection | 类型 | No Skill | Direct | Conditioned |
|---|---|---|---|---|
| `val:0001` | 灯光观察 | 失败（50） | 成功（23） | 成功（4） |
| `val:0005` | 普通搬运 | 成功（8） | 成功（5） | 成功（5） |
| `val:0007` | 清洁 | 未知（43；第 44 次请求中断） | 失败（50） | 失败（50） |
| `val:0011` | 冷却 | 失败（50） | 失败（50） | 失败（50） |
| `val:0014` | 加热 | 未知（13；第 14 次请求中断） | 成功（9） | 成功（10） |
| `val:0017` | 双物体 | 成功（25） | 成功（9） | 失败（50） |

两候选共 12 个 episode 均完整结束，六组 Direct／Conditioned 的保存执行条件全部匹配；Direct 单独成功 1 项，Conditioned 单独成功 0 项。No Skill 仅四项完整结束，对每份候选只有四组可比完成记录；不能拿 2/6 当作完整基线成功率，或把连接中断解释为 Skill 优劣。共 16 个完整 episode、2 个中断 episode；没有重跑或替换。

这次小样本没有显示显式条件化策略优于普通同信息修订。Conditioned 在灯光上更短，在双物体上失败，Direct 在该项成功；不能挑选单项优势作结论，也不能由一次差异证明稳定优劣、单项编辑因果或数值预条件化效果。机器可读逐项结果、全部三臂成对核验与费用见 [summary.json](../results/summary.json)，原始和派生操作核验见 [verification.json](../results/verification.json)。

轨迹的离线核对（不回流更新器）：

- 灯光任务中，Conditioned 的第 1–4 步为见碗、取碗、到 dresser、开灯，原生成功。Direct 第 1 步已见碗，第 20 步才取碗；第 8 步非法尝试取灯，第 18 步先开灯未完成，最后第 23 步持碗走到已开启的灯旁成功。因此不能把这项任务概括为“必须以 use 作为最后动作”。
- 普通搬运的 Direct／Conditioned 五步动作和观察逐项相同；No Skill 先用三步查空柜，之后五步与两候选一致。这里没有两种更新策略之间的行为差异；更短的单次搜索不等于稳定效率收益。精确步骤、来源 hash 和可比性核验见[离线观察](../results/early_observations.json)。
- 清洁任务两份候选均在 50 步失败。Direct 没有取物、清洗或放置；Conditioned 第 22、27 步取同一 knife，第 24、31 步放回来源 drawer，第 29 步实际 clean 一次，但没有完成。任务写 `butterknife`，动作对象写 `knife`；只记录可见名称差异，不推断隐藏物体类型或唯一失败原因。No Skill 实际执行 43 步后，第 44 次模型请求连接失败，结果为未知，不能计为 50 步任务失败。
- 在清洁任务中，冻结问题 w3 得到局部支持：Conditioned 在第 6 步看过空 drawer 2，之后第 25、37、49 步再次返回，早先观察已移出两步窗口；局部避重没有阻止这次长周期重访，但短窗口是否为唯一原因尚不确定。w1 只能确认有实际重开，不能证明它是必要恢复；该任务的 w2 看到放回来源但未成功，单凭它不能判断来源禁令的影响。观察问题不是必须产出确定结论的评分表。
- 冷却任务三臂均在 50 步失败，均未取物、冷却或交付；逐步环境返回和合法命令中没有出现目标 plate。Parent 重访空 cabinet 1；Direct 第 37–44 步重复巡查 cabinet 1–4，第 49 步为空动作；Conditioned 第 1–19 步探索 cabinet 1–9，之后仍多次回访。这只能确认搜索未找到目标，不能写成看见目标却忽略，也不能断言环境没有目标或冷却规则执行失败。
- 加热任务给 w2 提供了更具体的边界：两候选都从 fridge 取 tomato，加热后放回同一 fridge，分别在 Direct 第 9 步、Conditioned 第 10 步成功。这证明本批确实出现了任务要求的合法回源，而且实际没有被阻断；但两份 Skill 都写了绝对禁止回源，成功不能证明文字规则已合理条件化或被忠实执行。两者成功也不能与中断的 No Skill 比胜负。
- 双物体任务中，Parent 第 7、25 步完成两次交付，Direct 第 5、9 步完成两次交付。Conditioned 第 25 步只交付第一件，随后第 26–50 步仍在搜索，没有第二次取物或交付；不是“单件后提前停止”。其第 43 步还有一次格式异常造成的非法动作。初始搜索路线和后续执行都不同，不能把该回归定位为 Memory、Fusion 或某一句文本的独立因果作用。

## 预算与成本

总上限为 2 个 Train + 18 个 Selection = 20 个 episode，以及一次 Diagnosis、两侧 proposal／Editor 共 5 次语义调用。实际构造已用满 5 次，没有语义返工。Actor 为 `deepseek-v4-flash`，更新模块为 `deepseek-v4-pro`。参数沿用 temperature 1.0、thinking enabled、reasoning_effort medium、max_tokens 16384、stream false、seed 42、HTTP timeout 300 秒及最多 6 次传输尝试；episode 不重试。

| 构造阶段 | 请求数 | prompt tokens | completion tokens | total tokens |
|---|---:|---:|---:|---:|
| 两项 Train Actor | 100 | 56,538 | 44,025 | 100,563 |
| Diagnosis | 1 | 17,570 | 7,545 | 25,115 |
| Direct proposal + Editor | 2 | 79,297 | 10,275 | 89,572 |
| Conditioned proposal + Editor | 2 | 79,673 | 16,288 | 95,961 |
| 构造合计 | 105 | 233,078 | 78,133 | 311,211 |

包含被拒绝的 Conditioned Editor。Selection 与全程成本如下；构造和派生评价各计一次，格式处理为零模型请求，复用历史来源不重复计费。

| Selection / 全程 | 请求数 | prompt tokens | completion tokens | 已报告 total tokens |
|---|---:|---:|---:|---:|
| Selection No Skill | 191 | 106,349 | 158,459 | 264,808 |
| Selection Direct | 146 | 123,782 | 82,442 | 206,224 |
| Selection Conditioned | 169 | 164,881 | 77,896 | 242,777 |
| Selection 合计 | 506 | 395,012 | 318,797 | 713,809 |
| 含构造的全程合计 | **611** | **628,090** | **396,930** | **1,025,020** |

全程 606 次 Actor 请求、5 次语义调用、611 次 HTTP 尝试，没有追加尝试或 episode 重跑。两次连接中断请求及其 HTTP 用量未知；**1,025,020 是已报告用量之和，不包含这两次未知量，不能写成精确全部消费。** 实际执行为 Train 100 步、Selection 504 步；请求数大于步数来自两个请求阶段中断。Selection 三臂的列表外动作分别为 4、2、1，全部保留。

上述是提供方报告 token，不推算货币费用。五次更新调用消耗 210,648 tokens，完整历史输入仍很重；本次未通过增加字段或额外自证调用解决该问题。不同 Skill 长度及不同执行路径也导致 Actor 成本不同，不宣称等 token 对照。

## 核验与下一步

新定位处理及派生评价有 13 项合成测试；V22 方法测试 244 项、环境接口测试 35 项通过。测试不代表真实方法效果。原构造通过来源、输入、调用、输出、冻结和成本核验，仍保留错误状态；派生评价通过来源、候选不变、任务与用途、实际轨迹、缓存结果、预算和成本核验。两候选原文 SHA-256 分别为 `f16bbfdfa3aa4db8c3b6fec545d1ba28669406c3e2397082e8b9c3d21ff09880` 与 `8e76d87a3de10afa348c3ecdfa5004b80cce6cbbc51fc8cac65b85b0363e9c3f`。

对照本轮开始前的 260 项文件快照，旧 V22 代码、测试、实验产物均未变，仅修改上述设计／协议／索引并追加日志；旧日志 448,334 字节前缀逐字保留。05 原操作仍以 `no_change` 状态通过核验。新增文件与文档链接检查通过；`git diff --check` 仍只报告原有日志第 6619 行末空白，未清理历史行。检查记录见 [preservation.json](../results/preservation.json)。实际未提交源码 hash 由两处运行 manifest 冻结，原操作和派生操作分别核验，不能只用 Git HEAD 代表本次实现。

只读核验入口为 `python -m src.skill_evolution.v22.conditional_trial verify --run-dir artifacts/methods/v22/failure_trial_20261015/run` 与 `python -m src.skill_evolution.v22.reconciled_selection verify --run-dir artifacts/methods/v22/failure_trial_20261015/reconciled_selection`。它们不重跑任务或调用模型。

本次完成了失败反馈到冻结独立对照的链路，但核心作用学习假设仍未得到验证。下一步应先收敛两处机制问题：现有响应认识是否对当前要求提供具体、适用的改变依据，以及 Editor 是否引入了未在有效要求中明确表达的策略变化。恒等仍合法，不为制造变换而削弱初稿；本批 Selection 不继续作为反复调候选的场地。继续围绕失败修复，暂不扩展成功程序提炼、复杂价值判断或长期循环。
