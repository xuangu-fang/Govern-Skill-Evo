# Terra R05 / R06 重跑：连通性检查

2026-10-28。当前状态：**内网代理模型访问被拒绝，尚未启动实验重跑。**

## 已验证

- 使用用户指定的内网地址，现有环境中的凭据与本次提供的凭据一致；未修改或归档凭据。
- `POST /chat/completions`，模型名 `gpt-6.1-terra`：HTTP 401，`team_model_access_denied`。
- 同一路径，模型名 `openai/gpt-6.1-terra`：同样返回 HTTP 401，`team_model_access_denied`。
- `GET /models` 和 `GET /v1/models` 均返回 HTTP 200，均列出 17 个模型，其中没有 Terra 或其他 GPT 模型。
- 可确认网络和代理可达、当前凭据能读取模型列表；不能据此确认代理未部署该模型，只能确认当前凭据下请求被拒绝，模型列表中不可见。

## 请求参数

最小探测请求使用 `reasoning_effort=medium`、`max_completion_tokens=256`、`stream=false`，消息为要求回复 OK 的短文本。未发送 DeepSeek 的 `thinking` 参数，也未发送 `temperature`。

根据 OpenAI Docs，Terra 支持 medium 推理；Chat Completions 的 `max_completion_tokens` 包含可见输出与推理 token。当前拒绝发生在模型访问阶段，因此**尚未验证内网代理接受这些参数，也未确认实际后端响应模型**。256 仅为连通性探测预算，不是正式模块重跑预算。

- [Terra 官方模型文档](https://developers.openai.com/api/docs/models/gpt-6.1-terra)
- [Chat Completions 参数文档](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)

## 实验边界

此次没有发送 R05 / R06 的实验输入，没有运行任何方法模块、Actor、完整训练或测试；没有修改方法 prompt 和生产代码。仅新增本目录中的探测记录。

原计划仍为：先在当前 prompt 下固定原始输入，逐模块对照；连通并确认实际模型及参数之后再执行。Diagnosis 对照 DeepSeek 的 v5 重跑；其他模块使用各自原始输入；不把新 Skill diff 与旧 Candidate 轨迹混用。需要为当前凭据开通目标模型，或确认该模型在内网代理中的可访问别名，之后才能继续。

原始请求和脱敏响应见 `connectivity/`，机器可读状态见 `status.json`。
