# Train 任务池与历史重复性冻结

当前已按用户批准冻结 **两轮各 8 项、共 16 项全新 Train**，正式清单和执行顺序见文末修订记录。**实验仍等待启动授权**。最初暂定两轮各 10 项；固定 SkillOpt Train 共 39 项，按事前排除规则只剩 16 项，因此先记录不足，再由用户明确调整为 8+8。没有扩大到原始 ALFWorld Train、混入 Selection/Test 或补入旧任务。

## 来源与规则

- 全集：`benchmarks/alfworld/editions/skillopt_39_18_134/train/items.json`，SHA-256 `76dc1f738fafc9c3c0dae606eb9434b1e1a34b814874e4d791242f9ec90e6378`。
- 排除：01—09 中实际执行、冻结计划已选及被引用为历史接触的 Train 身份；09 合成案例不作为环境接触。05/07 已披露的前置 Train 执行同时排除。恢复目录内的同一轨迹副本不算独立运行。
- 排名：固定 seed `v22.unified_dsc.v2.train-stream.20261016.seed42`；按 `SHA256(UTF8(seed + "\n" + id + "\n" + gamefile + "\n"))` 升序，同 hash 按 ID 排序。规则已写入脚本再计算排名；不使用任务家族、成败、隐藏计划或修复可能性。
- 结果：[task_inventory.json](config/task_inventory.json) 保存全部 39 项身份、124 份来源文件哈希、每项排除证据、候选排名及静态文件检查。来源文件均存在。
- 脚本：[inventory_tasks.py](config/inventory_tasks.py)；`--check` 仅重算并比较，不写文件，不发网络请求，不实例化环境。

## 历史覆盖

| 阶段 | 真实执行或复用的 Train | 说明 |
|---|---|---|
| 01 | 0000、0012 | 新执行；包含中断/恢复档案，均视为已经接触 |
| 02 | 0000、0012 | 复用 01，无新增环境执行 |
| 03 | 0000、0012 | 复用 Parent 并执行 Candidate |
| 04 | 0000、0012 | 复用既有输入，无新增环境执行 |
| 05 | 0006、0022、0035 | 新执行；计划另披露前置 Train 历史 |
| 06 | 0021、0034 | 新执行；沿用已冻结来源 |
| 07 | 0007、0021、0023、0034、0036 | 原始回放及新一批筛查/回放 |
| 08 | 0001、0002、0006、0007、0008、0009、0013、0014、0021、0022、0023、0024、0027、0028、0029、0034、0035、0036、0037、0038 | 两轮 20 项；恢复档案按身份去重 |
| 09 | 复用 08 的 20 项 | 3 个真实材料探针；其余 4 个合成探针没有 Train 身份，0 个新 episode |

表中 ID 省略统一前缀 `train:`。01—08 的独立任务并集为 22 项。05/07 声明的前置检查另包含 `train:0005`，其真实轨迹保存在 `artifacts/benchmarks/alfworld/upstream_noskill_train_check_20261014/tasks/train_0005/llm_20261014T031204240482Z/trajectory.json`。计入该已披露接触后，排除集合为 **23 项**，并非 22 项。没有额外“仅冻结未执行”且未包含于实际执行集合的 Train 项。

## 原始盘点的候选排名

`0019, 0004, 0020, 0017, 0025, 0033, 0016, 0010, 0032, 0003, 0026, 0018, 0011, 0015, 0031, 0030`

全部固定 39 项的 `game.tw-pddl` 和 `traj_data.json` 均存在且可只读解析，`task_type` 与 manifest 一致。检查保存游戏文件与任务文件哈希，只确认格式和身份；没有启动 TextWorld、reset/step，也不证明真实 reset 必然成功。

## 原 20 项请求的不足记录

原设置需要 20 项，缺少 4 项。盘点完成时未创建正式 `task_manifest.json`，也未自动分配 8+8、补旧任务或扩大数据集，而是等待用户决定任务边界。随后用户批准 8+8；独立正式清单及协议修订见下节，原始盘点继续保留。

只读复核命令：

```bash
python experiments/methods/v22/11_unified_dsc_stream/config/inventory_tasks.py --check
```

此项复核确认原始盘点与来源未变化；原 20 项请求确实不足。它不代表模型或环境已经执行，也不代替后续完整实验 preflight。

## 2026-10-16 用户批准的任务边界修订

用户随后明确选择 **两轮各 8 项、全部使用新 Train**。上述 20 项请求不足的原始盘点保留不变；本节及新正式 manifest 记录已经批准的 8+8 分配。此次授权仅覆盖实验准备和任务边界调整，**仍未授权模型调用或环境执行**。

直接采用已冻结排名的前 8 项和后 8 项，不重新抽样、不调整 seed、不引入成败或家族配额：

| 轮次 | 按执行顺序的 Train ID |
|---|---|
| 第一轮 | 0019、0004、0020、0017、0025、0033、0016、0010 |
| 第二轮 | 0032、0003、0026、0018、0011、0015、0031、0030 |

正式清单：[task_manifest.json](config/task_manifest.json)，协议 `v22.grouped_continual.v4`，SHA-256 `74e0cd98d0a62077ed3b7a02875fff68db01e9e9bf5a21c815bdbd0c320c764a`。每项完整原始 Train entry 保持不变；16 项互不重复，与历史排除集合交集为空。清单绑定原始盘点、其生成脚本、manifest 生成脚本、Train 全集和历史来源哈希。

[freeze_task_manifest.py](config/freeze_task_manifest.py) 可精确重建清单；只读检查命令：

```bash
python experiments/methods/v22/11_unified_dsc_stream/config/freeze_task_manifest.py --check
```

manifest 精确重建及原始 inventory 只读复核均通过。原始 inventory 仍显示 `insufficient_unused_train`，特指其已经冻结的 20 项请求；不应把这段历史状态误读为获批 8+8 清单仍不足。
