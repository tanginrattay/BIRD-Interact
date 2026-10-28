# Qwen 3.7 Plus simulator 接入

> 2026-10-13 更新：当前代码已恢复原版两阶段 simulator 协议；下文单阶段说明属于历史状态。恢复范围和待完成验证见 [恢复记录](REFERENCE_PROTOCOL_RESTORE_2026-10-13.md)。

本次只切换 user simulator。system agent 仍使用原有 Moonshot Kimi 3 配置；原密钥、budget、system agent policy 均不改动。

## 配置

在项目根目录 `.env` 中填写 `USER_SIM_API_KEY=`，不要把 Key 提交到 Git 或粘贴进聊天。

```dotenv
USER_SIM_MODEL=qwen3.7-plus
USER_SIM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
USER_SIM_API_KEY=
USER_SIM_PIPELINE=single_stage
USER_SIM_ENABLE_THINKING=false
USER_SIM_THINKING_BUDGET=2048
```

默认地址对应百炼华北2（北京），Key 必须与地域匹配。也可将 API_BASE 改为控制台提供的业务空间专属地址 `https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`。不要在 API_BASE 后加 `/chat/completions`，代码会追加。

`false` 为非思考模式，方向上对应此前网页快速测试，但网页与 API 不保证等价。不是 `reasoning_effort=low`。若需要有限思考，将 ENABLE_THINKING 改为 true，2048 为自选思考 token 上限，并非官方 low 档；此时总输出上限为思考预算+1024，避免把全部空间挤占成思考。1024 为原有单阶段回答预算。此调整不涉及 bird-coins。

## 调用逻辑

- `shared/config.py`：增加独立 simulator 配置，Key 不进入 Settings 的 repr。
- `user_simulator/bailian.py`：现有 httpx 直接请求百炼兼容 API，不增加 SDK 依赖；不继承 Moonshot、OPENAI 或共享 LiteLLM Key/base。
- `user_simulator/server.py`：协议可选 `single_stage / two_stage / auto`。Qwen 与 Kimi 使用同一个 `_ask_direct` 提示及隐藏上下文构造。此次未修改提示词，不修正 C09 边界争议，避免模型迁移时混入 prompt 实验。
- `scripts/check_user_simulator.py` 和 `scripts/prepare_pilot.py`：保存协议及 Qwen 思考配置，不再将非 Kimi 模型一律误记为两阶段。这些值来自本地配置，运行前须确保服务已重启且使用同一环境，不是服务器实际请求抓包。
- HTTP JSON 顶层发送 `enable_thinking`；按需发送 `thinking_budget`；使用 `max_completion_tokens` 控制总输出。不是把 extra_body 嵌套进 HTTP JSON，也不向 Qwen 发送 Kimi 的 reasoning_effort=none。
- 只读取最终 `message.content`，不把 `reasoning_content` 当回答。HTTP错误、空答及 length 截断显式报错，不转成用户不理解，也不自动重试扩大费用。普通日志只记模型、结束原因和用量，不输出 Key/隐藏 prompt；用量目前不写入 benchmark 结果 JSON。
- Key 留空时，在发请求之前明确报缺少 USER_SIM_API_KEY。

## 验证与生效

离线测试（不调用付费 API）：

```bash
conda activate bird-interact
python -m unittest user_simulator.test_server user_simulator.test_bailian shared.test_llm -v
```

填好 Key 后，需要重启 user simulator 服务使新环境变量生效。不要在未完成的 benchmark 中途重启或切换模型；已有 shell 中同名环境变量优先于 `.env`。现有 `scripts/start_services.sh` 会 pkill uvicorn 并重启三个服务，只在确认没有其他进行中的任务后使用。

可以复用已有的实时校准脚本（会产生 API 费用，且依赖服务已启动）：

```bash
python -m scripts.check_user_simulator --output results/usersim_qwen37_first.json
```

该脚本是原有8问校准，不是网页10问全集，尚未包含 gaming_7/cybermarket_2。本次只做 mock HTTP 和本地上下文验证，没有进行真实 API 连通性或语义质量验收。

## 文档依据

核查日期：2026-10-04。

- [百炼 OpenAI兼容 Chat API](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-chat-completions)：地址、消息格式、enable_thinking、thinking_budget、max_completion_tokens。
- [Qwen 3.7 Plus 模型信息](https://help.aliyun.com/zh/model-studio/qwen3-7-plus)：模型名、能力、上下文和地域。

本地 single_stage 协议不是原论文两阶段 simulator 的等价复现。新实验请单独标记 Qwen 型号、思考配置和 single_stage，不与历史 Kimi 配置混为同一 baseline。
