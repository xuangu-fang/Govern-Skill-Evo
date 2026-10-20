"""Archive offline prototype results and verify historical protection; no model APIs."""
from pathlib import Path
import hashlib,json,importlib.util,subprocess,re
from datetime import datetime,timezone
E=Path(__file__).resolve().parent;ROOT=E.parents[3];P=E.parent/'v23_2_preconditioner_memory_ab_001'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def l(p,s):return f'[{s}]({p})'
t=read(E/'results/tests.json');assert t['exit_code']==0 and not t['network_attempts'];assert all(c['outcome']=='passed' for c in t['cases'])
f=read(E/'config/source_manifest.json')
for p,h in f['source_files'].items():assert sha(ROOT/p)==h,p
assert sha(E/'reports/P3C2_ALGORITHM_DESIGN.md')==f['design_before_implementation_sha256']
req=read(P/'p3b_B_format_001/runs/B/request.json');payload=json.loads(req['body']['messages'][1]['content']);assert read(E/'fixtures/payload.json')==payload
matrix=read(E.parent/'v23_2_preconditioner_commitment_analysis_001/results/commitment_matrix.json');assert len(matrix['rows'])==22
# Validate prior successful pair without regenerating a historical result.
from copy import deepcopy
reqA=read(P/'p3b_A_format_001/runs/A/request.json');a,b=deepcopy(reqA),deepcopy(req)
for q in (a,b):
 d=json.loads(q['body']['messages'][1]['content']);d.pop('memory');q['body']['messages'][1]['content']=d
