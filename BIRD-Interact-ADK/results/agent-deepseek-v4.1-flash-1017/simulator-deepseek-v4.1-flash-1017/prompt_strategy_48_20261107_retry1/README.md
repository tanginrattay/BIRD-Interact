# BIRD-INTERACT Prompt策略对照：48次完整结果

**48/48有效完成，0任务级错误。** 四任务×四条件×三重复，2026-11-07；全部为本次新运行，原版/修改版的两次诊断不计入。实验矩阵、日志、Prompt哈希、282次知识定义查询响应（包含未找到）与预算链均通过核验，见 [validation.json](validation.json)。

[完整指标与每任务统计](../../../../trajectory_analysis/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107_retry1/README.md) · [结论与轨迹案例](../../../../trajectory_analysis/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107_retry1/FINDINGS.md) · [四种完整Prompt](../../../../trajectory_analysis/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107_retry1/PROMPTS.md) · [原版/修改版配对诊断](../original_code_diagnosis_20261107T083430Z/README.md)

## 配置与边界

Agent和Simulator均为官方deepseek/deepseek-flash，官方文档当前对应DeepSeek V4.1 Flash 1017；a-interact / Lite / 原版v1两阶段 / 非思考 / patience=3 / temperature=0 / concurrency=1。Agent输出上限4096；Simulator action200、response1024。初始预算按原公式：credit22、virtual20、polar24、cybermarket20。未设置模型或Simulator种子。

四组只改变Agent Prompt；原Baseline常量保持原文。唯一运行时代码差异是可选AINTERACT_PROMPT_APPENDIX追加文本。原版51.297秒、修改版关闭追加50.836秒，均正常完成credit_11，证据另存诊断目录。本批36次启用追加、12次Baseline也均正常完成。上次中断的确切根因仍不能追认，不据独立诊断503断言正式任务故障。

批处理调用原scripts/start_services.sh和orchestrator.runner，使用conda activate bird-interact，继承原NO_PROXY/no_proxy。未修改工具、成本、Callback、模型包装、Simulator、DB与benchmark。各任务由原runner reset=True创建新Session并初始化Simulator/任务DB；每批重启服务，日志中的invocation ID跨run无重叠。原runner不保存Session ID，不能声称档案里有该字段。

## 档案索引

- [eval_a_interact.json](eval_a_interact.json)：48条统一结果；新增condition/repetition/logical_run_id/source指针，原始字段保持原样。
- 各baseline_r1、A_r1等12目录：原runner的eval_a_interact.json、runner.log、services.log、verification.json；每目录4条任务。这些原始文件没有被合并文件替换。
- [summary.json](summary.json)：组均值、样本标准差和三轮四任务均值。
- [tasks.jsonl](tasks.jsonl)、[metadata.json](metadata.json)：精确任务与冻结设置、完整任务文件哈希。
- prompts/：四组完整文本与A/B/C追加文件；[baseline_integrity.json](baseline_integrity.json)、[prompt_control_validation.json](prompt_control_validation.json)为控制校验。
- [visible_knowledge_snapshot.json](visible_knowledge_snapshot.json)：各任务按原隐藏规则过滤的可见知识，用于离线核验，不注入Agent。
- [source_hashes.json](source_hashes.json)、[code_changes.patch](code_changes.patch)、[runtime_versions.json](runtime_versions.json)：源与依赖证据。
- [source_result_manifest.json](source_result_manifest.json)、[artifact_manifest.json](artifact_manifest.json)：源结果与整个归档的SHA256。

credit_11的CES知识分量封顶与GT SQL不一致，保留原评测。三条明确Simulator错答、四条漏答已按轨迹单列。源日志本来会截断长文本，完整保留原runner已保存的全部字段，不声称恢复未记录的内容。Context Tokens因无usage而不可得。语义指标为明示规则的单一离线审查，带完整证据，不是Agent自评，也没有独立双审。

本批48次为唯一比较主体；之前中断尝试及两次配对诊断另存，不计入均值，不补历史baseline。各实验仅三次重复，不声称统计显著性或论文创新。
