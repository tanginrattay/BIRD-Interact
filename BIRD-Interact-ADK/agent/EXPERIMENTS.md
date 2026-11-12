# 实验索引与结论

最近核查：2026-11-12。以下数字来自已有结果与分析报告，本轮未重跑。P2 的分母为全部题目，包含 P1 gate；不能把未进入 P2 的记录一律解释为独立 follow-up 失败。平均 Reward 保留四位小数。

## 72 题主线

共同任务文件 SHA256：`dcaa82470060263d08f023d92ee15218b10eb80cf50479c2cf66aace74f50296`。五组均为 Lite / a-interact，v1 / two_stage，patience=3、concurrency=1；Simulator 归档名为 DeepSeek V4.1 Flash 1017。Agent max_tokens=4096，Simulator action=200 / response=1024。详见 [完整五组分析与可比性核查](../trajectory_analysis/docs/five_variants_trajectory_analysis.md)。

| 日期 | Agent / 方案 | P1 | P2 | 总 Reward | 平均 Reward | 证据 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 10-28 | DeepSeek / Baseline | 29/72 | 13/72 | 24.2 | 0.3361 | [结果](../results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/baseline72_v1_20261028/README.md) |
| 11-08 | DeepSeek / Native | 15/72 | 7/72 | 12.6 | 0.1750 | [结果](../results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/requirement_native72_20261108T101116Z/README.md) |
| 11-08 | DeepSeek / 2-calls | 27/72 | 17/72 | 24.0 | 0.3333 | [结果](../results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/requirement_2calls72_20261108T114900Z/README.md) |
| 11-09 | GPT-6.1-sol / Baseline | 54/72 | 37/72 | 48.9 | 0.6792 | [对照报告](../results/agent-gpt-6.1-sol/simulator-deepseek-v4.1-flash-1017/comparison72_20261109T030938Z/COMPARISON.md) |
| 11-09 | GPT-6.1-sol / Native | 52/72 | 35/72 | 46.9 | 0.6514 | 同上 |

所有日期为 2026 年。五组各有 72 条结果；完整 session 和逐题证据的具体覆盖情况以分析报告及各组校验文件为准。

实验身份与限制：

- DeepSeek Baseline ID：`baseline72_v1_20261028`，合并百炼 11 题与 Platform 61 题。与 11 月 State 实验不是同期、同渠道的完全冻结对照。
- Native ID：`requirement_native72_20261108T101116Z`；2-calls ID：`requirement_2calls72_20261108T114900Z`。两者具体实现以实验目录的源码快照和 manifest 为准。2-calls 当时为 `92a299c` 加可靠性修复 diff，不能只用该 commit 重建。
- GPT ID：`comparison72_20261109T030938Z`；Baseline `main@8138403`，Native `state/requirement-tracking@4ff1580`。Agent 经 AINET，两组均省略不支持的 temperature 参数，Simulator 保持 DeepSeek。两组任务错误均为 0。
- 同题可配对不代表同反馈；各组行动不同会引出不同 Simulator 回复。2-calls 的指令、调用阶段和实现也不同，不能视为仅改变一次调用的纯消融。

已观察到：DeepSeek Native 27/72 题以 DSML/XML 样式伪工具文本终止，没有对应结构化调用；这与 State 校验拒绝不是同一问题。2-calls 总 Reward 接近 Baseline，但成功集合改变，Agent tokens 为 17,861,715，约为 Native 的 2.58 倍。GPT Native 也没有总体提升。完整行为证据、配对统计与语义限制见五组报告，不以聚合得分代替逐题解释。

## Part B：跨 Backbone 行为分析（2026-11-12）

这是对既有实验的离线分析，不是新运行。[报告](../trajectory_analysis/docs/gpt_deepseek_transfer_analysis_part_b.md) · [证据索引与原始位置](../trajectory_analysis/docs/part_b_data/evidence.json)。报告重新解析五组 evaluator、288 份现存 session 和 4,869 条工具记录，对 72 题做 Baseline 配对/行动序列筛查、12 题做语义决策核查；个案不代表全量行为发生率。DS Baseline 缺完整 session，截断内容保持 unavailable。

| Baseline 比较范围 | 两者成功 | 仅 GPT 成功 | 仅 DeepSeek 成功 | 两者失败 |
| --- | ---: | ---: | ---: | ---: |
| P1，全 72 题 | 29 | 25 | 0 | 18 |
| P2，全 72 题，含 P1 gate | 13 | 24 | 0 | 35 |
| P2，两者均通过 P1 的 29 题 | 13 | 7 | 0 | 9 |

GPT 的可借鉴行为包括更早识别会改变 SQL 的缺口、切换信息源、落实投影/行粒度约束以及选择可区分原因的诊断；部分 SQL 推理差异仍可能依赖 Backbone。`disaster_2` 展示缺定义后的知识漫游；`credit_4`、`robot_10` 展示提问覆盖；`archeology_M_4` 展示已有约束未落实；`solar_10` 展示排名诊断问题。`robot_8`、`virtual_1` 中 DeepSeek 有局部优势，`mental_M_2` 有共同正例，`gaming_2` 显示澄清本身也可能引入冲突。

