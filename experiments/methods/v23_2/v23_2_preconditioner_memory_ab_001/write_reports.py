"""Write pre-registered P3-A documents. Never populates experimental outcomes."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];E=Path(__file__).resolve().parent
R=E/'reports';C=E/'config'
def read(p):return json.loads(p.read_text())
def link(t,p):return f'[{t}]({p})'
def write(n,t):(R/n).write_text(t.strip()+'\n')
m=read(C/'memory_B.json');d=read(C/'original_diagnosis.json');cfg=read(C/'call_config.json');cap=read(E/'results/capacity.json');manifest=read(C/'input_manifest.json')
original=Path(manifest['original_diagnosis_path'])
L=lambda t,n:link(t,E/n)
source=L('Memory原文、Diff和source引用','reports/P3A_MEMORY_EVIDENCE.md')
summary={
'M1':('S1_R01 新增desklamp共址流程；P1 50步失败，Q1 4步成功，其余四对均成功，完成触发与先后顺序有差异。','支持保留目标与灯共址、避免远程反复开关；对u1扩大到lamp搜索的范围有约束。','不能把先take/先turn-on设成唯一正确顺序；不说明所有任务都应寻找灯。'),
'M2':('同一desklamp编辑附带保留非灯任务行为；P6–P10/Q6–Q10五对均成功，步数有差异。','保留非灯任务的搜索、获取、交付；提示不要因新搜索强制流程破坏直接完成。','未隔离证明保留子句导致成功；不是任何新搜索策略均无副作用的保证。'),
'M3':('S1_R02 同时追加通用搜索/精确对象/条件clean/交付并收窄灯任务；P5失败，Q5在bathtubbasin找到dishsponge并clean/place成功；部分简单任务增步，循环仍有。','扩大覆盖与精确对象方向可有收益；开闭容器和必要交付要保留，避免宣称反循环提示稳定奏效。','没有灯任务验证范围收窄效果；联合编辑不证明某顺序、禁止回访或某子句独立收益。'),
'M6':('S1_R03 修改搜索及反循环，联合精确对象/温度处理；Q4 diningtable找到bread获救，Q2漏同类countertop3而失败，Q6非法移动/空检查、49步才取plate导致未完成。','历史编辑后的收益与局限可校准覆盖单位、状态前提、预算与效果强度；不能只把它当几个额外失败例子。','不证明类内穷尽或跨族一定优越，不支持固定阈值/永久动作禁令；7→6是联合单次结果。falling back措辞不代表Adapter fallback。'),
'M7':('S1_R03/R04 直接持物cool/heat、按可见合法动作处理并直送；R04 P3 14步/Q3 7步、P4 21步/Q4 7步；目标未找到时无法应用。','支持目标已获取且动作可用时保留明确温度操作和后续交付；校准u2 state-changing示例必须有前提。','不能从总步数差异分离全部温度子句效应，不能拿来强制所有搜索后必成功或所有设备状态不需open。knowledge中absent类断言不作全局不存在依据。'),
'M8':('R03/R04 精确类别规则及温度条款共同加强；Parent操作pot/cup替代，Candidate避免相应近似物处理，仍有步限失败。','精确对象与不以替代物完成任务需保留；避免把“不操作替代物”误读为已经解决搜索。','不能证明近似物回避独立提高成功率；absent与未找到需区分，不据此停止搜索。'),
'M9':('R04 新增多实例计数/可见剩余目标回源，联合温度编辑；newspaper双方10步成功，saltshaker与candle回源成功但部分增步，keychain/cd仍失败。','约束绝对不回访的范围：来源当前/近期显示剩余目标时回源是有用行为；保留数量和交付，不能把已访问等同耗尽。','当前R05没有多物体任务，跨任务应用需论证；不支持任意远期记忆、任何访问都可回返，或把多物体调度直接移植到所有搜索。')}
append='''# P3-A 历史响应预注册索引

B组完整保留当轮七条Memory，A组没有这些entries或sources。下文是研究评价说明，不进入任何模型消息，不改写knowledge。不开展新的全面Memory审计；M6沿用P2逐项核查，其余条目用于预登记来源及适用边界。尤其不能把所有B组变化归于M6，也不能把其他条目的“absent”直接视为隐藏环境不存在的已证事实。

'''
append+=L('冻结B组Memory','config/memory_B.json')+' 的 `entries[id=...]`、`sources[context/diff]`、`sources[context/Pn或Qn]` 是完整原文，source中含Parent/Diff或run/command_sets。'+L('不可变原文件哈希','config/source_hashes.json')+' 与 '+L('逐Memory引用索引','config/memory_source_index.json')+' 可复核。\n\n'
for e in m['entries']:
 mid=e['id'];a,b,c=summary[mid]
 append+=f'## {mid}\n\n**knowledge原文**\n\n> {e["knowledge"]}\n\n**编辑—响应**：{a}\n\n**支持的判断**：{b}\n\n**不能推出**：{c}\n\n**原始evidence完整索引**：`'+ '`、`'.join(e['evidence'])+'`。\n\n'
append+='## 四份真实Diff（未改写）\n\n'
for k,v in m['sources'].items():
 if k.endswith('/diff'):append+=f'### {k}\n\n```diff\n{v["diff"]}```\n\n'
append+='''来源执行全文已经在冻结Memory sources中，不再复制独立轨迹。M6具体核查见P2报告；当轮sources只展开被引用run，不代表完整重放所有历史任务。B是整个Active包的处理，不是M6单条消融。即使B差异涉及M6，M3/M7/M8/M9和上下文组织也可能共同影响。
'''
write('P3A_MEMORY_EVIDENCE.md',append)

design=f'''# P3-A：R05固定Original的Memory有无对照设计

**状态：离线单变量装配通过，请求与评价预注册冻结；没有发送，没有真实Preconditioner响应。当前内网模型上下文容量尚未核实，P3-B执行就绪验收暂不通过。**

## 研究问题与假设边界

检验历史编辑—行为响应能否在相同Original Plan和当前证据下，对最终Update的策略、适用条件、范围或强度提供可追溯的增量作用。它可能表现为更合理的Keep、收窄、替换、拆合或撤回；不规定B应比A多做Adjustment，不以某种搜索算法为标准答案。

可观察假设：B相对A出现实质行为要求差异，且“过去改了什么→实际出现什么响应/局限→为何影响这次差异”的链条有据。空假设/未观察到增量：Effective行为相同，或只有reason引历史而实际Update不变。不同但无依据、过强或丢失有效行为也不是改善。

## 唯一Original与选择R05的原因

使用 {link('用户授权重试的P1-B合法Diagnosis',original)}。决策revise，Goal及u1/u2、basis、顺序、Checks完整冻结；原文件SHA256为 `{manifest['original_diagnosis_file_sha256']}`。不是正式V23旧Plan、P1输出或首次截断结果，也没有人工修正。

R05 Goal基本为精确目标、覆盖/步效、必要处理交付及desklamp共址保留，不把某个具体扫描算法锁为唯一方法。u1同类编号单向推进/耗尽后换类/避回旧编号及全局未查状态可由Preconditioner调整；u2 no-op后不重试等价动作及立即state-changing的范围也可调整。接口不要求Diagnosis先生成完美策略。

完整Diagnosis快照保留顶层reason供追溯；**实际Preconditioner用户输入只有原plan，不包含Diagnosis顶层reason或生成过程**。不得把研究报告或原reason里未选轨迹信息偷偷加入请求。

## 两组与控制变量

| 项目 | A无Memory | B真实Memory |
|---|---|---|
| 原Parent/Original/Grouping/背景 | 相同 | 相同 |
| 当前完整runs | P1 P3 P6 P7 P8 P10 | 相同六条 |
| Grouping | G1–G4原装配内容 | 相同 |
| command_sets | 103个实际所需候选表 | 相同 |
| Memory | `{{"entries":[],"sources":{{}}}}` | R05当时M1 M2 M3 M6 M7 M8 M9及全部对应sources |
| Prompt | 正式冻结V23 Preconditioner+原Execution Context | 逐字相同 |
| 模型/参数/容量 | 当前路由冻结，见输入报告 | 完全相同 |
| 输出/编译 | 原契约/原确定性编译 | 相同 |

B经实际R05 request、input、round_input、rounds/R04/memory Active和不可变commits核对一致。**没有M10、事后认识或人工总结**。B内容本身不改写；知识和source作为整体变量，不是摘要消融。

当前证据按原Plan引用选择，不按Memory选取；单步引用展开整条run。G1–G4没有自动扩展成员，因此P2/P4/P5/P9只有已有Grouping摘要，不新增完整轨迹。P2/P4未来可设独立扩展条件，本阶段没有构造第二套实验。不得根据第一次输出结果临时补充。

## 允许的结论范围与混杂

1. A/B差异是整个Memory包的条件差异，包括知识、额外轨迹/候选和更长上下文；两臂本身不能隔离“只有知识总结”“只有原轨迹”或M6单条作用。
2. 同一模型名不保证服务端模型版本永久不变；temperature=1无配对seed，顺序、缓存、负载和随机性均可能影响。调用时必须记录实际response_model、时间、usage及错误；不同实际后端/参数则不能声称控制成立。
3. 上下文长度A约0.21M字符、B约1.63M字符；注意力/长度效应与内容效应无法由两臂隔离。不能给A加填充或截短B来制造“等长”，那是新实验。
4. 历史配对大多是单次联合编辑；响应支持范围不等于单条规则独立因果收益。P3-B也不执行Skill，不能推导成功率提升。
5. P4摘要显示直接路径，不构成同实例反事实；不能以未提供P4完整动作条件作强制验收。P2有效回返摘要与Parent/Goal仍可用于范围判断，但不得声称已经全面核查回返菜单。
6. 当前Actor两步历史限制在两组相同。允许局部、可观察的编号线索或近期新颖性探索；不因未被历史证明就禁止新策略。

## P3-B预注册执行规则（本次不执行）

- 在模型上下文容量确认后且用户授权P3-B，校验最终freeze及请求/来源哈希；若route、Prompt、输入或配置变了则停，不自动重装/改名继续。
- 固定A后B的顺序，每组一次逻辑调用、最多一次HTTP请求；无输出择优。顺序本身是限制，不能解释为随机化对照。
- 不直接用会自动重试的 `local_validation.run_stage`。拟复用 `grouping.live_generator` 的单次请求能力及原解析/编译，在独立P3-B归档中保留冻结请求和完整结果；本次不实现或启动发送编排。
- 原CLI的上游loader默认正式Diagnosis模板，不能不加核验就拿它读取P1-B。继续用本次已验证的 `local.load_attempt(..., prompt_path=P1B冻结路径)` 只读加载；消息必须等于冻结请求。不得改方法代码绕过。
- 截断/API错误/契约失败完整归档成本，停止该组；另一组只在无共同配置阻断时按原预算执行。重试须用户另行授权、原请求与参数不变，不自动补采样。
- 合法no_change/need_evidence作为真实语义结果留存；Effective为null时不造策略。缺历史本身不是need_evidence充分理由，应核对模型理由。
- 先分别评价每组，再做语义差异与历史链条追溯；B不是正确答案。结果相同则如实写未观察到具体增量。
- 只生成Preconditioner结果，不进入Editor、Actor、Replay、Gate或Prompt迭代。

评价见{L('协议与空结果模板','reports/P3A_EVALUATION_PROTOCOL.md')}；请求/哈希/限制见{L('输入冻结报告','reports/P3A_INPUT_FREEZE.md')}。
'''
write('P3A_EXPERIMENT_DESIGN.md',design)

known={
'u1':{'current':'P3:7–11空drawer回访、13–16找到mug后交付；P6/P8循环且部分位置未到；P10:32才发现apple，33/35/38获取处理交付。支持减少重复和覆盖遗漏，不证明唯一顺序。当前/候选/两步历史不等于全局visited；G1和Goal提示有用回返/共址要保留。',
'history':'M6的真实搜索编辑既有diningtable收益，也有同类countertop3遗漏和49步才获取的预算失败；M3混合覆盖与精确目标反馈；M9有条件回源及增步；M1/M2/M7/M8提供应保留行为及条件。'},
'u2':{'current':'P1:4不可用go shelf2→Nothing happens；P7:11/12重复look；P8:39/P10:25空手inventory。支持状态不变时避免无信息重复，不支持状态改变后永久禁止同动作或等价动作，也不证明一切信息获取都应立即换成state-changing。',
'history':'M6候选仍重复不可用移动与空位置检查，提示反循环条款未稳定落实而非应禁止整类动作；M7动作可用/持物温度处理及交付条件，M8精确对象，M9有效回源提供范围保留。'}}
template=[]
for u in d['plan']['updates']:
 template.append({'update_id':u['id'],'original_update':u,'known_current_evidence':known[u['id']]['current'],'historical_increment':known[u['id']]['history'],
 'A_decision':None,'B_decision':None,'A_reason':None,'B_reason':None,'A_adjustments':None,'B_adjustments':None,'A_checks':None,'B_checks':None,
 'effective_A':None,'effective_B':None,'material_difference':None,'difference_evidence':None,'new_commitment_risk':None,'attribution_boundary':None,'conclusion':None})
(C/'evaluation_template.json').write_text(json.dumps({'status':'pre_registered_no_outputs','goal':d['plan']['goal'],'original_checks':d['plan']['checks'],'updates':template},ensure_ascii=False,indent=2)+'\n')
protocol=f'''# P3-A：预注册评价与归因协议

**本协议在任何P3-B模型调用前冻结。A/B响应字段全部留空。本文研究注释不进入请求。**

## 1. 比较前先独立评价

先验证输出契约与编译，再依次读每组完整reason、adjustments（含basis、reason及to.text）、有效Checks和Effective updates。明确ready/Keep、局部撤回、no_change及need_evidence；记录被改、未改、合并拆分的所有行为要求，不以Adjustment数判断。

逐项记录策略、触发条件、适用范围、强制程度、顺序、完成/停止前提及保留行为。Goal程序原样保留，不能把Goal文字仍在当成Update必然保留了行为。Checks是未来观测问题，不能当成Actor会执行的补救指令。

不以关键词、篇幅或更谨慎的措辞评分；不预设类内穷尽错误、跨类别轮换正确；大幅调整及明确操作均可合理。区分明确可纠正的前提错误、支持不足的必要性主张和仍值得探索的新假设。

## 2. 两组共同拥有的事实与判断边界

| 项目 | 当前实际证据 | 可纠正／保留 | 不可推导 |
|---|---|---|---|
| 覆盖/循环 | P3:7–11重复空drawer，P6/P8遗漏与循环，P10:32晚找到 | 减少无信息重复，不能把局部观察当全局已检查；目标发现后进入必要处理交付 | 某一种编号穷尽/类别轮换/排序已被证明最优 |
| Actor能力 | 原Execution Context：当前观察/候选、两组行动前历史、步数 | 要求全局耗尽状态需可恢复依据；允许依当前编号或近期结果的局部探索 | 当前没出现等于从未访问；只要使用编号就天然可执行或天然错误 |
| no-op/信息获取 | P1:4不可用移动；P7:11–12相同look；P8:39、P10:25空inventory | 把无效重复限定于相关状态和前提；保存有新信息/前提改变后的必要操作 | 单次无效证明以后所有等价动作都无效；所有信息动作都应禁止 |
| 有效行为 | Parent/Goal/G1、P1:2/8/9；P3:14/16；P7替代knife失败；P10:33/35/38 | 精确对象、灯共址、获取、必要处理及交付；寻找新位置不得无条件排除有用目的地 | 原轨迹未选全文就说明该行为从未发生；仅凭Goal保留便可忽略Update冲突 |

这些修正即使只出现在B，仍可能是Memory促发模型注意当前证据，**不能直接叫作独有历史信息收益**。A没修正不等于A没有相应证据。

## 3. 历史包的额外信息及来源

{source}保存七条knowledge原文、每项实际Diff/执行索引、支持与不支持的判断。B整体包含M1/M2/M3/M6/M7/M8/M9，不是M6独立消融。

M6最重要的增量不是又出现了循环，而是：**过去确实写过某些扩展搜索/反循环规则，执行既出现覆盖收益，也留下同类遗漏、无效移动和过晚获取；效果与方向并不等价。** 这种编辑与响应联系可以限制效果保证或改变适用条件，但不唯一决定替代调度。

M1/M2灯与非灯行为保留、M3通用联合编辑混合响应、M7直接温度操作前提、M8近似物回避但未救回、M9有条件回源与计数，均可能影响B。因此评估时逐项定位所用Memory/source；多个共同支持时全部列出，不虚构单条归因。

本实验不纠偏旧knowledge，也不视其为真值oracle。M7/M8等出现absent措辞时，只能按实际sources判断“未找到”的范围，不得据此新增全局不存在/搜索结束条件。对未专门审计的断言标明不确定性，不在本阶段扩大为全面Memory审计。

## 4. 四类结果与两级历史作用

| 分类 | 操作判据 | 如何报告 |
|---|---|---|
| 当前证据纠正 | 改动的理由可由两组共有当前事实/任务/Actor能力成立；无具体历史响应额外链条 | 修正可以有价值，但不直接算Memory增量。若仅B修正，记录“B独有当前证据纠正，机制归因未明” |
| 历史响应增量线索 | B与A有实质差异；历史真实编辑、对应行为响应和当前差异适用关系可追溯；差异本身合理且未破坏保留要求 | 分开历史信息影响与编辑—响应预条件化，均只称单次线索 |
| 无依据新承诺 | 原/新要求增加顺序、次数、排他、终止、效果保证等，却无对应证据或清楚可检验问题假设；或有动机但附带约束超出其支持 | 不算改善。即使引用Memory、发生Adjustment或A也犯错也不豁免 |
| 无实质更新差异 | Effective行为语义等价；只有reason引用、措辞、ID或篇幅不同 | 未观察到具体Update增量。Checks差异可单列“观测设计变化”，不冒充Actor策略变换 |

四类是研究判定，不加入模型Schema；同一个Update可有局部历史增量和局部新风险，不能用一个“通过”掩盖混合结果。

**历史信息影响**：B用了额外案例/总结，产生可定位的不同要求，但未把实际编辑与响应联系起来。例如只借旧任务中某目标位置给出新规则。这最多是历史信息相关线索；若有不当推广，仍属无据承诺。

**编辑—行为响应预条件化线索**必须同时具备：

1. 指明旧Skill具体修改（source Diff），不是只有相似任务目标。
2. 指明对应实际行为改善/反例/副作用及适用条件，保留联合编辑归因限制。
3. 说明该联系为何改变当前Update某一具体要求，而非给reason加一条引用。
4. 在最终Effective文本中找到实际改变，或有依据保留了A错误删掉的要求；核查其他有效行为没有被无据破坏。

若模型未明确提供链条，而研究者从sources推断有联系，必须标为“与历史相容的研究者推断”，不能补写成模型已利用该机制。显式reason也只证明其表述依据，不证明隐藏因果推理。

## 5. 组间判定流程

1. **锁定对照有效性**：哈希、唯一Memory差异、服务端模型/参数一致；任一失败不做正常AB归因。
2. **每组独立评价**：对u1/u2逐项区分有效要求、可探索假设、过强/不可执行承诺、新退化；准备/Keep本身不等于错。
3. **语义差异定位**：写出A/B实际句子和行为差异，不能仅列reason或调整数量。合并拆分按原u1/u2来源追踪，不只对ID。
4. **先扣除共有依据**：列出共有当前证据已能支持的部分。A修正、B同样修正不算增量；B独有修正也需查历史是否提供不同支持。
5. **追溯历史增量链**：Memory ID→Diff→配对动作/条件→对当前差异的支持/局限。分事实、判断、探索假设，禁止将整体胜负归因单条编辑。
6. **检查附带损害**：固定阈值/顺序、绝对禁回访、一次类别采样就停、保证进展或额外任务限制是否有独立依据；不因一个差异合理而整体通过。
7. **给限定结论**：当前纠正、历史信息线索、响应预条件化线索、无依据变化或无实质变化。B Keep/A Adjust允许前者合理；A提出与历史相似的策略不构成偷偷使用Memory。
8. **结果/停点完整性**：合法语义停点按原契约，缺失响应/技术失败不当作语义失败。只有一组有效时可独立分析，不能声称已完成两组增量比较。

单次对照没有排除生成随机性、不同上下文长度/注意力、顺序及后端变化；没有检验Skill行为，因此不能独立证明任何具体编辑的因果收益。

## 6. 冻结评价模板

机器模板：{L('evaluation_template.json','config/evaluation_template.json')}。以下结果格为空；P3-B在新结果目录复制填写，不改本模板。

'''
for u in d['plan']['updates']:
 protocol+=f'### {u["id"]}\n\n**Original Update原文**\n\n> {u["text"]}\n\n'
 protocol+='| 字段 | 内容 |\n|---|---|\n'
 for name,val in [('已知问题/当前依据',known[u['id']]['current']),('历史增量',known[u['id']]['history']),('A组决策/reason/Adjustment/Checks',''),('B组决策/reason/Adjustment/Checks',''),('Effective A',''),('Effective B',''),('具体差异：策略/条件/范围/强度/组合',''),('差异依据：当前或历史Diff/轨迹',''),('新承诺与必要行为风险',''),('归因边界',''),('结论','')]:protocol+=f'| {name} | {val} |\n'
 protocol+='\n'
protocol+='''Goal全文与原Checks保留在机器模板及原Plan快照。检查u1/u2的联合依赖：收窄u1不能使u2无前提去处理/交付，改u2也不能允许替代物完成任务。未调用Editor，不能判断实际Patch会怎样实现。
'''
write('P3A_EVALUATION_PROTOCOL.md',protocol)

freeze=f'''# P3-A 输入冻结与执行准备状态

**两组均为UNSENT请求，尚无真实Preconditioner响应；没有生成实验Effective Plan。结构测试中Keep/stop/identity夹具仅用于纯函数校验，未作为实验结果保存。**

实验控制、Schema及本地容量检查通过；当前proxy模型上下文窗口/精确分词未核实，因此**尚不能无条件批准进入P3-B发送**。不以历史官方调用成功冒充新路由保证。

## 1. 请求和快照

- {L('A_UNSENT.json','requests/A_UNSENT.json')}：合法空Memory。\n- {L('B_UNSENT.json','requests/B_UNSENT.json')}：当时七条Memory及sources。\n- {L('完整Original Diagnosis','config/original_diagnosis.json')}、{L('Original Plan','config/original_plan.json')}：字节相同原Diagnosis、语义相同Plan，保留decision/Goal/Updates/basis/顺序/Checks。\n- {L('共同payload','config/common_payload_without_memory.json')}、{L('system消息','config/system_message.json')}、{L('Actor背景','config/background.json')}、{L('证据选择索引','config/evidence_index.json')}。\n- {L('原Preconditioner模板','config/preconditioner_prompt.md')}、{L('原Execution Context','config/execution_context.md')}：均与正式contract+recoveries冻结内容一致，无历史候选补丁。\n- {L('B Memory','config/memory_B.json')}、{L('A Memory','config/memory_A.json')}、{L('当轮Active索引','config/active_index.json')}、{L('不可变来源哈希','config/source_hashes.json')}。\n- {L('输入哈希清单','config/input_manifest.json')}、{L('最终预注册冻结','config/freeze.json')}（同时冻结评价协议与空模板）。

| 哈希对象 | SHA256 |
|---|---|
| 原始Diagnosis文件 | `{manifest['original_diagnosis_file_sha256']}` |
| Plan规范化JSON | `{manifest['original_plan_canonical_sha256']}` |
| B Memory规范化JSON | `{manifest['memory_B_canonical_sha256']}` |
| 除Memory共同payload规范化JSON | `{manifest['common_payload_canonical_sha256']}` |
| A请求文件 | `{manifest['files_sha256']['requests/A_UNSENT.json']}` |
| B请求文件 | `{manifest['files_sha256']['requests/B_UNSENT.json']}` |

文件SHA计算实际bytes；规范化JSON为sort_keys=True、ensure_ascii=False、紧凑分隔符。两种哈希不混用。每份完整请求含endpoint/body/timeout_seconds/attempts，不含API key；UNSENT状态由文件名及manifest标注，不往模型body加标记。

## 2. 一致性与契约

调用原 `pc.messages_for/preconditioner_input`，并与 `local.messages_for` 对照；消息解析后的顶层parent/plan/runs/grouping/command_sets完全一致，system逐字一致。移除user JSON的memory后，整个请求对象相同。唯一主动变量为 `body.messages[1].content` 内的 `memory` 对象。

A `entries=[]; sources={{}}`由原`empty_memory/validate_memory`接受，未换Prompt。B与round_input、实际历史请求、Active加载逐值相等；M10不在其中。选择仍是P1/P3/P6/P7/P8/P10、G1–G4、103候选表，未因Memory改变。

原编译器分别验证两组Keep、need_evidence、全撤回、同文本替换、引用权限；A引用不存在M6被拒绝，B合法接受。Goal/原Checks保留行为核验通过。该权限差异是Memory可用范围的预期结果，不是Schema变化。没有模型响应、没有语义评分器。

## 3. 当前路由与参数

| 项目 | 冻结值 |
|---|---|
| Endpoint | `{cfg['call_config']['endpoint']}` |
| model | `{cfg['call_config']['model']}` |
| temperature | 1.0 |
| thinking / reasoning_effort | enabled / medium |
| max_tokens / stream | 16384 / false |
| timeout | 配置300秒；现有HTTP函数connect=10秒、read=300秒 |
| 其余生成参数 | 无seed、top_p、presence/frequency penalty、response_format额外设置；按冻结body发送 |
| 重试 | P3-B每组一次请求；自动重试0，重试另行授权 |
| 容量 | 4,000,000消息字符；6,000,000消息UTF-8 bytes |

读取当前环境优先、.env兜底的base，仅保存非密配置和credential_present布尔值，不保存密钥。与 `model_routing.route_call_config` / `grouping.call_configuration` 核对一致。历史R05是官方deepseek-flash；本次两组同用当前内网deepseek-v4.1-flash，**只在本次AB内部控制一致，不宣称复用了历史服务端模型**。

现有代码变动已由P2记录；本次不恢复。`local.run_stage`先从环境解析路由且要求max_attempts=3，会自动技术重试，不能直接满足预注册一次请求限制。原CLI的上游loader也不能默认当作支持P1-B模板。未来应复用现有单次HTTP generator与原解析/编译，发前校验冻结消息/路由；本次仅记录，不新增联网运行器。已存在可复用单次调用能力，不需要改Schema或方法算法。

## 4. 容量、Token与成本可得估计

| 组别 | 消息字符 | 消息UTF-8 bytes | 同类历史比率粗估输入Token | 加16384输出上限 |
|---|---:|---:|---:|---:|
'''
for arm,x in cap['arms'].items():freeze+=f'| {arm} | {x["message_chars"]:,} | {x["message_utf8_bytes"]:,} | {x["estimated_input_tokens_range"][0]:,}–{x["estimated_input_tokens_range"][1]:,} | {x["estimated_with_max_output_range"][0]:,}–{x["estimated_with_max_output_range"][1]:,} |\n'
freeze+='''
本地字符/byte admission均通过；B约A的7.7倍字符。估计用正式R04/R05/R06 Preconditioner保存的实际prompt_tokens与序列化消息字符比率：356103/1217815、470139/1613177、432863/1493400。原始usage与文件路径在capacity.json。

**这个区间只是三份历史比率的最小/最大值，不是置信区间、上下界或当前tokenizer精确计数；真实值可能在区间之外。** 当前无DeepSeek tokenizer，tiktoken包存在但编码缓存不存在，离线加载被网络隔离阻止，没有下载。不能把字符直接当Token，也不把其他旧版本的1M预算移植成当前模型服务能力。

历史官方R05已成功处理约47万输入Token，但当前内网模型的最大上下文、单请求限制及是否input+output共享预算没有可核验当前材料。记录unknown并作为执行前停点；不压缩sources、不减max_tokens、不切路由绕过。本地admission不是服务端context通过证明。

按上述不确定估计，两组累计输入约53–54万Token，另有最多32768输出预算，B占主要成本与延迟；缓存/实际生成量未知。未核实当前路由费率，因此不计算货币报价。本次实际新增API消耗0，Token消耗0。

## 5. 通过项与停点

- 唯一Original、两组仅Memory差异、六条当前证据对称、真实Active无M10、空Memory合法、装配/编译契约、评价预注册、不预设搜索答案、哈希可复现：离线通过。
- 方法/历史归档保护和零调用：见最终protection.json；没有源码/Prompt/Schema/Memory修改。
- 执行就绪：**待当前proxy模型上下文容量确认**。P3-B还须独立授权，并按上述单次发送规则进行编排；不得直接运行旧自动重试入口。
- 未完成项不隐去：不能声称“当前模型必然接收B”或“已准备好立即调用”。也没有证据证明B已经超限；这是未核实，不是已发生的API失败。

只新增本P3-A目录。复核入口 `PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python .../verify_freeze.py` 读取冻结产物、哈希及旧档保护，不重新生成请求。构造脚本拒绝覆盖已有input_manifest。调用数、环境执行均为0；P3-A到此停止。
'''
write('P3A_INPUT_FREEZE.md',freeze)
