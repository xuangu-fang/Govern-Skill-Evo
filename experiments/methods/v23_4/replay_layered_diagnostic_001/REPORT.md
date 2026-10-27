# V23.4 Replay 分层诊断实验 001

日期：2026-10-22。本目录为隔离实验；八次诊断调用全部完成，不进行新完整 Replay、不发布 Memory、不修改生产机制。

## 1. 结果先行

**目前更支持的解释是：Replay 的不稳定性涉及条件性归纳，以及完整 Knowledge 形成时的事实选择、解释协调与历史校准；“模型看不到事实”或“长上下文导致无法找到事实”不足以解释本轮结果。** 证据定位和最终引用也存在波动，不能排除它们的贡献，更不能给三个环节分配确定的因果权重。

三个关键观察：

1. **定向判断能反复恢复 P6 中丢失或错配的事实。** R05 局部 A、完整 B 各两次，均正确区分当前 Q7:25 与历史 S1_R04/Q6:25，均识别 Parent P8:8 的直接开柜行为，均把 soapbar 的未找到限制在已观察范围，均说明 apple 三步差在取得目标之前。R06 四次均保留 heat plate 的 13 步成功/50 步失败，均保持 cool tomato 的八步搜索差与局部温变相同。完整事实上下文并未使这些核心判断普遍失败。
2. **事实和标题读对之后，结论仍会越界。** R05_B 两次都先读出 Admissible Actions 的全局位置，随后分别写成 pillow 在两项修改范围之外、pillow 没有执行任一新条款。没有非法动作不能证明全局合法动作检查不适用或没有执行。此类偏差不需要假设模型没读到 Diff。
3. **定向问答也不稳定，不能把所有问题推迟到完整 Replay。** R05_A 第二次把 countertop 1 的 candle 3 混进 cabinet 2；R06_B 第一次在正文说对 tomato 动作的同时引用不存在的 Q2:40/Q2:11；第二次把三步 placement 写成五步（五步其实是取得后的完整流程）。旧 Memory 的过强解释虽然在诊断回答中受到限制，却没有每次都被明确校准。

因此，“模型能理解单项证据，但综合任务更易出错”有依据；“只要拆成多个 Knowledge 就解决了”以及“只需压缩上下文”均未获得本轮支持。报告以下区分可直接确认的输出表现与对机制的推测。

## 2. 设计、变量与冻结

调用前冻结 [PROTOCOL.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/PROTOCOL.md)、提取脚本、问题、请求和 [独立标准事实](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/private/standard_facts.json)。标准事实未进入任何请求。分析依据为 P6 实际 HTTP request.body.messages；未用完整归档里未发送的状态补齐历史窗口。

### A/B 内容

| 条件 | 当前完整执行 | 历史完整动作序列 | 保留历史认识 | Evidence 字符数 |
|---|---:|---:|---|---:|
| R05_A | 8 runs / 4 pairs | 8 runs / 4 pairs | M8 原文及全部证据来源，加 T1 历史 candle 两侧 | 290,809 |
| R05_B | 20 runs / 10 pairs | 70 runs / 35 pairs | 原 P6 全部七条 | 884,531 |
| R06_A | 2 runs / 1 pair | 22 runs / 11 pairs | M7/M10 原文及全部证据来源 | 345,508 |
| R06_B | 14 runs / 7 pairs | 58 runs / 29 pairs | 原 P6 全部七条 | 857,205 |

R05_A 保留当前 pillow、失败 butterknife、soapbar、apple 两侧完整轨迹，以及 M8 所有来源和历史 candle 双方；R06_A 保留当前 cool tomato 双方，以及 M7/M10 的全部历史来源。未仅选支持答案的事件；旧的 absence 解释未被修正，多项正负比较保留。当前所有保留 run 的 initial、每一步 before/action/after/feedback、outcome 完整保留，历史完整有序动作/反馈与已有详细窗口原样保留。菜单仅按保留对象的引用去重/选择。

