# BIRD-Interact-ADK 本地改动、可比性与研究边界

核查依据：当前工作树相对于 Git HEAD `451fe2c3518ee1cf908d8139e2913483bd519381` 的 diff，以及本轮实验记录。这里的“原版”指这个 Git 基点下的 ADK 实现，不表示已经核查最新上游、论文和官方所有配置完全相同。文中的行号对应当前代码，后续修改可能移动。

核心结论：我们既做了工程修复，也改动了 user simulator 的交互协议。尤其是 Kimi 单阶段回答路径，不能描述成完全不影响评测语义的兼容性修复。当前成绩是本地固定 simulator 配置下的结果，不能直接当作官方协议复现成绩。

## 1. 改动总表

| 文件/位置 | 具体改变 | 性质及实验影响 |
| --- | --- | --- |
| `user_simulator/server.py::_call_llm` | 不再吞掉模型异常；检测空 content；支持独立 system message 和 reasoning_effort | 错误可见性、消息格式和调用参数变化 |
| `user_simulator/server.py::_extract_output` | 接受普通文本及原 `<s>` 格式，去除完整 think 块和部分输出前缀 | 解析兼容性变化；格式异常不再伪装成用户不理解 |
| `user_simulator/server.py::_parse_action` | 抽取并检查 action；加入历史 | 两阶段路径的解析和输入变化 |
| `user_simulator/server.py::_generate_response` | 使用统一解析、空答报错；加入历史 | 两阶段路径的解析和输入变化 |
| `user_simulator/server.py::_ask_sync / _ask_kimi` | Moonshot Kimi simulator 绕过两阶段，直接回答，使用新提示 | **实质性评测协议变化** |
| `shared/llm.py::call_llm` | 可选 reasoning_effort 参数转发给 LiteLLM | 默认调用不变；Kimi simulator 显式传 none |
| `shared/models.py::AskUserRequest` | 增加 dialogue_history | 服务协议扩展 |
| `system_agent/tools.py::ask_user` | 发送已有澄清历史，并检查 HTTP 状态 | 未改变 system agent 推理提示，但改变 simulator 可见上下文与错误反馈 |
| `orchestrator/runner.py::_save / _run_one` | 每条保存，临时文件 + flush/fsync + replace | 持久化改动；不改变打分和 agent 决策规则 |

本轮没有修改 `system_agent/agent.py` 的 reasoning/tool policy、`system_agent/callbacks.py` 的 coin 规则、数据库 evaluator 或 benchmark 原始 task 内容。`user_simulator/prompts.py` 也没有直接改动，但 Kimi 路径已经不再使用其中的两阶段模板，不能据此声称“没有改 prompt”。

## 2. 错误与解析处理：原来的统一 fallback 是怎么来的

位置：[server.py](../user_simulator/server.py)，当前 `_call_llm` 约第 66 行，`_extract_output` 约第 83 行。

原代码会吞掉异常：

```python
except Exception as e:
    logger.error(f"LLM call failed: {e}")
    return ""
```

原响应解析在没有识别出 `<s>` 或 `</s>` 时，直接返回：

```python
return "I'm not sure I understand your question."
```

所以 API 异常、空回复，以及没有标签的正常答案，都可能变成同一句“用户不理解”。现在正常纯文本会被保留，异常向外传播；空回复显式失败：

```python
if not content or not content.strip():
    raise ValueError("User simulator model returned an empty response")
```

action parser 现在用正则匹配 `labeled(...)`、`unlabeled(...)` 或 `unanswerable()`，未匹配时报错。该检查是格式检查，不验证所选 action 的语义是否正确。

实测旧 Kimi action 请求：500 token 上限下 finish_reason 为 length，499 个 token 用于 reasoning，content 为空；2048 上限也出现耗尽。由此证明至少一个实际故障在模型输出预算/推理模式与旧 prompt 的组合，而不只是标签解析。最初仅修改解析的处理是不完整的。

