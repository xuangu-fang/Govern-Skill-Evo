"""Archive the single format diagnostic without claiming a controlled Memory A/B."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,importlib.util,subprocess,re
from datetime import datetime,timezone
from src.skill_evolution.v23 import preconditioner as pc
E=Path(__file__).resolve().parent;P=E.parent;ROOT=P.parents[3];A=E/'runs/A';B=P/'p3b_results/runs/B'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def link(p,label):return f'[{label}]({p})'
req=read(A/'request.json');original=read(P/'requests/A_UNSENT.json');breq=read(P/'requests/B_UNSENT.json');payload=json.loads(req['body']['messages'][1]['content'])
r=read(A/'response.json');parsed=read(A/'preconditioner.json');eff=read(A/'effective_plan.json');be=read(B/'effective_plan.json');meta=read(A/'run.json')
assert sha(A/'request.json')==sha(E/'requests/A_UNSENT.json')
x=deepcopy(req);x['body']['messages'][0]=original['body']['messages'][0];assert x==original
assert original['body']['messages'][0]==breq['body']['messages'][0]
assert req['body']['messages'][0]!=breq['body']['messages'][0]
assert parsed['decision']=='ready' and parsed['adjustments']==[] and parsed['checks'] is None
assert pc.compile_effective_plan(parsed,payload)==eff==payload['plan']
assert pc.compile_effective_plan(read(B/'preconditioner.json'),json.loads(read(B/'request.json')['body']['messages'][1]['content']))==be
http=read(A/'http_response.txt');assert http['choices'][0]['message']['content']==r['content']==(A/'raw_output.txt').read_text();assert json.loads(r['content'])==parsed
assert r['finish_reason']==http['choices'][0]['finish_reason']=='stop'
for p,h in read(E/'config/freeze.json')['files_sha256'].items():assert sha(E/p)==h,p
known=[read(B/'response.json')['usage']]+[read(P/f'p3b_A_retry_{i:03d}/runs/A/response.json')['usage'] for i in range(1,5)]+[r['usage']]
tot={k:sum(u[k] for u in known) for k in ['prompt_tokens','completion_tokens','total_tokens']}
checks={'at':datetime.now(timezone.utc).isoformat(),'freeze_unchanged':True,'actual_request_hash_matches':True,'only_system_changed_from_original_A':True,'original_AB_system_identical':True,'new_A_system_differs_from_old_B':True,'original_compiler_accepted':True,'effective_equals_original_plan':True,'nonempty_adjustment_field_generation_tested':False,'B_recompile_equal':True,'new_http_requests':1,'automatic_retries':0,'new_environment_calls':0,'cumulative_http_attempts':7,'known_cumulative_tokens':tot,'initial_timeout_usage':None,'overall_cumulative_tokens':None,'controlled_memory_AB_complete':False}
save(E/'results/execution_receipt.json',checks)
(E/'reports/EXECUTION_REPORT.md').write_text(f'''# A组格式补充后的单次验证

**本次获得合法ready输出并由原编译器生成Effective Plan；模型选择Keep全部Original Updates。**没有非空Adjustment，因此尚未验证生成替代Update时能否稳定遵守字段层级。

## 冻结与调用

- 原A/B system内容逐字一致；仅Memory不同，空Memory不会在程序中移除输出格式要求。
- 本次唯一相对原A的变化是system Output Format新增一段。{link(E/'config/preconditioner_prompt.md','完整Prompt')}、{link(E/'config/prompt.diff','精确Diff')}、{link(E/'config/freeze.json','调用前冻结记录')}、{link(E/'reports/DESIGN.md','设计边界')}。
- 强调basis/reason属于Adjustment外层、to仅含id/text、不复制输入Update的basis、不添加占位字段、外层basis/reason非空；多个当前引用逗号分隔，不写斜杠合并形式。没有修改Schema、编译器或行为策略规则。
- 冻结时间{read(E/'config/freeze.json')['at']}；实际开始{meta['started_at']}，结束{meta['finished_at']}。
- deepseek-v4.1-flash；temperature=1，Thinking enabled，reasoning_effort=medium，stream=false，max_tokens=16384，timeout=300秒；HTTP200，finish_reason=stop，返回模型一致。
- 1次HTTP，自动重试0，耗时{meta['elapsed_seconds']:.3f}秒。没有人工修复或根据结果继续迭代Prompt。

## 结果与消耗

`decision=ready`、`adjustments=[]`、`checks=null`。Effective Plan与冻结Original Plan完全一致，Goal、u1、u2、basis、Checks及顺序未变。

输入60,133、输出4,893（包含reasoning 4,574）、总65,026 Token；API报告缓存输入0。累计7次HTTP，已返回usage合计{tot['total_tokens']:,} Token，首次A超时用量未知，故累计总消耗仍未知。无可靠货币费用，不推算账单。

## 离线验证

实际请求哈希等于本次冻结；去除system变更后与原A完全相同；旧A/B system相同；原编译器重复编译结果一致；B原结果可原样重编译；调用前合法字段fixture通过，非法to.basis fixture被拒绝。fixture是确定性结构测试，不是模型输出。运行后冻结文件未变。

{link(A/'request.json','完整请求')}；{link(A/'http_response.txt','原始HTTP')}；{link(A/'raw_output.txt','模型原文')}；{link(A/'preconditioner.json','合法输出')}；{link(A/'effective_plan.json','Effective Plan')}；{link(A/'usage.json','用量')}；{link(E/'results/execution_receipt.json','核验收据')}。

本次A不是原严格Memory单变量实验的有效补臂：system已变，不能把它与旧B作无混杂因果比较。所有旧失败、旧B和P3-A冻结保持原样，正式默认Prompt未改。
''')
(E/'reports/ASSESSMENT.md').write_text(f'''# 合法A的内容核查与比较边界

## A本身

A完整保留原u1/u2。reason声称：

> the numbered-series/type-switch heuristic makes the coverage requirement implementable with the Actor's two-step history

但最终u1仍要求识别“not yet inspected in this search”、类内编号序列耗尽后再换类。两步近期历史与编号线索不自动提供全局访问/耗尽状态，reason没有证明所有决策点都可恢复该状态。不能因其自称executable就判定能力问题已解决；编号探索本身仍可作为有条件的新策略，而非一概错误。

u2仍保留`do not repeat that action or an equivalent one`和`Instead immediately take a state-changing action`，未明确状态/动作前提改变后的重试与有价值信息获取边界。当前P1:4、P7:11/12、P8:39和P10:25已可支持这一边界审查，不需要历史Memory才能提出。开头允许“reveal new information”，所以也不能夸大为全面禁止信息动作。

Goal保留精确对象、必要处理交付、desklamp等要求；没有新增行为条款，也没有解决原有约束之间的潜在冲突。Checks原样保留，不能视为Actor额外执行的补救指令。

Keep本身合法，并非必须Adjustment；本次具体可执行性论证仍不足。没有Editor或Replay，不判断实际Skill行为好坏。

## 与旧B仅作描述性对照

| 项目 | 新格式A | 原Prompt B |
|---|---|---|
| Prompt | 原Prompt加字段/引用格式说明 | 原冻结Prompt |
| Memory | 空 | M1/M2/M3/M6/M7/M8/M9及sources |
| u1 | 保留类内编号穷尽及之后换类 | 改为跨类型采样/近期去重；附带其他类型采样后才回同类，以及types或locations一次结束 |
| u2 | Keep | Keep |
| Goal/Checks | 保持Original | 保持Original |

B的变换与历史M6/M3的混合响应有显式联系，但only-after和类别/位置一次终止仍有支持不足。新A不调整、旧B调整是实际文本差异；由于Prompt与Memory同时不同，**不能将差异归因于Memory**。原{link(P/'p3b_results/reports/P3B_MEMORY_ATTRIBUTION.md','B历史依据核查')}保持为独立分析。

## 为什么原B成功、原A连续失败？

已确认原A/B的system、模型、参数相同；原请求未启用服务端结构化Schema约束，依赖自然语言格式要求与事后校验。A的四次完整输出均把basis/reason放进to条目，说明重复的字段映射问题；输入Original Update含basis而replacement不含basis，是可能的混淆来源。B单次成功只能说明相同契约可以被遵守，不能证明Memory保证结构正确。

上下文内容/长度、采样随机性、调用时点可能影响输出；本实验没有隔离这些因素，不能指定唯一内部原因。首次A超时不是格式失败。第四次A首先还遇到斜杠当前引用被历史正则识别的问题，但其字段层级与空外层依据独立不合法。

本次成功走的是空adjustments分支，没有生成to对象。因此它既不证明格式补充导致成功，也不证明原字段错位问题已可靠解决；更不能将格式通过误称为策略构造或Memory机制通过。
''')
texts=['# Original / 新格式A / 原B 完整产物对照','本表仅保存全文；两份有效输出Prompt不同，不是Memory单变量对照。']
for label,obj in [('Original Plan',payload['plan']),('新格式A Preconditioner',parsed),('新格式A Effective Plan',eff),('原B Preconditioner',read(B/'preconditioner.json')),('原B Effective Plan',be)]:texts+=['## '+label,'```json\n'+json.dumps(obj,ensure_ascii=False,indent=2)+'\n```']
(E/'reports/OUTPUTS.md').write_text('\n\n'.join(texts)+'\n')
(E/'reports/DECISION.md').write_text(f'''# 最终结论

本次补充格式Prompt后，A一次请求合法返回ready、adjustments=[]，原编译器生成Effective Plan，全部保留原u1/u2。没有人工修补。耗时43.584秒，65,026 Token。

原A/B Prompt完全相同；新A与旧B不同。B一次成功不能证明Memory提高格式遵循能力；连续A错位是已观察现象，其内部原因尚不能唯一确定。

本次未生成非空to，故不能宣布替代Update字段问题已经修复。当前u1全局进度前提与u2状态相关的重复边界仍未改善。

不能把新A Keep、旧B Adjust当作Memory增量证据。原严格A/B对照仍未完成；如后续要采用新格式Prompt，应将其作为新的共同条件冻结并对称验证，本次不自动调用B。

{link(E/'reports/EXECUTION_REPORT.md','执行/冻结/用量')}；{link(E/'reports/ASSESSMENT.md','独立核查与原因边界')}；{link(E/'reports/OUTPUTS.md','全文对照')}；{link(E/'results/protection.json','历史保护')}。

仅新增独立p3b_A_format_001，未改正式默认配置、Prompt或Schema，未运行其他模块/环境。旧retry_004在本次请求前补齐归档；所有先前原始响应保留。完成后停止。
''')
spec=importlib.util.spec_from_file_location('protect',ROOT/'experiments/methods/v23_2/v23_2_diagnosis_interface_audit_001/verify_protection.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);v.EXP=E
before=read(E/'config/protected_before.json');after=v.snapshot();changed=sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k));save(E/'results/protection.json',{'checked_files':len(before),'after_files':len(after),'unchanged':not changed,'changed':changed,'excluded':[str(E),'__pycache__','.pytest_cache'],'new_http_requests':1,'new_environment_calls':0})
(E/'results/git_status_after.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))
links=[]
for f in (E/'reports').glob('*.md'):
 for t in re.findall(r'\]\(([^)]+)\)',f.read_text()):assert Path(t).exists(),t;links.append(t)
save(E/'results/offline_checks.json',{**checks,'report_links_checked':len(links),'historical_protection_passed':not changed})
print(json.dumps({'valid':True,'decision':parsed['decision'],'adjustments':len(parsed['adjustments']),'protection_unchanged':not changed,'checked_files':len(before),'changed':changed,'known_tokens':tot['total_tokens']}))