局部 A 是“相关证据子集”，**不是短片段或低上下文条件**：仍约 9–11 万输入 tokens，保留关联 Memory 的全部证据有意增加冗余，以避免挑选单向证据。T1 两个易混事件都在 A；T4 初始候选位置、完整访问顺序与旧解释均保留。B 的 evidence 等于原 P6 User JSON，且原始序列化文本逐字嵌入；A 的每个保留 source/run/entry 均与实际 P6 相等。

两组共用同一诊断 System、同一问题和输出格式。诊断主任务替代 P4 的 Memory 生成主任务；从原 P6 `## Execution Context` 起的 Actor 背景与视图说明原样复用。**所以 B 是完整 P6 事实上下文，不是完全相同的 P6 任务指令。** 不能将 B 与旧 Replay 的差异解释成纯输出粒度因果效应。

问题只要求识别动作、来源、条件、比较和未知，不告知“错配”“目标不存在不成立”等标准答案。不过显式点名 Q7:25、P8:8 和行为阶段必然提供注意力焦点；这是定向诊断与自由学习的关键差异。

输出为隔离 `answers` 数组，每项含 `id/facts(sources,text)/conditions/comparison/conclusion/uncertainty`，不进入生产 Schema。目标约 100–180 英文词/题，没有因超出建议长度而重试或删减原文。

### 调用与重复

模型为 `deepseek-v4.1-flash`，temperature=1、reasoning_effort=medium、thinking.enabled、max_tokens=32768、stream=false；端点、原调用配置与 P6 保持一致，单次传输无隐藏重试。初始顺序 R05_A、R05_B、R06_B、R06_A；之后按调用前登记规则，对出现优先问题错误/重要遗漏或 A/B 实质差异的案例，两侧各补一次。

初始评分在 [initial_evaluation.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/initial_evaluation.json)；补充前冻结 [repeat_plan.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/repeat_plan.json)，依据 R05 T3 与 R06 T4/T5 等触发，顺序为 R05_A、R05_B、R06_A、R06_B。每个条件恰好两次，不按语义好坏选最终答案。八次全部 HTTP 成功、JSON 合法、finish_reason=stop；**零技术重试、零语义失败自动重采样**，四次补充是已注册的稳定性重复。

逐次 [CALLS.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/CALLS.md) 记录 tokens、时长与终止；`runs/<condition>/attempt_00N/` 保留 `attempt.json` 与全部 `parsed.json`，原始 HTTP 请求、响应和启动记录按相同层级存于 [调用归档](../../../../artifacts/methods/v23_4/replay_layered_diagnostic_001/runs/)。

| 指标 | 结果 |
|---|---:|
| HTTP 调用总数 | 8 |
| 输入 tokens 合计 | 1,520,679 |
| 输出 tokens 合计（含 reasoning） | 68,531 |
| 总 tokens | 1,589,210 |
| R05 A 输入 tokens / B | 91,600–91,620 / 284,439 |
| R06 A 输入 tokens / B | 109,445–109,473 / 274,812–274,851 |

相同条件重复请求的 body 完全相同，但服务返回的 input usage 偶有 20–39 tokens 差异；原样记录，原因未知，不据此声称事实输入改变。局部相对完整输入约减少 R05 68%、R06 60%，但这不是效果归因：A/B 同时改变长度、无关来源数量和相关来源的相对显著性。

## 3. 标准事实与逐项评价

完整 [SCORES.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/SCORES.md) 列出 32 个回答的六维评分，每行链接原始输出。[evaluation.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/evaluation.json) 保存原文、JSON 路径、问题引文、标准来源和具体偏差。2=满足，1=部分/有歧义/重要遗漏，0=明确矛盾或不受支持；不计算笼统“正确率”。人工分析非盲评，没有调用评分模型。

