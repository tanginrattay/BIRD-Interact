"""Record transport usage only; preserve simulator prompts, calls and replies."""
import json
import os
import sys
import threading
import time
from pathlib import Path
sys.path.insert(0, os.environ["EVAL_PROJECT_ROOT"])
import litellm
RUN=Path(os.environ["EVAL_RUN_DIRECTORY"])
original=litellm.completion
lock=threading.Lock()
def observed_completion(*args, **kwargs):
    start=time.time()
    try:
        response=original(*args, **kwargs)
    except Exception as exc:
        row={"model":kwargs.get("model"),"max_tokens":kwargs.get("max_tokens"),"started_unix":start,"elapsed_seconds":time.time()-start,"error_type":type(exc).__name__}
        with lock, (RUN / "simulator_usage.jsonl").open("a") as f:f.write(json.dumps(row)+"\n")
        raise
    usage=getattr(response,"usage",None)
    row={"model":kwargs.get("model"),"max_tokens":kwargs.get("max_tokens"),"started_unix":start,"elapsed_seconds":time.time()-start,"usage":usage.model_dump() if usage is not None else {}}
    with lock, (RUN / "simulator_usage.jsonl").open("a") as f:f.write(json.dumps(row)+"\n")
    return response
litellm.completion=observed_completion
from user_simulator import server
if __name__=="__main__":
    import uvicorn
    uvicorn.run(server.app,host="127.0.0.1",port=16001,log_level="info")
