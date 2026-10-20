# P1-A：Diagnosis 策略承诺的证据追溯与失败归因

独立离线分析归档。唯一输入来源是已冻结的P0/P1材料及其正式V23当前Parent执行。没有新的模型输出或行为实验；默认方法仍为原V23。

主要结论：现有输入足以纠正R04的无据必要前置链／回源范围问题，以及R05类别覆盖与位置覆盖的混淆。R06目标解绑、删除穷尽和进展保证、增加近期fallback是实质改善；全局状态依赖与保留边界仍未完全落地。策略优劣和最佳切换尺度没有被当前材料证明，不应以“未经验证”为由封禁合理探索。

## 报告

- [P1A_EVIDENCE_TRACE.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_trace_001/reports/P1A_EVIDENCE_TRACE.md)：21项关键承诺的实际字段、沿袭关系、当前证据、支持范围及判断；包含pre-action候选和两步历史反例。
- [P1A_ROOT_CAUSE_ANALYSIS.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_trace_001/reports/P1A_ROOT_CAUSE_ANALYSIS.md)：区分可观察的功能性归因、信息缺口与无法证明的内部推理解释。
- [P1A_NEXT_STEP.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_trace_001/reports/P1A_NEXT_STEP.md)：P1-B最小研究建议与P0验收方法，未编写新Prompt、未实施。
- [EVIDENCE_INDEX.md](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_trace_001/reports/EVIDENCE_INDEX.md)：原文件路径及JSON Pointer约定。

## 确定性核验与保护

[audit.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_trace_001/audit.py)只读既有归档，使用标准库及从原文件提取的两个纯Actor渲染函数，输出限于本目录；不导入／执行项目阶段、不访问网络、不做自然语言评分。

运行：

```sh
python /Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_trace_001/audit.py
```

- 27条Parent轨迹、663步实际Actor消息与事实装配核对通过；122个关键步骤提供摘录，其余用原路径引用。
- 原环境候选与Actor可见候选分开保存；精确过滤`help`，保留其余顺序、空白与重复项；后菜单仅取下一步前菜单。
- Diagnosis无Memory；新旧user输入相同；system差异仅为冻结P1的两处替换；只采用result指向的合法输出。
- P0/P1冻结清单13项、case来源哈希35次核对通过。重复来源按原case保留，不将35当作35个独立文件。
- 12,286个保护文件的集合与SHA-256保持一致，包括正式V23、先前V23.2/P0/P1归档、源码／配置／Prompt、相关测试／文档和原有未提交文件。Test仅计算保护哈希，未分析其内容。
- 新增LLM、Actor、Replay及其他自进化阶段调用均为 **0**；新增模型Token、API费用为 **0**。既有P1的3次调用不是本次新增成本。

结果见[机械核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_trace_001/results/audit.json)、[保护核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_diagnosis_trace_001/results/protection.json)。这是输入完整性／研究可追溯性通过，**不是P1语义通过，也不是P1-B/P2授权**。

本次仅新增本目录文件。旧报告不改写；本文对旧报告中“预算遗漏”“回源排除”“类别早停”的结论补充了适用边界：没有Editor／新Skill，不能把文本风险写成已发生的行为退化。完成P1-A后停止。
