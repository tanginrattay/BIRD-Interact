# 离线审查记录模板

每条 run 的 task_cards 保存自动提取指标和带工具序号的证据，trajectory 保存原始完整 JSON 字段。语义判读写入 semantic_annotations.json：键为 `<condition>_r<repetition>__<task_id>`，每项包含 metrics、resolved_information_units、unresolved_information_units、ask_reviews、coverage_evidence、semantic_redundancy_evidence、notes。

metrics 必须包含 knowledge_coverage_tools_plus_user、ambiguity_resolution_rate、user_semantic_resolution_rate、unnecessary_ask_rate、unnecessary_ask_count、partially_unnecessary_ask_count、semantic_redundancy_calls（排除精确重复）、semantic_redundancy_definition_occurrences。无法判断的指标为 null 并解释证据缺口。

覆盖与解决单位必须引用实际结果或回答，不依据 Agent 的自述。一次 ask 可能完全或部分解决多个单位；也可能回复不完整、与 GT 冲突或仅重述概念。问得早不等于问得正确。

全量检索的相关率是条目级；同时提供 useful-query rate，二者回答不同问题。若未找到定义而重复查询名称变体，应标 repeated failed lookups / 无效探索，不假称取得了重复知识。

应审查：

1. 单项/全量的成本变化是否被名称查询成本抵消。
2. B 是否减少重复与低相关查询，是否仅因更早停止或未覆盖关键知识。
3. C 是否在首次大规模检索前提出真正重要的语义澄清；不能只比较 ask 总数。
4. C 的问题在提问时是否已可由现有可见证据回答。
5. Simulator 回答是否给出正确完整公式、阈值与视图/输出意图；单独保留 simulator 错误标记。
6. SQL 是否采用已获信息；分离获取成功与使用失败。
7. P1/P2 成功是否可能受知识库/GT 不一致、空结果或 DDL 评测影响。
8. 若减少查询同时降低覆盖或成功率，应明确报告。

没有完整有效 runs 时，不生成组均值或策略优劣结论。API 错误、超时、人工取消均保留为基础设施状态，不当作 reward=0 的策略失败。
