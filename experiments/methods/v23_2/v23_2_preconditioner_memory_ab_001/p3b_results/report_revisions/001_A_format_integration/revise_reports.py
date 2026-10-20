"""Offline report revision integrating valid format-A; preserve original run records."""
from pathlib import Path
from copy import deepcopy
import json,hashlib,importlib.util,subprocess,re
from datetime import datetime,timezone
from src.skill_evolution.v23 import preconditioner as pc
E=Path(__file__).resolve().parent;R=E.parents[1];P=R.parent;ROOT=P.parents[3];A=P/'p3b_A_format_001/runs/A';B=R/'runs/B'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def link(p,s):return f'[{s}]({p})'
def block(s):return '> '+s.replace('\n','\n> ')
now=datetime.now(timezone.utc).isoformat()
original=read(P/'config/original_plan.json');ar=read(A/'preconditioner.json');br=read(B/'preconditioner.json');ae=read(A/'effective_plan.json');be=read(B/'effective_plan.json')
aq=read(A/'request.json');bq=read(B/'request.json');oldaq=read(P/'requests/A_UNSENT.json')
ap=json.loads(aq['body']['messages'][1]['content']);bp=json.loads(bq['body']['messages'][1]['content'])
assert pc.compile_effective_plan(ar,ap)==ae==original
assert pc.compile_effective_plan(br,bp)==be
assert ap['plan']==bp['plan']==original
assert ap['memory']=={'entries':[],'sources':{}}
assert [x['id'] for x in bp['memory']['entries']]==['M1','M2','M3','M6','M7','M8','M9']
ac,bc=deepcopy(ap),deepcopy(bp);ac.pop('memory');bc.pop('memory');assert ac==bc
assert oldaq['body']['messages'][0]==bq['body']['messages'][0]
assert aq['body']['messages'][0]!=bq['body']['messages'][0]
ac,bc=deepcopy(aq),deepcopy(bq);ac['body'].pop('messages');bc['body'].pop('messages');assert ac==bc
assert ae['goal']==be['goal']==original['goal'];assert ae['checks']==be['checks']==original['checks']
assert ae['updates'][1]==be['updates'][1]==original['updates'][1]
assert ae['updates'][0]!=be['updates'][0]
for k,h in read(P/'config/freeze.json')['files_sha256'].items():assert sha(P/k)==h,k
for k,h in read(P/'p3b_A_format_001/config/freeze.json')['files_sha256'].items():assert sha(P/'p3b_A_format_001'/k)==h,k
sources={'A_format':{'path':str(A),'request_sha256':sha(A/'request.json'),'response_sha256':sha(A/'http_response.txt'),'effective_sha256':sha(A/'effective_plan.json')},'B_original':{'path':str(B),'request_sha256':sha(B/'request.json'),'response_sha256':sha(B/'http_response.txt'),'effective_sha256':sha(B/'effective_plan.json')},'original_plan':{'path':str(P/'config/original_plan.json'),'sha256':sha(P/'config/original_plan.json')},'raw_runs_unchanged':True,'original_AB_system_same':True,'selected_AB_system_same':False,'selected_AB_only_user_difference_memory':True,'selected_AB_parameters_same':True,'comparison_type':'descriptive_effective_comparison_with_prompt_confound','strict_memory_AB_passed':False,'report_updated_at':now}
save(E/'results/selected_sources.json',sources)
paths=[('A initial',R/'runs/A'),('B original',B)]+[(f'A retry_{i:03d}',P/f'p3b_A_retry_{i:03d}/runs/A') for i in range(1,5)]+[('A* format_001',A)]
ledger=[]
for label,d in paths:
 m=read(d/'run.json');resp=read(d/'response.json') if (d/'response.json').exists() else {};u=resp.get('usage')
 ledger.append({'label':label,'path':str(d),'status':m['status'],'error':m.get('error'),'elapsed_seconds':m['elapsed_seconds'],'finish_reason':resp.get('finish_reason'),'usage':u,'http_attempts':m['http_attempts']})
