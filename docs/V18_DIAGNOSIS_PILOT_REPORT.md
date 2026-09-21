# v18 Diagnosis Prompt 第一次固定输入试验

2026-09-18；Prompt `v18-group-diagnosis-1`。这是第 3 步的初步语义检查，不是完整 Skill 演化实验或效果验收通过报告。

**2026-09-19 职责边界更正**：本报告记录的是 v1 观察。正式 v18 中，旧 Simulator 的 STOP artifact 属于上游 benchmark 问题，不作为 Diagnosis/Prompt v2 核心语义验收项。下文保留历史事实并按该边界调整归类；原始模型输入、输出和统计均未改写。当前优化只针对未知产生额外义务、候选规律强度提升和条件/范围丢失。

## 设置与来源

固定三份历史 Evolution group 输入：R2 g5（定价）、R2 g3（订票/人数/姓名）、R3 g6（定价）。每组 deepseek-v4-pro 调用一次，temperature=0、reasoning_effort=high、24,000 completion token 上限、300 秒 timeout、无 SDK/应用重试。不运行新的 Agent、User、Grouping、Compiler、Editor 或 Monitor。

输入清单：[sources.json](../experiments/configs/v18_diagnosis_pilot_001/sources.json)。调用前核对四类历史文件摘要、原始请求与旧输出验收；发给 v18 的 learner payload 与原 v17 请求完全相同。旧 Diagnosis 输出只参与来源复验，不发送给模型。不使用 Monitor 轨迹或隐藏 evaluator 作为新输入。

实际 Prompt SHA-256：`f3ebc4917b7edb6283b0fdbd42e3c85b159704dbd73b5861fce1b6d63f8f3254`。
原始请求/响应/验收产物：[pilot 目录](../artifacts/v18_diagnosis_pilot_001)。完整结果：[summary.json](../artifacts/v18_diagnosis_pilot_001/summary.json)。这些产物保留在本地 artifacts 中，不纳入正式学习或候选选择。

## 结构结果

| 固定输入 | 结构/引用验收 | Addressability | Gap | 用时 | Provider total tokens |
|---|---|---|---:|---:|---:|
| R2 g5 | VALID | ADDRESSABLE | 2 MISSING | 280.4 秒 | 75,705 |
| R2 g3 | VALID | ADDRESSABLE | 1 MISSING | 144.0 秒 | 53,248 |
| R3 g6 | VALID | ADDRESSABLE | 2 MISSING | 164.6 秒 | 68,240 |

合计 3 次模型调用、5 个 gap、197,193 provider-reported tokens。不是费用估算；各组并发，耗时不相加作为墙钟总时长。三个 Parent 都是 S0，因此本次没有真实 NEEDS_REVISION/SHOULD_REMOVE 语义样本，删除仅有工程测试，尚未做模型侧证据门槛验证。

## 逐组语义检查

### R2 g5：保留了条件差异，仍有新增执行门槛风险

Analysis 不再把结算变化概括为任意变化：明确 horizon 保留原价，summit 四条均重定价；还明确指出 summit 没有查询保留航段当前搜索价，不能证明它等于结算价。第一个 gap 保留 horizon 计算依据，这是有用的条件信息保持。

第二个 gap 将 summit 的有限机制证据转成 guard：不要仅依据原价/显示价提交最后一次修改，须先取得用户接受实际金额可能不同的确认，否则在工具无法解决时转人工。引用中的真实用户阈值当然不能绕过，但输出尚未充分证明这一新的渠道级前置要求是必要修复，也未证明所有合法信息补救途径都不可用。尤其 reason 将“避免不可逆错配”直接当成 Skill 可修复依据，不等于解决原任务。

评估：条件归纳较历史 v17 输出更具体；避免新增执行门槛这一目标仍未充分达成。不能因缺少精确 summit 机制而硬编码补全正确价格映射，也不能把该 guard 直接评为有效成功修复。

### R2 g3：未重复生成姓名外观规则，人数指导仍有范围与强度疑问

输出把 T024 缺独立 first/last name 的问题保留为 unresolved，没有产生姓名外观检查或 placeholder 禁止订票 gap。人数对照得到保留：5 人单订合规、6 人单订不合规、7 人拆 4+3 合规；行李问题因精确分类未知未强行生成指导。

人数 Analysis 称其为候选边界，但 gap 使用超过 5 人不得单订、每单至多 5 人的强指令，还附带每笔拆分使用相同付款方式等要求。候选身份虽在后文解释，强度是否被提升、附加付款一致性是否有充分独立依据，仍需审查。

评估：没有复现历史姓名外观门槛，保留了有用数量对照；不能据此认定整组 gap 已语义合格。

### R3 g6：价格映射保留，另有旧 Simulator artifact

第一个 gap 明确保留 horizon 原价 / summit 当前搜索价的映射，并标注为经验候选而非可见 policy，Analysis 与 gap 的条件关系较完整。

第二个 gap 要求确认后立即执行 update。其引用 `T004/R021/R1/E0035` 是用户确认且包含 `###STOP###` 的最后一条消息。已经核对本次输入中的原文；在该 benchmark 的实际运行中没有下一次 Agent 决策机会。模型却在 reason 中声称这是一个可到达的下一回合，并否认自己是在尝试恢复已结束轨迹。

归类更正：原 v1 分析曾把该项视为 Addressability 语义失败。按正式职责边界，这是旧 benchmark/runtime artifact，不要求 Diagnosis 正确解释其运行时后果；它不作为 v2 核心语义验收项，也不用于继续 patch Prompt。上游修复不改变历史事实，历史输入及输出继续原样保存。

## 结论与边界

本次完成了 Prompt、完整请求、v18 transport/验收的接入验证；三组都成功返回，184 项相关工程测试通过。小规模试验显示部分具体规律和信息缺口被更好保留，同时仍有新增门槛和强度提升问题。**不能宣布 v18 Diagnosis 语义目标已全部通过，不能据此宣布成功率改善。**这一判断不以 STOP artifact 的解释为依据。

历史请求保存 Prompt v1 原文和全部响应，不自动修补、不选择最优输出、不以新版本覆盖本次结果。后续 Prompt 试验另建目录，重点检查“未知是否被转成额外义务或转人工要求”“候选关系到 gap 的强度保持”“条件与适用范围是否保留”；不要简单要求所有未知机制先验证后执行，也不围绕旧 STOP artifact 继续 patch。

这三个定向挑选的开发样本不是独立 held-out 评测，每组一次也不能测量固定输入生成方差。Simulator v18 的修复不会改变历史输入中的终止事件；本次没有测试修复版 Simulator 的实际残余 STOP 率，也没有运行任何 Candidate/Gate。
