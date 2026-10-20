# V22 07：原 Train 响应学习与后续更新验证

日期：2026-10-15。状态：**预声明的有界流程已完成，共 11 个新 Train episode、7 次语义调用；没有新 Selection／Test、语义重试、episode 重跑或候选采用。Skill 修复出现真实正例；历史响应改善下一轮预条件化更新的第二个核心假设尚未得到正面验证。**

## 问题与范围

先检验 06 的不变 Skill 是否改善原 Bread 搜索／冷却和双 CD 交付失败，再检验从这些真实修改中学到的响应是否改变下一轮更新，并由对应失败 Train 的实际执行检验。保留同信息 Direct／Conditioned 对照，暂停新增 Selection／Test，不扩展成功经验或效率优化。

执行前声明见 [plan.json](../config/plan.json)。原始产物根目录为 `artifacts/methods/v22/train_response_20261015/`。原 06 全部产物保持不变；本轮只读取其 Train Parent、两份 Candidate、有效要求和执行前观察问题，Selection 不进入学习或构造。

## 固定协议

1. 两份原文不变的 Candidate 各在 `train:0021`、`train:0034` 执行一次，共四次 Replay；与已有 No Skill 比较，不重造候选、不按结果重跑。
2. 两次反馈学习各从空 Memory 开始，分别绑定 Direct／Conditioned 实际 Skill、diff、Parent 和对应 Candidate 轨迹，保留联合归因、条件、限制和未知。不同 context ID 的新 Effect 原样合并，下一轮两臂读取同一集合。旧照明／清洁认识保留归档，不自动迁移。
3. 固定 `train:0007`、`train:0023`、`train:0036` 各执行一次 No Skill。这是普通搬运、冷却和双物体三个相关更新方向的最小未用 Train ID；元数据关联不等于实际 Effect 适用。只把全部完整失败交给独立 Diagnosis，成功／中断保留且不换题。两组共享初稿和 Memory，使用已有策略及同一个 Editor，冻结后分别在对应失败 Train Replay。

最多 13 个新 episode、7 次语义调用，每 episode 最多 50 步；Actor 使用 `deepseek-v4-flash`，学习与更新使用 `deepseek-v4-pro`，temperature=1，thinking=enabled，reasoning_effort=medium。episode／语义重试为零，客户端有界传输尝试最多六次。没有适用响应时允许 Keep，空学习增量、Diagnosis 停止及构造失败按实记录。

本轮仍以 No Skill 为下一轮 Parent，两份旧候选未采用。这里验证更新器响应认识的跨任务复用，不是完整历史继承或已采用 Skill 的连续发布。两臂共享 Parent，独立学习调用不构成独立实验重复；同信息对照也不单独检验有 Memory 优于无 Memory。

## 原失败 Train Replay

四次 Candidate 执行均完整结束，与对应原 No Skill 的保存执行条件全部匹配。Direct 原文 SHA256 为 `f16bbfdfa3aa4db8c3b6fec545d1ba28669406c3e2397082e8b9c3d21ff09880`，Conditioned 为 `8e76d87a3de10afa348c3ecdfa5004b80cce6cbbc51fc8cac65b85b0363e9c3f`，执行前后不变。事实明细与配对核对见 [original_replay.json](../results/original_replay.json)。

| 原任务 | 已有 No Skill | Direct 原文 | Conditioned 原文 |
|---|---|---|---|
| `train:0021` Bread 冷却交付 | 50 步失败 | 50 步失败 | 50 步失败 |
| `train:0034` 两件 CD 放入 drawer | 50 步失败 | 50 步失败 | 第 50 步成功 |

Bread 三臂均没有在逐步观察中看到目标，没有取物、冷却或交付动作。Parent 导航 37 次／7 个不同位置，Direct 38 次／8 个位置，Conditioned 44 次／8 个位置；两份候选仍出现长周期重复。不能把“搜索未解决”扩写成“冷却或交付规则执行后无效”。三条 Bread 轨迹均无非法动作。

原 CD Parent 第 33 步交付第一件，第 44 步拿起第二件，却在第 50 步把它放回 dresser；另有两次非法取物。Direct 第 46 步才看到 CD，第 47 步拿起、第 49 步交付第一件，第 50 步是 `look`，未进行第二次取物，零非法动作。其交付第二件的策略尚未获得充分执行机会。

Conditioned 第 43 步看到 CD，第 44 步拿起第一件、第 46 步放入 drawer 1，第 47 步回 dresser、第 48 步拿第二件、第 50 步交付同一 drawer，原生成功。第 34 步另有一次非法动作 `examine shelf 3<br>`。返回来源时两步输入仍有先前取物来源信息，无须假定额外长期记忆；但不能据此把成功单独归因于某条规则、一次少犯错或 Fusion。两份联合修改的搜索路线和尾段执行均不同，且每项仅一次。合法回源例外仍未被这两个任务验证。

