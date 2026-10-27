# R05 行为机制逐任务核对

所有 P/Q 步号指本次新执行：P1–P10 为 Parent，Q1–Q10 为 Candidate，依次对应 val:0001–val:0010，不能与历史 Diagnosis 的同名步号混用。原始记录见 [TRACE_INDEX.md](TRACE_INDEX.md)。判断依据是动作、当时菜单、可见观察和环境反馈，不使用模型内部 reasoning。

| 任务 | Parent / Candidate | 实际行为与判断 |
|---|---|---|
| 0001，bowl + desklamp | 成功 4 / 成功 4 | 两组逐步动作相同：desk 取 bowl → dresser → use desklamp。目标与灯同处的成功行为保留，未出现非法导航或直接回退机会；不能据此证明新增 u3 起作用 |
| 0002，pillow + desklamp | 成功 5 / 成功 6 | Parent 先检查 bed 1/2 再携 pillow 去 desk 开灯；Candidate 先去 desk，再找 pillow、返回 desk 开灯。多的一步是起始探索差异，必要返回不计作搜索循环。未观察到同位置导航不可用的回退情境 |
| 0003，mug → sidetable | 成功 4 / 成功 4 | 两组都是 diningtable 取 mug、到 sidetable 放置，动作相同；保留基础成功能力，未经历防循环触发 |
| 0004，mug → sidetable（另一实例） | 成功 4 / 成功 4 | 同样逐步动作一致，无额外清洗或灯操作 |
| 0005，pencil → desk | 成功 5 / 成功 6 | Parent 先去 drawer 1 找到 pencil；Candidate 先查看 desk 再去 drawer 1，因此多一步。未出现回访循环，不能把这一步差异直接归因于搜索规则 |
| 0006，clean butterknife → drawer | 成功 8 / 成功 8 | 两组先检查 countertop 1/2，均在第 3 步拿到真正的 butterknife，再清洗并放置；同一表面有 knife 也未取错。此次新 Parent 已成功，不能用历史 Parent 失败给 Candidate 记一次修复 |
| 0007，clean butterknife → drawer（困难实例） | 失败 50 / 失败 50 | 两组都未拿到精确 butterknife，却操纵 knife。Parent P7:8/10/17 取 knife，P7:12/19 清洗，P7:9/14/21 放回，共 8 次非目标操纵；Candidate Q7:9/13 取 knife，Q7:10/19 放回，Q7:17 清洗，共 5 次。u1 明确未被稳定遵循，不能把失败全归为“目标未找到所以规则没有触发”。随后两组继续回访 drawers/countertops，未在预算内解决任务 |
| 0008，clean soapbar → cabinet | 失败 50 / 失败 50 | 两组都见到 cabinet 2 中的 soapbottle/spraybottle，未把它们当成 soapbar 操纵；但长期循环，均未访问菜单中可选的 shelf 1。Candidate 查看了更多位置（包括 bathtubbasin、sinkbasin 2），仍有 36 次目标获取前导航回访，与 Parent 相同；u2 未可靠停止循环 |
| 0009，clean soapbar → toilet | 成功 8 / 成功 6 | 两组从同一 countertop 获取 soapbar。Parent P9:2 执行格式异常的命令，无效果，P9:3 空手检查 inventory；Candidate 直接拿取、清洗、放置，省两步。这个差异含输出/解析层面的异常，不能直接认定为 u3 的策略性收益 |
| 0010，cool apple → microwave | 成功 14 / 成功 11 | Parent 第 8 步到 diningtable、第 9 步拿 apple，此前两次回访；Candidate 第 5/6 步即到 diningtable 并拿到 apple，无目标获取前导航回访。后续冷却、打开目的地微波炉、放置的动作序列相同；三步差异来自搜索阶段，与 u2 的扩展方向一致，但不是独立因果证明 |

## u3 的实际执行边界

Candidate 的 Q8:39 在菜单没有 `go to cabinet 3` 时仍发出该命令，反馈 `Nothing happens.`。当时菜单提供 `examine cabinet 3`，Q8:40 才执行该直接动作，但柜子早已看过且为空。这说明：

- 合法性预检没有稳定执行，不能把章节范围修正直接等同于执行遵循。
- 先做一次非法导航、再重复查看已知空位置，不是“预先选用适当直接动作并推进任务”的完整成功例。
- Parent 本身也会使用直接动作：P8:8 在没有 `go to cabinet 3` 的菜单下直接 `open cabinet 3`，得到了新内容观察；P8:15 的非法导航后则 P8:16 重查空 cabinet 1。这种行为不是 Candidate 独有。
- 两个 desklamp 任务里两组动作都合法，但未出现足以区分 u3 回退作用的情境。本轮支持保留其成功行为，不能证明全局规则已在各类任务稳定发挥作用。

## 计数与解释

- 普通任务的回访代理：首次成功拿到精确目标前，对已导航过的位置再次发出**合法**导航命令；desklamp 同处路线不纳入。Parent 58、Candidate 61。
- 0007 未取得精确目标，计数会包含错误替代物的搬运路线；它不是纯粹的搜索循环指标。普通任务的正确目标取得后必要返回均被排除。
- 重复可见 observation/menu/action 签名为 33 → 27，和导航回访数量回答不同问题，不能挑选其中一个宣布防循环成功。
- 无效/无效果执行为 3 → 1：Parent 包含 P8:12 的空动作、P9:2 的格式异常动作，以及 P8:15 的不可用导航；Candidate 是 Q8:39 的不可用导航。可识别的不可用导航实际是 1 → 1。
- “无导航命令时选中直接容器动作”的自动候选为 2 → 1；这些候选包含重查已知空位置，必须人工判断是否适当和是否带来进展，不能直接当作规则成功次数。

本轮没有观察到任务成功率提升。局部效率改善、额外探索开销与未遵循行为同时存在。不能由少了三步或单项动作减少推出 D/S/C、Memory 或某一 Update 的独立收益。
