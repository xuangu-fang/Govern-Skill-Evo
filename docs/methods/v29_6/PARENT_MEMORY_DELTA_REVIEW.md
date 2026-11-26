# parent_memory_delta_v1 实现与离线验收

最新运行状态：用户已授权当前新方案正式训练，并在训练成功后顺序运行最终 Test。已于 2026-11-05T03:35:25.223097+08:00 启动；[实时状态](../../../experiments/launches/v29_6_parent_memory_delta_v1_docvqa160_20261105_033511/status.json)。本次只运行新方案，实验参数不变，未设置定时任务。以下“未启动”表述记录此前设计/离线验收时点，原始成绩仍属于首次 v29.6。

状态：已将确认后的 Preconditioner／Editor Prompt 同步至设计与运行时；未启动训练或最终 Test，未调用真实模型。当前领域指南修订尚未实验，首次 v29.6 的 325/374 不能归属于当前版本。

## 设计与两处澄清

基线为 docvqa_domain_v1＋env_adaptation_v1。[完整设计](drafts/parent_memory_delta_v1/README.md)、[Preconditioner](prompts/preconditioner.md)、[Editor](prompts/editor.md) 已同步。

1. 将整合条件收窄为：
   > Where repeated affected guidance would otherwise leave the correction duplicated, conflicting, or incomplete, consolidate the relevant occurrences within this Original's scope.

   只处理本次修正所必需的相关位置，避免把发现重复变成额外编辑目标。
2. 已明确：Preconditioner 知道 Parent 完整覆盖且无合理行为增量时首选 WITHDRAW；Editor 空 patch 是实施阶段发现已满足要求时的兜底，不能作为主动 KEEP 已知冗余提案的理由。该说明写在决策段，原空 patch、编译及输出合同逐字保留。

其余沿用确认的设计：Parent 判断行为差异和旧规则处理，Memory 通过相关比较影响方向、范围与强度，必要实施要求进入 text。Editor 只调整两个职责段，落实指定处理并检查必要分支。

## 接入与版本追踪

- [六项 before/after](revisions/parent_memory_delta_v1/changes.json)：Preconditioner 四项，Editor 两项；两处澄清包含在 P4 内。
- [Preconditioner 相对此前领域修订的 diff](revisions/parent_memory_delta_v1/preconditioner.diff)、[Editor diff](revisions/parent_memory_delta_v1/editor.diff)。
- [修改前快照](revisions/parent_memory_delta_v1/before/)、[澄清前草案快照](revisions/parent_memory_delta_v1/draft_before_clarifications/)、[范围及哈希清单](revisions/parent_memory_delta_v1/manifest.json)。
- 当前相对 v29.5 的累计 diff 已同步；原领域修订 diff 仍描述领域阶段，不覆盖历史记录。

运行时沿用现有加载路径和配置身份，通过 Prompt 内容哈希区分修订。未修改身份校验或恢复机制，不迁移、续跑或重写历史 campaign。源码 Prompt 已变化，不得用当前文件代替旧实验的 implementation.json 与逐调用归档。

## 冻结范围

领域指南与其嵌入块、Diagnosis、Replay、Actor、初始 Skill、证据权限、机器输出合同、Memory、Gate、patch 组合、预算和恢复算法不变。所有运行 Python、测试代码、正式配置和既有实验结果保持原样。

160 题及原顺序、10×15＋10 批次、374 题 Test、模型、采样、32,768 token 预算、并发 15/60、重试与超时全部保持现有配置。没有新增模型阶段、全局压缩、独立规则计分或组合复测；没有同步 Brutus 后续补丁。

纯等价简化仍可能因 Gate 0/0 而 Defer。本修订仅改善有依据的行为修正及其必要整合，不保证全局去冗余、模型遵循或成绩改善。

## 离线验收

本轮验收：115 项既有 v29.6 离线测试全部通过（无失败、错误或跳过），配置与只读 CLI 预检查通过；722 项累计设计检查及 365 项澄清后静态审阅通过。305 个冻结文件哈希不变，网络/外部进程尝试为零。

当前结果见 [运行链路验收](../../../artifacts/verification/v29_6_parent_memory_delta_v1/validation.json)、[设计静态检查](design_validation.json)和[澄清后设计审阅](drafts/parent_memory_delta_v1/review_validation.json)。首版领域验收及环境适配验收保持原样。

静态验证先重放首次方法设计、领域修订及环境适配，再重放本次六项变更；同时核对两处澄清、来源快照、授权范围外文件、设计/运行时一致、证据与机器合同。历史阶段的校验仍对历史重建文本执行，没有把本次授权修改简单标成任意允许。

离线验收复用现有 v29.6 测试及配置核对，以合成响应运行，不请求模型。测试进程禁止网络连接与子进程，配置预检查禁止读取凭据、正式训练及 Test，也不创建正式 campaign。

可复核入口（均为离线验证）：

```sh
python docs/methods/v29_6/revisions/parent_memory_delta_v1/verify_offline.py
python docs/methods/v29_6/validate_design.py
```

本轮不将合成设计情境冒充已执行的模型行为测试；没有扩大现有 Test 的使用，也没有启动额外评估。
