# P3-A2 新 Train 案例预注册

冻结于 2026-10-21T02:39:11.466718+00:00，早于任何本轮 Editor/Actor 输出。未调用新案例的模型、环境 reset 或读取其游戏内容/答案。

## 身份筛选与抽样

原始池只枚举 `/Users/didi/.cache/alfworld/json_2.1.1/train`，共 3553 个游戏文件。任务族取目录名，实例取规范路径和 trial ID，不以文件名不同认定独立。排除旧 39 条 Train edition 全部实例及仓库开发归档提及的实例，实际排除 39 个原始 Train 游戏。六族固定顺序为 pick_and_place_simple, pick_clean_then_place_in_recep, pick_heat_then_place_in_recep, pick_cool_then_place_in_recep, look_at_obj_in_light, pick_two_obj_and_place。

种子 230302；规范路径字典序排序；Python Random(seed) 每族不放回抽两条，第一/第二条分别放入批次 1/2；不足不补采其他族。共选 12 条，任务请求将由未来环境初始观察提取，本轮不猜写请求。

排重扫描 artifacts/methods、experiments/methods、docs 的元数据及文本身份，排除显式 Test/final 路径、原始 HTTP 响应、模型请求正文等。读 131888 份文件，每份至多前 131072 字节，11295 份存在未扫描尾部。另完整读取旧 Train items。只读身份，未访问最终 Test 数据目录或运行 Test。详细排除来源见 new_train_exclusions.json。

**暴露边界**：排除 R04/R05/R06 的规范实例（这些也位于不同原始 split），旧 Train edition 和扫描范围内 V23.2/V23.3/P1-R/Memory 来源可定位的实例；不能排除仅用自然语言、另一别名、截断尾部或仓库外记录的先前暴露。因此称“在已核查身份范围内未发现暴露”，不称绝对独立泛化集。

下面的 task_id 是本实验新建的局部 Train 标签，**不是**已有 39 条 edition 的编号；规范 gamefile 为权威身份。未来执行需用独立 manifest/合法输入适配，不能覆盖默认清单或冒用旧编号。

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

## 下一轮固定条件草案（本轮不执行）

两批均优先使用本轮 parent.md 与 memory_v3_integration_001/config/full_payload.json.memory（M1/M2/M3/M6/M7/M8/M9），不吸收本轮或新任务的后验响应。两个批次互不更新 Parent/Memory；若接口不兼容须在未来开跑前重新冻结，不能看输出后更换。

每批先在六条共同任务执行 Parent，再同一 Grouping、一次共同多行 Diagnosis，冻结 Original 后分别 V23 自由更新与 V23.3 Patch，随后同配置 Editor 和配对 Candidate Replay。相同当前证据与历史输入，单次生成不择优。

预算草案：每批 Grouping 1、Diagnosis 1、Preconditioner 2、Editor 2，共 6 次模块调用；最多 18 Episode（6 Parent+6 A+6 B）、900 Actor 决策。两批合计最多 12 模块调用、36 Episode、1800 Actor 决策；技术重试/模型/超时在未来单独冻结，当前未授权执行。合法停点缩减依赖调用，不增补样本。

评价：原生成功、步数、类别与实例覆盖、无信息重复、无效动作、精确目标、必要处理/数量/交付、实际 Skill Diff 和退化；分别报告技术有效性、更新构造及行为结果。保留全部预注册案例，不据胜负筛除；不用于最终 Test 调参。
