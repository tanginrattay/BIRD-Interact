"""Summarize observed metrics; do not invent semantic quality scores."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
RUN=Path(__file__).resolve().parent
result=json.loads((RUN/"eval_a_interact.json").read_text())
audit=json.loads((RUN/"state_validation.json").read_text())
rows=result["results"]
history=[h for r in rows for h in r.get("requirement_state_history",[])]
missing=[]
for r in rows:
    for i,h in enumerate(r.get("requirement_state_history",[])):
        if not h["accepted"]:
            text="".join(p.get("text","") for p in (h.get("model_content") or {}).get("parts",[]) if not p.get("thought"))
            missing.append({"task_id":r["task_id"],"response_index":i+1,"kind":"missing" if "state_update" not in text else "invalid","error":h["error"],"model_content":h.get("model_content")})
(RUN/"state_missing_and_invalid.json").write_text(json.dumps(missing,ensure_ascii=False,indent=2)+"\n")
sim=[json.loads(line) for line in (RUN/"simulator_usage.jsonl").read_text().splitlines()] if (RUN/"simulator_usage.jsonl").exists() else []
trajectory=[t for r in rows for t in r.get("tool_trajectory",[])]
log_checks={}
for name in ["agent_service","simulator_service","db_service","runner"]:
    lines=(RUN/(name+".log")).read_text(errors="replace").splitlines()
    log_checks[name]=[{"line":i+1,"text":v} for i,v in enumerate(lines) if re.search(r"Traceback|\bERROR\b|LLM call failed|HTTP/1\.1[\" ]+[45]\d\d",v)]
(RUN/"log_validation.json").write_text(json.dumps(log_checks,ensure_ascii=False,indent=2)+"\n")
count=len(history);accepted=sum(h["accepted"] for h in history);absent=sum(h["kind"]=="missing" for h in missing)
summary={"task_count":len(rows),"metrics":result["metrics"],"state_responses":count,"accepted_updates":accepted,"missing_updates":absent,"invalid_updates":len(missing)-absent,"acceptance_rate":accepted/count if count else None,"missing_rate":absent/count if count else None,"structural_checks_passed":audit["structural_checks_passed"],"structural_issues":audit["structural_issues"],"tool_trajectory_counts":dict(Counter(t.get("tool") for t in trajectory)),"tool_trajectory_costs":{tool:sum(t.get("cost",0) or 0 for t in trajectory if t.get("tool")==tool) for tool in {t.get("tool") for t in trajectory}},"budget_used_total":sum(r.get("budget_used",0) or 0 for r in rows),"budget_remaining_total":sum(r.get("budget_remaining",0) or 0 for r in rows),"agent_tokens":{k:sum(h.get("usage",{}).get(k,0) or 0 for h in history) for k in ["prompt_token_count","candidates_token_count","total_token_count"]},"simulator_tokens":{k:sum(s.get("usage",{}).get(k,0) or 0 for s in sim) for k in ["prompt_tokens","completion_tokens","total_tokens"]},"simulator_calls":len(sim),"log_error_counts":{k:len(v) for k,v in log_checks.items()},"requirement_coverage":{"status":"pending evidence-based semantic annotation","value":None},"false_resolution":{"status":"pending evidence-based semantic annotation","value":None},"semantics_not_inferred_from_structure_or_task_score":True}
(RUN/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
(RUN/"RESULTS.md").write_text("# Native State 72-task run\n\n原始运行和结构指标如下。Requirement Coverage 与 False Resolution 尚待独立语义标注，未计算；不能用结构校验或 SQL 得分代替。\n\n```json\n"+json.dumps(summary,ensure_ascii=False,indent=2)+"\n```\n")
manifest={str(p.relative_to(RUN)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(RUN.rglob("*")) if p.is_file() and p.name not in ["manifest.json","run_completion.json","supervisor.log","summary.log"] and "__pycache__" not in p.parts}
(RUN/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False,indent=2))
