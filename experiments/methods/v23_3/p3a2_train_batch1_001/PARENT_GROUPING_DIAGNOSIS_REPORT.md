# Parent、Grouping 与 Diagnosis

六条任务固定来自 P3-C1 Batch-1 预注册，详见 manifest.json、tasks.json；未重新抽样。共同 Parent 与当时 R05 Parent 一致，Memory 保持 M1/M2/M3/M6/M7/M8/M9，不包含本轮反馈。预注册去重有历史文本前缀及未知别名的局限，不能声称已排除一切外部接触。

| 任务 | Parent 结果 | 步数 | 主要证据 |
|---|---|---:|---|
| P1 box→armchair | 成功 | 39 | 36 coffeetable 找到，37 take，39 move；此前重复导航 |
| P2 clean kettle→cabinet | 成功 | 12 | 7 找到、8 take、10 clean、12 move |
| P3 heat mug→coffeemachine | 步数上限 | 50 | 未观察到 mug，无 take/heat/move；多次返回空柜 |
| P4 cool apple→diningtable | 成功 | 8 | 3 找到、4 take、6 cool、8 move |
| P5 alarmclock/desklamp | 成功 | 5 | 3 take、4 回灯处、5 use 成功；回返有必要 |
| P6 two watch→dresser | 步数上限 | 50 | 未观察到 watch；无 take/move，循环和空手 inventory |

全部正常结束，4/6 成功、164 步；原 verifier 通过。P1–P3 在串行阶段，用户改为四并发后 P4–P6 并发执行，未重跑前三条。这是运行时调度差异，保留为比较限制。

共同 Grouping 一次成功：G1=P1/P3/P6 搜索循环与覆盖，G2=P2/P4 处理交付，G3=P5 灯具共位。Diagnosis 首次 HTTP 401 无输出，经用户授权保持请求重试，第二次 HTTP 返回唯一有效 revise。原 Schema 和加载校验通过，u1/u2 各三项独立要求行；未人工拆分或修正。

Original 全文见 original_plan.json。u1 要求扩展表面/设备搜索、到达后检查、直到精确目标/数量或所有可达候选位置检查完；u2 要求避免已空位置重复、完成未测类别或实例后再回访、遇循环换表面/设备。Goal 保留精确目标、必要处理交付及灯具共位，但也绑定了扩展类别与避免空位的实现方向。Checks 包括换类、目标数量和保留能力。

Diagnosis 不读取 Memory。正式 V23 证据选择随本次 Original 引用选入 P1/P3/P6；A/B 均使用这三条完整选定证据及相同 Memory v3，而非六条全量轨迹。相同 user payload 和完整冻结消息见 stage2_freeze.json、各 messages_frozen.json。

主要风险详见 DIAGNOSIS_GATE_NOTES.md：P3 实际去过 countertop，P6 去过 sidetable/dresser，不能说完全未扩展到表面；“不含目标”不等于空；“打开每个候选”应区分容器与开放表面；最近两步并不支持全局已访问状态。未事后改写 Original。
