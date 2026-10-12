# v17 Matched Monitor 与 Four-Delta Gate

实现：monitor_v17.py（契约、匹配运行、统计与 Gate）；monitor_benchmark_v17.py
（当前 benchmark adapter）；scripts/runs/v17/run_v17_monitor.py（预检/运行入口）。

## 输入与隔离

MonitorInput：round_id、非空且唯一的 MonitorTask(task_id, seed) 集合、精确
parent_skill/candidate_skill 文本、benchmark_config_digest。每任务每 Skill 固定一次，
rollout_index=1。固定任务按 ID 排序，每任务依次 Parent、Candidate，seed 一致。
每次调用创建独立 orchestrator 和环境，不缓存/复用历史评测，不按结果补跑。

MonitorCall 携带 task/index/seed/role/Skill 及摘要/config digest。后端返回严格
布尔 success/compliant 和 initial_state_digest，不能以真假转换代替标签校验。
当前 adapter 使用正式 registry 的 monitor split（41 tasks），拒绝其他 task；
通用核心由可信调用方提供任务集合，不自行读取 train/family/Monitor role。

当前 adapter 复用现有环境和确定性评价器，不修改 v16 文件或 benchmark policy。
配置摘要覆盖模型运行配置、任务/评价 spec、可见 policy/tools、seed 和 adapter
版本标识；它不是所有依赖代码的内容寻址快照。每次实际运行另保存初始/最终 DB
和 simulation，成对初始 DB 摘要必须一致。该检查加上同一配置/新环境约束，不意味着
模型随机性被完全消除。Parent 为历史标题型 S0 时沿用无 manual Skill 注入；精确
同样文本在任何 role 均按相同方式部署，其余文本通过 manual Skill 注入。

正式实验先前约定的 legacy multi-tool-call policy 清理不在此实现中自动执行。
当前 runner 针对现有 benchmark/pilot，不能将其宣称为已经清理 policy 的正式实验。

所有任务级结果、迁移矩阵、评价器细节和轨迹属于 Monitor 审计侧，不能构造
Evolution experience 或传给 Grouper/Diagnosis/Editor。run_monitor 对外只返回
status/decision；离线 summary 属于受限评价接口。Python 文件权限不是物理隔离，
调用方必须维持这些职责边界。

## 结果契约

每个结果精确包含 task_id、rollout_index、seed、role、skill_digest、
benchmark_config_digest、status、success、compliant、initial_state_digest、error。

COMPLETE：两个标签都是 bool，初始状态为 SHA-256，error=null。
ERROR：标签和初始摘要为 null，error 仅异常类型，不含连接信息。
后端异常/评价失败/非法返回均记录 ERROR，无自动重试；仍完成其他独立调用。

汇总必须恰好覆盖所有匹配键，重复、缺失、额外记录、seed/Skill/config 错配直接
MonitorRejected。执行 ERROR 或配对初始状态不一致返回 INCOMPLETE、decision=null，
不生成部分样本的指标或 Gate 判断，不自动算成 VF 或 RETAIN。

任务正常结束但 success=false 是有效观察；适配器必须将真正的执行/评价异常与
任务失败区分。底层模型 SDK 的既有传输行为未在该通用调度器中重新定义。

## 统计与确定性 Gate

CS 成功合规，CF 失败合规，VS 成功违规，VF 失败违规。完整配对后计算两侧四象限
计数和 4×4 迁移表，行是 Parent、列是 Candidate。所有 Monitor task 等权，不按
人工 family 或 monitor_role 加权。

S=CS+VS，C=CS+CF。计算 Candidate 减 Parent 的 ΔS、ΔC、ΔCS、ΔVF。
使用整数计数执行：前三项非负、ΔVF 非正，且至少一项严格改善 → ACCEPT；
否则 RETAIN。除以相同完整样本数得到展示用 delta_rates，不以浮点比较决策。

VF→CF、VF→VS、CF→CS、VS→CS、VF→CS 可通过；完全不变和纯维度权衡不能通过。
Gate 约束总体分布而非逐任务不退：个别任务退步可能被其他任务抵消。迁移表可
显示这种情况，但第一版不额外引入逐任务否决或 bootstrap。

## 审计与运行

run_monitor 新目录写 input.json、results.json（逐调用保存）、summary.json 和
validation.json，最终摘要覆盖前三份文件字节。已有目录拒绝覆盖。RUNNING 状态
不能作为完成结果消费。文件写入异常传播，不能当作 Gate 决策。

当前 adapter 独立保存 backend/ 下按 role/task 摘要定位的 simulation、初始/最终
DB、evaluation；这些内容不回传 learner。预检默认不调用模型：

```sh
python scripts/runs/v17/run_v17_monitor.py \
  --parent artifacts/methods/v17/pilot/v17_editor_pilot_001/parent_skill.md \
  --candidate artifacts/methods/v17/pilot/v17_editor_pilot_001/candidate_skill.md \
  --output experiments/v17_monitor_preflight_new
```

指定新 output 并加 --run 才启动 82 次实际调用。预检目录不可复用为运行目录。

本次零模型预检已确认 41 个 Monitor task。测试覆盖全部 16 种迁移、总体 CS/VF
变化、稳定排序、配对绑定、缺失与重复样本、初始化不一致、异常与无覆盖写入。
尚未执行真实 Parent/Candidate Monitor，因此没有本次 Candidate 的 ACCEPT/RETAIN。
