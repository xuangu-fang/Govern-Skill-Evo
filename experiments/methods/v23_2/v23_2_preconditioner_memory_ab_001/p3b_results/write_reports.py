"""Archive P3-B execution and evidence-based evaluation; no generation calls."""
import json
from pathlib import Path
E=Path(__file__).resolve().parent;P=E.parent
read=lambda p:json.loads(p.read_text())
receipt=read(E/'results/execution_receipt.json')
original=read(P/'config/original_plan.json')
b=read(E/'runs/B/preconditioner.json');ep=read(E/'runs/B/effective_plan.json')
assert receipt['groups']['A']['run']['status']=='technical_failure' and receipt['groups']['B']['run']['status']=='valid'
def link(t,p):return f'[{t}]({p})'
def write(n,t):(E/'reports'/n).write_text(t.strip()+'\n')
L=lambda t,p:link(t,E/p)
PL=lambda t,p:link(t,P/p)
A=receipt['groups']['A']['run'];B=receipt['groups']['B']['run'];u=B['usage']
execution=f'''# P3-B 执行报告

**两次授权请求均已发出，零自动重试。A读取超时，B合法完成，因此没有形成有效的A/B输出对照。不能把A缺失结果当作Keep、no_change或无Memory语义失败。**

## 冻结及授权

使用P3-A请求原件；Original是 `v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001/diagnosis.json`。未修改Goal、Updates、basis、Checks或重新运行Diagnosis。

发送前核验P3-A freeze、input_manifest、全部source哈希、当轮Active、唯一Memory变量；实际HTTP发送前再次核验正文与完整request文件SHA256。A空Memory，B为M1/M2/M3/M6/M7/M8/M9及sources；两组仍只有P1/P3/P6/P7/P8/P10、G1–G4与原103候选表。未加入M10或P2/P4完整当前轨迹。

用户本次明确授权直接执行，确认内网别名与此前模型对应，不需再查上下文容量。该授权单独记录于 {L('authorization.json','config/authorization.json')}；未覆盖P3-A原先的待确认状态。本次没有额外容量探测或路由探测调用。

| 项目 | A | B |
|---|---|---|
| 请求模型 | deepseek-v4.1-flash | deepseek-v4.1-flash |
| response_model | 未收到 | {B['response_model']} |
| 开始UTC | {A['started_at']} | {B['started_at']} |
| 结束UTC | {A['finished_at']} | {B['finished_at']} |
| 耗时 | {A['elapsed_seconds']:.3f}秒 | {B['elapsed_seconds']:.3f}秒 |
| HTTP请求尝试 | 1 | 1 |
| 自动重试 | 0 | 0 |
| 状态 | transport ReadTimeout | HTTP 200 / ready / stop |
| parsed / Effective | 不可得，没有生成 | 原解析、Schema、编译通过 |

Endpoint为冻结的 `http://llm-proxy.intra.xiaojukeji.com/chat/completions`；temperature=1、thinking=enabled、reasoning_effort=medium、stream=false、max_tokens=16384、read timeout=300秒、connect timeout=10秒。两组均未更改参数。

## 发送与失败处理

仅在新的P3-B目录增加最小包装器 {L('run_once.py','run_once.py')}，复用 `grouping.live_generator`、原JSON解析器和 `compile_effective_plan`。没有运行 `local.run_stage` 的自动三次重试循环。包装器持久化一次性execution_claim；重复运行会拒绝，不能通过重启偷偷重采样。

HTTP Session的adapter重试总数为0，禁止redirect，内网Session不继承外部代理；每次post前核对完整请求、timeout、body及调用计数。实际请求文件与P3-A原件字节哈希一致，见 {L('preflight','config/preflight.json')}、{L('A发送记录','runs/A/dispatch.json')}、{L('B发送记录','runs/B/dispatch.json')}。

A的错误原文：`Read timed out. (read timeout=300)`。它没有返回HTTP状态、响应正文、finish_reason或usage，不能伪造这些文件。客户端超时不说明服务端未计算或未计费，亦不证明容量超限、模型拒绝或共同配置错误。按预注册的单组独立失败规则继续B；B在57.5秒合法返回。不据此解释A超时的根因。

B完整原始HTTP正文保存于 {L('http_response.txt','runs/B/http_response.txt')}，包含服务返回内容；{L('response.json','runs/B/response.json')}、{L('raw_output.txt','runs/B/raw_output.txt')}、{L('parsed.json','runs/B/parsed.json')} 与 {L('effective_plan.json','runs/B/effective_plan.json')} 可追溯。A仅保存已发送请求、dispatch、时间、错误及“响应/usage不可得”记录，没有伪造响应或Effective。

## 实测用量

| 用量 | A | B |
|---|---|---:|
| input tokens | 未返回，未知 | {u['prompt_tokens']:,} |
| output tokens | 未返回，未知 | {u['completion_tokens']:,} |
| 其中reasoning tokens | 未返回，未知 | {u['completion_tokens_details']['reasoning_tokens']:,} |
| total tokens | 未返回，未知 | {u['total_tokens']:,} |
| cached input tokens | 未返回 | API未提供，不按0处理 |

B的4,751 reasoning tokens已包含于5,270 output，不重复加总。已知用量小计480,027；**两组实验总Token未知**，不能把A按0加总。没有可靠货币账单，未估算费用。两请求耗时合计{A['elapsed_seconds']+B['elapsed_seconds']:.3f}秒；这不是服务端总计算时长。

## 编译核验与保护

B同时调整一次u1，u2原样Keep；无拆分、合并或撤回。Goal原样，checks=null使c1–c3原样保留。所有替代text逐字进入Effective，u2逐字不变；重编译与保存结果相同。Effective u1的basis按原程序保留Original来源，M6/M3/M8引用位于Adjustment.basis而非Effective.basis；这是原编译契约，不是证据被漏传。

Preconditioner reason不自动成为Actor指令；本次不调用Editor。结构合法不能证明新的策略合理。

保护结果见 {L('protection.json','results/protection.json')}；仅新增本p3b_results目录，正式V23、旧V23.2、P0–P3-A、Memory、Parent、Campaign和Test保持原样。Test仅哈希保护，没有用于分析。新增逻辑调用2、HTTP尝试2、自动重试0；Editor/Actor/Replay/Gate/Memory/Diagnosis/环境调用均0。
'''
write('P3B_EXECUTION_REPORT.md',execution)

