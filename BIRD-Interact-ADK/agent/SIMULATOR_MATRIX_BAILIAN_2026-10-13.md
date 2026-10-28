# 百炼多型号simulator筛选：接手说明

17通用模型×原版v1/v2×固定4问已全部完成，无需恢复或重跑。原始轨迹、自动初筛、内容复核及推荐见 [完整汇总](../results/simulator_matrix_bailian_20261013/README.md)。

136次澄清、272阶段请求，全部HTTP200；总报告tokens=900791，单型号最多58322。26次fallback中20次第二阶段有非空无标签原始文本，其中14次正常stop。43阶段length；仅思考模型还会由reasoning占满原版输出额度。故障不能概括为模型不会回答。

优先候选为deepseek-v4.1-flash + v1，备选qwen3.7-max-2026-06-08或qwen3.5-plus-2026-02-15 + v1，但未自动修改主配置；当前.env仍是Lite / qwen3.7-plus / v1。DeepSeek候选也有公式/字段披露风险，其他候选存在分组纠错遗漏。四问筛选不是稳定性证明或完整官方测评。

Kimi2.5 v1在SQL索取中披露表列与要求，Kimi2.7-code v1直接输出参考SQL片段；不能把初筛4/4误读为语义/信息披露全部通过。完整逐条复核包含这些问题。

新增scripts/simulator_matrix.py以隔离子进程复用原版_ask_sync；不调用system agent或SQL评分，不修改prompt、解析、原预算，无重试。最多四模型并发。每型号v1 action=200、v2 action=500、response=1024；不会为思考补充预算。代码及数据hash已保存。

user_simulator/bailian.py扩大裸型号allowlist，全部走simulator专属百炼端点/密钥；不能把裸百炼ID改为厂商前缀，以免走独立API。is_bailian_simulator用于server路由，DeepSeek system agent仍由shared/llm.py独立接入。部分仅思考型号按专页配置true，结论限于记录参数。13项离线检查通过，原版协议函数及prompt一致性检查通过。

修改前快照Git提交仍为5aa6d55；原版对照451fe2c。恢复和新筛选实现尚未提交，保留既有工作树。中断后的续接只完成汇总和交接文档，没有再次调用模型。
