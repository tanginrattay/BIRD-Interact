"""One-time, byte-preserving historical result migration (no model/API calls)."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOVES = {
    "results/eval_a_interact.json": "results/agent-unknown/simulator-unknown/initial5_repaired/eval_initial5.json",
    "results/eval_a_interact_kimi3_5.json": "results/agent-kimi-k3/simulator-unknown/early5/eval_kimi3_5.json",
    "results/eval_a_interact_kimi26_10.json": "results/agent-kimi-k2.6/simulator-unknown/early10/eval_kimi26_10.json",
    "results/usersim_calibration_v2.json": "results/simulator-only/kimi-k2.6/calibration/usersim_calibration_v2.json",
    "results/usersim_calibration_v3.json": "results/simulator-only/kimi-k2.6/calibration/usersim_calibration_v3.json",
    "results/pilot36_seed42": "results/agent-kimi-k3/simulator-kimi-k2.6/pilot36_seed42",
}


def main():
    records = []
    for old, new in MOVES.items():
        source, target = ROOT / old, ROOT / new
        if not source.exists() or target.exists():
            raise RuntimeError(f"Migration requires source present and target absent: {old} -> {new}")
        files = sorted(source.rglob("*")) if source.is_dir() else [source]
        for path in files:
            if path.is_file():
                suffix = str(path.relative_to(source)) if source.is_dir() else ""
                records.append({
                    "original_path": str(path.relative_to(ROOT)),
                    "archived_path": str(Path(new) / suffix) if suffix else new,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "bytes": path.stat().st_size,
                })
    for old, new in MOVES.items():
        target = ROOT / new
        target.parent.mkdir(parents=True, exist_ok=True)
        (ROOT / old).rename(target)
    for entry in records:
        assert hashlib.sha256((ROOT / entry["archived_path"]).read_bytes()).hexdigest() == entry["sha256"]
    manifest = ROOT / "results/archive_manifest_2026-10-04.json"
    with manifest.open("x") as f:
        json.dump({"note": "Original bytes preserved; historical source manifests retain original paths. Model attribution is documented in results/README.md.", "files": records}, f, indent=2)
    # Mechanical path updates only in live documentation and helper scripts.
    # Archived results (including their Markdown source copies) stay byte-identical.
    for directory in (ROOT / "agent", ROOT / "scripts"):
        for path in directory.rglob("*"):
            if path.suffix not in {".md", ".py"} or path.resolve() == Path(__file__).resolve():
                continue
            original = path.read_text()
            updated = original
            for old, new in MOVES.items():
                updated = updated.replace(old, new)
            if updated != original:
                path.write_text(updated)
    print(f"Archived and SHA-256 verified {len(records)} files; manifest: {manifest}")


if __name__ == "__main__":
    main()