known={k:sum((x['usage'] or {}).get(k,0) for x in ledger) for k in ['prompt_tokens','completion_tokens','total_tokens']}
save(E/'results/cumulative_ledger.json',{'attempts':ledger,'known_usage':known,'all_attempts_usage':None,'unknown_reason':'initial A ReadTimeout; server consumption unavailable','observed_wall_seconds_sum':sum(x['elapsed_seconds'] for x in ledger),'new_model_calls_this_revision':0,'new_environment_calls':0})
backup=E/'before/reports';protocol=P/'reports/P3A_EVALUATION_PROTOCOL.md';common=P/'config/common_payload_without_memory.json';memory=P/'config/memory_B.json';histindex=P/'reports/P3A_MEMORY_EVIDENCE.md'
header='**修订说明：本报告以合法的新格式A（记作A*）与原B作描述性对照。A*修改过输出格式Prompt，故不满足原P3-A的同Prompt控制条件；不是严格的Memory单变量验证。旧报告及执行记录已保留。**\n'
rows=[]
for x in ledger:
 u=x['usage'];details=(u or {}).get('completion_tokens_details',{});cached=(u or {}).get('prompt_tokens_details',{}).get('cached_tokens',(u or {}).get('cache_read_input_tokens'))
 vals=[str(u[k]) if u else '未知' for k in ['prompt_tokens','completion_tokens','total_tokens']]
 state='合法ready' if x['status']=='valid' else (x['error']['message'] if x['error'] else x['status'])
 if x['label']=='A initial':state='ReadTimeout，无响应'
 rows.append(f"| {x['label']} | {state} | {vals[0]} | {vals[1]} | {details.get('reasoning_tokens','未知')} | {cached if cached is not None else '未提供'} | {vals[2]} | {x['elapsed_seconds']:.3f} |")
