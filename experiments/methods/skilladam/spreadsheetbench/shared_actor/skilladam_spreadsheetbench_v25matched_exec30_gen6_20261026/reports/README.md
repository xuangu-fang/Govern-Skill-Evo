# SkillAdam：30次实际执行 / 每份程序6次请求

用户已授权中断旧训练，旧档完整保留。本实验从原始 initial Skill 重新开始，8批×15题、顺序不变，不复用旧轨迹或得分。

Actor并发4，输出32768；整题无累计时限，API单次300秒，程序单次600秒。30次只计实际执行；网络错误、截断和格式错误共同消耗生成每份程序的6次总请求额度。六次耗尽记为生成未完成，保留检查点、暂停批次，不评分、不跳过任务。无标准答案纠错反馈。

详见 restart_plan.json 和 docs/methods/v25/EXECUTION_GENERATION_BUDGETS.md。配置正式冻结后不得中途修改。No Skill / initial Skill旧测试仍属于旧条件，本次未重启测试集。
