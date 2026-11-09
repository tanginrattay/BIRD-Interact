import json,hashlib,re,sys,importlib.util
from pathlib import Path
from collections import Counter
base=Path(sys.argv[1]);names=sys.argv[2:] or ['baseline_main','requirement_tracking']
def fence(text,lang='json'):
 n=max([len(s) for s in re.findall(r'`+',text)]+[2])+1;m='`'*n
 return m+lang+'\n'+text+'\n'+m+'\n\n'
for name in names:
 run=base/name;data=json.loads((run/'eval_a_interact.json').read_text());rows=data['results'];assert len(rows)==72
 out=run/'markdown';out.mkdir(exist_ok=True);index=['# '+name+': 72 task trajectories','','All saved result fields are preserved without additional truncation. Any truncation already present in the source remains unchanged.','', '| Task | P1 | P2 | Reward | Budget used |','|---|---|---|---:|---:|'];counts=Counter()
 for r in rows:
  text='# '+r['task_id']+'\n\n[Task index](README.md)\n\n'
  for k,v in r.items():text+='## '+k+'\n\n'+fence(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,indent=2),'text' if isinstance(v,str) else 'json')
  (out/(r['task_id']+'.md')).write_text(text)
  index.append(f"| [{r['task_id']}]({r['task_id']}.md) | {r.get('phase1_passed')} | {r.get('phase2_passed')} | {r.get('total_reward')} | {r.get('budget_used')} |")
  counts.update(t.get('tool','UNKNOWN') for t in r.get('tool_trajectory',[]))
 (out/'README.md').write_text('\n'.join(index)+'\n')
 extra={'tool_trajectory_counts':dict(counts),'total_budget_used':sum(r.get('budget_used',0) for r in rows),'task_elapsed_seconds_total':sum(r.get('elapsed_seconds',0) for r in rows),'source_result_sha256':hashlib.sha256((run/'eval_a_interact.json').read_bytes()).hexdigest(),'exported_tasks':72}
 (run/'trajectory_summary.json').write_text(json.dumps(extra,indent=2)+'\n')
 spec=importlib.util.spec_from_file_location('frozen_report',run/'source_snapshot/orchestrator/report.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.generate_html(str(run/'eval_a_interact.json'),str(run/'report.html'))
 hashes={str(p.relative_to(run)):hashlib.sha256(p.read_bytes()).hexdigest() for p in run.rglob('*') if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and p.suffix in ['.json','.jsonl','.log','.md','.py','.html'] and p.name!='evidence_sha256.json'}
 (run/'evidence_sha256.json').write_text(json.dumps(hashes,indent=2)+'\n');print(name,'exported',len(rows),'tasks; hashed',len(hashes),'evidence files')