因此，第一个核心问题已出现一个具体正例和明确限制：这份不变 Conditioned Skill 在原双 CD 失败上完成任务，Bread 搜索仍未改善；Direct 未完成这两项原生目标。原 06 构造并未显示历史驱动要求变换，这次修复也不能倒推为预条件化收益。

## 从真实反馈学到的 Memory

两次 `deepseek-v4-pro` 调用均完成并通过现有结构／来源校验，得到 Direct 三条、Conditioned 两条 Effect。各臂从空 Memory 独立学习，context 分别为 `07_original_direct`、`07_original_conditioned`；合并只拼接不同 ID 的记录，不把重复认识计为独立支持，不合并成未经验证的单规则结论。明细、完整 claim／limits 和原候选身份见 [learning.json](../results/learning.json)。

| Effect | 主要作用认识 | 关键限制 |
|---|---|---|
| `07_original_direct:m1` | 当前“换候选／检查关闭容器”的联合 Skill 在这两任务上仍未完成 | 搜索与搬运打包；Bread 未见目标；仅两个实例 |
| `07_original_direct:m2` | CD 发现后一次目标交付没有放回来源，Parent 则把后一个 CD 放回来源 | 未完成整题；发现太晚、步数预算可解释差异；未实际恢复第二件收集 |
| `07_original_direct:m3` | 两步窗口外的无收益位置仍可能被重新访问 | 只证明这些重访，不能把所有重访都判为违规或有害 |
| `07_original_conditioned:m1` | 双 CD 联合候选完成两次目标交付，Parent 错误放回来源并失败 | 单次配对、联合归因；合法回源条件未测试 |
| `07_original_conditioned:m2` | Bread 中短窗口搜索仍重复，未改善 Parent 同样存在的失败 | 不是已测量的孤立回归；不能据此禁止状态变化后的必要回访 |

离线核对保留原始学习解释的局限：Direct 对关门／重开时序漏写第 35 步第二次关门；第 49 步交付后还有第 50 步 `look`，应理解为未恢复第二件收集，不能解释为毫无交付后观察。Conditioned 的一次成功回访不能证明全局必要性，其 open 对“任务不要求合法回源”的表述也过强；实际只是当前执行未覆盖这一需要。这些解释没有人工回填进 Memory 或送作新的模型指导。

主要活跃 Effect 的条件化观察及限制仍有来源支持。旧照明／清洁 Memory 原文保留，未加入此次共享活跃集合。下一轮两臂消费冻结的同一五条认识，并可据当前证据判定不适用或 Keep；没有强制非恒等变换。

## 预定新 Train 筛查

三项均只执行一次，没有替换或补足失败。详见 [screen.json](../results/screen.json)。

| 任务 | No Skill 结果 | 后续用途 |
|---|---|---|
| `train:0007` Pencil → Desk | 16 步成功 | 仅保留筛查结果，不进入 Diagnosis 或效率学习 |
| `train:0023` Bread 冷却 → CounterTop | 50 步失败，未开始取物／冷却／交付 | 进入共享 Diagnosis 与后续对应 Replay |
| `train:0036` 两件 Keychain → ArmChair | 50 步失败，第 39 步正确交付第一件 | 进入共享 Diagnosis 与后续对应 Replay |

新 Keychain 任务并非旧 CD 的同状态复制：第 36 步看到的 sofa 2 只有一件目标，第 37 步拿起、第 39 步交付后，第 40 步 look，随后继续重复搜索，未找到第二件。旧 CD 的成功不能推出“所有多物体任务都应返回同一来源”；需要结合当前可见目标数量、搜索状态和历史支持条件判断适用性。本段为离线事实核对，不追加给模型作为人工初稿或指导。

## 下一轮：历史是否改变实际更新

一次独立 Diagnosis 只读取两条新失败，返回三项要求：`u1` 按当前／最近两步避免空位置循环，`u2` 根据任务数量继续收集和交付，`u3` 保留已交付对象并避免再次进入空位置。两侧 proposal 的 user 消息逐字相同，包含同一初稿、当前证据和五条 Effect；两侧 Editor 使用同一策略及同一完整 Memory。完整原始决定和要求见 [construction.json](../results/construction.json)。

