# 当前研究状态

最近核查：2026-11-12。依据本地代码、实验 README、Part A/B 分析及用户同步的网页讨论；本轮没有重跑实验或验证服务在线状态。

## 当前重点

在 BIRD-Interact 上研究多轮 Text-to-SQL scaffold。已探索 Prompt 信息获取策略，以及显式 Requirement State 的 Native、2-calls 两种实现。当前优先研究候选为 **M1：由影响 SQL 的 Requirement Gap 驱动信息源切换**，目标是将有效交互决策用于低成本 Backbone。M1 优先级来自 Part B 与网页讨论；尚未实现、未验证，具体实验方案未定。M2/M3 暂列后续候选，不同时铺开。

## 最近进展

- **最新完成实验：Qwen3.8-Flash 的 36 题 Baseline / Native 对照（11-12）。** Native 的 P1/P2 和总 Reward 均低于 Baseline；包含 State-only 提前结束及一例空名称工具调用错误。GLM 正式实验已取消，没有正式结果。见 [实验表与报告入口](EXPERIMENTS.md)。
- **已有 72 题五组分析（11-09）。** 包括 DeepSeek Baseline / Native / 2-calls、GPT Baseline / Native。DeepSeek Native 有明显行动通道问题；2-calls 恢复接近 Baseline 的总成绩但增加调用成本；GPT Native 未显示整体提升。详见 [五组分析](../trajectory_analysis/docs/five_variants_trajectory_analysis.md)。
- **Part B 已完成（11-12）。** 对 Baseline 做跨 Backbone 配对与关键决策分析，提出信息源切换、契约落实和失败诊断三个机制；也保留 DeepSeek 局部优势、Simulator 反馈差异及历史渠道混杂。见 [Part B](../trajectory_analysis/docs/gpt_deepseek_transfer_analysis_part_b.md)。
- **目前结论边界：** State 能被校验、保存、注入，不等于它语义正确或实际改善决策。现有比较还混有指令、调用方式、历史环境及 Simulator 反馈差异，不能据此证明 State 本身有用或无用。

## 下一步

1. 优先细化 M1 的最小机制与验证方案：先区分“缺定义／尚未查到／已有证据可推导”的固定历史决策点测试，再考虑同期 Baseline 与 M1 端到端对照。控制过度澄清、错误确认、成本和 P1/P2 退化，具体方案仍需讨论。
2. 保持五份活跃文档随研究进展更新；旧报告已按原路径移入 `trashbin/agent/`。
3. 利用已有 Qwen 小规模对照检查跨 Backbone 共性；是否扩展到 72 题或新增模型尚未确定。候选模型需另做价格、ID、思考控制与协议预检，不恢复已取消的 GLM 正式实验。新对话不因方向已记录就自行实现或启动付费实验。

## 接手时核查

- 本文记录项目研究状态，不指定当前检出分支；用 `git branch --show-current` 和 `git status --short` 核对现场。各分支实现与历史版本见 [DEVELOPMENT](DEVELOPMENT.md)。
- 网页上下文与旧文档整理已纳入活跃文档。`trashbin/` 仅本地保留，默认不读、不扫描。
- 实际服务是否运行、当前 `.env` 对应哪套实验未核查；不能由文档或分支推断，运行前按 DEVELOPMENT 核对。