assert a==b
index={str(p.relative_to(ROOT)):sha(p) for p in [*(E.parent/'v23_2_preconditioner_commitment_analysis_001/reports').glob('*.md'),P/'config/original_plan.json',P/'config/memory_B.json',P/'reports/P3A_EVALUATION_PROTOCOL.md',P/'p3b_A_format_001/runs/A/preconditioner.json',P/'p3b_B_format_001/runs/B/preconditioner.json',P/'p3b_A_format_001/runs/A/effective_plan.json',P/'p3b_B_format_001/runs/B/effective_plan.json']}
save(E/'config/evidence_references.json',index)
(E/'config/INTERNAL_CONTRACT.md').write_text('''# 实验内部编辑契约

本格式仅为实验中间表示，不修改正式Preconditioner/Editor/Memory契约。

顶层：plan_sha256, decision, reason, edits, checks。edit：update_id, operation, anchor_text, replacement_text, role, basis, reason, depends_on。全部字段必须存在且无额外字段。

operation=replace/delete/insert_before/insert_after；role=target/supporting/independent。supporting的depends_on为非空0起始下标，只指向target/independent；其余空。delete的replacement_text为空，其他非空。anchor非空、精确唯一、只在原快照匹配。重复、冲突、过期均拒绝。未选字节保持。原编译器验证最终Adjustment/Checks。

ready空edits是Keep；need_evidence空edits且checks=null；no_change显式整段delete所有Updates且checks=[]。完整delete可撤回，部分撤回须显式修正Checks。拆合/新ID/新Update不支持。

见reports/P3C2_ALGORITHM_DESIGN.md的完整哈希、冲突规则及语义限制。实现为anchored.py；未来草案为anchored_prompt_draft.md；人工夹具不能作为模型答案。
''')
(E/'reports/P3C2_IMPLEMENTATION_REPORT.md').write_text(f'''# P3-C2-B 实现报告

**完成的是独立确定性原型，不是已验证的新预条件化算法。** 全部文件位于本目录；正式源码、Prompt、默认配置和P0—P3-C1不变。没有联网生成、Editor阶段、Actor或Replay。

## 1. 实际实现

| 文件 | 功能 |
|---|---|
| {l(E/'anchored.py','anchored.py')} | 精确契约/哈希/引用/依赖/锚点校验；UTF-8区间应用；原Adjustment转换；原compiler；audit/Diff；离线CLI拒绝时仅写receipt |
| {l(E/'prepare_fixtures.py','prepare_fixtures.py')}及fixtures | 构造HUMAN测试方案；payload是保存B请求的用户输入逐字段副本；不造新真实结果 |
| {l(E/'tests/test_anchored.py','test_anchored.py')} | 52项原型测试，包括真实R05文本、Unicode/CRLF、非法操作、停点和语义风险 |
| {l(E/'run_tests.py','run_tests.py')} | 禁止socket连接后执行原型与77项既有相关测试；记录每项结果；旧阶段调用均本地mock |
| {l(E/'run_human_demos.py','run_human_demos.py')} | 7份人工演示（6次结构编译/停点、1次预期拒绝），仅本目录归档 |
| {l(E/'config/anchored_prompt_draft.md','未来Prompt草案')} | 以B_format为上下文，改为一次生成锚定方案；保留既有证据/Actor约束；不含22项人工分析答案 |
| {l(E/'config/prompt_vs_B_format.diff','草案Diff')} | 所有改动可审阅；没有接入默认路由，没有发送 |

## 2. 完整文本如何得到

真实R05 u1人工单项测试选择Original字节`[523,610)`，替换为人工局部片段。程序复制`[0,523)`，写replacement，再复制`[610,1072)`，形成1087字节的新u1；后段对应新`[625,1087)`。u2的514字节全部保持，Goal/Checks保持。详见{l(E/'results/human_runs/single_replace/audit.json','字节映射')}与{l(E/'results/human_runs/single_replace/changes.diff','实际Diff')}。

这份text没有来自第二次模型生成或另一份完整替代字段。每个受影响Update只汇总为一条from/to，引用并集与编辑解释在外层；一对一允许保留原ID。通过原`compile_effective_plan`，并在真实归档saved输入上通过`editor.editor_input`纯函数；没有执行Editor生成。

两段目标/配套夹具用depends_on明确联系。应用按原位置，而非提交顺序；后项不会匹配新生成文本。插入/删除不会自动补空格。未指定片段逐UTF-8字节核验；展示Diff不是新的patch应用输入，字节映射是精确保留依据。

## 3. 支持的决定及操作

replace/delete/insert_before/insert_after、多个Update多个非冲突编辑、ready Keep、need_evidence停点、整段delete撤回及全部撤回no_change均已测试。部分撤回不自动删Checks；引用失效直接拒绝。非法goal、额外字段、过期hash、重复锚点（含重叠出现）、模糊/不存在锚点、冲突插入/编辑、未知依据和ID均失败关闭，无自由生成回退。

大范围乃至全文replace可行，无长度阈值。全文被选择时原文保护区为空，此时不能声称细粒度保留；模型可通过过宽选择减弱机制优势，未来必须评价。

## 4. 已知限制

- 不支持正式契约已有的merge/split/新ID/全新Update；需此能力的案例应阻断或按未来预注册范围处理，不能假称缺证据。多Update关联编辑仍支持。
- supporting只能依赖target/independent根编辑；不支持递归依赖图。同锚前后两个插入、插入触碰其他锚等保守拒绝，需明确重述方案，不猜执行顺序。
- 编译器不能判basis对某句话的支持强度；role不能证明配套必要；局部replacement可引入多项新承诺，局部编辑之间可能冲突。
- 未改文本也可能有旧问题；保持它只证明无附带重写，不代表策略正确。语义风险夹具结构通过，不计作算法语义失败或成功。
- 哈希绑定完整Plan修订，非身份鉴权；未来执行端还需核对冻结输入/Prompt/模型参数。当前CLI纯离线，无API发送入口或自动重试。
- 新Prompt是草案，尚无遵循率、Token容量或策略质量验证。固定R05已有设计暴露，不能作为未接触泛化样本。

## 5. 运行方式与隔离

在仓库根目录执行（out必须为不存在的新目录）：

```sh
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python experiments/methods/v23_2/v23_2_commitment_anchored_001/anchored.py --payload experiments/methods/v23_2/v23_2_commitment_anchored_001/fixtures/payload.json --proposal experiments/methods/v23_2/v23_2_commitment_anchored_001/fixtures/single_replace.json --out experiments/methods/v23_2/v23_2_commitment_anchored_001/results/manual_new_run
```

仅为人工夹具执行，不应作为真实Preconditioner响应发布。错误receipt保留原文件引用/哈希和错误原因，未输出部分Effective。历史保护见{l(E/'results/protection.json','核验记录')}。
''')
case_lines=['# 全部离线测试结果','', '| 测试 | 状态 | 秒 |','|---|---|---:|']
for c in t['cases']:case_lines.append(f"| `{c['id']}` | {c['outcome']} | {c['seconds']:.4f} |")
(E/'results/TEST_CASES.md').write_text('\n'.join(case_lines)+'\n')
(E/'reports/P3C2_TEST_REPORT.md').write_text(f'''# P3-C2 离线测试报告

**最终129项通过，0项失败；其中52项原型、74项原Preconditioner、3项原Editor纯交接。** socket.connect/connect_ex/create_connection均封锁，网络尝试0；新增模型调用/Token/环境执行均0。输入和策略文本由人工测试夹具提供，不是模型验证。

{l(E/'results/pytest.log','最终日志')}；{l(E/'results/TEST_CASES.md','129项逐项清单')}；{l(E/'results/tests.json','机器结果')}。本次仅重复运行因断言修正或新增覆盖需要的测试，没有扩大到环境或全Campaign。

## 1. 七类验收

| 要求 | 测试和实际结果 |
|---|---|
| 单项定向替换 | R05真实u1一个调度条件被替换，其余两段原文逐字节保持；没有程序自动新增sampled once；正式Adjustment字段正确 |
| 目标与配套 | 两个不相连原锚点，supporting明确依赖target；按原位置合成，索引不当作应用顺序；依赖错误/循环拒绝 |
| 跨Update/下游 | 单改u1时u2/Goal/Checks完全不变；真实归档的Editor纯输入函数接受；多Update显式编辑可同时表达 |
| 大范围编辑 | 人工全文替换且结果更长仍接受；audit明确未选保护区为零；不以修改大小评分 |
| 非法方案 | 不存在/重复/重叠锚、边界插入冲突、未知Update、过期Goal/text/basis/Checks/顺序、非法操作/role/basis/字段、Goal修改、非法正式Adjustment、失效Checks等拒绝 |
| Keep/停点/撤回 | Keep=ready空edits且Effective=Original；need_evidence空edits/nullChecks返回null；整段delete映射to=[]；no_change须全部撤回/Checks=[]；部分撤回不自动修Checks |
| 结构与语义区分 | 人工插入类别级终止条件结构通过；audit将风险原文、插入锚点和Diff暴露；标记semantic_validity=not_evaluated，未伪造语义审核 |

额外覆盖：Unicode/emoji/CRLF/尾空格不归一化；重复JSON键拒绝；后项只匹配原快照；输出重复运行一致；canonical哈希忽略对象键序但保护数组序和全部Plan内容；未来草案渲染无未填占位符，不含R05/M6/S01等人工答案。

## 2. 真实保留映射与风险暴露

{l(E/'results/human_runs/single_replace/audit.json','单项audit')}：原u1前523字节保持，原`[610,1072)`映射到新`[625,1087)`且SHA相同；u2 `[0,514)`完整保留。所有原Update来源和修改映射都可审计。

{l(E/'results/human_runs/semantic_risk/audit.json','风险audit')}中的`replacement_text`由人工加入：

> Stop searching after each receptacle category has been sampled once.

它有锚点/结构合法basis和reason，故程序接受。但其语义合理性并未被程序判断。原compiler同样接受。这个测试刻意防止把字符串边界约束误称为证据充分性证明。

{l(E/'results/human_runs/rejected_missing/receipt.json','失败停点')}只记录anchor_missing，未产生Effective文件；{l(E/'results/human_demos.json','全部人工演示')}记录6次结构编译/合法停点和1次预期拒绝，无模型响应。

## 3. 初始失败与修正

首轮121通过、1失败：无效Checks已被原编译器正确拒绝，测试误预期错误文案`unknown Update`，实际为`check.update_ids: invalid references`。仅修正新测试断言，未修改原compiler或绕过校验。{l(E/'results/pytest_initial.log','初始失败日志')}、{l(E/'results/tests_initial.json','初始机器结果')}保留。随后122通过；增加哈希覆盖、跨Update依赖和新草案渲染测试后最终129通过。

以上只验证工程性质与接口，人工替换文本仍可能保留旧策略问题或产生语义冲突，不是新策略质量验收。
''')
(E/'reports/P3C2_NEXT_EXPERIMENT.md').write_text(f'''# P3-C2 后续受控模型实验准备（未执行）

## 1. 要检验的干预

旧自由替换Preconditioner vs 本实验锚定构造。两个条件均使用真实R05 Memory，不用旧无Memory A与新有Memory候选混比。旧B_format只能历史参照；需新同条件重复才能初步考察稳定性。

唯一主动干预为构造方式及其必要输出契约/指令。它包括锚定生成要求和确定性应用，不是只改某一字符串。若观察改善，也不能单独归因于字节复制而忽略模型指令变化。下一步仍需另行授权，当前没有发送请求。

## 2. 固定材料与配置

- Original：P1-B R05授权retry合法plan，canonical SHA-256 `{f['plan_canonical_sha256']}`；来源与文件哈希见{l(E/'config/source_manifest.json','来源清单')}。
- Parent、Grouping、六条当前runs P1/P3/P6/P7/P8/P10与候选不变；B真实Active M1/M2/M3/M6/M7/M8/M9及完整sources，无M10，不补P2/P4。
- 用户payload与保存B完全相同。未来仅system中替换构造/内部契约并填写确定性plan hash；执行背景保持。不给模型22项人工标签、矩阵、夹具或研究者理想策略。
- 固定当前已保存参数：{json.dumps(f['model_parameters'],ensure_ascii=False)}，timeout沿用300秒；模型/端点及返回实际模型必须在调用前核验，不能假定服务端永久不变。
- 保持原compiler及Editor接口。选定新草案和代码hash后冻结，再调用；不得根据输出补锚、改Prompt、修JSON或调整语义重采样。

草案：{l(E/'config/anchored_prompt_draft.md','完整Prompt')}；{l(E/'config/prompt_vs_B_format.diff','与原B差异')}。它保留原Parent适当性、历史比较和Actor条件，仅改变构造操作与实验内部输出要求。所有inputs/prompt必须在未来发送前装配并复核容量，不把旧B的成功调用当作新草案容量保证。

## 3. 建议预算与失败规则

建议预注册3次旧/3次新，共6次逻辑调用、每次最多1次HTTP、0自动重试；交错旧新顺序并保留全部结果。此预算只是待授权方案，不是本次调用许可。若只授权一次配对，只能作为可用性/现象探索，不能称稳定优越。

API失败/截断/非法JSON/锚点不唯一/冲突/编译失败均保留原响应和成本，停止该次，不自动回退整段生成。公共路由或容量阻碍则暂停实验，不压缩Memory或改单侧证据。若未来要技术重试，需预先统一或另行授权，不因语义不理想重采样。

模型必须直接生成锚定方案；禁止先生成完整Update再第二次解释。实现尚无live runner，因此调用前需要最小一次调用归档适配、内部格式解析及原响应保留；不能直接用正式run_preconditioner期待内部edits兼容正式JSON。

## 4. 预注册评价

先分别评价各输出，再比较同Original的最终行为要求。区分结构有效率、未选片段保持与语义更新质量。

1. 历史响应是否真正作用于对应原承诺？同时识别当前证据本就支持的修正。
2. 目标修改有无问题依据/合理可检验预期？合理Keep也合法。
3. 配套修改是否说明不改就不可执行/矛盾/损害必要行为？标签本身不算依据。
4. 是否顺带改变完成单位、回访资格、任务阶段/强度？新增要求是否有独立动机，而非借用整体理由？
5. 精确目标/处理交付/可知有效回访是否保留；旧不合理要求是否仍遗留？原文保持不是旧策略正确证明。
6. 是否仍允许明确、大幅、非保守的探索？不能以更少字符、更短输出或更少Adjustment判优。
7. 记录全文锚点等可能绕过细粒度保护的选择；结构合法但语义无据仍判为语义问题。人工风险夹具不作为训练答案。

“新构造减少无据附带承诺且有据目标变换未被抑制”才是目标信号；仅未编辑文本被保留是工程保证，不足以证明历史预条件化有效。需要观察结构失败率/输出Token成本，不把锚点失败全部记为语义失败。

## 5. 范围与运行阻碍

- 只支持同ID替换/撤回和多Update编辑；拆合/新ID未实现。未来案例如需这些操作须在调用前明确实验范围，不能输出后拿限制当方法成功。
- 当前无API调用适配、无本轮真实上下文容量验证、无冻结发送请求；需要完成这些并获得授权才能运行。
- 原代码无法检查语义、依赖必要性或组合冲突。未来人工承诺评价和真实行为验证仍必要；不得增加第二审核Agent替代本次设计。
- R05已用于机制设计。模型验证之后需预先选择未参与设计的Train案例评估泛化；不能把旧R04/R06自动称为未接触样本，更不能用最终Test调参。
- Memory增量要在新机制下另做同Prompt有无Memory对照；构造方式对照不能直接回答Memory独立收益。
- 文本通过之后，Editor/Replay须另行授权。单次行为仍不隔离具体规则因果收益。

本阶段只完成准备，不启动上述实验。
''')
# Freeze the final offline prototype, not a sent model request.
items=[E/'anchored.py',E/'prepare_fixtures.py',E/'prepare_prompt.py',E/'run_tests.py',E/'run_human_demos.py',E/'tests/test_anchored.py',E/'config/anchored_prompt_draft.md',E/'config/prompt_vs_B_format.diff',E/'config/INTERNAL_CONTRACT.md',E/'reports/P3C2_ALGORITHM_DESIGN.md',*(E/'fixtures').glob('*.json')]
save(E/'config/prototype_freeze.json',{'at':datetime.now(timezone.utc).isoformat(),'files':{str(p.relative_to(E)):sha(p) for p in items},'status':'offline_prototype_and_draft_only_no_model_call'})
spec=importlib.util.spec_from_file_location('protect',ROOT/'experiments/methods/v23_2/v23_2_diagnosis_interface_audit_001/verify_protection.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);v.EXP=E
before=read(E/'config/protected_before.json');after=v.snapshot();changed=sorted(p for p in before.keys()|after.keys() if before.get(p)!=after.get(p))
protection={'at':datetime.now(timezone.utc).isoformat(),'checked_before':len(before),'checked_after':len(after),'changed_outside_experiment':changed,'unchanged':not changed,'new_model_calls':0,'new_tokens':0,'environment_executions':0,'new_real_candidate':False,'artifacts':'Only HUMAN deterministic synthetic plans; old real outputs unchanged','network_attempts_tests':len(t['network_attempts']),'test_data':'Hash protection only; no Test contents analyzed'}
save(E/'results/protection.json',protection)
links=[]
for report in (E/'reports').glob('*.md'):
 for target in re.findall(r'\]\(([^)]+)\)',report.read_text()):
  if target.startswith(('http:','https:')):continue
  assert Path(target.split('#')[0]).exists(),(report,target);links.append(target)
protection['report_links_checked']=len(links);save(E/'results/protection.json',protection)
(E/'results/git_status_after.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))
assert not changed,changed
print(json.dumps({'tests':len(t['cases']),'protection':protection},ensure_ascii=False,indent=2))
