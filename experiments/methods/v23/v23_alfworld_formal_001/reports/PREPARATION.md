# V23 ALFWorld 正式实验准备报告

日期：2026-10-19（Asia/Shanghai）。结论：**READY（仅准备完成，尚未启动）**。

57 条优化任务、134 条 Test 均完成真实身份和本地路径核对。六轮 10/10/10/10/10/7；S0/S1 配置已冻结；离线回归 **531 passed、19 subtests passed**。没有模型请求、Actor 执行、ALFWorld Episode、Test 评价或正式 Campaign 初始化。`artifacts/methods/v23/v23_alfworld_formal_001/` 尚不存在。

## 1. 来源与研究设置的边界

- [SkillAdam 论文 §5.3](https://arxiv.org/html/2609.08944v1#S5.SS3)：合并 Train 与 Selection、保留 Test、单遍优化、seed=42、同批对照。论文使用 GPT-5.5 和轨迹初始化 Skill，本次 V23 沿用 deepseek-flash 并从 null 开始，并非原方法复现。
- [SkillAdam 官方实验 profile](https://github.com/ruc-datalab/SkillAdam/blob/b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1/skilladam/experiments/main_results.json)：ALFWorld 为 39/18/57/134，batch=10、6 轮、`include_partial_final_batch=true`、`sampling_strategy=sequential`、`shuffle_optimization_pool=false`。
- [SkillAdam 官方数据 profile](https://github.com/ruc-datalab/SkillAdam/blob/b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1/skilladam/data/profiles/alfworld_main_results.json) 与 [SkillOpt 公开清单](https://github.com/microsoft/SkillOpt/tree/ae2f766ea02cb41855b6f8f10e38e10264ce0a1b/data/alfworld_path_split)：逐条比较 ID、gamefile、task_type 及数组顺序，三个 split 全部相同。不是仅凭数量相同推定。
- 2026-10-19 固定 SkillAdam commit `b6c9640f7a9e0d5e3a500c25bc4e6369eeca78f1`；SkillOpt commit `ae2f766ea02cb41855b6f8f10e38e10264ce0a1b`。GitHub API 遭遇 rate limit 后，使用公开 Git HEAD 与固定 revision 的原始文件/只读 checkout 完成核对。来源副本与 provenance 见 [data/source](../data/source/)。不含游戏 payload 的公开清单保留原样。
- 本地原清单来源 commit `343db229dbd5ddaf9df6b1d5540d8bcdb2604d5c`，本次重新获取的当前公开清单与其逐条一致。源目录 `benchmarks/alfworld/editions/skillopt_39_18_134/` 未改写。

**顺序决策已经用户确认：采用官方顺序，不执行 shuffle。** 官方 CLI 合并 Train 后接 Selection，加载器在各 split 按 ID 排序；本清单的原顺序本来就按 ID 排序。官方 sampler 按顺序切 10 条、保留不足一批的尾部。实际代码片段已保存于来源目录。seed=42 保留用于环境与受控随机操作，不声称它保证 LLM 确定性。初始请求中的 seed=42 shuffle 备选约定没有启用；这不是遗漏，也没有同时保留第二套运行顺序。

当前公开 profile 给出可复现配置，不能据此声称复原作者历史 API 输出。V23 的 null 初始化、严格成功数 Gate、Memory/Preconditioner、无轨迹压缩均是本项目机制；官方 SkillAdam 的初始化、宽松 Gate、压缩等没有引入。

## 2. 本地数据与隔离核验

- 数据根：`/Users/didi/.cache/alfworld`，目录版本 `json_2.1.1`。
- 运行 Python：`/Users/didi/miniforge3/envs/alfworld/bin/python`。
- 安装版本通过 package metadata 静态读取：alfworld 0.4.2、textworld 1.7.0、numpy 1.26.4、requests 2.32.5。
- Train 对应 `json_2.1.1/train`；Selection 的原 split 为 `val`，对应 `valid_seen`；Test 对应 `valid_unseen`。
- 全部 191 个 gamefile 存在，且 `pddl_domain`、`pddl_problem`、`grammar` 为非空字符串；相邻 `traj_data.json` 与 `initial_state.pddl` 均存在；任务类型、trial 身份与元数据吻合。没有启动 TextWorld 或验证动态可解性。
- 191 个 ID 与解析后的 gamefile 路径均唯一；优化池内部重复 0、Test 内部重复 0、优化/Test 交叉 0；缺失或无法映射 0。
- 完整实际映射见 [local_mapping.json](../data/local_mapping.json)，数据检查见 [verification.json](../data/verification.json)。不存在按数字后缀猜测任务对应关系的步骤。

| 任务类型 | Train | Selection | Optimization | Test |
|---|---:|---:|---:|---:|
| look_at_obj_in_light | 5 | 3 | 8 | 18 |
| pick_and_place_simple | 7 | 3 | 10 | 24 |
| pick_clean_then_place_in_recep | 9 | 4 | 13 | 31 |
| pick_cool_then_place_in_recep | 6 | 3 | 9 | 21 |
| pick_heat_then_place_in_recep | 7 | 3 | 10 | 23 |
| pick_two_obj_and_place | 5 | 2 | 7 | 17 |
| **合计** | **39** | **18** | **57** | **134** |

## 3. 已有开发接触

按 gamefile 核对 `artifacts/methods/v22` 与 `v23` 下 778 份 trajectory.json，实际模型请求/响应记录与公开清单匹配。重复拷贝不重复计算游戏数：**57/57 条优化任务都有 V22 接触记录，12 条另有 V23 接触记录**。中断执行也算接触，不伪称为完整成功执行。

完整交集是 `train:0000–0038` 与 `val:0000–0017`。V23 交集：`train:0001, 0002, 0006, 0007, 0012, 0013, 0014, 0015, 0016, 0017, 0022, 0028`。逐游戏、逐来源路径见 [development_overlap.json](../data/development_overlap.json)。不删除、不替换这些任务；正式实验从空 Skill/Memory 开始，不复用这些历史执行作为正式结果或初始 Memory。

补充独立性说明：方法 V22/V23 档案中没有 Test 轨迹，但早期 `artifacts/benchmarks/alfworld` 已有覆盖这 134 条 Test 的基准执行记录（281 份含步骤记录）。本次只盘点身份和文件路径，没有使用其得分、轨迹内容选择优化任务或生成更新。见 [prior_test_execution_inventory.json](../data/prior_test_execution_inventory.json)。因此只能说本轮 Test 不参与优化，不能说这些任务在项目历史上从未被执行或接触过。S0/S1 将在未来授权后按当前共同协议重新评价，不能直接拿旧结果替代。

## 4. 六轮完整任务清单

以下 gamefile 均相对于 ALFWORLD_DATA。`train:` / `val:` 保留公开 ID 与来源身份；Selection 进入合并优化池，不是独立 Gate 验证集。分批文件保存全部 57 个有序 ID；配置保存对应原始 item；无重抽样、补齐或任务类型均衡化。

### R01（10 条）

| task_id | source_split | task_type | gamefile |
|---|---|---|---|
| train:0000 | train | look_at_obj_in_light | `json_2.1.1/train/look_at_obj_in_light-AlarmClock-None-DeskLamp-305/trial_T20190908_082736_108723/game.tw-pddl` |
| train:0001 | train | look_at_obj_in_light | `json_2.1.1/train/look_at_obj_in_light-CD-None-DeskLamp-304/trial_T20190907_185649_782438/game.tw-pddl` |
| train:0002 | train | look_at_obj_in_light | `json_2.1.1/train/look_at_obj_in_light-CD-None-DeskLamp-320/trial_T20190907_224439_174735/game.tw-pddl` |
| train:0003 | train | look_at_obj_in_light | `json_2.1.1/train/look_at_obj_in_light-Pillow-None-DeskLamp-316/trial_T20190908_232421_645610/game.tw-pddl` |
| train:0004 | train | look_at_obj_in_light | `json_2.1.1/train/look_at_obj_in_light-Statue-None-DeskLamp-319/trial_T20190907_035546_167548/game.tw-pddl` |
| train:0005 | train | pick_and_place_simple | `json_2.1.1/train/pick_and_place_simple-CellPhone-None-Shelf-313/trial_T20190908_123725_452958/game.tw-pddl` |
| train:0006 | train | pick_and_place_simple | `json_2.1.1/train/pick_and_place_simple-Newspaper-None-Sofa-211/trial_T20190906_175004_203092/game.tw-pddl` |
| train:0007 | train | pick_and_place_simple | `json_2.1.1/train/pick_and_place_simple-Pencil-None-Desk-302/trial_T20190908_032836_462632/game.tw-pddl` |
| train:0008 | train | pick_and_place_simple | `json_2.1.1/train/pick_and_place_simple-SoapBar-None-GarbageCan-416/trial_T20190908_020839_714699/game.tw-pddl` |
| train:0009 | train | pick_and_place_simple | `json_2.1.1/train/pick_and_place_simple-Statue-None-CoffeeTable-222/trial_T20190907_131249_788749/game.tw-pddl` |

### R02（10 条）

| task_id | source_split | task_type | gamefile |
|---|---|---|---|
| train:0010 | train | pick_and_place_simple | `json_2.1.1/train/pick_and_place_simple-ToiletPaper-None-ToiletPaperHanger-406/trial_T20190908_122807_136741/game.tw-pddl` |
| train:0011 | train | pick_and_place_simple | `json_2.1.1/train/pick_and_place_simple-ToiletPaper-None-ToiletPaperHanger-415/trial_T20190908_050443_333939/game.tw-pddl` |
| train:0012 | train | pick_clean_then_place_in_recep | `json_2.1.1/train/pick_clean_then_place_in_recep-Apple-None-DiningTable-4/trial_T20190908_104413_450768/game.tw-pddl` |
| train:0013 | train | pick_clean_then_place_in_recep | `json_2.1.1/train/pick_clean_then_place_in_recep-DishSponge-None-Shelf-20/trial_T20190907_222429_992578/game.tw-pddl` |
| train:0014 | train | pick_clean_then_place_in_recep | `json_2.1.1/train/pick_clean_then_place_in_recep-DishSponge-None-Shelf-401/trial_T20190908_072225_397518/game.tw-pddl` |
| train:0015 | train | pick_clean_then_place_in_recep | `json_2.1.1/train/pick_clean_then_place_in_recep-Kettle-None-Cabinet-2/trial_T20190909_043103_418752/game.tw-pddl` |
| train:0016 | train | pick_clean_then_place_in_recep | `json_2.1.1/train/pick_clean_then_place_in_recep-Knife-None-Drawer-22/trial_T20190907_224827_746945/game.tw-pddl` |
| train:0017 | train | pick_clean_then_place_in_recep | `json_2.1.1/train/pick_clean_then_place_in_recep-Lettuce-None-DiningTable-20/trial_T20190906_191148_519826/game.tw-pddl` |
| train:0018 | train | pick_clean_then_place_in_recep | `json_2.1.1/train/pick_clean_then_place_in_recep-Lettuce-None-Fridge-13/trial_T20190908_203022_601787/game.tw-pddl` |
| train:0019 | train | pick_clean_then_place_in_recep | `json_2.1.1/train/pick_clean_then_place_in_recep-Plate-None-Fridge-5/trial_T20190909_112954_869911/game.tw-pddl` |

### R03（10 条）

| task_id | source_split | task_type | gamefile |
|---|---|---|---|
| train:0020 | train | pick_clean_then_place_in_recep | `json_2.1.1/train/pick_clean_then_place_in_recep-Spoon-None-DiningTable-18/trial_T20190909_102159_277894/game.tw-pddl` |
| train:0021 | train | pick_cool_then_place_in_recep | `json_2.1.1/train/pick_cool_then_place_in_recep-Bread-None-CounterTop-1/trial_T20190908_212439_711334/game.tw-pddl` |
| train:0022 | train | pick_cool_then_place_in_recep | `json_2.1.1/train/pick_cool_then_place_in_recep-Bread-None-CounterTop-15/trial_T20190909_085448_256298/game.tw-pddl` |
| train:0023 | train | pick_cool_then_place_in_recep | `json_2.1.1/train/pick_cool_then_place_in_recep-Bread-None-CounterTop-16/trial_T20190908_143948_082471/game.tw-pddl` |
| train:0024 | train | pick_cool_then_place_in_recep | `json_2.1.1/train/pick_cool_then_place_in_recep-Pan-None-StoveBurner-27/trial_T20190906_212619_469871/game.tw-pddl` |
| train:0025 | train | pick_cool_then_place_in_recep | `json_2.1.1/train/pick_cool_then_place_in_recep-Plate-None-DiningTable-17/trial_T20190909_122939_032098/game.tw-pddl` |
| train:0026 | train | pick_cool_then_place_in_recep | `json_2.1.1/train/pick_cool_then_place_in_recep-Pot-None-CounterTop-1/trial_T20190909_124252_504581/game.tw-pddl` |
| train:0027 | train | pick_heat_then_place_in_recep | `json_2.1.1/train/pick_heat_then_place_in_recep-Apple-None-Fridge-20/trial_T20190908_013911_274341/game.tw-pddl` |
| train:0028 | train | pick_heat_then_place_in_recep | `json_2.1.1/train/pick_heat_then_place_in_recep-Egg-None-CounterTop-12/trial_T20190908_215527_416490/game.tw-pddl` |
| train:0029 | train | pick_heat_then_place_in_recep | `json_2.1.1/train/pick_heat_then_place_in_recep-Mug-None-CoffeeMachine-1/trial_T20190907_222924_821086/game.tw-pddl` |

### R04（10 条）

| task_id | source_split | task_type | gamefile |
|---|---|---|---|
| train:0030 | train | pick_heat_then_place_in_recep | `json_2.1.1/train/pick_heat_then_place_in_recep-Mug-None-CoffeeMachine-28/trial_T20190908_062730_537428/game.tw-pddl` |
| train:0031 | train | pick_heat_then_place_in_recep | `json_2.1.1/train/pick_heat_then_place_in_recep-Plate-None-Cabinet-13/trial_T20190907_062749_759882/game.tw-pddl` |
| train:0032 | train | pick_heat_then_place_in_recep | `json_2.1.1/train/pick_heat_then_place_in_recep-Potato-None-Fridge-2/trial_T20190909_030845_198194/game.tw-pddl` |
| train:0033 | train | pick_heat_then_place_in_recep | `json_2.1.1/train/pick_heat_then_place_in_recep-Tomato-None-CounterTop-26/trial_T20190907_005525_499114/game.tw-pddl` |
| train:0034 | train | pick_two_obj_and_place | `json_2.1.1/train/pick_two_obj_and_place-CD-None-Drawer-319/trial_T20190907_145515_348252/game.tw-pddl` |
| train:0035 | train | pick_two_obj_and_place | `json_2.1.1/train/pick_two_obj_and_place-Candle-None-Drawer-427/trial_T20190909_043917_251333/game.tw-pddl` |
| train:0036 | train | pick_two_obj_and_place | `json_2.1.1/train/pick_two_obj_and_place-KeyChain-None-ArmChair-222/trial_T20190909_100312_677332/game.tw-pddl` |
| train:0037 | train | pick_two_obj_and_place | `json_2.1.1/train/pick_two_obj_and_place-Newspaper-None-Sofa-212/trial_T20190908_112632_208041/game.tw-pddl` |
| train:0038 | train | pick_two_obj_and_place | `json_2.1.1/train/pick_two_obj_and_place-SaltShaker-None-SideTable-21/trial_T20190909_041626_844806/game.tw-pddl` |
| val:0000 | val | look_at_obj_in_light | `json_2.1.1/valid_seen/look_at_obj_in_light-AlarmClock-None-DeskLamp-323/trial_T20190909_044715_250790/game.tw-pddl` |

### R05（10 条）

| task_id | source_split | task_type | gamefile |
|---|---|---|---|
| val:0001 | val | look_at_obj_in_light | `json_2.1.1/valid_seen/look_at_obj_in_light-Bowl-None-DeskLamp-301/trial_T20190909_150719_492274/game.tw-pddl` |
| val:0002 | val | look_at_obj_in_light | `json_2.1.1/valid_seen/look_at_obj_in_light-Pillow-None-DeskLamp-323/trial_T20190908_053153_077977/game.tw-pddl` |
| val:0003 | val | pick_and_place_simple | `json_2.1.1/valid_seen/pick_and_place_simple-Mug-None-SideTable-329/trial_T20190909_032318_169393/game.tw-pddl` |
| val:0004 | val | pick_and_place_simple | `json_2.1.1/valid_seen/pick_and_place_simple-Mug-None-SideTable-329/trial_T20190909_032340_274147/game.tw-pddl` |
| val:0005 | val | pick_and_place_simple | `json_2.1.1/valid_seen/pick_and_place_simple-Pencil-None-Desk-310/trial_T20190909_113054_894334/game.tw-pddl` |
| val:0006 | val | pick_clean_then_place_in_recep | `json_2.1.1/valid_seen/pick_clean_then_place_in_recep-ButterKnife-None-Drawer-30/trial_T20190908_052007_212776/game.tw-pddl` |
| val:0007 | val | pick_clean_then_place_in_recep | `json_2.1.1/valid_seen/pick_clean_then_place_in_recep-ButterKnife-None-Drawer-8/trial_T20190909_124425_112757/game.tw-pddl` |
| val:0008 | val | pick_clean_then_place_in_recep | `json_2.1.1/valid_seen/pick_clean_then_place_in_recep-SoapBar-None-Cabinet-402/trial_T20190908_055221_984342/game.tw-pddl` |
| val:0009 | val | pick_clean_then_place_in_recep | `json_2.1.1/valid_seen/pick_clean_then_place_in_recep-SoapBar-None-Toilet-410/trial_T20190906_201106_979461/game.tw-pddl` |
| val:0010 | val | pick_cool_then_place_in_recep | `json_2.1.1/valid_seen/pick_cool_then_place_in_recep-Apple-None-Microwave-19/trial_T20190906_210937_878489/game.tw-pddl` |

### R06（7 条）

| task_id | source_split | task_type | gamefile |
|---|---|---|---|
| val:0011 | val | pick_cool_then_place_in_recep | `json_2.1.1/valid_seen/pick_cool_then_place_in_recep-Plate-None-CounterTop-1/trial_T20190906_205324_559361/game.tw-pddl` |
| val:0012 | val | pick_cool_then_place_in_recep | `json_2.1.1/valid_seen/pick_cool_then_place_in_recep-Tomato-None-Microwave-18/trial_T20190909_012524_159092/game.tw-pddl` |
| val:0013 | val | pick_heat_then_place_in_recep | `json_2.1.1/valid_seen/pick_heat_then_place_in_recep-Apple-None-DiningTable-26/trial_T20190907_060234_011675/game.tw-pddl` |
| val:0014 | val | pick_heat_then_place_in_recep | `json_2.1.1/valid_seen/pick_heat_then_place_in_recep-Tomato-None-Fridge-15/trial_T20190909_020200_054379/game.tw-pddl` |
| val:0015 | val | pick_heat_then_place_in_recep | `json_2.1.1/valid_seen/pick_heat_then_place_in_recep-Tomato-None-Fridge-23/trial_T20190909_082320_103350/game.tw-pddl` |
| val:0016 | val | pick_two_obj_and_place | `json_2.1.1/valid_seen/pick_two_obj_and_place-Book-None-Desk-313/trial_T20190908_125930_920681/game.tw-pddl` |
| val:0017 | val | pick_two_obj_and_place | `json_2.1.1/valid_seen/pick_two_obj_and_place-CreditCard-None-Safe-323/trial_T20190907_001129_214240/game.tw-pddl` |

## 5. 正式配置与执行语义

配置见 [campaign.json](../config/campaign.json)、[protocol.json](../config/protocol.json)、[no_skill_eval.json](../config/no_skill_eval.json)、[v23_eval.json](../config/v23_eval.json)。使用现有 Campaign 配置结构，没有第二套轮次调度。

| 项目 | 冻结值 |
|---|---|
| S0 | No Skill，134 Test；不演化、不生成 Memory |
| S1 | null Parent、空 Active Memory；完整 V23，6 轮，1 Epoch；完成后 134 Test |
| Actor / 模块 | deepseek-flash；https://api.deepseek.com |
| 请求参数 | temperature=1、thinking enabled、reasoning_effort=medium、stream=false |
| 单请求输出上限 | 16,384 Token（包含推理） |
| 时间限制 | 模块 timeout=300s；Actor requests connect timeout=10s、read timeout=300s（不是严格总墙钟上限） |
| Actor | 50 步；当前观察/动作候选＋最近两组行动前观察与动作 |
| 环境 | TextWorld PDDL；AlfredDemangler(shuffle=False)；fresh reset；seed=42 |
| 基础 Prompt | execution_protocol 中的实际 system/initial/history 原文，未修改 |
| 模块输入上限 | 300,000 字符；实际 messages UTF-8 400,000 字节 |
| 重试 | 首次＋最多两次；失败全部保留；耗尽停止，显式 resume 才新增预算 |
| Gate | Candidate 成功数严格大于 Parent 才 ACCEPT；其余 RETAIN |
| Replay | 同批真实配对；不接收 Gate；RETAIN 仍可学习 |
| 状态 | 当轮冻结 Parent/Memory；新 Memory 下轮生效；Parent/Active Memory 原子发布 |

S0 与 S1 Test 的任务顺序、模型、基础 Prompt、历史、环境、步数、生成参数和成功语义完全相同，只有正式 Skill 指导可能不同。环境成功来自 won；技术中断不是普通失败，不能悄悄排除任务。没有 LLM seed 参数；seed=42 不保证输出相同。协议中原有的提供方参数解释属于此前元数据，本次没有重新改变参数或宣称验证其服务端实现。

配置继承 v23_evolution_001 的全部模型、重试及容量参数；仅更新批次、task_items、实际环境文件快照，以及显式优化 split/数据根/Actor 路由。凭据不写入配置，静态确认本机存在凭据配置，但未验证在线额度或服务可用性。实际 gamefile 内容直接冻结在 campaign.environment_files，文件约 5 MB；不使用新增哈希体系。S0/S1 Test 配置包含相同的真实 task items。

## 6. 最小适配与交接

1. `src/skill_evolution/v23/evolution.py`：新增可选 `optimization_splits=['train','val']`，默认仍仅 Train；合并池必须保存 task_items，Test 一律拒绝。Actor 使用原 split 和显式 optimization purpose；执行前比较当前 manifest item 与冻结身份。数据根/Actor base URL 显式传给现有子进程，避免环境变量漂移切换路线。
2. `src/adapters/alfworld/skill_runtime.py`：仅新增显式 `optimization` 用途，允许 train/val 学习，保留来源 split；不把它标成独立 selection；原有 purpose 权限不变，Test 仅 final。
3. `src/adapters/alfworld/run_task_skill.py`：CLI 接受该用途；执行协议、动作处理与模型参数不变。
4. `evolution.final_parent(campaign)`：只读接口，核验全部轮次发布链与最终状态，返回正式 Parent 文件或 None；不回退到最后一个 Candidate。
5. 本目录 `test_commands.py`：只打印复用现有 fixed-Skill Actor CLI 的 134 条命令，不执行。S1 必须已完成六轮且使用本次配置；读取 final_parent，若为 None 则完全不传 --skill-file。它不是新评价算法或自动调度器。旧 `eval_test.py` 不作为本次入口，以免混用旧 runner/重试协议。

现有 Orchestrator 不限制每轮固定大小；以实际列表运行，Gate 的 compared 为该轮有效配对数；第六轮 7 条无需特殊算法。恢复保持冻结任务顺序，上游合法结果复用。新增功能不改写旧档案；旧 Campaign 已冻结源码，源码变动后其 run/resume 仍可能按原有规则拒绝漂移，不代表历史结果文件被修改。

未来明确授权后，优化启动入口（**本次没有执行**）：

```bash
python -m src.skill_evolution.v23.evolution run \
  --campaign artifacts/methods/v23/v23_alfworld_formal_001/S1 \
  --config experiments/methods/v23/v23_alfworld_formal_001/config/campaign.json
```

最后 Test 的只读命令生成入口（打印，不执行；S1 未完成时拒绝）：

```bash
PYTHONPATH=. python experiments/methods/v23/v23_alfworld_formal_001/test_commands.py --group S0 --shell
PYTHONPATH=. python experiments/methods/v23/v23_alfworld_formal_001/test_commands.py --group S1 --shell
```

以后真正执行这些命令需要用户的启动授权。本次未生成或运行 shell 批次，也未创建正式 state.json。Test 命令 stop-on-error，不会把异常任务静默跳过；此准备不实现额外 Test 汇总调度或自动任务重跑。

## 7. 请求与 Token 预算

详见 [budget.json](../config/budget.json)。假设各轮都生成 Candidate 且没有语义停点：

| 范围 | Episode 上限 | Actor 逻辑请求上限 | 模块逻辑请求上限 | 含最多三次尝试的 HTTP 上限 | 生成 Token 理论上限 |
|---|---:|---:|---:|---:|---:|
| 六轮优化 | 114（57 Parent＋57 Candidate） | 5,700 | 30（每轮五个 LLM 模块） | 17,190 | 281,640,960 |
| S0 Test | 134 | 6,700 | 0 | 20,100 | 329,318,400 |
| S1 Test | 134 | 6,700 | 0 | 20,100 | 329,318,400 |
| 合计 | 382 | 19,100 | 30 | 57,390 | 940,277,760 |

这是首次启动的最坏请求/输出上限，**不是预计消耗，也不是包含输入的总 Token 上限**。每 Episode 最多 50 步；未生成 Candidate 时后续相关阶段不调用；Gate 为纯程序。显式 resume 可能开启新请求预算并重开部分任务，必须另计。

历史经验仅作场景参考：v23_evolution_001 两个四任务轮次分别 237,652/598,251 总 Token。按优化任务数 57/4 线性外推约 **339 万～853 万总 Token**。按各轮 8 个 Actor episode 的实际总量外推，**每组 134 Test 约 216 万～427 万**；两项 Test 加优化约 **771 万～1,706 万**。这些不是统计置信区间，不是保证上限；十任务批次、六轮完整历史来源累积、更长 Skill、重试及推理随机性可能显著改变实际消耗。

最大风险是后续 Preconditioner/Replay 输入容量：当前机制向模型提供 Active Memory 引用的完整历史来源。READY 只表示可以按配置启动，不保证六轮都能在原容量内完成。超出 300,000 字符或 400,000 字节时按既定规则停止、保存证据，不自动压缩、截断或加预算。未知未来 Memory 不能通过准备工作预先证明一定装得下。

## 8. 离线验证与档案保护

执行命令：

```bash
PYTHONPATH=. /tmp/gse-v23-py313/bin/python experiments/methods/v23/v23_alfworld_formal_001/prepare.py
PYTHONPATH=. /tmp/gse-v23-py313/bin/python experiments/methods/v23/v23_alfworld_formal_001/run_offline_tests.py
```

回归：**531 passed，19 subtests passed**；新增 18 项准备/交接测试。日志见 [offline_tests.txt](offline_tests.txt)。测试入口禁止 socket 连接和环境/Actor 子进程，仅允许既有测试所需的 `git rev-parse HEAD` 元数据读取；模块回复和环境均为 fixture，不是任何实际 ALFWorld Episode。

覆盖数量与 gamefile 身份、真实任务类型、来源隔离、重复/遗漏、官方顺序可复现、池内容变化拒绝复用、旧参数逐项相等、显式 val 优化权限、Test 拒绝、S0/S1 共同协议、模拟六轮 ACCEPT/RETAIN、最后一轮 compared=7、最终正式 Parent/None 读取、重复 resume 零新增调用、未完成 Campaign 拒绝最终评价。已有错误注入及恢复回归保持通过。

初次新增测试有两项 fixture 的 model 字段不匹配正式配置而失败；已修正模拟记录，不改变生产校验或删除测试。随后完整回归通过。准备程序重复读取会逐值比较已有文件；池、批次或配置变化时报错，不默默复用旧分批。先前 v23_evolution_001 正式状态逐字节检查不变；没有写入旧实验档案或任何 Prompt。

## 9. 最终结论

**READY。** 57 条优化任务与 134 条 Test 真实完整；官方顺序的六轮已冻结；S0/S1 配置与现有 Orchestrator/固定 Skill Actor 入口兼容；离线全部通过。没有缺失数据或当前必要配置阻碍。

仍需在正式运行中观察在线服务、累计输入容量、长推理成本与语义停点。此前开发接触和早期基准 Test 执行已披露，不将本次准备或模拟通过解释成独立效果证据。

**本次止于准备。等待明确授权后才能启动 Campaign 或任一 Test。**

## 用户授权的并行启动调整（2026-10-19）

用户明确放弃首次手动中断的未完成 S1。清理前确认启动进程组、Actor 与子进程均已退出；只删除原 S1 的 51 个文件及该 Campaign 的 launch/campaign.log/interruption 文件，未备份到新实验。此前外部 API 用量无法撤销，删除的运行不纳入重新启动的统计。

原 campaign.json 仅新增 `actor_max_workers: 8`，prepare.py 同步该值；原数据、官方批次、模型参数、初始 Skill/Memory、所有 Prompt 和 Gate/Replay 规则不变。最多 8 条独立 Episode 并行；尾批最多 7 条。结果按冻结顺序汇总；任务失败不再提交后续任务，已启动任务安全保存后停止。只有 Parent/Candidate 阶段并行。

新增 11 项并行测试；完整离线回归 **542 passed、19 subtests passed**（当前 offline_tests.txt）。原有 531 项回归均保留并通过。已测试并发界限、乱序身份、隔离目录、失败排空与状态不发布、resume 复用，以及完整六轮接口。

本次在相同 S1 路径使用 `run`，从 R01/null Parent/空 Memory 全新启动；不是 resume、第二个实验或新算法版本。最终 Test 仍未授权执行。运行请求统计只读取新 S1，启动记录见同一 artifact 根目录。并行只保证协议和身份一致，不保证 LLM 随机轨迹与串行相同。
