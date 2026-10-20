"""Integrate same-format valid A/B; report only, no further model calls."""
from pathlib import Path
from copy import deepcopy
import json,hashlib,importlib.util,subprocess,re
from datetime import datetime,timezone
from src.skill_evolution.v23 import preconditioner as pc
E=Path(__file__).resolve().parent;P=E.parent;R=P/'p3b_results';ROOT=P.parents[3]
A=P/'p3b_A_format_001/runs/A';B=E/'runs/B';OLD=R/'runs/B';REV=E/'report_revision'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def link(p,s):return f'[{s}]({p})'
def quote(s):return '> '+s.replace('\n','\n> ')
aq,bq=read(A/'request.json'),read(B/'request.json');ap,bp=[json.loads(q['body']['messages'][1]['content']) for q in [aq,bq]]
ar,br=read(A/'preconditioner.json'),read(B/'preconditioner.json');ae,be=read(A/'effective_plan.json'),read(B/'effective_plan.json');original=read(P/'config/original_plan.json')
assert aq['body']['messages'][0]==bq['body']['messages'][0]
x,y=deepcopy(aq),deepcopy(bq)
for z in [x,y]:j=json.loads(z['body']['messages'][1]['content']);j.pop('memory');z['body']['messages'][1]['content']=j
assert x==y
assert ap['memory']=={'entries':[],'sources':{}} and bp['memory']==read(P/'config/memory_B.json')
assert [e['id'] for e in bp['memory']['entries']]==['M1','M2','M3','M6','M7','M8','M9']
assert ap['plan']==bp['plan']==original
assert [r['ref'] for r in ap['runs']]==[r['ref'] for r in bp['runs']]==['P1','P3','P6','P7','P8','P10']
assert pc.compile_effective_plan(ar,ap)==ae==original
assert pc.compile_effective_plan(br,bp)==be
assert be['goal']==ae['goal'] and be['checks']==ae['checks']
assert be['updates'][1]==ae['updates'][1] and be['updates'][0]!=ae['updates'][0]
assert be['updates'][0]['text']==br['adjustments'][0]['to'][0]['text']
for base in [P/'p3b_A_format_001',E]:
 for f,h in read(base/'config/freeze.json')['files_sha256'].items():assert sha(base/f)==h,f
for d in [A,B]:
 raw=read(d/'http_response.txt');resp=read(d/'response.json');assert raw['choices'][0]['message']['content']==resp['content']==(d/'raw_output.txt').read_text();assert json.loads(resp['content'])==read(d/'preconditioner.json');assert resp['finish_reason']=='stop'
assert sha(E/'config/preconditioner_prompt.md')==sha(P/'p3b_A_format_001/config/preconditioner_prompt.md')
selection={'at':datetime.now(timezone.utc).isoformat(),'A':{'path':str(A),'request_sha256':sha(A/'request.json'),'effective_sha256':sha(A/'effective_plan.json')},'B':{'path':str(B),'request_sha256':sha(B/'request.json'),'effective_sha256':sha(B/'effective_plan.json')},'system_sha256':hashlib.sha256(aq['body']['messages'][0]['content'].encode()).hexdigest(),'system_identical':True,'all_other_request_fields_except_memory_identical':True,'memory_ids':['M1','M2','M3','M6','M7','M8','M9'],'current_runs':['P1','P3','P6','P7','P8','P10'],'same_prompt_input_control_passed':True,'protocol_amendment':'Both arms use authorized output-format addition; not byte-identical original P3A prompt. Historical reports and freezes retained.','causal_mechanism_established':False,'new_http_requests':1,'new_environment_calls':0}
save(E/'results/selected_sources.json',selection)
paths=[('A initial',R/'runs/A'),('B original prompt',OLD)]+[(f'A original retry_{i:03d}',P/f'p3b_A_retry_{i:03d}/runs/A') for i in range(1,5)]+[('A format (selected)',A),('A original retry_005',P/'p3b_A_retry_005/runs/A'),('B format (selected)',B)]
ledger=[]
for label,d in paths:
 m=read(d/'run.json');r=read(d/'response.json') if (d/'response.json').exists() else {};u=r.get('usage');ledger.append({'label':label,'path':str(d),'status':m['status'],'error':m.get('error'),'usage':u,'elapsed_seconds':m['elapsed_seconds'],'http_attempts':m['http_attempts'],'started_at':m['started_at'],'finished_at':m['finished_at'],'finish_reason':r.get('finish_reason')})
