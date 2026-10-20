# P3-C2-B 实现报告

**完成的是独立确定性原型，不是已验证的新预条件化算法。** 全部文件位于本目录；正式源码、Prompt、默认配置和P0—P3-C1不变。没有联网生成、Editor阶段、Actor或Replay。

## 1. 实际实现

| 文件 | 功能 |
|---|---|
| [anchored.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/anchored.py) | 精确契约/哈希/引用/依赖/锚点校验；UTF-8区间应用；原Adjustment转换；原compiler；audit/Diff；离线CLI拒绝时仅写receipt |
| [prepare_fixtures.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/prepare_fixtures.py)及fixtures | 构造HUMAN测试方案；payload是保存B请求的用户输入逐字段副本；不造新真实结果 |
| [test_anchored.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/tests/test_anchored.py) | 52项原型测试，包括真实R05文本、Unicode/CRLF、非法操作、停点和语义风险 |
| [run_tests.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/run_tests.py) | 禁止socket连接后执行原型与77项既有相关测试；记录每项结果；旧阶段调用均本地mock |
| [run_human_demos.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/run_human_demos.py) | 7份人工演示（6次结构编译/停点、1次预期拒绝），仅本目录归档 |
| [未来Prompt草案](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/config/anchored_prompt_draft.md) | 以B_format为上下文，改为一次生成锚定方案；保留既有证据/Actor约束；不含22项人工分析答案 |
| [草案Diff](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/config/prompt_vs_B_format.diff) | 所有改动可审阅；没有接入默认路由，没有发送 |

## 2. 完整文本如何得到

真实R05 u1人工单项测试选择Original字节`[523,610)`，替换为人工局部片段。程序复制`[0,523)`，写replacement，再复制`[610,1072)`，形成1087字节的新u1；后段对应新`[625,1087)`。u2的514字节全部保持，Goal/Checks保持。详见[字节映射](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/results/human_runs/single_replace/audit.json)与[实际Diff](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/results/human_runs/single_replace/changes.diff)。

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

仅为人工夹具执行，不应作为真实Preconditioner响应发布。错误receipt保留原文件引用/哈希和错误原因，未输出部分Effective。历史保护见[核验记录](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_commitment_anchored_001/results/protection.json)。
