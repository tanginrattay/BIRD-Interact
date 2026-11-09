"""Run frozen main then frozen requirement-tracking; no production edits."""
import os,sys,json,time,subprocess,hashlib,signal,traceback
from pathlib import Path
from datetime import datetime,timezone
import httpx,psycopg2
from dotenv import dotenv_values
BASE=Path(sys.argv[1]);M=json.loads((BASE/'manifest.json').read_text());ROOT=Path(M['project_root']);PY=sys.executable
config={k:v for k,v in dotenv_values(ROOT/'.env').items() if v is not None}
ENV=os.environ.copy();ENV.update(config)
ainet=config['AINET_API_BASE'].rstrip('/')
if not ainet.endswith('/v1'):ainet+='/v1'
ENV.update(SYSTEM_AGENT_MODEL='openai/gpt-6.1-sol',USER_SIM_MODEL='deepseek/deepseek-flash',LITELLM_API_BASE=ainet,LITELLM_API_KEY=config['AINET_API_KEY'],OPENAI_API_BASE=ainet,OPENAI_API_KEY=config['AINET_API_KEY'],PROMPT_VERSION='v1',USER_SIM_PIPELINE='two_stage',USER_SIM_ENABLE_THINKING='false',PATIENCE='3',DATASET='lite',SYSTEM_AGENT_PORT='16000',USER_SIM_PORT='16001',DB_ENV_PORT='16002',LITELLM_LOCAL_MODEL_COST_MAP='True',NO_PROXY='127.0.0.1,localhost',no_proxy='127.0.0.1,localhost')
# Explicitly retain yesterday's official DeepSeek simulator transport.
assert ENV['DEEPSEEK_API_BASE'].rstrip('/')=='https://api.deepseek.com'
for k in list(ENV):
 if k.startswith('AINTERACT_PROMPT_'):ENV.pop(k)
M['agent_endpoint']=ainet;M['versions']={}
import importlib.metadata
for pkg in ['google-adk','google-genai','litellm','pydantic','httpx']:M['versions'][pkg]=importlib.metadata.version(pkg)
M['runtime_overrides']={k:ENV[k] for k in ['SYSTEM_AGENT_MODEL','USER_SIM_MODEL','LITELLM_API_BASE','PROMPT_VERSION','USER_SIM_PIPELINE','USER_SIM_ENABLE_THINKING','PATIENCE','SYSTEM_AGENT_PORT','USER_SIM_PORT','DB_ENV_PORT']}
(BASE/'manifest.json').write_text(json.dumps(M,indent=2))
def now():return datetime.now(timezone.utc).isoformat()
def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str)+'\n')
def dbnames():
 with psycopg2.connect(host=ENV.get('PG_HOST','127.0.0.1'),port=int(ENV.get('PG_PORT','5432')),user=ENV.get('PG_USER','root'),password=ENV.get('PG_PASSWORD','123123'),dbname='postgres') as conn:
  with conn.cursor() as cur:cur.execute('SELECT datname FROM pg_database ORDER BY datname');return [r[0] for r in cur.fetchall()]
def stop(p):
 if p and p.poll() is None:
  p.terminate()
  try:p.wait(timeout=20)
  except subprocess.TimeoutExpired:p.kill();p.wait()
def baseline_observer(run):
 text='''import os,sys,json
from pathlib import Path
sys.path.insert(0,os.environ['EVAL_PROJECT_ROOT'])
RUN=Path(os.environ['EVAL_RUN_DIRECTORY'])
from system_agent import server
original=server.runtime.run_turn
async def observed_turn(task_id,mode,message,**kwargs):
 result=None;error=None
 try:
  result=await original(task_id=task_id,mode=mode,message=message,**kwargs)
  return result
 except Exception as exc:
  error=type(exc).__name__+': '+str(exc)
  raise
 finally:
  ref=server.runtime._session_refs.get((mode,task_id))
  if ref:
   runner,_=await server.runtime._get_runner(mode)
   session=await runner.session_service.get_session(app_name=ref.app_name,user_id=ref.user_id,session_id=ref.session_id)
   (RUN/'sessions'/(task_id+'.json')).write_text(json.dumps({'task_id':task_id,'session_id':ref.session_id,'runtime_error':error,'session':session.model_dump(mode='json',exclude_none=True)},ensure_ascii=False,indent=2)+'\\n')
server.runtime.run_turn=observed_turn
if __name__=='__main__':
 import uvicorn
 uvicorn.run(server.app,host='127.0.0.1',port=16000,log_level='info')
'''
 (run/'observer_agent.py').write_text(text)
