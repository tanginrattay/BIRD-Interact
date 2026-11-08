# 48-run Prompt strategy experiment — 2026-11-07

状态：模型异步服务不可用，已停止本次尝试。有效完成 **0/48**，中断尝试1次，其余47次未启动。详见 experiment_status.json 和 validation.json。没有生成正式任务结果 JSON，也没有策略得分。

Agent / Simulator：官方 deepseek/deepseek-flash；官方模型映射为 V4.1 Flash 1017。a-interact / Lite / v1 two-stage / non-thinking / patience=3 / concurrency=1。

## 文件

- prompts/baseline.txt、A.txt、B.txt、C.txt：四种完整 Prompt；*_appendix.txt 为追加策略。
- tasks.jsonl：四条原始任务，保持全部 benchmark 字段和 ID。
- metadata.json、source_hashes.json、code_changes.patch：控制变量、源代码校验、最小 Prompt 选择改动。
- visible_knowledge_snapshot.json：离线研究用，各任务实际可见的知识库集合及源哈希；不注入 Agent。
- run_blocks.sh：批量调用仓库现有 scripts/start_services.sh 和 orchestrator.runner，不另实现任务运行逻辑。
- baseline_r1/ 等12个批次目录：原 runner JSON、runner.log、services.log、verification.json。
- batch.log：批次开始和完成状态。

批次顺序：r1 baseline/A/B/C；r2 B/C/baseline/A；r3 C/A/baseline/B。每次任务由原 runner reset=True 创建新 ADK Session，并初始化 Simulator 与任务数据库。每批重启原有三个服务，清除运行时历史；不共享 Agent Session。

所有工具、Callback、预算、模型/Simulator 参数、数据库源与 benchmark 数据保持原样。唯一运行时代码改动是从可选 AINTERACT_PROMPT_APPENDIX 文件追加文本；未设置时使用逐字相同的原始常量。

## 已知限制

原日志截断部分长文本，不保存 usage；Context Tokens 不可得。离线知识条目集合通过原知识库与 deleted_knowledge 过滤规则重建，不能声称恢复了截断日志。

credit_11 的 CES 定义含分量封顶要求，而参考 SQL 没有封顶；不修正此既有差异，分析中单独标注。四条任务均隐藏部分必要定义；区分 tool-only 覆盖与结合用户回答的覆盖。原 Callback cost 字段是标价，实际扣费另按预算差额核验。

完整分析见同名 trajectory_analysis 目录中的 EVALUATION_PROTOCOL.md、per_run_metrics.csv、group_summary.json、task_cards/ 和 trajectory/。

诊断证据及中断时间见 experiment_status.json。原 runner 已成功 cleanup_task（HTTP200）。分析目录同名 README.md 明确列出全部指标缺失与本轮无法得出的结论。
