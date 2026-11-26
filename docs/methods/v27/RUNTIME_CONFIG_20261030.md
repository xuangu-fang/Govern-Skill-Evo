# v27 容量配置对齐与独立环境补充

按用户要求，沿用 v24.1、v25、v26 实际运行配置中的容量保护阈值。本次仅配置、补充依赖和离线验证，不启动实验。

| 参数 | 已保存值 |
|---|---|
| max_input_chars | 4,000,000 |
| max_message_utf8_bytes | 6,000,000 |
| context_window_tokens | 不设置；恢复为可选检查 |
| 方法 retry_delay_seconds | 2.0秒，与 v24.1、v25、v26 对齐 |

方法重试间隔同时更新正式 JSON 配置与 `campaign_config(adapter)` 默认值；Actor 的重试间隔仍为1.0秒，其他配置不变。

`campaign_config(adapter)` 默认生成上述配置；显式提供 context_window_tokens 时仍校验其类型和范围，并在请求前检查输入估算＋输出预留。省略时只执行与旧版本一致的字符／字节硬上限检查，继续记录输出预留，不声称已验证服务端窗口。

配置文件为 [v27_lmb53_epoch1_deepseek_flash.json](../../../experiments/configs/v27_lmb53_epoch1_deepseek_flash.json)：保留53题优化、124题Test、六批单遍、SkillOpt原生初始Skill、deepseek-flash、Actor16384输出、五个方法模块16384／32768输出、六次总请求额度及原并发配置。没有创建运行目录。五个模块的主要职责、Prompt 和输出契约不变。

独立环境 `/Users/didi/miniforge3/envs/LiveMathematicianBench` 已补装 `python-dotenv==1.2.4`。安装命令使用该环境的完整解释器路径，未向其他环境安装。`pip check` 通过；版本已加入 requirements.lock.txt，runtime_manifest.json 的锁定文件哈希同步更新。environment.yml 已引用该锁文件，无需增加第二处包声明。

新增回归验证：

- 默认构造器和保存的配置一致，沿用4M／6M，五个模块均不设置 context_window_tokens；显式窗口仍可使用，非法值仍拒绝。
- 使用环境真实安装的 dotenv 解析合成 .env，并调用 v27 的凭据函数，验证有效配置、缺失密钥和错误地址。真实项目 .env 读取被替换为合成文件，未读取实际密钥、未调用服务端。

C01 继续使用自己的有界测试配置，结果及适用范围没有变化。其窗口预算不再成为正式实验启动的强制配置项。

独立环境离线验收共53个测试通过，网络连接尝试、真实模型请求、实验启动均为0，数据哈希未变化。这里的零网络计数指离线验收，不包含安装依赖时的包索引访问。

- [离线总报告](../../../artifacts/verification/v27_offline_runtime_config_20261030/validation.json)
- [逐测试结果](../../../artifacts/verification/v27_offline_runtime_config_20261030/test_results.json)
- [环境依赖补充记录](../../../artifacts/benchmarks/livemathematicianbench/dotenv_20261030/validation.json)

此前各轮验收报告保留，不覆盖。
