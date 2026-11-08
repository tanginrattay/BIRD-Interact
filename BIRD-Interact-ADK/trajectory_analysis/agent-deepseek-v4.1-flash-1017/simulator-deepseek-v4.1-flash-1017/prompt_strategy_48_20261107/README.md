# Prompt 知识检索与用户交互对照实验：受阻记录

2026-11-07。本轮计划 48 次，**有效完成 0/48**。仅启动 baseline / repetition 1 / credit_11；约 10 分 25 秒后中断。其余 47 次未启动。不能计算四组均值、标准差、任务成功率或语义指标，也不能给出任何策略有效性的实验证据。

## 原因与证据边界

原 runner 成功完成数据库、Simulator、ADK Session 初始化，但首个 run_session 没有返回任务结果。独立诊断中，官方 models 接口、同步最小生成和仓库同步包装可用；异步 LiteLLM 最小生成返回 503 `Service is too busy`，带工具的异步最小调用约 30 秒超时。因此怀疑当前异步生成/工具通道的服务可用性问题；**正式任务没有返回 503，不能将诊断结果当成正式任务错误响应**。

中断后，原 runner 的 finally 成功调用 cleanup_task（HTTP 200）。本轮服务已停止。没有将中断当作任务失败，没有用历史 baseline 补齐。API 诊断不计入48次。

[原始档案与日志](../../../../results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107/README.md)；[状态与诊断](../../../../results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107/experiment_status.json)。

## 四种具体 Prompt

全部完整文本已保存，Baseline 与 HEAD 原始常量逐字一致；B、C 没有真实实现程序状态管理，均为模型遵循的 Prompt 指令。

| 条件 | 完整 Prompt | 差异 |
| --- | --- | --- |
| Baseline | [baseline.txt](../../../../results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107/prompts/baseline.txt) | 原文 |
| A | [A.txt](../../../../results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107/prompts/A.txt) | 预计1–2定义用单项，≥3考虑全量；避免全量后重复单项 |
| B | [B.txt](../../../../results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107/prompts/B.txt) | 信息缺口、已获内容、相关性、解决状态、预算和上下文负担；逐次判断信息增益并更新状态 |
| C | [C.txt](../../../../results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107/prompts/C.txt) | 完整B + 结构/已有领域知识/用户语义/未知概念四类不确定性，选择数据库、知识库或用户获取证据 |

实际成本为单项0.5、全量1、名称列表0.5、ask_user 2 bird-coins。沿用 a-interact / Lite / v1 two-stage / non-thinking / patience=3 / concurrency=1，Agent 4096输出上限，Simulator action200 / response1024，温度0。没有配置随机种子，不改变原随机性。当前 official deepseek-flash 映射 V4.1 Flash 1017，依据 [官方文档](https://api-docs.deepseek.com/quick_start/pricing/)；别名不是不可变模型快照。

## 指标对比与每任务行为

| 条件 | 有效完成 | 检索/交互/成功/Reward/预算 | 均值与样本标准差 |
| --- | ---: | --- | --- |
| Baseline | 0/12 | NA | NA |
| A | 0/12 | NA | NA |
| B | 0/12 | NA | NA |
| C | 0/12 | NA | NA |

credit_11、virtual_1、polar_M_4、cybermarket_1 均没有完整有效的新轨迹，不能描述本轮典型行为变化。没有任何假设得到支持或被否定。

所有指标的定义、语义评价标准与任务级固定信息需求见 [EVALUATION_PROTOCOL.md](EVALUATION_PROTOCOL.md)。[REVIEW_CHECKLIST.md](REVIEW_CHECKLIST.md) 明确需要保存的提问、知识覆盖与语义判断证据。[analyze.py](analyze.py) 为离线提取程序，已做语法检查；由于没有完成结果，**尚未通过本轮真实数据验证，也没有完成任何语义标注**。空 per_run_metrics / semantic_annotations 和全部NA的 group_summary 仅表明数据缺失。

## 既有数据与日志限制

credit_11 的 CES 知识原文规定分量封顶1.0，参考 SQL 未实现封顶；保留原数据与评分逻辑。四条任务都隐藏部分关键知识，必须区分工具覆盖和结合用户回答后的覆盖。长结果会被现有 Callback/ADK 日志截断，可用冻结可见知识库重建返回条目集合，但不能冒称恢复原始日志。Context Tokens 因原日志不保存 usage 而不可可靠获取。

下一步首先恢复同一模型、同一配置下的异步工具调用，再以新的结果目录重新完整运行48次，保留本次中断档案。研究层面最值得观察：**关键定义被隐藏时，早期准确澄清能否将节省的检索成本转化为信息覆盖与任务成功，而非只是更少调用或更早停止。** 目前这仍是待检验问题。