comparison=f'''# P3-B Update独立评价与比较边界

**A无有效输出；先记录其不可评价，再独立分析B。以下Original→B变化不是A→B增量。**

## 1. A组独立评价

A读取超时，没有reason、adjustments、checks或Effective Plan。u1/u2是否Keep、如何改变、是否使用当前证据均**无法判断**。不把Original代填Effective A，不用正式V23/此前任何无Memory输出补位。A的技术失败不是预条件化语义失败。

## 2. B组独立评价

### 实际总体判断

> {b['reason']}

唯一Adjustment的实际reason：

> {b['adjustments'][0]['reason']}

其basis为 `{b['adjustments'][0]['basis']}`；decision=ready、checks=null。

### u1：从编号穷尽改成跨类型采样，有问题动机，但附带限制仍越界

| 行为要求 | B实际文本 | 独立评价 |
|---|---|---|
| 搜索方向 | `breadth-first coverage ... rather than exhausting one long same-type series` | 当前P6长drawer搜索、P8循环、P10晚到diningtable支持尝试重新安排覆盖；M6/M3也提供混合反馈。跨类型探索可保留为候选假设，不是天然错误；也没有证据证明它一定胜过所有类内穷尽 |
| 近期反循环 | `use the current observation and the last two pre-action pairs`；`not present in that recent history` | 比全局未访问集合更接近Actor实际输入，明确了观察窗口。近期未出现不等于全局未访问，不能据此认为已实现全局广度覆盖；“different listed receptacle or type”留有选择，不是固定全局类别顺序 |
| 类内切换尺度 | `after sampling a few same-type containers ... switch` | few没有给出2次/3次等固定数值，不应机械判为数值阈值。它是有减少单类耗时动机、尚未验证的调度假设；但“few”的跨多步进度未明确，不能声称已完整解决信息能力问题 |
| 全局未访问条件 | `while other receptacle types remain unvisited or the step count is already high` | 步数可见，high未定量不等于已规定阈值；然而“其他类型仍未访问”仍需超出两步窗口的全局进度，文本未给恢复依据。reason所称better fits能力并未贯穿最终规则 |
| 续查同类的前提 | `Return to remaining numbers in a series only after other plausible types or locations have been sampled` | 这是实质性强顺序：先完成其他采样才能续查。既需累计采样/剩余编号状态，也没有独立证据证明这一排他前提必要。M6遗漏同类countertop3反而提示不能无条件推迟同类余项；不据此反向规定必须类内穷尽 |
| 新搜索终止条件 | `until ... all plausible candidate types or locations have been inspected once` | Original u1未规定类别采样终止，Parent边界是合理receptacles而非types。`types or locations`使类别采样与位置耗尽混用，可能在同类仍有未查实例时满足宽泛停止读法；并依赖全局进度。合理的广度动机不足以支持这个附带变化。是文本风险，未执行所以不声称已发生过早停止 |
| 必要行为保留 | 保留exact target/no-substitute、到达闭容器就open；Goal和u2含获取/处理/交付；作用域仍含持目标后lamp搜索 | 精确对象等主要保留。没有新增必然成功/guarantee progress字面保证，也没有数值批次或固定全局类别排序。scope未排除已知有用目的地，新的采样前提与近期回避可能干扰有效返回；G1共址与M9回源需区分，不能据文案直接认定一切回源被禁止 |

B识别了全局已检查集合问题，但最终又引入“其他类型unvisited/已sampled/所有types或locations一次”。**局部近期新颖性条件有所落实，全局策略状态依赖仍未解决。**不把所有编号策略一概判不可执行：某些进度可由当前编号/可见候选恢复；问题是本次跨族累计条件并无这种说明。

B没有为“所有类别采样后才能回同类”和类别级结束条件分别给出证据或可检验预期。不能将广度探索的合理动机自动扩展为所有附带强制条件的依据。

### u2：保持原文，条件范围问题未处理

B明确写 `Keep the no-op avoidance update unchanged`，Effective u2与Original完全一致。当前P1:4不可用移动、P7:11/12相同look、P8:39/P10:25空inventory确实支持避免**相同条件下**无信息重复。

但最终仍为：`do not repeat that action or an equivalent one`，随后 `Instead immediately take a state-changing action`，未明确动作前提/相关状态变化后可重试，亦未细分新信息获取与世界状态改变。开头“change the world or reveal new information”保留信息价值，所以不能夸大成“禁止所有look/inventory”；真正问题是触发后禁止重复的作用时段与例外没有清楚界定。

这是原案继承的范围风险，不是B新增禁令；仅称current evidence支持它并不足以处理这个风险。M6的实际不可用移动反馈没有落实为u2的状态前提修正。**是否A本来也会Keep，完全未知。**

### Goal、Checks与落地

Goal保持冻结原文，未变成新的算法目标。Checks c1–c3原样：c1观测新位置/换类与不回扫，c2观测no-op转state-changing，c3保留处理交付和灯行为。其结构仍引用有效u1/u2，但c1未专门区分类别采样与同类未查位置，c2也未补状态变化后可重试的范围。Checks不能替最终指令补上缺失前提。

编译器准确落实u1替代、u2 Keep；没有编译失真迹象。问题出在实际策略构造/保留判断，而非reason没有进入编译。未调用Editor，不评价实际Patch或行为。

## 3. 各对象对照（A缺失不能补造）

| 对象 | Original | Effective A | Effective B |
|---|---|---|---|
| u1方向/顺序 | 同类编号单向，耗尽后换类 | 不可得 | 跨类型采样，少量同类后切换，其他采样后才回剩余编号 |
| u1信息前提 | 全局未查/系列耗尽，另有近期反循环 | 不可得 | 明确最近两步；但保留其他类型未访问/已采样等累计前提 |
| u1结束 | 当前Update以找到目标/预算为目标；Parent有位置检查一次边界 | 不可得 | 新增types或locations检查一次的结束表达 |
| u2 | 无效后不重复等价动作，立即state-changing | 不可得 | 完全Keep，状态条件未收窄 |
| Goal / Checks | 原文 | 不可得 | 原样 |
| 实际A/B语义差异 | — | **无法比较** | 只能相对Original评价 |

## 4. 全文对照

### Original Goal

> {original['goal']}

'''
for i in range(2):
 comparison+=f'### {original["updates"][i]["id"]} Original\n\n> {original["updates"][i]["text"]}\n\n**Effective A：未获得。**\n\n**Effective B：**\n\n> {ep["updates"][i]["text"]}\n\n'
