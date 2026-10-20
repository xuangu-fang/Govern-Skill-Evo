"""Write P2 reports from verified offline outputs; never changes source archives."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
EXP=Path(__file__).resolve().parent
S=ROOT/'artifacts/methods/v23/v23_alfworld_formal_001/S1'
m=json.loads((EXP/'results/memory_audit.json').read_text())
r=json.loads((EXP/'results/run_evidence_index.json').read_text())
s=json.loads((EXP/'results/r05_selection.json').read_text())
def link(label,path): return f'[{label}]({path})'
def report(name,text): (EXP/'reports'/name).write_text(text.strip()+'\n')
idx=link('来源与原始执行索引',EXP/'reports/SOURCE_INDEX.md')
checks=link('离线核验结果',EXP/'results/receipt.json')
protection=link('保护核验',EXP/'results/protection.json')
source='''# P2 来源索引

本目录是只读分析产物。所有 step 标识一基；原始 JSON 的 steps 数组零基。历史上下文中的 P/Q 分别为 Parent/Candidate。R05 当前 P3/P4 与未来阶段 P3 无关，不要混淆。

## 实际请求与快照

'''
for rnd in ['R05','R06']:
 p=Path(m[rnd]['path']); a=Path(m[rnd]['active_path'])
 source+=f'### {rnd}\n\n- '+link('实际 request.json',p/'request.json')+'：`body.messages[1].content` 解析后的 `memory.entries / memory.sources`。\n'
 source+='- '+link('实际 response.json',p/'response.json')+'、'+link('HTTP 状态',p/'http_status.json')+'、'+link('运行记录',p/'run.json')+'：本次校验状态 valid，与保存请求共同证明历史调用已完成，不仅是未发送装配。\n'
 source+='- '+link('装配输入',p/'input.json')+'、'+link('round_input',S/f'rounds/{rnd}/round_input.json')+'、'+link('Active 索引',a/'active.json')+f'：IDs = {", ".join(m[rnd]["active_ids"])}。\n'
 for cid in ['S1_R03']+(['S1_R05'] if rnd=='R06' else []):
  source+='- '+link(f'{cid} 不可变 commit',a/f'archive/{cid}.json')+'：`entries[id=M6/M10].knowledge/evidence`；`context.payload.parent/diff/runs/command_sets/pairs`；`context.candidate/record_paths`。\n'
 source+='\n'
source+='## 原始 Skill 编辑\n\n'
for cid in ['S1_R03','S1_R05']:
 p=Path(m[cid]['editor_path'])
 source+=f'- {cid}: '+link('actual.diff',p/'actual.diff')+'、'+link('candidate.md',p/'candidate.md')+'。严格 Patch 应用于 archive Parent 得到相同 Candidate；没有调用 Editor 模型。\n'
source+='\n## 40 条原始执行路径\n\n| 上下文／ref | 原记录 | task_id | 步数／成功 |\n|---|---|---|---|\n'
for key,v in r.items():
 source+=f'| {key} | {link("record",v["path"])} | {v["task"]["id"]} | {v["steps"]} / {v["outcome"]["success"]} |\n'
source+='''
每条 raw record 的 `steps[n-1].admissible_commands/messages/action/observation/feedback` 分别核查环境行动前候选、Actor 实际消息、动作、动作后观察及反馈。归档 facts 的 `steps[step=P*:n/Q*:n].before.commands_ref` 解析自 `command_sets`，不是 after 菜单。过滤只去掉精确的 `help`，其余内容、重复和顺序保留。最后一步 after.commands_ref 为 null 不表示空菜单。

## P1-B R05 静态输入来源

'''
p=ROOT/'artifacts/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001'
source+=link('合法重试 Diagnosis',p/'diagnosis.json')+'、'+link('原始输入',p/'input.json')+'、'+link('请求',p/'request.json')+'。只读取合法结果；未把第一次截断输出作为 Plan。Diagnosis 顶层 reason 不进入 Preconditioner。\n\n'
source+=link('静态选择与尺寸',EXP/'results/r05_selection.json')+' 保留相同 Original Plan 和 Grouping；所有补充条件只在内存中构造、未发送，没有产生新的 Plan。\n\n'
source+=link('原始来源哈希',EXP/'config/source_hashes.json')+'；'+link('紧凑执行索引',EXP/'results/run_evidence_index.json')+'；'+link('实际 Memory 与 Diff 核验',EXP/'results/memory_audit.json')+'。紧凑索引只是定位辅助，判断以原始记录及 archive 为准。\n'
report('SOURCE_INDEX.md',source)

mem=f'''# P2：M6 / M10 语义保真核查

**结论：M6 的主要混合反馈准确，不需要先改写。M10 确认存在“新位置→新类别”的事实单位混淆，以及“未找到→不存在”的证据越界；准确 Diff 和被引用执行仍在 R06 实际请求中。不能据此证明 Memory 偏差造成了 Keep，更不能保证改写后会改善决策。**

只分析正式 Train。未使用 Test，未使用 R06 结束后的 M12/M13。原始文件、JSON 字段、task/game 哈希见{idx}；离线结果见{checks}。

## 1. 快照与传递链

| 调用 | 实际 Active 所在目录 | Active IDs | 本次关注 |
|---|---|---|---|
| R05 | rounds/R04/memory | M1 M2 M3 M6 M7 M8 M9 | M6；**没有 M10** |
| R06 | rounds/R05/memory | M1 M2 M6 M7 M9 M10 M11 | M6 与 M10 |

两轮由 `preconditioner/result.json` 定位实际 attempts/001。核验 `request.body.messages == messages_for(saved)`，解析出的 Memory 与保存 input、round_input 以及当时 Active/commits 重载完全一致。两轮有 HTTP 响应、response 和 valid 结果；这是历史实际请求，不仅是磁盘存在或静态装配。仅凭客户端归档不能判断服务端注意力或模型是否理解每条事实。

M6 两轮内容完全相同，来源 S1_R03。M10 来源 S1_R05，只用于 R06。`load_memory` 对每项 evidence 加入完整 Parent/Diff/Execution Context；引用某一步会展开该条历史 run 的完整 initial、before/action/after/feedback/outcome 及相关完整候选表，**不等于展开该历史轮的全部任务**。

- M6 自身引用 P2/Q2、P4/Q4、P6/Q6；当时其他 Active entries 还带入 S1_R03 的 P5/Q5、P7/Q7、P8/Q8、P9/Q9、P10/Q10。共 8 对，未含 P1/Q1、P3/Q3，不能仅凭该请求独立重算十对 7/10→6/10。
- M10 引用且 R06 实际携带 S1_R05 的 P6/Q6、P7/Q7、P8/Q8、P10/Q10，共 4 对；完整十对在不可变 archive，本次离线核对 7/10→9/10。其余六对不在 R06 sources，不声称所有汇总依据都逐条传入。
- 本次从原始 record 重建 S1_R03、S1_R05 全部 40 条 facts，核对源 run、候选、反馈及配对 task/game/seed；严格应用实际 Diff 得到原 Candidate。不是重跑环境，也不是对事实概括的自动语义评分。

## 2. M6 原文与实际支持

原文来自 R05/R06 `memory.entries[id=M6].knowledge`，完全相同：

> {m['R05']['entries'][0]['knowledge']}

### 真实编辑边界

S1_R03 actual.diff 的搜索修改加入当前/近期观察、当明显 cabinets/fridge 未找到时转向 drawers/shelves/diningtable/其他位置、高步数优先新位置；同时联合修改精确类别、直接持物温度处理和处理后交付。Parent 已有打开闭容器、避免立即空回访、空手 inventory、全部合理位置检查一次等基础规则。因此 knowledge 的 `rewrote ... to add` 不能解释为每个提到的子句都是新创造，但未发现它据此错误分配独立收益。

实际修改全文在来源索引的 R03 actual.diff；不含固定批次、类内穷尽后才能换类、永久动作禁令。

| 原始配对证据 | 可支持认识 | 不能推出的要求／核查判断 |
|---|---|---|
| S1_R03 P4 50步失败；Q4:12 到 diningtable，13 取 bread，15 cool，17 place 成功 | Candidate 这一次扩大到了有目标的位置，行为与扩展搜索方向一致 | 不能分离搜索和新增温度处理的贡献，更不能证明 diningtable 必须优先或固定跨类别顺序最优。M6 已用 consistent / mixed 限定，准确 |
| P2:15 countertop 3、16 取 bread、18 cool、20 place 成功；Q2 50步失败，多次 countertop 2（25/30/36），没有到 countertop 3 | 同类别实例仍可能遗漏；联合新 Skill 并不稳定避免循环／遗漏 | 不支持“类别轮换导致遗漏”或“必须穷尽类别后切换”。两端同 task/game hash/seed/初始状态；并非不同任务难度解释此对差异。M6 没有写出强制反向规则 |
| P6:31 到 cabinet 9，32 open，33 取 plate，36 cool，38 place；Q6:47 到 cabinet 9、48 open、49 take、50 到 fridge 结束 | Candidate 找得太晚，未留下足够完成步骤；动作/覆盖效率是局限 | 不证明应固定保留多少步，也不能把退化归因于某一个搜索子句 |
| Q6:4/10/15/20/26/37 选不可用 `go to cabinet 3`，结果 Nothing happens；其后多次 examine 空位置 | 当时动作前提不成立、重复无进展；当前候选及状态应参与选择 | raw `fallback` 为 null，不能将 knowledge 的 `falling back to a no-op` 当作 Adapter 自动 fallback。它可描述无效结果，但工程机制措辞不准；不支持永久禁止 go/examine，M6 也没有提出这种禁令 |
| P5/Q5 cool pan、P10/Q10 heat mug 均50步失败；全十对7→6 | 混合反馈、循环仍存在；新编辑未稳定解决问题 | “within plausible stochastic variation”是合理可能性而非统计检验；各实例一次且联合编辑，因果未隔离。M6 明确保留此限制 |

**M6 判定：** 核心观察、反例、条件与单次联合编辑的不确定性保真；没有发现足以要求先重写 M6 的策略级错误。仅需在研究解释中避免把 no-op 称为程序 fallback、把略降结果称为已证实随机波动。M6 已能约束“新方向必然覆盖所有实例/稳定无循环”等过强解释，不能唯一决定搜索调度。策略优劣未知不等于 Memory 错误。

## 3. M10 原文与实际支持

原文来自 R06 `memory.entries[id=M10].knowledge`：

> {next(e['knowledge'] for e in m['R06']['entries'] if e['id']=='M10')}

### 真实 Diff 与 summary 的差别

S1_R05 actual.diff 的关键原句：

> run a single-pass sweep that spreads across distinct receptacle families rather than exhausting or looping over one type.

后文要求新位置、近期观察避免空回访；一族没有收获后切到不同未检查族，再回访先前位置；预算内扩大容器与表面覆盖；直到找到精确目标或所有合理 **receptacles** 一次。另一个联合编辑强化 knife/butterknife 等精确类别。

M10 保留了跨族方向、single-pass、换族先于回访、预算及混合反馈；**省略了 `rather than exhausting` 这个直接影响调度比较的限定**。保留的 `after one family ... yields nothing` 可被理解成查部分或查完一族，弱化了策略对比的清晰度。但它没有明确要求类内穷尽；也不能把 Diff 反对困在一类解释为隔离实验证明所有类内穷尽都坏。

| 判断点 | 原轨迹／字段 | 结论与支持边界 |
|---|---|---|
| butterknife 修复是否是进入新类别 | S1_R05 P6:3 已到 countertop 1，后续7/11/15又到；Q6:3 也到 countertop 1，16 到 countertop 2 看见 butterknife，17取、19clean、21place；Parent50失败 | **确认事实单位混淆。** countertop 1 与2是同类不同实例。支持到达此前遗漏的位置，不能把该修复称为 Parent 从未进入的 family。M10 自己同时写 Parent 到过 countertop，内部已可发现张力 |
| soapbar 修复 | P8 50步无 shelf 1；Q8:18 到 shelf1、19取、21clean、23place | 这里确实新增了 shelf 类覆盖；但Q8先开cabinet1–4且仍回访，不是严格无循环调度的示范。该例不能替 butterknife 例纠正覆盖单位 |
| “no exact butterknife was present” | P7/Q7均50步未找到；初始候选含 cabinet1–18 等。P7只到部分 cabinets、Q7更少；仍有多个未查位置 | **现有来源不足以证明环境中不存在目标。** 应区分未发现与全局不存在。不是已证明物体实际存在，也不能用任务名称作为存在性 oracle |
| near-match 的联合影响 | P7:5取 knife，7clean，9place；Q7未重复此替代物处理，但仍失败 | 整体失败不等于所有行为无改善；成功／失败不能独立归因于搜索策略 |
| 循环与增步 | P10 apple38步成功；Q10到diningtable为40、最终46步；均成功但Q多次回访 | M10准确保留局限；不能承诺跨族一定更快或不再循环 |
| 总结果7→9、已成功任务无新增失败 | archive全部十对离线核对一致；R06 sources仅其中四对 | 汇总准确，单次联合编辑；统计与因果边界未消失。`rescues depended ... uninspected family`对两次救回一并使用仍错误扩大单位 |

### 对实际策略决策的影响分层

1. **已证实的语义问题**：新实例被概括为新类别；未发现被提升为不存在；省略 actual.diff 的反类内耗尽限定。
2. **决策风险**：容易把覆盖收益理解成“类别级调度已获支持”；模糊的 family yields nothing 可被不同调度吸收；目标不存在断言可能误导停止边界。但这些是风险，不能断言实际发生某种停止调整。
3. **实际已观察的决策**：正式 R06 `preconditioner.reason` 写 `M6/M10 support the uninspected-family sweep as a direction even though it is not a guaranteed cure`，并据两步历史认为 ordered memory-independent sweep 合适，adjustments=[]。最终保留原始类内穷尽 Update，未在显式理由中解释与原 Diff 调度的差别。**这证明支持范围没有在显式判断与最终变换中充分展开，不证明 M10 概括是造成 Keep 的原因。**准确 Diff/轨迹确实在输入；Goal、当前证据解释及随机性也可能相关。

因此归类为“**概括存在偏差，但关键原始依据已传入**”。部分断言是重要事实边界错误，并非全面证据缺失。为评估纠偏作用，未来可以单独冻结修正概括的实验副本；本次不改历史 Memory，不把这种试验混入 R05有/无Memory主比较，更不能承诺修正后必有效。

## 4. 对后续的约束

- R05只可用当时 M6 等 Active；M10不是其历史，不能为了有利反例加入。
- M6可提供“过去真实编辑后的混合响应”，超出当前循环事实；但不决定唯一搜索顺序。
- M10支持研究具体遗漏位置/类别与调度假设的关系；不支持固定类别排序、采样阈值、永久禁回访、未找到就宣告不存在。
- 原始 source 的可获得性与正确使用必须分别检验。下一阶段有无Memory比较才可能观察增量决策作用；本阶段没有这种结果。

方法、Prompt、Memory、历史归档未由本次修改；零新增模型、Token及环境调用。见{protection}。
'''
report('P2_MEMORY_AUDIT.md',mem)

selection=f'''# P2：R05 当前证据选择核查

**P4是有价值的直接路径对照，但不是纠正主要过强要求的唯一依据。当前输入已有P3循环及其可选动作、P6/P8/P10覆盖问题，Grouping也准确保留P4摘要。若下一阶段评价整项u1的行为保留，建议显式补充P2与P4；若只检验历史响应对搜索调度/no-op约束的增量，原选择可用。不要通过修改Original Plan引用偷偷补齐。**

来源见{idx}。本报告研究 **P1-B合法R05 Original Plan** 的静态Preconditioner输入；它尚未实际发送。正式V23 R05实际调用使用另一份Original，不能把其Keep当作对P1-B的判断。

## 1. 选择逻辑及边界

`src/skill_evolution/v23/preconditioner.py::preconditioner_input` 把整个 `diagnosis.plan` 序列化（Goal、Updates及basis、Checks），提取P引用；引用一步即展开整条run。显式G引用或与已选P相交会选Grouping条目，**不会反向补齐所有members**。顶层Diagnosis reason不转发、不参与选取。为已选run保留initial及每步before/after的候选表。

P1-B R05当前选择 P1/P3/P6/P7/P8/P10；G1–G4都在。P2/P4/P5/P9没有完整轨迹，但各有Grouping摘要，不能说完全消失。此处是引用选择，不是请求截断或容量不足。

u1 实际要求包括 `During any search ... (or for the desklamp once the target is in hand)`、`Sweep ... same-type ... without returning to earlier ones; once that series is exhausted ... switch`；u2包括 `do not repeat that action or an equivalent one`、`immediately take a state-changing action`。完整原文保存在 r05_selection.json 的 original_plan。没有生成或修改Update。

## 2. P3/P4：相同任务类型，不是同一初始实例配对

| 条件 | P3 | P4 |
|---|---|---|
| task_id | val0003 | val0004 |
| task | put some mug on sidetable | put a mug in sidetable |
| game trial | T20190909_032318_169393 | T20190909_032340_274147 |
| game SHA256 | {r['S1_R05/P3']['game_sha256']} | {r['S1_R05/P4']['game_sha256']} |
| seed/Parent | 42，同一Parent | 42，同一Parent |
| 初始可见房间与候选 | 与P4相同，已有go to diningtable 1 | 与P3相同 |
| 物体分布 | diningtable到达后见一只mug及其他物体 | diningtable到达后见三只mug及不同物体 |
| 结果 | 16步成功 | 4步成功 |

P3:1–7检查drawer1–4；8–11回访四个drawers；12到sidetable，13才到diningtable发现mug，14取，16place。P4:1直接到diningtable发现mugs，2取mug1，3到sidetable，4place。

两个初始 observation 的任务句不同；“房间列表相同”不能写成完整初始状态相同。游戏hash及内容不同，因此不声称12步差异是调度独立收益。P4初始并不知道mug一定在diningtable；动作可用只证明可选，不证明该选择当时保证正确。

**P4带来的事实**：这类任务存在不先穷尽drawers、直接找到目标后交付的成功路径；具体候选和物体发现时点可核查。它限制“只有先扫编号系列才能完成”的必要性主张，但不能证明类内穷尽一定坏，也不是对条件性“在未找到时尝试扫序”的直接否定。

**不传P4具体损失**：无法从原始候选核对其第1步可选动作、发现前后状态、多mug条件及准确动作链。G2已写明直接diningtable→take→place，并区分P3回访与P5闭容器；对粗粒度“存在另一条成功路径”已足够，对精细同条件比较不够。P3完整原始菜单本身也证明diningtable在前期可选。故主要更新判断并非完全缺证。

## 3. 未选轨迹的必要性

| 轨迹／当前状态 | 额外关键事实 | 与目标Update关系 | 现有输入是否足够 | P3建议 |
|---|---|---|---|---|
| P2，仅G1摘要 | 1到desk见lamp；4在bed2取pillow；5回已访问desk；6use成功 | u1扩展到持目标后的lamp搜索；绝对排除早先位置会损害有效回返。P1是拿目标后新找到lamp，不能完全替代 | 判断“应保留共址”足够：Parent/Goal/G1都有；核对回返状态与候选不足 | **评价完整u1保留边界时建议补充**。仅研究循环/调度可保留原选择，不宣称回返全面检验 |
| P4，仅G2摘要 | 直接diningtable获取并交付，4步 | 限制调度必要性/范围，不证明最优排序 | 粗粒度比较足够，动作条件级对照不足 | **报告要使用P3/P4细对照时建议补充**；不是所有Memory实验的硬前提 |
| P5，仅G2摘要 | 1到闭drawer、2open、3取pencil、5交付 | 保留开容器与目标可见后直接获取 | P3已含打开闭容器，其他已选成功链提供获取交付；G2明确前提 | 暂不需要；若新方案拟删除open前提再专项核查 |
| P9，仅G4摘要 | 1countertop见soapbar、2取、4clean、6place成功 | 精确clean后交付，区别于P7错误knife及P10cool | 对本轮搜索/no-op主问题足够；Parent+G4+P10保留处理交付。但不是完整clean成功菜单证明 | 暂不需要；若评价处理/交付策略改动则补充，不能把cool等同clean |

P2的回返不是“在空位置反复搜索”；必须区分已知有效目的地与已检查无目标位置。Grouping已经提供此边界的线索，不应把未传完整P2解释为模型绝不可能纠正。

u2跨状态禁止重复／强制state-changing也可仅靠当前输入质疑：已选P3多次open不同drawer属于动作类型重复但有信息价值，首次必要examine/look与重复无新信息不同；单次Nothing happens不证明状态改变后重试也无效。无需M10才能识别这种范围问题；当前数据仍不证明最佳重试阈值。

## 4. 未发送输入的精确尺寸

按既有messages格式 `json.dumps(messages, ensure_ascii=False)` 计算字符与UTF-8 bytes；不是token估计，也不是服务端上下文接受保证。容量沿用P0 cases R05：4,000,000字符、6,000,000 bytes。

| 静态条件 | 有Memory字符 / bytes | 无Memory字符 / bytes | 相对原选择增量字符/bytes |
|---|---|---|---|
'''
for label,v in s['measures'].items():
 selection+=f'| {label} | {v["memory"]["chars"]:,} / {v["memory"]["bytes"]:,} | {v["no_memory"]["chars"]:,} / {v["no_memory"]["bytes"]:,} | +{v["added_chars"]:,} / +{v["added_bytes"]:,} |\n'
selection+=f'''
所有条件低于既有装配限制。P2+P4增加9,738字符/bytes，不构成这里的容量障碍；不因此建议全部补齐。历史Memory本身增加1,417,500字符/1,417,512 bytes，包含entries及sources；这不是本次Token消耗。

本次只在内存复制payload中测量，没有修改装配、Original Plan、basis、Grouping、证据选择配置或发送任何请求。尺寸记录见{link('r05_selection.json',EXP/'results/r05_selection.json')}。

## 5. 对未来实验的明确建议

优先保留R05合法P1-B Original作为固定Plan。若目标是**整项Update构造及有效行为保留**，建议未来独立明确冻结“当前证据原选择+P2+P4”条件，理由为已知目的地回返与直接路径对照；不用P5/P9为完整性堆输入。原装配结果继续留存，不假称仍是未经改变的默认选择。

若目标收窄为**历史编辑响应对搜索调度和状态相关重复约束的增量作用**，原六条+Grouping已经足以开展；P4不是必须先补的硬阻碍。验收不得反过来要求没有传入的精细P4条件比较。此选择需要在P3调用前固定，不能看输出后选有利条件。

无论选哪一条件，无Memory/有Memory两组必须具有相同Original Plan、Parent、当前runs/menus、Grouping、system背景、参数、容量。仅Memory的entries+sources不同。不能一组补P4而另一组不补，也不能修改basis来引入P4后宣称Original没变。补充证据是独立实验条件，不是Memory改进。

本阶段停止于建议与未发送尺寸核查。{protection}。
'''
report('P2_R05_EVIDENCE_SELECTION.md',selection)

decision=f'''# P2 阶段决策

**可准备后续R05固定Original Plan对照，不需要先重写M6或全面改造Memory。M10存在真实概括偏差，但并非R05当时输入；对R06应单独控制这一变量。R05未选P4不是主要更新判断完全无法进行的硬阻碍；若要完整评价u1，建议未来显式、对称补P2+P4。**

## 七项回答

| 问题 | 结论 |
|---|---|
| 1. M6是否有实际影响策略判断的概括偏差？ | 核心收益、遗漏、循环、预算不足与单次联合编辑限制准确。`falling back`不是实际Adapter fallback；轻微工程措辞不准，但未发现由此永久禁止动作等策略扩张。无需先修Memory |
| 2. M10位置与类别混淆是否证实？ | 是。P6已到countertop1，Q6在countertop2发现目标，属于同类新实例。另有未找到butterknife被写为不存在的证据越界；不是已证明目标实际存在 |
| 3. 原Diff与行为证据是否真实传递？ | 是：R05/R06实际请求包含M6对应Diff及引用run全文；R06包含M10 Diff及4对引用run。请求/响应/valid及快照重载核对通过。不是全部历史十对都传入；聚合结果本次回溯archive另核对 |
| 4. 主要是概括、缺证还是使用未验证？ | M10有局部概括失真/限定弱化；关键准确source未缺。概括如何影响实际Keep尚未隔离，不能归因已证。当前证据另存在选择性省略，应分开 |
| 5. P4等是否P3必须依据？ | 不是纠正主要过强要求的唯一必需证据；P3自身和G2已有关键事实。但若以P3/P4精细对照或完整u1保留为验收，就应补相应全文；建议P2+P4，不一律补齐 |
| 6. P3前需要修什么？ | 先固定评价范围、当前证据条件和两组对称输入；标明只用R05当时Memory。没有必须先动正式Memory或方法代码的证据。若研究R06“准确历史认识”则先独立说明M10修正副本条件，不能把原M10当无误真值 |
| 7. 暂不修什么？ | 不扩大Memory审计；不因摘要不够详尽重写M6；不自动补所有Parent；不调整Actor历史窗口；不规定唯一搜索调度、阈值、禁回访或停止策略；不把知识纠偏等同于决策收益 |

细节与原文见{link('Memory核查',EXP/'reports/P2_MEMORY_AUDIT.md')}、{link('R05证据选择',EXP/'reports/P2_R05_EVIDENCE_SELECTION.md')}及{idx}。

## 三类判断必须分离

| 仅凭当前Parent/任务条件可识别 | 历史M6/M10额外提供 | 综合后仍不能确定 |
|---|---|---|
| P3已有无新信息回访与直接获取交付；P6/P8遗漏位置；P10晚找到后仍需处理交付。不能把这些现象当作类内穷尽的唯一证明 | M6提供实际扩展搜索/近期避免循环编辑后的收益与同类实例遗漏、非法动作重复、晚发现仍失败的配对响应，而不只是另一些失败轨迹 | 类内穷尽与跨族何者更优、切换尺度、具体排序、预算分配、稳定成功率与步数收益 |
| G1/P2提供持目标后返回已知lamp的必要边界；已访问不等于无用；任务前提不因去重而消失 | M10提供R05实际反长时间困在一族Diff、两次修复与循环/增步并存；但只可用于R06及之后，且位置/类别及目标不存在断言须校正解释 | 哪个编辑独立导致收益/退化；M10失真是否导致Keep；纠正knowledge能否改善Update |
| 动作无效发生于具体状态；不支持永久禁同类动作，信息性动作并非必须立即state-changing | 历史联合编辑显示提示已被尝试却未稳定遵循，因此应限制保证性结论；不自动要求撤回整个方向 | 如何在Actor两步视野下最好实施全局覆盖；当前来源不能证明某个确定调度已获因果验证 |

R05当前材料能纠正条件错误，不代表Memory没有增量价值。P3应关注有无Memory时，**编辑—行为响应是否改变最终Update的方向、条件或强度，并且这种改变有可追溯依据**；只看引用Memory或Adjustment数不能回答。一次随机输出差异不等于稳定因果收益。

## 推荐的P3准备边界（未执行）

1. 固定R05 P1-B合法Original，不再生成Diagnosis；排除M10与事后Memory。
2. 明确取窄目标原六条，或完整u1评价的“六条+P2+P4”。后者增加9,738字符/bytes，低于已有容量，作为明确证据补充条件冻结；两臂相同。
3. 两臂仅改变历史Memory（entries与sources整体），不同时改Prompt或knowledge；若未来要测试M10修正概括，另列独立条件和轮次，保持原Archive不变。
4. 验收分开当前证据纠正、Memory增量、未验证探索。不预设类内或跨类标准答案，不强制Adjustment。

## 本次离线核验与保护

- 40条原始记录重建facts，与两个历史Memory context的动作、前后观察、候选、结果逐项一致；20对task/game/seed/initial配对一致。两份actual.diff严格应用得到相同Candidate，仅调用纯Patch函数。
- 两轮正式实际Preconditioner请求与重装消息相等；Active快照/不可变commit与输入相等；M6内容跨轮一致，M10只在R06。
- R05静态选择/七种尺寸条件在网络连接被禁止的脚本中运行；Original、Grouping保持不变。未发送任何请求。
- 第一次本地脚本因缺PYTHONPATH停止；第二次旧全源码基线检查因**任务前已有**模型路由/CLI改动停止。记录于preexisting_contract_drift.json；没有恢复或覆盖。改为核对实际用到的preconditioner装配/读取、memory读取、facts构建、editor.apply_patch函数AST与冻结版相等，并核对原请求逐项相等。与本任务无关的路由变更未执行。这些是离线核验启动错误，不是模型失败重试。
- 唯一新增区域为本P2目录，含三份报告、来源索引、轻量脚本、哈希/核验结果；保护覆盖已有src/experiments/artifacts/docs/tests/benchmarks及.gitignore，忽略缓存。Test只做哈希保护，不分析其轨迹。
- 保护细项与开始/结束状态见{protection}；已有未提交变化及冻结源码差异单独保留，不归因于P2。没有运行大量无关测试。
- **新增模型调用0、Token0、API成本0、Actor/环境调用0。没有修改Prompt、方法、Memory或默认配置，没有进入P3。**

本次结论是“能够明确数据和解释边界”，不是已改善Preconditioner或Skill性能。
'''
report('P2_DECISION.md',decision)
