# 原版与修改版配对运行诊断

使用同一 credit_11、同一 conda 环境、相同继承的 NO_PROXY/no_proxy、原 scripts/start_services.sh 与 orchestrator.runner，各运行一次。没有提前中断，两个请求均正常返回 HTTP200，并成功清理临时数据库。

| 代码 | Prompt | 耗时 | 结果 |
| --- | --- | ---: | --- |
| Git HEAD 原版 agent.py | 原始 Prompt | 51.2967秒 | 正常完成，SQL未通过 |
| 新代码，AINTERACT_PROMPT_APPENDIX 未设置 | 原始 Prompt | 50.837秒 | 正常完成，SQL未通过 |

详细数字以 comparison.json 为准。两次均为完整新 Session，保存全部结果、工具轨迹与 ADK events。两次用于诊断，不计入48次Prompt对照。

结论：本次未复现新增 Prompt 文件加载代码引起的运行故障，原版与修改版均能运行。上次卡住的确切根因尚不能确认；当时正式请求被提前中断，独立诊断503不能直接解释正式请求。不能断言必然是服务商或代理。后续保持本次验证通过的启动环境，在各组间只改变 Prompt。

agent_original.py / agent_modified.py 保存两版精确源文件；launch_environment.json 保存启动环境，密钥不记录。工作区 agent.py 已恢复修改版。