| 诊断 | 已冻结事实依据 | A 两次 | B 两次 | 既有 P6 Replay |
|---|---|---|---|---|
| R05 T1 来源 | 当前 Q7:25 合法 go drawer 2；历史 S1_R04/Q6:25 非法 go drawer 8 | 两次核心准确 | 两次核心准确 | 历史动作错归当前 Q7:25 |
| R05 T2 机会 | P8:8 菜单无 go cabinet 3、有 open；实际合法开空柜；Q8:39 仍非法 | 两次识别 Parent 行为；第二次漏 Candidate 后续违规 | 同左；第二次未显式写 Parent 菜单缺 go，但正确区分两侧菜单 | 没保留 Parent 已有直接操作，过宽否定观察到的进展 |
| R05 T3 范围 | 全局 Admissible 与非 desklamp 搜索分属不同范围 | 两次读出并保持边界 | 两次读出边界，随后在结论混淆没有违规与不适用/未执行 | 把范围合并；pillow 多一步纳入搜索解释 |
| R05 T4 soapbar | 未取得/50 步失败；初始 shelf 等未探索；不能证全局不存在 | 两次保留未知；第二次混写 candle 3 的位置 | 两次保留未知；第二次正确引入另一历史 soapbar 成功作为场景差异 | K4 写 absent；与 K3 not found 强度不一致 |
| R05 T6 apple | 14/11，取得步 9/6，后五动作一致 | 两次找到三步搜索差；第一次附带错误称合法动作规则未执行 | 同左 | 总数保留，局部搜索响应没有进入相关认识 |
| R06 T4 butterknife | S1_R05 双方 50 失败；Q 初始 cabinet18 未访问；M10 全局 absent 无依据 | 两次明确全局未知；仍有 search/absence 含混或套用旧 rescue 解释 | 两次明确全局未知；第一次混称中段步骤缺失，第二次 invalid-looking 表述含混 | 新 M12 继承旧 M10 absent 解释 |
| R06 T5 heat plate | P 取得4/加热11/成功13；Q 未取得、未温变、失败50；历史 P2:4 仅动作/反馈可见 | 两次保留不对称；第二次 no observable effect 比局部未触发更宽 | 两次保留；第一次引出条件化 savings 超出本 Pair，第二次边界清楚 | 不对称比较已正确保留 |
| R06 T6 tomato | 18/10，取得13/5；相同后五动作；局部温变零新增节省 | 两次核心准确 | 两次核心准确；第一次引用 Q2:40/11 不存在，第二次 placement 三步写五步 | 核心阶段比较已正确 |

“核心准确”不等于整个回答无错。例如 R05_A2 的物体位置错误没有推翻 soapbar 未找到，但仍是事实错误；R06_B1 的 tomato 正文正确也不能抵消不存在的引用。

## 4. 关键偏差发生在哪一层

### 4.1 来源绑定：原错配可被定向任务消除，但未证明定位问题不存在

当前 Q7:25 和历史 S1_R04/Q6:25 的动作、before/after、反馈在 A/B 中均可见。四次回答分别给出当前 butterknife 合法去 drawer 2、历史 candle 非法去 drawer 8，没有沿用 P6 的跨来源绑定。

**已确认：**模型在完整事实上下文中也能正确区分这两个事件；不能以“历史记录太多所以一定找不到”解释所有错误。**有依据推测：**完整 Replay 的主题选择与写作过程中，来源约束更容易丢失；定向问题点名两事件提供了额外关注。**尚不能判断：**是注意力引导、输出长度、知识任务负担、旧学习 Prompt 与诊断 Prompt 差异，还是采样导致改善。

残余反例是 R06_B1 T6：正文准确说取得5、冷却7、放置10，sources 却列 `Q2:40` 与 `Q2:11`。当前 Q2 只有十步，两个引用确定不存在。[REFERENCE_AUDIT.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/REFERENCE_AUDIT.json) 核对八份输出，仅这一份存在未解析引用。生产引用校验可以拦住这种错误，但 P6 的 Q7:25 是“存在却不支持”，引用存在性检查无法解决。这里不把诊断 schema 的可定位菜单/Plan 别名误当不存在证据。

### 4.2 范围与机会：正确读到标题仍未约束最终结论

