# P3-C1 完整 Replay 结果

最终 12/12 条 Episode 正常结束：9 success，3 step_limit，无技术未完成。这里“正常结束”包含耗尽 50 步后的正常失败，并不等于全部任务成功。12 条 raw trajectory 均通过 verifier，8 组 Parent–Candidate 配对与 4 组 A–B 条件核验通过。本轮只做离线审计，没有重放环境。

## 分组结果

| 条件 | 原生成功 | P3/P6/P7/P10 步数 | 总执行步数 | 成功任务步数合计 | 无效动作 / Nothing happens / fallback |
|---|---|---|---|---|---|
| Parent | 3/4（75%） | 4 / 10 / 50 / 14 | 78 | 28 | 0 / 0 / 0 |
| A | 3/4（75%） | 4 / 8 / 50 / 12 | 74 | 24 | 0 / 0 / 0 |
| B | 3/4（75%） | 4 / 11 / 50 / 12 | 77 | 27 | 1 / 1 / 0 |

Parent：P3 保持四步直达，P6 搜索后先到目的 drawer 再折返清洗，P10 多查 cabinet 与重复表面；P7 持续搜索但循环严重。

A：P3 相同；P6 顺序直接，P10 少两步；P7 开头连续检查七个 drawer 后仍循环，未解决目标发现。

B：P3 相同；P6 先查两个 drawer，较 Parent 多一步；P10 出现一次动作标签格式问题后恢复并成功；P7 先查三个 countertop，之后仍反复回到 drawer/已查表面。

## 配对结果

| 任务 | Parent | A | B | 本次可见差异 |
|---|---|---|---|---|
| P3 | success 4 | success 4 | success 4 | 三条动作链完全相同，无增益或退化 |
| P6 | success 10 | success 8 | success 11 | A–Parent −2 步；B–Parent +1；B–A +3。三组都取精确 butterknife、clean、交付 |
| P7 | step_limit 50 | step_limit 50 | step_limit 50 | 三组都未在执行反馈中观察到 butterknife；无 take/clean/move，无替代物操作 |
| P10 | success 14 | success 12 | success 12 | A/B 各少 2 步；B 第 2 步候选外动作，但最终精确 apple 完成 cool 和交付 |

相同成功分母下没有新增成功，也没有成功→失败退化。A 的局部步数优势与 B 的 P6 步数增加是实际观察，单轨迹不能估计稳定期望收益。P7 同为失败也不代表行为完全相同。

## 搜索覆盖与重复的描述统计

每格为“唯一导航位置数 / 类别数 / 同位置且相同返回观察的重复导航次数”。它不是语义质量分数：打开前后观察不同会漏计某些已检查位置重返；必要清洁、制冷与交付回返也可能被计入。

| 任务 | Parent | A | B |
|---|---|---|---|
| P3 | 2 / 2 / 0 | 2 / 2 / 0 | 2 / 2 / 0 |
| P6 | 4 / 3 / 2 | 4 / 3 / 0 | 5 / 3 / 0 |
| P7 | 13 / 4 / 18 | 11 / 3 / 24 | 11 / 3 / 25 |
| P10 | 5 / 5 / 2 | 5 / 4 / 1 | 5 / 4 / 0 |

P7：三组都打开全部七个 drawer，完成时间分别为 Parent 第 32 步、A 第 14 步、B 第 44 步。Parent 打开 cabinet 1–3，检查 countertop 1–2 与 sinkbasin；A/B 均只打开 cabinet 1，检查 countertop 1–3。A/B 的首个 cabinet 分别在第 45/34 步到达。三组初始可见 countertop 4，却均未访问；其余大量可见 cabinet 也未查。更多类别不等于目标位置覆盖，检查了 countertop 类不等于完成该类实例覆盖。没有读取隐藏游戏状态，不能说 butterknife 实际在某个遗漏位置，也不能说环境中没有它。

P6 Parent 第 6 步回 sinkbasin 是带物清洁，第 8 步回 drawer 是交付，不能因观察相同判为无效循环。P10 Parent 第 10 步返回 fridge 也是必要 cooling；第 5 步 examine 已空 cabinet 和第 7 步重复 countertop 才是不同性质的搜索开销。P7 各组从未持物、反复得到相同非目标内容，是更直接的无信息循环证据。

## 动作、目标与处理链

P3 全部：diningtable 找到 mug → take → sidetable → move，四步完成。

P6：Parent 第 3/4 步发现/取得 butterknife，7 clean，10 move；A 第 2/3 步发现/取得，5 clean，8 move；B 第 6/7 步发现/取得，9 clean，11 move。B 首四步查开 drawer 1/2，增加搜索开销，但提前打开目的 drawer 也省去交付时的一次 open，不能简单将四步都算净损失。

P10：Parent 第 8/9 步发现/取得 apple，11 cool，14 move；A/B 均第 6/7 步发现/取得，9 cool，12 move。没有以放入 fridge 替代 cool，没有省略交付；有效返回 appliance 被保留。A 第 5 步仍重访 countertop 1，说明“不重访”未稳定执行。

B/P10:2 原始输出含两个 `<action>` 开标签、一个闭标签。原投影器取首个标签匹配，得到含额外文本的候选外动作，环境返回 Nothing happens；`open fridge 1` 当时确实在菜单中，finish_reason=stop，fallback=null。第 3 步正确 open。该事实是 Actor 输出结构与既有投影行为问题，不能归因为 Memory 缺少开门知识、没有可用命令或 u3 要求错误。本轮未修补输出或重采样。

P7 没有找到目标后预算不足，而是整个 50 步未观察/取得精确目标；没有自行提前宣布覆盖完成。其余任务以原生成功反馈结束，未观察到必要清洁、制冷或交付缺失。未覆盖 heat、lamp、多实例数量能力，不能外推。

## 累计成本及异常

| 项目 | 全部原始与重启尝试累计 |
|---|---:|
| Editor 逻辑调用 | 2 |
| Episode 尝试 / 正常结束 | 25 / 12 |
| Actor 决策 / 客户端传输尝试 | 480 / 480 |
| 加 Editor 的客户端传输尝试 | 482 |
| 全部尝试执行动作 / 最终选定动作 | 467 / 229 |
| 已知 prompt / completion / total tokens | 663,893 / 250,140 / 914,033 |
| reasoning tokens，已包含在 completion | 209,131 |
| usage 未知的尝试 | 13 |
| 明确 HTTP 429 | 10 |

其余中断为一次 ReadTimeout、一次 ConnectionError，以及一次并行切换时遗留 worker 的工程中断；最后一种不写成服务限流。缺失 usage 不按零计，914,033 是已报告 token 合计，实际总量可能更高；货币费用未知。客户端连接失败不证明服务器收到 HTTP。中断前缀只进入成本，不进入成功率与最终步数。

证据：[逐步动作与反馈索引](TRAJECTORY_EVIDENCE.md)、[逐条统计](evidence.json)、[全部 25 次尝试与成本](costs.json)、[专项事实校验](specific_observations.json)、[最终选择原归档](../p3c1_r05_replay_restart_004/analysis.json)。
