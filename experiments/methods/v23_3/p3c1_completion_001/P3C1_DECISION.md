# P3-C1 结项决定

**P3-C1 已完成：两份真实 Candidate、四任务三条件共 12 条正常结束轨迹、完整行为分析与两批新 Train 预注册核验。** 本轮补报告新增模型调用 0、环境运行 0，原始中断报告和全部失败尝试保留。

Parent/A/B 均成功 3/4（75%），P7 均 step_limit 50；总步数分别 78/74/77。A 的两条成功轨迹各比 Parent 少两步，B 一条少两步、一条多一步。没有成功率改善证据；困难搜索的循环与遗漏没有解决。

| 必答问题 | 结论 |
|---|---|
| 1. A/B 是否都有有效 Candidate？ | 是。两次原始 Editor 输出均通过离线重载、原 Patch 严格应用和 actual.diff 一致性核验；没有重新生成 |
| 2. B 全部 Keep 是否仍更新 Skill？ | 是。B Effective=Original，但 Original 本身要求更新，Editor 修改 general step 1/2 并新增 step 5。B 不是 No Change 基线 |
| 3. Skill Diff 有何差别？ | A 增加精确类别例子、surface 范围、更广表面清单、同类剩余实例与跨类检查的强回访前提；B 落实 Original 的检查若干同类后向另一未查类别扩展。两组保留位置级完成条件、必要清洁和交付，u3 基本相同 |
| 4. 是否完成配对任务？ | 是。最终 12 条全部正常结束，8 组 Parent–Candidate 与 4 组 A–B 核验通过。原历史外网 Parent 未混入严格基线；重启时点、实际并发和模型随机性仍是限制 |
| 5. 相对 Parent 有哪些改善或退化？ | 无成功/失败转换。A/P6、A/P10 各少 2 步；B/P10 少 2 步，B/P6 多 1 步；B/P10 多一次格式诱发的无效动作。P7 A/B 唯一位置更少、重复代理更多，但不能仅靠次数判总体质量 |
| 6. A 的强约束是否实际造成伤害？ | 未证明。P7 开头七个 drawer 连续检查与条款相容，但后续并未遵守全部同类实例完成后才回访；缺少反事实。成功任务未见必要回返/direct action 被阻断。保留文本风险，不把它写成已证实失败原因 |
| 7. B 未变要求对行为有何影响？ | 被落实为 Skill，出现先查 countertop 再换 drawer 的路径，但循环和未查状态问题仍在，不能确认其净因果影响。B/P7:8 的有限历史没有完整已访问账本，是可核验的执行条件限制 |
| 8. 差异来自 Editor 还是 Preconditioner？ | 主要文本差异可追溯至 A/B Effective，未发现 Editor 独立大幅发明策略；执行差异还受 Actor 随机性和指令遵循影响。一次 Editor/条件不足以隔离 Editor 随机作用 |
| 9. 是否有初步行为收益？ | 有成功任务路线缩短的局部线索，尤其 A；没有成功率提升或可靠防循环证据。B 未产生 Update Patch，无法借此验证 Patch 粒度优势或预条件化机制优越性 |
| 10. 新 Train 预注册是否完成？ | 是。原冻结两批各六条，在 Editor 之前选定；本轮用冻结排除表复现相同抽样、12 个实例互异。未读取游戏答案或执行这些任务；暴露筛查有截断/别名限制，不能称绝对独立 |
| 11. 下一步优先决策、Editor 还是 Actor？ | 优先检验更新决策能否提出适应 Actor 可见历史的要求，区分规则不可执行与 Actor 未遵守；另行记录 action 标签契约问题。现有证据不支持先重写 Editor。已冻结新 Train 对照应保持方案和样本，任何专项机制变更另行预注册 |
| 12. 是否足够进入 D/S/C 结构化实现？ | 不足。现有结果只指出方向、范围、关联与可执行性的待验证问题，不能证明增加字段或依赖协议会改善行为。不自动进入实现 |

## 研究问题的三个不同答案

- **更新粒度：未验证。** B 为全部 Keep，没有实际 Update Patch；Editor 的 Skill Patch 成功不能替代 Update Patch 证据。
- **历史响应参与：有来源与语义对应，增量效应未验证。** M3/M6/M8 在原输入中，支持目标边界、防遗漏和处理无效动作的动机；联合历史编辑/单次响应不证明当前强条件最优，也没有有无 Memory 消融。
- **策略构造质量：没有稳定改善结论。** 必要目标/处理/交付在这四例中保留，部分路线更短；P7 搜索失败和状态需求问题仍在。不能从局部效率推断泛化成功率提高。

## 下一阶段建议与停止点

最值得继续的是**执行已经预注册的两批新 Train 方法对照**，检验真实修改与 Keep 在新的开发实例中如何落实，而不是继续围绕 R05 改提示词。固定 Parent、Memory 的 R05 时间边界、任务清单、Actor/Editor、模型预算和共同 Original/当前证据；每批仅让 A/B 的 Preconditioner 构造方法不同，按原计划分别生成一次。未来运行前冻结技术重试与具体可用路由，不能依据结果择样本或更换 Original。此设计检验整体方法，仍不能单独归因于 Diff 格式或 Memory 因果增量。

本轮只提出建议，**没有启动新 Train、下一轮 A/B、Editor、Replay、Gate、Memory 更新或完整自进化**。也没有提交、重置或清理既有工作区修改。

## 交付与证据

- [PROTOCOL.md](PROTOCOL.md)：原冻结条件、追加技术恢复授权、实际范围与局限。
- [EDITOR_REPORT.md](EDITOR_REPORT.md)：实际 Effective → Skill Diff 与保留边界。
- [REPLAY_REPORT.md](REPLAY_REPORT.md)：完整三方结果、覆盖、动作、成本。
- [BEHAVIOR_COMPARISON.md](BEHAVIOR_COMPARISON.md)：u1/u2/u3、M3/M6/M8、事实与归因边界。
- [NEW_TRAIN_CASES.md](NEW_TRAIN_CASES.md)：原十二例与只读复核。
- [TRAJECTORY_EVIDENCE.md](TRAJECTORY_EVIDENCE.md)：最终十二条完整执行动作/环境反馈及 raw 链接。
- [validation.json](validation.json)、[costs.json](costs.json)、[protection.json](protection.json)：可复算校验、全部尝试成本与文件保护。

累计已报告 914,033 tokens（reasoning 209,131 已包含于 completion），13 次尝试 usage 未知，金额未知；480 Actor 决策仍在 600 上限内。包括追加授权的重启共有 25 次 Episode 尝试，不能表述为只执行过 12 次。最终行为统计使用首次正常完成的 12 条，未择优。
