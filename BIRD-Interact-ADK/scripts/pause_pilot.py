"""Stop this pilot and preserve saved results plus log-derived completion markers."""
import json
import os
import re
import signal
import time
from pathlib import Path

root = Path.cwd()
directory = root / "results/agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42"
targets = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        args = (proc / 'cmdline').read_bytes().decode().split('\0')
        if (proc / 'cwd').resolve() != root or not Path(args[0]).name.startswith('python'):
            continue
        runner = 'orchestrator.runner' in args and any(
            arg.startswith('results/agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42/baseline_') and arg.endswith('.json')
            for arg in args)
        service = 'uvicorn' in args and any(x in args for x in (
            'system_agent.server:app', 'user_simulator.server:app', 'db_environment.server:app'))
        if runner or service:
            targets.append(int(proc.name))
    except (OSError, IndexError, UnicodeError):
        continue
for pid in targets:
    os.kill(pid, signal.SIGSTOP)

log = '\n'.join(path.read_text() for path in sorted(directory.glob('baseline_*.log')))
completed = []
for task, reward, budget, seconds in re.findall(
        r'Task (\S+) done\. Reward: ([\d.]+), Budget used: ([\d.]+), Time: ([\d.]+)s', log):
    completed.append({'task_id': task, 'total_reward': float(reward),
                      'budget_used': float(budget), 'elapsed_seconds': float(seconds),
                      'source': 'log_only; full trajectory may not have been saved'})
saved_files = {path.name: json.loads(path.read_text())
               for path in sorted(directory.glob('baseline_*.json'))}
saved = {'results': [row for data in saved_files.values() for row in data['results']]} if saved_files else None
done = {row['task_id'] for row in completed}
if saved:
    done.update(row['task_id'] for row in saved['results'])
tasks = list(map(json.loads, (directory / 'tasks.jsonl').read_text().splitlines()))
remaining = [task for task in tasks if task['instance_id'] not in done]
(directory / 'remaining_tasks.jsonl').write_text(''.join(json.dumps(t) + '\n' for t in remaining))
(directory / 'pause_checkpoint.json').write_text(json.dumps({
    'completed_from_log': completed, 'saved_results': saved, 'saved_files': list(saved_files),
    'remaining_ids': [t['instance_id'] for t in remaining],
    'note': 'Incomplete task restarts from beginning. Log-only records do not contain trajectories.'
}, indent=2))
for pid in targets:
    try:
        os.kill(pid, signal.SIGTERM)
        os.kill(pid, signal.SIGCONT)
    except ProcessLookupError:
        pass
time.sleep(3)
for pid in targets:
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
print(json.dumps({'stopped_pids': targets, 'completed': sorted(done),
                  'remaining': len(remaining), 'full_results_saved': saved is not None}))
