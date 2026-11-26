# v28 SearchQA 实验协议设计

2026-11-02 新实验采用 [30 题批次联合设计](SEARCHQA_BATCH30_20261102.md)。下文保留为已中断的 15 题批次实验协议，不作为新配置入口。

2026-11-01：根据用户选择，合并 400 Train 与 200 Validation 为 600 题优化池；Actor 的任务执行方式、批次与 epoch 参考本地冻结的 SkillAdam SearchQA 主结果配置；训练／测试并发按用户要求设为 15／15，覆盖 SkillAdam 原生的 3／3；DeepSeek 模型与失败恢复沿用当前 v27；Gate 沿用成功数严格增加才接受。

本文件与 `experiment_plan.json` 是设计记录；可运行配置由 `config.py:campaign_config` 根据显式初始 Skill 构造。2026-11-01 已完成 Actor Prompt、评分、持久化 Actor、六次共享尝试、批次归档恢复及完整 EM-only Gate 身份校验；现已继续接入五模块 Prompt、执行证据、输出合同及 Memory；完整 campaign 训练调度、方法重试恢复和独立 Test 调度现已接入。没有启动训练或模型测试。

## 参数及来源

| 参数 | v28 设计值 | 来源 |
|---|---|---|
| 优化池 / 独立 Test | 600 / 1400 | 用户确认；已冻结数据 |
| 优化池顺序 | 原 Train 400 题顺序，接原 Validation 200 题顺序；不排序、不打乱 | SkillAdam SearchQA 保留 manifest 顺序及 sequential sampler |
| batch / epoch / 批数 | 15 / 1 / 40 | SkillAdam SearchQA 主结果参数 |
| Gate 样本 | 当前训练批的同一组 15 题 | SkillAdam same-batch；延续本方法 Parent/Candidate 配对约束 |
| Actor 训练并发 / Test 并发 | 15 / 15 | 用户明确指定；覆盖 SkillAdam 原生的 3 / 3 |
| Actor 轮数 / 工具 | 1 / 无 | SkillAdam SearchQA rollout |
| 输入 | 完整 context＋question；Skill 放入 system 的 skill_section | SkillAdam SearchQA build_messages |
| 回答解析 | 最后一个完整 answer 元素；无匹配时取最后非空行 | SkillAdam SearchQA extract_answer |
| 模型 | deepseek-flash，官方 chat/completions 接口 | 用户要求对齐当前 v27 |
| thinking / reasoning_effort / temperature | enabled / medium / 1.0 | 当前 v27 |
| Actor 输出上限 | 49,152，使用 max_tokens | 当前 v27；覆盖 SkillAdam 原生的 16,384 |
| 请求 / 连接超时 | 300s / 10s | 当前 v27；覆盖 SkillAdam 原生的 600s |
| SDK 隐式重试 | 0 | 当前 v27 Actor |
| Actor 总尝试 | 6，含首次；失败后等待 1.0×尝试序号秒 | 当前 v27 Actor |
| Gate | candidate_success > parent_success 才 ACCEPT，否则 RETAIN | 用户确认；F1 不参与 Gate |

SkillAdam 主结果的 max_iterations=60 是采样上限。600 题按 15 题分批顺序遍历一次，实际只有 40 批；不循环补足 60 批。v28 不因参考其调度而继承原生 Momentum、编辑预算、阈值 Gate 或连续失败早停。

原生 SkillAdam 的 EM/F1 阈值 Gate 不用于 v28。v28 在有效无更新或 Gate 拒绝时保留 Parent 并继续后续批次；执行不完整或归档损坏时停止并按恢复规则处理。

## 数据视图

- 原始冻结锁：`data/searchqa/v28_dataset.lock.json`。
- 新优化视图：`data/searchqa/v28_train600_v1/manifest.json`。
- 原始 `prepared_v1/{train,val,test}/items.json` 及冻结锁均未改写。
- 新视图保存 600 个 ID、每题 source_split/effective_split、40 个固定批次及 1400 个 Test ID，按 ID 读取已有正文，不再复制一套正文。
- 600 个优化 ID 唯一，且与 1400 个 Test ID 无交集；所有原始划分的 ID 和顺序与本地 SkillAdam 主结果清单逐项一致。
- Validation 已进入优化池，不能再称为独立选择集。Test 不参与演化、Memory 更新或 Skill 选择。

## Actor 与评分的任务适配

SkillAdam 的 SearchQA Actor 直接保留 context 字符串，不采用 SkillOpt 的 6000 字符截断。当前 2000 题最长 context 为 4820 字符，两者在这套数据上都不会触发该截断；v28 协议仍应显式采用完整 context，禁止默默改写原始输入。

Actor 仅接收 question/context/skill，不接收 reference answers。推理隐藏字段及失败尝试不进入五模块证据；原始响应留在执行审计归档。

