# AINET gpt-6.1-sol：同配置 72 题对照

| 分支 | P1 | P2 | 平均 reward | 运行错误 |
|---|---:|---:|---:|---:|
| baseline_main | 54/72 (75.00%) | 37/72 (51.39%) | 0.679167 | 0 |
| requirement_tracking | 52/72 (72.22%) | 35/72 (48.61%) | 0.651389 | 0 |

Requirement-tracking 平均 reward 差值：-0.027778。每组只运行一次，不能据此确定稳定的因果收益。

## 固定配置

Agent：AINET `/v1/chat/completions`，`openai/gpt-6.1-sol`，原 4096 输出上限（LiteLLM 映射为 `max_completion_tokens`）。网关拒绝 `temperature`，两组统一通过仅作用于 agent 的 `litellm.drop_params=True` 省略该参数；未显式指定 reasoning effort。

Simulator 与 2026-11-08 native 72 题保持一致：官方 DeepSeek endpoint，`deepseek/deepseek-flash`（历史实验由用户确认对应 DeepSeek v4.1 Flash 1017），`v1`、`two_stage`、thinking disabled、patience 3。Simulator、shared、DB 源文件逐一验证与昨日快照哈希相同。

复用昨日 72 题的原始字节及顺序；a-interact，并发 1。两组来自 main、state/requirement-tracking 的独立已提交快照；原工作分支和未提交改动保留。模型参数兼容启动失败的记录另存，未混入正式结果。

## 配对变化

- P1：新增通过 4 题，失去通过 6 题；具体 task IDs 见 paired_summary.json。
- P2：新增通过 7 题，失去通过 9 题；具体 task IDs 见 paired_summary.json。

## 用量（服务报告，不等同于账单）

| 组别 | Agent prompt | Agent output | Agent total | Simulator total |
|---|---:|---:|---:|---:|
| baseline_main | 5367053 | 102332 | 5469385 | 1238090 |
| requirement_tracking | 7583714 | 186199 | 7769913 | 1453432 |

缓存及 reasoning 用量详情见各组 validation.json；未取得单价和账单，不推算金额。服务返回的模型 ID 不构成底层模型身份的独立验证。

## 证据

- [Baseline 完整逐题轨迹](baseline_main/markdown/README.md) · [交互式报告](baseline_main/report.html) · [原始结果](baseline_main/eval_a_interact.json)
- [Requirement 完整逐题轨迹](requirement_tracking/markdown/README.md) · [交互式报告](requirement_tracking/report.html) · [原始结果](requirement_tracking/eval_a_interact.json)
- [逐题配对 CSV](paired_comparison.csv) · [配对摘要](paired_summary.json) · [实验配置及 commit](manifest.json)
- [State 结构及持久化审计](requirement_tracking/state_validation.json)：不评估 requirement 的语义覆盖或错误消歧。

原始 session、ADK events、工具轨迹、日志、source_snapshot 和 SHA-256 均保留。Markdown 无新增截断；源数据中已有的截断无法恢复。

最终验证：两组所有完整性检查通过；State 637/638 次更新接受，1 次拒绝，State 回放与持久化检查通过，未因 State 协议阻断原生工具调用。原工作区 diff/status 完全保留，数据库名列表恢复，PostgreSQL 恢复停止状态。详见 final_validation.json。
