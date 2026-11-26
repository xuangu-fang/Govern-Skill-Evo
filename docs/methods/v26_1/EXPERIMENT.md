# OfficeQA v26.1 实验配置与报告方案

状态：固定参数的设计方案，尚未实现或运行。机器可读参数见 [experiment_plan.json](experiment_plan.json)，不能传给旧v26 CLI。首轮比较回答“采用v29.4方法的整体方案在OfficeQA上的表现”，不单独识别Grouping、Gate或Editor预算各自贡献。

## 1 数据与初始化

| 项目 | 设计值与来源 |
|---|---|
| 数据版本 | OfficeQA Full，revision `763a8366abf2a3605c381d53586d844dc60fa756` |
| prepared_root | `data/officeqa/releases/763a8366abf2a3605c381d53586d844dc60fa756/prepared` |
| parsed_root | 同release下`upstream/treasury_bulletins_parsed`，使用其transformed及解析JSON |
| 优化池 | 原Train 50 + Validation 24 = 74，保留成员、内容与来源顺序；effective split=train，source_split在元数据保留 |
| 调度 | `10/10/10/10/10/10/10/4`，1 epoch，不重新采样、打乱或额外遍历 |
| Test | 原172题及其顺序，与优化池无ID交集 |
| 初始Skill | [正式v26初始原文](baseline/officeqa/initial_skill.md)，887字符含换行；不运行Stage0 |
| 初始Memory | `{"rounds":[]}`，不继承旧学习产物、缓存、响应或checkpoint |
| 模型环境 | 现有OfficeQA环境；原公共Runtime、工具及评分器；独立v26.1优化运行器尚待实现 |

准确的八批ID和172个Test ID均写入设计JSON，并与正式v26的config及release manifest核对。该JSON不包含测试题正文、答案或逐题错误分析。

旧`corrected_v2`语料与早期数据revision只作历史来源；它们不能与上述正式release混用。即使ID相同，任务内容、source_files/source_docs映射、初始页面和源资产也须遵循release。后续预检核对prepared manifest、来源文件、初始消息与当前任务；不能只比较ID或版本字符串。

## 2 Actor配置

| 参数 | 值 |
|---|---|
| model / endpoint | deepseek-flash / `https://api.deepseek.com/chat/completions` |
| transport | direct HTTP，无内层重试，无自动重定向 |
| thinking / reasoning_effort / temperature | enabled / medium / 1.0 |
| token_limit_field | max_tokens，保留公共接口max_completion_tokens到该字段的映射 |
| 输出预算 | 默认32,768；仅训练UID0007为65,536，Parent与Candidate一致 |
| Test输出预算 | 全部172题32,768；无UID0111或其他临时例外 |
| model rounds | 最多24，最终回答占一轮，无额外收尾轮 |
| tools | 原glob/read/grep、allowlist及错误返回；无独立工具次数上限 |
| workers | Train 4 / Test 4，题内轮次和工具顺序执行 |
| timeout / connect timeout | 300 / 10秒 |
| 请求额度 | 每模型轮最多6次总尝试，包含首次；等待2×已用请求次数秒 |

保留每页24,000/初始页面累计80,000字符限制；read最多4,000字符，grep20匹配、glob50匹配。原生read默认start=1、limit=80，整数转换、最小值处理、路径验证等保持原工具实现；这些不是新增Skill强制策略。工具只读当前题许可文件，不能访问prepared任务答案文件。

Actor重试沿用现有分类：超时/连接失败、408/409/429/500/502/503/504可在剩余额度重试，明确额度耗尽429除外；length、空响应及结构损坏按原协议处理；完整工具调用结构错误使用临时格式反馈。400/401/403、其他不可重试状态、拒绝等停止。合法工具参数值/文件访问错误作为正式观察进入下一轮。正常答错或无工具最终文本不按评分再生成。

24轮正常耗尽与六次生成失败分开报告。前者保持原生已完成空答案零分，后者不评分，不发布完整集指标。每轮理论上至多6次，所以一题理论上最多144次请求尝试，但不把这个理论上限当作正常预算消耗目标。

## 3 四模块配置

| 模块 | max_tokens | timeout_seconds | connect_timeout_seconds |
|---|---:|---:|---:|
| Diagnosis | 32,768 | 300 | 10 |
| Preconditioner | 32,768 | 300 | 10 |
| Editor | 32,768 | 300 | 10 |
| Replay | 32,768 | 300 | 10 |

四模块使用相同endpoint、deepseek-flash、thinking enabled、medium、temperature=1.0；每阶段六次总尝试，退避基数2秒。max_tokens包含供应商计入的推理token，不是输入窗口或保证普通文本长度。删除Grouping额度不转移给其他阶段；Editor相对旧v26由16,384提高到32,768是独立记录的配置变量。

方法层与Actor层的历史错误分类不同，不能为“统一”而静默改动。方法层沿用v26传输：HTTP401可重试；429/500/502/503/504在响应不含`insufficient_quota`或`quota_exceeded`时可重试；408/409等不自动继承Actor分类。连接/读取错误、响应损坏、length及识别出的输出合同错误使用本调用剩余额度，非输出来源/磁盘/版本错误直接停止。这个保留选择见[原方法传输](../../../src/skill_evolution/v26/transport.py)，不是对401行为的新建议。