comparison+='### Checks（Original与B相同）\n\n```json\n'+json.dumps(ep['checks'],ensure_ascii=False,indent=2)+'\n```\n\n'
comparison+=f'实际结构化输出见 {L("B Preconditioner","runs/B/preconditioner.json")}、{L("B Effective","runs/B/effective_plan.json")}；原始当前执行与菜单见 {PL("固定共同输入","config/common_payload_without_memory.json")}。'
write('P3B_UPDATE_COMPARISON.md',comparison)

attribution=f'''# P3-B Memory归因：有显式历史解释，但没有可估计的A/B增量

**A没有有效响应，所以无法判断“加入Memory是否促成了相对无Memory的不同且更合理更新”。不能把B相对Original的变化冒充B相对A的历史增量；也不能报告“观察到零增量”。本次增量是未能检验。**

B的显式reason确实引用了M6/M3的残留循环、遗漏与指导未稳定遵循，并实际改变u1。这个事实比“仅在reason中提Memory、全文不变”更具体，但仍不满足预注册的完整增量归因：没有A参照，新增规则又有支持不足。以下只检验B自身历史链条的质量。

所有历史材料来自 {PL('冻结B Memory','config/memory_B.json')} 的entries与sources；更细来源见 {PL('预注册历史索引','reports/P3A_MEMORY_EVIDENCE.md')}。没有M10，没有事后认识。

## 1. 共有当前证据已经能支持的判断

- P6在大量drawer上消耗预算、P8在少数位置循环、P10:32才在diningtable找到apple：支持改善位置覆盖/减少无信息重复，允许尝试其他搜索安排；不独立证明跨类最好。
- 原Actor两组历史：可质疑全局visited/耗尽状态，允许当前/近期可见线索。B明确last-two条件不需要独有历史信息才能提出。
- P1:4 Nothing happens、P7:11/12重复look、P8:39/P10:25空inventory：能支持状态相关的去重纠正；B保持原u2，没落实范围收窄。
- 当前Parent/Goal/G1及P3获取交付、P7错误knife、P10处理交付已支持精确目标和必要行为保留。B保留no-substitute并不自动构成M8独有增量。

由于A缺失，连“B独有的当前证据纠正”都不能确认。这里只能说这些B要求可由共有证据成立，不能直接计作Memory贡献。

## 2. B实际引用的编辑—响应链

| Memory /实际Diff | 对应行为与局限 | B明确解释与实际要求 | 支持范围判定 |
|---|---|---|---|
| M6，`sources[S1_R03/diff]`：current/recent反循环，明显cabinets/fridge没找到后扩展drawers/shelves/diningtable，高步数优先新位置；联合精确对象/温度编辑 | Q4:12 diningtable发现bread，13取、15cool、17place，相对Parent50步失败获救；P2:15 countertop3找到bread并20成功，Q2反复countertop2、未去3且50失败；Q6:4等无效move，49才取plate、50到fridge未完成 | Adjustment.reason称M6/M3反循环和broader-search语言未稳定遵循、仍漏位置；u1从类内穷尽改成breadth-first sampling | **显式引用的是实际编辑后混合反馈，链条部分成立。**它支持对强效果承诺保持限制、重新考虑覆盖；不证明先采样所有其他类型再回同类，也不支持类别采样结束 |
| M3，`sources[S1_R02/diff]`：新增通用开容器/少空回访/精确对象/条件clean/交付，同时收窄灯任务 | P5错用soapbottle且50步失败；Q5:19到bathtubbasin发现dishsponge，20取、22clean、24place；其他任务仍循环，部分简单任务增步 | 与M6一起作为广度探索与反循环语言未稳定兑现的依据 | 支持扩大覆盖与精确目标的联合方向，以及收益有条件；不隔离证明某个采样调度有效。B未提供该历史如何确定few、only-after及新终止条件的依据 |
| M8，`sources[S1_R03/diff]`、`sources[S1_R04/diff]`：精确类别和温度条件不使用近似物 | R03 P5操作pot而Q5未操作；P10及R04P1操作cup而Candidate避免，双方仍有步限失败 | B明确说M8支持保留no-substitute，最终u1保留 | 保留有据，但原Plan/当前P7已经有同一约束，属于相容支持，不能证明新增变换；不把knowledge中absent当隐藏环境不存在事实 |

表中具体S1_R03/S1_R02 Diff及step是研究者对M6/M3/M8来源的展开，B原文没有逐条列出这些历史step。模型明确陈述的是“历史指导未稳定遵循、仍有遗漏”，不能进一步声称它已用Q2/Q6解释了only-after或类别终止条件；这些附带要求恰恰缺少相应说明。

B未明确讨论M1/M2/M7/M9对本次决定的作用，不能宣称模型完全没有阅读它们。M9的有条件回源/额外检查增步仍可用来离线核查B的限制，但这是研究者核查，不补写成B已经使用的论据。

## 3. 三个关键推导边界

**方向与调度。** B总体reason把“historical Memory show exhaustive same-type sweeps or cycling consume budget”连在一起。M6/M3主要证明编辑后仍循环/遗漏，当前P6能观察到长drawer搜索；这些不同证据不等于已隔离证明所有类内穷尽有害。宽泛地概括成历史已支持某个反向调度，会越过证据边界。

**动机与附带约束。** 改成跨类型探索有当前问题动机，可以作为新策略试验；但“其他类型采样完才回剩余编号”“全部types或locations一次即可结束”需要独立理由。M6同类实例遗漏不能为推迟所有同类余项提供充分支持，也没有证明类别采样能代替位置覆盖。B没有给出对应的新假设及观测预期。

**局部信息与全局进度。** B明确两步历史约束，却在最终文本继续使用remain unvisited/have been sampled/all ... inspected once。reason声称能力更匹配，不等于这些状态判断已可执行。短期新颖性不能恢复全局穷尽/采样状态。

## 4. 按预注册类型记录

| 类型 | 本次结论 |
|---|---|
| 当前证据纠正 | B对近期反循环有具体化、改变搜索方向有动机；但u2范围未纠正。不能判断哪些是A没有的纠正 |
| 历史信息影响 | B明确引用历史反馈，与u1变换一起出现；只能说显式解释使用了历史，不证明输入Memory导致该变化 |
| 编辑—行为响应预条件化增量线索 | **未能建立完整A/B线索。**B内部有“旧提示未稳定兑现→重构搜索”的部分联系，但没有A参照，且替代方案仍有无据限制 |
| 无依据新承诺 | B的only-after全局采样续行条件及types-or-locations终止条件支持不足；few本身不是固定数值，不应一概判错 |
| 无实质更新差异 | **不能判定。**没有Effective A，既不能宣称不同，也不能宣称等价或零增量 |

## 5. 可确认与不可确认

可确认：合法B真实调整了u1、保持u2，显式引用M6/M3/M8，编译准确；广度探索的合理动机没有约束住全部附带要求，能力限制也没有落实到所有最终条件。

不可确认：A本会怎么输出；Memory是否导致变换；有无Memory哪组更好；M6单条的贡献；生成随机性/长度/顺序作用；任何Skill执行成功率或步数收益。没有Editor/Replay，也没有语义重采样。

**下一步首先是经另行授权补齐缺失A、仍保持冻结请求与参数，才能尝试完成比较；不是现在做候选行为Replay，也不是依据B一份结果增加Prompt补丁。**即使后续补齐A，调用时点不同和单次随机性仍须记录；稳定增量需要再预注册重复对照。局部Memory消融应等到存在可复核的增量信号后再确定对象，不预设M6就是唯一原因。
'''
write('P3B_MEMORY_ATTRIBUTION.md',attribution)

