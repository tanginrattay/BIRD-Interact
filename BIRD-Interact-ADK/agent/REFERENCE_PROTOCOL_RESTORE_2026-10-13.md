# 原版 simulator 协议恢复与 Qwen 验证状态

2026-10-13：修改前状态已提交为 `5aa6d55`。原版 ADK 基点为 `451fe2c`。

## 已恢复

- `user_simulator/server.py` 的任务状态、阶段切换、两阶段 action/response 模板构造、token 上限（v2 action=500、response=1024）、标签解析、异常/fallback 处理均恢复为原版。
- 移除 `_ask_direct` 新提示词和单阶段路由，不向 simulator 追加澄清历史。
- `shared/models.py`、`system_agent/tools.py` 恢复为原版。
- `user_simulator/prompts.py`、system agent 提示与预算回调、数据库 evaluator 未修改。
- `.env` 将 `USER_SIM_PIPELINE` 改为 `two_stage`；配置仅接受此值。服务运行时固定两阶段。

`server.py` 相对原版只新增三行 Qwen 调用分支。百炼客户端保留独立密钥、enable_thinking=false 与原版相同的输出上限；非正常 finish_reason 会在客户端报错，随后按原版外层逻辑返回空字符串。没有扩充 token 或修改模型提示来强制通过。

保留结果原子保存、每条保存和独立输出目录，这些不改变打分或 agent 决策。DeepSeek 接入及模型调用参数保留。K3-low 设置仍在共享模型封装中，当前 DeepSeek/Qwen 路径不使用它；历史 Kimi 成绩配置不能据此回填。

## 验证

`python -m unittest user_simulator.test_server user_simulator.test_bailian shared.test_llm -v`：12 项通过。

新增测试对原版 simulator 除 `_call_llm` 外的所有函数/类做 AST 一致性检查，并对 prompts、请求模型、system agent 工具/提示/预算文件做字节一致性检查。百炼客户端用 mock HTTP 验证，不能证明真实 API 可用。

真实验证入口：

```bash
python -m scripts.check_reference_simulator --output results/reference_protocol_qwen_20261013/probe_live.json
```

该脚本用 Lite 随附 schema 文本，运行原版 `_parse_action` / `_generate_response`，真实模型请求记录原始输出、action、fallback 和错误。覆盖9问、3个数据库、6个独立任务，不运行 system agent，不执行 SQL 评分。输出包含隐藏测评信息，只供研究者查看。

当前尚未完成真实验证：沙箱内18次模型请求均网络失败；`results/reference_protocol_qwen_20261013/probe.json` 是受限网络失败记录，不能视为模型失败或正式成绩。网络升级被自动审批拒绝，原因是向外部 Qwen API 发送隐藏参考 SQL 和歧义标注尚未获得明确的数据发送授权。等待用户对此明确授权后再运行，不绕过审批。

恢复的是仓库 ADK 原版协议，不等于已经核验论文参考实现完全一致。Qwen 替换论文 simulator、prompt v1/v2 和任务范围仍须披露；恢复协议后也不能把跨配置分数差异全归因于 agent 方法。


## 三次服务验证准备（用户缩减测试范围）

用户随后要求仅三次，并按 agent/README.md 启动环境。已启动 PostgreSQL 和三个服务，启动输出为 `ALL_SERVICES_READY`。新增 `scripts/check_reference_service.py`：从真实数据库环境服务初始化任务及 schema，再对 simulator 的 `/ask` 发送 alien_1/2/3 三个问题。两阶段共六次模型请求，不调用 system agent、不打分。

实际执行仍被自动审批拒绝，理由是用户授权了三次测试，但没有明确批准隐藏 SQL、歧义标注和 schema 外发到 Qwen 百炼 API。本轮没有发生三次真实澄清调用，无模型可用性结论。测试服务在临时执行会话中运行，之后可能需要按 README 重启。

获明确外发授权后的命令：

```bash
python -m scripts.check_reference_service
```


## 实际框架三任务验证已完成

用户进一步明确允许测评框架涉及的数据外发后，直接使用 runner 跑完 alien_1、alien_2、alien_3。共五次 ask_user，四次实质回复，一次仅返回 action 标签，无统一 fallback。P1/P2 均1/3，平均reward=0.3333；服务日志两次 length 截断。没有执行独立校准脚本。详见 [本次报告](../results/reference_protocol_qwen_20261013/README.md) 和 [完整结果](../results/reference_protocol_qwen_20261013/eval_three.json)。此前审批阻断条目为历史记录，已不代表当前验证状态。


## 最新：恢复原版content处理，五任务已完成

按用户要求移除了百炼非stop拒绝检查与空串主动报错，直接content.strip()，由原版解析器处理。12项离线检查通过。重新启动服务后，runner运行alien_1–5：全部完成，无任务级错误；P1=1/5，P2=0/5，平均reward=0.14。五次实际simulator回复：一次实质回答、两次仅action标签、两次拒答；另一次ask_user被预算拦截。没有空文本或统一fallback，但仍有明确格式问题。

最新结论及附件见 [五任务报告](../results/reference_protocol_qwen_20261013/five_original_content/README.md)。前文保留非stop拒绝检查的描述为历史状态，当前已经删除。


## 最新诊断：第一阶段截断与无效action传播

保持v2及500/1024预算，对alien_1/3两个原始异常问题各复现一次，共四次Qwen请求。alien_1正常；alien_3第一阶段输出500 tokens后length截断，未生成action，原版解析取第一行`<think>`传入第二阶段；第二阶段真实输出只有`<s>labeled("interference level")</s>`（stop，12 tokens），不存在被解析遗漏的自然语言答案。关闭API thinking不能阻止v2提示词要求的普通content内think文本。详细证据与后续判断见 [诊断报告](../results/reference_protocol_qwen_20261013/diagnosis_two_cases/README.md)。本次仅增加独立诊断脚本，没有修改原版prompt或解析逻辑。


## 最新：Lite切换v1后的五任务测试

用户要求按Lite论文配置尝试v1。确认本地Lite共300条后，.env已设置PROMPT_VERSION=v1并重启服务；当前保留v1。同样运行alien_1–5，代码与上一轮v2的hash一致；v1原版action=200、response=1024。五条全部完成：P1=1/5、P2=1/5、reward=0.20。十次澄清中4次实质回答、5次固定fallback、1次action-only，服务日志另有一次连接中断。v1仍未稳定可用，不能由分数上升判定兼容性已解决。详情见 [v1五任务报告](../results/reference_protocol_qwen_20261013/five_v1/README.md)。


## 最新：百炼17型号两版本四问矩阵完成

无需重跑：136澄清、272阶段HTTP200，13项离线检查通过。原版两阶段prompt/解析/预算不改，运输层增加17裸型号支持。结果、诊断与候选建议见 [矩阵汇总](../results/simulator_matrix_bailian_20261013/README.md) 及 [接手说明](SIMULATOR_MATRIX_BAILIAN_2026-10-13.md)。主.env保持Qwen3.7 Plus/v1。
