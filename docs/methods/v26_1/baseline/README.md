# OfficeQA v26.1 设计来源快照

本目录固定2026-11-04设计时的来源原文。`method/`是四模块方法底稿；`officeqa/`是已完成v26的配置、初始Skill、正式release manifest及现有执行/证据/评分源码。Python文件是只读来源副本，不是v26.1实现，不得当作新运行入口。

精确来源与副本对应见[source_files.json](source_files.json)。Actor无Skill基础协议和工具schema由rollout.py的字面量提取；源execution_context_template仍保留原模板，正式四份设计Prompt已完整展开，不能把该模板当成可发送的system。

方法规范：Diagnosis/Preconditioner来自v29.4；Editor/Replay来自v29.4实际沿用的v29.2。补丁、Gate、Memory算法来源路径在[来源映射](../source_map.json)登记。v28.3/v27.1仅为迁移与验收参考，未复制它们的任务输入或运行设置。

训练基线：`experiments/campaigns/v26_officeqa_official_train74_epoch1_20261029_230230`。release为`763a8366abf2a3605c381d53586d844dc60fa756`，不使用早期corrected_v2。来源配置含旧七模块身份但knowledge_review已禁用，不能作为新四模块可执行配置。

manifest保留原资产身份字段以定位数据，不把它变成新全仓库哈希门槛。当前执行仍需原OfficeQA来源验证；常规历史恢复范围由新合同定义。后续上游变化不能自动改写这些快照或已审阅Prompt。
