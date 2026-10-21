# 最终选定轨迹索引与逐步执行证据

仅列真实执行动作及环境反馈，不转录模型思维文本。各任务首次正常结束的轨迹用于最终比较；中断前缀只计成本。

## Parent P3

[原始 trajectory.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_3/p3c1_r05_replay_001/episodes/Parent/P3/trajectory.json)；success，4 步。

任务：put some mug on sidetable.

| 步 | 实际动作 | 环境反馈 |
|---|---|---|
| 1 | `go to diningtable 1` | You arrive at diningtable 1. On the diningtable 1, you see a cd 2, a cellphone 3, a cellphone 1, a keychain 3, a mug 1, a pen 2, a pencil 3, and a pencil 2. |
| 2 | `take mug 1 from diningtable 1` | You pick up the mug 1 from the diningtable 1. |
| 3 | `go to sidetable 1` | You arrive at sidetable 1. On the sidetable 1, you see a creditcard 1, a keychain 1, and a pen 1. |
| 4 | `move mug 1 to sidetable 1` | You move the mug 1 to the sidetable 1. |

## Parent P6

[原始 trajectory.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_3/p3c1_r05_replay_001/episodes/Parent/P6/trajectory.json)；success，10 步。

任务：put a clean butterknife in drawer.

| 步 | 实际动作 | 环境反馈 |
|---|---|---|
| 1 | `go to sinkbasin 1` | You arrive at sinkbasin 1. On the sinkbasin 1, you see a spatula 1, a spoon 2, and a spoon 1. |
| 2 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a cup 1, a houseplant 1, a mug 1, and a peppershaker 1. |
| 3 | `go to countertop 2` | You arrive at countertop 2. On the countertop 2, you see a butterknife 1, a cellphone 1, a egg 1, a fork 2, a fork 1, a knife 2, a knife 1, a ladle 1, a lettuce 1, and a tomato 1. |
| 4 | `take butterknife 1 from countertop 2` | You pick up the butterknife 1 from the countertop 2. |
| 5 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is closed. |
| 6 | `go to sinkbasin 1` | You arrive at sinkbasin 1. On the sinkbasin 1, you see a spatula 1, a spoon 2, and a spoon 1. |
| 7 | `clean butterknife 1 with sinkbasin 1` | You clean the butterknife 1 using the sinkbasin 1. |
| 8 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is closed. |
| 9 | `open drawer 1` | You open the drawer 1. The drawer 1 is open. In it, you see nothing. |
| 10 | `move butterknife 1 to drawer 1` | You move the butterknife 1 to the drawer 1. |

## Parent P7

[原始 trajectory.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_3/p3c1_r05_replay_restart_004/attempt_1/episodes/Parent/P7/trajectory.json)；step_limit，50 步。

任务：clean some butterknife and put it in drawer.