def summarize(plan):
 run=Path(plan['run']);data=json.loads((run/'eval_a_interact.json').read_text());rows=data['results'];expected=[json.loads(l)['instance_id'] for l in (run/'tasks.jsonl').read_text().splitlines() if l.strip()]
 usage={};events=0
 for p in (run/'sessions').glob('*.json'):
  for e in json.loads(p.read_text())['session'].get('events',[]):
   events+=1
   for k,v in (e.get('usage_metadata') or {}).items():
    if isinstance(v,(int,float)):usage[k]=usage.get(k,0)+v
 sim={};scalls=0
 if (run/'simulator_usage.jsonl').exists():
  for l in (run/'simulator_usage.jsonl').read_text().splitlines():
   scalls+=1
   for k,v in (json.loads(l).get('usage') or {}).items():
    if isinstance(v,(int,float)):sim[k]=sim.get(k,0)+v
 errors=[{'task_id':r['task_id'],'error':r['error']} for r in rows if r.get('error')]
 actual=[r['task_id'] for r in rows];checks={'72_results':len(rows)==72,'task_ids_and_order_match':actual==expected,'unique_ids':len(set(actual))==72,'72_sessions':len(list((run/'sessions').glob('*.json')))==72,'all_results_have_trajectories':all(bool(r.get('tool_trajectory')) for r in rows),'all_results_have_adk_events':all(bool(r.get('adk_events')) for r in rows),'no_task_errors':not errors,'source_unchanged':all(hashlib.sha256((Path(plan['source'])/p).read_bytes()).hexdigest()==h for p,h in plan['code_sha256'].items())}
 state={}
 if (run/'state_observations.jsonl').exists():
  sr=[json.loads(l) for l in (run/'state_observations.jsonl').read_text().splitlines()];responses=[r for r in sr if r['type']=='model_response'];state={'model_responses':len(responses),'responses_with_state_error':sum(bool(r.get('state_error')) for r in responses),'unchanged_response_checks':all(r.get('original_response_unchanged') for r in responses)}
 summary={'metrics':data['metrics'],'checks':checks,'task_errors':errors,'session_event_count':events,'agent_usage':usage,'simulator_calls':scalls,'simulator_usage':sim,'state_observations':state}
 save(run/'validation.json',summary)
 (run/'RESULTS.md').write_text('# '+plan['name']+'\n\nCommit: `'+plan['commit']+'`\n\n```json\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n```\n\nOnly model connectivity and benchmark outcomes are assessed; underlying provider model identity and monetary cost are unverified.\n')
 return summary
