# V23.2：历史 Memory 与 Preconditioner 更新决策核查

日期：2026-10-19。来源仅为正式 V23 六轮优化实验 `artifacts/methods/v23/v23_alfworld_formal_001/S1/`。本次为历史证据研究，无新模型请求、环境运行、Candidate 或 Active Memory 写入；未读取最终 Test 轨迹，未使用三次 V23.2 实验输出作原始证据。

**主要发现：历史限制通常已经被读取并复述，约束作用主要减弱在“对具体修改的适用解释 → Keep／Adjustment 决策”之间。** 搜索覆盖的局部收益，被用来支持并未被历史验证的具体搜索方式；“仍会循环、收益依赖覆盖到目标位置”的反例，又被压缩为“不保证治愈”，没有充分约束新策略的顺序、范围和效果承诺。R06 是最强证据；R03 是部分调整但解释过满；R05 的 Keep 有当前证据与后续收益，不能直接判错，只能指出论证没有充分处理混合反馈。

Memory 并非没有用：R04 的温度更新存在明确的历史引用、实际策略变换与对应行为；R05 精确类别及 R06 温度更新的 Keep 也有合理依据。但 Memory 自身有事实粒度和跨轮混淆问题，须单独归责。尤其 R06 后形成的 M13 存在明确错误，不能倒推成 R06 Preconditioner 的输入问题。

## 1. 证据边界与时间顺序

以各阶段 `result.json` 指向的真实有效 attempt 为准。完整来源入口、57 个任务的配对结果及原始轨迹链接见 [SOURCES.md](SOURCES.md)，机器可读路径和时序见 [index.json](index.json)。文中 `R03/P2:15` 表示 R03 的 Parent 执行 P2 第 15 步；同名 P/Q 在不同轮次不是同一执行。

核对了六轮 Preconditioner 的保存输入、渲染消息、原始响应和确定性编译结果；输入 Memory 与该轮 `round_input.json` 及前一 Active Memory 快照一致。246 个历史 source 引用与其原轮次 Diff／配对事实相等；114 条 Parent/Candidate 原始轨迹逐步核对 action、返回观察和 won。Replay 的 Plan 投影按现有协议去除 Update basis，行为文本和 Checks 不变。此核验只确认证据链一致，不把结构合法当成语义正确。

| 调用轮次 | 当时 Parent | 当时实际可见 Memory | 本轮执行之后才形成 | Gate |
|---|---|---|---|---|
| R01 | 无 Skill | 空 | M1、M2 | ACCEPT 9→10/10 |
| R02 | R01 Skill | M1、M2 | M3 | ACCEPT 6→7/10 |
| **R03** | **R02 Skill** | **M1、M2、M3** | M4、M5、M6 | **RETAIN 7→6/10** |
| R04 | R02 Skill | M1–M6 | M7 替代 M4；M8 替代 M5；新增 M9 | RETAIN 7→6/10 |
| **R05** | **R02 Skill** | **M1、M2、M3、M6、M7、M8、M9** | M10 替代 M3；M11 替代 M8 | **ACCEPT 7→9/10** |
| **R06** | **R05 Skill** | **M1、M2、M6、M7、M9、M10、M11** | M12 替代 M10；M13 替代 M7 | **RETAIN 6→5/7** |

R05/R06 的 `val:*` 属于正式协议的优化池 Selection 任务，不是最终 Test。RETAIN 保留 Parent，但不取消对该轮 Candidate 的经验记录。因此 R03/R04 的温度指导虽然进入 M4/M7，却没有进入 R05 Parent；R05 实际 Diff 也没有添加温度流程。R06 再提出温度更新，不是简单重复已经落地的有效条款。[各轮源文件](SOURCES.md)

## 2. Memory 实际学到了什么

这里的“支持”区分观察到的行为与独立因果证明。各轮均是多项修改联合应用、每任务单次执行；不同任务实例间的目标位置也不同。不得将整份 Candidate 的成功变化归给某一条 Update。

