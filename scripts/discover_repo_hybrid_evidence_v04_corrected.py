#!/usr/bin/env python3
"""Invariant-only corrected-ground-truth wrapper for v0.4 hybrid search.

The hybrid algorithm/config family is unchanged. Only the six-task development
label source is replaced by repo-evidence-dev-v0.3-corrected.json after the
Kubernetes fixture audit. The eight previously sealed v0.1 tasks remain the
same seen development data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import discover_repo_frontier_v02 as v02

CORRECTED = ROOT / "benchmarks/runtime-traces/pilots/repo-evidence-dev-v0.3-corrected.json"
SEALED_V01 = ROOT / "benchmarks/runtime-traces/sealed/repo-frontier-unseen-v0.1.json"


def corrected_load_tasks():
    out = []
    for path in (CORRECTED, SEALED_V01):
        out.extend(json.loads(path.read_text(encoding="utf-8"))["tasks"])
    return out


v02.load_tasks = corrected_load_tasks

import discover_repo_hybrid_evidence_v04 as hybrid  # noqa: E402

if __name__ == "__main__":
    hybrid.main()