R05_B1 T3 的 conditions 已写“search rewrite scoped ... non-desklamp，Admissible Actions sits globally”，结论却写：

> The pillow pair lies outside the operative scope of both changes.

R05_B2 明确写 general action-selection constraint，又称 pillow `does not exercise either new clause`。全局检查在合法行动之前也可以执行；记录没有非法动作只说明未观察到违规，不能反推检查未发生。直接 fallback 的特定触发机会与全局 command verification 应分开。

同类推断在 A1/B1 的 apple 回答中都出现：因为没有非法命令，所以 Admissible Actions 没执行。这说明问题并非只在长上下文出现；也不是标题信息缺失。**已确认偏差位置是从观察到适用/执行状态的推断。** A 的两次 T3 没有该错误，B 两次都有相关错误，提供完整上下文负担的线索，但两个样本且其他问题有双向波动，证据不足以定为长度效应。

T2 的四次均找到 Parent 直接开柜，足以恢复 P6 忽略的能力比较。不过补充两次都集中列 Parent 后续违规，漏掉 Candidate Q8:39。这不是新增虚构事实，却表明**定向问答也会选择性保留比较的一侧**；准确识别某一步不等于比较覆盖完整。

### 4.3 not found 与 absent：能作边界判断，不等于完成历史解释校准

R05 四次都限定 soapbar 未在探索区域出现，并保留未访问位置。R06 四次也都明确全局 butterknife 不存在未被证明。旧 M8/M10 的相关解释仍在输入，标准答案没有告诉模型“这里不能判断不存在”。因此，P6 的 absent 不是由信息不足必然导致，模型具备将证据不足表达为未知的能力。

但 R06_A1 结论仍使用 `search/absence failure`；A2 一边保留全局未知，一边以旧 M10 关于 rescues 的说法解释当前失败。B1 把完整动作序列与详细状态混淆，写 `The unobserved middle steps are missing`，实际中段动作/反馈全在，仅 before/after/menu 未展开。B2 的 `invalid-looking placement` 也应与“动作合法但任务对象错误”区分，按含混而非明确 feedback 造假评分。

**已确认：**定向结论多数能收窄，却没有稳定、显式地将旧 Knowledge 内的事实与解释逐项校准。**有依据推测：**“保留历史认识”与“校准历史解释”的操作没有统一落实；在短回答中也可看到解释残留。**尚不能判断：**这些残留会否在完整数组替换时被保留、删除或修正；本次诊断没有要求实际修订 Memory，不能把它当作跨轮修订已通过。

### 4.4 汇总压缩与阶段计数：局部条件仍会出现新的错误

R05_A2 T4 将 `candle 3, candle 2, soapbottle 2, spraybottle 2` 放在 cabinet 2。正确输入是 P8:3 在 countertop 1 看到 candle 3；P8:6 cabinet 2 只有其余三个。输出仍正确说 soapbar 全局未知。这个新的局部位置绑定错误说明缩小上下文并不保证事实汇总正确。

R06_B2 T6 正确给出取得前13/5、总18/10，却在 placement 段说五步。真正 placement 为 go microwave/open/move 三步；五步是取得后 go fridge/cool/go microwave/open/move。它保留整体阶段差，却在二级阶段命名中移动了计数边界。**错误不在总数读取，而在行为分类与数字绑定。**

### 4.5 heat plate：复杂比较能保持，条件化解释仍可过强

四次都保留 Parent 已找到 plate 并13步成功、Candidate 未到 countertop3、未取得/温变并50步失败。历史 P2:4 只有 trace 动作/反馈，没有详细状态；回答无需补造这一状态即可作出获得目标的判断。

R06_B1 从“Candidate 没有温变机会”转到支持条件化温变 savings。这个失败 Pair 本身只能证明机会不对称，不能证明只要找到目标就节省。A2 的 `no observable effect here` 也比“没观察到温变执行收益”更宽：不能由没进入温变阶段排除整个提示编辑对前序行为的间接影响。B2 则明确不证明 edit 导致失败，也不证明此任务温变改善。

