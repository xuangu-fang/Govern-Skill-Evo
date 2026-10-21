# Editor 实际落实

A 使用首个有效 A2 Effective，原 Editor Prompt、参数和 Patch 引擎，一次真实生成成功，严格 load_editor(expected_preconditioner=...) 重载通过。原始请求、响应、patch.diff、actual.diff、candidate.md 位于 editors/A/。B 前六次无合法 Effective，未调用 Editor；第七次首次通过后，一次 B Editor 生成合法 Candidate，严格重载通过。

A actual.diff 将一般非灯具流程的第 1 条改成按不同类别的首轮搜索，增加第 2 条近期反循环规则，原精确目标/清洗/直接交付三条保留并顺延编号；灯具段落未改变。u1 的不同类别搜索、关闭容器开启、表面设备覆盖、类别一次的首轮完成条件全部进入 Skill。u2 的最近位置避访、改换类别、循环触发、空手不查 inventory 全部进入 Skill。没有把已指出的类别终点风险隔离在解释里，它成为 Actor 实际输入。

Editor 将普通流程适用范围列举为 put/clean/cool/heat/transfer，与 Goal 中任务范围一致，但保留的执行步骤只明确 clean，没有补出 cool/heat 的处理流程；它不是对新增 cool/heat 能力的完整实现。若后续 Actor 正确处理，这不能归因于新增明确处理条款。近期反循环段虽写“unproductive”，具体例外仍不充分（带物交付/必要处理回返依赖后续保留条款和 Actor 理解）。

Editor 去掉 Effective u1 解释性“only current observation and last two steps”的句子，但保留当前候选/当前观察选择和 u2 immediately preceding step；未加入外部记忆机制。所有类别状态要求仍是文本要求，不是工程保证。

结构落实有效不等于策略合理。A 的类别覆盖终点来自 Preconditioner，并非 Editor 自行新增；cool/heat 范围列举由 Editor 明文化。B 前六次无 actual.diff；第七次对应的实际落实如下。

## B7 → Candidate B

editors/B/ 保存一次真实请求、响应、patch.diff、actual.diff、candidate.md。与 A 的系统 Prompt、模型参数相同，严格 upstream 校验通过；两份 Candidate 不同，见 editor_input_audit.json。B 将未改 u1 完整落实到 Skill 第1条，把局部触发的 u2 放到第2条；保留位置级检查终点、多目标数量、空手不重复查 inventory，原精确目标/清洗/直接交付段落顺延，灯具段未改。Editor 未添加新的强制类别交替或类别一次终点。

B 的主流程介绍仍列 put/clean/transfer，未像 A 增列 cool/heat；两组实际步骤都未新增完整 cool/heat 操作流程。B 按 Effective 保留“打开每个候选”、全局剩余未测试条件；新增标题 known-empty 又与正文 lacks target 有概念差异。这些约束风险仍在 Actor 输入中，结构正确不代表可执行性已解决。

A 与 B 在主要落实上均忠实反映各自 Effective：A 的类别首轮终点和强制换类、B 的位置终点与可选未检查关闭容器来自 Preconditioner/Original，不是 Editor 独立创造。没有因 B Keep u1 而省略其 Skill 更新。
