"""Own only this run's processes; no global process killing or code changes."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
import httpx
import hashlib
import psycopg2
sys.path.insert(0, str(Path.cwd()))
from shared.config import settings
PROJECT = Path.cwd()
RUN = Path(__file__).resolve().parent
PYTHON = sys.executable
ENV = os.environ.copy()
ENV.update({"SYSTEM_AGENT_PORT":"16000", "USER_SIM_PORT":"16001", "DB_ENV_PORT":"16002",
            "SYSTEM_AGENT_MODEL":"deepseek/deepseek-flash", "USER_SIM_MODEL":"deepseek/deepseek-flash",
            "PROMPT_VERSION":"v1", "USER_SIM_PIPELINE":"two_stage", "USER_SIM_ENABLE_THINKING":"false",
            "PATIENCE":"3", "DATASET":"lite", "LITELLM_LOCAL_MODEL_COST_MAP":"True", "PYTHONPATH":str(PROJECT),
            "EVAL_PROJECT_ROOT":str(PROJECT), "EVAL_RUN_DIRECTORY":str(RUN),
            "NO_PROXY":"127.0.0.1,localhost", "no_proxy":"127.0.0.1,localhost"})
processes = []
logs = []
runner = None
outcome = {"started_at_utc":datetime.now(timezone.utc).isoformat()}
try:
    metadata = json.loads((RUN / "metadata.json").read_text())
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in metadata["code_sha256"].items()), "Source changed after snapshot"
    with psycopg2.connect(host=settings.pg_host,port=settings.pg_port,user=settings.pg_user,password=settings.pg_password,dbname="postgres") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT datname FROM pg_database ORDER BY datname")
            (RUN / "databases_before.json").write_text(json.dumps([r[0] for r in cur.fetchall()],indent=2))
    specs = [("agent", [PYTHON,str(RUN / "observer_agent.py")]),
             ("simulator", [PYTHON,str(RUN / "observer_simulator.py")]),
             ("db", [PYTHON,"-m","uvicorn","db_environment.server:app","--host","127.0.0.1","--port","16002","--log-level","info"])]
    for name,command in specs:
        f = (RUN / (name+"_service.log")).open("w");logs.append(f)
        p = subprocess.Popen(command, cwd=PROJECT, env=ENV, stdout=f, stderr=subprocess.STDOUT)
        processes.append((name,p))
    (RUN / "service_pids.json").write_text(json.dumps({name:p.pid for name,p in processes},indent=2))
    health = {}
    with httpx.Client(timeout=2,trust_env=False) as client:
        for attempt in range(45):
            for port in [16000,16001,16002]:
                try:
                    r=client.get(f"http://127.0.0.1:{port}/health")
                    if r.status_code==200:health[str(port)]=r.json()
                except httpx.HTTPError:pass
            if len(health)==3:break
            for name,p in processes:
                if p.poll() is not None:raise RuntimeError(f"{name} service exited: {p.returncode}")
            time.sleep(1)
    if len(health)!=3:raise RuntimeError("Service health checks did not complete")
    if not health['16000'].get('adk_available'):raise RuntimeError("ADK runtime unavailable")
    (RUN / "service_health.json").write_text(json.dumps(health,ensure_ascii=False,indent=2))
    command=[PYTHON,"-m","orchestrator.runner","--mode","a-interact","--data",str(RUN/"tasks.jsonl"),"--limit","72","--concurrency","1","--output",str(RUN/"eval_a_interact.json")]
    (RUN / "runner_command.json").write_text(json.dumps(command,indent=2))
    f=(RUN / "runner.log").open("w");logs.append(f)
    runner=subprocess.Popen(command,cwd=PROJECT,env=ENV,stdout=f,stderr=subprocess.STDOUT)
    print(json.dumps({"status":"running","runner_pid":runner.pid,"run_directory":str(RUN)},ensure_ascii=False),flush=True)
    previous=-1
    while runner.poll() is None:
        try:
            data=json.loads((RUN/"eval_a_interact.json").read_text());completed=len(data['results'])
            if completed!=previous:
                print(json.dumps({"completed":completed,"tasks":[{"id":r['task_id'],"state_error":r.get('requirement_state_error'),"error":r.get('error')} for r in data['results']]},ensure_ascii=False),flush=True);previous=completed
        except (FileNotFoundError,json.JSONDecodeError):pass
        time.sleep(1)
    outcome["runner_exit_code"]=runner.returncode
    if runner.returncode:raise RuntimeError(f"runner failed: {runner.returncode}")
    outcome["completed_at_utc"]=datetime.now(timezone.utc).isoformat()
    print(json.dumps(outcome),flush=True)
except Exception as exc:
    outcome['error']=type(exc).__name__+': '+str(exc)
    print(json.dumps(outcome),flush=True)
    raise
finally:
    if runner is not None and runner.poll() is None:
        runner.terminate()
        try:runner.wait(timeout=15)
        except subprocess.TimeoutExpired:runner.kill();runner.wait()
    for name,p in processes:
        if p.poll() is None:
            p.terminate()
            try:p.wait(timeout=15)
            except subprocess.TimeoutExpired:p.kill();p.wait()
    outcome['services_stopped']={name:p.poll() is not None for name,p in processes}
    (RUN / 'run_completion.json').write_text(json.dumps(outcome,ensure_ascii=False,indent=2)+'\n')
    for f in logs:f.close()
    try:
        cleanup={}
        with psycopg2.connect(host=settings.pg_host,port=settings.pg_port,user=settings.pg_user,password=settings.pg_password,dbname="postgres") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT datname FROM pg_database ORDER BY datname")
                after=[r[0] for r in cur.fetchall()]
                cur.execute("SELECT count(*) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND backend_type = 'client backend'")
                clients=cur.fetchone()[0]
        cleanup={"database_names_restored":after==json.loads((RUN / "databases_before.json").read_text()),"database_names_after":after,"other_client_connections":clients}
        if metadata["pg_initial_status"]=="exited" and not clients:
            stopped=subprocess.run(["docker","stop","bird_interact_postgresql"],capture_output=True,text=True,timeout=30)
            cleanup["postgres_restored_to_stopped"]=stopped.returncode==0
        (RUN / "database_cleanup.json").write_text(json.dumps(cleanup,indent=2))
    except Exception as exc:
        (RUN / "cleanup_error.txt").write_text(type(exc).__name__+": "+str(exc))
    if outcome.get("runner_exit_code")==0:
        with (RUN / "analysis.log").open("w") as f:
            checked=subprocess.run([PYTHON,str(RUN / "analyze_run.py")],cwd=PROJECT,env=ENV,stdout=f,stderr=subprocess.STDOUT)
        outcome["analysis_exit_code"]=checked.returncode
        with (RUN / "summary.log").open("w") as f:
            summarized=subprocess.run([PYTHON,str(RUN / "summarize_run.py")],cwd=PROJECT,env=ENV,stdout=f,stderr=subprocess.STDOUT)
        outcome["summary_exit_code"]=summarized.returncode
    (RUN / "run_completion.json").write_text(json.dumps(outcome,ensure_ascii=False,indent=2)+"\n")
