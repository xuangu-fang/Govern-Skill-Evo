"""Archive exact-B-prompt A attempt without repairing reference spelling."""
from pathlib import Path
from copy import deepcopy
import json,re,hashlib,importlib.util,subprocess
from datetime import datetime,timezone
from src.skill_evolution.v23 import preconditioner as pc
from src.skill_evolution.v23.grouping import references
E=Path(__file__).resolve().parent;P=E.parent;ROOT=P.parents[3];A=E/'runs/A';B=P/'p3b_results/runs/B'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
req=read(A/'request.json');breq=read(B/'request.json');r=read(A/'response.json');o=read(A/'parsed.json');meta=read(A/'run.json');p=json.loads(req['body']['messages'][1]['content']);bp=json.loads(breq['body']['messages'][1]['content'])
assert sha(A/'request.json')==sha(P/'requests/A_UNSENT.json')
assert req['body']['messages'][0]==breq['body']['messages'][0]
x,y=deepcopy(req),deepcopy(breq)
for q in [x,y]:j=json.loads(q['body']['messages'][1]['content']);j.pop('memory');q['body']['messages'][1]['content']=j
assert x==y
assert set(o)=={'decision','reason','adjustments','checks'} and o['decision']=='ready' and o['adjustments']==[] and o['checks'] is None
http=read(A/'http_response.txt');assert r['content']==http['choices'][0]['message']['content']==(A/'raw_output.txt').read_text();assert r['finish_reason']==http['choices'][0]['finish_reason']=='stop'
try:pc.compile_effective_plan(o,p)
except ValueError as exc:assert str(exc)=='reason: unavailable historical reference'
else:raise AssertionError('Unexpected compile success')
assert not (A/'effective_plan.json').exists()
matched=re.findall(r'[A-Za-z0-9_-]+/(?:diff|[PQ]\d+(?::[A-Za-z0-9_]+)?)',o['reason'])
refs={s['step'] for run in p['runs'] for s in run['steps']};assert {'P1:4','P6:20','P8:5'}<=refs
save(E/'results/reference_diagnostic.json',{'first_error':meta['error'],'regex_matches':matched,'current_refs_in_joined_text':['P1:4','P6:20','P8:5'],'current_refs_all_present':True,'root_fields_correct':True,'adjustments_empty':True,'interpretation':'Slash-joined current evidence is lexically recognized as historical paths; not proof of invented historical Memory. No response edits and no bypassed compilation.'})
save(E/'results/usage_verified.json',{'usage':r['usage'],'response_model':r['response_model'],'finish_reason':r['finish_reason'],'source':'raw HTTP and response.json; usage.json null finish_reason is error-handler metadata'})
save(E/'results/execution_receipt.json',{'at':datetime.now(timezone.utc).isoformat(),'new_http_requests':1,'automatic_retries':0,'same_system_as_original_B':True,'only_memory_input_difference':True,'request_sha256':sha(A/'request.json'),'response_sha256':sha(A/'http_response.txt'),'effective_A':None,'cumulative_http_attempts':8,'known_cumulative_tokens':899091,'all_attempts_tokens':None,'initial_timeout_usage_unknown':True,'new_environment_calls':0,'B_not_called':True})
(E/'reports/P3B_DECISION.md').write_text(f'''# 原B Prompt下重新运行A（retry_005）

**本次实际请求与原冻结A相同，与已有B除Memory外完全一致；没有使用补充格式Prompt，也没有新B调用。**

HTTP200、finish_reason=stop。模型返回ready、adjustments=[]、checks=null，意图Keep Original。根字段正确、没有to条目，因此这次没有basis/reason错层问题。

原编译器仍拒绝：`reason: unavailable historical reference`。reason包含`P1:4/P6:20/P8:5`；现有历史引用正则实际匹配为`{matched}`。这三个单独的当前步骤均在实际输入中。可确认是当前引用简写与历史路径识别之间的冲突，不能据此称为编造Memory。

没有修改原reason、替换分隔符或绕过校验；未生成Effective Plan。因而不能把模型的Keep意图写成已合法编译的A。此前新格式A仍是独立有效产物，不覆盖它或旧失败；原同Prompt有效对照仍未补齐。

## 用量与边界

一次HTTP，零自动重试，耗时{meta['elapsed_seconds']:.3f}秒。输入60,011，输出8,424（其中reasoning 8,121），总68,435 Token；缓存字段未提供。累计8次HTTP，已返回usage总899,091 Token，最早超时消耗未知。无可靠货币费用。

所有原始请求、HTTP、response、raw_output、parsed、失败均保存在runs/A。异常分支usage.json的finish_reason=null与原响应stop不同，另存results/usage_verified.json，以原响应为准。

本次只新增retry_005，不修改Prompt、方法、Schema、引用校验、Memory、之前的报告或任何历史运行。不运行Editor、Actor、Replay、Gate或环境。完成归档后停止。

[原始响应]({A/'raw_output.txt'})；[引用诊断]({E/'results/reference_diagnostic.json'})；[执行收据]({E/'results/execution_receipt.json'})；[保护核验]({E/'results/protection.json'})。
''')
spec=importlib.util.spec_from_file_location('protect',ROOT/'experiments/methods/v23_2/v23_2_diagnosis_interface_audit_001/verify_protection.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);v.EXP=E
before=read(E/'config/protected_before.json');after=v.snapshot();changed=sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k))
save(E/'results/protection.json',{'checked_files':len(before),'after_files':len(after),'unchanged':not changed,'changed':changed,'new_http_requests':1,'new_environment_calls':0})
(E/'results/git_status_after.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True));assert not changed,changed
print(json.dumps({'same_prompt_as_B':True,'new_calls':1,'effective_plan':False,'regex_matches':matched,'protected_files':len(before),'protection_unchanged':True},ensure_ascii=False))
