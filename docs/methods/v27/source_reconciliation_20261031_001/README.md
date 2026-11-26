# v27 历史来源与当前源码核对

2026-10-31。本次处理启动前检查中唯一的来源冻结失败，不修改实验参数、v27／SkillAdam
运行实现或旧版本源码，不启动实验。

## 原因与已核对差异

`draft_20261030_001/source_manifest.json` 是设计阶段工作区字节的历史记录。
其中 `src/skill_evolution/v25/config.py` 的历史哈希为
`0eb49350a75bd8724639afb901c0f39f240d7256d30fa5ffeccdfa1d9c9be2e5`；当前哈希为
`663df9baa746cf6a123ab9e151fd3feb2d55b202f83a75156e63ddc5c889efde`。

从旧实验冻结工作区找回与历史哈希完全一致的副本，保存为
[历史源码](v25_config.historical.py.txt)，同时保存[本次审查的当前源码](v25_config.reviewed.py.txt)
与[完整差异](v25_config.diff)。恢复来源路径及两份哈希记录于
[核对清单](reconciliation.json)。当前版本增加了 Review 启用／禁用选择，默认禁用，
按选择设置 Memory 发布策略，并在校验和 baseline 构造中保留这一选择。

v27 使用自己的配置和运行实现，已经固定禁用 Review。AST 检查确认不导入
v24／v25／v26 或 OfficeQA；五份运行 Prompt 与当前设计稿逐字一致，初始 Skill 与
SkillOpt 原生文件一致。因此上述旧版本文件变化不改变 v27 的实验行为。

## 验收规则

原始来源清单保持原字节，不把历史哈希替换成当前哈希。新增独立的审查清单：

- 原始清单本身须与本次记录的 SHA-256 一致。
- 65个来源中，64个继续要求当前字节与原清单完全一致。
- 唯一已审查变化须同时验证：历史副本匹配原哈希、当前源码匹配审查副本及新哈希、
  保存的 diff 与两份副本重新生成的 diff 完全一致。
- 任一来源后续再变、快照／diff 损坏、原清单改写或审查记录缺失，仍导致验收失败。
- v26 迁移底稿检查、v27 独立性、Prompt 和初始 Skill 检查继续保留。

实现仅位于测试与验收脚本，不进入模型请求或 Campaign 运行路径。报告单列
`source_provenance.json`，明确区分 `unchanged` 与 `reviewed_source_change`，不把后者报告为未变化。
新增3项测试，其中包含未来源码漂移、证据损坏和记录缺失的多个反例。

历史失败报告保留：此前52／53通过的结果没有被回写。本次重跑结果另存于
[v27验收](../../../../artifacts/verification/v27_offline_source_reconciliation_20261031/validation.json)、
[来源核对明细](../../../../artifacts/verification/v27_offline_source_reconciliation_20261031/source_provenance.json)
和[SkillAdam复核](../../../../artifacts/verification/lmb_skilladam_after_source_reconciliation_20261031/validation.json)。

## 本次结果

独立 `LiveMathematicianBench` 环境：v27 **56／56通过**，失败、错误、跳过均为0；
SkillAdam **29／29通过**。两套网络连接尝试和真实模型请求均为0，数据哈希未变。
107项设计映射继续按对应自动检查报告，不把历史人工样例算作本轮重新执行的语义验收。

[受保护文件核对](../../../../artifacts/verification/v27_offline_source_reconciliation_20261031/protected_sources.json)
确认本轮前后576个文件哈希不变，覆盖旧版本与v27运行源码、LMB接入、上游SkillAdam、
两份实验配置、环境锁文件和原始来源清单。本次变化只涉及验收逻辑、回归测试和文档证据。
此前阻塞全套离线验收的来源不一致已正式核对完成；未验证在线服务或真实模型效果，未启动实验。
