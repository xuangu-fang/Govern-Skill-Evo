# P3-C1 新 Train 预注册核验

本文件是原预注册的结项核验，不是看完 R05 后新选案例。权威清单为 [原 new_train_cases.json](../p3c1_r05_replay_001/new_train_cases.json)，协议为 [原 NEW_TRAIN_CASES.md](../p3c1_r05_replay_001/NEW_TRAIN_CASES.md)，排除来源为 [new_train_exclusions.json](../p3c1_r05_replay_001/new_train_exclusions.json)。三者保持不变。

冻结时间 2026-10-21 02:39:11.466718 UTC（北京时间 10:39:11），早于 A/B Editor 起始 02:40:56/02:41:40 UTC，亦早于本轮 Replay。抽样时未看到 Candidate 行为，本次未按已知输赢调整任何样本。

## 方法与复核结果

原始 Train 池 3,553 个规范 gamefile；排除旧 39 条 Train edition 全部实例及可检索开发历史身份，实际排除 39 个，余 3,514 个。规范路径字典序、六个任务族固定顺序、Python Random(230302) 每族不放回抽两条，首条进入批次 1、次条批次 2。每批六族各一例，共 12 个不同实例。本轮只枚举路径，使用**原冻结排除表**复现，逐项相同；未重新用新增报告进行后验排重。

原历史身份扫描读取 artifacts/methods、experiments/methods、docs 中符合条件的 131,888 份文件，每份最多 131,072 字节，11,295 份有未扫描尾部；排除显式 Test/final 路径及指定原始请求/响应文件。另完整纳入旧 Train edition 身份。因此仅能称“在已核查身份范围内未发现暴露”，不能排除别名、自然语言描述、截断尾部或仓库外记录中的接触。R04/R05/R06 为另一原始 split 的实例，不能冒充这里的新 Train。没有访问最终 Test 或读取这些新游戏的隐藏内容/解法。

下面 task_id 是未来独立实验的局部标签，并非旧 39 条 edition 编号；规范 gamefile 是权威身份。未来需独立 manifest/合法输入适配，不覆盖默认任务清单。实际自然语言任务请求待未来环境初始观察读取，本轮不猜写。

| 批次 | task_id | 任务族 | 规范 gamefile |
|---|---|---|---|
| 1 | `train:p3a2_1_01` | pick_and_place_simple | `json_2.1.1/train/pick_and_place_simple-Box-None-ArmChair-217/trial_T20190907_170746_281017/game.tw-pddl` |
| 1 | `train:p3a2_1_02` | pick_clean_then_place_in_recep | `json_2.1.1/train/pick_clean_then_place_in_recep-Kettle-None-Cabinet-5/trial_T20190909_042851_438667/game.tw-pddl` |
| 1 | `train:p3a2_1_03` | pick_heat_then_place_in_recep | `json_2.1.1/train/pick_heat_then_place_in_recep-Mug-None-CoffeeMachine-23/trial_T20190906_194121_936472/game.tw-pddl` |
| 1 | `train:p3a2_1_04` | pick_cool_then_place_in_recep | `json_2.1.1/train/pick_cool_then_place_in_recep-Apple-None-DiningTable-15/trial_T20190906_192043_926936/game.tw-pddl` |
| 1 | `train:p3a2_1_05` | look_at_obj_in_light | `json_2.1.1/train/look_at_obj_in_light-AlarmClock-None-DeskLamp-318/trial_T20190906_180754_637797/game.tw-pddl` |
| 1 | `train:p3a2_1_06` | pick_two_obj_and_place | `json_2.1.1/train/pick_two_obj_and_place-Watch-None-Dresser-205/trial_T20190907_181954_161870/game.tw-pddl` |
| 2 | `train:p3a2_2_01` | pick_and_place_simple | `json_2.1.1/train/pick_and_place_simple-HandTowel-None-CounterTop-421/trial_T20190909_145525_802579/game.tw-pddl` |
| 2 | `train:p3a2_2_02` | pick_clean_then_place_in_recep | `json_2.1.1/train/pick_clean_then_place_in_recep-DishSponge-None-Shelf-1/trial_T20190908_114111_289794/game.tw-pddl` |
| 2 | `train:p3a2_2_03` | pick_heat_then_place_in_recep | `json_2.1.1/train/pick_heat_then_place_in_recep-Potato-None-Fridge-30/trial_T20190907_193517_118086/game.tw-pddl` |
| 2 | `train:p3a2_2_04` | pick_cool_then_place_in_recep | `json_2.1.1/train/pick_cool_then_place_in_recep-Cup-None-SideTable-21/trial_T20190906_192855_164902/game.tw-pddl` |
| 2 | `train:p3a2_2_05` | look_at_obj_in_light | `json_2.1.1/train/look_at_obj_in_light-CD-None-DeskLamp-302/trial_T20190907_154641_341365/game.tw-pddl` |
| 2 | `train:p3a2_2_06` | pick_two_obj_and_place | `json_2.1.1/train/pick_two_obj_and_place-KeyChain-None-SideTable-322/trial_T20190909_034001_524438/game.tw-pddl` |

## 保留原下一轮方案，不执行

两批固定当前 R05 Parent 与 Memory 时间边界：`p3c1_r05_replay_001/parent.md`，以及 `memory_v3_integration_001/config/full_payload.json.memory` 的 M1/M2/M3/M6/M7/M8/M9；按 Memory v3 渲染。不得吸收本轮 Replay 后验知识、M10 或两批之间的新响应。两批之间不更新 Parent/Memory。

每批六条任务先共同执行 Parent，再一次 Grouping、一次共同 Diagnosis；冻结同一 Original、当前执行证据、command_sets、背景和 Memory。A/B 分别一次 Preconditioner、一次 Editor，然后在相同六条任务执行两个 Candidate。保持同一 Actor/Editor 配置与单次生成不择优；合法停点减少后续调用，不补采其他任务。

原预算草案：每批 6 次模块调用（Grouping 1、Diagnosis 1、Preconditioner 2、Editor 2），最多 18 Episode、900 Actor 决策；两批 12 次模块调用、36 Episode、1,800 Actor 决策。模型路由、超时、技术失败/重试规则仍需在未来执行前冻结。本轮重启授权不能自动扩展为新批次无限重试授权。

评价保持原生成功、步数、类别/实例覆盖、无信息重复、无效动作、精确目标、必要处理/数量/交付、实际 Skill Diff 与新增退化；保留全体预注册案例，不据胜负筛除。分别报告更新构造、技术有效性与行为结果，不把新 Train 称为最终 Test，也不用于 Test 调参。

本次新任务模型调用 0、环境 reset/Replay 0；[只读复现结果](train_preregistration_check.json) 已归档。下一轮尚未启动。