| 步 | 实际动作 | 环境反馈 |
|---|---|---|
| 1 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is closed. |
| 2 | `open drawer 1` | You open the drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 3 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is closed. |
| 4 | `open drawer 2` | You open the drawer 2. The drawer 2 is open. In it, you see nothing. |
| 5 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a dishsponge 1, a egg 1, a houseplant 1, a soapbottle 1, and a tomato 1. |
| 6 | `go to cabinet 1` | You arrive at cabinet 1. The cabinet 1 is closed. |
| 7 | `open cabinet 1` | You open the cabinet 1. The cabinet 1 is open. In it, you see nothing. |
| 8 | `go to cabinet 2` | You arrive at cabinet 2. The cabinet 2 is closed. |
| 9 | `open cabinet 2` | You open the cabinet 2. The cabinet 2 is open. In it, you see a bowl 1. |
| 10 | `go to cabinet 3` | You arrive at cabinet 3. The cabinet 3 is closed. |
| 11 | `open cabinet 3` | You open the cabinet 3. The cabinet 3 is open. In it, you see nothing. |
| 12 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a dishsponge 1, a egg 1, a houseplant 1, a soapbottle 1, and a tomato 1. |
| 13 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 14 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is open. In it, you see nothing. |
| 15 | `go to drawer 3` | You arrive at drawer 3. The drawer 3 is closed. |
| 16 | `open drawer 3` | You open the drawer 3. The drawer 3 is open. In it, you see a spoon 2. |
| 17 | `go to drawer 4` | You arrive at drawer 4. The drawer 4 is closed. |
| 18 | `open drawer 4` | You open the drawer 4. The drawer 4 is open. In it, you see nothing. |
| 19 | `go to drawer 5` | You arrive at drawer 5. The drawer 5 is closed. |
| 20 | `open drawer 5` | You open the drawer 5. The drawer 5 is open. In it, you see a pen 3. |
| 21 | `go to drawer 6` | You arrive at drawer 6. The drawer 6 is closed. |
| 22 | `open drawer 6` | You open the drawer 6. The drawer 6 is open. In it, you see nothing. |
| 23 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a dishsponge 1, a egg 1, a houseplant 1, a soapbottle 1, and a tomato 1. |
| 24 | `go to sinkbasin 1` | You arrive at sinkbasin 1. On the sinkbasin 1, you see a apple 2. |
| 25 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 26 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is open. In it, you see nothing. |
| 27 | `go to drawer 3` | You arrive at drawer 3. The drawer 3 is open. In it, you see a spoon 2. |
| 28 | `go to drawer 4` | You arrive at drawer 4. The drawer 4 is open. In it, you see nothing. |
| 29 | `go to drawer 5` | You arrive at drawer 5. The drawer 5 is open. In it, you see a pen 3. |
| 30 | `go to drawer 6` | You arrive at drawer 6. The drawer 6 is open. In it, you see nothing. |
| 31 | `go to drawer 7` | You arrive at drawer 7. The drawer 7 is closed. |
| 32 | `open drawer 7` | You open the drawer 7. The drawer 7 is open. In it, you see nothing. |
| 33 | `go to cabinet 1` | You arrive at cabinet 1. The cabinet 1 is open. In it, you see nothing. |
| 34 | `go to cabinet 2` | You arrive at cabinet 2. The cabinet 2 is open. In it, you see a bowl 1. |
| 35 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 36 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is open. In it, you see nothing. |
| 37 | `go to drawer 3` | You arrive at drawer 3. The drawer 3 is open. In it, you see a spoon 2. |
| 38 | `go to drawer 4` | You arrive at drawer 4. The drawer 4 is open. In it, you see nothing. |
| 39 | `go to drawer 5` | You arrive at drawer 5. The drawer 5 is open. In it, you see a pen 3. |
| 40 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a dishsponge 1, a egg 1, a houseplant 1, a soapbottle 1, and a tomato 1. |
| 41 | `go to countertop 2` | You arrive at countertop 2. On the countertop 2, you see a bread 2, a bread 1, a egg 3, a lettuce 2, a mug 1, a peppershaker 1, a plate 3, a pot 1, a sink 1, and a spoon 1. |
| 42 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 43 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is open. In it, you see nothing. |
| 44 | `go to drawer 3` | You arrive at drawer 3. The drawer 3 is open. In it, you see a spoon 2. |
| 45 | `go to drawer 4` | You arrive at drawer 4. The drawer 4 is open. In it, you see nothing. |
| 46 | `go to drawer 5` | You arrive at drawer 5. The drawer 5 is open. In it, you see a pen 3. |
| 47 | `go to drawer 6` | You arrive at drawer 6. The drawer 6 is open. In it, you see nothing. |
| 48 | `go to drawer 7` | You arrive at drawer 7. The drawer 7 is open. In it, you see nothing. |
| 49 | `go to cabinet 1` | You arrive at cabinet 1. The cabinet 1 is open. In it, you see nothing. |
| 50 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a dishsponge 1, a egg 1, a houseplant 1, a soapbottle 1, and a tomato 1. |

## Parent P10

[原始 trajectory.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_3/p3c1_r05_replay_001/episodes/Parent/P10/trajectory.json)；success，14 步。

任务：cool some apple and put it in microwave.

