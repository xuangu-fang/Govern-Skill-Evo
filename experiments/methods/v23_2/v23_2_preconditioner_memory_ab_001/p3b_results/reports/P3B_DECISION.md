# P3-B阶段结论：同Prompt有效A/B已补齐

**本版主对照改为：合法A_format_001（无Memory）与新B_format_001（真实R05 Memory）。两组完整system Prompt逐字相同，其他请求字段除Memory外完全一致。原B和失败尝试仅作历史记录，不与新B混用。**


## 1. 实验控制与实际结果

本次保留A已授权的格式修复，未再修改策略性Prompt。B完整请求除Memory外与A一致；双方均由原解析器接受并由原编译器产生Effective Plan。因此当前配对的输入控制与结构验收通过。此格式修复是对最初P3-A协议的明确修订，旧冻结和失败尝试仍保留。

- A：ready，Keep全部Original Updates。
- B：ready，替换u1，优先探索尚未使用的类别；仍保留单向扫描、开闭容器与精确目标要求。u2、Goal和Checks不变。
- B引用M3/M6的历史编辑与混合响应，确实对应最终u1变化。不是只在reason中提及Memory。

## 2. 三项判断分别成立到什么程度？

**A. 历史响应是否影响更新取舍？——出现初步方向性线索。** B明确以旧反循环指导未稳定奏效、扩大覆盖的条件性收益解释策略变换。可是当前执行本身也支持探索其他类别，单次A/B不能证明此变化必然由Memory引起，也不能隔离M6作用。

**B. 替代Update是否更合理？——未充分通过。** B引入`every receptacle type ... has been sampled once`的结束条件，未说明为何每类一次即可替代具体位置覆盖。M6恰有同类其他实例遗漏的反例。B仍依赖全局未用类别/全部类别采样记录，当前候选与两步历史不能一般性提供这些状态。方向变化不能推导出整体构造改善。

**C. 是否保留有效行为与合理探索？——文本部分保留，但尚有风险。** 精确对象、温度/交付和灯任务Goal保留，跨类别探索可以是合理假设。没有证据证明类别一次终止、全局进度前提合理。u2未变，对状态变化后重试的边界也未获得增量修正。未执行Actor，不能声称实际发生提前停止或行为退化。

## 3. 怎样区分当前纠正与历史增量？

先独立评价A/B每项行为要求；再定位B相对A的实质差异，并追溯它是否利用了“历史改了什么—随后观察到什么”的关系。当前事实已经支持的合法动作、减少重复等，不直接记为历史独有收益。引用历史但未改变Update不算变换；不同但无据的类别终止条件也不算改善。本次仅u1方向变化具备响应预条件化线索，完整替代方案未满足有据构造要求。u2、Goal、Checks没有观察到增量。

## 4. 成本、保护与下一步

本次新增B一次请求，0重试，90.796秒、490,937 Token；所选合法A/B总555,963 Token。全部历史9次请求已知合计1,390,028 Token，初次A超时消耗未知。无可靠货币账单。没有Editor、Replay、Actor或环境执行。

旧报告先备份，随后只更新四份主报告与评价JSON；[保护核验](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/results/protection.json)记录历史文件检查。详细对照见[更新对照](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/reports/P3B_UPDATE_COMPARISON.md)，归因见[Memory归因](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/reports/P3B_MEMORY_ATTRIBUTION.md)，调用账本见[执行报告](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/reports/P3B_EXECUTION_REPORT.md)。

**结论：同Prompt对照已完成；观察到有历史响应依据的方向变化，但没有证实Memory稳定改善最终策略构造。** 不晋升默认方法，不宣称Skill性能提升。若后续获授权，先以预注册同条件重复核查方向信号，再决定其他实验；本次不追加Prompt补丁、不开展行为验证，完成后停止。
