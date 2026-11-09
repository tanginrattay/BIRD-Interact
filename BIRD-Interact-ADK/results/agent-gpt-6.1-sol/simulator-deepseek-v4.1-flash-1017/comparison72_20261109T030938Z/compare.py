import json,csv,sys,hashlib
from pathlib import Path
b=Path(sys.argv[1]);names=['baseline_main','requirement_tracking'];data={n:json.loads((b/n/'eval_a_interact.json').read_text()) for n in names};maps={n:{r['task_id']:r for r in d['results']} for n,d in data.items()};ids=list(maps[names[0]]);assert len(ids)==72 and set(ids)==set(maps[names[1]])
rows=[]
for tid in ids:
 a=maps[names[0]][tid];s=maps[names[1]][tid]
 rows.append({'task_id':tid,'baseline_p1':a['phase1_passed'],'state_p1':s['phase1_passed'],'baseline_p2':a['phase2_passed'],'state_p2':s['phase2_passed'],'baseline_reward':a['total_reward'],'state_reward':s['total_reward'],'reward_delta':round(s['total_reward']-a['total_reward'],10),'baseline_budget_used':a['budget_used'],'state_budget_used':s['budget_used'],'baseline_ask_user':sum(t.get('tool')=='ask_user' for t in a['tool_trajectory']),'state_ask_user':sum(t.get('tool')=='ask_user' for t in s['tool_trajectory'])})
with (b/'paired_comparison.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary={}
for phase in ['p1','p2']:
 summary[phase]={'gained':[r['task_id'] for r in rows if r['state_'+phase] and not r['baseline_'+phase]],'lost':[r['task_id'] for r in rows if r['baseline_'+phase] and not r['state_'+phase]]}
summary['reward_increased']=[r['task_id'] for r in rows if r['reward_delta']>0];summary['reward_decreased']=[r['task_id'] for r in rows if r['reward_delta']<0]
summary['average_reward_delta']=data[names[1]]['metrics']['average_reward']-data[names[0]]['metrics']['average_reward'];summary['same_task_bytes']=(b/names[0]/'tasks.jsonl').read_bytes()==(b/names[1]/'tasks.jsonl').read_bytes();summary['single_run_per_variant']=True
(b/'paired_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
lines=['# AINET gpt-6.1-sol：同配置 72 题对照','', '| 分支 | P1 | P2 | 平均 reward | 运行错误 |','|---|---:|---:|---:|---:|']
for name in names:
 m=data[name]['metrics'];v=json.loads((b/name/'validation.json').read_text());lines.append(f"| {name} | {m['phase1_count']}/72 ({100*m['phase1_rate']:.2f}%) | {m['phase2_count']}/72 ({100*m['phase2_rate']:.2f}%) | {m['average_reward']:.6f} | {len(v['task_errors'])} |")
lines+=['',f"Requirement-tracking 平均 reward 差值：{summary['average_reward_delta']:+.6f}。每组只运行一次，不能据此确定稳定的因果收益。",'', '## 固定配置','', 'Agent：AINET `/v1/chat/completions`，`openai/gpt-6.1-sol`，原 4096 输出上限（LiteLLM 映射为 `max_completion_tokens`）。网关拒绝 `temperature`，两组统一通过仅作用于 agent 的 `litellm.drop_params=True` 省略该参数；未显式指定 reasoning effort。','', 'Simulator 与 2026-11-08 native 72 题保持一致：官方 DeepSeek endpoint，`deepseek/deepseek-flash`（历史实验由用户确认对应 DeepSeek v4.1 Flash 1017），`v1`、`two_stage`、thinking disabled、patience 3。Simulator、shared、DB 源文件逐一验证与昨日快照哈希相同。','', '复用昨日 72 题的原始字节及顺序；a-interact，并发 1。两组来自 main、state/requirement-tracking 的独立已提交快照；原工作分支和未提交改动保留。模型参数兼容启动失败的记录另存，未混入正式结果。','', '## 配对变化','']
for phase in ['p1','p2']:lines.append(f"- {phase.upper()}：新增通过 {len(summary[phase]['gained'])} 题，失去通过 {len(summary[phase]['lost'])} 题；具体 task IDs 见 paired_summary.json。")
lines+=['', '## 用量（服务报告，不等同于账单）','', '| 组别 | Agent prompt | Agent output | Agent total | Simulator total |','|---|---:|---:|---:|---:|']
for name in names:
 v=json.loads((b/name/'validation.json').read_text());u=v['agent_usage'];su=v['simulator_usage'];lines.append(f"| {name} | {u.get('prompt_token_count',0)} | {u.get('candidates_token_count',0)} | {u.get('total_token_count',0)} | {su.get('total_tokens',0)} |")
lines+=['', '缓存及 reasoning 用量详情见各组 validation.json；未取得单价和账单，不推算金额。服务返回的模型 ID 不构成底层模型身份的独立验证。','', '## 证据','', '- [Baseline 完整逐题轨迹](baseline_main/markdown/README.md) · [交互式报告](baseline_main/report.html) · [原始结果](baseline_main/eval_a_interact.json)','- [Requirement 完整逐题轨迹](requirement_tracking/markdown/README.md) · [交互式报告](requirement_tracking/report.html) · [原始结果](requirement_tracking/eval_a_interact.json)','- [逐题配对 CSV](paired_comparison.csv) · [配对摘要](paired_summary.json) · [实验配置及 commit](manifest.json)','- [State 结构及持久化审计](requirement_tracking/state_validation.json)：不评估 requirement 的语义覆盖或错误消歧。','', '原始 session、ADK events、工具轨迹、日志、source_snapshot 和 SHA-256 均保留。Markdown 无新增截断；源数据中已有的截断无法恢复。']
(b/'COMPARISON.md').write_text('\n'.join(lines)+'\n');print(json.dumps(summary,ensure_ascii=False,indent=2))