| 步 | 实际动作 | 环境反馈 |
|---|---|---|
| 1 | `go to fridge 1` | You arrive at fridge 1. The fridge 1 is closed. |
| 2 | `open fridge 1` | You open the fridge 1. The fridge 1 is open. In it, you see a bowl 1, and a mug 1. |
| 3 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a bread 1, a butterknife 1, a lettuce 1, a pan 1, and a pot 1. |
| 4 | `go to cabinet 1` | You arrive at cabinet 1. On the cabinet 1, you see nothing. |
| 5 | `examine cabinet 1` | On the cabinet 1, you see nothing. |
| 6 | `go to fridge 1` | You arrive at fridge 1. The fridge 1 is open. In it, you see a bowl 1, and a mug 1. |
| 7 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a bread 1, a butterknife 1, a lettuce 1, a pan 1, and a pot 1. |
| 8 | `go to diningtable 1` | You arrive at diningtable 1. On the diningtable 1, you see a apple 1, a cup 2, a cup 1, a egg 1, a mug 3, a potato 1, a soapbottle 1, a spatula 2, a spatula 1, a spoon 2, and a spoon 1. |
| 9 | `take apple 1 from diningtable 1` | You pick up the apple 1 from the diningtable 1. |
| 10 | `go to fridge 1` | You arrive at fridge 1. The fridge 1 is open. In it, you see a bowl 1, and a mug 1. |
| 11 | `cool apple 1 with fridge 1` | You cool the apple 1 using the fridge 1. |
| 12 | `go to microwave 1` | You arrive at microwave 1. The microwave 1 is closed. |
| 13 | `open microwave 1` | You open the microwave 1. The microwave 1 is open. In it, you see nothing. |
| 14 | `move apple 1 to microwave 1` | You move the apple 1 to the microwave 1. |

## A P3

[原始 trajectory.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_3/p3c1_r05_replay_001/episodes/A/P3/trajectory.json)；success，4 步。

任务：put some mug on sidetable.

| 步 | 实际动作 | 环境反馈 |
|---|---|---|
| 1 | `go to diningtable 1` | You arrive at diningtable 1. On the diningtable 1, you see a cd 2, a cellphone 3, a cellphone 1, a keychain 3, a mug 1, a pen 2, a pencil 3, and a pencil 2. |
| 2 | `take mug 1 from diningtable 1` | You pick up the mug 1 from the diningtable 1. |
| 3 | `go to sidetable 1` | You arrive at sidetable 1. On the sidetable 1, you see a creditcard 1, a keychain 1, and a pen 1. |
| 4 | `move mug 1 to sidetable 1` | You move the mug 1 to the sidetable 1. |

## A P6

[原始 trajectory.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_3/p3c1_r05_replay_001/episodes/A/P6/trajectory.json)；success，8 步。

任务：put a clean butterknife in drawer.

| 步 | 实际动作 | 环境反馈 |
|---|---|---|
| 1 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a cup 1, a houseplant 1, a mug 1, and a peppershaker 1. |
| 2 | `go to countertop 2` | You arrive at countertop 2. On the countertop 2, you see a butterknife 1, a cellphone 1, a egg 1, a fork 2, a fork 1, a knife 2, a knife 1, a ladle 1, a lettuce 1, and a tomato 1. |
| 3 | `take butterknife 1 from countertop 2` | You pick up the butterknife 1 from the countertop 2. |
| 4 | `go to sinkbasin 1` | You arrive at sinkbasin 1. On the sinkbasin 1, you see a spatula 1, a spoon 2, and a spoon 1. |
| 5 | `clean butterknife 1 with sinkbasin 1` | You clean the butterknife 1 using the sinkbasin 1. |
| 6 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is closed. |
| 7 | `open drawer 1` | You open the drawer 1. The drawer 1 is open. In it, you see nothing. |
| 8 | `move butterknife 1 to drawer 1` | You move the butterknife 1 to the drawer 1. |

## A P7

[原始 trajectory.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_3/p3c1_r05_replay_restart_002/attempt_1/episodes/A/P7/trajectory.json)；step_limit，50 步。

任务：clean some butterknife and put it in drawer.

