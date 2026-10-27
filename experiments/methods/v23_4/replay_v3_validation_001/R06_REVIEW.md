# R06 首份合法输出审查

对象：`runs/R06_replay/attempt_002/parsed.json`，隔离提交 M12 修订 M10、M13 修订 M7。没有编辑原文。

| 条目 | 有效内容 | 仍需区分的限制 |
|---|---|---|
| M12/K1 历史搜索 | 保留butterknife/soapbar两项成功修复、apple38→46退化；把原M10中无证据的“没有exact butterknife存在”改为“no exact butterknife was found” | 仍把countertop2发现说成Parent未到过相应family；Parent已访问countertop1，是具体实例未到达，不是整个family从未到达 |
| M12/K2 当前改善 | 保留tomato18→10搜索差、creditcard24→9、book失败→40成功；注明联合编辑和单次执行不能给出孤立因果估计 | 与温变主题没有协调出tomato局部零新增收益的限制。`matching locations`压缩了原Diff中“与已检查位置可见内容相同”的条件，不能当作明确的离开目标位置指令，也不能当作精确复述 |
| M12/K3 当前限制 | plate9对8、apple未找到和持续循环均保留；使用未找到而非全局不存在 | 此项没有实质性新增动作错配；范围受当前观察约束 |
| M13/K1 温变收益 | 保留tomato39对8、8对7，plate虽减少开门但总步数9对8；比V2避免直接把所有历史Parent都描述成插入循环 | 概括为 `robust local reduction ... conditional on acquiring the exact target`，却遗漏同样取得目标、局部操作完全相同的cool tomato。历史heat-egg被写入文本，却没有自己的双方Evidence，S1_R03/P9、Q9也从投影消失 |
| M13/K2 温变前置条件 | 保留heat plate Parent找到目标13步成功、Candidate未到目标位置50步失败的不对称比较；当前apple和历史mug改用observed search中未找到 | 不能将这一成功校准推广为所有Active条目都已校准；未修订M11、M9仍有较强absent解释 |

cool tomato的可见事实是Parent第13步、Candidate第5步取得目标，其后均为去fridge、cool、去microwave、open、place五步。18→10差异在取得目标之前。V3搜索条目正确提到搜索变化，但未像P4那样明确保留“已有相同温变能力、没有新增局部收益”。这项遗漏会改变对温变条款适用范围和收益强度的认识，不能只归为少列一个任务。

下一轮投影仍保留tomato完整动作trace，但Parent详细窗口仅4–14、Candidate仅1–6，两个cool步骤15/7没有展开详细状态。相比P4，独立温变比较所需的详细证据覆盖退化。creditcard双方则重新得到保留，相对V2是有价值的恢复。

V3本轮修订文本没有把目标未找到升级成全局不存在，这是相对P4/V2的进步；然而旧Active中M11仍写“exact target was absent”等表述。未修订一条Memory本身不必然错误，但不能声称全库解释已纠正。

总体：R06优于V2的若干重要方面，但未全面超过P4；取得了部分条件校准和当前能力比较，仍遗漏重要零收益边界，并发生具体位置与容器类型的归纳升级。
