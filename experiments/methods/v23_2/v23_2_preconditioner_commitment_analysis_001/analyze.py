"""Offline research only: verify archived equality and quote spans; never compile or call a model."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,importlib.util,subprocess,re
from datetime import datetime,timezone
E=Path(__file__).resolve().parent;ROOT=E.parents[3];P=E.parent/'v23_2_preconditioner_memory_ab_001'
A=P/'p3b_A_format_001/runs/A';B=P/'p3b_B_format_001/runs/B'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def link(p,label):return f'[{label}]({p})'
def block(s):return '> '+s.replace('\n','\n> ')
aq,bq=read(A/'request.json'),read(B/'request.json');ap,bp=[json.loads(q['body']['messages'][1]['content']) for q in (aq,bq)]
ar,br=read(A/'preconditioner.json'),read(B/'preconditioner.json');ae,be=read(A/'effective_plan.json'),read(B/'effective_plan.json')
o=read(P/'config/original_plan.json');c=read(P/'config/common_payload_without_memory.json');m=read(P/'config/memory_B.json')
x,y=deepcopy(aq),deepcopy(bq)
for q in (x,y):
 d=json.loads(q['body']['messages'][1]['content']);d.pop('memory');q['body']['messages'][1]['content']=d
assert x==y and aq['body']['messages'][0]==bq['body']['messages'][0]
assert ap['memory']=={'entries':[],'sources':{}} and bp['memory']==m
assert {k:v for k,v in ap.items() if k!='memory'}==c
assert ap['plan']==bp['plan']==o==ae
assert be['goal']==o['goal'] and be['checks']==o['checks'] and be['updates'][1]==o['updates'][1]
assert br['adjustments'][0]['from']==['u1'] and br['adjustments'][0]['to'][0]['text']==be['updates'][0]['text']
assert ar['adjustments']==[] and ar['checks'] is br['checks'] is None
assert [i['id'] for i in m['entries']]==['M1','M2','M3','M6','M7','M8','M9']
assert [r['ref'] for r in c['runs']]==['P1','P3','P6','P7','P8','P10']
original_diagnosis=ROOT/'artifacts/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001/diagnosis.json'
assert read(original_diagnosis)['plan']==o
for base in (P/'p3b_A_format_001',P/'p3b_B_format_001'):
 for f,h in read(base/'config/freeze.json')['files_sha256'].items():assert sha(base/f)==h,f
for base,r in ((A,ar),(B,br)):
 resp=read(base/'response.json');assert resp['content']==(base/'raw_output.txt').read_text();assert json.loads(resp['content'])==r
 assert resp['finish_reason']=='stop';assert read(base/'run.json')['status']=='valid'
assert read(A/'response.json')['response_model']==read(B/'response.json')['response_model']
files=[original_diagnosis,P/'config/original_plan.json',P/'config/memory_B.json',P/'config/common_payload_without_memory.json',ROOT/'src/skill_evolution/v23/preconditioner.py',ROOT/'src/skill_evolution/v23/preconditioner_prompt.md',ROOT/'src/skill_evolution/v23/execution_context.md']
for d in (A,B):files.extend(d/n for n in ('request.json','preconditioner.json','effective_plan.json','response.json','raw_output.txt','run.json'))
files.extend((P/'p3b_B_format_001/config/preconditioner_prompt.md',P/'p3b_B_format_001/config/prompt.diff'))
save(E/'config/comparison_manifest.json',{'created_at':datetime.now(timezone.utc).isoformat(),'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'original_diagnosis':str(original_diagnosis),'A':str(A),'B':str(B),'same_request_except_memory':True,'same_system':True,'same_original':True,'A_equals_original':True,'B_changes_only_u1_text':True,'memory_ids':[e['id'] for e in m['entries']],'current_runs':[r['ref'] for r in c['runs']],'parameters':{k:v for k,v in aq['body'].items() if k!='messages'},'new_calls':0,'new_tokens':0,'new_effective_plans':0,'note':'References and hashes only; no archived model result regenerated. Format repair is authorized P3A amendment.'})
# Small evidence index: exact selected observations, no copied full trajectories or extra input assembly.
evidence=[]
def steps(source,nums):
 if '/' in source:
  bundle=m['sources'][source];run=bundle['run'];menus=bundle['command_sets'];path=P/'config/memory_B.json';prefix=f'sources["{source}"].run'
 else:
  run=next(r for r in c['runs'] if r['ref']==source);menus=c['command_sets'];path=P/'config/common_payload_without_memory.json';prefix=f'runs[ref={source}]'
 for s in run['steps']:
  if int(s['step'].split(':')[-1]) in nums:
   cmds=menus[s['before']['commands_ref']]
   evidence.append({'source':source,'path':str(path),'field':prefix+f'.steps[step={s["step"]}]','task':run['task'],'step':s['step'],'before_observation':s['before']['observation'],'before_commands_ref':s['before']['commands_ref'],'before_commands_sha256':hashlib.sha256(json.dumps(cmds,ensure_ascii=False).encode()).hexdigest(),'action':s['action'],'action_in_pre_candidates':s['action'] in cmds,'after_observation':s['after']['observation'],'feedback':s['feedback'],'outcome':run['outcome']})
for k,n in {'P1':[2,4,8,9],'P3':[7,8,11,13,14,16],'P6':[6,14,16,18,50],'P7':[5,7,9,11,12],'P8':[9,39,50],'P10':[25,32,33,35,38], 'S1_R02/P5':[37,42,50],'S1_R02/Q5':[19,20,22,24],'S1_R03/P2':[15,16,20],'S1_R03/Q2':[25,30,50],'S1_R03/P4':[50],'S1_R03/Q4':[12,13,15,17],'S1_R03/P6':[32,33,36,38],'S1_R03/Q6':[4,10,15,48,49,50],'S1_R04/Q3':[5,7],'S1_R04/Q9':[6,7,9]}.items():steps(k,n)
for k,fragment in [('S1_R03/Q2','go to countertop 3'),('S1_R03/P4','take bread')]:
 assert not any(fragment in s['action'] for s in m['sources'][k]['run']['steps'])
assert all('go to shelf 1'!=s['action'] for s in next(r for r in c['runs'] if r['ref']=='P8')['steps'])
save(E/'results/evidence_index.json',{'note':'Selected exact facts only; command references resolve to original before-command sets. No post-action menu substituted. Current P2/P4 remain Grouping-only, not added full runs.','facts':evidence,'memory_entries':m['entries'],'diff_references':{k:{'path':str(P/'config/memory_B.json'),'field':f'sources["{k}"].diff','sha256':hashlib.sha256(m['sources'][k]['diff'].encode()).hexdigest()} for k in m['sources'] if k.endswith('/diff')}})
# Stable analytical labels are NOT new Update IDs or an executable Plan.
rows=[]
def add(id,uid,oq,bq,title,origin,change,condition,unit,strength,evidence,boundary,judgment):
 ot=o['updates'][0 if uid=='u1' else 1]['text'];bt=be['updates'][0 if uid=='u1' else 1]['text']
 assert oq is None or oq in ot,(id,'Original quote');assert bq is None or bq in bt,(id,'B quote')
 rows.append(dict(id=id,update=uid,title=title,original_quote=oq,effective_A_quote=oq,effective_B_quote=bq,source_field=f'updates[id={uid}].text',A_change='完整保留Original',origin=origin,transformation=change,condition=condition,object_unit=unit,strength=strength,evidence=evidence,support_boundary=boundary,judgment=judgment))
add('S01','u1','During any search for the exact requested object (or for the desklamp once the target is in hand)','During any search for the exact requested object (or, once the target is in hand, for the desklamp)','搜索作用阶段','Parent灯任务/一般检索；Original合并检索范围','保留','精确目标尚未获得；或已持物但需找灯','任务阶段/目标','条件要求','Goal；Parent灯Procedure；当前P1:2/8/9，Grouping G1','灯搜寻阶段下一句仍说exact item absent，范围衔接不够清楚；不能解释为已经有物也应无目的搜索；既有模糊，非B独有。','保留有据；阶段条件存在继承性模糊')
add('S02','u1','treat the search as coverage of distinct candidate receptacles rather than a loop over a few','do not restrict the search to one container type or to a small set of locations','覆盖方向','Parent系统搜索；Original位置覆盖；B强调类别','扩大覆盖维度/替换重点','持续搜索未找到','位置→位置+类别','方向性要求，B有否定式约束','当前P3:7–13/P6:6–50/P8；M3 Q5/M6 Q4','反重复和位置覆盖有据；跨类别是合理探索，不证明每个任务都必须访问多类别。找到即结束应优先。','方向有据；具体调度是探索')
add('S03','u1','When the current observation shows the requested item is absent','When the current observation shows the exact requested item is absent','局部缺失触发','Original继承Parent visibly lacks','保留','当前观察中未见精确目标','当前位置','条件要求','Parent先开闭容器；当前P6:18/50到达时drawer仍closed','未看到不等于已检查或全局不存在；结合S08先开容器。B移动句不能盖过开容器前提。','可保留，需局部且已可检查的解释')
add('S04','u1',None,"choose the next destination from the admissible 'go to' list",'移动可用性','Actor基础协议已有，B在u1显式化','新增到Update文本，继承环境约束','选择移动时','动作/位置','合法候选约束','当前P1:4移动不在before候选→no-op；M6 S1_R03/Q6:4/10/15同类问题','当前证据已足够；候选提供合法移动，不提供访问进度，不保证每个合法移动有用。','有依据的明确化；不能计为历史独有增量')
add('S05','u1','move to a receptacle not yet inspected in this search','sample a receptacle type not yet used in this search','全局新颖性','Original/Parent全局未查位置；B换为类别','替换状态单位，未消除依赖','需要判断此次搜索从未使用','位置→类别','条件要求','Execution Context；当前候选不含visited；M3/M6混合覆盖响应','局部近期新颖性可以探索；全局未用类别需可恢复状态。类别更少不等于两步历史足够。','已有信息依赖换了单位仍未解决')
add('S06','u1','once that series is exhausted without the target, switch to a different receptacle type',"rather than another instance of the type just swept or a location you just saw was empty",'类别切换优先级','Original先耗尽；B不再明示耗尽门槛','替换；放松耗尽门槛，同时偏向未用类别','当前未见目标、刚扫过一类/刚看过空位置','类别/实例','选择优先且rather than有排他性','当前P6长drawer段；M3 Q5新位置；M6 Q4扩展成功/Q2遗漏同类','有动机早换探索，未验证最佳切换尺度；just swept是否整类不明，不能声称B指定严格逐次轮换。','合理探索，排他强度/阶段定义尚不充分')
add('S07','u1','before re-entering the series',"go to cabinets, countertops, shelves, fridge, diningtable, or sinkbasin before re-entering the drawer series",'同类重新进入条件','Original耗尽后先换类再重入；B例示保留并移动触发点','继承局部先换类顺序，可能提前适用','一段抽屉搜索未得目标','类别与同类剩余实例','局部前置顺序；不是全类别完成要求','M6 Q2未访问countertop3；M9已知目标回源；当前G1 P2摘要','原文or是可选类别，不是全局固定排序；无“所有其他类别都采样后才返回”的明文。无条件推迟已知有价值同类位置不受证据支持。','局部探索可留；更强全类别禁返解读不成立')
add('S08','u1','Sweep a numbered series of same-type containers in one direction without returning to earlier ones','While sweeping the numbered instances of one container type, move in one direction and do not return to an instance you just left empty','编号推进与回访限制','Original新增单向系列；Parent仅避免立即回空','部分保留/收窄禁返对象','处于一次类内扫描，刚离开位置为空','编号实例/近期位置','单向扫描+条件禁返','当前P3:7–11空回访；M3/M6旧避返未稳定落实；M9条件回源','无return to earlier ones变成just left empty，较局部；仅单向编号可借当前编号/候选执行，不能因此保证全局遍历；合理回源不应由单向扫描跨阶段禁止。','收窄有据；单向作为启发式可探索')
add('S09','u1','open a closed cabinet/drawer/fridge on arrival and inspect its contents','open a closed cabinet/drawer/fridge on arrival and inspect its contents before leaving','先检查闭容器','Parent已明确before leaving；Original省略该短语；B恢复','保留/恢复完整前提','到达且闭合、仍需找目标','具体容器/动作','条件要求','当前P6:18/50 closed；M3 Diff及开容器响应','不能将“未观察到目标”直接理解为离开闭容器；到达闭容器并未完成采样。额外开容器在易例可增步，不推广到与任务无关操作。','有据保留，防止采样与检查混同')
add('S10','u1','Use the most recent observations to notice when the next move would revisit a receptacle just left empty or repeat the same small set of locations','a location you just saw was empty','近期循环检测','Parent/Original近期回空；B部分压缩','保留即时空回访，删去显式小集合循环检测','近期可见且无新目标/状态变化','近期位置','避返条件','P3:7–11；P6:6/14/16；M6反循环未稳定兑现','近期线索可执行；较长小集合循环本来也超两步，删除不等于降低已证有效行为；B全局类别不能替代可见局部信号。','局部保留合理；长周期能力仍有限')
add('S11','u1',None,'Continue until the exact target is found','发现目标的检索出口','Parent已有；Original依赖Goal/Parent；B显式化','新增文本但继承任务阶段','当前发现精确目标','目标/检索阶段','结束搜索而非结束任务','当前P3:13/14/16；P10:32/33/35/38；M3 Q5/M6 Q4','找到≠获得/处理/交付；Goal保留后续流程。灯任务找灯出口有S01模糊，不应把整任务结束混入。','继承有据；不支持任务直接终止')
add('S12','u1',None,"or every receptacle type available in the room's action list has been sampled once",'类别采样终止','Original无此条件；Parent是all plausible candidate receptacles inspected once','新增到Update；将Parent位置穷尽边界换成类别采样边界','目标未找到但每类已采样一次','位置检查→类别代表采样','独立的替代结束条件','M6 P2:15/16 vs Q2遗漏countertop3；Parent首步全文；M3/M6 Diff仍为receptacles','部分实例不等于整类，更不等于全部合理位置。B未把它限定为一轮探索结束后继续搜；也不能推断Actor已经提前结束。调度动机不足以支持此完成标准。','新增越界承诺；文本风险已确认，行为后果未知')
add('S13','u1','This is coverage for finding the exact target within the step budget','This is coverage for finding the exact target within the step budget','预算目标','Original已有，B原样保留','保留','50步总预算下搜索','任务预算','目的性表述，非保证','当前P10:32–38；M6 Q6:48–50、P6:38完成','不是guarantee；不含数值预留预算，也未规定处理交付保底。不能说B删了原有明确数值预算，因为Original不存在。','目的保留；后处理预算执行边界仍未明确')
add('S14','u1','it does not permit picking up, conditioning, or placing a substitute object','it does not permit picking up, conditioning, or placing a substitute object','精确目标/不替代','Parent/Original已有','保留','目标尚未找到或仅近似物可见','物体类别/获取处理交付','任务正确性约束','当前P7 knife非butterknife失败；M3 Q5；M8旧Diff/响应','不操纵替代物不等于能够成功，也不证明目标不存在；M8不支持提前停止。','有依据保留')
add('N01','u2','Do not spend steps on actions that cannot change the world or reveal new information.','Do not spend steps on actions that cannot change the world or reveal new information.','无信息无变化动作','Original概括Parent反空查','保留','可知动作无状态变化且无新信息','动作/状态','原则性避免','P7:11/12；M6 Q6重复不可用移动','or允许有信息价值的非状态变化动作；不能读作所有look/inventory禁止；预先准确判断无新信息仍有认识边界。','原则有据；不是全面信息动作禁令')
add('N02','u2',"If an action returns 'Nothing happens,'","If an action returns 'Nothing happens,'",'no-op触发不重复','Original新增广义反馈触发','保留','刚收到no-op','动作/当时前提','与N03组成不重复约束','当前P1:4 off-list；M6 Q6:4/10/15 off-list','反馈证明当时未奏效，不证明后续所有状态都无效；原文无until state changes时限，也未明示永久。需收窄歧义而非断言已永久禁令。','状态作用域不足；当前事实可识别')
add('N03','u2','do not repeat that action or an equivalent one','do not repeat that action or an equivalent one','等价动作禁重试','Original新增，Parent限立即回空/重复空inventory','保留','no-op/重复look/空inventory任一触发后','动作等价类/状态','排他要求，等价/时间边界不清','M6 Q6同一不可用移动；当前P1:4','历史只支持当时同无效前提，未测试全部等价动作。无证据要求永久禁止，亦无证据说已发生禁用有效重试。','需条件限定；M6提示旧规则未兑现而非证明更强禁令')
add('N04','u2',"if a 'look' repeats the description you already have for the current receptacle", "if a 'look' repeats the description you already have for the current receptacle",'重复look','Original显式新增look触发；Parent有空位置避免重访','保留','同位置内容已知且本次look重复','观察/当前位置','避免继续重复条件','当前P7:11/12相同反馈；M6空位置exam重复','这次look无新增信息可观察；状态变化后可能有用，不应排除；历史不提供最佳查询频率。','局部要求有据；后续适用边界需保留')
add('N05','u2',"if 'inventory' is issued while carrying nothing", "if 'inventory' is issued while carrying nothing",'空手inventory','Parent已Do not repeatedly；Original扩大为一次触发','保留Original强化','当前已知空手而发inventory','持物状态/信息动作','一次空查后禁重复','P8:39/P10:25；M3/M6 Diff反重复空查','已知空手时反复空查无益；仅实际空手不等于Actor事先可知，首次查询可用于消除不确定性。不可机械禁止全部inventory。','重复限制有据，空手知识前提不清')
add('N06','u2','Instead immediately take a state-changing action','Instead immediately take a state-changing action','立即状态改变','Original新增替代动作强度','保留','信息/no-op触发后下一步','动作选择','立即且限定state-changing','P1:4、P7:11/12浪费；M6 Q6重复无效','避免无信息重复不逻辑蕴含下一步只能改变状态；若必要新信息不可由观察得，应允许获取。可用动作/任务阶段需另满足。','附带强度依据不足，现有材料无实际B退化证明')
add('N07','u2','move to a new uninspected receptacle','move to a new uninspected receptacle','u2残留全局新位置','Original继承Parent/u1进度要求','保留','决定转去搜索','位置/搜索进度','替代动作之一','Execution Context；S05全局信息边界','u1变为类别不解决u2全局未查；不是新B引入。移动可选项非每次必须移动。','继承性能力问题未修正')
add('N08','u2','open a closed container, take the target, perform the required clean/cool/heat, or place the target at the destination','open a closed container, take the target, perform the required clean/cool/heat, or place the target at the destination','任务相关动作备选','Original整合Parent/Goal任务流程','保留','依闭合/目标可取/持有/处理完成等实际前提','动作/任务阶段','可选动作列举，非顺序强制','P3:14/16；P10:33/35/38；M7 Q3:5/7','or不是命令任意执行未满足前提动作；需Actor现有候选和Goal约束。heat有历史条件证据，当前六条无成功heat。','有效行为文本保留；不能据此保证所有前提完整')
save(E/'results/commitment_matrix.json',{'status':'offline_research_annotations_not_a_plan','sources':{'original':str(P/'config/original_plan.json'),'A':str(A/'effective_plan.json'),'B':str(B/'effective_plan.json')},'rows':rows,'goal':o['goal'],'checks':o['checks'],'no_official_update_ids_added':True})
header=f'''本报告只使用最近合法同格式Prompt配对：{link(A/'preconditioner.json','A_format_001')}、{link(B/'preconditioner.json','B_format_001')}。Original来自{link(original_diagnosis,'R05 P1-B授权重试Diagnosis')}的`plan`。不混用原B、无效A或旧正式Plan。没有新增模型、环境、编译输出或Candidate。

{link(E/'config/comparison_manifest.json','材料路径及哈希')}核验：完整请求删除唯一`memory`字段后相同；A空Memory，B为M1/M2/M3/M6/M7/M8/M9，无M10；当前完整runs仍P1/P3/P6/P7/P8/P10，Grouping G1—G4相同。A Effective等于Original；B只改u1文本，Goal/u2/Checks不变。格式补充是已授权协议修订，不是P3-A原Prompt逐字不变。
'''
trace=f'''# P3-C1 承诺追溯

{header}

## 1. 如何读取证据

- O/A/B字段均为`updates[id=...].text`；下文S/N编号仅为研究定位，不写入任何正式Update。逐条引文已经以子串核验，A每项均与Original相同。Original/Effective全文仍在原文件，未重写。
- 当前事实：{link(P/'config/common_payload_without_memory.json','共同输入')}的`runs[ref=Pn].steps[step=Pn:s]`。P2/P4/P5/P9仅已有Grouping摘要，不能把其全文作为A/B可用证据。
- 历史事实：{link(P/'config/memory_B.json','真实Memory')}的`entries[id=Mx]`、`sources["S1_Rxx/diff"].diff`、`sources["S1_Rxx/Qn"].run.steps[step=Qn:s]`。历史Pn/Qn必须带轮次，避免与当前R05混淆。
- {link(E/'results/evidence_index.json','精简证据索引')}保留选定步的行动前观察、候选引用/哈希、动作、执行后反馈和结果。合法性均按`before.commands_ref`核查，未用after候选替代。不复制整批轨迹。
- 研究者展开sources的结论不等于模型实际叙述过的推理。B只显式引用M3/M6；其余Memory用于研究保留条件，不能声称B据其调整。

## 2. 关键来源事实与支持边界

| 来源 | 实际修改/行为 | 能支持什么，不能支持什么 |
|---|---|---|
| 当前P3:7–11，13/14/16 | 空drawer回访后在diningtable找到mug，获取交付成功 | 改善低信息重复和具体位置覆盖；不是“换类必然优于扫描”的隔离证据 |
| 当前P6:6/14/16、18–50 | 早期drawer/其他位置循环，后段长drawer推进，50只到达closed drawer20而未检查其内容 | 长同类安排与预算问题；不得把whole run说成只访问一类或已查完20个 |
| 当前P8:9–50；P10:32–38 | P8重复cabinet等且未去shelf1；P10晚到diningtable后取apple、cool、place成功 | 改善搜索机会分配，保留后续处理；P8也访问过bathtub/countertop，不能抹去这些类别 |
| M3 / S1_R02/diff + P5/Q5 | 添加通用搜索/开容器/避回空/精确对象/条件clean/直接交付等联合条款；Parent替代soapbottle失败，Q5:19到bathtubbasin取dishsponge，22clean，24交付成功 | 有条件的拓展覆盖与精确目标联合收益，且别的任务仍循环；没有独立证明类别采样是有效成分 |
| M6 / S1_R03/diff + P4/Q4 | 加current/recent反循环、缺目标/高步数时扩展新位置；Q4:12到diningtable找到bread，13取、15cool、17交付；P4步限 | 支持再次审视原覆盖安排；不确定最优类别顺序/切换尺度 |
| M6 / S1_R03/P2:15/16/20 vs Q2:25/30/50 | Parent到countertop3找到bread并成功；Candidate回countertop2但从未到3，最终失败 | 同类别实例仍有价值。类别访问不代表该类检查完；不能反推必须类内穷尽 |
| M6 / S1_R03/Q6:4/10/15、48–50 | 多次go cabinet3不在行动前候选且Nothing happens；48开cabinet9、49取plate、50到fridge，未完成；Parent38成功 | 旧反循环/预算优先文字未稳定兑现；支持当时动作前提校验、留意后处理预算，不支持永久禁用动作类 |
| M1/M2 | 灯共址与普通任务行为保留；M1记录不同成功动作顺序 | 保留任务条件，不能锁唯一严格灯步骤顺序 |
| M7 / S1_R04/Q3:5/7 | 持potato时合法heat并交付成功，Diff有条件直接温度处理 | 当前目标/动作前提成立时保留处理；无目标时不能保证成功。M7中“robust”等词不当独立因果证明 |
| M8 | 近似物不替代，未发现精确物时仍失败 | 不替代有任务依据；“没找到”不当作隐藏世界不存在/可以停止 |
| M9 / S1_R04/Q9:6/7/9 | 当前/近期可见源处有剩余精确saltshaker时回源取第二个并交付 | 有效回访与盲目空回访不同；本轮主要是单物/灯，不能强行新增多物流程；不能普遍禁止已访问位置 |

所有历史比较为单次联合编辑，不隔离子句因果收益。M6 knowledge并未规定类别一次停止；实际Diff仍是`all plausible candidate receptacles have been inspected once`。

## 3. Parent、Goal、Checks的约束谱系

Parent一般检索第一项：

{block(c['parent'].split('1. Identify and search')[1].split('\n2. Manipulate')[0].join(['1. Identify and search','']))}

Parent自身已有全局未查/全部位置检查一次边界；这不证明它可观测，也不保证全部可达。其下一项又说未找到就继续系统搜索，存在“穷尽但未找到”如何处理的模糊。Original u1没有新增明确停止标准，也没有明确撤销Parent边界。B新增的是类别级更弱完成标准，不是从完全没有停止边界凭空增加停止概念。

Goal（A/B逐字相同）：

{block(o['goal'])}

Goal保留精确对象、必要处理/交付、灯共址和直接获取放置。B没有新增成功保证；其`effective ingredient`位于reason，是过强的解释性成分归因。Update中的within budget是目的，不应机械判为guarantee。当前Parent全文没有明确heat/cool专节；相关保留依据来自Goal、u2列举、当前P10 cool和历史M7，不把后轮Candidate Skill混作Parent。

Checks（A/B均返回null，原条目保留）：

'''
for k in o['checks']:trace+=f"- `{k['id']}` / `checks[id={k['id']}].question`：{k['question']}\n"
trace+='''
C1关注新位置/换类与空回访，却没有直接检验类别一次退出时是否仍有剩余合理位置；C2关注避免no-op，不单独检验状态变化后的重试；C3保留获得精确目标后的处理交付。Checks不是Actor指令，不能弥补Update缺失的条件。本次不修改它们。

## 4. 行为承诺逐项矩阵

'''
for r in rows:
 trace+=f"### {r['id']} · {r['title']}\n\n| 字段 | 分析 |\n|---|---|\n"
 fields=[('原文定位',r['source_field']),('Original',r['original_quote'] or '该Update未明示，须结合Parent/Goal判断谱系'),('Effective A', '原文不变（同上）' if r['original_quote'] else '同Original，无此独立子句'),('Effective B',r['effective_B_quote'] or '无对应子句'),('来源/谱系',r['origin']),('实际变换',r['transformation']),('行为及适用条件',r['condition']),('对象单位',r['object_unit']),('强制程度',r['strength']),('证据定位',r['evidence']),('支持边界/可执行性',r['support_boundary']),('判断',r['judgment'])]
 for k,val in fields:trace+=f"| {k} | {val.replace('|','／')} |\n"
 trace+='\n'
trace+='''## 5. u2未变意味着什么

M6额外提供的是“加入反循环/反空查指导后仍有重复不可用移动与预算失败”的响应，不是仅又一条no-op示例。它可以促使重新检查指导怎样落地、可用动作前提是否明确；当前P1:4本已能发现合法动作问题。B对u1显式补go-to候选，却对u2只用“与观察相符”解释Keep，没有处理N03等价/时间作用域和N06立即state-changing边界。这是最终文本未体现这些边界，不是证明模型没读M6。

M6并没有展示同一动作在前提改变后重试成功，因此不能说Memory已直接验证某一种重试规则。相关限制来自状态依赖逻辑、当前能力与原规则的范围核查。也不能说u2必须改才代表Memory被正确使用；有充分前提解释的Keep可能合理，这份输出未给出足以消解歧义的解释。N01本来允许有新信息的动作，N08的or是备选，不能据关键词编造全面禁令。
'''
(E/'reports/P3C1_COMMITMENT_TRACE.md').write_text(trace)
(E/'reports/P3C1_TRANSFORMATION_BOUNDARY.md').write_text(f'''# P3-C1 变换边界

{header}

## 1. 一次方向调整实际包含了什么

完整证据与原文见{link(E/'reports/P3C1_COMMITMENT_TRACE.md','承诺追溯')}，机器矩阵见{link(E/'results/commitment_matrix.json','22项承诺矩阵')}。S/N编号是分析编号，不是正式Update ID。

Original：位置覆盖目标 → 类内编号单向扫描 → 该序列耗尽后换类 → 再次进入之前先换类别。A原样Keep，并在reason声称编号启发式可由两步历史落实；没有解释如何恢复全局未查和耗尽状态。

历史：M3/M6显示扩展位置与精确目标指导下存在成功，也显示避回空/高步数优先新位置未稳定落实，仍有同类别实例遗漏、无效动作和晚发现。这支持重新考虑具体覆盖安排和执行前提，不确定唯一替代调度。

B：去当前合法候选中的未用类别 → 不优先继续刚扫过类别 → 在抽屉例子中先换类再重入 → 类内单向仍保留，回访限定到刚离开空实例 → 新增“每类别采样一次”的出口。方向调整、合法性、回访强度、状态单位与完成判据是五种不同决定。

## 2. 边界对照

| 要求 | 是否有改变动机 | 历史响应支持什么 | B实际如何改变 | 判断 |
|---|---|---|---|---|
| 搜索调度 S02/S06 | 有，当前长drawer段/循环，原规则效果不稳 | M3 Q5/M6 Q4扩展到具体新位置后成功；联合编辑有条件支持 | 从显式类内耗尽门槛转向未用类别优先；仍保留类内扫描 | 值得探索，不证明跨类必优，不是固定round-robin |
| 类别切换 S06/S07 | 有，防止局限少数类型/位置 | M6也有跨cabinet/shelf/fridge但漏countertop3的失败，限制过度推广 | 缺目标时偏向未用类型，例示另一类别后重入drawer | 局部安排有动机；无充分理由让任何新类别都高于已知有价值同类实例；切换尺度未确定 |
| 同类回访 S07/S08/S10 | 空回访可限制，有用回源需保留 | M9已知源处剩余目标；M6同类实例遗漏 | 删除return to earlier ones，换成just left empty；例子仍先换类再重入 | 有意义的局部收窄；没有明文“全其他类别完成后才能回返”，不能强加此结论 |
| 完成条件 S11/S12 | 找到目标应进入后续任务；没有独立类别一次退出动机 | Parent/M3/M6是位置检查边界；M6同类遗漏反对把类型当位置覆盖完成 | 明确新增every receptacle type sampled once | **单位/强度越界**；调度变化不需要同步降低搜索完成标准 |
| 全局进度 S05/S12 | 有，Actor只有两组历史 | 历史文字未稳定执行；不是所有编号都不可行 | 位置未查变成类别未用/全部采样 | 信息依赖换名保留。候选只告诉可做动作，不能恢复全历史 |
| 无效动作 N01—N08 | 状态不变的无信息重复应避免 | M6旧规则下仍重复off-list移动；未证明永久禁动作/只许state-changing | u2完全不变，u1补合法goto | 可保留局部目标；u2状态/等价/信息价值边界未澄清，不等于Memory完全没被用 |
| 必要行为 S01/S09/S13/S14 | 通常需保留，若证据支持可有针对性改 | M1/M2灯与交付，M7处理前提，M8不替代，M9有条件回源 | Goal/u2保留，开容器/不替代保留；类别结束可能提前剥夺目标发现机会 | 文字保留不等于无冲突；未观察真实退化，不能说后处理被删除 |

## 3. “其他类别采样后才允许返回”应怎样读

B实际两处文字：

> sample a receptacle type not yet used in this search rather than another instance of the type just swept

> go to cabinets, countertops, shelves, fridge, diningtable, or sinkbasin before re-entering the drawer series

第二句用or并置可选类别，不是按此列表固定排序。before确实表达先换到其他类别再重入的局部顺序；这个结构Original也有，只是Original明确在序列耗尽后生效，B没有保留同样的耗尽条件。

第一句更强：只要有未用类型可选，字面上偏向它而非刚扫过类型另一个实例，可能连续推迟同类剩余位置。可以报告这种行为风险和未说明例外，不能把它改写为“必须采样完所有其他类型才允许任何回访”。B也没有固定检查两个/三个位置的数值规则；本次不沿用早期候选的错误。

M9的有用回源不是空回访。B的just left empty本身可以与有目标源回访相容；更广的未用类型优先、单向扫描和阶段模糊仍可能竞争。尚无Editor/Actor，不能确定最终会以哪一条为优先。

## 4. 搜索出口的谱系和单位变化

| 层次 | 原文/事实 | 含义 |
|---|---|---|
| Parent一般检索1 | `until the exact target is found or all plausible candidate receptacles have been inspected once` | 已有位置级检查一次边界，同时依赖全局状态；不是已验证正确的oracle |
| Parent一般检索2 | `If the exact target has not yet been found, continue the systematic search` | 未找到应继续，和第一项穷尽边界的衔接未充分定义 |
| Original/A u1 | 无单独“全部位置/类别一次就结束”句；Goal要求目标获取处理交付 | 不能据此断言Original取消了Parent边界；也不能声称它明文要求无限搜索 |
| B u1 | `Continue until the exact target is found or every receptacle type available in the room's action list has been sampled once.` | 出口从位置检查换成类别采样，且候选菜单类别的动态范围未说明 |

访问类别≠检查该类别全部位置；到达闭容器≠打开并检查；当前可移动的类别≠隐藏世界全部可能位置；完成搜索子程序≠完成任务。M6 P2/Q2直接显示“去过countertop类”仍可能错过另一个countertop上的目标。

B未说明这是一次探索阶段结束后还将恢复剩余位置搜索，因此不能替它补写“只是一轮采样结束”的救济解释。另一方面，它也没有明确发出终止Episode动作；准确结论是**引入可读作停止搜索的不足出口**，而不是已证明真实任务早停。

## 5. 目标变换、必要配套与附带承诺

**目标变换**：在当前问题下重新安排类内持续搜索与跨类别探索的机会；可大幅改变方向，历史并不支持仅做文字微调。

**必要配套**：如果放松类内耗尽门槛，就需处理仍然要求同类耗尽后才能换类的旧条件，使两者一致；如选择依近期信息触发，则条件必须可由当前/近期信息判定。合法移动、闭容器先检查、精确目标及后续任务前提仍适用。配套可以跨句甚至跨u1/u2，但必须有真实依赖，不能默认整段自由重写。

**不是必需的配套**：每类采样一次即结束、固定全局类别顺序、永久排除同类剩余位置或状态变化后的重试。改变搜索方向并不逻辑要求这些条款成立。后几项并非本次B全都出现，只用于界定不能由方向动机自动授权的空间。

可允许的边界示例（研究者假设，不是新Plan）：允许把“换类必须等当前类耗尽”改为依据可见局部信息进行探索分配，同时保持目标获得后的处理/交付以及对有价值剩余位置的访问资格。若只改变这一调度关系，不需要同时降低完成标准；若另有证据支持结束边界变化，应独立论证。此示例没有指定类别、批量、最终Skill文本，未经过模型或执行验证。

## 6. 可观察的功能性解释

B的reason对“为何改调度”给了解释，对“为何所有类别一次即可结束”没有相应论证。`from:[u1]`授权输出的是整段完整替代text，不能在接口层区分某个子句是目标变换还是顺带新增；编译器复制合法text并验证结构与引用，不判断结束条件的证据。

因此可以定位：**一处历史响应动机通过整段替换承载了多项独立承诺，其中完成判据的变化没有自己的依据，却一起进入Effective。** 这是已观察到的变换边界失守，而不是证明模型某个隐藏心理过程。源码也没有要求必须增加结束条件，更不是强迫B这样写。自由全文表达允许细致修改，但不保证语义范围保持。

B已明确使用M3/M6并改变实际Update，故“完全未读取Memory”不符合显式输出。更准确的缺口是：未将混合响应落实为不同承诺的差异化支持范围。随机性、输入长度等仍可能解释为何这次选择如此，当前材料不能隔离原因。
''')
(E/'reports/P3C1_MECHANISM_PROPOSAL.md').write_text(f'''# P3-C1 最小机制建议：以承诺为作用对象的定向重写

这是待验证设计假设，不是已实现算法。没有新Prompt、Schema、状态机、评分器或Agent；没有构造正式Effective Plan。依据：{link(E/'reports/P3C1_TRANSFORMATION_BOUNDARY.md','变换边界分析')}。

## 1. 一个统一的操作规则

**历史编辑—响应先定位需要改变的行为关系；允许修改该关系及使其成立所必需的相连条件，其余必要行为边界保持，除非有另一条独立依据支持改变。**

作用范围不是“改多少字”，而是“哪些行为选择被重新授权”。可以大幅替换策略；也可以Keep、拆分、合并或撤回。一个目标变换可能连带多个条件，不能把全部配套都机械当成越界；但每个额外关系必须有独立问题动机或必要依赖。

## 2. 怎样真正执行这条规则

以下是现有Preconditioner内部的判断顺序，不增加独立模型阶段或结构化输出字段。研究矩阵用于离线评价，不要求模型输出S/N编号。

| 内部决策 | 操作与依据 | R05锚点 | 既有输出中的落实 |
|---|---|---|---|
| 定位作用对象 | 用原Update原句界定触发条件、选择对象、顺序/强度、出口；将相关历史Diff和响应关联到具体行为关系 | M6扩展后混合结果作用于“序列耗尽才换类”及位置覆盖风险，不自动作用于任务结束 | `from`仍指u1；`reason`用原句/行为关系说明改变什么，`basis`列当前引用/M3/M6 |
| 决定允许变化 | 当前事实与历史响应决定某关系可Keep、收窄、强化、替换或撤回；证据不唯一时允许问题明确的新假设 | 跨类更早尝试可为探索，不声称历史证明更优 | 完整`to.text`给明确可操作行为；未验证预期放`reason`，必要时用`checks`观察 |
| 判断配套依赖 | 假设不改变某相邻条件，目标变换是否无法执行、前后矛盾或破坏任务必要行为？若是，说明具体依赖；若否，应独立给依据而非自动带入 | 放松耗尽前提要协调旧耗尽门槛；不能依未知全局状态触发；类别一次结束对换类不是必要条件 | 同一replacement可改多个句；关联多个原Update时用现有同时Adjustment，不串接新Update |
| 保留未受影响边界 | 核对新旧具体要求的语义差异，明确没有依据改变的有效边界；原边界本身错误则单独处理，不盲目保护 | 目标获取后的处理/交付、可知的有效回源、先检查闭容器；Parent全局穷尽也不能因旧有而视作真理 | 完整`to.text`保留必要内容；如拆合则配套更新Checks引用 |
| 处理剩余无据承诺 | 对新添的顺序/范围/出口关系，如果既非目标、无必要依赖又无独立问题依据，不能随整段替换默认接受 | 类别一次终止没有独立依据，应排除该附带变化；不是因此撤回全部跨类探索 | 在生成最终合法响应时完成定向重写；有独立可行部分则保留，必要时合法撤回/停止 |

“必要配套”的检验不是数学因果证明，而是可审阅的行为依赖解释。例如：删除类别一次结束仍能表达换类探索，因此它不是表达该方向的逻辑必要条件。若另一个实验问题确实要检验有界采样，应说明采样后如何继续任务及其独立动机；不能假借历史覆盖收益为整套约束背书。

## 3. 合理探索怎么保留

- 不要求历史已有成功策略；当前问题可以提出全新大幅方案。要求清楚：回应什么问题、预期哪种可观察行为改变、何种条件下不应继续套用。
- 具体操作可以坚定明确，未验证性写在reason/checks，不把Actor指令改成含糊的“也许”。
- 允许在有独立动机时改变结束条件、顺序甚至范围；禁止的是把对方向的支持自动传给所有附带条款，不是禁止某类策略。
- 不以unvisited/always/once等词直接判定。局部编号推进可能由观察恢复；近期新颖性可探索；全局未查如果没有可恢复依据才是前提问题。可观测性沿用原Actor约束，不恢复暂缓的能力优化项目。
- u2如果合理Keep，需按当时状态/信息价值解释为何范围适当；不因M6含负例就必须更严禁令。M6能促使检查旧指导未落实，不证明某种新强度必然奏效。

## 4. 现有接口能做什么，不能做什么

源码：{link(ROOT/'src/skill_evolution/v23/preconditioner.py','preconditioner.py')}，`compile_effective_plan`（51—126行）；原规则：{link(ROOT/'src/skill_evolution/v23/preconditioner_prompt.md','原Prompt')}第2—4节。

| 层次 | 已有能力 | 不能保证 |
|---|---|---|
| Preconditioner语义判断 | 将目标与配套变化映射到完整replacement；reason/basis表达依据；checks表达行为预期；允许Keep/拆合/撤回 | 单靠指令不能保证每次正确分解承诺、识别依赖或保留所有边界 |
| Adjustment表达 | `from`选原Update、`to`输出完整id/text；多个有依赖要求可在同段或合法拆合中落实 | `from`不能指定语义子句或设置锁定区；每条basis支持整次Adjustment，不是自动逐子句证明 |
| 确定性编译 | 检查字段/ID、引用存在、每原Update最多消费一次、合法拆合、新ID冲突、Checks存活引用；Goal程序保持；未消费Update原样保留 | 不识别“类别一次”是否等于“位置穷尽”、触发状态是否可见、全段新限制是否有据、自然语言实际含义 |
| 研究评价/后续执行 | 独立核查目标变换、必要配套和额外承诺；之后观察真实动作 | 无执行则不能判定新终止已经早停或某调度成功率更高 |

本次只读检查源码和已存编译结果，没有调用编译器生成新Plan。Effective中basis按原Update谱系继承，历史证据仍保留在Adjustment的basis/reason；评估必须读两者，不能把Effective无M3/M6当成引用丢失。

若要**程序强制**子句范围不变，现有无结构text接口没有足够信息；需要结构化承诺、编辑跨度或语义审核等额外机制。这些不在本次范围，也不应假装已有编译器能做到。当前最小方案是可执行的模型决策流程假设与离线可反驳评价，尚非代码级保证。

## 5. 与“更谨慎”的实质差别及诚实边界

原Prompt已说证据支持、保留重要有效行为、不引入无关要求，仍产生本次结果。因此不能只再加一句谨慎便宣称算法创新。

此建议的潜在区别在于**生成对象与操作边界**：先选择要改变的行为关系、明确必要依赖，再完成整段表达；不是先自由生成完整替代、事后笼统寻找证据。变化范围能够被离线矩阵逐项反驳：调度变化有据不自动给结束条件授权；一个配套变化必须能说明不改它为何造成执行/一致性问题。

但若下一实现只是把这些词加入Prompt、reason更长，而最终text仍自由附加限制，那么实质上仍是普通提示修辞。只有后续对照观察到：有据目标变换保留、依赖条件处理正确、无据附带承诺减少、必要行为未损失，才能主张产生操作层面的增量。当前没有证据证明该增量已实现。

## 6. 下一阶段如何检验（仅建议，不执行）

1. 先冻结承诺级评价与本次原A/B结果，不能把研究者的边界示例当唯一正确策略或模型结果。
2. 若获授权实现一个最小候选，在同一Original/当前证据/真实Memory/模型和格式契约下，与现有Prompt比较。新Prompt有Memory只对旧A无Memory会同时改变两个变量，不能归因。若还要检验Memory增量，应在新候选下也保持同Prompt的有无Memory对照。
3. 先独立评价每个输出，再比较：是否合理作用于目标关系；多项改动的配套依赖能否说明；是否保护位置/类别粒度、任务前提；探索是否仍具体；Keep是否有据。不要只统计修改多少。
4. 可预注册重复数与技术失败处理，保留全部样本，不语义择优；不根据第一结果临时换证据/改Prompt。扩大到其他冻结案例时，用它们验证不同边界，不写特定搜索答案。
5. 文本层通过后另行授权Editor/Replay，核查实际切换、同类剩余位置、真实终止/处理交付及no-op重试。单次轨迹仍不足以证明稳定因果收益。

不建议当前继续无目的重复旧Prompt直到抽到理想输出。若问题是“方向信号多稳定”，预注册重复旧A/B仍有独立价值；若目标是修复本次已定位的范围失守，应先把这套变换规则和验收边界讲清。两者回答不同研究问题。
''')
(E/'reports/P3C1_DECISION.md').write_text(f'''# P3-C1 阶段结论

{header}

## 1. 本次直接结论

**历史响应支持重新审视的是长同类搜索的调度强度、反循环规则的实际可落实性、具体位置覆盖及后处理预算风险；它没有证明类别采样即可完成搜索。B确实改变了前一部分，同时又未经独立论证改变了后一部分。**

可观察的功能性原因是：M3/M6的方向性依据被用于整条u1的替换，新的text同时携带调度、进度状态和结束标准；reason解释了调度修订，却没有解释为何类别一次是充分退出条件。原编译只检查结构/引用，照样保留这些语义要求。不能据此断言隐藏推理心理过程，也不把责任归为Memory没进入输入。

## 2. 十项问题的回答

| 问题 | 结论 |
|---|---|
| 1. A Keep与B Adjustment主要差异？ | A保留“类内单向序列耗尽后换类”。B优先未用类别，保留类内单向、把禁返收窄到刚离开的空实例；显式合法goto，并新增类别采样一次结束。u2/Goal/Checks不变。 |
| 2. 哪些变化有历史响应支持？ | M3/M6“旧指导有局部覆盖收益但仍循环/遗漏/晚获取”支持重新考虑调度与实际条件，B明确据此变化方向；不是证明固定轮换优越。 |
| 3. 哪些当前事实就足够？ | 当前P3/P6/P8/P10支持改善覆盖机会分配；P1:4支持合法移动；Actor两步历史限制已能质疑全局进度；当前任务/Goal支持精确目标及处理交付。B独有纠正不等于Memory独有信息。 |
| 4. 哪些是合理探索？ | 较早换类、局部编号推进、利用近期空观察避返，只要触发可见且不排除必要行为，可作为待验证策略。没有证据确定最佳切换尺度或顺序。 |
| 5. 哪些附带承诺越界？ | S12类别一次退出无充分独立依据；S05/S12全局未用/完成状态缺可恢复支持；对未用类别的一般优先可能推迟有用同类实例，需要条件限定。B没有明文“所有其他类别采完才可返回”，也没有数值批次/固定全局排序，不能编造这些错误。 |
| 6. 哪些旧问题未解决？ | 全局未查依赖从位置移到类别，u2仍全局新位置；N03状态/等价动作边界、N06立即state-changing过强仍在；预算只有目标性文字。B没有删除原有明确预算额度——Original本来没有。 |
| 7. 为什么不是Memory没被读取？ | 请求含完整真实Memory sources，B显式引用M3/M6编辑后的响应并实际改变u1。能证明显式利用线索，不能证明内部如何处理全部反例。缺口在于支持范围没有落实到各独立承诺。 |
| 8. 下一最小机制？ | 历史响应定位原行为关系；确定目标变换与必要配套；其余必要边界保持或另给独立依据；最终仍用原Adjustment完整text表达。允许大幅改动与新假设，不新增字段/Agent。 |
| 9. 还应重复原Prompt A/B吗？ | 估计随机稳定性时有价值；不应为抽到理想答案继续重试。当前修复目标更适合先明确变换规则与承诺级验收，再授权受控对照，不能由本次直接宣布算法有效。 |
| 10. 哪些需后续实验？ | 定向规则是否稳定减少无据附带要求需模型对照；真实搜索覆盖/终止/交付/no-op效果需Editor与Replay；策略优劣及独立因果收益需更严谨重复或隔离比较。均未执行。 |

## 3. 如何落实为最小机制而不是又一句谨慎提示

将“允许改变的对象”明确为原Update中的行为关系，而非整段主题：例如可以改变换类门槛，并协调与其冲突的旧耗尽要求；这不自动允许把搜索完成单位改成类别。对每项配套问：不一起改，目标变换是否不可执行、矛盾或损害必要任务行为？若不是，就需要独立依据或问题明确的新假设。

用原`reason`解释目标/配套与保留边界，用`basis`关联当前和历史响应，用`to.text`完整表达；不输出研究矩阵或新增字段。编译器仍只能检查结构，不能保护语义子句。因此这是可评估的生成流程假设，**尚不能声称形成了受程序保证或已验证有效的算法增量**。详细建议见{link(E/'reports/P3C1_MECHANISM_PROPOSAL.md','机制方案')}。

## 4. u2与保留条件的特别边界

M6确实增加了“旧反循环编辑之后仍重复不可用移动”的信息；B未据此改变u2。但M6未隔离验证状态变化后的重试成功，也未证明最佳查询策略，不能机械强制Adjustment。可以确认的是u2边界仍未澄清，不是B完全没用Memory。

Parent位置级结束条件自身也依赖全局状态，不应当作必须永久保留的真理。需保护的是任务必要条件与证据单位的一致性；旧不合理要求有据时同样可修改。Goal保留灯/处理/交付，不能自动消除Update中可能阻碍目标发现的规则。没有新Skill/执行，不能报告这些风险已经造成早停或失败。

## 5. 交付与保护

- {link(E/'reports/P3C1_COMMITMENT_TRACE.md','承诺追溯')}：22个u1/u2语义单元，另列Goal/Checks/Parent约束；逐项原文、来源、当前/历史依据和判断。
- {link(E/'reports/P3C1_TRANSFORMATION_BOUNDARY.md','变换边界')}：方向、切换、回访、出口、进度、u2与必要行为分别判断。
- {link(E/'reports/P3C1_MECHANISM_PROPOSAL.md','最小机制方案')}：内部判断、既有接口、编译能力边界及未来实验建议。
- {link(E/'results/commitment_matrix.json','机器可读矩阵')}、{link(E/'results/evidence_index.json','事实索引')}、{link(E/'config/comparison_manifest.json','材料哈希')}、{link(E/'results/protection.json','保护核验')}。

本次新增模型调用0、Token0、环境执行0；未修改Prompt/方法/Memory、未重跑A/B、未生成新Original/Effective或Candidate。旧P3-B报告保持原样。本阶段完成后停止，不进入P3-C2。
''')
# Final protection includes all prior phases and formal results; Test bytes only hashed.
spec=importlib.util.spec_from_file_location('protection',ROOT/'experiments/methods/v23_2/v23_2_diagnosis_interface_audit_001/verify_protection.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);v.EXP=E
before=read(E/'config/protected_before.json');after=v.snapshot();changed=sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k))
result={'at':datetime.now(timezone.utc).isoformat(),'protected_files_before':len(before),'protected_files_after':len(after),'changed_outside_new_directory':changed,'unchanged':not changed,'new_model_calls':0,'new_tokens':0,'environment_executions':0,'new_plans_or_candidates':0,'compiled_existing_or_new_plans':False,'report_quote_assertions_passed':len(rows),'request_equality_except_memory':True,'prior_freeze_hashes_verified':True,'raw_parsed_output_identity_verified':True,'command_checks_use_before':True,'test_access':'Hash protection only; no Test contents used for analysis','preexisting_git_changes':'config/git_status_before.txt','scope':'Only this new directory written; sources are references/excerpts, not regenerated outputs'}
save(E/'results/protection.json',result)
links=[]
for p in (E/'reports').glob('*.md'):
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if target.startswith(('http:','https:')):continue
  assert Path(target.split('#')[0]).exists(),(p,target);links.append(target)
result['report_links_checked']=len(links);save(E/'results/protection.json',result)
(E/'results/git_status_after.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))
assert not changed,changed
print(json.dumps(result,ensure_ascii=False,indent=2))
