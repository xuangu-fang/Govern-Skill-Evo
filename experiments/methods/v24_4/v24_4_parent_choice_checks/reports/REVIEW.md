# 540 词 Preconditioner 的冻结输入对照

R02 复用上次由冻结 Diagnosis 生成的 Original 以及 P4、P6、P8；R05 复用六条引用轨迹及 M1–M9。初次请求的用户消息、输入文件和调用参数与对应旧版一致。两轮评估止于有效 Plan。R02 首次返回多余字段 reason_extra，程序按既有验证流程要求修正，第二次通过，有效文本与首次相同。R05 首次通过。

## R02

[旧有效文本](../../../../../artifacts/methods/v24_4/v24_4_decision_evidence_checks/R02/preconditioner/result.json) · [新有效文本](../../../../../artifacts/methods/v24_4/v24_4_parent_choice_checks/R02/preconditioner/result.json) · [决策时的观察和命令](../../../../../artifacts/methods/v24_4/v24_4_parent_choice_checks/R02/preconditioner/input.json)

u1 仍为 REPLACE。旧文强调先打开当前关闭的容器，再考虑导航。新文明确相邻容器被打开后，若发现目标，先去容器再拿。两版均依赖整局访问记录。Parent 本来已经要求目标可见可拿时立即拿取。

- P4:11。刚打开柜子 3，反馈为空，菜单提供 open cabinet 6。Actor 实际去了水槽。新文规定如何记录隔处打开的容器，以及发现目标后如何处理，却没有给当下的开柜动作优先级。
- P6:4。隔处打开柜子 2，只见盘子，任务要水壶。随后菜单已有 take plate 1 from cabinet 2 且无 go to cabinet 2。这里没有遇到目标；即使要拿可见物体，记录也不支持先移动是必要步骤。
- P6:10。继续去柜子 6 仍然允许，但首选“整局未查过”的判断没有局部依据。P8:24 可以去餐桌也可以去水槽，两者的访问状态都不在当时两步历史内。第 25 步可见生菜即拿已由 Parent 覆盖。文字没有在这些搜索决策上建立可直接执行的新增偏好。

## R05

[旧有效文本](../../../../../artifacts/methods/v24_4/v24_4_r05_success_priority/preconditioner/result.json) · [新有效文本](../../../../../artifacts/methods/v24_4/v24_4_parent_choice_checks/R05/preconditioner/result.json) · [冻结轨迹与 Memory](../../../../../artifacts/methods/v24_4/v24_4_parent_choice_checks/R05/preconditioner/input.json)

u1 均 WITHDRAW。u2 从 REPLACE 变为 KEEP，编译后的有效内容是完整 Original。旧文 prefer 换类，并要求尽量采样所有类别；新文明确要求未采样类别优先于已采样类别的第二个位置。首遍换类排序仍在。P6:3 从抽屉 1 去抽屉 2、P10:2 从台面 1 去台面 2 都会被延后。新理由声称 P6 未查水槽，但 P6:26 确实到了水槽。

M2（柜子到餐桌）和 M6（台面到餐桌）的成功搜索均得到换类偏好的支持；在多个新类别可选时，规则不会特别选中餐桌。M3、M4 都有在柜子 9 找到目标的成功分支。只要还有未采样类别，继续查下一个柜子的优先级就降低。采全类别后的继续规则只允许稍后回来。M7 中连续查到台面 3 也有同样的风险，M7 的翻转归因为空，仅作为行为证据。没有新的 Actor 执行来估计成败。

本次生成不足以支持把本版升级为训练默认。R02 引入了额外动作，但未修复实际搜索选择；R05 的决策标签改变，历史冲突仍在。
