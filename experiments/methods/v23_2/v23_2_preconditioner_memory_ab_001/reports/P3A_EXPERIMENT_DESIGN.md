# P3-A：R05固定Original的Memory有无对照设计

**状态：离线单变量装配通过，请求与评价预注册冻结；没有发送，没有真实Preconditioner响应。当前内网模型上下文容量尚未核实，P3-B执行就绪验收暂不通过。**

## 研究问题与假设边界

检验历史编辑—行为响应能否在相同Original Plan和当前证据下，对最终Update的策略、适用条件、范围或强度提供可追溯的增量作用。它可能表现为更合理的Keep、收窄、替换、拆合或撤回；不规定B应比A多做Adjustment，不以某种搜索算法为标准答案。

可观察假设：B相对A出现实质行为要求差异，且“过去改了什么→实际出现什么响应/局限→为何影响这次差异”的链条有据。空假设/未观察到增量：Effective行为相同，或只有reason引历史而实际Update不变。不同但无依据、过强或丢失有效行为也不是改善。

## 唯一Original与选择R05的原因

使用 [用户授权重试的P1-B合法Diagnosis](/Users/didi/Desktop/Govern-Skill-Evo/artifacts/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001/diagnosis.json)。决策revise，Goal及u1/u2、basis、顺序、Checks完整冻结；原文件SHA256为 `e026bb6dcd8ea2dedb85ee29c8f356299979e90e7d8153fd2b2f5597ce7f3fbb`。不是正式V23旧Plan、P1输出或首次截断结果，也没有人工修正。

R05 Goal基本为精确目标、覆盖/步效、必要处理交付及desklamp共址保留，不把某个具体扫描算法锁为唯一方法。u1同类编号单向推进/耗尽后换类/避回旧编号及全局未查状态可由Preconditioner调整；u2 no-op后不重试等价动作及立即state-changing的范围也可调整。接口不要求Diagnosis先生成完美策略。

完整Diagnosis快照保留顶层reason供追溯；**实际Preconditioner用户输入只有原plan，不包含Diagnosis顶层reason或生成过程**。不得把研究报告或原reason里未选轨迹信息偷偷加入请求。

## 两组与控制变量

| 项目 | A无Memory | B真实Memory |
|---|---|---|
| 原Parent/Original/Grouping/背景 | 相同 | 相同 |
| 当前完整runs | P1 P3 P6 P7 P8 P10 | 相同六条 |
| Grouping | G1–G4原装配内容 | 相同 |
| command_sets | 103个实际所需候选表 | 相同 |
| Memory | `{"entries":[],"sources":{}}` | R05当时M1 M2 M3 M6 M7 M8 M9及全部对应sources |
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

评价见[协议与空结果模板](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/reports/P3A_EVALUATION_PROTOCOL.md)；请求/哈希/限制见[输入冻结报告](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/reports/P3A_INPUT_FREEZE.md)。
