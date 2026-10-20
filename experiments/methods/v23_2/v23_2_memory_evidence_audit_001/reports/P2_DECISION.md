# P2 阶段决策

**可准备后续R05固定Original Plan对照，不需要先重写M6或全面改造Memory。M10存在真实概括偏差，但并非R05当时输入；对R06应单独控制这一变量。R05未选P4不是主要更新判断完全无法进行的硬阻碍；若要完整评价u1，建议未来显式、对称补P2+P4。**

## 七项回答

| 问题 | 结论 |
|---|---|
| 1. M6是否有实际影响策略判断的概括偏差？ | 核心收益、遗漏、循环、预算不足与单次联合编辑限制准确。`falling back`不是实际Adapter fallback；轻微工程措辞不准，但未发现由此永久禁止动作等策略扩张。无需先修Memory |
| 2. M10位置与类别混淆是否证实？ | 是。P6已到countertop1，Q6在countertop2发现目标，属于同类新实例。另有未找到butterknife被写为不存在的证据越界；不是已证明目标实际存在 |
| 3. 原Diff与行为证据是否真实传递？ | 是：R05/R06实际请求包含M6对应Diff及引用run全文；R06包含M10 Diff及4对引用run。请求/响应/valid及快照重载核对通过。不是全部历史十对都传入；聚合结果本次回溯archive另核对 |
| 4. 主要是概括、缺证还是使用未验证？ | M10有局部概括失真/限定弱化；关键准确source未缺。概括如何影响实际Keep尚未隔离，不能归因已证。当前证据另存在选择性省略，应分开 |
| 5. P4等是否P3必须依据？ | 不是纠正主要过强要求的唯一必需证据；P3自身和G2已有关键事实。但若以P3/P4精细对照或完整u1保留为验收，就应补相应全文；建议P2+P4，不一律补齐 |
| 6. P3前需要修什么？ | 先固定评价范围、当前证据条件和两组对称输入；标明只用R05当时Memory。没有必须先动正式Memory或方法代码的证据。若研究R06“准确历史认识”则先独立说明M10修正副本条件，不能把原M10当无误真值 |
| 7. 暂不修什么？ | 不扩大Memory审计；不因摘要不够详尽重写M6；不自动补所有Parent；不调整Actor历史窗口；不规定唯一搜索调度、阈值、禁回访或停止策略；不把知识纠偏等同于决策收益 |

细节与原文见[Memory核查](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_memory_evidence_audit_001/reports/P2_MEMORY_AUDIT.md)、[R05证据选择](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_memory_evidence_audit_001/reports/P2_R05_EVIDENCE_SELECTION.md)及[来源与原始执行索引](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_memory_evidence_audit_001/reports/SOURCE_INDEX.md)。

## 三类判断必须分离

| 仅凭当前Parent/任务条件可识别 | 历史M6/M10额外提供 | 综合后仍不能确定 |
|---|---|---|
| P3已有无新信息回访与直接获取交付；P6/P8遗漏位置；P10晚找到后仍需处理交付。不能把这些现象当作类内穷尽的唯一证明 | M6提供实际扩展搜索/近期避免循环编辑后的收益与同类实例遗漏、非法动作重复、晚发现仍失败的配对响应，而不只是另一些失败轨迹 | 类内穷尽与跨族何者更优、切换尺度、具体排序、预算分配、稳定成功率与步数收益 |
| G1/P2提供持目标后返回已知lamp的必要边界；已访问不等于无用；任务前提不因去重而消失 | M10提供R05实际反长时间困在一族Diff、两次修复与循环/增步并存；但只可用于R06及之后，且位置/类别及目标不存在断言须校正解释 | 哪个编辑独立导致收益/退化；M10失真是否导致Keep；纠正knowledge能否改善Update |
| 动作无效发生于具体状态；不支持永久禁同类动作，信息性动作并非必须立即state-changing | 历史联合编辑显示提示已被尝试却未稳定遵循，因此应限制保证性结论；不自动要求撤回整个方向 | 如何在Actor两步视野下最好实施全局覆盖；当前来源不能证明某个确定调度已获因果验证 |

R05当前材料能纠正条件错误，不代表Memory没有增量价值。P3应关注有无Memory时，**编辑—行为响应是否改变最终Update的方向、条件或强度，并且这种改变有可追溯依据**；只看引用Memory或Adjustment数不能回答。一次随机输出差异不等于稳定因果收益。

## 推荐的P3准备边界（未执行）

1. 固定R05 P1-B合法Original，不再生成Diagnosis；排除M10与事后Memory。
2. 明确取窄目标原六条，或完整u1评价的“六条+P2+P4”。后者增加9,738字符/bytes，低于已有容量，作为明确证据补充条件冻结；两臂相同。
3. 两臂仅改变历史Memory（entries与sources整体），不同时改Prompt或knowledge；若未来要测试M10修正概括，另列独立条件和轮次，保持原Archive不变。
4. 验收分开当前证据纠正、Memory增量、未验证探索。不预设类内或跨类标准答案，不强制Adjustment。

## 本次离线核验与保护

- 40条原始记录重建facts，与两个历史Memory context的动作、前后观察、候选、结果逐项一致；20对task/game/seed/initial配对一致。两份actual.diff严格应用得到相同Candidate，仅调用纯Patch函数。
- 两轮正式实际Preconditioner请求与重装消息相等；Active快照/不可变commit与输入相等；M6内容跨轮一致，M10只在R06。
- R05静态选择/七种尺寸条件在网络连接被禁止的脚本中运行；Original、Grouping保持不变。未发送任何请求。
- 第一次本地脚本因缺PYTHONPATH停止；第二次旧全源码基线检查因**任务前已有**模型路由/CLI改动停止。记录于preexisting_contract_drift.json；没有恢复或覆盖。改为核对实际用到的preconditioner装配/读取、memory读取、facts构建、editor.apply_patch函数AST与冻结版相等，并核对原请求逐项相等。与本任务无关的路由变更未执行。这些是离线核验启动错误，不是模型失败重试。
- 唯一新增区域为本P2目录，含三份报告、来源索引、轻量脚本、哈希/核验结果；保护覆盖已有src/experiments/artifacts/docs/tests/benchmarks及.gitignore，忽略缓存。Test只做哈希保护，不分析其轨迹。
- 保护细项与开始/结束状态见[保护核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_memory_evidence_audit_001/results/protection.json)；已有未提交变化及冻结源码差异单独保留，不归因于P2。没有运行大量无关测试。
- **新增模型调用0、Token0、API成本0、Actor/环境调用0。没有修改Prompt、方法、Memory或默认配置，没有进入P3。**

本次结论是“能够明确数据和解释边界”，不是已改善Preconditioner或Skill性能。
