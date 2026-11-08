# Native Requirement State：完整 72 题实验

任务文件直接复制历史 baseline72_v1_20261028/tasks.jsonl，72 个 ID、顺序、文件 SHA256 一致。metadata.json 记录来源、配置、版本和比较限制。

按用户确认，本次 Agent 和 Simulator 的模型均归档为 DeepSeek v4.1 Flash 1017；API 请求名仍如实保留为 deepseek/deepseek-flash，两者使用 DeepSeek 官方 API。原 metadata 与 manifest 保存在 *.at_completion.json；原始日志中的旧路径为历史记录，不改写。

配置：a-interact，concurrency=1，v1，two_stage，patience=3，Agent/Simulator 均 deepseek/deepseek-flash。保持通过 8 题验证的生产源码；source_snapshot/ 和 working_tree.patch 保存运行版本，无新 commit。

- supervisor.log、service_pids.json、runner.log：启动、进度、服务归属。
- eval_a_interact.json：每完成一题原子保存完整结果、工具 trajectory、State 历史与当前评测指标。
- state_observations.jsonl：实际注入 State、回调前后、原生工具调用保留与 State 错误。
- sessions/<task>.json：每题完整真实 Session Events（含文本、工具参数与返回、state_delta）。
- simulator_usage.jsonl：仅记录原有模拟用户调用的 usage，不增加调用或改回复。
- 完成后自动生成 state_validation.json、trace_<task>.md、state_missing_and_invalid.json、summary.json、RESULTS.md、manifest.json。
- Coverage/False Resolution 保持待语义标注，不由 Runtime 结构或 SQL 成绩代算。
- run_completion.json 记录退出及后处理结果；database_cleanup.json 核对数据库列表恢复。结束只停止本次服务，并在没有其他客户端连接时将原本停止的 PostgreSQL 恢复停止。

启动后请保持电脑运行。若再次关机，已有逐题结果仍在，但进行中任务的内存 Session 无法恢复；恢复运行需要另行核对，不应直接覆盖本目录重跑。
