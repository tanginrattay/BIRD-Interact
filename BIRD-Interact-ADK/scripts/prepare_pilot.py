"""Prepare a reproducible two-tasks-per-database Lite pilot and safe metadata."""

import hashlib
import json
import random
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from shared.config import settings
from user_simulator.bailian import is_qwen_simulator


def main():
    destination = Path("results/agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42")
    destination.mkdir(exist_ok=False)
    source = Path(settings.data_path)
    groups = defaultdict(list)
    excluded = {f"alien_{i}" for i in range(1, 6)}
    for task in map(json.loads, source.read_text().splitlines()):
        if task["instance_id"] not in excluded:
            groups[task["selected_database"]].append(task)
    rng = random.Random(42)
    selected = [task for db in sorted(groups) for task in rng.sample(groups[db], 2)]
    assert len(selected) == 36, "Expected 18 Lite databases"
    (destination / "tasks.jsonl").write_text(
        "".join(json.dumps(task, ensure_ascii=False) + "\n" for task in selected))
    paths = sorted(path for folder in ("system_agent", "user_simulator", "shared", "orchestrator", "db_environment")
                   for path in Path(folder).glob("*.py"))
    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": 42, "excluded": sorted(excluded), "concurrency": 1,
        "mode": "a-interact", "dataset": settings.dataset,
        "system_agent_model": settings.system_agent_model,
        "user_sim_model": settings.user_sim_model,
        "prompt_version": settings.prompt_version, "patience": settings.patience,
        "simulator_route": "two_stage",
        "simulator_enable_thinking": (settings.user_sim_enable_thinking
                                      if is_qwen_simulator(settings.user_sim_model) else None),
        "simulator_thinking_budget": (settings.user_sim_thinking_budget
                                      if is_qwen_simulator(settings.user_sim_model)
                                      and settings.user_sim_enable_thinking else None),
        "task_ids": [task["instance_id"] for task in selected],
        "difficulty_counts": dict(Counter(task.get("difficulty_tier", "unknown") for task in selected)),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "code_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], text=True),
    }
    (destination / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    with (destination / "code_changes.patch").open("w") as output:
        subprocess.run(["git", "diff", "--", *map(str, paths)], stdout=output, check=True)
    print(json.dumps({"directory": str(destination), "tasks": len(selected),
                      "system_model": settings.system_agent_model, "user_model": settings.user_sim_model,
                      "difficulty_counts": metadata["difficulty_counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
