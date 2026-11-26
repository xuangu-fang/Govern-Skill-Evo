# V25.1 Prompt 与两组对照审阅稿

状态：**草案，等待用户审阅；未安装、未发起模型请求、未启动训练或测试。**

本目录把 V25.1 定义为：在共同 Actor 环境说明及关闭 Verify/Repair 的条件下，只修改 Preconditioner 对当前 Update 的判断要求。V25 对照组使用原 Preconditioner。与历史 78.21% 的结果相比，两组都采用了新的共同条件，因此历史结果不能代替本次对照组。

## 阅读顺序

1. [共同 Actor 完整 Prompt](/Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v25_1/prompt_review_20261030_001/common/actor_system.md)
2. [共同 Actor 与环境说明的完整差异](/Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v25_1/prompt_review_20261030_001/diffs/01_common_actor.patch)
3. [V25.1 Preconditioner 完整 Prompt](/Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v25_1/prompt_review_20261030_001/v25_1/preconditioner.md)
4. [Preconditioner 完整差异](/Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v25_1/prompt_review_20261030_001/diffs/02_v25_1_preconditioner.patch)
5. [对照定义、接入边界与验收方案](/Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v25_1/prompt_review_20261030_001/experiment_plan.md)

`baseline/` 保留本次已完成 SheetBench 实验的六份原始 Prompt。`common/` 是两组共用的拟议内容；`v25_1/preconditioner.md` 是唯一组间算法 Prompt 差异。差异文件的标签指向本审阅包，不是运行目录；没有将这些补丁应用到运行源码。

## 基准选择

实际基准是 `v25_skilladam_upstream_actor_prompt_20261030_001/scheduled_run/v25/frozen_workspace` 中的实验源码。当前工作区的 Actor system/initial/runtime-feedback 模板和消息渲染函数与它不同：工作区模板仍包含预算说明。当前工作区与冻结版本的 Preconditioner、初始 Skill 和 execution_context 文件相同。

因此，不能把新增的“关闭审核”JSON 直接交给当前工作区入口，就认为已经复现了本稿的共同 Actor。JSON 没有冻结全部 Prompt 和消息渲染代码。后续批准接入时必须明确加载本稿，并验证最终实际消息；本次未创建可启动的新实验入口。

## 共同 Actor 的修改

| 项目 | 原实验输入 | 本稿拟议输入 | 理由 |
|---|---|---|---|
| 路径 | 要求使用运行器提供的路径，但初始 Skill 含重赋值示例 | 明确不得重赋值；Skill 中的路径占位符指运行器提供的变量 | 与实际格式校验一致 |
| 执行方式 | 要求返回代码；初始 Skill 又描述探索、写文件、执行 | 明确由外部执行器运行，探索和自检写进程序 | 避免暗示存在交互工具 |
| 预览与文件 | 提醒预览可能截断 | 保留提醒，并说明程序能读完整原输入、每次执行重新开始 | 说明能力及文件边界 |
| 反馈与结束 | 没有完整说明 | 只返回格式、运行、输出文件错误；有效文件提交后不返回评分反馈 | 区分正常提交与任务正确 |
| 公式 | 没有说明不重算 | 说明不自动重算、评分读取缓存值、写公式不会计算缓存 | 公开基础环境事实 |
| 公式交付要求 | 要求完成任务 | 明确缓存事实不意味着可以丢弃任务明确要求的公式或其他交付物 | 不把评分适配当作通用答案策略 |

共同 Actor 不加入 token 数、剩余次数、超时数字或预算分配策略。实际预算及错误反馈机制保持原配置。优化器的 `execution_context` 仍保留预算事实，因为它用于判断修改的可执行性，不会直接作为 Actor system Prompt 注入。

Actor user 模板、运行错误反馈模板、初始 Skill 全文不变。Library Selection、原输出要求等也保留，避免把额外策略调整混入此次共同说明。初始 Skill 中的 `Explore / Execute / Confirm` 被解释为程序与执行器的工作，而不是额外工具；确认也不意味着能读取参考答案。

公式缓存说明只公开读取方式，没有提供公式求值器，没有改变评分，也没有规定所有任务必须写字面值。对明确要求公式的任务，原环境的交付要求与评分能力之间仍可能存在张力；本稿不借 Prompt 偷换任务要求，也不承诺仅补充说明即可解决全部公式题。

## V25.1 Preconditioner 的修改

| 位置 | 具体变化 | 保留的自由度 |
|---|---|---|
| 第 2 节，经验匹配 | 将 Memory 中具体的编辑—行为—结果关系对应到当前 Update；区分未实现、未触发与实际效果；反例不能自动推出相反默认规则 | 可以直接使用报告的 Knowledge，不要求重新追查全部历史 |
| 第 3 节 S | 只有不确定性影响操作或适用性时，才需决定如何改变边界；必要条件落实进 patch | 不因因果未确认就自动缩小规则；允许有依据的泛化 |
| 第 3 节 C | 当前 Update 与 Parent 的覆盖、冲突和优先级必须明确；只处理与当前更新有关的协调 | 不扫描 Parent 历史问题，不增加修复队列 |
| 第 4 节，决策与输出 | 用原 `reason → change → patch` 表达证据到实际行为的关系；替换重复说明 | 允许 KEEP，不要求每条引用都产生修改，不增加输出字段 |

第 1 节、D 的定义、Explicit Keep、最终联合一致性检查，以及第 5—7 节的 patch、引用、Checks 和 JSON 输出契约保持原文。重点是让原机制更稳定地执行，而不是增加一个审核层。

新 Prompt 没有插入训练任务编号、特定表格答案、测试案例或业务规则。历史案例只用于审阅解释和将来的行为检查。

关闭 Verify/Repair 后，Preconditioner 也不承担全面事实审核：仅基于现有输入处理与当前 Update 相关的明显矛盾与适用条件，不调用额外模型，不检索未提供的轨迹。

## 建议重点审阅

- 共同 Actor 是否充分说明执行事实，同时避免指定任务解法？
- 是否接受初始 Skill 保持原文，以共同 system 说明澄清其工作流与路径语义？
- V25.1 是否只约束当前 Update，而且仍允许合理探索、KEEP 和较大范围的有依据修改？
- 是否接受两组都关闭 Verify/Repair，并且只把 Preconditioner 正文作为组间变量？

用户审阅通过后，才进行版本注册、独立运行目录与源码冻结、实际消息核对和必要的离线接入验证，再启动明确批准的对照。当前审阅稿没有创建自动启动任务。
