# 本科科研项目：Agent for Multi-turn Text-to-SQL

本项目研究在多轮交互中完成 Text-to-SQL 的 agent：面对有歧义的自然语言需求，如何查询数据库信息、向用户澄清、保留已确认的意图，并在有限交互预算内生成正确 SQL。研究重点是 inference-time agent architecture、interaction policy、memory/state、planning、budget-aware tool use 和 ambiguity resolution，不以训练或微调基础模型为主要路线。

当前实验平台是 **BIRD-INTERACT**，主要使用 **BIRD-Interact-Lite 的 a-Interact 模式**。此前已尝试 Kimi K2.6 和 Kimi 3 作为 system agent；具体每次运行使用的模型需要单独保存配置，不能仅凭结果文件推断。

## 当前交接状态（文档更新：2026-10-09；最近运行：2026-10-04）

最新分析交接：[Flash36条诊断、simulator审查及历史Kimi对照](FLASH_KIMI36_ANALYSIS.md)。包含成绩、共性/差异、评测干扰、36条逐任务标注和未完成事项。2026-10-09仅更新文档，没有新运行；后续先读此文件，再按需查看原始轨迹。

用户因成本决定迁移模型。侧边对话已接入 **Qwen 3.7 Plus simulator**，配置型号为 `qwen3.7-plus`，单阶段、非思考模式。侧边对话最初只完成离线/mock 验证；本轮已通过一条真实任务验证 API 调用和服务配置生效，现已逐条审查36条Flash任务中的46条真实澄清回复：调用链正常，但存在公式错误与不完整回答，详细分析见下文。