(R/'reports/P3B_EXECUTION_REPORT.md').write_text(f'''# P3-B执行报告（纳入合法A*的修订版）

{header}

## 1. 本次修订使用什么

- A*：{link(A/'preconditioner.json','format_001合法输出')}；{link(A/'effective_plan.json','Effective A*')}。ready、adjustments=[]、checks=null，完整Keep Original。
- B：{link(B/'preconditioner.json','首次原B合法输出')}；{link(B/'effective_plan.json','Effective B')}。ready、1条u1替换、checks=null，u2 Keep。
- Original Plan仍是P1-B用户授权R05重试后的合法Diagnosis，{link(P/'config/original_plan.json','冻结Plan')}。未换成正式V23旧Plan、P1输出或手工Plan。
- 本次只修订报告/评价归档，新增模型调用、Token与环境执行均0。
- 原报告逐字节备份在{link(backup/'P3B_EXECUTION_REPORT.md','修订前执行报告')}；原runs/A仍表示首次超时，**未用A*覆盖它**。results/summary.json、旧execution_receipt和旧protection均保留为初次执行收据，当前选择见{link(E/'results/selected_sources.json','修订来源索引')}。

## 2. 控制条件与偏离

| 条件 | 原冻结A/B | 本报告A*/B |
|---|---|---|
| Parent / Original Plan / Grouping / command_sets | 相同 | 相同 |
| 当前完整轨迹 | P1、P3、P6、P7、P8、P10 | 完全相同，未增加P2/P4/P5/P9 |
| Actor背景 | 原V23 | 相同 |
| Memory | A空；B真实R05七条及sources | 同左，无M10 |
| system Prompt | 完全相同 | **不同：仅A*增加输出字段及引用格式说明** |
| 模型/temperature/Thinking/推理/预算 | 相同 | 相同 |
| Schema /编译器 | 原V23 | 不变，均合法编译 |

A*增加一段：basis/reason放在Adjustment外层、to仅含id/text、不复制输入basis或占位字段、外层依据/理由非空、当前引用逗号分隔。见{link(P/'p3b_A_format_001/config/prompt.diff','精确Diff')}与{link(P/'p3b_A_format_001/config/freeze.json','调用前冻结')}。虽只改格式说明，也可能影响输出选择，不能假定语义影响为零。

两份合法输出可比较实际行为要求，但“有Memory→差异”的归因受到Prompt变化、非对称技术重试、时点、上下文长度/缓存与随机性限制。原同Prompt条件下A经历超时与四次无效响应，仍无合法Effective A。

## 3. 全部尝试与成本

deepseek-v4.1-flash，temperature=1，Thinking enabled，reasoning_effort=medium，stream=false，max_tokens=16384，timeout=300秒；每次1个HTTP、0自动重试。内部路由名称已由用户确认。两份合法输出response_model均相同、finish_reason=stop。

| 尝试（实际顺序） | 状态 | 输入 | 输出 | 其中reasoning | 缓存输入 | 总Token | 秒 |
|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

累计7次HTTP；已知输入{known['prompt_tokens']:,}、输出{known['completion_tokens']:,}、总{known['total_tokens']:,} Token。首次A超时服务器消耗未知，完整实验总量仍未知。两份合法输出A*+B合计545,053 Token，不包含失败尝试。reasoning属于输出子集、缓存属于输入子集，不重复加总；没有可靠货币费用。

retry_004的首个历史引用错误来自reason的P3/P6等简写被正则匹配为历史路径；不是已证实的历史事实捏造。它同时有空外层basis/reason及to字段越界，仍无效。所有失败均保留，未人工修补或当作有效结果。部分旧异常处理器的usage.json将finish_reason记null，原HTTP/response.json为stop；累计表以原响应为准。

A*本次空adjustments没有生成to对象，所以格式通过不等于已证明非空替代对象的字段错位问题修复。

## 4. 核验与保护

原P3-A冻结、A*冻结哈希均核对；选用请求仅system和Memory两类内容不同，其他输入/参数一致；两份结果由原编译器离线重编译一致。A* Effective完整等于Original；B Goal/Checks/u2等于Original，u1与Adjustment.to.text相同。B Effective basis保留Original来源谱系，而M6/M3/M8见Adjustment.basis，这是既有编译规则。

本次只更新四份P3B报告及evaluation_filled.json，另存修订备份、来源索引、完整用量账本和保护核验。所有原始模型请求/响应、Prompt、Memory、方法、Campaign、Test不变。{link(E/'results/protection.json','本次保护结果')}；{link(E/'results/cumulative_ledger.json','全部尝试账本')}。
''')
comparison=f'''# P3-B Update对照（A* Keep与原B Adjust）

{header}

## 1. A*独立评价

A*的reason称：

{block("the numbered-series/type-switch heuristic makes the coverage requirement implementable with the Actor's two-step history")}

u1未改变。仍要求`not yet inspected in this search`、单向扫完同类编号再换类；两步历史与编号线索不能自动恢复整个搜索的访问集合或穷尽状态。它没有说明这些必要前提如何持续获得。编号/局部有序探索可以是合理假设，不能一概判错；但本次对整条要求可执行的肯定超过了已说明的依据。P6的长drawer搜索耗尽预算也需要区分重复与覆盖安排，不由“方向正确”消除。

u2未改变。P1:4 no-op、P7:11/12重复look、P8:39/P10:25空inventory支持避免状态未变时的无信息重复；原文未明确状态改变后重试或有效信息获取的例外，仍要求立即state-changing。开头允许reveal new information，因此不夸大为禁止全部look/inventory。

A*没有新增强制要求，保留精确目标、必要处理交付、desklamp Goal及检查项；但原有边界问题仍在。合法Keep不等于必然合理，也不因没有Adjustment而自动判错。reason中“Memory为空”是其显式陈述，不证明其只因空Memory而Keep。

## 2. B独立评价

B确实把u1换成breadth-first跨类型探索、最近两组历史去重，保留精确目标/不替代和到达开容器；u2保持。改变探索安排有当前循环/覆盖问题与历史混合响应的动机，允许作为待验证假设，不要求它已被证明最优。

但B同时引入：

{block('Return to remaining numbers in a series only after other plausible types or locations have been sampled.')}

{block('Continue until the exact target is found or all plausible candidate types or locations have been inspected once.')}

前者新增排他续行条件；后者把types与locations放在同一完成边界，可能使类别采样代替实例覆盖。它们不能只凭扩大覆盖动机获充分支持；`remain unvisited`/`have been sampled`/`all ... once`仍依赖累计状态。文本风险未经过Actor验证，不能说已经发生过早停止或成功率退化。`a few`不是固定2/3次，括号类别列表不是已确定的强制全局顺序。

B对u2保留与A*相同的状态范围歧义。Goal仍含有效任务行为，但不能仅凭Goal保留就保证搜索续行限制不会与有效回源发生冲突。

## 3. 行为要求逐项差异

| 项目 | A*实际Effective | B实际Effective | 核查判断 |
|---|---|---|---|
| 同类编号搜索 | 必须单向扫完序列再换类 | 不穷尽长同类序列；采样few后换类 | 实质策略差异；两者优劣未隔离验证 |
| 近期去重 | 原有recent observations，加全局uninspected | 明确last two pre-action pairs、近期未出现候选 | B局部范围更明确，但共有Actor说明已支持，不是独有历史知识 |
| 全局状态 | not yet inspected、series exhausted | unvisited、sampled、all inspected once | 两者均残留未充分落实的信息前提 |
| 回到同类余项 | 穷尽后换类别再重入 | 其他合理类型/位置采样后才回余项 | B增加排他条件，M6同类遗漏不证明该条件必要 |
| 搜索结束 | u1没有新增类别一次结束条件 | exact target或all plausible types/locations once | B新增粒度混淆风险；不能等同于完整位置覆盖 |
| 无效动作u2 | 原文Keep | 完全相同Keep | 无更新增量，状态相关重复边界未改善 |
| 目标/交付/灯/Goal | 原样 | 原样；u1保留no-substitute | 无新增差异，不直接归功于M8 |
| Checks | 原c1/c2/c3 | 完全相同 | 无观测标准差异；Checks不是执行补救指令 |

## 4. Original、Effective全文及调整

以下全文直接读取原始JSON；未重写模型输出。A* u1/u2、Goal/Checks均与Original严格相同，故合列全文，避免把同一文本重复三次。

### Goal（Original=A*=B）

{block(original['goal'])}

### u1 Original = Effective A*

{block(original['updates'][0]['text'])}

### u1 Effective B

{block(be['updates'][0]['text'])}

### u2 Original = Effective A* = Effective B

{block(original['updates'][1]['text'])}

### A*完整决策

```json
{json.dumps(ar,ensure_ascii=False,indent=2)}
```

### B完整决策与Adjustment

```json
{json.dumps(br,ensure_ascii=False,indent=2)}
```

### 三者相同Checks

```json
{json.dumps(original['checks'],ensure_ascii=False,indent=2)}
```

原文定位：{link(A/'effective_plan.json','A*全部字段')}；{link(B/'effective_plan.json','B全部字段')}；{link(common,'共有当前证据')}。u1有实质差异，u2无差异；这项描述可确认，但Prompt不一致阻断纯Memory归因。
'''
(R/'reports/P3B_UPDATE_COMPARISON.md').write_text(comparison)
(R/'reports/P3B_MEMORY_ATTRIBUTION.md').write_text(f'''# P3-B Memory归因（合法A*补充版）

{header}

**现在能确认实际Update差异，但仍不能确认Memory造成了更合理的增量。**阻碍已从“没有任何合法A”变为“合法A*的Prompt与B不同，且B新增的部分策略要求缺乏依据”。不能继续沿用缺失A的旧结论，也不能直接宣布预条件化通过。

## 1. 先扣除共有当前证据

{link(common,'共有payload')}中P3空drawer回访、P6长drawer搜索、P8循环、P10:32才在diningtable取得搜索发现，足以支持减少无信息重复和尝试扩大覆盖；不独立证明某个调度最优。原Actor执行背景已明确两组历史，足以质疑全局visited要求。P1:4、P7:11/12、P8:39、P10:25支持状态相关去重。精确对象、必要处理交付、desklamp约束已经在Parent/Original/Grouping/当前执行中。

A*没有修正，不表示缺少这些信息；B明确近期范围，也不能仅因A*未写就记作历史独有贡献。B保留no-substitute同样不是A*丢失后被Memory救回的要求，两组都保留。

## 2. 历史编辑—响应与B具体变换

实际Memory来自{link(memory,'冻结R05完整Memory')}，七条为M1/M2/M3/M6/M7/M8/M9，无M10。各条全文、Diff和sources路径见{link(histindex,'调用前历史证据索引')}。

| Memory及历史实际编辑 | 行为响应/限制 | B显式解释和实际变换 | 对差异的支持范围 |
|---|---|---|---|
| M6：sources[S1_R03/diff]把搜索改为current/recent反循环、未找到时扩展drawers/shelves/diningtable、高步数优先新位置；联合精确对象/温度修改 | Q4:12发现bread、13取、15cool、17place，对应Parent50失败；P2:15到countertop3并20成功，Q2重复countertop2而未去3且50失败；Q6:49才拿plate、50到fridge未完成 | Adjustment.reason明确说旧anti-revisit/broader-search未稳定遵循仍漏位置；u1从穷尽改为breadth-first | 支持重新考虑覆盖及限制效果承诺，有编辑—响应联系；不证明“其他类型采样完才回同类”或“类别一次即可结束” |
| M3：sources[S1_R02/diff]新增通用开容器、少空回访、精确目标、任务需要才clean和交付，联合收窄灯行为 | P5错取soapbottle且50失败，Q5:19到bathtubbasin发现dishsponge、20取、22clean、24place；其他任务仍循环，简单任务部分增步 | 与M6共同作为旧语言未稳定兑现的依据 | 支持覆盖/精确目标方向有条件收益；没有隔离证明一种跨类采样调度更优 |
| M8：S1_R03/diff及S1_R04/diff强化精确对象及温度处理不替代 | pan/pot、mug/cup案例中Candidate减少近似物操作但仍失败 | B显式用M8支持no-substitute，最终保留 | 有据的相容支持；A*和Original也保留，未形成独有更新增量；不能将未找到误当隐藏全局不存在 |

具体历史step是研究者按sources展开，不是B原reason逐项写出的推理。B显式说了旧指导未稳定兑现；不能补写成它已用Q2/Q6证明only-after、few或终止边界。历史均为联合编辑、单次执行，不能把整份Candidate的结果独立归因某个子句。

B未显式讨论M1/M2/M7/M9，不证明它未读取；也不能把整包作用归因于M6。M9有条件回源等可作研究者保留行为核查，不能伪装成模型已陈述的原因。

## 3. 按预注册规则分开结论

| 分类 | 当前证据与A*/B结果 | 结论 |
|---|---|---|
| 当前证据纠正 | B比A*更明确最近两组去重，并探索不同覆盖；A*未变 | 可确认局部文本变化；共有当前材料已支持，不直接算历史增量 |
| 历史信息使用 | B显式引用M6/M3/M8并改变u1 | 明确陈述使用历史，不能证明Memory是组间差异原因 |
| 编辑—行为响应预条件化 | B把旧搜索编辑的混合响应与重构u1联系起来，实际方向确有变化 | 有内部证据利用线索；**合理的组间因果增量未建立**：Prompt不同，替代方案部分附带限制无据 |
| 无依据新承诺 | B的only-after续行与types/locations一次结束；A*保留原全局前提 | B不是因为Adjustment非空就更合理；A*也未解决原风险 |
| 无实质差异 | u2、Goal、Checks相同 | 对这些内容没有观察到Update增量；u1则不能称“无差异” |

## 4. 核心解释与限制

本次资料显示的是：**相同Original下，一份无Memory且补充格式说明的合法输出选择Keep；一份有Memory且原Prompt的输出引用历史混合反馈并改变u1，但没有约束住所有替代要求。**它与“历史响应可能参与方向选择”的假设相容，尚不证明Memory带来了更优构造。

格式说明虽然没有指定搜索方案，也不能假定对Keep/Adjust选择无影响；A*走空adjustments分支更使这种可能性无法排除，不能反向断言格式补充使模型保守。非对称技术失败筛选、temperature=1、时点及输入长度差异进一步限制归因。无效A文本不纳入有效对照，不对其中策略择优。

若继续，优先预注册同Prompt的配对/重复验证，先保证两臂合法可比较。现有材料不足以直接晋升方法、挑M6作唯一作用来源或宣称行为收益；本次不调用新B、不运行Editor/Replay、不迭代Prompt。
''')
(R/'reports/P3B_DECISION.md').write_text(f'''# P3-B最终报告（纳入合法A*）

{header}

**报告与描述性对照已补齐：A*完整Keep；B替换u1、Keep u2。两者u1确有实质差异，但目前不能认定历史Memory产生了更合理、可归因的更新增量。**

| 必答问题 | 修订结论 |
|---|---|
| 1. A最终如何调整？ | 新格式A*为ready、adjustments=[]，u1/u2全文及Goal/Checks均保持Original。原同Prompt A仍没有合法输出 |
| 2. B如何调整？ | u1改为跨类型breadth-first采样及明确近期去重；u2保持；Goal/Checks保持 |
| 3. Effective是否实质不同？ | 是，u1的同类穷尽/换类/返回余项/终止条件不同；u2、Goal、Checks相同 |
| 4. 哪些纠正当前证据已足够？ | 对全局visited/穷尽前提提出质疑、减少无信息重复、限定状态变化后的重试、保留精确对象和处理交付。A*未纠正不表示这些证据不存在 |
| 5. 是否观察到历史响应相关变换？ | B显式联系M6/M3旧编辑的混合响应并改变u1，是实际证据使用线索；但Prompt不同，不能将A*/B差异归因于Memory |
| 6. B是否新增无据承诺？ | 是，其他类型采样后才回同类余项，以及types或locations一次的结束边界支持不足；全局进度依赖仍在 |
| 7. 是否支持合理增量机制通过？ | 不通过此项结论：既有控制条件偏离，也有替代构造不足。不能据此宣布Memory有效或无用 |
| 8. 哪些是单次线索？ | A*接受原案的理由、B历史反馈与方向变换联系、双方最终边界问题；不证明稳定优劣或Actor行为结果 |
| 9. 后续优先什么？ | 优先同Prompt、预注册的配对/重复验证及非空Adjustment格式可靠性；不直接进入行为Replay或语义Prompt补丁搜索。本次不执行 |

A* reason把编号/换类启发式视为两步历史下可执行，但最终全局uninspected/穷尽要求未得到充分解释。B更明确局部近期去重，也改变方向，却新增：

> Return to remaining numbers in a series only after other plausible types or locations have been sampled.

> Continue until the exact target is found or all plausible candidate types or locations have been inspected once.

这些不能仅凭改善覆盖的动机充分成立；潜在副作用尚未经过Actor执行，不声称已经导致退化。双方u2均未明确状态变化后的重试边界。合理Keep和探索均允许，本结论不以Adjustment数量判胜负。

## 状态与交付

- 有效输出材料：已齐（A*新格式、B原Prompt）。描述性比较：已完成。**原P3-A严格Memory单变量验收：未满足，Prompt不一致。**
- A*成功为43.584秒、65,026 Token；旧B57.498秒、480,027 Token。全程累计7次HTTP，已知830,656 Token，首次A超时消耗未知；本次报告修订新增模型调用/Token/环境执行均0。
- 四次原Prompt A完整响应均契约失败，另有一次超时；原始记录保留。A*为空adjustments，所以不能把本次格式通过当作非空to层级问题已解决。
- 原四份报告和评价JSON先备份，本次只修改这些报告/评价及新增修订归档；原请求、响应、Prompt、Memory、方法、Campaign和Test不变。

{link(R/'reports/P3B_EXECUTION_REPORT.md','执行与全部成本')}；{link(R/'reports/P3B_UPDATE_COMPARISON.md','全文与逐项对照')}；{link(R/'reports/P3B_MEMORY_ATTRIBUTION.md','历史增量归因')}；{link(E/'results/selected_sources.json','来源与哈希')}；{link(E/'results/protection.json','本次保护核验')}；{link(backup/'P3B_DECISION.md','旧版结论')}。

已停止，不新增模型请求、不进入Editor、Candidate Replay或后续实现。
''')
filled=read(P/'config/evaluation_template.json');filled.update(status='descriptive_comparison_complete_A_format_vs_B_original_prompt_confound',selected_sources=sources,strict_memory_AB_passed=False)
for item in filled['updates']:
 uid=item['update_id'];ai=next(u for u in ae['updates'] if u['id']==uid);bi=next(u for u in be['updates'] if u['id']==uid)
 item.update(A_decision=ar['decision'],B_decision=br['decision'],A_reason=ar['reason'],B_reason=br['reason'],A_adjustments=[x for x in ar['adjustments'] if uid in x['from']],B_adjustments=[x for x in br['adjustments'] if uid in x['from']],A_checks=ae['checks'],B_checks=be['checks'],effective_A=ai,effective_B=bi,A_variant='format_001 (different system prompt)',B_variant='original frozen prompt',A_technical_status='valid ready; original A failures preserved',attribution_boundary='Two valid outputs permit descriptive comparison; differing system prompts and repeated technical attempts prevent Memory-only attribution.')
 if uid=='u1':item.update(material_difference='A retains numbered-series exhaustion; B uses cross-type sampling, only-after resumption, and types-or-locations termination.',difference_evidence='Current P3/P6/P8/P10 and Actor context already support reconsidering coverage and global progress. B explicitly cites M6/M3 mixed responses and M8 preservation; source chain in report.',new_commitment_risk='A inherits global-progress assumptions; B retains global-progress conditions and adds unsupported resumption/termination requirements.',conclusion='Substantive difference and explicit historical use observed; reasonable incremental Memory effect not established.')
 else:item.update(material_difference='None: u2 exactly equal to Original in both.',difference_evidence='Shared current no-op/look/inventory evidence; no final change in either arm.',new_commitment_risk='Inherited state-scope ambiguity and immediate state-changing requirement; no new B-only prohibition.',conclusion='No observed Update increment for u2.')
