# V25 当前 Preconditioner／120题／8批×15题完整训练

2026-10-26 用户要求中断并删除10题实验后，从头启动本轮。使用当前项目源码及 history-primary-v2 Preconditioner，从原始 initial Skill 和空 Memory 开始；120题原顺序、1 epoch、Actor并发4、输出32768。

沿用连续时间线；不新增去重机制。每题30次实际程序执行，每份程序6次API总请求，无整题累计时限；API单次300秒、程序单次600秒。无标准答案或评分纠错反馈。只训练，不自动启动Test。

10题训练目录 _005 已按用户要求删除；此前其他实验及SkillAdam不修改。本轮配置为 config.json，冻结源码为 campaign/contract.json，启动记录 launch.json，日志 train.log，监控状态 monitor_state.json。每小时检查，最多连续3次失败恢复；预算耗尽不自动追加请求。
