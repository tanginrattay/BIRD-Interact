# 多轮 Text-to-SQL Agent Scaffold 研究

本项目借助 BIRD-Interact 测评框架，开发并测试自己的 Text-to-SQL agent scaffold。研究对象是模型外部的提示、状态管理、工具使用和交互控制：如何获取缺失信息、澄清用户意图、整合证据，并在预算内生成正确 SQL、处理后续要求。

当前已开展的实验主要使用 BIRD-Interact-Lite 的 a-interact 模式。BIRD-Interact 提供任务、模拟用户、数据库环境、评分和预算协议；`system_agent/` 是被测 agent 的主要实现位置。保留原仓库代码布局，`agent/` 用于维护研究上下文，不存放新的 agent 实现。

## 研究定位与参考背景

据用户 2026-11-12 同步的网页讨论，课题由早期“多智能体协同 Text-to-SQL 数据合成”转向老师要求的 **Agent for Multi-turn Text-to-SQL**。主要贡献聚焦 inference-time scaffold，不以训练、微调或蒸馏 Backbone 为主，也不把简单角色拆分、Prompt 调优或 Benchmark 已有工具与预算机制作为创新本身。需要明确研究问题、定量实验和消融。

Memory、Planning、Interaction Policy、Experience Reuse、Budget-aware Tool Use、Model Switching 是探索范围，不表示均已实现。当前希望把有效的交互决策机制用于低成本模型，使其接近、或在部分任务上超过旗舰模型；这是研究目标，尚未得到验证。GPT 是行为参照，不是绝对正确的 Teacher。

用户此前接触过 DySQL-Bench，重点阅读过 MERIT 与 Budget-Constrained Tool Learning with Planning（BTP）。网页阅读笔记提示：MERIT 已覆盖 episode/turn 两级记忆检索及涉及训练的 PRM；BTP 涉及历史工具估值、frequency constraint、Knapsack 和 blacklist。选题需避免重复简单成功样例检索，并研究工具价值如何随当前任务缺口变化。此处记录用户阅读背景；论文具体版本、上述机制细节与新颖性边界尚未在本轮核对原文，正式相关工作论证前需核实。

## 阅读入口

| 文档 | 用途 |
| --- | --- |
| [STATUS.md](STATUS.md) | 先读：现在做到哪、接下来做什么 |
| [EXPERIMENTS.md](EXPERIMENTS.md) | 做过哪些实验、成绩和证据在哪里 |
| [DESIGN.md](DESIGN.md) | scaffold 机制、设计决策与未解决的问题 |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 代码入口、分支、运行与验证约定 |

新对话的工作和文档更新规则见根目录 [AGENT.md](../AGENT.md)。用户结束工作时只需说“请根据本对话内容，更新 agent/”，接手 agent 应自行维护以上文档及本入口，不需要用户再次说明更新方法。

## 资料边界

- [根 README](../README.md)：原框架说明，不能代替本地研究状态。
- [results/](../results/)：实验原始产物；[trajectory_analysis/](../trajectory_analysis/)：逐题轨迹与分析。两者保持原结构。
- 本目录只保留五份活跃文档；旧报告已移入 `trashbin/agent/`。
- `trashbin/`：本地忽略的弃用材料暂存区，按原项目路径存放，默认不读、不扫描。

这套文档于 2026-11-12 根据本地代码与实验记录建立。已同步用户同日提供的网页讨论增量；实验事实以本地记录为准，未实现的方向见 DESIGN。