这与 P6 的有效能力一致：重要历史对照可独立保留；但**保留正确比较不自动保证结论恰好落在比较支持的范围内**。

## 5. 三层诊断矩阵与因果边界

逐组 P6 原始引文与路径保存在 [cross_layer.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/cross_layer.json)，引用 R05 attempt_002、R06 attempt_001，没有对旧响应修补。

| 实际观察 | 支持的解释 | 证据强度与限制 |
|---|---|---|
| T1 四次定向正确，P6 错配；T2 四次找到直接开柜而 P6 遗漏 | 具备读取能力，完整学习任务的关注选择/综合绑定可能更脆弱 | 表现已确认；内部环节有依据推测，任务差异与采样仍竞争 |
| T3 B 两次读对全局标题仍作错误机会结论；A1 apple 也有同类推断 | 条件性归纳本身不稳定，非单纯事实检索失败 | 已确认输出中的推断失配；不需假设模型没看到标题 |
| A/B 的 absence 定向结论都保留未知，P6 写 absent | 完整 Knowledge 归纳或旧解释继承可能放大结论 | 跨层差异确认；没有严格隔离自由选题、长度、主 Prompt |
| B1 引用不存在，B2 修复引用但新增阶段计数错误；A2 新物体位置错 | 采样/表达波动与局部绑定问题仍存在 | 已确认两次不同；无法估计稳定错误率或服务端随机性来源 |
| heat plate 四次保持，且 P6 已保持 | 不对称历史比较不是普遍能力缺失 | 已确认本案例；不推广到所有历史修订 |
| B 比 A 更大但核心来源/未知判断普遍正确，B 还能找对另一历史 soapbar 成功 | 未见完整上下文全面破坏核心检索的证据 | 不等于上下文无影响；A仍大、B来源更多、样本少 |

剩余竞争解释至少包括：定向问题提供注意力定位；诊断任务比完整学习少选题、跨 Knowledge 协调与完整修订职责；短输出减少关系丢失机会；P4 主学习 Prompt 与诊断指令不同；temperature=1 下采样波动；上下文顺序/干扰源规模及服务端未暴露因素。不能以本轮确定这些因素的各自贡献。

本轮没有出现足以稳定归类为“局部核心事实错误、完整也核心错误”的 T1 模式，也没有稳定复现“A 正确、B 跨来源身份错配”。出现更多的是事实读对后附带推断过强，或同一回答正确正文配错误引用。因此**证据目前更靠近条件性认识形成与综合校准问题，但尚无法证明它是唯一或量化意义上的主要原因**。

## 6. 对完整 Knowledge 与跨轮修订能说什么

既有 P6 中，R06 修订 M10/M7 时保留 heat plate 不对称比较，正确区分 cool tomato 的局部保持与整体搜索变化；与此同时把 M10 的 absent 解释带进新 M12。R05 新增 Memory，apple 只留下任务数字，成功 butterknife P6/Q6 未被引用，P8:8 也没成为关键 Evidence。

本轮 A/B 并未要求生成 Memory，因此：

- 能确认被遗漏事实可以被模型准确读出，不能确认在自由选择 Knowledge 时它一定会纳入。
- 能确认 absent 可以被收窄，不能确认完整数组替换会保留全部仍有效正反认识。
- 能确认来源存在性审计能找到 Q2:40/11，不能据此验证自然语言蕴含。合法 Q7:25 被错误描述仍需要语义核对。
- 没有重新测试成功 butterknife 的能力保持选择；它不是本轮定向问题，不能拿失败 butterknife 诊断冒充验证成功对照。

Evidence 选择影响下一轮窗口的风险仍在：P6 apple 只引结尾，搜索状态下一轮不展开；P8:8 的菜单未被选中；成功 butterknife 没有进入来源。这些是上一轮确定性投影确认的后果，本轮没有修改引用或窗口来掩盖。多 Knowledge 的独立 Evidence 有助于追溯和局部审查；本轮没有证明它自动执行了事实核对，也没有建立它改善历史修订稳定性的因果证据。