save(R/'results/evaluation_filled.json',filled)
# Historical-run records remain unchanged. Only the five explicitly listed report files may change.
spec=importlib.util.spec_from_file_location('protect',ROOT/'experiments/methods/v23_2/v23_2_diagnosis_interface_audit_001/verify_protection.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);v.EXP=E
before=read(E/'protected_before.json');after=v.snapshot();changed=sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k));allowed=set(read(E/'allowed_changes.json'));unexpected=[k for k in changed if k not in allowed]
backup_pass=all(sha(E/'before'/Path(k).relative_to(R.relative_to(ROOT)))==before[k] for k in allowed)
links=[]
for f in (R/'reports').glob('P3B_*.md'):
 for t in re.findall(r'\]\(([^)]+)\)',f.read_text()):
  target=Path(t)
  if target==E/'results/protection.json':continue
  assert target.exists(),(f,t);links.append(t)
save(E/'results/protection.json',{'at':datetime.now(timezone.utc).isoformat(),'checked_files':len(before),'after_files':len(after),'changed':changed,'allowed_changes':sorted(allowed),'unexpected_changes':unexpected,'protected_unchanged':not unexpected,'old_reports_backup_matches':backup_pass,'before_after_sha256':{k:{'before':before.get(k),'after':after.get(k)} for k in changed},'new_model_calls':0,'new_environment_calls':0,'new_tokens':0,'links_checked':len(links)})
(E/'results/git_status_after.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))
assert not unexpected and backup_pass
print(json.dumps({'reports_revised':4,'evaluation_updated':True,'protected_files':len(before),'allowed_changes':len(changed),'unexpected_changes':unexpected,'backup_verified':backup_pass,'new_calls':0},ensure_ascii=False))