known={k:sum((r['usage'] or {}).get(k,0) for r in ledger) for k in ['prompt_tokens','completion_tokens','total_tokens']};pair={k:read(A/'response.json')['usage'][k]+read(B/'response.json')['usage'][k] for k in known}
save(E/'results/cumulative_ledger.json',{'attempts':ledger,'known_usage':known,'selected_pair_usage':pair,'all_attempts_usage':None,'reason':'initial A ReadTimeout usage unknown','new_http_requests':1,'automatic_retries':0})
rows=[]
for r in ledger:
 u=r['usage'];token=[str(u[k]) if u else '未知' for k in ['prompt_tokens','completion_tokens','total_tokens']];cache=(u or {}).get('prompt_tokens_details',{}).get('cached_tokens');reason=(u or {}).get('completion_tokens_details',{}).get('reasoning_tokens','未知');status='合法ready' if r['status']=='valid' else r['error']['message'];status='ReadTimeout，无响应' if r['label']=='A initial' else status
 rows.append(f"| {r['label']} | {status} | {token[0]} | {token[1]} | {reason} | {cache if cache is not None else '未提供'} | {token[2]} | {r['elapsed_seconds']:.3f} |")
common=P/'config/common_payload_without_memory.json';memory=P/'config/memory_B.json';hist=P/'reports/P3A_MEMORY_EVIDENCE.md';backup=REV/'before/reports'
header='**本版主对照改为：合法A_format_001（无Memory）与新B_format_001（真实R05 Memory）。两组完整system Prompt逐字相同，其他请求字段除Memory外完全一致。原B和失败尝试仅作历史记录，不与新B混用。**\n'
(R/'reports/P3B_EXECUTION_REPORT.md').write_text(f'''# P3-B执行报告：同格式Prompt对照完成

{header}

## 1. 结果来源与协议修订

A使用{link(A/'preconditioner.json','已保存合法A')}，未重新调用；B使用{link(B/'preconditioner.json','本次新B')}。A ready、adjustments=[]；B ready、一条u1替换；均通过原解析器与编译器，checks=null。

双方使用用户批准保留的同一格式修复，只明确字段归属、非空依据/解释和引用分隔，没有新增策略性要求。{link(E/'config/preconditioner_prompt.md','共同Prompt')}与{link(E/'config/prompt.diff','相对原版Diff')}逐字等于A格式版。本次没有再编辑Prompt。

这恢复了**当前配对的同Prompt、唯一Memory输入变量**。它是经用户授权的P3-A格式协议修订，不声称原冻结Prompt逐字未变。旧P3-A、原B、各次失败和此前异Prompt报告均保留；旧同Prompt原A仍没有合法输出，但已不作为本版主比较臂。

## 2. 实际控制条件

| 项目 | 核验 |
|---|---|
| system Prompt | 逐字相同，SHA-256 `{selection['system_sha256']}` |
| Original Plan | 同一P1-B R05授权重试合法Diagnosis，Goal、Updates、basis、Checks、顺序相同 |
| Parent / Grouping / command_sets | 完全一致，G1—G4与既有候选不变 |
| 完整当前执行 | P1、P3、P6、P7、P8、P10，两组相同；未增加P2/P4/P5/P9 |
| Actor背景 | 原V23当前观察/候选、最近两组历史、步数限制不变 |
| Memory | A空entries/sources；B为M1/M2/M3/M6/M7/M8/M9及全部冻结sources，无M10 |
| 模型/参数 | 同deepseek-v4.1-flash、temperature=1、Thinking enabled、reasoning_effort=medium、stream=false、max_tokens=16384、timeout=300秒 |
| Schema/编译 | 原实现不变，均合法ready、HTTP200、finish_reason=stop；返回模型相同 |

{link(E/'results/selected_sources.json','机器核验及请求哈希')}。分别删除用户输入memory后，完整请求（含system、参数、端点、timeout）相等；不是仅比较Prompt文件名。

## 3. 调用与全部成本

本次只新增B一次HTTP，自动重试0，耗时90.796秒，输入474,839、输出16,098（其中reasoning 15,426），总490,937 Token，缓存输入1,024。完成原因stop且JSON完整，不以接近预算误判截断。

所选A耗时43.584秒，总65,026 Token。当前合法配对共{pair['total_tokens']:,} Token（输入{pair['prompt_tokens']:,}、输出{pair['completion_tokens']:,}）。

| 尝试（实际顺序） | 状态 | 输入 | 输出 | 其中reasoning | 缓存输入 | 总Token | 秒 |
|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

全研究累计9次HTTP，已返回usage合计{known['total_tokens']:,} Token；首次A超时服务器消耗未知，所以总体消耗仍未知。reasoning/缓存分别属于输出/输入子集，不重复加总。未提供可靠货币费用，不推算账单。{link(E/'results/cumulative_ledger.json','完整账本')}。

retry_004/005的首个历史引用拒绝涉及斜杠当前轨迹被正则识别为历史路径，不视为已证实的Memory捏造。retry_004还独立有层级/空字段错误；retry_005为空adjustments。无效输出均未人工修补或纳入有效语义对照。原异常处理usage元数据的null finish_reason以原HTTP/response中的stop校正汇总，不改原文件。

## 4. 验证、归档和边界

B非空to条目本次只有id/text，外层basis/reason有效，提供一次非空Adjustment遵守契约的实际样本；不能证明格式修复已稳定解决生成问题。原编译器重复编译A/B一致；A Effective等于Original，B仅u1文本变化，Goal/u2/Checks保持。B Effective的basis保留Original谱系，历史引用在Adjustment.basis中，这是原编译规则。

{link(E/'config/freeze.json','调用前冻结')}；{link(B/'request.json','完整B请求')}；{link(B/'http_response.txt','原HTTP')}；{link(B/'raw_output.txt','B原文')}；{link(B/'effective_plan.json','B Effective')}；{link(A/'effective_plan.json','A Effective')}。

两份有效样本不是重复实验：A来自先前格式修复尝试，B为本次单次结果，调用时点、输入长度/缓存及前期非对称技术失败限制因果推广。没有因语义结果选优或追加调用。Editor/Actor/Replay/Gate/Memory更新及环境执行均0。

仅新增本次B归档并更新四份主报告与评价JSON。{link(backup/'P3B_EXECUTION_REPORT.md','上一版报告备份')}；{link(E/'results/protection.json','保护核验')}。原请求/响应、历史Prompt、Memory、方法、Campaign和Test保持。
''')
(R/'reports/P3B_UPDATE_COMPARISON.md').write_text(f'''# P3-B Update对照：同Prompt的A与新B

{header}

## 1. A独立评价

A ready、adjustments=[]，全部保留。reason认为：

{quote("the numbered-series/type-switch heuristic makes the coverage requirement implementable with the Actor's two-step history")}

但实际u1仍含`not yet inspected in this search`和`once that series is exhausted`，没有解释两步历史如何恢复全局访问/耗尽状态。编号及局部单向探索可以有合理动机，不能一概判错；本次reason对整条规则可执行的肯定却不充分。当前P6后期长drawer扫描耗尽预算，也不足以证明“必须扫完再换类”。

u2保留无效后不重复相同/等价动作及立即state-changing，未明确前提改变后的重试、有信息价值动作的边界。当前P1:4、P7:11/12、P8:39/P10:25足以检查该问题。原文首句允许reveal new information，不能夸大成完全禁止look/inventory。

Goal/Checks及精确目标、处理交付、desklamp要求保留，无新增条款；但不代表原有范围问题解决。Keep合法，不按没有Adjustment判错，也不以reason“Memory为空”断言模型仅因无历史而Keep。

## 2. 新B独立评价

新B只替换u1，basis引用当前P6/P8/P10、G3及M3/M6。它没有像旧B一样引用M8，也不能沿用旧B原文冒充本次输出。

它保留单向编号探索、到达开闭容器、近期空位置避免重复、精确对象/不替代，新增明确从当前admissible go-to列表选目的地，并把核心优先级改为：

{quote('sample a receptacle type not yet used in this search rather than another instance of the type just swept')}

跨类型探索有当前问题动机及历史混合反馈支持，可以作为新假设。**具体实现仍有两个关键问题：**

1. `not yet used in this search`需要累计类别访问状态。当前动作候选说明可选动作，不说明哪些类别访问过；两步近期信息也不等于全程类型进度。reason称“executable from recent observations and admissible list”，没有在最终文本补足这一前提。
2. 新终止条件：

{quote('Continue until the exact target is found or every receptacle type available in the room\'s action list has been sampled once.')}

这把类别采样一次作为搜索完成边界；M6的同类countertop 3遗漏恰好说明“到过该类”不等于覆盖该类其他实例。历史Diff原文是`all plausible candidate receptacles have been inspected once`，并未授权把位置覆盖替换为类别一次采样。它可能提前放弃仍有未查同类位置，但没有Actor执行，不能说已发生停止/失败。

本次没有固定数字批次、没有明确保证progress；括号内类别是举例，不能机械解释成固定全局顺序。与旧B不同，也没有逐字规定“所有其他类型都采样后才允许回同类”。新B偏好未用类别，例示换类别后再回drawer；这些具体条件和类别终止风险须按本次文本判断，不套用旧报告。

u2、Goal、Checks与A完全相同。精确目标、获取、温度处理、交付、desklamp的原有目标保留；搜索停止条件可能影响找到目标前的覆盖，不能仅凭Goal仍在就宣称全部有效行为都保证保留。

## 3. 原始事实核查

{link(common,'共有当前证据')}：P6:18到drawer4后继续，P6:50到drawer20但尚不能称已打开检查20；整条没有到cabinet，但前期也去countertop/sinkbasin。P8反复cabinet/sinkbasin且没到shelf1，但P8:2到bathtubbasin、P8:7/13/20到countertop，所以不能把整条P8说成只访问两种类别。P10:32到diningtable才发现apple，33取、35cool、38交付。它们说明循环/覆盖问题，不隔离证明最优类别安排。

## 4. 实质差异表

| 内容 | A Effective | 新B Effective | 判断 |
|---|---|---|---|
| 搜索安排 | 单向穷尽同类编号后换类 | 优先未用类别而非刚扫类别的下一实例，仍保留类内单向扫描 | 有方向/调度变化；合理探索动机不证明唯一优越性 |
| 候选依据 | 未检查位置及近期观察 | 明确从admissible go-to选下一目的地 | 可由共有当前协议/候选支持，不是历史独有收益 |
| 进度依赖 | 全局位置未查、类内耗尽 | 全局类别未用、所有类别已采样 | 换了状态粒度，没有彻底消除不可见信息前提 |
| 回访/换类 | 耗尽同类才换；之后可重入 | 优先新类型，例示换类后回drawer；刚离开空位置不回访 | 不强行解读为所有类型采样完才可返回；仍可能限制有效覆盖 |
| 搜索终止 | u1未新增类别完成边界 | 每个可用类别采样一次即可结束 | 新增依据不足的粒度变化，与M6同类遗漏警示不匹配 |
| u2 | Original Keep | 完全相同Keep | 无更新增量；状态改变后的重试边界均未修正 |
| Goal/Checks/no-substitute | 保留 | 保留 | 无差异，不能算B额外修复 |

## 5. 全文及实际Adjustment

### Goal（Original=A=B）

{quote(original['goal'])}

### u1 Original = A

{quote(original['updates'][0]['text'])}

### u1 新B

{quote(be['updates'][0]['text'])}

### u2 Original = A = B

{quote(original['updates'][1]['text'])}

### A完整输出

```json
{json.dumps(ar,ensure_ascii=False,indent=2)}
```

### 新B完整输出

```json
{json.dumps(br,ensure_ascii=False,indent=2)}
```

### 保持不变的Checks

```json
{json.dumps(original['checks'],ensure_ascii=False,indent=2)}
```

原始字段见{link(A/'effective_plan.json','A Effective')}、{link(B/'effective_plan.json','新B Effective')}。本次u1实质不同，u2/Goal/Checks相同；没有Editor Patch或行为结果，不能推定任务成功率。
''')
(R/'reports/P3B_MEMORY_ATTRIBUTION.md').write_text(f'''# P3-B历史响应增量归因：同Prompt配对

{header}

**同Prompt混杂已消除。现在观察到：A保留原案；B显式用M3/M6的编辑后响应重构u1。存在历史响应参与更新方向选择的初步线索，但没有证明整条替代Update更合理，尤其类别采样结束和全局进度前提仍无充分支持。**

## 1. 共有当前证据能够独立支持的部分

P6长drawer扫描、P8反复访问、P10很晚才换到diningtable已支持质疑覆盖安排并尝试跨类别探索。Actor两步历史已足以质疑全局visited/穷尽；可选动作列表已经可用于选择合法移动。P1/P7/P8/P10的no-op与重复信息动作已足以检查状态相关的重复限制。

因此A没改、B改，不等于B所用理由全部来自独有历史知识。要识别历史增量，必须看“旧Skill怎么改过—后续实际怎样—为何影响本次文本”，不能仅用A/B差异或Memory引用计数。

## 2. B明确表达的编辑—响应关系

B的Adjustment.reason实际说：

{quote('Memory M3/M6 record that the anti-cycling/revisit-avoidance wording was not reliably followed and did not by itself break the cycling/step-limit failure, whereas added search breadth combined with exact-target guidance did help.')}

它以此改变u1的优先级，不是仅在reason中提Memory而全文Keep。A没有该历史解释，最终保留同类穷尽。下面是研究者对其引用的真实sources展开，不能视作模型逐步陈述过的隐藏推理。

| 来源 | 实际Diff | 配对响应与局限 | 对当前变换的支持 |
|---|---|---|---|
| M3，sources[S1_R02/diff] | 新增通用检索/开容器、少空回访、精确对象、条件clean、直接交付；同时收窄灯适用范围 | P5错取soapbottle且失败；Q5:19到bathtubbasin找到dishsponge、20取、22clean、24place成功；其他实例循环仍在，部分简单任务增步 | 支持扩大覆盖与精确目标联合方向可能有益，反循环文本未稳定兑现；不证明一种类别采样规则就是有效成分 |
| M6，sources[S1_R03/diff] | current/recent反循环，未找到时扩展drawers/shelves/diningtable，高步数优先新位置；联合温度与精确目标指导 | Q4:12到diningtable发现bread，13取、15cool、17place；Parent该对50失败。P2:15到countertop3拿bread并20成功，Q2反复countertop2、未去3且50失败。Q6:49才取得plate、50到fridge未完成 | 支持重新考虑位置覆盖、警惕旧指导未落实和预算/同类遗漏；不能推出“每类别一次就结束” |

完整知识和来源：{link(memory,'冻结Memory')}；{link(hist,'预注册证据索引')}。本次再核对了上述原始Diff/动作/结果。历史为联合编辑和单次执行，不可将整体收益/退化独立归因某个子句。

B的总reason称`the effective ingredient is sampling additional receptacle types plus exact-target/no-substitute guidance`。这是比记录本身更强的成分归因：M3/M6观察与扩大覆盖一致，但没有隔离证明“类别采样”这一调度就是起作用的成分。当前P10也有换类别后成功，不因此证明类别一次覆盖充分。

## 3. 反例有没有约束最终要求？

B确实吸收了“旧反循环文字未稳定消除循环”，没有把所有原规则完全否定：仍保留近期空位置避返和单向扫描。改为跨类型探索作为新假设可以合理。

但M6同类countertop3被遗漏与Q6过晚获取的限制，没有在最终文本形成相应的实例覆盖/后处理预算边界。相反，B要求所有类型采样一次即可结束，可能在某类别仍有未查实例时终止。这是对最终规定可直接提出的证据一致性问题；不能据此推断模型内部完全没有读反例，也不声称已导致Actor退化。

B从候选列表构造未用类别选择，候选却不编码全局历史。这一执行前提也未在实际Update中落实。reason自称可执行不能替代最终条件核查。

## 4. 按预注册类型判定

| 类型 | 本次观察 | 判定 |
|---|---|---|
| 当前证据纠正 | B改变长同类安排、明确go-to候选；A未改 | 当前材料本就允许，不能全部计为Memory独有贡献 |
| 历史信息使用 | B真实引用M3/M6，知识还含实际旧编辑和混合响应 | 不只是一般任务示例，存在明确历史解释 |
| 编辑—响应预条件化线索 | 旧反循环/扩大覆盖的混合响应→重构u1的优先级，最终文本确实变化 | **方向层面的初步线索成立**；单次样本不证明因果，整条Update未满足“变化有据且不引入明显无据限制”的充分条件 |
| 无依据附带要求 | 类别一次结束；全局未用类别/全部采样状态；effect ingredient过强概括 | 不能当作合理增量，显示历史限制没有充分约束替代构造 |
| 无实质更新差异 | u2、Goal、Checks、精确目标保留要求相同 | 这些方面未观察到增量；不能称全部无差异 |

本次basis只显式引用M3/M6，没有M8；不能沿用旧B的M8理由。本输入仍包含七条Memory，无法把差异归因于M6单条，也不能证明其余条目没有作用。

## 5. 核心回答

**加入Memory的这份输出与无Memory不同，且具有可追溯的编辑—响应解释；但“不同且整体更有依据”没有成立。**历史反馈似乎参与了从原策略到另一探索方向的选择，尚未可靠约束替代方案的进度前提和结束边界。

同Prompt恢复后，仍是两个单次样本；输入长度/缓存、调用时点和前期非对称技术失败不能排除。格式补充版也属于用户授权协议修订，不混同最初原Prompt实验。可报告响应预条件化线索，不能报告稳定因果收益，更不能报告Skill性能提升。

后续若继续，优先预注册同条件重复以检验这一方向信号是否稳定，再决定定向消融；当前不优先执行存在明确终止风险的Candidate，也不自动追加Prompt规则。本次停止。
''')
(R/'reports/P3B_DECISION.md').write_text(f'''# P3-B阶段结论：同Prompt有效A/B已补齐

{header}

## 1. 实验控制与实际结果

本次保留A已授权的格式修复，未再修改策略性Prompt。B完整请求除Memory外与A一致；双方均由原解析器接受并由原编译器产生Effective Plan。因此当前配对的输入控制与结构验收通过。此格式修复是对最初P3-A协议的明确修订，旧冻结和失败尝试仍保留。

- A：ready，Keep全部Original Updates。
- B：ready，替换u1，优先探索尚未使用的类别；仍保留单向扫描、开闭容器与精确目标要求。u2、Goal和Checks不变。
- B引用M3/M6的历史编辑与混合响应，确实对应最终u1变化。不是只在reason中提及Memory。

## 2. 三项判断分别成立到什么程度？

**A. 历史响应是否影响更新取舍？——出现初步方向性线索。** B明确以旧反循环指导未稳定奏效、扩大覆盖的条件性收益解释策略变换。可是当前执行本身也支持探索其他类别，单次A/B不能证明此变化必然由Memory引起，也不能隔离M6作用。

**B. 替代Update是否更合理？——未充分通过。** B引入`every receptacle type ... has been sampled once`的结束条件，未说明为何每类一次即可替代具体位置覆盖。M6恰有同类其他实例遗漏的反例。B仍依赖全局未用类别/全部类别采样记录，当前候选与两步历史不能一般性提供这些状态。方向变化不能推导出整体构造改善。

**C. 是否保留有效行为与合理探索？——文本部分保留，但尚有风险。** 精确对象、温度/交付和灯任务Goal保留，跨类别探索可以是合理假设。没有证据证明类别一次终止、全局进度前提合理。u2未变，对状态变化后重试的边界也未获得增量修正。未执行Actor，不能声称实际发生提前停止或行为退化。

## 3. 怎样区分当前纠正与历史增量？

先独立评价A/B每项行为要求；再定位B相对A的实质差异，并追溯它是否利用了“历史改了什么—随后观察到什么”的关系。当前事实已经支持的合法动作、减少重复等，不直接记为历史独有收益。引用历史但未改变Update不算变换；不同但无据的类别终止条件也不算改善。本次仅u1方向变化具备响应预条件化线索，完整替代方案未满足有据构造要求。u2、Goal、Checks没有观察到增量。

## 4. 成本、保护与下一步

本次新增B一次请求，0重试，90.796秒、490,937 Token；所选合法A/B总555,963 Token。全部历史9次请求已知合计1,390,028 Token，初次A超时消耗未知。无可靠货币账单。没有Editor、Replay、Actor或环境执行。

旧报告先备份，随后只更新四份主报告与评价JSON；{link(E/'results/protection.json','保护核验')}记录历史文件检查。详细对照见{link(R/'reports/P3B_UPDATE_COMPARISON.md','更新对照')}，归因见{link(R/'reports/P3B_MEMORY_ATTRIBUTION.md','Memory归因')}，调用账本见{link(R/'reports/P3B_EXECUTION_REPORT.md','执行报告')}。

**结论：同Prompt对照已完成；观察到有历史响应依据的方向变化，但没有证实Memory稳定改善最终策略构造。** 不晋升默认方法，不宣称Skill性能提升。若后续获授权，先以预注册同条件重复核查方向信号，再决定其他实验；本次不追加Prompt补丁、不开展行为验证，完成后停止。
''')
evaluation=read(P/'config/evaluation_template.json')
evaluation.update(status='same_prompt_valid_pair_completed',sources=selection,input_control_passed=True,mechanism_established=False,A={'response':ar,'effective_plan':ae},B={'response':br,'effective_plan':be},conclusion='Direction-level response-grounded transformation signal; replacement construction not established as better; no behavioral causal result.')
for item in evaluation['updates']:
 uid=item['update_id'];item.update(A_decision='keep',B_decision='replace' if uid=='u1' else 'keep',effective_A=next(u for u in ae['updates'] if u['id']==uid),effective_B=next(u for u in be['updates'] if u['id']==uid))
 item['assessment']=({'material_difference':'Prioritize unused receptacle types; add category-once stopping condition; retain one-direction sweep and exact-target constraints.','historical_basis':['M3','M6'],'supported_signal':'Prior edits and mixed responses explicitly motivate actual direction change.','unsupported_requirements':['Global unused-category progress without demonstrated state support','Every category sampled once as search termination'],'attribution_limit':'Current runs also motivate breadth; joint historical edits and single stochastic pair do not isolate Memory or M6 causality.'} if uid=='u1' else {'material_difference':None,'historical_increment_observed':False,'remaining_issue':'No additional qualification for retry or information action after state change.'})