## 7. 下一阶段仅建议两个候选方向

### 方向一：先研究“比较单位与解释强度如何约束最终 Knowledge”

针对共同根因：同一段里先读对事实/标题，最终却把无违规变成未执行、无机会变成无效果、未找到变成 absent，或把旧收益解释套入未触发 Pair。现有 Prompt 已要求范围、机会、因果和历史校准；重复添加同义规则缺乏诊断价值。

候选最小实验：继续使用冻结事实与同一模型，在隔离目录中比较原完整 Replay 与一个**仍单次调用、原输出 Schema**的候选学习任务。候选只改变形成 Knowledge 的决策顺序，要求在已有认识文本中先形成“编辑范围—两侧机会/行为—观察支持的结论”，再组织主题和完整修订；不预填结论、不提供标准答案、不新增审核角色。预先确定有限重复与评分，关注能否同时保持历史重要比较、收窄旧错误解释，以及避免把未触发写成无因果效果。

这是 Replay 学习决策方面的候选实验，**尚不需要改生产机制或增加字段**。即使改善，也只能证明该任务组织在所测案例有益，不能仅由这轮定向问答认定必然有效。可加入一个新的冻结案例检验泛化，避免只适应已知对象。

### 方向二：若仍怀疑关联负担，单独测试来源与比较的呈现位置

针对共同根因：长输入中的来源/局部状态需要跨字段关联，正文与引用可能脱节；但本轮未证明长度主导。最小备选是**完整 Replay 同任务、同事实、同旧 Memory、同 Schema、同模型**下，只重排来源/Pair/已有菜单的相邻关系，保留所有原内容且不加入解释性标签或答案；预注册有限重复。不要同时删减来源、改学习 Prompt、加新字段，否则又难区分因素。

这属于输入组织假设验证，**当前不要求改 Memory v3 压缩算法**。度量来源动作绑定、关键反例覆盖、正文与 Evidence 对应、以及条件性结论是否改善。若仅引用更准而 scope/absence 推断不变，就不应把呈现调整宣称为解决语义学习。存在性审计可作实验读数，但它与语义蕴含不同；已有生产校验职责无须因本轮另建审核模块。

两方向都尚未执行。优先方向一；方向二作为竞争解释对照，而非立刻扩大正式链路。

## 8. 交付与完整性

主要文件：

- 设计与提取：[PROTOCOL.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/PROTOCOL.md)、[design.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/design.py)、[完整输入与请求归档](../../../../artifacts/methods/v23_4/replay_layered_diagnostic_001/config/)。
- 独立标准：[private/standard_facts.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/private/standard_facts.json)，调用前冻结，未发送。
- 调用：[run.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/run.py)、[CALLS.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/CALLS.md)、[全部回答与调用结果](runs/)、[原始调用归档](../../../../artifacts/methods/v23_4/replay_layered_diagnostic_001/runs/)。
- 评价：[SCORES.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/SCORES.md)、[evaluation.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/evaluation.json)、[cross_layer.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/cross_layer.json)。评分脚本只记录人工判断并核对引文，不调用评分模型。
- 完整性：[INPUT_VERIFICATION.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/INPUT_VERIFICATION.json)、[REFERENCE_AUDIT.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/REFERENCE_AUDIT.json)、[AUDIT.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_4/replay_layered_diagnostic_001/AUDIT.json)。

确定性核验通过：A/B 问题、System 与模型配置一致；B 事实全文等于实际 P6；A 保留对象原样、无历史状态扩展；八次实际发送 body 等于冻结请求；没有隐藏重试；受保护的 **12,388 个既有文件哈希未变**。正式 Replay、Memory v3、Preconditioner、P4 Prompt、Active Memory、旧实验和 Actor/Editor 均未修改或重跑。日志内 `semantic_score: not yet evaluated` 是调用完成时的原始元数据，未事后覆盖；最终语义评分独立保存在 evaluation.json。
