# 传输读取超时后的续跑修订

第2次Parent/P7尝试在第16次Actor请求触发ReadTimeout，原记录error_stage=model_request、没有响应正文或动作。run.py按原非429停点保存results.json并退出。本修订在下一次调用前冻结，依据用户明确要求继续重启直到全部任务结束，将“无响应的ReadTimeout”这一技术中断纳入续跑范围；不把语义失败、JSON/标签问题、截断输出或模型有效响应纳入重采样。

保留前两次所有数据与results.json。resume.py从attempt_3开始，继续同一Parent/P7、原模型与300秒读取超时、同样50步上限、每决策一次HTTP；无进程交接，子进程自然结束。仅429或model_request阶段的ReadTimeout可触发后续完整Episode重启，其他错误仍停止。429按既有退避240/300秒；ReadTimeout后等待60秒。当前已有429次累计Actor请求，仍不超过600总预算，每次开局预留50。

最终记录另存final_results.json，旧停止结果不覆盖。第一次正常终局即接受，不要求成功。除这项传输故障范围外，原输入、保护、归档、禁止事项不变。