这些修复改善了错误可观测性，但并不保证内容正确；例如未闭合 think、截断回复、模型臆测都不能仅靠当前解析器排除。原始 shared LLM 封装仍只返回字符串，未保留 finish_reason/usage，完整诊断仍有缺口。

## 3. 对话历史：输入确实发生了变化

位置：[models.py](../shared/models.py) 第 52 行附近；[tools.py](../system_agent/tools.py) 第 205 行附近。

请求类型新增：

```python
dialogue_history: List[Dict[str, str]] = []
```

system agent 工具将已经存在于 session state 的历史发送给 simulator：

```python
json={"task_id": task_id,
      "question": question,
      "dialogue_history": tool_context.state.get("dialogue_history", [])}
resp.raise_for_status()
```

历史只包含此前 ask_user 的 agent 问题和 user 回复，不等于完整 tool trajectory、模型推理或全部任务事件。当前问题独立发送，收到回答后才追加到历史。

两阶段路径把历史附加到模板后；Kimi 直接路径把历史放进 task context。它可能改善连续澄清，也可能把早先错误答案带入后续回答，因此属于影响交互行为的输入改动，而不是纯日志改动。HTTP 异常现在被工具的外层 except 转为 `Error: ...`，不会当正常回答追加历史。

## 4. Kimi 单阶段路径：最大的可比性变化

位置：[server.py](../user_simulator/server.py) 第 154–203 行附近。

实际路由依据是 **user simulator 的模型名**，与 system agent 模型名无关：

```python
if settings.user_sim_model.startswith("moonshot/kimi-"):
    return _ask_kimi(state, question, dialogue_history)
action = _parse_action(state, question, dialogue_history)
return _generate_response(state, question, action, dialogue_history)
```

原路径先判断 labeled/unlabeled/unanswerable，再根据 action 生成答案；新 Kimi 路径只有一次模型调用。没有独立 action 判定，也没有输出 action 供分析。

新调用参数：

```python
content = _call_llm(prompt, max_tokens=1024, reasoning_effort="none",
                    system_prompt=instructions)
```

`_call_llm` 构造两条消息：

```python
messages = [{"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}]
```

`shared/llm.py` 仅在参数非空时加入 `kwargs["reasoning_effort"]`。system agent 的 `build_adk_model()` 没有在本轮被修改，其 max_tokens=4096 是已有设置。LiteLLM/provider 可能对 temperature 等参数进行转换，不能把代码中的 temperature=0 等同于所有 API 均确定性输出。

当前 Kimi prompt 的用户消息包含：

```python
f"Task ID: {state.task_data.get('instance_id', '')}\n"
f"Original request: {state.clear_query}\n"
f"Ambiguous request: {state.amb_user_query}\n"
f"Ambiguity annotations: {state.get_ambiguity_json()}\n"
f"Ground truth SQL: {state.get_gt_sql_str()}\n"
f"Previous clarification dialogue: {json.dumps(dialogue_history or [], ensure_ascii=False)}\n"
f"Clarification question: {question}\n"
"Your concise answer:"
```

原始清晰问题、标注和 SQL 不是新创造的答案来源，原两阶段 generator 本来就能看到这些隐藏信息。但是新路径新增了明确的 ambiguous request、历史等输入，同时**没有使用原 generator 中的 db_schema 和 SQL_Glot 分段输入**。完整 external_knowledge 定义也没有自动加入；knowledge_ambiguity 通过 get_ambiguity_json 提供。

因此，设置文件里的 `PROMPT_VERSION=v2` 无法单独标识当前 Kimi prompt。记录实验必须同时注明 `kimi_direct` 路由及 server.py 的代码版本/hash。

## 5. 新 system prompt 的具体要求及校准过程

完整文本在 `_ask_kimi()` 的 `instructions` 中。关键原文：

```text
The original clear request and reference SQL define your intent.
... question, and earlier dialogue may contain WRONG assumptions;
they do not override that intent.
Correct any false premise relevant to the question ...
If offered choices are all wrong or partly wrong, reject or qualify them ...
Correct earlier mistaken user replies when needed.
```

