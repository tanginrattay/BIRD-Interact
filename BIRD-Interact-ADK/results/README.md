# 实验结果归档

历史原始文件按 agent / simulator 分组，完整 JSON、日志、任务集和人工可读 Markdown 均保留。迁移前后逐文件 SHA-256 校验；路径映射、大小和校验值见各对应实验目录内的 `archive_manifest_2026-10-04.json`。没有调用模型或重跑实验。

| 结果 | Agent | Simulator | 说明 |
| --- | --- | --- | --- |
| [早期 10 条](agent-kimi-k2.6/simulator-unknown/early10/eval_kimi26_10.json) | Kimi K2.6（原文件名依据） | 未记录，未知 | P1/P2 均 0；早期调试，不作健康 baseline |
| [早期 5 条](agent-kimi-k3/simulator-unknown/early5/eval_kimi3_5.json) | Kimi 3（原文件名依据） | 未记录，未知 | P1/P2 均 0；早期调试，不作健康 baseline |
| [修复后初始 5 条](agent-unknown/simulator-unknown/initial5_repaired/eval_initial5.json) | 未保存型号，待确认 | Kimi 路径，但具体型号未保存，待确认 | 原默认 `eval_a_interact.json`；P1 2/5，P2 1/5，平均 reward 0.34 |
| [36 条 pilot 人读报告](agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42/markdown/README.md) | `moonshot/kimi-k3` | `moonshot/kimi-k2.6` | metadata 明确记录；seed42；单阶段 kimi_direct；不是后来新增的 K3-low 或 Qwen 版本 |
| [校准 v2](simulator-only/kimi-k2.6/calibration/usersim_calibration_v2.json) / [v3](simulator-only/kimi-k2.6/calibration/usersim_calibration_v3.json) | 无 system agent | `moonshot/kimi-k2.6` | 各 8 条直接 simulator 请求；JSON 的 prompt_version 均为 v2，文件 v2/v3 是校准迭代编号 |

36 条 pilot：32 条有完整 JSON，4 条仅有日志摘要；请勿把这四条说成有完整轨迹。`baseline_resume1.json` 和 `baseline_resume2.json` 是同一 pilot 的分段，不是独立实验。旧 checkpoint/remaining_tasks 不是当前待运行清单。归档中的原始 source_manifest 和 Markdown 源文本故意不改写，里面的旧绝对/相对路径可通过对应实验目录内的迁移清单定位；归档目录内的相对报告链接仍有效。

## 后续运行

runner 不指定 `--output` 时自动生成独立目录：

```text
results/agent-<配置模型>/simulator-<配置模型>/<UTC时间>-<随机ID>/eval_a_interact.json
```

目录内的 `eval_a_interact.json` 只属于这一次运行，不再写入根目录默认文件。显式 `--output` 也拒绝覆盖已存在结果。JSON 的 `run_metadata` 保存 agent/simulator 配置、pipeline、thinking 开关、prompt_version、任务文件和预算等，不含密钥。它记录 runner 配置，不是服务实际模型的独立证明：换模型后仍须重启对应服务。历史结果不能用当前 DeepSeek Flash / Qwen 3.7 Plus 配置回填。

继续同一任务集时使用新输出文件并保留旧分段；不要覆盖历史结果。归档路径中的 unknown 是证据不足标记，而非模型名称。

## DeepSeek V4.1 Flash 1017 / 原版v1 / 72题 baseline

[完整报告](agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/baseline72_v1_20261028/README.md)：72题全部完成。统一模型配置deepseek-v4.1-flash-1017，原版v1两阶段，非思考模式。P1=29/72，P2=13/72，平均reward=0.336111。该目录作为本批实验的统一结果入口，包含完整JSON、任务集、逐题Markdown及校验清单。

## DeepSeek Flash / V4 Pro：36题对照

[对照报告](agent-deepseek-deepseek-flash/simulator-qwen3.7-plus/pilot36_seed42_20261004_retry1/deepseek_pilot36_comparison_20261004.md)与共享比较JSON归入Flash的对应实验目录，报告同时链接两组原始结果；初次TLS失败状态归入未带retry1的对应实验目录。

## 百炼 DeepSeek V4.1 Flash 1017 早期运行

[早期归档](agent-openai-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/baseline72_v1_20261028T033527Z/README.md)中的 `openai/` 是OpenAI兼容接口的路由前缀，实际模型及提供方是百炼DeepSeek，并非OpenAI模型。该归档主结果含11条有效完整记录和56条接口错误，另一次重试含61条接口错误；11条有效记录与最终72题归档逐字段相同，但错误记录、服务日志及元数据不相同，因此保留。完整72题结果仍以上方统一归档为准。

## DeepSeek V4.1 Flash 1017 / Native Requirement State / 72题

[实验说明](agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/requirement_native72_20261108T101116Z/README.md)、[结果汇总](agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/requirement_native72_20261108T101116Z/RESULTS.md)：与上方 Baseline 的72题内容和顺序一致；P1=15/72，P2=7/72，平均reward=0.175。Agent与Simulator均调用DeepSeek官方API，请求名为deepseek/deepseek-flash，按用户确认归档为V4.1 Flash 1017。完整Session、State记录、源码快照和迁移说明均在目录内。