summary={'started_at_utc':now(),'status':'starting','runs':{}};save(BASE/'status.json',summary)
pg_started=False;initial=None
try:
 initial=subprocess.check_output(['docker','inspect','-f','{{.State.Status}}','bird_interact_postgresql'],text=True).strip();M['postgres_initial_status']=initial;save(BASE/'manifest.json',M)
 with httpx.Client(timeout=1,trust_env=False) as c:
  for port in [16000,16001,16002]:
   try:r=c.get(f'http://127.0.0.1:{port}/health')
   except httpx.HTTPError:continue
   raise RuntimeError(f'Port {port} already in use; refusing to interfere')
 if initial!='running':subprocess.run(['docker','start','bird_interact_postgresql'],check=True,capture_output=True);pg_started=True
 for _ in range(40):
  try:before=dbnames();break
  except psycopg2.OperationalError:time.sleep(1)
 else:raise RuntimeError('PostgreSQL not ready')
 save(BASE/'databases_before.json',before)
 for plan in M['runs']:
  run=Path(plan['run']);src=Path(plan['source']);procs=[];handles=[];runner=None
  summary.update(status='running',active_run=plan['name']);summary['runs'][plan['name']]={'started_at_utc':now(),'status':'running'};save(BASE/'status.json',summary)
  if plan['name']=='baseline_main':baseline_observer(run)
  env=ENV.copy();env.update(PYTHONPATH=str(src),EVAL_PROJECT_ROOT=str(src),EVAL_RUN_DIRECTORY=str(run))
  try:
   specs=[('agent',[PY,str(run/'observer_agent.py')]),('simulator',[PY,str(run/'observer_simulator.py')]),('db',[PY,'-m','uvicorn','db_environment.server:app','--host','127.0.0.1','--port','16002','--log-level','info'])]
   for name,cmd in specs:
    log=(run/(name+'_service.log')).open('w');handles.append(log);procs.append((name,subprocess.Popen(cmd,cwd=src,env=env,stdout=log,stderr=subprocess.STDOUT)))
   save(run/'service_pids.json',{name:p.pid for name,p in procs});health={}
   with httpx.Client(timeout=2,trust_env=False) as c:
    for _ in range(60):
     for port in [16000,16001,16002]:
      try:
       r=c.get(f'http://127.0.0.1:{port}/health')
       if r.status_code==200:health[str(port)]=r.json()
      except httpx.HTTPError:pass
     if len(health)==3:break
     for name,p in procs:
      if p.poll() is not None:raise RuntimeError(name+' exited during startup')
     time.sleep(1)
   assert len(health)==3 and health['16000'].get('adk_available'),health
   assert health['16000']['model']=='openai/gpt-6.1-sol'
   save(run/'service_health.json',health)
   cmd=[PY,'-m','orchestrator.runner','--mode','a-interact','--data',str(run/'tasks.jsonl'),'--limit','72','--concurrency','1','--output',str(run/'eval_a_interact.json')];save(run/'runner_command.json',cmd)
   log=(run/'runner.log').open('w');handles.append(log);runner=subprocess.Popen(cmd,cwd=src,env=env,stdout=log,stderr=subprocess.STDOUT);save(run/'runner_pid.json',{'pid':runner.pid});previous=-1
   while runner.poll() is None:
    for name,p in procs:
     if p.poll() is not None:raise RuntimeError(name+' service died')
    try:
     data=json.loads((run/'eval_a_interact.json').read_text());n=len(data['results'])
     if n!=previous:
      previous=n;summary['runs'][plan['name']].update(completed=n,metrics=data['metrics']);save(BASE/'status.json',summary);print(now(),plan['name'],n,json.dumps(data['metrics']),flush=True)
     if n>=3 and all(r.get('error') for r in data['results'][-3:]):raise RuntimeError('Three consecutive task errors; stopped to avoid invalid batch')
    except (FileNotFoundError,json.JSONDecodeError):pass
    time.sleep(2)
   if runner.returncode:raise RuntimeError(f'runner exit {runner.returncode}')
   report=summarize(plan)
   if not report['checks']['72_results']:raise RuntimeError('Incomplete task batch')
   summary['runs'][plan['name']].update(status='complete',completed_at_utc=now(),validation=report);save(BASE/'status.json',summary)
  finally:
   stop(runner)
   for name,p in procs:stop(p)
   for f in handles:f.close()
   save(run/'process_cleanup.json',{'all_owned_services_stopped':all(p.poll() is not None for _,p in procs),'at_utc':now()})
 summary.update(status='complete',completed_at_utc=now());summary.pop('active_run',None)
 # Concrete side-by-side report.
 lines=['# AINET gpt-6.1-sol: matched 72-task comparison','', '| Variant | P1 | P2 | Average reward | Task errors |','|---|---:|---:|---:|---:|']
 for name,r in summary['runs'].items():
  v=r['validation'];m=v['metrics'];lines.append(f"| {name} | {m['phase1_count']}/72 | {m['phase2_count']}/72 | {m['average_reward']:.6f} | {len(v['task_errors'])} |")
 lines+=['','Simulator unchanged from 2026-11-08 native run: official DeepSeek deepseek/deepseek-flash alias, v1 two_stage, thinking disabled, patience 3. Task bytes/order fixed; concurrency 1. Agent openai/gpt-6.1-sol through AINET, max_tokens 4096, temperature 0 inherited.','', 'Frozen committed main and state/requirement-tracking source trees; current workspace branch and uncommitted changes preserved.','', 'Full raw results, tool trajectories, ADK events, sessions, logs, source hashes, token counts and validation are retained in each variant directory. Provider identity and monetary billing are not independently verified. Requirement semantic coverage was not annotated.']
 (BASE/'COMPARISON.md').write_text('\n'.join(lines)+'\n')
except BaseException as exc:
 summary.update(status='failed',error=type(exc).__name__+': '+str(exc),failed_at_utc=now());traceback.print_exc()
finally:
 try:
  after=dbnames();cleanup={'database_names_restored':after==before,'database_names_after':after}
  if pg_started and cleanup['database_names_restored']:
   with psycopg2.connect(host=ENV.get('PG_HOST','127.0.0.1'),port=int(ENV.get('PG_PORT','5432')),user=ENV.get('PG_USER','root'),password=ENV.get('PG_PASSWORD','123123'),dbname='postgres') as conn:
    with conn.cursor() as cur:cur.execute("SELECT count(*) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND backend_type = 'client backend'");clients=cur.fetchone()[0]
   cleanup['other_client_connections']=clients
   if clients==0:cleanup['postgres_restored_to_stopped']=subprocess.run(['docker','stop','bird_interact_postgresql'],capture_output=True,timeout=40).returncode==0
  save(BASE/'database_cleanup.json',cleanup)
 except Exception as exc:summary['cleanup_error']=type(exc).__name__+': '+str(exc)
 save(BASE/'status.json',summary)