| 步 | 实际动作 | 环境反馈 |
|---|---|---|
| 1 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is closed. |
| 2 | `open drawer 1` | You open the drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 3 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is closed. |
| 4 | `open drawer 2` | You open the drawer 2. The drawer 2 is open. In it, you see nothing. |
| 5 | `go to drawer 3` | You arrive at drawer 3. The drawer 3 is closed. |
| 6 | `open drawer 3` | You open the drawer 3. The drawer 3 is open. In it, you see a spoon 2. |
| 7 | `go to drawer 4` | You arrive at drawer 4. The drawer 4 is closed. |
| 8 | `open drawer 4` | You open the drawer 4. The drawer 4 is open. In it, you see nothing. |
| 9 | `go to drawer 5` | You arrive at drawer 5. The drawer 5 is closed. |
| 10 | `open drawer 5` | You open the drawer 5. The drawer 5 is open. In it, you see a pen 3. |
| 11 | `go to drawer 6` | You arrive at drawer 6. The drawer 6 is closed. |
| 12 | `open drawer 6` | You open the drawer 6. The drawer 6 is open. In it, you see nothing. |
| 13 | `go to drawer 7` | You arrive at drawer 7. The drawer 7 is closed. |
| 14 | `open drawer 7` | You open the drawer 7. The drawer 7 is open. In it, you see nothing. |
| 15 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a dishsponge 1, a egg 1, a houseplant 1, a soapbottle 1, and a tomato 1. |
| 16 | `go to countertop 2` | You arrive at countertop 2. On the countertop 2, you see a bread 2, a bread 1, a egg 3, a lettuce 2, a mug 1, a peppershaker 1, a plate 3, a pot 1, a sink 1, and a spoon 1. |
| 17 | `go to countertop 3` | You arrive at countertop 3. On the countertop 3, you see a fork 1, a kettle 1, a ladle 1, a lettuce 3, a pen 1, a soapbottle 3, a spatula 2, and a spoon 3. |
| 18 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 19 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is open. In it, you see nothing. |
| 20 | `go to drawer 3` | You arrive at drawer 3. The drawer 3 is open. In it, you see a spoon 2. |
| 21 | `go to drawer 4` | You arrive at drawer 4. The drawer 4 is open. In it, you see nothing. |
| 22 | `go to drawer 5` | You arrive at drawer 5. The drawer 5 is open. In it, you see a pen 3. |
| 23 | `go to drawer 6` | You arrive at drawer 6. The drawer 6 is open. In it, you see nothing. |
| 24 | `go to drawer 7` | You arrive at drawer 7. The drawer 7 is open. In it, you see nothing. |
| 25 | `go to drawer 4` | You arrive at drawer 4. The drawer 4 is open. In it, you see nothing. |
| 26 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a dishsponge 1, a egg 1, a houseplant 1, a soapbottle 1, and a tomato 1. |
| 27 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 28 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is open. In it, you see nothing. |
| 29 | `go to drawer 3` | You arrive at drawer 3. The drawer 3 is open. In it, you see a spoon 2. |
| 30 | `go to drawer 4` | You arrive at drawer 4. The drawer 4 is open. In it, you see nothing. |
| 31 | `go to drawer 5` | You arrive at drawer 5. The drawer 5 is open. In it, you see a pen 3. |
| 32 | `go to drawer 6` | You arrive at drawer 6. The drawer 6 is open. In it, you see nothing. |
| 33 | `go to drawer 7` | You arrive at drawer 7. The drawer 7 is open. In it, you see nothing. |
| 34 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a dishsponge 1, a egg 1, a houseplant 1, a soapbottle 1, and a tomato 1. |
| 35 | `go to countertop 2` | You arrive at countertop 2. On the countertop 2, you see a bread 2, a bread 1, a egg 3, a lettuce 2, a mug 1, a peppershaker 1, a plate 3, a pot 1, a sink 1, and a spoon 1. |
| 36 | `go to countertop 3` | You arrive at countertop 3. On the countertop 3, you see a fork 1, a kettle 1, a ladle 1, a lettuce 3, a pen 1, a soapbottle 3, a spatula 2, and a spoon 3. |
| 37 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 38 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is open. In it, you see nothing. |
| 39 | `go to drawer 3` | You arrive at drawer 3. The drawer 3 is open. In it, you see a spoon 2. |
| 40 | `go to drawer 4` | You arrive at drawer 4. The drawer 4 is open. In it, you see nothing. |
| 41 | `go to drawer 5` | You arrive at drawer 5. The drawer 5 is open. In it, you see a pen 3. |
| 42 | `go to drawer 6` | You arrive at drawer 6. The drawer 6 is open. In it, you see nothing. |
| 43 | `go to drawer 7` | You arrive at drawer 7. The drawer 7 is open. In it, you see nothing. |
| 44 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 45 | `go to cabinet 1` | You arrive at cabinet 1. The cabinet 1 is closed. |
| 46 | `open cabinet 1` | You open the cabinet 1. The cabinet 1 is open. In it, you see nothing. |
| 47 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a dishsponge 1, a egg 1, a houseplant 1, a soapbottle 1, and a tomato 1. |
| 48 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 49 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is open. In it, you see nothing. |
| 50 | `go to drawer 3` | You arrive at drawer 3. The drawer 3 is open. In it, you see a spoon 2. |

