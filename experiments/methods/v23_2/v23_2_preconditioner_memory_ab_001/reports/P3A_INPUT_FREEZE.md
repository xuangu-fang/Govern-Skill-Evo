# P3-A 输入冻结与执行准备状态

**两组均为UNSENT请求，尚无真实Preconditioner响应；没有生成实验Effective Plan。结构测试中Keep/stop/identity夹具仅用于纯函数校验，未作为实验结果保存。**

实验控制、Schema及本地容量检查通过；当前proxy模型上下文窗口/精确分词未核实，因此**尚不能无条件批准进入P3-B发送**。不以历史官方调用成功冒充新路由保证。

## 1. 请求和快照

- [A_UNSENT.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/requests/A_UNSENT.json)：合法空Memory。
- [B_UNSENT.json](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/requests/B_UNSENT.json)：当时七条Memory及sources。
- [完整Original Diagnosis](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/original_diagnosis.json)、[Original Plan](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/original_plan.json)：字节相同原Diagnosis、语义相同Plan，保留decision/Goal/Updates/basis/顺序/Checks。
- [共同payload](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/common_payload_without_memory.json)、[system消息](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/system_message.json)、[Actor背景](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/background.json)、[证据选择索引](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/evidence_index.json)。
- [原Preconditioner模板](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/preconditioner_prompt.md)、[原Execution Context](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/execution_context.md)：均与正式contract+recoveries冻结内容一致，无历史候选补丁。
- [B Memory](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/memory_B.json)、[A Memory](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/memory_A.json)、[当轮Active索引](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/active_index.json)、[不可变来源哈希](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/source_hashes.json)。
- [输入哈希清单](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/input_manifest.json)、[最终预注册冻结](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/freeze.json)（同时冻结评价协议与空模板）。

| 哈希对象 | SHA256 |
|---|---|
| 原始Diagnosis文件 | `e026bb6dcd8ea2dedb85ee29c8f356299979e90e7d8153fd2b2f5597ce7f3fbb` |
| Plan规范化JSON | `d960969ccebd23ad013fea0130e6f1bfa85b2759deaad4dcc8ae78675d68ce62` |
| B Memory规范化JSON | `d641f11a7d4162762ff539bbe6bafe6b5ed6c3e2dea29b22389371f3d5281ccf` |
| 除Memory共同payload规范化JSON | `34ae6ad313daa728640fce7eb251a68fb653728d9173deda964c17f42ba6f549` |
| A请求文件 | `d6d60e11d20ffefc590316a3b3fce25e9a4e4183e0fcf06f82b84198eb10bd2a` |
| B请求文件 | `72d673dd856da2da2690094cf1496204484ec45b897d2750c6d20d9e7a41b8fa` |

文件SHA计算实际bytes；规范化JSON为sort_keys=True、ensure_ascii=False、紧凑分隔符。两种哈希不混用。每份完整请求含endpoint/body/timeout_seconds/attempts，不含API key；UNSENT状态由文件名及manifest标注，不往模型body加标记。

## 2. 一致性与契约

调用原 `pc.messages_for/preconditioner_input`，并与 `local.messages_for` 对照；消息解析后的顶层parent/plan/runs/grouping/command_sets完全一致，system逐字一致。移除user JSON的memory后，整个请求对象相同。唯一主动变量为 `body.messages[1].content` 内的 `memory` 对象。

A `entries=[]; sources={}`由原`empty_memory/validate_memory`接受，未换Prompt。B与round_input、实际历史请求、Active加载逐值相等；M10不在其中。选择仍是P1/P3/P6/P7/P8/P10、G1–G4、103候选表，未因Memory改变。

原编译器分别验证两组Keep、need_evidence、全撤回、同文本替换、引用权限；A引用不存在M6被拒绝，B合法接受。Goal/原Checks保留行为核验通过。该权限差异是Memory可用范围的预期结果，不是Schema变化。没有模型响应、没有语义评分器。

## 3. 当前路由与参数