“仅 DeepSeek 成功”为 0 只指这两组最终阶段成绩，不否定局部优势。DS 历史 11/61 渠道混合、运行时期、不同提问引发的 Simulator 反馈与数据缺失仍限制因果解释；GPT 不作为绝对正确 Teacher。M1/M2/M3 是从轨迹提出的研究假设，机制与验证思路见 [DESIGN](DESIGN.md)。

## 最新：Qwen 36 题对照（2026-11-12）

实验 ID：`comparison36_20261112`。[归档入口](../results/agent-qwen3.8-flash/simulator-deepseek-v4.1-flash-1017/comparison36_20261112/README.md) · [分析报告](../results/agent-qwen3.8-flash/simulator-deepseek-v4.1-flash-1017/comparison36_20261112/analysis/REPORT.md) · [选题依据](../results/agent-qwen3.8-flash/simulator-deepseek-v4.1-flash-1017/comparison36_20261112/SELECTION.md)。

| 方案 | P1 | P2 | 总 Reward | 平均 Reward |
| --- | ---: | ---: | ---: | ---: |
| Qwen Baseline | 19/36 | 9/36 | 16.0 | 0.4444 |
| Qwen Native | 13/36 | 8/36 | 11.5 | 0.3194 |

36 题为目的抽样，覆盖 18 库、20 Query / 16 Management，不是 72 题总体的随机代表样本，也不与全 72 题成绩直接排名。两组任务及顺序一致，Baseline 先跑。Agent 为百炼 `openai/qwen3.8-flash`，关闭思考，temperature=0、max_tokens=4096；Simulator 为 DeepSeek，v1/two_stage，patience=3、并发 1。

源码复用旧 Baseline / DeepSeek Native，独立快照增加 Qwen API 参数适配；以 `qwen_formal/` 下各组 `source_snapshot`、配置和 manifest 为准，不将其视为当前工作树的新实现。

Native 有 5 题以仅 State 文本结束；State history 388 次，39 接受、349 拒绝或缺失。`mental_M_1` 有空名称 function_call，后续历史转换出错，未重跑；缺失字段保留 unavailable。没有检测到与 DeepSeek Native 相同的末条 DSML/XML 模式，不等于工具协议整体无误。实际 State 驱动后续决策的比例仍 unavailable。GLM 正式实验取消；早期 API 预检不算正式成绩。

## 较早探索

- **Prompt-only，2026-11-07，48 runs：** 四任务 × Baseline/A/B/C 四条件 × 三重复。A 关注工具成本，B 加入信息需求和已有状态，C 再区分不确定性与信息来源。48/48 完成并有离线语义审查；小样本、单一审查者，不作为稳定收益证明。
- 早期动机是重复单项知识查询、较晚 ask_user 及探索预算消耗；不能将减少查询次数本身当成收益。网页提到的 `prompt/explore` 未在当前分支列表核实，不作为实际归档地址。
- 该实验保存在 `prompt/exploration-policy@775e5b0`，ID 为 `prompt_strategy_48_20261107_retry1`。该归档不保证在其他分支或新克隆的工作目录中存在，使用分支路径定位。可在本项目目录只读查看：

```bash
git show prompt/exploration-policy:./trajectory_analysis/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107_retry1/README.md
```

- 早期 Kimi、Qwen Simulator 筛选及协议恢复是历史工程探索；入口见 [历史结果索引](../results/README.md)。Simulator 和协议不同，不与主线直接混合汇总。部分 Kimi pilot 只有日志摘要，不声称全部有完整轨迹。

历史环境诊断另见 [Flash/Kimi 36 题分析](../results/analysis_flash_vs_kimi36_20261004/README.md)：记录过空结果评分、CURRENT_DATE 日期漂移、任务文字与参考 SQL 冲突。这里只保留历史问题入口，当前是否仍存在需另行核查，不自动修改评分或历史成绩。早期 Kimi/Qwen 单阶段 Simulator 曾改变协议；2026-10-13 恢复 ADK 两阶段路径，见 [恢复后验证记录](../results/reference_protocol_qwen_20261013/README.md)。这些阶段不能直接混作官方原版或同期 scaffold 对照。

## 新增实验的记录要求

文档中的本地证据链接依赖相应归档在当前工作目录可用；缺失时先查所属分支和本地归档，不为补链接而复制结果或改写其归属。

每个独立实验保留 ID、日期、任务字节/顺序、Agent 与 Simulator 配置、源码快照或 commit+diff、P1/P2 分母、Reward、错误/未完成情况、真实 usage 和证据链接。先记录实际完成情况，再下结论。失败重试与原运行分别保留；未知数据不估算。`results/` 和 `trajectory_analysis/` 默认被忽略，部分证据曾显式提交，文件在本地存在不等于已经入 Git。