## A P10

[原始 trajectory.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_3/p3c1_r05_replay_restart_002/attempt_1/episodes/A/P10/trajectory.json)；success，12 步。

任务：cool some apple and put it in microwave.

| 步 | 实际动作 | 环境反馈 |
|---|---|---|
| 1 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a bread 1, a butterknife 1, a lettuce 1, a pan 1, and a pot 1. |
| 2 | `go to countertop 2` | You arrive at countertop 2. On the countertop 2, you see a cup 3, a knife 3, a knife 2, a spatula 3, and a tomato 1. |
| 3 | `go to fridge 1` | You arrive at fridge 1. The fridge 1 is closed. |
| 4 | `open fridge 1` | You open the fridge 1. The fridge 1 is open. In it, you see a bowl 1, and a mug 1. |
| 5 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a bread 1, a butterknife 1, a lettuce 1, a pan 1, and a pot 1. |
| 6 | `go to diningtable 1` | You arrive at diningtable 1. On the diningtable 1, you see a apple 1, a cup 2, a cup 1, a egg 1, a mug 3, a potato 1, a soapbottle 1, a spatula 2, a spatula 1, a spoon 2, and a spoon 1. |
| 7 | `take apple 1 from diningtable 1` | You pick up the apple 1 from the diningtable 1. |
| 8 | `go to fridge 1` | You arrive at fridge 1. The fridge 1 is open. In it, you see a bowl 1, and a mug 1. |
| 9 | `cool apple 1 with fridge 1` | You cool the apple 1 using the fridge 1. |
| 10 | `go to microwave 1` | You arrive at microwave 1. The microwave 1 is closed. |
| 11 | `open microwave 1` | You open the microwave 1. The microwave 1 is open. In it, you see nothing. |
| 12 | `move apple 1 to microwave 1` | You move the apple 1 to the microwave 1. |

## B P3

[原始 trajectory.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_3/p3c1_r05_replay_restart_002/attempt_2/episodes/B/P3/trajectory.json)；success，4 步。

任务：put some mug on sidetable.

| 步 | 实际动作 | 环境反馈 |
|---|---|---|
| 1 | `go to diningtable 1` | You arrive at diningtable 1. On the diningtable 1, you see a cd 2, a cellphone 3, a cellphone 1, a keychain 3, a mug 1, a pen 2, a pencil 3, and a pencil 2. |
| 2 | `take mug 1 from diningtable 1` | You pick up the mug 1 from the diningtable 1. |
| 3 | `go to sidetable 1` | You arrive at sidetable 1. On the sidetable 1, you see a creditcard 1, a keychain 1, and a pen 1. |
| 4 | `move mug 1 to sidetable 1` | You move the mug 1 to the sidetable 1. |

## B P6

[原始 trajectory.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_3/p3c1_r05_replay_restart_002/attempt_2/episodes/B/P6/trajectory.json)；success，11 步。

任务：put a clean butterknife in drawer.

