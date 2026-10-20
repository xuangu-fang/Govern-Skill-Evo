"""Read-only validation and failure archive; no network or output repair."""
from pathlib import Path
import json,hashlib,importlib.util,subprocess,re
from datetime import datetime,timezone
from src.skill_evolution.v23 import preconditioner as pc
E=Path(__file__).resolve().parent;P=E.parent;ROOT=P.parents[3];A=E/'runs/A';B=P/'p3b_results/runs/B'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def link(p,s):return f'[{s}]({p})'
r=read(A/'response.json');http=read(A/'http_response.txt');out=read(A/'parsed.json');req=read(A/'request.json');payload=json.loads(req['body']['messages'][1]['content'])
assert sha(A/'request.json')==sha(P/'requests/A_UNSENT.json')
assert read(A/'http_status.json')['status_code']==200
assert r['finish_reason']==http['choices'][0]['finish_reason']=='stop'
assert r['usage']==http['usage']
assert set(out['adjustments'][0])=={'from','to','basis','reason'}
assert set(out['adjustments'][0]['to'][0])=={'id','text','basis','reason'}
try:pc.compile_effective_plan(out,payload)
except ValueError as exc:assert str(exc)=='Replacement Update: unexpected fields'
else:raise AssertionError('Unexpected valid output')
assert not (A/'effective_plan.json').exists()
assert pc.compile_effective_plan(read(B/'preconditioner.json'),json.loads(read(B/'request.json')['body']['messages'][1]['content']))==read(B/'effective_plan.json')
usage={**r['usage']};save(E/'results/usage_verified.json',{'usage':usage,'finish_reason':r['finish_reason'],'response_model':r['response_model'],'source':['runs/A/http_response.txt','runs/A/response.json'],'note':'Original runner error handler recorded null finish_reason in usage.json. Raw HTTP and response.json agree on stop. Original files preserved; this is metadata reconciliation, not output repair.'})
save(E/'results/schema_diagnostic.json',{'error':'Replacement Update: unexpected fields','json_path':'$.adjustments[0].to[0]','allowed_fields':['id','text'],'actual_fields':list(out['adjustments'][0]['to'][0]),'unexpected_fields':['basis','reason'],'adjustment_outer_fields_valid':True,'output_repaired':False,'effective_plan_exists':False})
prior=read(P/'p3b_A_retry_001/runs/A/response.json')['usage'];bu=read(B/'usage.json')['usage'];tot={k:sum(x[k] for x in [usage,prior,bu]) for k in ['prompt_tokens','completion_tokens','total_tokens']}
save(E/'results/execution_receipt.json',{'at':datetime.now(timezone.utc).isoformat(),'new_http_requests':1,'automatic_retries':0,'cumulative_http_requests':4,'actual_order':['A initial timeout','B valid','A retry_001 schema failure','A retry_002 replacement schema failure'],'A_valid':False,'AB_effective_comparison_complete':False,'B_reused_without_call':True,'request_sha256':sha(A/'request.json'),'response_sha256':sha(A/'http_response.txt'),'known_cumulative_tokens':tot,'initial_A_usage':None,'overall_cumulative_tokens':None,'new_environment_calls':0,'other_module_calls':0,'output_repair':False})
(E/'reports/P3B_EXECUTION_REPORT.md').write_text(f'''# A组第二次授权重试

**已发送一次；取得完整响应，但原Schema拒绝，未补齐A Effective Plan。**

本次请求SHA-256 `{sha(A/'request.json')}`，与P3-A逐字节一致。原preflight再次核验冻结清单、来源、B真实Active Memory，以及两组只有Memory差异；B未重跑。

模型deepseek-v4.1-flash；temperature=1，Thinking enabled，reasoning_effort=medium，stream=false，max_tokens=16384，连接10秒、读取300秒。参数和Prompt未变。HTTP200，finish_reason=stop，返回模型deepseek-v4.1-flash，耗时60.692秒。

## 具体失败

原编译器在`$.adjustments[0].to[0]`拒绝：`Replacement Update: unexpected fields`。该条目应只有id/text，实际另含basis/reason。本次Adjustment外层from/to/basis/reason已齐全；与上次同时存在外层非法字段不同。未删除字段、未移动字段、未生成手工修复的Effective Plan。

## 实际用量

| 尝试 | 结果 | 输入 | 输出 | reasoning（含在输出中） | 总Token | 秒 |
|---|---|---:|---:|---:|---:|---:|
| 初始A | ReadTimeout | 未知 | 未知 | 未知 | 未知 | 300.341 |
| 原B | 合法ready | 474757 | 5270 | 4751 | 480027 | 57.498 |
| A retry_001 | Adjustment字段失败 | 60011 | 10345 | 9629 | 70356 | 55.793 |
| A retry_002（本次） | Replacement字段失败 | 60011 | 11268 | 10409 | 71279 | 60.692 |

本次缓存命中输入59,392 Token，属于60,011输入的子集，不另行累计。其他尝试未提供缓存字段，不视为零。已返回usage合计621,662 Token（输入594,779、输出26,883）；初始A超时用量未知，所以实验总消耗仍未知。不推算货币费用。

异常处理器保存的usage.json把finish_reason记为null，原HTTP和response.json实际均为stop；保留原文件，以{link(E/'results/usage_verified.json','核验用量')}注明来源。未更改模型响应。

{link(A/'request.json','实际请求')}；{link(A/'http_response.txt','原始HTTP响应')}；{link(A/'raw_output.txt','原始输出')}；{link(A/'parsed.json','解析但契约无效的JSON')}；{link(E/'results/schema_diagnostic.json','字段诊断')}；{link(E/'results/execution_receipt.json','执行收据')}。

本次新增一次HTTP，零自动重试；累计四次HTTP。真实顺序为A超时→B合法→A两次经授权技术重试，所有尝试均保留。没有对合法输出择优或语义重采样。
''')
(E/'reports/P3B_UPDATE_COMPARISON.md').write_text(f'''# A原始文本与有效对照边界

**A仍无合法Effective Plan，不能完成预注册的Effective A/B对照。**

本次A原文表示保留u2、调整u1，拟保留类内单向扫描并加入提前换类的预算条件：

> switch ... once that series is exhausted, or earlier when continuing the same type would risk spending the remaining step budget on a single receptacle type

同时要求：

> do not re-enter an exhausted series

它把部分去重依据收窄为当前观察和最近两组历史，但仍使用exhausted series；预算风险判断尚无明确的估计依据。关于u2可执行的reason不能替代对状态变化后重试边界的核查。以上只描述{link(A/'raw_output.txt','无效原文')}，不构成合法更新，也不据此声称实际行为优劣。

B原有合法Effective仍为跨类型采样、近期去重，u2保持，Goal/Checks保持。其他类型采样后才回同类、types或locations检查一次即可结束的附带要求，仍缺充分支持并残留全局进度依赖。原有{link(P/'p3b_results/reports/P3B_UPDATE_COMPARISON.md','Original/B全文及独立评价')}未修改。

A非法输出不能通过人工去掉basis/reason来补齐对照；也不能将其原文与B的有效输出混用，然后宣称Memory产生合理增量或没有增量。
''')
(E/'reports/P3B_MEMORY_ATTRIBUTION.md').write_text(f'''# 第二次A重试后的历史增量判断

**仍未具备有效A参照；历史编辑—行为响应的额外更新作用尚未完成检验。**

- 当前执行与Actor能力说明本来就能支持质疑全局进度、减少无信息重复、重新考虑长同类搜索。这些不自动属于Memory独有增量。
- B明确引用M6/M3的旧扩展搜索与反循环指导未稳定兑现，并实际改变u1；M8支持精确目标。但其only-after及types/locations一次结束要求仍有依据不足。
- 本次A原文提出预算条件及局部去重，但契约失败；不能当作合法A，不以它估算B相对A的收益。
- 原有{link(P/'p3b_results/reports/P3B_MEMORY_ATTRIBUTION.md','M6/M3/M8的Diff—轨迹证据分析')}继续作为B独立评价，不能升级为已经完成的A/B因果归因。

本次失败属于输出契约失败，不是证据显示某一搜索策略效果差，也不是证明Memory无用。即使后续补齐，单次有效对照仍不能排除随机性、不同输入长度/缓存、时点和技术重试筛选的影响，更不证明Skill行为收益。
''')
(E/'reports/P3B_DECISION.md').write_text(f'''# 最终结论：第二次授权重试仍未补齐A

本次A收到HTTP200、finish_reason=stop的完整响应，但`to[0]`多出basis/reason；原编译器报`Replacement Update: unexpected fields`。没有合法Effective Plan，没有人工修补。

B没有重跑，原合法结果保持。A/B有效更新对照仍未完成，不能回答加入Memory是否产生不同且更有依据的Effective Update。A原文的策略意图只作失败诊断，不替代有效编译结果。

本次新增1次请求、71,279 Token、60.692秒，自动重试0。原A超时及上次字段错误均保留；累计4次HTTP。已知usage累计621,662 Token，初始超时用量仍未知。

只新增p3b_A_retry_002运行包装器、原始产物、核验及报告。没有修改方法/Prompt/Schema，没有Editor、Actor、Replay、Memory或环境执行。完成归档后停止，不再自动请求。

{link(E/'reports/P3B_EXECUTION_REPORT.md','执行报告')}；{link(E/'reports/P3B_UPDATE_COMPARISON.md','更新比较边界')}；{link(E/'reports/P3B_MEMORY_ATTRIBUTION.md','归因结论')}；{link(E/'results/protection.json','历史保护核验')}。
''')
spec=importlib.util.spec_from_file_location('protection',ROOT/'experiments/methods/v23_2/v23_2_diagnosis_interface_audit_001/verify_protection.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);v.EXP=E
before=read(E/'config/protected_before.json');after=v.snapshot();changed=sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k))
save(E/'results/protection.json',{'checked_files':len(before),'after_files':len(after),'unchanged':not changed,'changed':changed,'excluded':[str(E),'__pycache__','.pytest_cache'],'new_http_requests':1,'environment_calls':0})
(E/'results/git_status_after.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))
links=[]
for f in (E/'reports').glob('*.md'):
 for t in re.findall(r'\]\(([^)]+)\)',f.read_text()):assert Path(t).exists(),t;links.append(t)
save(E/'results/offline_checks.json',{'request_hash_equal':True,'HTTP_200_finish_stop':True,'schema_failure_reproduced':True,'no_A_effective':True,'B_recompile_equal':True,'report_links_checked':len(links)})
print(json.dumps({'protection_unchanged':not changed,'checked_files':len(before),'changed':changed,'links':len(links)}))