目的：解决 alien_5 提问预设 encoding method 时，simulator 沿用错误分组的问题。要求它纠正分组、指标、统计对象和阈值，而不是一味从给定选项里选一个。

信息披露限制：

```text
Use ordinary language and conceptual metric names;
never quote SQL expressions, table aliases, schema identifiers,
internal annotations, or reasoning.
Do not add thresholds or formulas unless asked.
```

对于 SQL/表名/列名/实现细节索取，提示要求固定拒绝：

```text
Sorry, I can clarify my requirements, but cannot provide SQL or database implementation details.
```

这只是 prompt 约束，没有额外验证器保证执行。直接路径曾经历简短 user-only prompt、增加纠错约束、独立 system message 的迭代；36-task pilot 使用的是最后一种。八条校准覆盖了原始错误多选、明确二选一、错误指标组合、错误历史纠正、正常澄清和 SQL 索取，最终那八条符合预期，见 `results/simulator-only/kimi-k2.6/calibration/usersim_calibration_v3.json`。

跨库 pilot 仍出现限制：credit_M_6 给出了表/列名称，vaccine_7 给出 SQL 表达式，cybermarket_2 的答案漏掉筛选条件。八条校准不等于 simulator 在所有任务上可靠。尤其 DDL 任务中用户要求创建的表/列名可能是合法意图，不应和泄露底层 schema 混为一谈；当前拒绝规则可能过宽。

此外，原有 Phase 2 切换只更新 reference_sql，clear_query 仍来自 Phase 1，这个问题本轮未修复。当前直接提示强调清晰问题与 SQL，遇到两者跨阶段不一致时可能受影响；这是风险，不等于已证明每个 Phase 2 结果受损。

## 6. 保存、抽样、暂停和导出

[runner.py](../orchestrator/runner.py) 将每 5 条保存改为每条保存：

```python
with temporary_path.open("w") as f:
    json.dump(output, f, indent=2, default=str)
    f.flush()
    os.fsync(f.fileno())
os.replace(temporary_path, output_path)
...
completed += 1
await _save()
```

此改动在第一次暂停后加入；它不改变 SQL 评测标准或预算。第一次暂停时最初四条尚未落盘，只保留日志摘要。后面 32 条有完整结果；中断中的任务从头重跑，并非恢复到同一个模型调用中间。

新增辅助文件（不属于原 baseline agent 策略）：

- [check_user_simulator.py](../scripts/check_user_simulator.py)：真实 HTTP 校准请求与隐藏输入/输出记录，不自动证明语义正确。
- [test_server.py](../user_simulator/test_server.py)：以 AST 提取部分函数进行无依赖测试；模型响应是 mock，不能替代真实 LLM 验证。
- [prepare_pilot.py](../scripts/prepare_pilot.py)：18 个数据库各抽 2 条，seed=42，排除 alien_1–5，保存配置、hash 和 diff。
- [pause_pilot.py](../scripts/pause_pilot.py)：停止此实验进程，保存已完成标记和剩余列表。日志摘要不能重建完整对话。
- [export_pilot_markdown.py](../scripts/export_pilot_markdown.py)：完整字段展开和原始文件全文封装；不重新执行 evaluator。
- [README.md](README.md)：研究定位、实验观察和校准说明。

`alien_1_gt.md`、`alien_1_trace.md` 是已有未跟踪文件，不属于本轮代码修复。`.env` 中的用户配置与数据/结果属于本地文件；本文不复制密钥，也不把其内容当作已审计的 Git diff。

## 7. 对可比性的影响，以及应如何继续

需要区分三种结论：

