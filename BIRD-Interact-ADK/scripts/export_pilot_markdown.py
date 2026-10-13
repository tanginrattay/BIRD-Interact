"""Render every saved pilot field and archive exact source text in Markdown."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path('results/agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42')
OUT = ROOT / 'markdown'


def fence(text, language='text'):
    length = max([len(x) for x in re.findall(r'`+', text)] + [2]) + 1
    marker = '`' * length
    return f'{marker}{language}\n{text}\n{marker}\n\n'


def render(value, label, depth=2):
    heading = '#' * min(depth, 6)
    result = f'{heading} {label}\n\n'
    if isinstance(value, dict) and value:
        return result + ''.join(render(v, k, depth + 1) for k, v in value.items())
    if isinstance(value, list) and value:
        return result + ''.join(render(v, f'{label}[{i}]', depth + 1) for i, v in enumerate(value))
    if isinstance(value, str):
        return result + fence(value, 'sql' if label == 'sql' else 'text')
    return result + fence(json.dumps(value, ensure_ascii=False), 'json')


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / 'tasks').mkdir(exist_ok=True)
    (OUT / 'sources').mkdir(exist_ok=True)
    tasks = list(map(json.loads, (ROOT / 'tasks.jsonl').read_text().splitlines()))
    records = {}
    for path in sorted(ROOT.glob('baseline_*.json')):
        for record in json.loads(path.read_text())['results']:
            assert record['task_id'] not in records
            records[record['task_id']] = (path.name, record)
    checkpoint = json.loads((ROOT / 'pause_checkpoint.json').read_text())
    summaries = {r['task_id']: r for r in checkpoint['completed_from_log']}
    sources = [*sorted(ROOT.glob('baseline_*.json')), *sorted(ROOT.glob('baseline_*.log')),
               ROOT / 'metadata.json', ROOT / 'pause_checkpoint.json', ROOT / 'tasks.jsonl',
               ROOT / 'remaining_tasks.jsonl', ROOT / 'code_changes.patch']
    manifest = []
    for source in sources:
        raw = source.read_text()
        block = fence(raw, 'json' if source.suffix == '.json' else 'text')
        # Verify exact textual round trip, including trailing newlines.
        opening_end = block.index('\n') + 1
        closing_start = block.rfind('\n' + re.match(r'`+', block).group(0) + '\n\n')
        assert block[opening_end:closing_start] == raw
        name = source.name + '.md'
        (OUT / 'sources' / name).write_text(f'# 原始文件：{source.name}\n\n以下代码块完整保留原始文本；旧检查点仅表示当时进度。\n\n' + block)
        manifest.append({'source': str(source), 'markdown': str(OUT / 'sources' / name),
                         'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
    rows = []
    for task in tasks:
        task_id = task['instance_id']
        name = task_id + '.md'
        if task_id in records:
            source, record = records[task_id]
            text = f'# {task_id}\n\n[返回总览](../README.md) · 来源：{source}\n\n'
            text += '全部结果字段按原顺序展开；字符串原样放入代码块。ADK 事件、工具结果和最终回复均不裁剪。\n\n'
            text += render(record, '完整评测记录')
            text += render(task, '研究者对照用：完整 benchmark task（包含隐藏信息）')
            asks = sum(t.get('tool') == 'ask_user' for t in record.get('tool_trajectory', []))
            row = f"| [{task_id}](tasks/{name}) | {record.get('phase1_passed')} | {record.get('phase2_passed')} | {record.get('total_reward')} | {record.get('budget_remaining')} | {asks} | 完整 |"
        else:
            record = summaries[task_id]
            text = f'# {task_id}\n\n[返回总览](../README.md)\n\n**只有日志摘要，完整 SQL、对话和 ADK 轨迹没有保存，无法恢复。**\n\n'
            text += render(record, '已保存摘要') + render(task, '完整 benchmark task（不是运行轨迹）')
            row = f"| [{task_id}](tasks/{name}) | 未保存 | 未保存 | {record['total_reward']} | 未保存 | 未保存 | 仅日志 |"
        (OUT / 'tasks' / name).write_text(text)
        rows.append(row)
    (OUT / 'source_manifest.json').write_text(json.dumps(manifest, indent=2))
    index = '''# 36-task pilot：结果与分析

全部 36 条均已执行结束。最后一条 virtual_M_4 在 2026-09-29 20:13:59 完成。

## 阅读方法与完整性

每条任务单独一个 Markdown，依次包含原始结果的所有字段、完整 dialogue_history、tool_trajectory、adk_events、final_response，以及额外提供的 benchmark task 全字段。字符串不截断、不概括；同一内容出现在多个源字段时也保留，不去重。

`sources/` 将原始 JSON、日志、配置、抽样任务和代码差异完整封装为 Markdown，生成时逐一验证文本往返一致；`source_manifest.json` 保存源文件 SHA-256。JSON 中已有的 `<truncated>` 是原记录的裁剪，导出不能恢复；可对照同任务 ADK 事件寻找更完整内容。

最初 4 条（alien_11、alien_7、archeology_1、archeology_9）在第一次暂停前没有保存完整结果，只有日志中的 reward、预算消耗和耗时。这里不会编造其 SQL、对话或阶段状态。旧 pause_checkpoint 和 remaining_tasks 状态不能用于判断最终是否完成。

本材料含隐藏真实问题和参考 SQL，仅供研究者分析，不能输入被评测 system agent。

## 总体指标与分母

| 范围 | 任务数 | P1 通过 | P2 通过 | 总 reward | 平均 reward |
| --- | ---: | ---: | ---: | ---: | ---: |
| 完整 JSON 记录 | 32 | 12（37.50%） | 9（28.13%） | 11.1 | 0.346875 |
| 另存日志摘要 | 4 | 未显式保存 | 未显式保存 | 0 | 0 |
| 全部 pilot | 36 | 12/36（33.33%，由零 reward 推断其余四条未通过） | 9/36（25.00%，同一假设） | 11.1 | 0.308333… |

完整记录中 32 条都有 follow-up；进入 Phase 2 的 12 条有 9 条通过（条件成功率 75%）。这不能说明 Phase 2 普遍更容易：只有先通过 Phase 1 的任务才能进入。

这是 18 个数据库各 2 条的均衡诊断样本，排除了最初用于开发的 alien_1–5。结果不是 Lite 全集随机任务成功率的无偏估计，也没有重复运行来估计模型波动。system agent 为 moonshot/kimi-k3，simulator 为 moonshot/kimi-k2.6；详细配置见来源附件。暂停后的 runner 仅调整为逐条原子保存结果，其代码变更晚于最初 metadata 中的指纹。

## 观察、证据与研究意义

### 1. 固定 fallback 已消失，但 simulator 仍需忠实性审查

完整 32 条里，22 条使用了 ask_user，共 31 次；没有出现原来的固定 fallback。这只证明恢复了可用回答，不能证明每条都正确。

- cybermarket_2：回复说 Trusted Vendors 需要认证级别和 VTI > 80 两个条件；参考 SQL 还要求 dispute ratio < 0.05 和 vendspan > 90。提交也漏掉这些条件，并且输出列/市场连接与目标不同。这是 simulator 不完整回答与 SQL 语义偏差并存的明确案例，不能把失败完全归因于 system agent。
- credit_M_6：simulator 给出确切列名 fsi，以及 employment_and_income、expenses_and_assets 等表名。vaccine_7 直接给出 NULLIF/CURRENT_DATE SQL 表达式。说明八条校准通过并未保证跨库的信息披露边界稳定。对 DDL 任务还需区分用户明确指定的新对象名称与底层 schema 泄露，不能机械地禁止一切名称。
- museum_6 的 Phase 2 澄清有有效回答；但服务实现切换阶段时只更新 reference_sql，clear_query 仍是 Phase 1。应审查 follow-up 上下文一致性，这属于待验证风险，不是已证明导致该任务失败的因素（该任务实际通过）。

因此，这批结果应命名为“当前 simulator 版本下的诊断 baseline”。若继续修改 simulator，后续方法比较应重跑同一配置下的 baseline，避免混用环境版本。

### 2. 失败后未继续行动，比单纯预算耗尽更值得优先排查

11/32 条结束时尚余至少 3 coins 且未完成两个阶段：cross_db_5、crypto_3、cybermarket_2、disaster_3、fake_1、gaming_M_4、news_9、solar_4、vaccine_2、virtual_6、virtual_M_4。其中 fake_1 和 gaming_M_4 一次 submit_sql 都没有调用。

许多最终文本停在未完成的分析或 SQL 中。shared/llm.py 为 ADK model 配置了 max_tokens=4096，这是应检查的候选因素；现有导出没有足够的模型 finish_reason 证据，不能直接认定全部是 token 截断。先记录终止原因、工具调用是否生成及 token usage，区分运行控制和策略选择，再设计失败恢复机制。

### 3. 澄清需要覆盖完整查询意图，尤其是范围、粒度和指标

- crypto_3：澄清指出按 riskandmarginpivot 取前 5 条；提交却升序排序，并连接 orders/marketdata 取得多条波动率。参考 SQL 是 pivot 降序前 5 条，配合全局单条最新波动率。说明澄清后的局部映射正确仍不足以得到完整语义。
- vaccine_2：成功澄清了传感器状态，但提交用原始 tempstabidx 代替复合 TSS，缺少目标中的 critical 过滤、时间范围及舍入等逻辑。不能因为有一次有效 ask_user 就认为意图已完整确认。
- solar_3：失败后澄清 TPCI，下一次 Phase 1 提交成功，是有价值的正例；但没有配对消融，不能量化澄清带来的因果收益。

这支持研究“明确的意图状态＋提交前语义检查”：记录分组/统计对象、指标、过滤、时间、排序和输出结构，并标识哪些已确认，哪些仍是假设。应使用普通 task query 和交互信息，不能把研究者可见的 GT 注入 agent。

### 4. 不要用相关性证明问得更多就更好

有澄清的 22 条中 P1 成功 8 条；没有澄清的 10 条中成功 4 条。样本难度、任务类型和 agent 的选择都不同，这组比例不能说明 ask_user 有害或无效。需要固定任务和模型做配对比较。

## 建议的下一步

先审查 simulator 忠实性与终止原因两个实验基础问题，再选一个机制做对照。优先候选是语义检查/澄清覆盖；预算规划也有动机，但不能把所有停止都解释为预算问题。

目前无需直接扩跑 300 条。先用已发现的代表案例定位运行终止原因、核对不完整/过度披露的 simulator 回复，然后冻结环境版本。若要完整分析全 36 条轨迹，需要补跑最初 4 条；补跑是新的随机运行，不能伪装为旧运行轨迹。修复环境后再用同一任务集比较 baseline 与单一机制，最终在独立保留集验证。

## 逐任务索引

| Task | P1 | P2 | Reward | 剩余 coins | ask_user | 记录完整性 |
| --- | --- | --- | ---: | ---: | ---: | --- |
'''
    index += '\n'.join(rows) + '\n\n## 原始来源全文\n\n'
    index += ''.join(f'- [{item["source"].split("/")[-1]}](sources/{Path(item["markdown"]).name})\n' for item in manifest)
    (OUT / 'README.md').write_text(index)
    print(f'Exported {len(tasks)} task Markdown files and {len(sources)} exact source archives to {OUT}')


if __name__ == '__main__':
    main()
