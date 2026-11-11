# v24.4 R05 Diagnosis 与预条件快检

使用正式 R05 归档的十条 Parent 执行（6/10）和原轮 M1–M9。唯一改动是开发版 Diagnosis 的 FORM THE PLAN 三段。Preconditioner 沿用 parent_choice 版本。两阶段均在第一次调用通过校验。Original 只生成 u1，basis 自动选入 P4、P6、P7、P8、P10 五条完整轨迹及所引用的菜单。P2 在 Diagnosis 输入内，未被引用。Preconditioner 决定 WITHDRAW，编译结果为 null。没有进入 Editor、Candidate、Gate 或历史题复跑。

## 动作对照

| 决策 | 已发生的行为 | Original u1 的选择 | WITHDRAW 后的选择 |
|---|---|---|---|
| R05 P4:6 | 找杯子。离开 drawer 3 回到 drawer 1。菜单还包括 drawer 4、sidetable 1、diningtable 1。 | 按全程记录应避开 drawer 1，但 Actor 最近两步只有 open drawer 2、go to drawer 3。没有足够信息识别 drawer 1 是旧位置。 | Parent 已要求优先未查位置。同样没有增加当场辨认 drawer 1 的依据。 |
| R05 P8:14 | 找 soapbar。从已打开的 cabinet 1 又去 cabinet 2。菜单包括 shelf 1、toilet 1。最近两次移动抵达已打开的 cabinet 4 和 cabinet 1，但 cabinet 2 上次出现在更早处。 | 若将最近反馈识别为循环，会更倾向换类。文本没有说明怎样判定已经循环，也不能靠这两步确定所有备选位置的访问状态。 | Parent 允许换类，并要求避开已查未变位置，但没有在循环时优先换类的排序。 |
| R03 M6，Q8:2 | 从 countertop 1 去 diningtable 1，当场发现 apple，下一步拿取。 | 此时没有循环，换类可选，未给出优先去餐桌的理由。 | Parent 允许换类。 |
| R04 M7，P2:2–4 | 从 countertop 1 继续到 2、3，拿到 plate。R05 P2:2–3 也从 bed 1 继续到 bed 2 后拿到 pillow。 | 未出现循环，继续同类仍可选。“不要只穷尽一类”没有明确何时应中断。 | Parent 允许连续查新位置。M7 的历史退步没有归因到某个 Update。 |

与同一 Preconditioner 的旧 R05 快检相比，旧 Original 产生两条，撤回 u1、保留了“查同类第二处之前先换类”的 u2；这次没有单独提出这一优先级。在本次输出中，Memory 确实进入理由，M2/M6 支持换类可有收益，M3/M4 记录持续查新柜子的成功路径受扰。撤回避免了无条件换类，但没有学到能执行的新选择。Preconditioner 把全部行为称为 Parent 已覆盖，略过了 Original 里仅在循环时优先换类这一差别；该差别有没有可用触发信号，与它是否重复，应分别判断。以上动作对照为对规则和既有轨迹的核查，不是本次对新 Skill 的效果测量。
