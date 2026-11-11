# v24.4 决策证据提示词快检

两次快检共完成三次真实模块调用，均在首次回复通过校验，止于有效 Plan。R02 直接使用第二次复跑归档的完整十题 Diagnosis 输入，程序依新 Plan 的 basis 选择下游轨迹和菜单，Memory 取自同轮原调用。R05 新旧 Preconditioner 输入文件逐字节相同，含 Parent、两条 Original、六条引用轨迹、菜单及 M1–M9。两个轮次各自复用源 campaign 的调用配置。以下是对输出文字的决策推演，本次 Candidate 执行数为零。

## R02

[新 Diagnosis](../../../../../artifacts/methods/v24_4/v24_4_decision_evidence_checks/R02/diagnosis/result.json) · [新有效 Plan](../../../../../artifacts/methods/v24_4/v24_4_decision_evidence_checks/R02/preconditioner/result.json) · [实际下游输入](../../../../../artifacts/methods/v24_4/v24_4_decision_evidence_checks/R02/preconditioner/input.json) · [正式旧版](../../../../../artifacts/methods/v24_4/v24_4_alfworld_keep_after_regression_repeat_20261107_174810/rounds/R02/preconditioner/result.json) · [上次手动补 P8 版](../../../../../artifacts/methods/v24_4/v24_4_r02_repeat_add_p8_20261107_1815/preconditioner/result.json)

原 Diagnosis 引用 P4、P5、P6、P9。新 Diagnosis 提出一条 u1，自选 P4、P6、P8，其中 P8:24 是唯一的成功步骤引用。它把 P8 当作查新位置能找到目标的支持，并未用它指出餐桌与水槽在当时同属访问状态未知。它提出全局记录已查位置和内容，Preconditioner 的 REPLACE 明确当前关闭容器优先于导航，但仍要求追踪整局历史。R01 Memory 记录了类似访问集提案的 Defer，没有翻转事件，无法据此判断其效果。

| 决策 | 原有效规则与新有效规则 |
|---|---|
| P4:4 海绵 | 当前柜子 1 关闭且可打开，新文明确先打开。Parent 已有开柜条款，实际也开了。新理由举的 P4:3 是去柜子的导航步。 |
| P4:11 海绵 | 柜子 3 刚打开为空，菜单有直接打开柜子 6，也可回水槽，实际回水槽。新文知道从别处打开也算检查过，却没有给此时的 open cabinet 6 以优先级。这个区别也适用于理由引用的 P6:4，当时 Actor 已经直接打开柜子 2。 |
| P6:10 水壶 | 开完柜子 5 后实际去柜子 6。原正式版要求查多个同类后先换类。上次补 P8 版将换类偏好限定于可见循环。本次取消换类偏好，允许向前查，但仍依赖判定哪些位置尚未检查。 |
| P8:24–29 生菜 | 新文允许去餐桌，随后拿取、清洗、回来放置。第 24 步最近两步是去冰箱、去台面，两步窗口无法把餐桌与水槽按新旧排序。保留成功动作的可能性，尚无证据表明它提高了该动作的优先级。新文还把“所有位置已查完”和“已持有目标”并列为退出并转向处理/放置的条件，前者本身不足以执行处理。 |

## R05

[本次输出](../../../../../artifacts/methods/v24_4/v24_4_decision_evidence_checks/R05/preconditioner/result.json) · [相同的冻结输入](../../../../../artifacts/methods/v24_4/v24_4_decision_evidence_checks/R05/preconditioner/input.json) · [上次同输入的有效 Plan](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/preconditioner/result.json) · [上次实跑及历史对照](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_keep_20261107_1652/CANDIDATE_REVIEW.md)

- u1 从上次的 REPLACE 改为 WITHDRAW。Parent 已要求避开内容未变的位置，新增 inventory 兜底缺少行为收益的证据。上次明确以“最近一次看过内容”为基准，排除了把刚才开柜本身当作以后回访的理由。P8:9 实际从柜子 4 返回已打开检查过的柜子 2。撤回后由 Parent 处理这一选择，它关于“开过柜子算状态变化”的例外仍有解释空间。
- u2 仍为 REPLACE。上次优先在一个封闭容器与一个到达即可查看的位置之间交替，本次变为每种类别至少检查一次，再访问已采样类别中的下一个位置。这与冻结 Original 的首选顺序基本相同。Original 已有采完各类再继续的后续分支，补充例子和回访例外不构成这一分支的新修复。
- 当前 P6:3 开完抽屉 1 后实际去抽屉 2，两版均压低继续查抽屉的优先级。上次在检查一个开放位置后优先回到下一个封闭容器，新版要等其他类别均已采样。P10:2 实际从台面 1 去台面 2，新版立即压低台面 2。
- M2 的面包题从柜子转餐桌，M6 的苹果题从台面转餐桌。新文给换类优先级，因此兼容这两个成功选择，但未在多个新类别中指定餐桌。M3、M4 的成功路线需要继续查到柜子 9，新文在其他类别尚未采样时会打断同类推进。模型理由引用了这些退步，却用采完类别后的兜底回应早期选择。M7 记录了台面 3 的成功分支，归因为空，模型未讨论；同类连续查台面的动作同样会被延后。

适合保留为开发版本的变化是 Diagnosis 自选了 P8 并传递了完整轨迹。两个有效 Plan 均未通过设计稿中的实质行为审阅。R02 没有解决动作时访问状态未知的问题，R05 没有保护会被首遍换类优先级打断的历史成功路径。没有根据这次单次生成推断测试成功率。
