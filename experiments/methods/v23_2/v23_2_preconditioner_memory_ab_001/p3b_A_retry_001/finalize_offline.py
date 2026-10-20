"""Offline receipt/report generation only. Never repairs or sends model output."""
from pathlib import Path
import hashlib,json,importlib.util,subprocess,re
from datetime import datetime,timezone
from src.skill_evolution.v23 import preconditioner as pc
E=Path(__file__).resolve().parent;P=E.parent;ROOT=P.parents[3];O=P/'p3b_results';A=E/'runs/A';B=O/'runs/B'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def link(p,label):return f'[{label}]({p})'
r=read(A/'response.json');http=read(A/'http_response.txt');parsed=read(A/'parsed.json');req=read(A/'request.json');payload=json.loads(req['body']['messages'][1]['content'])
assert req==read(P/'requests/A_UNSENT.json') and sha(A/'request.json')==sha(P/'requests/A_UNSENT.json')
assert http['choices'][0]['finish_reason']==r['finish_reason']=='stop'
assert http['usage']==r['usage']
try:pc.compile_effective_plan(parsed,payload)
except ValueError as exc:assert str(exc)=='Adjustment: unexpected fields'
else:raise AssertionError('Unexpected valid output')
assert not (A/'effective_plan.json').exists()
br=read(B/'preconditioner.json');bp=json.loads(read(B/'request.json')['body']['messages'][1]['content']);be=read(B/'effective_plan.json')
assert pc.compile_effective_plan(br,bp)==be
adj=parsed['adjustments'][0]
shape={'adjustment_required':['from','to','basis','reason'],'actual':list(adj),'missing':sorted({'from','to','basis','reason'}-set(adj)),'unexpected':sorted(set(adj)-{'from','to','basis','reason'}),'replacement_required':['id','text'],'replacement_actual':list(adj['to'][0]),'replacement_unexpected':sorted(set(adj['to'][0])-{'id','text'})}
save(E/'results/schema_diagnostic.json',shape)
usage={'usage':r['usage'],'response_model':r['response_model'],'finish_reason':r['finish_reason'],'http_status':read(A/'http_status.json')['status_code'],'cached_tokens':None,'source':'response.json and original http_response.txt; both agree','note':'run_once.py error handler wrote null finish_reason in usage.json after schema failure. That metadata is retained; authoritative raw HTTP and response.json both say stop. No model output repaired.'}
save(E/'results/usage_verified.json',usage)
tot={k:r['usage'][k]+read(B/'usage.json')['usage'][k] for k in ['prompt_tokens','completion_tokens','total_tokens']}
receipt={'at':datetime.now(timezone.utc).isoformat(),'new_http_requests':1,'automatic_retries':0,'cumulative_http_requests':3,'actual_order':['A initial timeout','B valid','A authorized retry: schema failure'],'A_retry_status':'HTTP 200; stop; JSON parsed; schema rejected; no Effective Plan','B_reused':str(B),'valid_AB_comparison':False,'request_hash_equal':True,'request_sha256':sha(A/'request.json'),'raw_response_sha256':sha(A/'http_response.txt'),'B_effective_sha256':sha(B/'effective_plan.json'),'known_cumulative_tokens':tot,'initial_A_tokens':None,'all_attempts_total_tokens':None,'money_cost':None,'new_environment_calls':0,'new_other_module_calls':0,'semantic_resampling':False,'output_repair':False}
save(E/'results/execution_receipt.json',receipt)
(E/'reports/P3B_EXECUTION_REPORT.md').write_text(f'''# A组授权重试执行记录

**重试已执行一次，但A仍没有合法Effective Plan。本次是Schema失败，不是再次超时或输出截断。**

- 请求完全复用P3-A A组；SHA-256 `{sha(A/'request.json')}`。冻结清单、来源哈希、两组仅Memory不同、R05七条Active Memory已通过原preflight核对。
- 模型deepseek-v4.1-flash；temperature=1，Thinking enabled，reasoning_effort=medium，stream=false，max_tokens=16384；连接10秒/读取300秒。没有参数变化或容量探测。
- HTTP 200，response_model=deepseek-v4.1-flash，finish_reason=stop。耗时{read(A/'run.json')['elapsed_seconds']:.3f}秒；一次HTTP，自动重试0。JSON解析成功，原编译器拒绝：`Adjustment: unexpected fields`。
- Adjustment必须含from/to/basis/reason；实际在Adjustment层缺basis/reason，却新增basis_note/reason_placeholder；basis/reason错放在to[0]，而to条目只允许id/text。
- 未移动字段、未删除非法字段、未人工编译“修正版”，没有effective_plan.json。不是合法no_change/need_evidence，也不是合法Keep。

## 用量

| 尝试 | 状态 | 输入Token | 输出Token | 其中reasoning | 总Token | 秒 |
|---|---|---:|---:|---:|---:|---:|
| 原A | ReadTimeout | 未知 | 未知 | 未知 | 未知 | 300.341 |
| 原B（复用） | 合法ready | 474757 | 5270 | 4751 | 480027 | 57.498 |
| 本次A | Schema拒绝 | 60011 | 10345 | 9629 | 70356 | 55.793 |

本次新增70,356 Token。已返回usage的两次合计550,383 Token（输入534,768；输出15,615），**包含原A超时的实验累计总量仍未知**。reasoning包含在输出中，不重复累计；缓存用量和货币费用未提供，不推算。

原包装器异常分支将usage.json的finish_reason写为null，原始HTTP和response.json均保存stop。本次不覆盖该文件，另存{link(E/'results/usage_verified.json','核验后的用量与来源')}，以原响应为准。

实际顺序为A超时→B合法→A授权重试，不能描述成有效A先于B；若以后取得有效对照，也需保留顺序、时点、随机性和输入长度差异的归因边界。

## 原始产物

{link(A/'request.json','实际完整请求')}；{link(A/'http_response.txt','原始HTTP响应')}；{link(A/'raw_output.txt','输出原文')}；{link(A/'parsed.json','解析JSON（无效契约）')}；{link(A/'error.json','错误')}；{link(E/'results/schema_diagnostic.json','字段差异')}；{link(E/'results/execution_receipt.json','执行收据')}。

B原始结果仍引用{link(B/'effective_plan.json','原B Effective Plan')}，未重跑。无Diagnosis、Editor、Actor、Memory、Replay、Gate或环境调用。
''')
(E/'reports/P3B_UPDATE_COMPARISON.md').write_text(f'''# 补充后的比较可用性

**A重试取得文本，但契约失败，不能将其to.text当作Effective Update。正式A/B对照仍未完成。**

| 对象 | A授权重试 | B原有合法结果 |
|---|---|---|
| reason | 声称当前P6长drawer搜索耗预算、P3扩展到其他位置后成功，拟调整u1 | 引用当前执行及M6/M3历史混合反馈，调整u1 |
| u1有效结果 | 无：非法Adjustment未进入原编译器 | breadth-first跨类型采样、近期去重，并增加only-after及types/locations一次结束要求 |
| u2有效结果 | 无；原文声称保持，不能当已编译Keep | 保持Original |
| Goal/Checks | 无有效编译产物 | 均保持Original |

## A原始文本的诊断性记录（不纳入有效对照）

A原文提出：

> after a short bounded run of that series, switch to a different receptacle type

以及：

> then continue the series only if other types have been covered

它仍使用`not yet inspected this search`等全局进度条件；short bounded run没有规定具体2/3次。原文声称u2保留，未给状态改变后重试的明确修正。这些只用于记录非法响应的内容，不能声称已构造合法策略，也不能把reason中的轨迹概括直接当成核验事实。

本次无Memory原文也提到跨类型探索，因此“提到跨类型探索”本身尤其不能作为Memory使用的充分判据。但这不是有效A/B策略对照，更不能用它估计Memory增量。

## B的独立评价保持不变

B的跨类型探索有问题动机，局部recent-history去重可由当前证据支持；但`Return ... only after other ... sampled`和`all plausible candidate types or locations ... once`仍有依据不足、全局进度与潜在过早停止风险。u2没有明确状态变化后重试边界。没有Actor执行，不能说风险已经导致失败。

完整Original/B文本和既有独立核查见{link(O/'reports/P3B_UPDATE_COMPARISON.md','原始对照报告')}。A原文完整保留于{link(A/'raw_output.txt','本次无效响应')}。既有报告反映首次运行时状态，未被重写。
''')
(E/'reports/P3B_MEMORY_ATTRIBUTION.md').write_text(f'''# A重试后的Memory归因边界

**仍无法回答加入Memory是否产生不同且更有依据的Effective Update：A没有合法Effective Plan。**

1. 当前P3/P6/P8/P10的覆盖与循环、Actor两组历史能力、P1/P7/P8/P10的无信息动作，已足以提出部分纠正；不能仅因B引用Memory就归功于历史。
2. B的M6/M3引用确实与u1方向改变一起出现。M6的S1_R03/diff反循环与扩展搜索联合编辑，对应Q4 diningtable成功、Q2漏countertop3、Q6过晚获取，支持混合响应认识，不证明唯一调度。
3. B新增其他类型采样后才回同类、types或locations一次的终止要求，并没有由上述编辑—响应链充分支持。M8对no-substitute的支持与Original/当前证据重叠。
4. 本次A原文也选择跨类，但未通过契约；不能人工摘出其策略文本组成“有效A”，也不能据此宣称B无增量或已有合理增量。
5. 既有{link(O/'reports/P3B_MEMORY_ATTRIBUTION.md','历史Diff与轨迹归因')}仍适用；本次仅改变“无响应”为“收到无效契约响应”，没有补齐有效参照。

结论不是Memory无用，也不是Memory有效，而是该对照的有效输出条件仍不满足。原A超时属于传输失败，本次A属于输出契约失败，不能将二者计作策略语义失败。任何后续重试需要另行决定，本次不再请求、不修输出、不改Prompt。
''')
(E/'reports/P3B_DECISION.md').write_text(f'''# A组授权重试：最终决定

**A补齐未成功：HTTP正常、输出未截断，但Adjustment字段结构不合法；原编译器拒绝，没有Effective Plan。**

- A本次实际想调整u1、保留u2，但只是无效响应中的意图，不能报告合法Keep/Adjustment。
- B继续复用原ready：u1改为跨类型采样，u2保持。其新增续行/结束要求的风险判断不变。
- 无法完成有效A/B更新差异比较，不能判断Memory是否产生更有依据的增量。
- 本次新增1次HTTP，0自动重试，55.793秒，70,356 Token。全实验累计3次HTTP；已知usage合计550,383 Token，首次A超时消耗仍未知。
- 本次只新增p3b_A_retry_001；原A失败、原B结果及全部旧报告保留。没有人工调整JSON，没有再次调用，也没有进入Editor/Replay。
- 下一步首先仍是解决有效A输出缺失，不能据现有材料优先开展行为Replay或宣布机制结论。本次不自行执行任何后续实验。

{link(E/'reports/P3B_EXECUTION_REPORT.md','执行与用量')}；{link(E/'reports/P3B_UPDATE_COMPARISON.md','比较边界')}；{link(E/'reports/P3B_MEMORY_ATTRIBUTION.md','归因判断')}；{link(E/'results/protection.json','文件保护核验')}。
''')
spec=importlib.util.spec_from_file_location('protection',ROOT/'experiments/methods/v23_2/v23_2_diagnosis_interface_audit_001/verify_protection.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);v.EXP=E
before=read(E/'config/protected_before.json');after=v.snapshot();changed=sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k))
save(E/'results/protection.json',{'at':datetime.now(timezone.utc).isoformat(),'checked_files':len(before),'after_files':len(after),'unchanged':not changed,'changed':changed,'excludes':[str(E),'__pycache__','.pytest_cache'],'new_http_requests':1,'new_environment_calls':0})
(E/'results/git_status_after.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))
links=[]
for f in (E/'reports').glob('*.md'):
 for t in re.findall(r'\]\(([^)]+)\)',f.read_text()):
  p=Path(t);assert p.exists(),t;links.append(t)
save(E/'results/offline_checks.json',{'freeze_preflight':True,'exact_A_request':True,'raw_finish_reason_stop':True,'schema_rejection_reproduced':True,'no_A_effective':True,'original_B_recompile_equal':True,'report_links_checked':len(links),'no_output_repair':True})
print(json.dumps({'protection_unchanged':not changed,'checked_files':len(before),'changed':changed,'report_links':len(links),'new_calls':1},ensure_ascii=False))
