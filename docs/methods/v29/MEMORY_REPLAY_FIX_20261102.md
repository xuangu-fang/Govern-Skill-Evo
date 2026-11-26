# v29 Replay 响应去重与 Memory 提交复用

2026-11-02。只修复第二阶段发现的重复展示、重复历史验证问题；没有调用模型、启动训练或真实 Test。五模块预算继续待定。

## Replay

模型输入中，完整普通响应仅保留在同 run 的 `attempts[0].assistant.content`。确认它与 `outcome.answer.raw_content` 精确相同后，才省略后者；不截断、不摘要、不更改预测答案、参考答案、评分或引用。原有 shared_initial 及重复 request_messages 省略继续保留。

原始 Actor 结果、完整文本事实、Call.input、Replay 校验 payload 和 Memory 审计束保留完整字段。新增 `restore_model_input()` 用于离线验证：展开 shared_initial 后，精确恢复该 run 的 request_messages 和 raw_content；不进入模型调用链。

Replay Prompt 仅补充这一展示说明，版本为 `v29_docvqa_replay_v2`，输入视图为 `v29_docvqa_pairs_shared_initial_v2`。安装 Prompt、设计 Prompt、三个 Replay 输入示例及中文说明已同步；输出合同与其他四模块不变。

## Memory

v29 原提交入口先完整 load，再进入继承提交器，继承提交器又扫描历史和 load。现在由单次 Memory 操作协调：

1. 在提交锁内首次读取并完整校验历史 bundle、Replay 输出、Active 提交链。
2. 同次操作复用已验证的 archive、contexts、view，以及完整批次和文本投影；每次引用继续检查传入内容。
3. 按既有合同计算本轮条目、修订、证据绑定和新 view；完成一致性核对后，先写不可变 commit，再原子更新 Active。
4. 返回值独立复制。临时结果在正常退出、异常和中断后丢弃；新调用和冷启动重新检查历史。

同次操作对涉及文件的原内容、目录成员、绑定任务和 Active 保留一致性核对；不重新解释和验证整条历史链。未扫描无关数据或加入运行源码保护体系。Memory 格式、ID 分配、幂等提交、pending 恢复、整条 Entry 修订，以及 ACCEPT/RETAIN 均可积累 Knowledge 的合同不变。

本次只优化现有 Memory 接口。完整 campaign 的准备、发布和联合恢复仍是第三阶段内容。

## 离线结果

完整验收 55 项通过，包含原有 45 项和新增 10 项。新增检查覆盖长响应/Unicode/空串/空白的无损还原、响应副本不一致拒绝、审计输入不变、历史遍历及批次校验次数、操作后缓存释放、提交格式与继承实现逐字节一致、依赖变化拒绝、pending/部分写入恢复，以及 Active 已写入后中断的幂等恢复。原有 commit 与 Active 之间中断的测试继续通过。

“已有一轮历史、每批两题”的合成场景：

| 指标 | 修复前核查观察 | 本次验收 |
|---|---:|---:|
| 一次新提交的底层历史链遍历 | 3 | 1 |
| 完整批次验证 | 80 | 4 |
| 完整 Actor 执行验证 | 未单独记录 | 8 |

四个批次是历史 Parent/Candidate 和当前 Parent/Candidate，各验证一次。上述统计不包含夹具构造和预注册；提交内的必要文件一致性比较仍执行。这些是调用次数，不能据此推算真实训练加速倍数。

同一短响应合成例中，固定原有共享机制，仅比较省略 raw_content 前后的 user JSON：9,746 → 9,539 字符。字符数不是 token 数，也不代表后续真实响应长度。完整输入仍可精确还原。

真实数据仅做静态检查：534 题、160/374 划分、439 张图片；没有生成真实题目响应。网络及模型请求数均为 0。

报告：[validation.json](../../../artifacts/verification/v29_memory_replay_fix_20261102/validation.json)、[unittest.log](../../../artifacts/verification/v29_memory_replay_fix_20261102/unittest.log)。

复现：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/didi/miniforge3/envs/DocVQA/bin/python scripts/verification/verify_v29_method.py --output artifacts/verification/v29_memory_replay_fix_20261102
```
