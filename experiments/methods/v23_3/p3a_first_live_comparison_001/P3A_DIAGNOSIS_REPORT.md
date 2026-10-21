# P3-A：真实 Diagnosis

首次逻辑调用返回合法 `revise`，原 Schema 校验通过；1 个 HTTP 请求，0 重试，finish_reason=stop，响应模型 deepseek-v4.1-flash。HTTP 耗时 62.55 秒，阶段耗时 62.66 秒。

usage：prompt 65,593，completion 8,815，total 74,408；reasoning 7,951 已包含在 completion 中，不重复相加。货币费用未知。

## 原始 Plan 与门控

完整且未经人工重排的 [Diagnosis](runs/diagnosis/diagnosis.json)、[原始响应](runs/diagnosis/response.json)、[实际 HTTP 原文](runs/diagnosis/http/001/http_response.txt)、[请求](runs/diagnosis/http/001/request.json)均保存。以下只是索引，不代替实验输入。

Goal：改善非灯具检索、处理、放置中的精确目标忠实性与搜索效率，同时保留已成功的灯具共处和精确目标完成行为。Goal 没有锁定类内穷尽、固定跨类顺序或特定开门实现，不构成本轮共同输入障碍。

| Update | 原始完整行为行 | 依据/Checks |
|---|---|---|
| u1 | 3 行：精确目标未观察到时不得操纵相近替代物；容器仅有不匹配对象时离开并继续搜索；非目标处理/放置不算进展 | G3、P7:5/7/9/outcome；c1 |
| u2 | 3 行：同类若干检查无目标后，在回查空位置前扩展至少一个未检查的其他类别；搜索包含可见开放表面；离开空容器并选未检查候选，避免回到已检查容器 | G2/G3/G4、P3/P6/P8/P10 相关步骤；c2 |
| u3 | 2 行：命令必须在当前候选中；导航不可用但直接操作可用时选择适当直接操作，否则选其他推进任务的合法动作 | P1:4、P6:20/21、P8:5/6；c3 |

u2 三行分别处理调度、搜索对象范围和回访选择，可以独立判断；条件与行为保持完整，不是机械换行。其他 Updates 也使用真实多行字符串。没有自动拆句、人工补行、改 Goal 或修策略。

[阶段门](results/diagnosis_gate.json) 在 A/B 请求前保存：**通过可比性门**。这不是策略质量通过。Original 仍有 `still-unexamined / uninspected / already-inspected` 的全局历史可得性问题；“至少一个其他类别”是可调整策略假设；“exact noun phrase”可能有过字面解释风险。全部原样保留给两组。

## 共同输入冻结

原 `preconditioner_input` 实际选入 P1、P3、P6、P7、P8、P10，G1—G4 和 103 个 command_sets；不是所有十条当前运行。两组看到完全相同的选入事实与历史 Memory。未选入 P2/P4/P5/P9 的整条执行不被暗补为请求证据。

[共同输入检查](results/common_input_checks.json) 已通过原自由替换和 Patch 接口的 Keep 编译兼容检查。A/B user message 字符串相等；A 消息 1,629,114 字符、B 1,631,947 字符，差别来自方法 system Prompt。均在已冻结工程字符/字节预算内；未探测或承诺服务端上下文容量。
