#!/usr/bin/env bash
set -euo pipefail
cd /home/nimir/study/adb/BIRD-Interact/BIRD-Interact-ADK
export CONDA_PREFIX=/home/nimir/miniconda3/envs/bird-interact
export PATH="$CONDA_PREFIX/bin:$PATH"
export NO_PROXY=127.0.0.1,localhost
export no_proxy=127.0.0.1,localhost
ROOT="$PWD/results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107"
run_block() {
  condition="$1"
  repetition="$2"
  block="$ROOT/${condition}_r${repetition}"
  if [[ -e "$block/runner.log" || -e "$block/services.log" || -e "$block/eval_a_interact.json" ]]; then
    echo "Refusing to overwrite archived attempt: $block; use a new experiment directory." >&2
    exit 1
  fi
  mkdir -p "$block"
  if [[ "$condition" == baseline ]]; then
    unset AINTERACT_PROMPT_APPENDIX
  else
    export AINTERACT_PROMPT_APPENDIX="$ROOT/prompts/${condition}_appendix.txt"
  fi
  echo "START $condition repetition $repetition $(date -Is)"
  bash scripts/start_services.sh > "$block/services.log" 2>&1
  python - "$block" <<'CHECK'
import ast,hashlib,json,sys,urllib.request,os
from pathlib import Path
root=Path(os.environ.get('AINTERACT_PROMPT_APPENDIX','')).parent.parent if os.environ.get('AINTERACT_PROMPT_APPENDIX') else Path('results/agent-deepseek-v4.1-flash-1017/simulator-deepseek-v4.1-flash-1017/prompt_strategy_48_20261107')
for f,digest in json.loads((root/'source_hashes.json').read_text()).items():
 assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==digest,f
from system_agent.agent import AINTERACT_INSTRUCTION,build_agent
agent=build_agent('a-interact')
expected=AINTERACT_INSTRUCTION+('\n\n'+Path(os.environ['AINTERACT_PROMPT_APPENDIX']).read_text() if os.environ.get('AINTERACT_PROMPT_APPENDIX') else '')
assert agent.instruction==expected
condition=Path(sys.argv[1]).name.rsplit('_r',1)[0]
assert agent.instruction==(root/'prompts'/f'{condition}.txt').read_text()
health={str(port):json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/health')) for port in [6000,6001,6002]}
assert health['6000']['adk_available']
assert health['6000']['model']=='deepseek/deepseek-flash'
Path(sys.argv[1],'verification.json').write_text(json.dumps({'health':health,'instruction_sha256':hashlib.sha256(agent.instruction.encode()).hexdigest(),'baseline_constant_sha256':hashlib.sha256(AINTERACT_INSTRUCTION.encode()).hexdigest()},indent=2))
CHECK
  python -m orchestrator.runner --mode a-interact --concurrency 1 --data "$ROOT/tasks.jsonl" --output "$block/eval_a_interact.json" > "$block/runner.log" 2>&1
  python - "$block/eval_a_interact.json" <<'CHECK'
import json,sys
r=json.load(open(sys.argv[1]))
assert len(r['results'])==4
errors=[(x['task_id'],x['error']) for x in r['results'] if x.get('error')]
assert not errors,errors
print('COMPLETE',sys.argv[1],r['metrics'],flush=True)
CHECK
}
run_block baseline 1
run_block A 1
run_block B 1
run_block C 1
run_block B 2
run_block C 2
run_block baseline 2
run_block A 2
run_block C 3
run_block A 3
run_block baseline 3
run_block B 3
echo "ALL_48_COMPLETED $(date -Is)"
