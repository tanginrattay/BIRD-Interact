# AINET gpt-6.1-sol：72题分支对照归档

2026-11-09完成，归档于`state/requirement-tracking`。先运行`main@8138403`，再运行`state/requirement-tracking@4ff1580`，每组72题。测试使用独立源码快照；原工作区`state/requirement-tracking-2calls`的未提交改动没有进入实验。

- [正式对照报告](comparison72_20261109T030938Z/COMPARISON.md)：Baseline P1=54/72、P2=37/72、平均reward=0.679167；Native State P1=52/72、P2=35/72、平均reward=0.651389。
- [最终验证](comparison72_20261109T030938Z/final_validation.json)：两组完整性和源码校验通过；State回放与持久化检查通过；637次更新接受、1次拒绝，未阻断原生工具；原工作区diff/status保留，数据库及PostgreSQL状态恢复。
- [逐题配对结果](comparison72_20261109T030938Z/paired_comparison.csv)与[配对摘要](comparison72_20261109T030938Z/paired_summary.json)。
- [配置与版本](comparison72_20261109T030938Z/manifest.json)、各组`source_snapshot`、原始JSON、Session、工具轨迹、ADK events、日志、逐题Markdown和HTML均保留。各组`evidence_sha256.json`记录证据校验值。
- [首次启动失败](comparison72_20261109T030623Z/status.json)：LiteLLM在发送模型请求前拒绝temperature=0，3题记为运行错误后停止；不纳入正式144题结果。[预检](comparison72_20261109T030938Z/tool_parameter_preflight.json)确认AINET省略temperature后支持原生工具调用，两组统一使用仅作用于agent进程的参数兼容设置。

Simulator保持2026-11-08配置：官方DeepSeek接口、`deepseek/deepseek-flash`别名、v1双阶段、非思考、patience=3；题目原始字节及顺序相同，并发1。实际测试配置与限制以正式报告为准，不将网关模型名当作底层模型身份的独立验证，不推算账单金额。

归档保留正式运行与首次启动失败的所有常规文件。Python缓存和指向本地数据集的绝对符号链接不入Git；复现需要原始`bird-interact-lite`数据集、本地PostgreSQL环境和自行配置的密钥。`source_snapshot/bird-interact-lite`链接仅供当时本机运行，不属于源码或证据哈希清单。更早的`comparison72_20261109T030619Z`只留下空目录，没有可归档文件。
