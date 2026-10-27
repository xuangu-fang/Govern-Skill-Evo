# R05 首份合法输出审查

对象：`runs/R05_replay/attempt_003/parsed.json`。以下 M10/M11/M12 为隔离提交分配的 ID，K 为报告定位编号，不是新增生产字段。

| 条目 | 有效内容 | 影响采用的问题 |
|---|---|---|
| M10/K1 | 正确记录 Candidate 仍取、清洗并放置 knife，说明强化精确对象措辞不保证遵从 | 把 soapbar 写为 `absent`，并概括为 `absent-target failure`。当前 Pair 未完成所有候选位置的探索，不能建立全局不存在条件 |
| M10/K2 | 保留 pencil、两组 mug 和正确 butterknife 的获取能力；不把成功说成首次获得能力 | 只引用取得目标步骤，完整 trace 和 outcome 可以支持后续行为；不应把这一点误判为引用无效。仍缺当前 apple 比较 |
| M10/K3 | 保留多轮“不操作近似对象也未成功”的边界 | 将 S1_R03/P10 写成 `took and heated a cup`。实际40步取cup、41步放回cabinet8，后续移进microwave并开关门，但完整50步trace没有heat动作。模型当时可见该完整动作序列。再次把未找到描述成 absent |
| M11/K1 | 识别 no-revisit 仍未稳定打破循环 | 称 Candidate 增加 Parent 未访问的两个“receptacle types”；实际是新实例bathtubbasin1和sinkbasin2，Parent已访问sinkbasin1。继续以 absent 作为失败条件 |
| M11/K2 | 保留历史bread改善、另一bread退化及plate38成功/50失败 | 结尾“failures concentrated when the exact target was absent”超出证据，且前述bread/plate两侧实际可找到目标。历史比较被保留不等于解释校准完成 |
| M12/K1 | 正确区分全局Admissible Actions；Q8:39非法导航及后续examine对应正确，不再把历史drawer8事件归给当前Q7:25 | 把direct-action分支概括为未测试，遗漏P8:8：菜单无go to cabinet3但有open cabinet3，Parent实际合法开柜。可确认既有能力与可用机会，不能确认Parent的内部导航意图或因果fallback。其“every other…eight successes”也未清楚处理同样失败的Q7 |

当前apple14→11及其取得目标前的三步搜索差异完全未写入新提案，P10/Q10引用也消失。soapbar-to-toilet8→6及desklamp范围外保持也未写入；不能仅因Prompt要求survey every pair便假设实际覆盖完成。

相对P4，补入了正确butterknife能力保持和历史搜索对照；相对V2，没有改善absent边界，重新出现历史cup动作错误。三份提案都没有可靠处理P8直接开柜的能力比较。

未来输入方面，当前P10/Q10、P9/Q9、P1/Q1、P2/Q2均未成为本轮Memory来源；P8仍保留完整trace，且引用P8:6的邻域展开包含P8:8（窗口4–8）。因此“该能力比较没有写进Knowledge”与“下一轮完全看不到它”必须区分。第二轮确有机会利用保留窗口进行校准，但不保证会做到。

这些问题属于事实、条件范围及比较选择，不是JSON不合法。未修改或剔除原样提案，仍使用它作为隔离第二轮研究对象。