| Memory／来源 | 真正的历史编辑与正向观察 | 反例、条件与总结核查 |
|---|---|---|
| M1、M2／R01 | 新增 desklamp 共址流程，并要求保留普通搬运；lamp 任务 4→5/5，普通搬运两侧均 5/5 | M1 保留实际步骤顺序并非一致；M2 不将所有步数改善归因于 lamp 编辑。与 R03 温度／搜索策略关联弱，主要是保存已有行为的背景；不能因未引用就算忽略相关经验。[R01](SOURCES.md#r01) |
| **M3／R02** | 同时新增一般检索、开容器、避免即时回访、精确目标、按需清洗与直接放置。P5 用 soapbottle 替 dishsponge 并失败；Q5:19–24 到 bathtubbasin 找到真目标、清洗并成功 | P4/Q4、P6/Q6、P8/Q8 均 50 步失败；开容器在原已成功任务也增步（4→8、4→7、9→10）。M3 保留了收益仅一对、条款捆绑、反循环未稳定遵守、lamp 边界未被测试等限制，整体忠实。`did not by itself break` 不能理解成做过单条款消融。[R02](SOURCES.md#r02) |
| **M6／R03** | 搜索条款改为当前／近期观察、具体开容器与扩大位置覆盖；同时改精确类别和温度。bread P4 失败，Q4:12–17 在 diningtable 找到目标并成功 | bread P2/Q2 从成功变失败；plate P6/Q6 从成功变失败；Q6 到第 49 步才取到 plate。M6 保留正反例、6 对 7 的整体结果与随机性／捆绑限制，没有把覆盖收益说成稳定解决循环。小误述：`falling back to a no-op` 对应 Q6:4 等 `Nothing happens`，但原始 `fallback=null`，应区分环境无效果与程序 fallback。[R03](SOURCES.md#r03) |
| M4→**M7**／R03→R04 | 条件是已找到精确目标；直接持物 heat/cool，减少插入和门切换。R03 pot/apple/egg 两侧均成功且 18→11、35→9、40→15 步；R04 potato/tomato 为 14→7、21→7 | M7 保留“找不到目标时无机会生效”，是较有针对性的条件经验。总体步数还包括搜索差异，不能全归温度条款；`robust reduction` 仍限于这批单次轨迹。其“exact mug was absent”等绝对表述超过“本轨迹未找到”的可证范围。[R03](SOURCES.md#r03)、[R04](SOURCES.md#r04) |
| M5→**M8**／R03→R04 | 明确不拿 pot 替 pan、不拿 cup 替 mug。Parent 操作近似物体，Candidate 留下近似物体继续搜索 | 相应任务两侧仍失败，避免替代与成功不是一回事。M8 明确保留无独立成功收益和联合编辑限制；但从“未找到”扩大到“确切目标不存在”的表述不够严谨。R03 的 M5 原文较谨慎地写了 `absent from the inspected locations`。[R03](SOURCES.md#r03)、[R04](SOURCES.md#r04) |
| **M9／R04** | 新增多实例计数和有源处证据时回源；newspaper 两侧 10 步成功，saltshaker 10→9，candle 30→34 | cd 和 keychain 两侧失败，循环仍在；没有成功率净增。保留精确数量行为有证据，不能证明原策略之外的普遍回源／进度恢复能力。R05 当前 Updates 不主攻多实例，不强制据此改 Plan；R06 的保留多实例边界与它相关，但 reason 没有显式处理。[R04](SOURCES.md#r04) |
| **M10／R05，替代 M3** | 实际 Diff 明说 `spreads across distinct receptacle families rather than exhausting or looping over one type`。Q6 到 countertop 2 找到 butterknife，Q8 到 shelf 1 找到 soapbar：两次失败转成功 | Q7 仍失败且循环；Q10 虽成功却 38→46 步，重访仍多。M10 记录这些限制。但其总括 `two additional successes ... in a family the Parent never reached` 过度概括：P6:3 已到 countertop 1，Q6:16 扩大的是同类位置覆盖；只有另一对可明确说新增 shelf 类别。局部事实段仍写对 countertop 2，故是总结粒度错误，不是整条来源失真。[R05](SOURCES.md#r05) |
| **M11／R05，替代 M8** | 精确类别原则扩展到 knife/butterknife 等；P7:5/7/9 取、洗、放 knife，Q7 没有替代；Q6/Q8 能处理真正目标 | P7/Q7 仍失败；M11 明确不能把两次搜索救回单独归因于类别条款。存在与 M8 类似的“未发现→不存在”措辞，不能据此把失败都解释成无目标。[R05](SOURCES.md#r05) |

**重要区分：M6 已包含“目标真实存在，但 Candidate 没覆盖到”的反例。** R03 P2 找到 countertop 3 的 bread，P6 找到 cabinet 9 的 plate；这些不是仅在“没有目标”时循环的无关反例。因此后续将其概括成“搜索不保证治愈”不能替代对覆盖方式的具体检查。

## 3. 逐 Update 的历史利用对照

三轮共 7 项 Original Updates，不把 Keep 自动当错误，也不把有 Adjustment 自动当利用成功。表内引用的文本均来自当轮真实 Preconditioner／Effective Plan；链接同时提供 Diagnosis、实际 Diff 与轨迹。

| 轮次／Update | 相关 Memory 与历史实际反馈 | Preconditioner 理解 | 最终 Update／Editor 变化 | 核查判断 |
|---|---|---|---|---|
| [R03 u1](SOURCES.md#r03) 精确类别 | M3 的搜索＋精确目标联合收益；M1/M2 不提供同策略反馈 | reason 说当前 runs 支持 exact-target，未单独把 M3 连到 u1 | Keep；Diff 扩写 pot/pan、cup/mug 和温度动作的 no-substitute | 当前 P5/P10 有充分新证据，Keep 合理；不能声称已证明由 Memory 导致。不得用本轮后才有的 M5/M6 为当时补理由 |
| [R03 u2](SOURCES.md#r03) 温度 | 当时没有 M4/M7 温度经验 | 依据当前 P5:33 等，将“先开门”改为 explicit action 可用就直接执行 | 有实质 Adjustment；Diff 第 4 步落实直接动作和按需开门 | 有依据的变换，但主要是当前证据贡献，不能包装为历史 Memory 的成功案例 |
| [R03 u3](SOURCES.md#r03) 搜索 | M3：扩大覆盖有一例联合收益，局部反循环仍未稳定遵守 | 明确引用 M3；把不回访称为 abstract，并声称改成 `observable local choices` | 调整掉显式 `track progress`，增加不同列出位置／具体拓展；仍保留 uninspected/unvisited，Diff 也写入这些要求 | Memory 产生了可见影响，非忽略；但 R02 被测试条款本来已含即时局部反循环，“更具体”未充分解释为何改变已失败响应。最终仍混合旧要求，解释过满 |
| [R05 u1](SOURCES.md#r05) 精确类别 | M8：不操作近似物体，但不保证找到目标 | `matches ... historical M8`，结合当前 P7 的 knife 错误 | Keep；Editor 在一般步骤 2 落实 exact category 确认与新近似类别 | 策略、条件和目标行为对应，合理 Keep；Q7 不再洗 knife 但仍失败，恰与历史条件性收益一致 |
| [R05 u2](SOURCES.md#r05) 跨类别 sweep | M3/M6：覆盖偶有收益，循环／漏查／增步仍出现 | 明说 `imperfectly followed`，随后 `do not justify a different executable strategy or withdrawal` | Keep；Diff 将旧广义搜索改为不耗尽单一类别的 single-pass family sweep | 新 Plan 确有策略差异且当前 P6/P8 支持扩大覆盖，不能判 Keep 必错；但 reason 未解释此差异为何应绕开已知失败，也未处理条件／强度层面的调整可能性 |
| [R06 u1](SOURCES.md#r06) 温度 | M7：已获得目标后，持物处理减少无效操作 | 明确 `M7 corroborates the direct holding-conditioning benefit`，加当前 P4/P5 证据 | Keep 原始更新；Editor 把温度处理并入一般第 3 步，非沿用之前被 RETAIN 的 Skill | 有条件匹配依据的 Keep；后续部分遵守不等于事前 Keep 错误，也不能把当前总步数下降写成完全遵守 |
| [R06 u2](SOURCES.md#r06) 类内升序到穷尽 | M6 的漏查反例；M10 的 family-spread 收益与仍循环／增步 | 已区分 `support ... as a direction` 与 `not a guaranteed cure`，但仍断言两项都 executable、无需调整 | Keep；原文 `When the current family is exhausted ... switch`；Diff 删除“不耗尽一类”，改 `work through one family at a time` | **证据最充分的判断缺口**：方向支持没有证明“先穷尽一类”这种相反调度；没有解释为何移除此前支持的覆盖边界。当前循环证据也不能独立证明升序穷尽优于原策略 |

未发现这些重点更新主要在 Editor 阶段被悄悄改成另一方向：R03、R05、R06 Diff 基本落实了 Effective Update 的操作要求。Diff 中仍保留若干 Parent 条件（如全候选检查一次的终止句），不能误称都是该轮新增。R06 `one family at a time` 是 Diagnosis 已提出的 family exhaustion 的展开，问题在上游已存在，不宜全归 Editor。

## 4. 六个重点案例

### 案例一：R02 M3 → R03 搜索调整——识别了限制，仍高估改写的作用

**历史修改与响应。** R02 Diff 同时追加开容器、精确目标、反即时循环等；P5 失败，Q5:19 到 bathtubbasin、20 取 dishsponge、22 清洗、24 放置成功。但 Q5 在首次到 bathtubbasin 前也已重复访问多处；Q4/Q6/Q8 仍失败。M3 据此保留“覆盖＋精确目标联合有效”和“反循环未可靠遵守”两面，而非认定全流程已改变。

**当前更新与决策。** R03 Original u3 明确 `track progress within the execution`。Preconditioner 引用 M3，说不应依赖 abstract no-revisit，应改局部选择；Adjustment 去掉 track progress 并增加选不同已列位置、开闭容器与拓展目标。Effective u3 仍有 `inspect uninspected drawers`、`unvisited listed location`，Editor 搜索段忠实加入。即便暂缓能力问题，也能看到另一个独立缺口：R02 已写 `Do not immediately revisit an already-open receptacle that visibly lacks the target`，历史失败不是仅因缺少局部措辞。新范围拓展可能有用，但不能仅凭“更加具体”认定旧反循环失败已被处理。

**随后观察。** Q4:12 去 diningtable，13 取 bread、17 成功，确有覆盖改善；Q2 从未去有 bread 的 countertop 3，P2:15–20 却成功；Q6:4/10/15 等仍无效移动，第 49 步才取 plate，P6 第 38 步已完成。7→6 来自一修复、两退化，不是搜索每处都变坏。形成 M6 后完整保留这组混合证据。**判断：部分历史转化成功，改写的充分性解释过强；不能证明改写造成两项退化。** [证据链](SOURCES.md#r02) → [R03 Plan／调整／Diff／配对](SOURCES.md#r03)

### 案例二：R03 温度响应 → R04 实际调整——历史反馈有效利用的正例

**历史与 Memory。** R03 u2 的变换来自当前证据；实际 Q8:7 直接 heat apple、Q9:13 持物 heat egg，对照 Parent 的插入、门切换、延后处理，形成 M4。该经验明确只在已经找到真目标时适用，不把整轮 RETAIN 视为温度方向无效。

**R04 决策与落实。** R04 Preconditioner 在 u1 的 basis 明列 M4、M5，reason 为 `Historical Memory M4 supports applying the explicit heat/cool action while holding the target without insertion or door toggling`。Adjustment 强化 exact-target 和温度动作 timing，最终 u1 明确动作可用就持物执行，Editor 实际新增 temperature-conditioned placement 第 5 项。R04 Q3:5/Q4:5 均直接加热，Q3/Q4 都 7 步完成，Parent 分别 14/21 步；形成 M7。R04 同时有搜索失败导致整轮 7→6 RETAIN，并不抵消条件性行为证据。

**判断。** 这是“历史特定动作响应 → 当前相同条件下的具体要求 → 实际 Diff → 对应行为”的正向链条。当前 P1/P4 等也支持调整，缺少无 Memory 对照，所以只能证明归档文本明确使用历史且转化有依据，不能量化 Memory 的独立贡献。[R03](SOURCES.md#r03) → [R04 原始与调整后 Plan、实际 Diff、轨迹](SOURCES.md#r04)

### 案例三：M6 → R05 u2——Keep 有理由，但混合反馈的约束论证不足

**历史关联。** M6 记录的是“具体扩大覆盖＋反即时循环＋预算较高时偏好新位置”，和当前“跨类别 single-pass、不耗尽单一类型”有相同覆盖方向，但不是同一具体调度。M6 既有 diningtable 成功，又有同任务对里漏 countertop 3、较晚到 cabinet 9 的失败。

**当前更新与理由。** Diagnosis 已在 u2 提出 `spreads across distinct receptacle families rather than exhausting or looping over one type`。Preconditioner 说 M6/M3 的规则 imperfectly followed，但不足以支持其他 executable strategy 或撤回，因此全部 Keep。当前 P6 反复回访后又连续开 drawer 3–19 直至预算耗尽，P8 漏 shelf，支持覆盖改善；新 u2 相对旧 Skill 有变化，不能只因引用负例便要求撤回。

**欠缺在哪里。** reason 没有解释“不耗尽一类”如何回应 M6 的具体漏查／较晚发现，也没有区分不支持“另造策略”与可支持缩小效果承诺、限定范围的不同决策。它保留了完整 single-pass／回访前覆盖要求，却仅以“历史不能证明应撤回”处理限制。这是论证不充分，不是已证明 Keep 最优或错误。

**已观察结果。** Editor 实际改搜索第 1 步并同时改精确类别第 2 步；P6/Q6 50→21（Q6:16 countertop 2）、P8/Q8 50→23（Q8:18 shelf 1）为两次救回；P7/Q7 仍 50 步失败。原 7 项成功全部保留，**没有成功→失败的退化**；效率方面 P5 5→6，P10 38→46，且 Q10 反复回访后第 40 步才到 diningtable。M10 记录这些局限，因此 ACCEPT 不是每条更新及每项要求被验证有效。**判断：有依据的新尝试和真实收益；历史限制对具体强度／条件的约束仍未被论证清楚。** [R03/M6](SOURCES.md#r03) → [R05 完整证据](SOURCES.md#r05)

### 案例四：M8 → R05 u1——合理 Keep，行为收益与成功率分开

R03/R04 的 no-substitute 编辑让 Candidate 不再操作 pot/cup 代替 pan/mug，但没有把未找到目标的任务变成功；M5→M8 保留条件性与归因限制。R05 当前 P7:5/7/9 又出现 take/clean/place knife 代替 butterknife，Diagnosis u1 将确切类别检查扩展到取、处理和放置之前。

Preconditioner 用当前错误与 M8 的相同作用方式支持 Keep；Effective 原样，Editor 第 2 步落实。Q7 看到 knife 后继续搜索，没有对应取洗放动作，但仍 50 步失败。与此同时 Q6/Q8 能获取正确类别并成功，未观察到规则阻止真目标处理。M11 将经验扩展到清洗／放置任务并保留两项编辑共同应用的限制。

**判断：历史关联与适用边界合理，Keep 不是未利用历史；可支持“避免无效替代”，不能单独支持“提高搜索成功”。** 同理 R03 u1 的 Keep 有当轮证据，但当时只有 M3，不能用后来 M8/M11 解释其决策。[R03](SOURCES.md#r03)、[R04](SOURCES.md#r04) → [R05](SOURCES.md#r05)

### 案例五：M6/M10 → R06 u2——方向支持没有约束策略反转

**历史证据。** R05 实际 Diff 强调不耗尽一种类型，M10 记录两次救回、Q7 持续循环及 Q10 增步。M6 更早已有“目标在可达位置，但 Candidate 未有效覆盖”的负例。两条经验同时存在，未因 M10 更新 M3 而丢掉 M6。

**新策略。** R06 Original u2 改为类内升序，`When the current family is exhausted ... switch`，并称 fixed order 能 `guarantee progress`。其 basis 中 P3 的循环证明当前搜索有问题；P1:34、P2:8 是到 countertop 2 找目标，并不独立验证类内穷尽策略。尤其 P1 已经历长时间柜子检查后才到 countertop 2，不能从最后成功推出此前搜索顺序优越。

**决策落点。** Preconditioner 精确写出 M6/M10 只支持 sweep `as a direction even though it is not a guaranteed cure`，却 Keep 整份 Plan；既未解释从“跨类分散、不耗尽一类”改成“穷尽一类再切换”的依据，也未调整 guarantee 表述。Editor 随后明确把旧句替换为 `work through one family at a time`。这是历史限制被识别、但未影响关键策略取舍的直接文本证据。

**当前行为。** Q1 开完 cabinet 1–9 后仍回访，最终 39 步与 Parent 40 步相近；P3/Q3 均失败；P6 第 17 步到 bed、24 步放完两本书，Q6 从未到 bed，持续 drawer/shelf/desk 搜索至 50 步失败；P7 先到 desk、10 步完成，Q7 开 drawer 1–10 后取 card，28 步完成。故整轮 6→5，没有新搜索成功救回。Q7 显示部分升序行为与增步同现，Q6 显示遗漏开放家具；Q1/Q3 仍不完全按固定序列走。**不能声称“完全执行升序算法造成退化”**，实际是局部顺序变化、持续不遵守与遗漏同时存在，且温度更新捆绑、无重复试验。

本轮后 M12 才明确总结新强度有遗漏家具、额外开抽屉且无明确救回；它修订 M10，不能视为 R06 事前已知结论。**判断：三轮中最明确的历史解释／更新决策问题；其后反馈强化风险认识，但未证明独立因果。** [R05 实际 Diff／M10](SOURCES.md#r05) → [R06 全链](SOURCES.md#r06)

### 案例六：M7 → R06 u1，以及之后的 M13——合理保留与 Memory 错误分开

**事前合理性。** M7 的直接持物温度处理在 R03/R04 有相同动作条件下的行为依据。R06 Parent 是只改了搜索和精确类别的 R05 Skill，尚无该温度流程；P4/P5 有真实门切换和插回，且 P4 到 microwave 时持物 heat 动作可用。Diagnosis u1 与 M7 实现方式匹配，Preconditioner Keep，Editor 合并到一般第 3 步，有充分依据。

**实际反馈。** R06 Q4 仍 open→insert→close→open→take→heat（5–10 步），13 步放到 fridge；P4 是 22 步。Q5 同样插入、开关再取出，12 步完成，Parent 18 步。减少重复操作不等于完全落实 no-insert；两侧还选取了不同 source/target instance，因此总步数差不能全部归因于温度条款。P1/Q1 与 P2/Q2 都使用显式 cool 并成功，P3/Q3 未找到 apple，无法验证该条件动作。

**明确的 Replay/Memory 认识错误。** R06 后的 M13 把当前一对写成 `heat-tomato-to-countertop`，称 Parent P4:21 放置、Candidate Q4:5 在关闭微波炉处直接加热且 Q4:7 放置。原始事实是：任务到 **fridge**；P4:21 是 go to fridge，22 才放；Q4:5 是 **open**，7 是 **close**，10 才 heat，13 才放。它所描写的 countertop、Q4:5 heat、Q4:7 place 与 **R04** 那一对吻合。可以确认跨轮事实混写；不能确认模型内部具体如何混淆。引用 ID 可解析不代表所述动作正确。

**判断：这次 Keep 仍合理；未完全遵守应如实进入历史。M13 是另一个明确的 Memory 总结错误，只影响未来潜在输入，不能拿来解释 R06 当时的 Keep。** M13 对 Q5 部分不遵守的记录是对的，不能因此把整条 Memory 全判无效。[R04 原行为](SOURCES.md#r04) → [R06 原始轨迹、Replay、M13](SOURCES.md#r06)

## 5. 跨轮共同问题与归责

| 观察到的问题 | 证据强度与定位 | 不应扩大成的结论 |
|---|---|---|
| **覆盖方向的收益被用于支持具体调度** | R03 “局部具体化”、R05 Keep、R06 类内穷尽均引用覆盖历史；R06 与旧 Diff 的顺序边界相反，是最强例。主要在历史关联粒度、解释和决策 | 不能说全部搜索 Keep 都错误，也不能说历史证明某种新策略必败 |
| **已承认反例，但没有解释其对当前修改的具体含义** | R05 `imperfectly followed` 后转向“不能证明应替换／撤回”；R06 `not a guaranteed cure` 后保留 guarantee。限制成为理由中的附注，未约束强度／顺序 | 反例本身不要求必须产生 Adjustment；合理 Keep 也可以成立，关键是当前差异和支持边界须说得通 |
| **“仍未遵守”被当成可通过再具体化解决的现象** | M3、M6、M10 连续记录循环未破；R03／R06 又加局部措辞／顺序。没有说明新增内容与此前已失败指令的关键差异 | 无法由单条轨迹判定是不理解指令、受限信息、探索随机性或其他原因；不恢复第一项能力优化 |
| Memory 总括丢失事实粒度或范围 | M10 把新 location 概括为新 family；M7/M8/M10/M11 的部分 absence 说法超出轨迹可证范围。会使历史适用性更难判断 | 未证明这些措辞实际导致 R06 决策；完整来源仍可读，不能把判断责任全部推给 Memory |
| Memory 跨轮混写 | M13 的 R06 Q4 动作／任务与原轨迹直接不符，像 R04 内容；这是已确认事实错误 | M13 在 R06 之后才形成，不是三轮 Preconditioner 失误的前因 |
| Editor／编译是否丢失历史调整 | 原响应到 Effective Plan 的确定性编译一致，所核查 Diff 主要忠实落实既定策略，未见共同故障在这里 | 语义并非因 JSON 合法而自动正确；Parent 保留条款也须区分来源 |
| Memory 的独立因果收益 | R04 有明确引用与策略落地正例，R05/R06 也有合理 Keep | 没有同材料去 Memory 对照、独立编辑消融或多次重复，无法证明每项选择由 Memory 导致，或量化其净收益 |

就本次三条搜索更新链而言，重复出现最多的是**保留高层覆盖方向、承认低层执行局限，却没有稳定地将局限转换为对当前具体修改的约束**。这不是统计意义上的总体频率结论，也不意味着 Memory 被完全忽略。R03 调整、R04 历史温度变换及 R05 精确类别 Keep 都反驳“历史完全无用”的说法。

还需区分“历史限制反复存在”与“每轮都原样忽视”：R03 确实改了策略；R05 又改变跨类安排且出现两次救回；R06 则引入与历史受益条件不一致的调度。这些是不同程度的利用不足，不是同一段规则被机械复制三次。

## 6. 少量后续研究方向（不在本次实现）

1. **优先让历史支持落到当前修改的具体差异。** 区分历史支持的改善目标、实际被测试的策略及适用条件，重点研究“为什么这一实现／范围／强度得到支持”。R06 表明仅说明方向合理并不足以保留反向调度；不需要预设新的匹配模块、评分或字段。
2. **研究混合反馈如何约束 Keep 与 Adjustment。** 对已出现的漏查、较晚发现、额外步骤及不遵守，判断当前新证据是否改变了适用关系。允许合理 Keep，也允许方向不变但调整范围／实现；避免把“负例不足以否定方向”直接等同于“原始实现无需变动”。效果承诺也须与证据强度一致，而非只在 reason 保留免责声明。
3. **后续轻量处理 Memory 的来源与事实边界。** 针对已确认的 location/family 混淆、未找到/不存在混淆及 M13 跨轮事实错误，优先保留轮次和观察范围的准确性。属于后续事实概括改善，不在本次修 Replay、改 Memory 或扩大为复杂审核系统。

这三项方向来自现有文本与轨迹的具体缺口，不是已经验证有效的新方法。当前最值得优先研究的是 Preconditioner 从**历史响应的支持范围到当前 Update 取舍**的转换；事实概括错误单列，Actor 信息能力问题继续暂缓。无证据支持把统一撤回、所有 Keep 强制调整或独立审核 Agent 作为必需方案。

## 7. 完成与保护

只新增独立分析目录中的本报告、来源索引、轻量只读提取脚本和核验记录。脚本调用现有只读加载／编译校验，不运行 Editor 或任何模型阶段；没有新自然语言分类器、方法接口或优化实现。读取失败与 RETAIN 的经验都按原样分析，没有修正历史文件。

保护清单覆盖正式 S1、V23/V23.2 源码与 Actor Adapter，修改前后核验见 [PROTECTION.json](PROTECTION.json)。不对研究文本额外运行整套工程回归；已完成档案一致性核验，无模型 Token 花费。本次到报告完成为止，不进入实现阶段。
