#!/usr/bin/env python3
"""Re-score v0.2 and v0.3 against corrected development ground truth.

No policy code or candidate family is changed. The only scoring correction is
Kubernetes current-context: config.go/writeCurrentContext replaces the invalid
loader.go/originating-files label documented by the audit artifact.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import discover_repo_frontier_v02 as v02

CORRECTED = ROOT / "benchmarks/runtime-traces/pilots/repo-evidence-dev-v0.3-corrected.json"
SEALED_V01 = ROOT / "benchmarks/runtime-traces/sealed/repo-frontier-unseen-v0.1.json"


def corrected_load_tasks():
    tasks = []
    for path in (CORRECTED, SEALED_V01):
        tasks.extend(json.loads(path.read_text(encoding="utf-8"))["tasks"])
    return tasks


v02.load_tasks = corrected_load_tasks

import discover_repo_behavior_windows_v03 as v03w  # noqa: E402


def capture(fn):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn()
    return json.loads(buf.getvalue())


def main():
    r2 = capture(v02.main)
    r3 = capture(v03w.main)
    print(json.dumps({
        "audit": "corrected-ground-truth-v02-v03",
        "tasks": 14,
        "ground_truth_correction": "k8s-current-context-evidence-001 -> config.go/writeCurrentContext",
        "v02": {
            "eligible_100_100": r2["eligible_100_100"],
            "selected": r2["selected"],
            "selected_task_rows": r2["selected_task_rows"],
        },
        "v03": {
            "eligible_100_anchor": r3["eligible_100_anchor"],
            "selected": r3["selected"],
            "selected_task_rows": r3["selected_task_rows"],
        },
        "selection_rule": "Prefer the simplest lower-byte policy that meets false-direct=0, frontier=100%, anchor=100%. Any chosen policy remains development-only until frozen and tested on a fresh unseen suite.",
        "claim_boundary": "Corrected development re-scoring only; no unseen claim."
    }, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
