import os,sys,json
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
   (RUN/'sessions'/(task_id+'.json')).write_text(json.dumps({'task_id':task_id,'session_id':ref.session_id,'runtime_error':error,'session':session.model_dump(mode='json',exclude_none=True)},ensure_ascii=False,indent=2)+'\n')
server.runtime.run_turn=observed_turn
if __name__=='__main__':
 import uvicorn
 uvicorn.run(server.app,host='127.0.0.1',port=16000,log_level='info')