system agent 当前使用 **DeepSeek Flash**：`SYSTEM_AGENT_MODEL=deepseek/deepseek-flash`，官方 OpenAI 兼容地址 `https://api.deepseek.com`。按 [DeepSeek 官方文档](https://api-docs.deepseek.com/quick_start/pricing/)，当前推荐 ID `deepseek-flash` 对应 V4.1 Flash；旧 `deepseek-v4-flash` 已转向同一模型。用户已在 `.env` 填入 `DEEPSEEK_API_KEY`（不在文档或日志记录密钥），原 Moonshot key、地址和模型行保留为注释；Qwen simulator 配置保持原样。

system agent 显式使用 `thinking={"type":"disabled"}`，保留 `max_tokens=4096` 和原重试设置。原因是 [官方思考模式文档](https://api-docs.deepseek.com/guides/thinking_mode/) 要求工具调用时完整回传历史 `reasoning_content`，当前 ADK 轨迹转换未保证保留该字段。本配置是非思考 baseline，不标为官方默认思考模式或 low 推理档。已通过 14 项离线测试，本轮已重启服务并运行一条真实任务验证调用链。后续修改配置仍需重启 system-agent 服务，使缓存的模型实例使用新配置。历史 Kimi pilot 配置和结果保留；网页 DeepSeek simulator 测试中的未知型号不能视为本次 system-agent 测试。

完整交接：[SIDE_CHAT_HANDOFF_2026-10-04.md](SIDE_CHAT_HANDOFF_2026-10-04.md)；接入说明：[QWEN_SIMULATOR_SETUP.md](QWEN_SIMULATOR_SETUP.md)；本地协议变化：[LOCAL_CHANGES_AND_COMPARABILITY.md](LOCAL_CHANGES_AND_COMPARABILITY.md)。该交接文档记录此前侧边对话状态；当前运行状态以本 README 的最新验证记录为准。

## 本地启动与单条验证

在仓库根目录执行，先在 `.env` 填写 `DEEPSEEK_API_KEY` 和 Qwen simulator 的 `USER_SIM_API_KEY`：

```bash
conda activate bird-interact
docker compose up -d postgresql
bash scripts/start_services.sh
```

非交互 shell 若尚未初始化 conda，先执行 `source /home/nimir/miniconda3/etc/profile.d/conda.sh`。启动脚本会停止现有 uvicorn 进程并重新启动三个服务；修改 `.env` 或模型代码后需重新运行。脚本显示 `ALL_SERVICES_READY` 后可检查：

```bash
curl --noproxy '*' http://localhost:6000/health
curl --noproxy '*' http://localhost:6001/health
curl --noproxy '*' http://localhost:6002/health
```

6000 为 system agent（还需检查响应中 `adk_available=true`），6001 为 user simulator，6002 为数据库环境。健康响应只验证服务存活；真实模型调用和数据库访问由下面的任务验证。

```bash
python -m orchestrator.runner --mode a-interact --limit 1 --concurrency 1
```

此命令运行数据文件第一条任务（Lite 默认是 `alien_1`），会调用真实 DeepSeek 和按需调用 Qwen，产生 API 费用。结果默认按 agent/simulator 型号与唯一运行 ID 保存到 `results/agent-*/simulator-*/*/eval_a_interact.json`，日志打印实际路径。可通过 `--output` 指定新文件，但不能覆盖已有结果；不要使用旧 Kimi 结果路径。API 连通不等于 SQL 正确，验收时分别检查错误、工具轨迹、澄清回复以及 P1/P2 结果。若执行环境限制 Docker socket、本地端口或外部网络，应通过执行工具请求相应权限。

### 2026-10-04 真实单条验证记录

使用上述环境和启动方式运行 Lite 第一条 `alien_1`；6000–6002 健康，6000 返回 `model=deepseek/deepseek-flash`、`adk_available=true`。真实 DeepSeek 工具调用、Qwen 澄清和数据库提交评测均完成，无任务级 API 错误。耗时 21.05 秒，P1 未通过、P2 未进入、reward=0；该记录证明调用链可运行，不证明模型准确率或 simulator 整体质量。

轨迹包含 29 次 `get_knowledge_definition`、一次 schema 查询、一次知识名称查询、一次 `ask_user`、一次 `submit_sql`。SNQI 定义查询返回未找到；Qwen 确认指标但拒绝提供公式；agent 最终使用猜测的 `snrratio + noisefloordbm` 公式提交失败。18 coins 耗尽，提交工具记录 budget_after=-1，最终结果按现有 runner 逻辑将剩余预算截为0；本轮未改变预算协议或 agent 策略。

- [完整结果和工具轨迹](../results/agent-deepseek-deepseek-flash/simulator-qwen3.7-plus/smoke_20261004/eval_a_interact.json)
- [runner 日志](../results/agent-deepseek-deepseek-flash/simulator-qwen3.7-plus/smoke_20261004/runner.log)
- [服务启动日志](../results/agent-deepseek-deepseek-flash/simulator-qwen3.7-plus/smoke_20261004/services.log)

本次自动执行使用 `nohup bash scripts/start_services.sh > <服务日志路径> 2>&1 < /dev/null &` 保持服务在启动命令结束后运行；普通交互终端可直接使用上面的 `bash scripts/start_services.sh`。

### DeepSeek Flash / V4 Pro 的历史36条复跑（已完成）

两轮均完成36/36，无任务级接口错误，任务ID及顺序、任务文件SHA256、代码hash、指标计数均核对通过。有效结果如下：

| Agent（均为非思考模式） | P1 | P2 | 平均 reward | 任务累计耗时 |
| --- | ---: | ---: | ---: | ---: |
| DeepSeek Flash（V4.1） | 11/36（30.56%） | 6/36（16.67%） | 0.2639 | 11.70 分钟 |
| DeepSeek V4 Pro | 5/36（13.89%） | 2/36（5.56%） | 0.1139 | 32.99 分钟 |

[对照汇总与完整结果入口](../results/deepseek_pilot36_comparison_20261004.md)。两轮评测完成时 `.env` 保留 Pro；用户随后决定后续使用 Flash，当前已改回 `SYSTEM_AGENT_MODEL=deepseek/deepseek-flash`，密钥保持原样。本轮Flash成绩高于Pro，仅代表当前36条、非思考模式、scaffold和simulator配置下的单次运行；不能由此确定模型总体能力顺序。

2026-10-04 按用户要求依次运行 Flash 和 V4 Pro，固定使用历史 `pilot36_seed42/tasks.jsonl` 的36条任务及顺序，SHA256 为 `aeb851d78736e4b1794f1c83080b2bf99425b0d0dcfe23f4e1728638d61c6b52`。两轮均为 a-interact、concurrency=1、patience=3、max_tokens=4096、非思考模式，simulator 使用当前 Qwen 3.7 Plus 单阶段非思考配置。历史 Kimi pilot 使用 Kimi K2.6 simulator，因此不能将新旧成绩差异全部归因于 system-agent 模型。

有效复跑目录：`results/agent-deepseek-deepseek-flash/simulator-qwen3.7-plus/pilot36_seed42_20261004_retry1/` 和 `results/agent-deepseek-deepseek-v4-pro/simulator-qwen3.7-plus/pilot36_seed42_20261004_retry1/`。每组包含任务副本、配置及代码 hash、health、runner/services 日志、完整结果和最终 validation。整体状态文件为 `results/deepseek_comparison_pilot36_seed42_20261004_retry1.json`。每条完成时 runner 原子保存结果；若中断，仅从尚未完成的任务继续，且使用新输出文件保留旧记录。

不带 `retry1` 的同名目录为无效尝试：执行环境中本机代理导致 DeepSeek TLS 证书校验失败，应排除这些接口错误结果。重跑在已授权的沙箱外环境中对服务进程及 runner 临时 unset `HTTPS_PROXY HTTP_PROXY ALL_PROXY https_proxy http_proxy all_proxy`，官方端点直接 HTTPS 证书验证通过，未关闭 TLS 校验；不需要修改 `.env` 的密钥。完成 Flash 后才切换 `.env` 的 `SYSTEM_AGENT_MODEL=deepseek/deepseek-v4-pro` 并重启服务；两轮评测完成时保留 Pro 配置；用户随后选择 Flash，当前 `.env` 已切回 Flash。


### Flash与历史Kimi 3的逐条诊断（2026-10-04）

[agent目录内完整分析与接手说明](FLASH_KIMI36_ANALYSIS.md)；[原分析附件、36条任务对照及47次澄清尝试审查](../results/analysis_flash_vs_kimi36_20261004/README.md)。已检查Flash全部36条和历史Kimi保存完整轨迹的32条；未重跑模型或改动评分。共同32条P1结果一致率为81.25%，主要共性是澄清覆盖不足、已确认条件未完整落实、聚合/输出契约偏差及无依据修复。Flash查知识更多并耗尽预算；Kimi有11条未完成但仍剩至少3 coins。

Qwen实际46次回复均非空、无调用错误，但virtual_6将1−x解释成倒数，另有公式回答不足；调用正常不等于语义完全可靠。评分拒绝预测与参考同时为空，影响vaccine_7和solar_3 P2；solar_4/polar_7 P2另有文字与参考SQL冲突。原分数保留，后续若修复协议或评分，baseline与方法必须在相同新环境重跑。历史Kimi使用不同simulator与推理配置，不能将成绩差异全部归因于system-agent模型。

## 这个 repo 是什么

本仓库是 **BIRD-Interact-ADK**：基于 Google ADK 实现 BIRD-INTERACT agent 与评测流程的代码库。它是本项目的实验基础设施；benchmark 数据、评测任务和原始协议来自 BIRD-INTERACT，并非本课题自行提出。仓库原始介绍与运行说明见 [根目录 README](../README.md)。

| 位置 | 作用 |
| --- | --- |
| `system_agent/` | 理解任务，通过 ADK 调用 schema、knowledge、SQL、ask_user、submit_sql 等工具 |
| `user_simulator/` | 接收澄清问题，使用当前任务的隐藏真实意图、标注和参考 SQL 模拟用户回答 |
| `db_environment/` | PostgreSQL 任务环境、SQL 执行、提交评测和阶段切换 |
| `orchestrator/` | 初始化服务、运行任务、并发调度、汇总结果 |
| `shared/` | 配置、模型调用、服务消息类型和数据库工具 |
| `bird-interact-lite/` | 本地 Lite 数据；当前包含 18 个数据库、300 个任务 |
| `results/` | 评测指标、工具轨迹、对话和 ADK 事件 |
| `agent/` | 本项目研究说明；当前不是独立的 agent 实现目录 |

a-Interact 中，system agent 自主决定探索、执行 SQL、澄清和提交的顺序，工具调用消耗 bird-coins。Phase 1 解决初始优先问题；成功后进入 Phase 2 follow-up。当前实现中两个阶段共享任务预算。隐藏清晰问题、歧义标注和参考 SQL 属于 simulator/evaluator 的信息，不能直接放进 system agent 的输入。

当前工作副本已修改 user simulator：保留普通文本回复、显式暴露调用错误、传递澄清历史。历史 Kimi simulator 使用直接澄清提示和 `reasoning_effort="none"`；10月4日接入后协议由 `USER_SIM_PIPELINE=auto/single_stage/two_stage` 选择，Qwen 3.7 和 Kimi 可使用共享 `_ask_direct` 单阶段提示。Qwen 使用独立百炼客户端和 `enable_thinking=false`，不发送 Kimi 的推理参数。旧 Kimi action-parser 曾在 500 token 下用掉 499 个 reasoning token，最终可见 content 为空；2048 上限也出现截断。这是本地协议变体，做实验比较时必须固定并记录。

## 初始 5 条结果解读（2026-09-29 历史快照）

数据来源：[归档的初始5条结果](../results/agent-unknown/simulator-unknown/initial5_repaired/eval_initial5.json)，并与本地 Lite 数据的清晰问题和参考 SQL 对照。该历史文件已脱离默认输出路径，型号信息不完整，不能用当前配置回填。下面是静态轨迹分析，没有重新执行 SQL 来分离每个差异的因果贡献。

共 5 个任务，全部来自 `alien` 数据库：Phase 1 成功 2/5（40%），Phase 2 成功 1/5（20%），平均 reward 0.34。进入 Phase 2 的两个任务中一个通过，即条件成功率 1/2。每任务平均约 425 秒。

| Task | Phase 1 / 2 | ask_user 次数 | 剩余 coins | 主要观察 |
| --- | --- | ---: | ---: | --- |
| alien_1 | 成功 / 失败 | 2 | 0 | 第一次提交升序，澄清后改 DESC 即通过；进入 Phase 2 时只余 0.5 |
| alien_2 | 成功 / 成功 | 2 | 2.5 | 澄清 TOLS 分类与阈值后两阶段均成功 |
| alien_3 | 失败 / 未进入 | 1 | 4.0 | 得到正确 LIF 解释，但按连接后的信号计数，参考 SQL 按 observatories 记录聚合 |
| alien_4 | 失败 / 未进入 | 0 | 3.5 | 未澄清 origin score，用 TechSigProb 代替 TOLS，并额外增加 infodense 过滤 |
| alien_5 | 失败 / 未进入 | 3 | 3.5 | 澄清集中在 JSON 细节，分组字段、平均指标、数量阈值仍与目标不一致 |

8 次 `ask_user` 均有实质回复，没有原来的统一 fallback。例如 alien_1 的回答纠正 SNR → SNQI、明确 SNQI > 0，并确认降序；alien_2 给出 TOLS 分类边界。这证明当前调用链已经能够完成有效澄清。

但 **simulator 能回答不等于回答始终可靠**。alien_5 的隐藏目标是按 modulation type 分组，simulator 却回答“one aggregated row per encoding method”，沿用了提问中的错误前提。它提供了 MCS 细节，却未纠正这一分组误解。alien_1 回复还包含 `s.SnrRatio - 0.1 * ABS(s.NoiseFloorDbm)` 这样的 SQL 片段，提示当前直接提示未严格守住原 prompt 的信息披露边界。后续评价 interaction policy 前，应先检查 simulator 的忠实性和允许披露的信息范围。

失败轨迹中几个值得注意的具体差异：

- alien_1：两次 Phase 1 提交仅排序方向不同，后一条通过，是“遗漏排序澄清导致额外提交成本”的直接证据。Phase 2 确实执行了提交：代码允许预算不足时最后一次免费提交。失败 SQL 仅从 observatories 聚合，参考 SQL 则从 signals 经 telescopes 连接 observatories，统计粒度不同，因此不能把 Phase 2 失败全部归因于预算。
- alien_3：参考 SQL 无 signals/telescopes 连接；system agent 加入连接后改变了参与统计的记录及事件计数。正确识别指标公式并不保证正确识别统计对象。
- alien_4：查了 10 次单项 knowledge definition、执行了 6 次 SQL，却一次也没问用户。数据探索无法直接证明用户说的 origin score 是哪个指标。
- alien_5：参考 SQL 使用 ModType、平均 MCS、平均 SNR、`COUNT(*) > 5` 和小写 JSON 字段 `mcs`/`snr`；提交使用 EncodeType、平均 ECI、平均 SNQI、`COUNT(*) > 1` 和大写 JSON 字段。此例还存在清晰文字“at least 5”与参考 SQL `> 5` 的边界不一致，归因时应单独标记数据问题。
- alien_3/4/5 结束时仍能支付一次 3-coin 提交，但停在约 1.7 万字符的分析文本。轨迹支持“未把剩余预算转为下一步行动”；仅凭当前结果不能证明是 token 截断、模型选择结束或运行控制问题，需补查 finish_reason 等运行元数据。

## 初始 5 条提出的假设与后续执行

本节保留当时的建议；下述跨库 pilot 已完成，当前进度与更具体假设见后文，不需要重新从抽样步骤开始。

这些结果足以提出可检验假设，尚不足以证明某种新架构有效。优先考虑以下问题，每次实验只改变一个机制，并保持模型、simulator、预算规则和任务集一致：

1. **澄清覆盖与优先级**：在格式细节前先确认分组对象、指标、过滤阈值、统计粒度和排序。比较首个正确提交前的成本、未解决的关键歧义数量及成功率。alien_1/4/5 提供了具体动机。
2. **结构化意图状态**：把已确认与仍待确认的语义记录下来，避免新信息只用于局部字段而未更新整体 SQL。alien_5 得知 MCS 后仍保留平均 ECI，是候选案例；尚不能据此断定“记忆缺失”就是根因。
3. **预算与行动管理**：减少无助于确认用户意图的探索，为提交和 follow-up 留出行动空间；检查失败后仍有预算却停止的现象。先排除运行控制故障，再测试策略改进。

建议先抽查当前 8 条 simulator 回复，对照隐藏意图标注“正确、遗漏、顺从错误前提、过度披露”；再固定 simulator 版本，扩展到约 30–50 个跨数据库、跨难度、跨歧义类型的 pilot 样本。这个数量是控制成本的起步方案，不是统计充分性的保证。不要只用 `--limit 50` 取文件前缀，因为任务按数据库聚集。

在同一批任务上比较 baseline 与一个最小改动，并对关键样本做重复运行，观察方向是否稳定。更可靠的最终结果应覆盖完整 Lite 或独立保留的评测集，并报告成功率差值与不确定性。当前五例适合做开发案例，不宜同时作为最终证明改进有效的测试集。

除 reward、P1/P2 外，建议记录首个正确提交前成本、澄清轮数、每阶段成本、预算剩余但未提交的比例、simulator 回答错误率，以及错误类别。必须保存模型与 API 配置（不含密钥）、prompt/simulator 版本、代码版本、任务 ID 和运行元数据；当前 JSON 本身没有完整模型配置，不能用于严格的跨模型归因。

当时的文档整理没有实现以上机制；随后已完成下文的36条 pilot，研究机制仍未实现。

## 后续 simulator 校准记录

已复现 alien_5 原始提问导致 simulator 错误确认 encoding method。随后为 Kimi 路径加入独立 system message，明确清晰意图优先、纠正提问及历史中的错误前提、只回答相关澄清、拒绝披露 SQL/schema 实现细节。

通过真实 HTTP 服务和当前 Kimi 配置完成 8 条校准请求：原始多选问题、分组二选一、错误分组与指标组合、平均指标解释、错误历史纠正、alien_1 与 alien_3 正常澄清，以及完整 SQL 索取。最终回复在这些检查中均符合预期，详见本地 [输入输出记录](../results/simulator-only/kimi-k2.6/calibration/usersim_calibration_v3.json)。中间版本 v2 仍有 schema 信息披露，不能作为通过版本。

复测入口（需先启动服务，输出文件名不能已存在）：

```bash
python -m scripts.check_user_simulator --output results/usersim_calibration_repeat.json
```

这些结果是小规模定性校准，并非对所有 task、Phase 2 或随机重复稳定性的保证。alien_5 的文字阈值与 SQL 阈值不一致也未被修改；后续遇到该边界时应单独审查。记录含 benchmark 隐藏信息，仅供研究者检查，不能输入 system agent。

## 36 条跨库 pilot：最终状态与完整性

seed=42，18个数据库各抽2条，排除已分析的 alien_1–5。历史配置为 system agent `moonshot/kimi-k3`、simulator `moonshot/kimi-k2.6`，本地单阶段协议，concurrency=1；不能把这批结果标为后来新增的 K3-low 或 Qwen simulator。最后一条 virtual_M_4 于2026-09-29 20:13:59结束，全部36条已执行完。

| 记录范围 | 数量 | P1 | P2 | 平均 reward |
| --- | ---: | ---: | ---: | ---: |
| 完整结果 JSON | 32 | 12/32（37.5%） | 9/32（28.125%） | 0.346875 |
| 首次暂停前日志摘要 | 4 | 显式字段未保存 | 显式字段未保存 | 0 |
| 合计 | 36 | 12/36（33.33%，按四条零分推断未通过） | 9/36（25%，同一假设） | 0.308333… |

32条完整记录中9条两阶段通过、3条仅P1通过、20条P1未通过；有follow-up的12条P1成功任务中9条P2成功，条件成功率75%。这不是Phase2普遍更容易的证据。

完整记录为 `results/agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42/baseline_resume1.json`（31条）和 `baseline_resume2.json`（1条）。最初 alien_11、alien_7、archeology_1、archeology_9 只有 baseline_run1.log/pause_checkpoint 中的摘要；无法恢复其完整对话、SQL和ADK事件。首次暂停后的 runner 改为每条结束原子保存结果。补跑四条会形成新随机运行，不能伪装成旧轨迹。

完整阅读入口：[Markdown总览与分析](../results/agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42/markdown/README.md)。每任务单独Markdown保留结果全字段、对话、工具、ADK事件、最终回复和研究者对照task；sources目录完整封装原始文件并验证文本往返一致。源记录自带的 `<truncated>` 不能由导出恢复。

旧 `pause_checkpoint.json` 和 `remaining_tasks.jsonl` 仍停留在最后一次暂停时，可能显示 virtual_M_4 剩余；判断最终进度应以 baseline_resume2.json/log 为准。**历史36条没有待续跑任务。**

## 逐条分析得到的机制研究方向

当前最有证据的候选是：**有来源的意图状态，以及保持已确认约束的局部SQL修复**。这些是机制假设，尚未编码、未做对照实验；以下对照参考SQL用于研究者分析，不允许输入被评测agent。

### 已确认的信息在生成或修复时丢失

| 案例 | 已得到的信息 | 最终行为及其研究含义 |
| --- | --- | --- |
| credit_8 | 用户解释TDSR应区分Own与Rent住房成本 | 提交仅保留mortgage分支；已取得的澄清未完整落实 |
| polar_5 | 用户给出WRMI乘积公式，waterlevelpercent不除100 | 首次提交公式正确；失败后又除100，产生无新证据支持的回退 |
| vaccine_7 | 用户明确CURRENT_DATE而非固定日期 | 首次提交使用当前日期；失败后改为2025-02-19，违背已确认约束 |
| mental_9 | 首条SQL使用High/Severe suicide risk计算SRP，与目标一致 | 第二条无新澄清却扩大为含抑郁/焦虑指标的另一种风险人群；这里是无证据修订，不能声称用户已明确确认全部SRP定义 |

最具体的研究假设：粗粒度“SQL不正确”反馈可能诱发agent修改已经正确的语义；维护约束及证据来源，在修复时优先检查未确认假设/实现错误，能否减少这种回退？同一SQL可能有多个错误，不能保证保护某项约束就整题通过，也不能因此宣称已找到唯一根因。

最小机制：记录确认内容、来源轮次、适用阶段/范围及对应SQL位置；修复产生语义变化时检查依据；有新证据或来源冲突时允许修订。不能把simulator所有回复永久当作绝对真值。

建议对照：原baseline、仅增加“不要违背已确认要求”的提示、显式意图状态加修改后检查。报告正确率与成本，并评估“正确澄清落实率”“无新证据的约束回退次数”。区分状态机制收益和简单提示收益，避免复杂框架堆叠后无法归因。

### 探索、澄清与提交前语义覆盖

- cross_db_4执行9次SQL、没有ask_user，最终指标定义、JSON字段和连接方式仍不匹配。SQL能运行/结果看起来合理，不能证明用户意图已确定。
- polar_7未澄清，提交把数值ESI变成可持续性分类。
- vaccine_2只澄清传感器状态，主要TSS、critical条件等仍不正确。
- crypto_3澄清排名字段后仍有排序方向、全局最新单条波动率范围等偏差。

可作为上述状态机制的扩展：区分schema问题、用户意图问题和实现一致性问题；提交前检查统计对象、指标、筛选、时间基准、排序/limit和输出结构的依据。不是要求把所有槽位都向用户询问。

### 运行终止与预算：先确认原因再提出贡献

32条中11条未完成全部阶段但结束时还剩至少3 coins：cross_db_5、crypto_3、cybermarket_2、disaster_3、fake_1、gaming_M_4、news_9、solar_4、vaccine_2、virtual_6、virtual_M_4。fake_1和gaming_M_4从未调用submit_sql。部分最终文本停在分析/SQL中途；当前记录不足以区分输出截断、主动结束、工具调用未形成或runtime未继续。

运行控制诊断应限时且所有实验组共享处理；基础故障修复不能包装成新agent机制。若证实策略停滞，再研究候选SQL持久保存、有界修复及明确提交动作。crypto_M_4在P1通过时耗尽预算而未进入后续执行，是预算计划的候选案例，但这批数据不足以优先支持固定预留策略。

### 环境/数据干扰与正例

- gaming_7：simulator把DS求和说成平均，agent除以3与错误回复一致，不能作为“没有遵循澄清”的例子。
- cybermarket_2：回复漏了争议率<0.05和活跃时长>90两项；SQL还存在其他偏差，不完全归因于simulator或agent其中一方。
- solar_4：follow-up文字只要求增加MCE>100过滤，但GT还改为panel type聚合。不能要求agent无依据推断隐藏改变。
- gaming_M_4/virtual_M_4参考SQL涉及关闭外键触发器的执行方式，需要审查协议，不应直接视为常规规划错误，也不能无授权在真实业务环境照搬。
- solar_3失败后澄清TPCI，下一次P1通过，是有效澄清的正例；无消融不能量化其因果收益。
- 22条有澄清任务中8条P1通过，10条无澄清任务中4条通过。任务难度和选择机制不同，不能据此得出问用户无效或有害。

所有这些案例整体保留，并单独标注干扰；不为提升分数悄悄删除。当前pilot适合开发/诊断，已经反复查看，不是最终独立验证集。

## 研究路线与官方baseline可比性

用户希望尽快回到研究主线，避免无限修复benchmark。已有环境能够跑任务、澄清、评分、保存轨迹，足以产生探索假设；后续基础设施工作应围绕影响可执行性/公平比较的明确问题设时间边界，不要求先修完所有标注和simulator问题。

本地单阶段simulator、历史新增对话输入，以及后续模型迁移都会改变环境。固定同环境可研究内部机制差异，但simulator错误仍可能与新提问策略相互作用；不能直接拿本地方法分数减去官方发布分数。正式验证在选定参考协议下让baseline和方法使用相同配置重跑。system agent与simulator可独立选模，不必为让同一供应商做simulator而持续改协议。

根README自报的历史ADK a-Interact结果：Lite300条、Sonnet4.5、Haiku4.5/v1 simulator，P1=36.67%、P2=23.67%、reward=0.328；它与我们的36条不构成严格模型对照。历史K3系统成绩也不是K3通用Text-to-SQL能力，不能据此称其弱模型或声称接近顶级模型。详见 [本地改动与可比性说明](LOCAL_CHANGES_AND_COMPARABILITY.md)。

用户提出过“优化较次模型，使其接近顶级模型”的目标。建议更可检验地表达为：通过推理时交互/状态机制，提高较低成本模型表现，研究与较强模型的性能—成本差距。强弱顺序应在同任务、同simulator、同scaffold下建立；“追平”是待验证目标，不是承诺。

最小比较：目标模型+原scaffold、目标模型+新机制、较强参考模型+原scaffold；机制内部再用简单提示作控制。记录准确率、token/实际费用、延迟和交互次数；固定bird-coins不等于固定计算费用，额外调用应与增加普通推理/采样预算的简单控制比较。最终使用未参与开发的样本，报告配对差异及不确定性。

**当前没有实现新的system-agent研究机制；DeepSeek Flash / V4 Pro + Qwen simulator 已各自完成相同36条 pilot baseline，结果见上文。** 后续固定配置再进行机制实验；勿将历史K3/K2.6结果当作新配置成绩。
