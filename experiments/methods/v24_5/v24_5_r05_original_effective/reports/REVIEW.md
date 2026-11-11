# v24.5 R05 快检

来源为 v24.4 正式训练 progress_decision_20261107_202453 的 R05。Diagnosis 输入与归档相同，含 R04 发布的 Parent、十条轨迹（7 成功、3 次步限）和菜单。由新 Original 自动选入 P5、P6、P7、P8、P10 及其菜单；Preconditioner 的 Memory 与原轮相同（M1–M6）。程序复用原配置和校验器。Diagnosis 第一次通过；Preconditioner 首次使用了不属于当前执行的历史侧标识 Q10，经标准校验反馈后第二次通过。后续判断使用通过校验的完整输出。

## 从 Parent 到有效 Update

| 决策 | Parent 及实际执行 | Original | 有效 Update |
|---|---|---|---|
| P6:1，找黄油刀。初始菜单列有 27 个抽屉、4 个台面 | Parent 偏好先查完合理类别。第一步去 drawer 1，第 50 步才到 drawer 26 | u2 建议在长串封闭容器前先试几个一步可查的开放表面 | REPLACE u2。第一步仍会提高开放表面的优先级，明确覆盖 Parent 的原排序，探查后回到同类单遍搜索。未指定某个台面 |
| P7:21，刚开完 drawer 7；P8:10，刚开完 cabinet 4 | 分别回到 drawer 1、cabinet 1。Parent 已要求该类查完就转向未查位置 | u1 强调禁止重扫，并偏向未接触类别 | WITHDRAW u1。当前两步上没有增加有证据的新选择。P7 在第 20 步已开完 drawer 7，因此 Preconditioner 的理由把较早和较晚的重扫混在一起 |
| 历史 M4，找锅，成功路线起步查 cabinet 1、2，后到 cabinet 9 | 实际前两个柜子均到达即揭示内容；第 18 步到 9 号柜，第 20 步拿锅 | u2 把约十二个同类封闭容器作为先查表面的触发条件 | 保留“约十二个以上”条件。归档初始菜单恰有 12 个柜子。若 Actor 按类别名估价，会推迟原成功开局。历史成功路线也查过台面，推迟是否影响终局仍未知 |

M5 的历史杯子退步出现在错过 countertop 3 的任务。它支持考虑开放表面的机会成本，未验证先试多少表面或何时覆盖 Parent。u2 的新选项与大致数量门槛均已出现在 Original 中。预条件的增量是明确规则冲突、优先级和返回原任务的条件，未明确处理 M4。对 M4 的完整菜单和柜子反馈为模型调用后人工核对，未额外提供给 Preconditioner。

本次止于一个有效 Update。表中规则选择为文本解读，只有 Parent 和历史侧行为是环境实测。

[Diagnosis 原始结果](../../../../../artifacts/methods/v24_5/v24_5_r05_original_effective/diagnosis/result.json) · [Preconditioner 原始结果和有效 Plan](../../../../../artifacts/methods/v24_5/v24_5_r05_original_effective/preconditioner/result.json) · [历史 M4 已有执行记录](../../../../../artifacts/methods/v24_4/v24_4_alfworld_progress_decision_20261107_202453/rounds/R03/candidate_runs/train_0024/record.json)