| 步 | 实际动作 | 环境反馈 |
|---|---|---|
| 1 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is closed. |
| 2 | `open drawer 1` | You open the drawer 1. The drawer 1 is open. In it, you see nothing. |
| 3 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is closed. |
| 4 | `open drawer 2` | You open the drawer 2. The drawer 2 is open. In it, you see nothing. |
| 5 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a cup 1, a houseplant 1, a mug 1, and a peppershaker 1. |
| 6 | `go to countertop 2` | You arrive at countertop 2. On the countertop 2, you see a butterknife 1, a cellphone 1, a egg 1, a fork 2, a fork 1, a knife 2, a knife 1, a ladle 1, a lettuce 1, and a tomato 1. |
| 7 | `take butterknife 1 from countertop 2` | You pick up the butterknife 1 from the countertop 2. |
| 8 | `go to sinkbasin 1` | You arrive at sinkbasin 1. On the sinkbasin 1, you see a spatula 1, a spoon 2, and a spoon 1. |
| 9 | `clean butterknife 1 with sinkbasin 1` | You clean the butterknife 1 using the sinkbasin 1. |
| 10 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see nothing. |
| 11 | `move butterknife 1 to drawer 1` | You move the butterknife 1 to the drawer 1. |

## B P7

[原始 trajectory.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_3/p3c1_r05_replay_restart_002/attempt_2/episodes/B/P7/trajectory.json)；step_limit，50 步。

任务：clean some butterknife and put it in drawer.

| 步 | 实际动作 | 环境反馈 |
|---|---|---|
| 1 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a dishsponge 1, a egg 1, a houseplant 1, a soapbottle 1, and a tomato 1. |
| 2 | `go to countertop 2` | You arrive at countertop 2. On the countertop 2, you see a bread 2, a bread 1, a egg 3, a lettuce 2, a mug 1, a peppershaker 1, a plate 3, a pot 1, a sink 1, and a spoon 1. |
| 3 | `go to countertop 3` | You arrive at countertop 3. On the countertop 3, you see a fork 1, a kettle 1, a ladle 1, a lettuce 3, a pen 1, a soapbottle 3, a spatula 2, and a spoon 3. |
| 4 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is closed. |
| 5 | `open drawer 1` | You open the drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 6 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is closed. |
| 7 | `open drawer 2` | You open the drawer 2. The drawer 2 is open. In it, you see nothing. |
| 8 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a dishsponge 1, a egg 1, a houseplant 1, a soapbottle 1, and a tomato 1. |
| 9 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 10 | `go to drawer 3` | You arrive at drawer 3. The drawer 3 is closed. |
| 11 | `open drawer 3` | You open the drawer 3. The drawer 3 is open. In it, you see a spoon 2. |
| 12 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is open. In it, you see nothing. |
| 13 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 14 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a dishsponge 1, a egg 1, a houseplant 1, a soapbottle 1, and a tomato 1. |
| 15 | `go to drawer 3` | You arrive at drawer 3. The drawer 3 is open. In it, you see a spoon 2. |
| 16 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is open. In it, you see nothing. |
| 17 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 18 | `go to drawer 4` | You arrive at drawer 4. The drawer 4 is closed. |
| 19 | `open drawer 4` | You open the drawer 4. The drawer 4 is open. In it, you see nothing. |
| 20 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is open. In it, you see nothing. |
| 21 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a dishsponge 1, a egg 1, a houseplant 1, a soapbottle 1, and a tomato 1. |
| 22 | `go to countertop 2` | You arrive at countertop 2. On the countertop 2, you see a bread 2, a bread 1, a egg 3, a lettuce 2, a mug 1, a peppershaker 1, a plate 3, a pot 1, a sink 1, and a spoon 1. |
| 23 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 24 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is open. In it, you see nothing. |
| 25 | `go to drawer 3` | You arrive at drawer 3. The drawer 3 is open. In it, you see a spoon 2. |
| 26 | `go to drawer 4` | You arrive at drawer 4. The drawer 4 is open. In it, you see nothing. |
| 27 | `go to drawer 5` | You arrive at drawer 5. The drawer 5 is closed. |
| 28 | `open drawer 5` | You open the drawer 5. The drawer 5 is open. In it, you see a pen 3. |
| 29 | `go to drawer 6` | You arrive at drawer 6. The drawer 6 is closed. |
| 30 | `open drawer 6` | You open the drawer 6. The drawer 6 is open. In it, you see nothing. |
| 31 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 32 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is open. In it, you see nothing. |
| 33 | `go to drawer 3` | You arrive at drawer 3. The drawer 3 is open. In it, you see a spoon 2. |
| 34 | `go to cabinet 1` | You arrive at cabinet 1. The cabinet 1 is closed. |
| 35 | `open cabinet 1` | You open the cabinet 1. The cabinet 1 is open. In it, you see nothing. |
| 36 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a dishsponge 1, a egg 1, a houseplant 1, a soapbottle 1, and a tomato 1. |
| 37 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 38 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is open. In it, you see nothing. |
| 39 | `go to drawer 3` | You arrive at drawer 3. The drawer 3 is open. In it, you see a spoon 2. |
| 40 | `go to drawer 4` | You arrive at drawer 4. The drawer 4 is open. In it, you see nothing. |
| 41 | `go to drawer 5` | You arrive at drawer 5. The drawer 5 is open. In it, you see a pen 3. |
| 42 | `go to drawer 6` | You arrive at drawer 6. The drawer 6 is open. In it, you see nothing. |
| 43 | `go to drawer 7` | You arrive at drawer 7. The drawer 7 is closed. |
| 44 | `open drawer 7` | You open the drawer 7. The drawer 7 is open. In it, you see nothing. |
| 45 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a dishsponge 1, a egg 1, a houseplant 1, a soapbottle 1, and a tomato 1. |
| 46 | `go to countertop 2` | You arrive at countertop 2. On the countertop 2, you see a bread 2, a bread 1, a egg 3, a lettuce 2, a mug 1, a peppershaker 1, a plate 3, a pot 1, a sink 1, and a spoon 1. |
| 47 | `go to drawer 1` | You arrive at drawer 1. The drawer 1 is open. In it, you see a knife 1, and a spatula 1. |
| 48 | `go to drawer 2` | You arrive at drawer 2. The drawer 2 is open. In it, you see nothing. |
| 49 | `go to drawer 3` | You arrive at drawer 3. The drawer 3 is open. In it, you see a spoon 2. |
| 50 | `go to drawer 4` | You arrive at drawer 4. The drawer 4 is open. In it, you see nothing. |

