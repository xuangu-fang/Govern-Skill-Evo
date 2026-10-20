# V22 当前模型路由准则：Actor 与更新模块

2026-10-16，用户更正。本文取代此前 `EXPERIMENT_MODEL_ROUTING.md` 的未来配置准则；旧文及失败档案保留，作为当时请求依据，不追溯改写。

|实际生效的 OPENAI_BASE_URL|Actor|分类及全部更新模块|
|---|---|---|
|`http://llm-proxy.intra.xiaojukeji.com`|`deepseek-v4-flash`|`deepseek-v4-pro`|
|`https://api.deepseek.com`|`deepseek-flash`|`deepseek-flash`|

更新模块包括 Diagnosis、Fusion、Editor、Replay／Memory Learning；全局分类同样使用表中更新模型。官方端不再使用 `deepseek-v4.1-flash`，也不保留原 Actor 模型。代理端维持 Flash Actor＋Pro 更新模块。

## 当前实现

独立修订身份为 `v22.endpoint_models.v2`，实现见 [model_routing.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/19_endpoint_actor_evolution_routing/revision/src/skill_evolution/v22/model_routing.py)。已有 [19 运行入口](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/19_endpoint_actor_evolution_routing/run.py) 在加载计划前读取实际环境配置；尾斜杠及 `/v1` 受支持。进程环境变量优先于 `.env`，密钥不写入路由记录。

[continual_runtime.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/19_endpoint_actor_evolution_routing/revision/src/skill_evolution/v22/continual_runtime.py) 在内存计划中同步绑定 `models.actor`、`models.evolution`、`classification.model`；Actor 调用和全部五个语义阶段读取该绑定。冻结后基址或最终模型不一致时停止，不静默降级或切换。原计划文件不会被路由解析覆盖。

19 的算法基线仍为 v3，不能将其直接当成已集成 P1 的运行器。P1 位于独立 17 revision，profile 为 `v22.unified_dsc.v4`；后续 P1 验证应显式使用上述路由映射和新的请求冻结，不更改其 D/S/C 规则、编码、证据、输出 Schema 或检查标准。旧冻结入口不会自动获得新模型配置。

## 与既有失败及预算的边界

17 的官方验证曾按当时指令使用 `deepseek-v4.1-flash`，8 次请求均被服务拒绝。原 request、response、model、Token 未返回状态及哈希必须保持原样；不将失败档案中的 model 改为 `deepseek-flash`。服务报错列出了 `deepseek-flash`，但这不等于当前请求参数、模型语义和成本已通过验证。

本次更正模型准则没有执行新的模型 API 或 ALFWorld，也没有重置已消耗的 8 次请求上限。后续继续真实验证须另行授权新的预算并冻结新的请求；不能对旧失败目录直接重跑。已有 No Skill、Memory、Gate、任务边界和算法不因路由更正而改变。