1. **当前平台内部机制比较**：在同一 simulator 模型、prompt、任务、evaluator、基础模型和预算下，对比原 system-agent scaffold 与新机制，可以研究新机制在这个环境中的效果。必须注明本地协议；固定环境也不能消除 simulator 错误带来的偏差，尤其新机制可能改变提问方式并受到不同影响。
2. **与官方发布分数比较**：目前不能严格比较。我们的 simulator 协议、模型、抽样任务集和运行配置不同，观察到分数更高/更低不能直接归因于框架或模型。
3. **声称在原 BIRD-INTERACT 协议下改进**：需要在选定的官方/参考配置上，在相同任务集重跑 baseline 和方法。应具体说明使用的是 ADK 还是 reference 实现，而不是笼统称“官方 baseline”。

建议把当前分支保留为诊断/开发环境，冻结并标记 simulator 版本，先实现一个小机制。正式确认实验增加一条 reference-protocol 路径：保留参考的两阶段 prompt 和 action 结构，使用能正常工作的固定 simulator 配置，让 baseline 与新方法都在该路径评估。优先复用可运行的参考配置；不必为了让 Kimi 担任 simulator 而无限修改 benchmark。system agent 和 simulator 是两个独立模型选择。

这不是要求现在再修复全部 benchmark。应预先设定一次有限的参考配置可运行性检查；若仍无法复现，就将论文/报告主张限定为明确披露的 ADK 变体，并用 simulator 审查和敏感性实验说明限制。当前数据仍可用于发现错误模式和开发方法，不应丢弃。

最小研究设计：相同环境下，目标模型+原 scaffold、目标模型+新机制、较强参考模型+原 scaffold。若有余力，再测试较强参考模型+新机制。跨环境时两边都重跑；不要拿本地方法直接减去 README 发布分数作为提升。

## 8. Kimi 3 当前表现与课题定位

现有完整 32 条：P1=12/32=37.5%，P2=9/32=28.125%，平均 reward=11.1/32=0.346875。最初四条日志 reward 均为 0；计入后平均 reward=11.1/36=0.308333。按正常奖励协议推断四条均未通过，则 P1=33.33%，P2=25%。四条的显式阶段字段和完整轨迹并未保存。

这些是“moonshot/kimi-k3 + 当前 ADK scaffold + 修改后的 Kimi simulator”的系统结果，不是 Kimi 3 单独的通用 Text-to-SQL 能力分数。失败还受上下文、输出长度、runtime 停止、simulator 和任务标注影响。

本地根 README 的历史表格自报：Lite 300 条、Claude Sonnet 4.5、patience=3、v1 simulator（Claude Haiku 4.5），a-interact ADK P1=36.67%、P2=23.67%、avg reward=0.328。此处只引用仓库自述，并未核验最新 leaderboard。数字量级相近已足以提醒我们“33% 不自动等于模型很差”，但不能据此断定模型相当、谁更强或已接近顶级模型。

将课题定位为“通过推理时交互机制，改善较低成本模型的多轮 Text-to-SQL 表现，缩小与较强模型的差距”是可研究的方向。建议用**较低成本模型**或**在相同基线下较弱的模型**定义对象，不预先把 Kimi 3 称为弱模型，也不预设一定能追平。

强弱顺序必须用同任务、同 simulator、同 evaluator 的原 scaffold 实测建立。目标指标包括 P1/P2、平均 reward、实际 API token 成本、延迟和交互次数。固定 bird-coins 并不代表 token 或费用相同；比较架构时需要报告额外调用成本，并与“直接增加基础模型推理/采样预算”这样的简单控制比较。

若方法提高准确率但成本超过直接使用较强模型，应如实报告准确率提升与成本取舍；不能自动声称更实用。若只在个别模型或当前 simulator 下有效，也要收窄主张。当前 36 条已用于诊断，适合作开发集；最终验证应使用未参与设计的样本，配对比较并报告不确定性。

当前推荐研究问题：显式维护用户意图、已确认信息与未确认假设，能否在相同或受控成本下改善多轮 SQL 任务完成率？“缩小模型差距”可以作为实验目标和结果分析角度，不必成为必须兑现的结论。