## B P10

[原始 trajectory.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_3/p3c1_r05_replay_restart_002/attempt_3/episodes/B/P10/trajectory.json)；success，12 步。

任务：cool some apple and put it in microwave.

| 步 | 实际动作 | 环境反馈 |
|---|---|---|
| 1 | `go to fridge 1` | You arrive at fridge 1. The fridge 1 is closed. |
| 2 | `[投影含额外文本的非法动作，详见原轨迹]` | Nothing happens. |
| 3 | `open fridge 1` | You open the fridge 1. The fridge 1 is open. In it, you see a bowl 1, and a mug 1. |
| 4 | `go to countertop 1` | You arrive at countertop 1. On the countertop 1, you see a bread 1, a butterknife 1, a lettuce 1, a pan 1, and a pot 1. |
| 5 | `go to countertop 2` | You arrive at countertop 2. On the countertop 2, you see a cup 3, a knife 3, a knife 2, a spatula 3, and a tomato 1. |
| 6 | `go to diningtable 1` | You arrive at diningtable 1. On the diningtable 1, you see a apple 1, a cup 2, a cup 1, a egg 1, a mug 3, a potato 1, a soapbottle 1, a spatula 2, a spatula 1, a spoon 2, and a spoon 1. |
| 7 | `take apple 1 from diningtable 1` | You pick up the apple 1 from the diningtable 1. |
| 8 | `go to fridge 1` | You arrive at fridge 1. The fridge 1 is open. In it, you see a bowl 1, and a mug 1. |
| 9 | `cool apple 1 with fridge 1` | You cool the apple 1 using the fridge 1. |
| 10 | `go to microwave 1` | You arrive at microwave 1. The microwave 1 is closed. |
| 11 | `open microwave 1` | You open the microwave 1. The microwave 1 is open. In it, you see nothing. |
| 12 | `move apple 1 to microwave 1` | You move the apple 1 to the microwave 1. |
