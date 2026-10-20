# V22 实验与验证的模型路由准则

2026-10-16。根据用户最新要求，后续新建实验、语义验证及另行冻结的恢复运行，均在准备阶段根据实际生效的 `OPENAI_BASE_URL` 选择更新模型。

| 实际 API 基址 | 更新／语义阶段模型 |
| --- | --- |
| `http://llm-proxy.intra.xiaojukeji.com` | `deepseek-v4-pro` |
| `https://api.deepseek.com` | `deepseek-v4.1-flash` |

此规则覆盖全局分类、Diagnosis、Fusion、Editor、Replay／Memory Learning。同一次冻结验证中的原表示与 P1 表示应使用同一路由模型和相同请求参数。**Actor 未被此次授权改变**；环境执行仍遵循其单独冻结的模型与参数，不能将语义阶段映射自动扩展到 Actor。

## 准备、冻结与执行

1. 在冻结消息和预算之前读取实际生效的环境配置。现有独立运行器使用 `.env` 的 `override=False`：已经存在的进程环境变量优先于 `.env`。档案记录生效基址、路由身份、原声明模型、最终请求模型，不记录 API key。
2. 对上述两个已指定端点应用映射；支持尾部 `/` 和 `/v1`。URL 不得携带账号密码、查询参数或 fragment。其他端点在当前实现中保留显式声明模型；这不表示已为其他端点建立新的模型映射，准备材料必须如实列出其配置。
3. 冻结实际请求模型、基址、完整 messages、请求参数、预算、来源及控制器代码。请求和原始响应分别记录请求模型及服务返回模型，不用配置名代替真实调用记录。
4. 冻结后不得静默切换端点或模型。环境变量变化、请求模型不一致或模型不可用时保留停点；不得自动降级、改模型重试或消耗额外语义调用。已授权的新端点／模型应通过独立的新冻结记录明确协议边界。
5. 不改写旧实验的配置、Prompt、失败记录、Token 和费用归属。旧检查点能否复用取决于其事实及来源身份是否保持一致；更换语义模型后的续行必须明确标注，不能声称原冻结协议从未变化。

## 与算法及 P1 编码的关系

模型路由是运行配置，P1 是无损消费编码，D/S/C 是更新算法；三者分别标识、分别冻结。端点映射不授权修改 Goal／Update／Watch／Open、D/S/C 决策规则、输出 Schema、Gate、Memory 应用、证据选择或调用次数。

`18_endpoint_model_routing` 使用独立运行修订身份 `v22.endpoint_evolution.v1`，其算法基线仍为 `v22.unified_dsc.v3`。P1 实现位于独立 `17_p1_input/revision`，算法 profile 为 `v22.unified_dsc.v4`，消费编码为 `v22.p1_shared_input.v1`。不能仅因 18 已实现路由，就假定 17 或历史恢复脚本已自动取得该能力；新验证控制器应显式采用映射并记录其来源。

跨端点或跨模型的旧结果只能作为背景，不能直接当作 P1 成本或语义效果的匹配对照。单次同模型对照也只能检验表示风险，不能识别压缩的因果收益。

## 当前实现只读复核

- [model_routing.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/18_endpoint_model_routing/revision/src/skill_evolution/v22/model_routing.py) 中两项映射与本准则一致；规范化处理尾斜杠及 `/v1`，未设置自动备用模型。
- [continual_runtime.py](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/18_endpoint_model_routing/revision/src/skill_evolution/v22/continual_runtime.py:201) 在内存计划中同步设置 `models.evolution` 与 `classification.model`，不改写原计划文件；冻结与实际调用会校验同一路由。
- [live_dependencies](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/18_endpoint_model_routing/revision/src/skill_evolution/v22/continual_runtime.py:309) 将最终模型用于全部语义阶段，Actor 继续读取 `models.actor`。
- [运行说明](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v22/18_endpoint_model_routing/README.md) 明确旧恢复脚本不自动升级，冻结后改变端点需要独立准备；它不证明模型实际可用。

本次复核仅新增本说明，并对映射进行离线断言；没有修改 17／18 的实现或冻结材料，没有发送模型请求或运行环境。

## 后续实际验证状态（2026-10-16）

上述映射是用户指定的配置准则，并不保证服务接受模型名称。随后 17 的独立 P1 验证控制器按官方路由发送 8 个冻结请求，服务均以 HTTP 400 拒绝 `deepseek-v4.1-flash`，返回支持的 API 名称为 `deepseek-flash`、`deepseek-v4-pro`。没有自动替换模型或追加请求。原准则不被服务报错静默改写；未来有费用的运行需要先明确用户认可且服务可接受的模型标识，再建立独立冻结。详见 [实现与验证报告](/Users/didi/Desktop/Govern-Skill-Evo/docs/methods/v22/UNIFIED_DSC_P1_IMPLEMENTATION_VALIDATION.md)。这项请求配置问题不能解释为 P1 或 D/S/C 语义失败。
