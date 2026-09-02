#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "benchmarks" / "FROZEN_MICROKERNEL_V04.json"


def main() -> None:
    doc = json.loads(FREEZE.read_text(encoding="utf-8"))
    base = doc["policy_commit"]
    prefix = doc["protected_prefix"]
    proc = subprocess.run(
        ["git", "diff", "--name-only", base, "HEAD", "--", prefix],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    changed = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if changed:
        raise SystemExit(
            "microkernel freeze violated; protected policy files changed after holdout source inspection:\n"
            + "\n".join(f"- {p}" for p in changed)
        )
    all_proc = subprocess.run(
        ["git", "diff", "--name-only", base, "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    eval_changes = [line.strip() for line in all_proc.stdout.splitlines() if line.strip()]
    print(f"OK: microkernel policy frozen at {base}; {len(eval_changes)} evaluation-only files changed")


if __name__ == "__main__":
    main()