decision=f'''# P3-B 阶段结论

**本次未完成有效A/B输出对照：A在300秒读取超时，B在57.498秒返回合法ready。两次调用预算已用完，没有重试或第三组。**

对于“加入Memory是否产生不同且更有依据的Effective Update”，答案是：**目前无法判断相对无Memory的增量。**B确实相对固定Original改变u1，但不能用Original代替缺失A。

| 必答问题 | 结论 |
|---|---|
| 1. A如何调整u1/u2？ | 无有效响应，未知；不是Keep或合法no_change |
| 2. B如何调整？ | u1由同类编号穷尽改成跨类型breadth-first采样/近期去重；u2保持原样。Goal/Checks不变 |
| 3. 两组是否有实质不同Effective？ | 无法比较，A不存在Effective。只确认Original→B的实质变化 |
| 4. 哪些纠正当前证据足够支持？ | 近期反循环、质疑全局visited、限定无效重复的状态前提、保留精确目标及处理交付；其中u2的范围问题B仍未修正 |
| 5. 是否观察到额外历史响应变换？ | B显式把M6/M3的旧搜索提示未稳定兑现与重构u1相联系，M8用于保留精确对象；但没有A，不能称为已观察到AB历史增量 |
| 6. B是否引入无据承诺？ | 是：其他类型采样后才返回同类余项的排他条件、types或locations一次的结束边界支持不足；还残留unvisited/sampled全局进度依赖。few不是固定数值批次；跨类型探索本身仍可合理 |
| 7. 是否支持机制产生合理增量？ | 不足。B有部分历史认识到方向变换的显式链条，但附带构造问题未消除，且比较臂缺失。不能判机制有效，也不能据此判Memory永远无用 |
| 8. 哪些仅单次线索？ | B对历史混合反馈的解释与策略选择、近期约束的局部落实、反复出现的全局条件与结束风险；不是模型内部因果机制或行为退化证明 |
| 9. 后续优先什么？ | 先经独立授权补齐A技术失败，再按原规则完成对照；之后若出现合理增量，优先预注册重复验证稳定性，再考虑定向消融。当前不优先Editor/行为Replay或新Prompt迭代 |

B的最关键文本：

> Return to remaining numbers in a series only after other plausible types or locations have been sampled.

> Continue until the exact target is found or all plausible candidate types or locations have been inspected once.

这两项不能仅凭“扩大覆盖”的动机获得充分支持；M6同类别位置遗漏尤其不能自动证明应等待其他类型全部采样。文本风险尚未经过Actor执行，不称为已发生过早停止或退化。

u2虽被reason称为executable，最终仍保留无效后不重复等价动作及立即state-changing，未明确条件变化后的重试/有效信息获取。不能把解释合理等同于问题已纠正。

## 用量、保护与交付

- A一次HTTP尝试，ReadTimeout 300.341秒；没有响应，Token和账单未知。B一次HTTP尝试，57.498秒，返回deepseek-v4.1-flash，finish_reason=stop。
- B实测输入474,757、输出5,270（其中reasoning 4,751）、总计480,027 Token；cached字段未提供。reasoning不重复累计。实验总Token因A未知而未知，未推算货币费用。
- 请求正文及字节哈希等于P3-A；唯一变量仍是历史Memory。完整记录、原响应与确定性编译见 {L('执行报告','reports/P3B_EXECUTION_REPORT.md')}。
- {L('独立评价与全文对照','reports/P3B_UPDATE_COMPARISON.md')}；{L('历史响应归因与限制','reports/P3B_MEMORY_ATTRIBUTION.md')}；{L('保护核验','results/protection.json')}。
- 仅新增p3b_results脚本和产物，旧P3-A冻结、V23/V23.2方法、Memory、Campaign和Test未修改。Editor/Actor/Replay/Gate/Memory/Diagnosis/环境调用均0。

已停止。没有自行重试A、没有第三次模型调用，没有进入P3-C、Editor或Candidate Replay。
'''
write('P3B_DECISION.md',decision)

# Preserve pre-registered template and fill only actually observed information in a new copy.
template=read(P/'config/evaluation_template.json');template['status']='P3B_A_timeout_B_valid_no_complete_AB'
for row in template['updates']:
 uid=row['update_id'];row['A_technical_status']='ReadTimeout; no response; all A model-result fields remain null'
 row['B_decision']=b['decision'];row['B_reason']=b['reason'];row['B_adjustments']=[a for a in b['adjustments'] if uid in a['from']]
 row['B_checks']=ep['checks'];row['effective_B']=next(x for x in ep['updates'] if x['id']==uid)
 row['material_difference']=None
 row['difference_evidence']='No A output; no AB difference can be evaluated.'
 row['new_commitment_risk']='u1: global sampling progress, only-after resumption and types-or-locations termination unsupported.' if uid=='u1' else 'u2: unchanged state-scope ambiguity; not a new B prohibition.'
 row['attribution_boundary']='B explicit historical reasoning is not evidence of AB incremental effect without A.'
 row['conclusion']='AB increment not evaluable; B independently assessed in report.'
(E/'results/evaluation_filled.json').write_text(json.dumps(template,ensure_ascii=False,indent=2)+'\n')
