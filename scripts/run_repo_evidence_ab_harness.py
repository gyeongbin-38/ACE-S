#!/usr/bin/env python3
"""A/B harness for real-repository source-evidence certificates.

Ground-truth expected_file and expected_anchor remain harness-only. The adapter
receives repository/revision/prompt and must return a path plus worker-visible
evidence. Quality passes only when:
  1. selected path is exact,
  2. exposed evidence is authentic against the frozen checkout, and
  3. the hidden expected anchor is present in worker-visible evidence.

This prevents a controller-only hidden read from being scored as sufficient.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from compare_runtime_ab_suite import run_suite
from run_runtime_ab_harness import norm_path, patch_task_end, run_adapter
from validate_runtime_taskset import validate as validate_taskset


def cache_key(repository: str, sha: str) -> str:
    return repository.replace("/", "__") + "__" + sha[:16]


def repo_root(repository: str, sha: str) -> Path:
    root = Path(os.environ.get("ACE_S_REPO_CACHE", Path(tempfile.gettempdir()) / "ace-s-repo-cache"))
    return root / cache_key(repository, sha)


def sha_line(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def exposed_records(result: dict) -> list[dict]:
    evidence = result.get("worker_evidence")
    if not isinstance(evidence, dict):
        return []
    records = evidence.get("records")
    return records if isinstance(records, list) else []


def verify_worker_evidence(result: dict, task: dict) -> tuple[bool, bool, str | None]:
    selected = result.get("answer")
    if not isinstance(selected, str) or not selected:
        return False, False, "missing selected path"
    path = repo_root(task["repository"], task["commit_sha"]) / selected
    if not path.is_file():
        return False, False, "selected source file missing from frozen checkout"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    records = exposed_records(result)
    if not records:
        return False, False, "worker evidence has no source records"

    authentic = True
    visible_text = []
    for record in records:
        if not isinstance(record, dict):
            authentic = False; continue
        lineno = record.get("line")
        text = record.get("text")
        digest = record.get("line_sha256")
        if isinstance(lineno, bool) or not isinstance(lineno, int) or not (1 <= lineno <= len(lines)) or not isinstance(text, str):
            authentic = False; continue
        source = lines[lineno - 1]
        if source != text or digest != sha_line(source):
            authentic = False
        visible_text.append(text)

    anchor = str(task["expected_anchor"]).lower()
    anchor_visible = anchor in "\n".join(visible_text).lower()
    return authentic, anchor_visible, None if authentic else "worker evidence does not match frozen source"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("taskset", type=Path)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--timeout-s", type=float, default=900.0)
    ap.add_argument("--material-improvement-pct", type=float, default=1.0)
    ap.add_argument("--require-pass", action="store_true")
    args = ap.parse_args()

    taskset = json.loads(args.taskset.read_text(encoding="utf-8"))
    validate_taskset(taskset)
    for task in taskset["tasks"]:
        if not isinstance(task.get("expected_anchor"), str) or not task["expected_anchor"].strip():
            raise ValueError(f"{task['task_id']}: expected_anchor is required")

    adapter_cmd = shlex.split(args.adapter)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    pairs = []
    rows = []

    for task in taskset["tasks"]:
        public_task = {
            "schema_version": "0.1",
            "suite_id": taskset["suite_id"],
            "task_id": task["task_id"],
            "task_stratum": taskset.get("task_stratum"),
            "repository": task["repository"],
            "commit_sha": task["commit_sha"],
            "prompt": task["prompt"],
        }
        tdir = args.out_dir / task["task_id"]
        tdir.mkdir(parents=True, exist_ok=True)
        tpath = tdir / "task.json"
        tpath.write_text(json.dumps(public_task, indent=2), encoding="utf-8")
        paths = {}

        for condition in ("OFF", "ON"):
            trace = tdir / f"{condition.lower()}.jsonl"
            result_path = tdir / f"{condition.lower()}-result.json"
            run_adapter(adapter_cmd, task_path=tpath, condition=condition, trace_out=trace, result_out=result_path, timeout_s=args.timeout_s)
            result = json.loads(result_path.read_text(encoding="utf-8"))
            path_ok = isinstance(result.get("answer"), str) and norm_path(result["answer"]) == norm_path(task["expected_file"])
            authentic, anchor_visible, detail = verify_worker_evidence(result, task)
            passed = bool(path_ok and authentic and anchor_visible)
            patch_task_end(trace, passed=passed, quality_score=1.0 if passed else 0.0, failure_category=None if passed else "MISS_CONTEXT")
            paths[condition] = trace
            rows.append({
                "task_id": task["task_id"],
                "condition": condition,
                "answer": result.get("answer"),
                "expected_file": task["expected_file"],
                "path_ok": path_ok,
                "evidence_authentic": authentic,
                "hidden_anchor_visible": anchor_visible,
                "passed": passed,
                "detail": detail,
                "adapter_metrics": result.get("metrics", {}),
            })

        pairs.append({"off": str(paths["OFF"].relative_to(args.out_dir)), "on": str(paths["ON"].relative_to(args.out_dir))})

    manifest = {"suite_id": taskset["suite_id"] + "-results", "pairs": pairs}
    manifest_path = args.out_dir / "paired-results.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    summary = run_suite(manifest_path, 0.0, args.material_improvement_pct)
    all_authentic = all(r["evidence_authentic"] for r in rows)
    all_anchor_visible = all(r["hidden_anchor_visible"] for r in rows)
    all_pass = all(r["passed"] for r in rows)
    report = {
        "taskset": taskset["suite_id"],
        "rows": rows,
        "paired_summary": summary,
        "source_evidence_gate": {
            "all_arms_authentic": all_authentic,
            "all_arms_hidden_anchor_visible": all_anchor_visible,
            "all_arms_pass": all_pass,
        },
        "ground_truth_boundary": "expected_file and expected_anchor are withheld from adapter input; expected_anchor is checked only after adapter execution against worker-visible, source-authenticated records.",
        "claim_boundary": "Deterministic real-repository runtime mechanics. This measures path/evidence fidelity and context exposure, not LLM semantic reasoning quality."
    }
    (args.out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    gate = all_pass and summary["suite_quality_gate_passed"] and summary["suite_efficiency_gate_passed"]
    if args.require_pass and not gate:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