合法no_change、KEEP、WITHDRAW、Editor null、Replay null不重采样；没有独立Update执行、候选择优重试或重组Selected额外Actor验证。已有完整响应优先恢复，耗尽不清零，无外层自动重启、自动预算提升、技术错误免计或单题补测政策。

输入保护沿用4,000,000字符/6,000,000 UTF-8字节，不设置context_window_tokens或Skill字符上限。实现前按真实初始输入和合成最大轨迹/增长Memory检查容量；这是请求保护，不等于服务端context保证。超限停止，禁止无记录截断、自动减批或压缩丢失证据。若需要改变批次或窗口，必须成为独立实验配置修订，不复用旧请求身份。

## 4 对照与效果解释

主要历史方法对照是完成八轮的正式v26运行：2轮ACCEPT、4轮RETAIN、2轮no_change。训练过程使用变化的Skill，不把累计Parent/Candidate成功数解释为最终固定Skill训练准确率。

旧独立Test在默认32,768下完成171题，UID0111技术未完成；之后单独以65,536重跑，合并报告118/172，EM=0.686046511627907、F1=0.6957364341085271。该值可作为**历史混合预算参考**，不能标作严格同预算完整对照。[原Test报告](../../../experiments/evaluations/v26_officeqa_official_test172_20261030_012818/report.json)、[合并报告](../../../experiments/evaluations/v26_officeqa_UID0111_65536_20261030_025803/combined_report.json)。

v26.1设计沿用原正式Test默认预算，不把事后UID0111补跑变成新自动规则；因此存在同样技术停止的可能。若172题未完整完成，报告未完成及pending，不用171题分母声称完整集效果，不以补零伪造完成。未来若另行选择统一65,536或预注册单题例外，应形成新预算方案和相应对照，不在本方案运行中自动切换。

方法来源的历史结果仅作背景：DocVQA v29.2 326/374、v29.4 323/374；SearchQA v28.1 1174/1400、v28.3 1187/1400。这些变化包含提示词/选择机制或预算差异；跨时间采样也未被控制。LMB v27.1无已完成效果结果可供本稿引用。SkillAdam等旧对照须先逐项核对语料、Actor、预算和重试政策，本次不重新运行它们。

已有Test结果及失败情况曾参与开发讨论。同集后续评估是开发背景下的探索性复评，不称作全新盲测。测试正文和答案不得进入Prompt、优化轨迹、Memory或初始Skill；只评最终Selected，不用Test挑checkpoint。

## 5 完整实验顺序

1. 独立实现完成，执行[离线验收](ACCEPTANCE.md)，包括完整合成74/172调度和真实数据只读预检；此阶段不构造真实传输或读取凭据。
2. 真实训练须独立启动，固定八批，从初始Skill和空Memory开始。每轮记录Parent、Original、调整、Effective、patch、Candidate、事件、Gate、Selected与提交状态。
3. 八轮全部完成才导出最终Selected及训练汇总。训练入口不自动启动Test，也不创建监督器。
4. 独立Test使用逐字相同的最终Skill及固定172题，冻结执行配置，允许原额度内恢复，完整覆盖后发布EM/F1；不更新Memory。
5. 效果分析区分真实观察、事件关联、程序决定和方法推断；不把合成测试或结构合法性当作语义效果验证。

## 6 必须报告的产物与指标

| 范围 | 必须记录 |
|---|---|
| 覆盖与身份 | 数据revision、完整ID/顺序、实际配置、Prompt原文/身份、运行器版本、初始及最终Skill、实际语料路径 |
| 训练 | 每轮完成状态、Parent/Candidate样本数和EM/F1、配对改善/退化、F1-only计数；短路与停止原因 |
| 提案与编辑 | Original/Effective数量、KEEP/REPLACE/WITHDRAW、空/null patch、实际diff；不以长度或数量代替效果 |
| 选择 | 每Update G/L及Retain/Reject/Defer/null；每条Retain的支持题数；归因/未归因的正负事件分别统计 |
| Selected | 与Parent/Candidate完整文本关系；新组合数量、比例；source=null时本轮分数留空 |
| Memory | 按轮追加的source_updates和事件、M编号、空事件轮、提交与游标；历史不改写 |
| Test | 完整覆盖时success_count/172、EM、F1；未完整时pending/errors及完整集指标null；训练和Test Skill逐字一致 |
| 成本 | Actor任务执行数、模型轮数、工具次数、物理HTTP次数、各类重试/length/结构错误、阶段耗时和总耗时 |
| token | 输入、输出、供应商reasoning/cache等细项，未知用量次数；reasoning已计入输出时不重复相加 |

如双方完整172题且预算政策一致，可报告逐题错转对/对转错、配对差异区间及预先指定的McNemar检验；单次探索性结果不宣称稳定因果收益。与旧混合预算结果比较必须保留预算标记。基线重跑、重复seed、新held-out和独立消融都是后续实验，不属于本稿已启动的工作。