评分组件已接入 SkillAdam SearchQA 的 normalized exact_match 和 best_token_f1，成功定义为 EM=1。用户再次确认 Gate 仅看 EM 成功数严格增加，F1 只记录和报告。两套上游虽都称 SQuAD 风格，但 SkillAdam 先去冠词、再按 Unicode 正则去标点，SkillOpt 先去 ASCII 标点、再去冠词；两者并非逐字等价。离线检查发现本地标准答案中有 3 条归一化输出不同，因此后续各对照方法必须使用同一个明确冻结的 scorer。环境验收用的 SkillOpt scorer 快照继续保留，不用于 v28 评分组件。

Actor 已按此前草案落实为 `v28_searchqa_actor_answer_element_words_v1`：保留 SkillAdam 的任务说明和 Skill 位置，将 Answer Format 中的字面 XML 示例改成文字描述元素；没有引入 LMB 的单选标签约束。原版模板仍保存在草案目录，当前写法未经过真实模型收益验证。实现与接口说明见 `src/skill_evolution/v28/README.md`。

## 失败恢复

Actor 与批次恢复已沿用当前 v27 的机制接入，并在入口以记录的源码哈希核对：

1. 首次、可重试技术错误、响应结构错误和 length 共用六次额度；length 响应先归档，再用原消息和原参数重试，不拼接截断内容、不提高额度。
2. 正常 stop 的回答只评分一次；答案错误、空字符串或格式不理想不触发基于评分的补答。缺失字段或非法响应结构仍按 v27 的技术错误处理。
3. 六次耗尽标为未完成，不补零分，不生成完整 Parent/Candidate 配对；resume 不重置额度。
4. 已有完整响应优先从归档恢复；已完成结果复用。归档损坏、完成标记缺失等依照 v27 校验边界停止，不能借恢复重复发请求。
5. 原始响应和已耗用 usage 保留审计；隐藏推理不进入优化证据。
6. 五模块的输出校验反馈、最多六次方法尝试和发布前恢复校验，已沿用 v27 接入 campaign 与方法阶段请求/重试执行器。它们与 Actor 尝试预算分开。

具体 HTTP 状态分类不在此重新定义，直接继承已记录的 v27 transport 实现。模块模型参数快照保存在 `experiment_plan.json` 的 module_calls_reference：Grouping/Editor 输出上限 16,384，Diagnosis/Preconditioner/Replay 为 32,768，均采用当前 v27 的 DeepSeek 参数。

## 当前实现与后续工作

- 初始 Skill：用户已选定 SkillOpt SearchQA 原始 initial.md，逐字复制至 `experiments/configs/v28_searchqa_initial_skill.md`，记录源码 commit 与 SHA-256；不执行 Stage0。
- 五模块方案已明确以 v27 为基线，仅做 SearchQA 任务与评分适配；不引入 v25.2 的两项新增 Prompt 要求，也不安排相应消融。设计稿见 `five_module_draft_20261101/DESIGN.md`；现已原样安装五份 Prompt，并接入输入投影、输出合同和训练执行证据。
- campaign/Test 编排、方法阶段六次尝试与反馈重试及发布恢复已接入。用户已确认沿用 v27，不设置 `context_window_tokens`；保留字符／字节保护，服务商 token 容量实测不作为配置完成前置条件。既定实验配置无剩余待补项，尚未启动真实实验。

`design_checks.json` 只证明数据和参数设计自洽，不代表上述功能已经实现或真实运行已经通过。

此前组件验收记录保留在 `artifacts/verification/v28_actor_scoring_20261101/validation.json`。本次 Actor/恢复/Gate 验收见 `artifacts/verification/v28_actor_runtime_20261101/validation.json`，涵盖六次共享额度、未知请求与已保存响应恢复、批次启动前全量归档审计、Test 隔离及 Gate 对原始响应和全部身份的验证。数据及 v27 源码不变，真实模型请求数为 0；不代表五模块和完整 campaign 已通过验收。


新增验收入口为 `scripts/verification/verify_v28_method.py`，报告写入 `artifacts/verification/v28_method_20261101/validation.json`。五模块层使用合成归档与手工输出串联，验证输入隔离、无 Update 数量上限、Plan/patch 合同、配对证据和 Memory 提交恢复；同时回归 Actor 与 Gate。未调用模型或启动训练/Test。已确认的设计目录保留历史快照，其旧源码保护哈希不再作为安装后状态校验；新报告独立记录安装 Prompt 和实现哈希。

完整调度的新增验收见 `artifacts/verification/v28_campaign_20261101/validation.json`，实现说明见 `CAMPAIGN_IMPLEMENTATION.md`；历史组件报告保留原范围。仅使用合成任务和响应进行故障注入与恢复验证，正式训练、真实 Test 和模型请求均未启动。