| 环节 | Direct | Conditioned |
|---|---|---|
| 搜索 `u1` | 用当前证据强调优先检查近期未检查的位置，仍依赖两步窗口 | Keep；理由明确识别历史循环限制，但认为历史不足以支持无需全局访问记录的更强规则 |
| 数量 `u2` | 引用 `07_original_conditioned:m1`，增加“每次放置后检查目的地，直到观察到所需数量” | Keep，认为初稿已包含数量与交付继续要求 |
| 保留 `u3` | Keep | Keep |
| 新观察 | 更新原两项问题 | 增加两步窗口之外仍会循环的 `w3` |
| Editor | 生成文本，明确加入每次放置后 examine；另有额外策略与终止措辞 | 生成较短文本，将空位置回避明确限于当前／两步窗口 |
| 结构／格式 | 通过，无需任何格式修复 | 通过，无需任何格式修复 |

这次 **Effect → 要求 → 文本的非恒等路径发生在 Direct**，而不是 Conditioned。Direct 把成功 CD 的作用认识转成目的地检查，但历史 CD 成功在第一次放置后立即返回来源，并未“每次放置后 examine”；后续再次到 drawer 时才看到先前对象。因此，这条新增强制动作至多是待测探索，不能说已经由历史成功验证。当前 Keychain Parent 本来也没有把一次放置当作整题完成，而是在继续搜索中失败，数量确认未必针对主要失败来源。

Conditioned 读取并讨论了相关历史，不是因为 Memory 不存在而 Keep；但新增观察问题没有改变有效要求。Keep 是合法决定，既不能直接视为机制失败，也不能计作已经展示方向／尺度／关联的实际变换。“没有得到可支持的更强规则”是本次模型的选择，不是所有可执行替代策略均不存在的证明。必须继续区分“历史参与判断”和“历史改变了实际更新”。

Editor 仍有解释边界：Direct 新增显式表面检查、`or when no admissible action can further progress` 终止例外，并把处理类对象写成如 `cool bread`，没有明确冷却前置步骤。Conditioned 也未展开冷却流程，但没有 Direct 那样完整的取物后直接去目的地程序。这些是原始候选的差异或潜在漂移，不在冻结后修正，也不能全部归因于 Fusion。

两份候选在任何新 Candidate Replay 前冻结，Direct SHA256 `315b85c3e028e857882232d6b14a2110b09911bb8ef4658f9ccda54fd0347f92`，Conditioned SHA256 `06c13be63920cb1d9c0a1dada2e7221d02e9467b6f67cd1ea012c0411de1e29c`。随后仅在 `train:0023`、`train:0036` 各执行一次，不增加 Selection、返工或后续学习调用。

## 新候选在对应失败 Train 的 Replay

四次均完整结束，保存的配对执行条件全部一致。没有基础设施未知；Direct Bread 中一次请求较慢但正常返回，不构成重试。具体事件、非法动作和配对字段见 [next_replay.json](../results/next_replay.json)。

| 新失败任务 | No Skill | Direct | Conditioned |
|---|---|---|---|
| `train:0023` Bread 冷却交付 | 50 步失败，未发现目标 | **28 步成功**，0 非法动作 | 50 步失败，未发现目标，0 非法动作 |
| `train:0036` 两件 Keychain 交付 | 50 步失败，已交付一件 | 50 步失败，未发现目标，2 非法动作 | 50 步失败，未发现目标，2 非法动作 |

Direct Bread 第 23 步在 diningtable 1 首次看到 Bread，第 24 步拿取，第 25 步去 fridge，第 26 步 `cool bread 1 with fridge 1`，第 27 步去 countertop，第 28 步交付并原生成功。此前第 14—22 步仍有冰箱／柜子循环，不能称长周期重复已经解决。虽然文本未明确冷却前置步骤，Actor 本次实际完成了冷却，不能把潜在文本缺口说成这条执行发生的错误。

Conditioned Bread 始终未看到目标，仍反复回访 fridge／cabinet。两条 Keychain Candidate 都没有进入目标 Keychain 的取物／交付阶段：Direct 第 34／40 步、Conditioned 第 22／28 步分别有两次非法导航。Conditioned 末尾拿起 box 并检查，未找到目标。这些是整体候选和实际搜索路径的观察，不能孤立归因于 Compiler Keep 或某条规则。相对 Parent 已交付一件，两份候选的实际进度更少；但计数、保护已交付对象及继续收集的规则均没有获得执行检验。

**Direct 的历史驱动要求变化也没有得到行为效果验证。** Bread 放置即终止成功，新增的放置后 examine 没有执行机会；Keychain 根本未进入交付。两条 Direct 轨迹都没有目的地 examine。Bread 的具体修复不能用于证明这条历史作用认识带来的数量检查有效，更不能用于证明 Conditioned 预条件化优势。