| 项目 | 冻结值 |
|---|---|
| Endpoint | `http://llm-proxy.intra.xiaojukeji.com/chat/completions` |
| model | `deepseek-v4.1-flash` |
| temperature | 1.0 |
| thinking / reasoning_effort | enabled / medium |
| max_tokens / stream | 16384 / false |
| timeout | 配置300秒；现有HTTP函数connect=10秒、read=300秒 |
| 其余生成参数 | 无seed、top_p、presence/frequency penalty、response_format额外设置；按冻结body发送 |
| 重试 | P3-B每组一次请求；自动重试0，重试另行授权 |
| 容量 | 4,000,000消息字符；6,000,000消息UTF-8 bytes |

读取当前环境优先、.env兜底的base，仅保存非密配置和credential_present布尔值，不保存密钥。与 `model_routing.route_call_config` / `grouping.call_configuration` 核对一致。历史R05是官方deepseek-flash；本次两组同用当前内网deepseek-v4.1-flash，**只在本次AB内部控制一致，不宣称复用了历史服务端模型**。

现有代码变动已由P2记录；本次不恢复。`local.run_stage`先从环境解析路由且要求max_attempts=3，会自动技术重试，不能直接满足预注册一次请求限制。原CLI的上游loader也不能默认当作支持P1-B模板。未来应复用现有单次HTTP generator与原解析/编译，发前校验冻结消息/路由；本次仅记录，不新增联网运行器。已存在可复用单次调用能力，不需要改Schema或方法算法。

## 4. 容量、Token与成本可得估计

| 组别 | 消息字符 | 消息UTF-8 bytes | 同类历史比率粗估输入Token | 加16384输出上限 |
|---|---:|---:|---:|---:|
| A | 211,788 | 211,794 | 61,387–61,929 | 77,771–78,313 |
| B | 1,629,288 | 1,629,306 | 472,250–476,422 | 488,634–492,806 |

本地字符/byte admission均通过；B约A的7.7倍字符。估计用正式R04/R05/R06 Preconditioner保存的实际prompt_tokens与序列化消息字符比率：356103/1217815、470139/1613177、432863/1493400。原始usage与文件路径在capacity.json。

**这个区间只是三份历史比率的最小/最大值，不是置信区间、上下界或当前tokenizer精确计数；真实值可能在区间之外。** 当前无DeepSeek tokenizer，tiktoken包存在但编码缓存不存在，离线加载被网络隔离阻止，没有下载。不能把字符直接当Token，也不把其他旧版本的1M预算移植成当前模型服务能力。

历史官方R05已成功处理约47万输入Token，但当前内网模型的最大上下文、单请求限制及是否input+output共享预算没有可核验当前材料。记录unknown并作为执行前停点；不压缩sources、不减max_tokens、不切路由绕过。本地admission不是服务端context通过证明。

按上述不确定估计，两组累计输入约53–54万Token，另有最多32768输出预算，B占主要成本与延迟；缓存/实际生成量未知。未核实当前路由费率，因此不计算货币报价。本次实际新增API消耗0，Token消耗0。

## 5. 通过项与停点

- 唯一Original、两组仅Memory差异、六条当前证据对称、真实Active无M10、空Memory合法、装配/编译契约、评价预注册、不预设搜索答案、哈希可复现：离线通过。
- 方法/历史归档保护和零调用：见最终protection.json；没有源码/Prompt/Schema/Memory修改。
- 执行就绪：**待当前proxy模型上下文容量确认**。P3-B还须独立授权，并按上述单次发送规则进行编排；不得直接运行旧自动重试入口。
- 未完成项不隐去：不能声称“当前模型必然接收B”或“已准备好立即调用”。也没有证据证明B已经超限；这是未核实，不是已发生的API失败。

只新增本P3-A目录。复核入口 `PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python .../verify_freeze.py` 读取冻结产物、哈希及旧档保护，不重新生成请求。构造脚本拒绝覆盖已有input_manifest。调用数、环境执行均为0；P3-A到此停止。
