# ALFWorld：39 Train / 18 Selection / 134 Test

本目录逐字节保留 SkillOpt 发布的 ALFWorld 路径清单，不重新抽样，不复制原始游戏数据。

来源：`microsoft/SkillOpt` commit `343db229dbd5ddaf9df6b1d5540d8bcdb2604d5c`，目录 `data/alfworld_path_split`。获取日期：2026-10-13。原始 URL 和各文件 SHA-256 见 [source.json](source.json)。

## 固定划分

| 用途 | 清单 | 数量 | 原始目录 |
|---|---|---:|---|
| Train：生成学习经验 | [train/items.json](train/items.json) | 39 | `json_2.1.1/train` |
| Selection：选择候选 Skill | [val/items.json](val/items.json) | 18 | `json_2.1.1/valid_seen` |
| Test：最终评测 | [test/items.json](test/items.json) | 134 | `json_2.1.1/valid_unseen` |

`val` 是上游文件名，在本项目中称 Selection。每项保留上游 `id`、`gamefile`、`task_type`。这三份清单是后续实验的任务身份依据；不要用遍历原始目录或重新随机抽样替代它们。

## 本机数据与路径解析

当前数据根目录为 `/Users/didi/.cache/alfworld`：

```bash
export ALFWORLD_DATA="/Users/didi/.cache/alfworld"
```

根目录应包含 `json_2.1.1` 和 `logic`。清单的 `gamefile` 为相对于该根目录的路径；运行器需解析为 `$ALFWORLD_DATA/<gamefile>`，不要相对于项目工作目录解析。迁移机器时只修改数据根目录，不改写基础清单。

手工体验某个 Train 任务（使用清单的第一个任务）：

```bash
conda activate alfworld
export ALFWORLD_DATA="/Users/didi/.cache/alfworld"
alfworld-play-tw "$ALFWORLD_DATA/json_2.1.1/train/look_at_obj_in_light-AlarmClock-None-DeskLamp-305/trial_T20190908_082736_108723"
```

`alfworld-play-tw` 接收任务目录，不接收 `items.json`；它是人工交互入口，不会自动批量评测这三份清单。

## 后续实验协议

- SkillOpt 式实验：用 39 个 Train 任务学习，在独立的 18 个 Selection 任务上选择 Skill，最终评测固定的 134 个 Test 任务。
- SkillAdam 论文式实验：基础清单仍保持分离；运行时将 Train 和 Selection 合并成 57 个优化任务，并在同一 minibatch 上比较修改前后的 Skill。Test 不变。
- 若做统一协议下的方法对比，明确区分它与各方法的原生论文复现协议。
- Test 不用于 Skill 生成、候选选择或参数调节。正式实验前固定模型、初始 Skill、步数预算、动作接口、seed、运行次数和轨迹输出位置。

协议参考：[SkillOpt 数据说明](https://github.com/microsoft/SkillOpt/blob/343db229dbd5ddaf9df6b1d5540d8bcdb2604d5c/data/README.md)、[SkillAdam 论文第 5.3 节](https://arxiv.org/html/2609.08944v1#S5.SS3)。

## 已完成的检查

[validation.json](validation.json) 记录 2026-10-13 本机静态检查：数量为 39/18/134；每份清单的 ID 和游戏路径均无重复；三个划分之间游戏路径无交集；全部 191 个游戏文件及其 `traj_data.json` 存在，任务类型与清单一致。

此静态检查没有运行任务或调用模型，不代表全部任务已完成运行验证。随后已接入[大模型单任务及 NoSkill Test 评测入口](../../../../src/adapters/alfworld/README.md)；具体运行结果以各次评测的轨迹和汇总为准。
