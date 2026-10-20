# P0：Diagnosis Goal—Update边界基线

本阶段不调用模型。正式V23只读，默认配置不变；此前五版Preconditioner候选均不进入本次方法。目标是隔离上游Diagnosis的目标、策略与效果承诺问题，再决定P1自身是否达标，不测试下游或行为性能。

## 实现与数据流

`grouping.load_grouping`提供完整Parent、当前轨迹、动作候选、背景和Grouping；`diagnosis.diagnosis_input`只装配parent/command_sets/runs/grouping。Diagnosis无Memory输入。返回decision/reason/plan；revise的Plan严格包含goal/updates/checks，Update为id/text/basis，Check为id/update_ids/question。no_change和need_evidence均plan=null。解析／校验只验证结构和证据引用，不判断自然语言策略质量。

Preconditioner读取原始Plan，并独立加入当轮Memory；其输入选择Plan引用的完整轨迹。已有编译器按Adjustments替换Update、保留或替换Checks，直接继承Original goal。没有goal_override。本轮保持此接口，也不向Diagnosis泄露Memory、旧Preconditioner输出或旧Effective。

原Diagnosis Prompt已要求Goal不应不必要地承诺一种实现策略，且已有Actor能力限制。R06输出没有可靠遵守：这不是要求缺失，也不能简单归因于Memory，因为Diagnosis并未读取Memory。现有V23.2局部工具可用显式prompt_path加载独立Diagnosis模板；旧src/v23_2/diagnosis_prompt.md属于第一项历史实验，本次不改它，也不设为默认。

## 固定材料和来源

`config/cases.json`引用原始Diagnosis attempt的input/messages/request/run/response/diagnosis、对应Grouping、round_input以及调用前已生效的容量恢复记录，并保存SHA-256。不从下游Effective重建输入。`run.py p0`核验Grouping→Diagnosis交接、原始请求消息、解析结果、Parent快照和原配置；`run.py check`可离线重验。`config/history_receipt.json`核对此前五候选共15组有效输出与原六版本对照一致，仅作为离线背景。

| 案例 | 原始Diagnosis | Grouping | 当时容量字符／UTF-8字节 | 本次重点 |
|---|---|---|---|---|
| R04 | attempts/001 | attempts/003 | 1,000,000／1,500,000 | 保留精确目标、温度操作、计数与交付；避免空泛化 |
| R05 | attempts/001 | attempts/002 | 4,000,000／6,000,000 | 当前位置遗漏／循环不直接证明固定类别调度或排他回访规则 |
| R06 | attempts/001 | attempts/001 | 4,000,000／6,000,000 | Goal中的ordered memory-independent sweep、Update中的穷尽和guarantee |

三轮均deepseek-flash、temperature=1、Thinking enabled、reasoning_effort=medium、stream=false、max_tokens=16384、timeout=300秒。以原Diagnosis request和run为准，不套用后续Preconditioner容量；R04的第二次容量恢复发生在其Diagnosis完成之后。本次严格最多3次实际HTTP请求，每轮一次，不自动重试；任何技术失败归档停止该案例。

原始文件位于`artifacts/methods/v23/v23_alfworld_formal_001/S1/rounds/{R04,R05,R06}/diagnosis/attempts/001/`。原Memory／Preconditioner／Effective及五候选的全文对照见[已有归档](../../v23_2_response_grounded_001/reports/OUTPUTS.md)，推导证据见[离线报告](../../v23_2_response_inference_analysis_001/reports/REPORT.md)。只做离线解释，P1实际模型消息与原Diagnosis user消息完全一致。

## 旧结果与证据边界

| 案例 | 旧Goal／具体策略 | 已有问题及有价值内容 |
|---|---|---|
| R04 | 扩展heat-then-place／multi-instance；u1精确对象、heat一次后直送；u2计数和扩大覆盖 | 目标总体围绕行为，但systematic search已略带方法；保留温度与交付很重要。原Diagnosis没有完整的“heat动作可用时持物直接执行”细化，那是后续Preconditioner贡献，不可混为原始基线。当前P2:6/P3:7/P4:5动作候选可独立支持该细化 |
| R05 | Goal含sweep uninspected families；u2跨类single-pass、避免穷尽一类 | 当前P6/P8循环、P6晚段长扫drawer和P10晚到diningtable，支持覆盖探索；不证明某个固定调度最优。M6的countertop3遗漏不能输入本轮Diagnosis，也不能要求它知道该历史实例 |
| R06 | Goal指定ordered memory-independent sweep；u2类内升序穷尽、换到未查类别、guarantee progress | Grouping仅界定覆盖／循环问题。Parent已有rather than exhausting一类的指导；当前P3失败不单独证明反向穷尽更好。u1有具体温度动作依据，双物体与交付属于需保留行为 |

旧Preconditioner研究显示：alignment识别调度差异但加入采样终止；construction和grounded主要修正信息源、保留穷尽；symmetric和calibration改变安排但有排序／尺度／强度问题。该现象支持本轮回溯上游承诺，不证明某版策略必然无效。所有历史联合编辑和单次输出均不能提供独立因果结论。

## 调用前统一评价标准

以下为人工证据评价，不是模型字段、自动评分或关键词黑名单。

| 标准 | 判断依据 | 不应误判为成功／失败 |
|---|---|---|
| A Goal | 是否表达要改善的行为、保留行为及必要约束；没有不必要的实现绑定 | 必要任务动作词不自动是实现绑定；Goal过于空泛也不合格 |
| B 具体策略 | Update明确条件、实际操作、范围及依赖，能够由Editor理解 | 删除所有具体方法不算成功；新策略未验证不自动错误 |
| C 承诺与证据 | 区分当前事实、行为问题、合理新假设、无据强制要求／效果保证 | 明确操作可以承载假设；有问题动机不证明所有附带要求合理 |
| D 职责边界 | Goal不把某项Update指定为唯一实现；具体方案留在Update可由后续调整 | 不新增goal_override；不声称下游实际改善，因为本次不调用 |
| E 新退化 | 检查有效策略丢失、Goal泛化、不可执行信息依赖、无据顺序／次数／范围及必要条件缺失 | 不以字数、Update数或某个词消失判断效果 |

R04关注当前证据中的温度操作条件、精确目标、计数与交付；R05关注当前具体遗漏与循环，不强求某种换类顺序；R06关注Goal绑定与Update效果保证，允许有依据的有序扫描或其他候选。逐条引用实际text与输入事实；不因模型reason自称合理而通过。

P1验收须同时覆盖A–E、仍有具体可执行策略、未把预期写成证明、无明显温度策略退化及新增无据强制要求，且契约和其他模块不变。单次结果只能说明固定材料下的局部现象。若失败，保留原文和不确定性，不继续搜Prompt，不自动进入P2。
