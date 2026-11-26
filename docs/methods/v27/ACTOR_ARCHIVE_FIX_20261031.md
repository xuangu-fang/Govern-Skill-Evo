# LMB Actor 请求与失败尝试归档校验修复（2026-10-31）

修复两路共用 Actor 的归档完整性缺口，不改变当前配置、模型参数、六次总尝试额度或截断重试策略。SkillAdam 原生优化器、证据压缩、Prompt、SDK重试和patch尝试次数保持不变。

## 实现

1. 每次请求在 started 标记之前冻结 request.json，内容由当前完整消息与冻结模型配置构造。真实传输使用同一构造器；完成与未完成归档都逐项核对 endpoint、messages、模型、输出上限、温度和thinking等参数。
2. 每个失败 error.json 原子写入自身checksum和 archive 指纹，记录请求、started、响应JSON、HTTP状态和原始正文的字节哈希及缺失状态。恢复时拒绝新增、删除或改动的失败档案，并重新核对可解析响应／HTTP错误的失败分类。
3. HTTP原文和JSON副本同时存在时必须一致。最终成功响应仍可在JSON副本丢失、完整HTTP档案可验证时只读恢复；失败尝试已提交的指纹不允许被回填覆盖。
4. Campaign、Test和SkillAdam整体恢复在提交任何Actor worker前检查全部已完成和未完成任务。发现损坏即停止；不能先执行其他待完成题目或新增优化器请求。
5. 真正未完成请求仍能恢复：只有已冻结请求但尚无started标记时复用原槽位；started后没有结果时计入unknown并消耗已用槽位；已有完整JSON／HTTP响应时本地解析；六次总额度不重置。

只有内部审计文件增加字段，Actor输出、五模块输入／输出契约不变。历史运行保留，当前源码身份变化不会被用于续跑旧冻结目录。

## 离线验收

新增测试覆盖Campaign、124道合成Test和SkillAdam恢复：修改或删除实际请求、失败响应JSON、HTTP正文／状态、错误记录，均在启动worker前拒绝，Actor／优化器零新增请求、原归档不被改写。恢复原档案后，真正待完成任务可继续；已完成任务不重发。

另覆盖全部未完成批次中的失败档案损坏、请求准备阶段中断、HTTP 503、畸形JSON、网络错误，以及已有截断重试和恢复边界。

最终报告：
- [v27](../../../artifacts/verification/v27_actor_archive_fix_final_20261031/validation.json)
- [SkillAdam](../../../artifacts/verification/lmb_skilladam_actor_archive_fix_final_20261031/validation.json)

以上为独立LMB环境的合成离线验收，不把107项映射称为全部语义场景实质通过。用户已授权验收通过后，两路从初始Skill使用新目录重新训练，各自训练成功并验证最终Skill后开启独立Test；失败不会自动扩充重试额度或启动Test。

最终验收：独立LMB环境 v27 69/69、SkillAdam 32/32 通过，失败、错误及网络连接尝试均为0；真实模型请求0，原始数据与prepared数据哈希未变。新增6项回归，含跨Campaign／合成Test／SkillAdam的15种损坏子场景。

## 本次新运行

已于北京时间2026-10-31 11:52启动两路训练，各自从原生初始Skill开始；各自成功结束并校验最终Skill后自动开启124题Test。实际状态以[启动与执行记录](../../../artifacts/benchmarks/livemathematicianbench/retrain_test_launch_20261031_114845/README.md)为准。历史训练及Test结果不覆盖。