for item in evaluation['updates']:
 uid=item['update_id'];a=item['assessment']
 item.update(A_reason=ar['reason'],B_reason=br['reason'],A_adjustments=ar['adjustments'],B_adjustments=[j for j in br['adjustments'] if uid in j['from']],A_checks=ar['checks'],B_checks=br['checks'],material_difference=a['material_difference'],difference_evidence=a.get('historical_basis',[]),new_commitment_risk=a.get('unsupported_requirements',[]),attribution_boundary=a.get('attribution_limit','No substantive difference observed; shared residual concerns are not Memory improvement.'),conclusion='Direction-level historical response signal with unsupported replacement requirements' if uid=='u1' else 'No substantive update difference')
save(R/'results/evaluation_filled.json',evaluation)
save(E/'results/execution_receipt.json',{'new_model_http_calls':1,'automatic_retries':0,'environment_calls':0,'same_prompt':True,'only_memory_input_difference':True,'original_parser_and_compiler_passed':True,'selected_pair_usage':pair,'known_cumulative_usage':known,'historical_total_usage_known':False,'strategy_prompt_changed_this_run':False})
spec=importlib.util.spec_from_file_location('protect',ROOT/'experiments/methods/v23_2/v23_2_diagnosis_interface_audit_001/verify_protection.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);v.EXP=E
before=read(E/'config/protected_before.json');after=v.snapshot();allowed=read(REV/'allowed_changes.json')
if isinstance(allowed,dict):
 print('allowed format',allowed);raise RuntimeError('Inspect allowed manifest shape')
changed=sorted(p for p in before.keys()|after.keys() if before.get(p)!=after.get(p));unexpected=sorted(set(changed)-set(allowed))
assert not unexpected,unexpected
for name in allowed:
 b=REV/'before'/Path(name).relative_to(R.relative_to(ROOT));assert sha(b)==before[name],name
protection={'checked_files':len(before),'changed':changed,'authorized_report_changes':allowed,'unexpected_changes':unexpected,'historical_artifacts_unchanged':not unexpected,'previous_report_backups_verified':True,'new_http_calls':1,'new_environment_calls':0,'test_data':'Hash protection only, no Test trajectory analysis'}
save(E/'results/protection.json',protection)
links=[]
for report in (R/'reports').glob('P3B_*.md'):
 for target in re.findall(r'\]\(([^)]+)\)',report.read_text()):
  if target.startswith(('http:','https:')):continue
  path=Path(target.split('#')[0]);assert path.exists(),(report,target);links.append(target)
protection['report_links_checked']=len(links);save(E/'results/protection.json',protection)
(E/'results/git_status_after.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))
print(json.dumps({'protection':protection,'selected_pair_usage':pair,'known_cumulative_usage':known},ensure_ascii=False,indent=2))
