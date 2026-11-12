# 开发、运行与复现

最近核查：2026-11-12。以下来自当前源码和脚本检查；本轮未安装依赖、启动服务或运行付费实验。

## 目录与执行链

当前项目目录为 `BIRD-Interact-ADK/`，实际 Git 顶层是其父目录 `BIRD-Interact/`。下列命令默认在本项目目录执行；`git show branch:./path` 可避免误用仓库根相对路径。

| 入口 | 作用 |
| --- | --- |
| [orchestrator/runner.py](../orchestrator/runner.py) | 加载任务、并发运行、保存结果与运行元数据 |
| [orchestrator/](../orchestrator/) | a-interact / c-interact 的阶段、会话与单题流程 |
| [system_agent/server.py](../system_agent/server.py) | 被测 agent 服务，端口 6000 |
| [system_agent/adk_runtime.py](../system_agent/adk_runtime.py) | ADK Runner、会话、事件和 State 持久化 |
| [system_agent/agent.py](../system_agent/agent.py) | 模型、指令、工具及 callbacks 装配 |
| [system_agent/tools.py](../system_agent/tools.py) | 数据库、知识、ask_user、submit_sql 工具 |
| [system_agent/callbacks.py](../system_agent/callbacks.py) | a-interact 预算及调用约束；c-interact 有独立 callbacks |
| `system_agent/requirement_tracking.py`（State 分支） | Native 或 2-calls 的 State 流程，具体机制依分支而异 |
| `system_agent/requirement_state.py`（State 分支） | State schema 与更新校验；main/Prompt 分支无此模块 |
| [user_simulator/](../user_simulator/) | 模拟用户服务，端口 6001 |
| [db_environment/](../db_environment/) | 数据库接口与评分服务，端口 6002 |
| [shared/config.py](../shared/config.py)、[shared/llm.py](../shared/llm.py) | 配置和模型适配 |

主要路径：runner → 单题 orchestrator → system agent / ADK 循环 → tools → Simulator 或数据库环境。区分被测 agent 和评分环境，追踪行为以代码及事件为准。

## ADK 概念在本项目中的位置

`agent.py` 的 LlmAgent 装配模型、instruction、tools 和 callbacks；`tools.py` 将 Python 函数包装为 FunctionTool。ADK Runner 由 `adk_runtime.py` 创建并驱动执行，不要与批量测评的 `orchestrator/runner.py` 混淆。Session 保存任务会话的 events 与自定义 state；新增 Requirement State 只补充任务状态，不替代模型/工具交互历史。

Callback 是模型或工具调用生命周期中的钩子：`callback_context` 可访问回调的 session state，`llm_request` 是本次送入模型的请求，`tool_context` 提供工具执行时的任务状态。Native 分支的 tracking 在 before-model 中注入、after-model 中提取 State；工具和预算 callbacks 使用 tool_context。修改时沿实际事件与 state_delta 持久化链核查，不只看一个函数返回值。

## 分支与源码身份

| 分支 | 用途 | 2026-11-12 整理前的 HEAD |
| --- | --- | --- |
| main | 本地 baseline；不等同于未修改上游 | 8138403 |
| prompt/exploration-policy | Prompt-only 实验与归档 | 775e5b0 |
| state/requirement-tracking | Native State | cbf2840 |
| state/requirement-tracking-2calls | 独立 State 调用实现 | 133801d |

不同探索使用独立 `prompt/...`、`state/...` 或体现研究机制的分支，避免将实验性改动直接混入 main。网页中的旧称 `prompt/explore` 不替代已核实的 `prompt/exploration-policy`。

这些 HEAD 是文档整理前的历史快照，整理提交会推进各分支 HEAD，具体实验用 [EXPERIMENTS](EXPERIMENTS.md) 所列版本与源码快照。开始工作先执行 `git status --short`、`git branch --show-current`、`git rev-parse --show-toplevel`。有未提交修改时不要擅自切分支、重置或覆盖。

`results/`、`trajectory_analysis/`、`trashbin/` 被忽略，但忽略规则不会取消已跟踪文件。核对某分支归档用 `git ls-tree -r --name-only <branch> -- results/ trajectory_analysis/`，不能仅凭当前磁盘文件判断归属。提交和跨分支同步须有用户明确授权；仅同步文档不应引入其他分支的实验实现。

## 配置与启动

配置优先级见 `shared/config.py`：环境变量、`.env`、代码默认值。默认 `prompt_version=v2`，而主线历史实验用 v1，因此不能依赖默认值复现实验。当前 config 的 `user_sim_pipeline` 只接受 `two_stage`；v1/v2 选择提示模板，不表示调用阶段数。不要打印整个 `.env`。

历史本机使用 `bird-interact` conda 环境。以下为运行入口，不代表当前环境已验证可用；执行前检查依赖、端口、Docker 数据库、脱敏后的实际模型参数与本次授权：

```bash
conda activate bird-interact
docker compose up -d postgresql
bash scripts/start_services.sh
```

启动脚本会执行 `pkill -f uvicorn` 并启动三个服务，可能影响本机其他 uvicorn 进程；不要在纯文档/分析工作中调用。它按 `.conda-py310`、激活的 conda、`.venv-adk`、默认 python 选择解释器。配置变更后要确认服务实际重新加载，runner 的配置记录不能独立证明服务模型已切换。

只读健康检查：

```bash
curl --noproxy '*' http://127.0.0.1:6000/health
curl --noproxy '*' http://127.0.0.1:6001/health
curl --noproxy '*' http://127.0.0.1:6002/health
```

服务在线不等于真实模型调用或 SQL 正确。经用户授权运行时，明确任务文件与并发，例如：

```bash
python3 -m orchestrator.runner --mode a-interact --data /path/to/frozen_tasks.jsonl --limit 1 --concurrency 1
```

上面任务路径是占位符，需替换为本次冻结题集。runner 默认并发为 5，主线对照用 1，必须显式指定。不指定 `--output` 时自动生成新的结果目录；指定时不得覆盖既有结果。`scripts/run_eval.sh` 可能自动启动服务，调用前阅读脚本。

## 验证与实验记录

`state/requirement-tracking` 分支的离线测试使用真实 ADK 和受控模型/HTTP，在具备依赖的环境运行：

```bash
python3 -m unittest discover -s tests -p 'test_requirement_tracking.py' -v
```

`test_requirement_tracking_live.py` 是显式 opt-in 的真实模型测试，不能当离线测试自动开启。本轮文档更新只做内容、链接和 diff 检查，不声称这些测试已通过。

对照实验先冻结任务字节/顺序、Simulator、模式、预算、并发和模型参数，再保存各组独立源码快照、diff、脱敏配置、原始结果、完整 sessions/events、日志及实际 usage。先做供应商参数与原生工具调用预检；已有 AINET 拒绝 temperature 的案例，Qwen 需要关闭思考适配。不能用相同模型显示名推断渠道与参数完全相同。

分析分别处理 P1、P2 和 P1 gate；保留错误、缺失与失败记录。轨迹中的 SQL 是证据，离线分析不执行它。新模型适配和修复先隔离验证，不能污染比较基线。真实验证与离线验证分开记录，不以结构校验代替语义结论。
