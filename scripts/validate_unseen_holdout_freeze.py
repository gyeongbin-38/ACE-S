#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "benchmarks" / "FROZEN_CONTROLLER_V04.json"


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    data = json.loads(FREEZE.read_text(encoding="utf-8"))
    base = data["controller_commit"]
    frozen = set(data["policy_files_frozen"])

    changed = set(filter(None, git("diff", "--name-only", f"{base}..HEAD").splitlines()))
    violations = sorted(changed & frozen)
    if violations:
        print("FAILED: unseen holdout modified frozen controller files")
        for path in violations:
            print("-", path)
        raise SystemExit(1)

    print(f"OK: controller frozen at {base}; {len(changed)} evaluation-only files changed")


if __name__ == "__main__":
    main()