## 两个核心问题的当前答案

1. **Skill 更新能否改善原失败？有真实正例，但不是稳定整体改善。** 不变的 06 Conditioned 在原 CD 任务完成两件交付；新 Direct 在本轮 Bread 失败上完成完整冷却交付。其他失败、未覆盖分支，以及 Keychain 的进度退化全部保留。
2. **真实响应能否帮助下一轮形成更合理的预条件化更新？链路已执行，收益尚未证明。** 五条 Effect 确实进入同信息更新；Direct 出现了可追溯的历史→要求→文本变化，但具体新增动作超出旧成功直接支持的范围，且本轮未实际触发。Conditioned 识别相关限制后 Keep，只改变观察问题，没有实际要求变换。这既不是“Memory 无用”的证明，也不能报告为预条件化已有效。

本轮暴露的核心机制问题是：**当相关历史已经显示初步策略不足时，何时应保留它，何时应提出符合 Actor 能力、范围可控的替代策略，并明确将其作为待 Replay 的探索？** 当前 Conditioned 把限制转为 watch 后保留原要求，Direct 则从历史成功引出了未经直接验证的新强制动作。下一阶段应优先研究这个更新决定边界及实际触发机会，而非增加 Memory 字段、扩展成功经验或恢复泛化评价。这是后续研究问题，本轮没有据结果修改算法或重跑案例。

最后四条执行另按既有契约组装为 `artifacts/methods/v22/train_response_20261015/next_feedback/{direct,conditioned}.json`，保留真实要求、Skill、diff、观察问题和配对来源；仅保存反馈，不增加模型学习、不回写当前五条 Memory，也不采用候选。

## 成本、复现与核验

预算为最多 13 个 episode、7 次语义调用；实际 11 个 episode（原候选 4、新 No Skill 筛查 3、新候选 4），7 次语义调用（真实反馈学习 2、Diagnosis 1、proposal 2、Editor 2）。所有新 episode 完整结束，语义调用均返回合法产物。已使用来源不重复计费，旧失败及 Selection 仍保留原记录。

| 阶段 | 新 episode | 语义调用 | 计费说明 |
|---|---:|---:|---|
| 原 Train Replay | 4 | 0 | 复用原 No Skill 与旧候选，不重复计构造费用 |
| 分臂 Memory 学习 | 0 | 2 | 85,406 tokens |
| 新 No Skill 筛查 | 3 | 0 | 成功实例虽不学习，执行费用仍计入 |
| 同信息更新构造 | 0 | 5 | 168,257 tokens |
| 新候选对应 Replay | 4 | 0 | 全部成功／失败结果计入 |

合计 **494 次 Actor 请求、7 次语义调用、501 次 HTTP 尝试，已报告 837,947 tokens**（prompt 611,065；completion 226,882），未知用量为 0，实际没有传输重试。分阶段完整费用及结果见 [summary.json](../results/summary.json)。同调用上限不等于实际 token 或推理耗时相同；一次协议匹配的执行不能消除采样差异。

Git HEAD 为 `7d4749541dab04397ea146e56dc762a26ba81a3b`，有原先未提交的 V22 工作，实际源码由执行前绑定和候选冻结 hash 识别。Actor 为 `deepseek-v4-flash`，更新／学习为 `deepseek-v4-pro`，temperature=1，max_tokens=16384，thinking=enabled，reasoning_effort=medium，stream=false；沿用原 ALFWorld 协议与两步历史能力，每条件只运行一次。

新增 [Train 构造薄入口](../../../../../src/skill_evolution/v22/train_response_update.py)和[实验编排](../config/run.py)，复用原学习、更新、执行与核验函数；既有 Diagnosis／Memory／Fusion／Editor 语义提示和输出契约未修改。新入口组合已有两种仅格式归一化政策，但本轮两份新 Editor 均无需修复。

离线重建两份学习输入、五条 Memory、当前独立 Diagnosis 输入、初稿／有效要求、同信息消息、Editor 文本／diff、执行前观察与冻结来源，核验通过；全部新轨迹仅为 Train／learning。V22 方法 **252 项单元测试通过**，其中新增 8 项测试覆盖同信息、格式保持、合法停止和失败边界。核验结果见 [verification.json](../results/verification.json)；这些检查不替代上文的语义和机制判断。`git diff --check` 仍报告原有实验日志第 6619 行尾随空白，未因本轮工作修改旧记录。

原 06、旧 Memory、既有源码、测试及历史结果的保存核对见 [preservation.json](../results/preservation.json)。本轮仅更新 V22 定位／结果索引并追加日志；未修改 v19、v20、v21，也未改写旧实验结果。
