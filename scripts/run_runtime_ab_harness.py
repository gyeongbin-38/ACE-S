#!/usr/bin/env python3
"""Run a frozen OFF/ON taskset through an external runtime adapter.

Ground truth is retained by this harness and is never written to the adapter's
task input. The adapter receives only task_id/repository/commit/prompt/stratum,
returns an answer plus a trace, and the harness overwrites final task quality
from external exact-path scoring before paired comparison.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import tempfile
from pathlib import Path

from compare_runtime_ab_suite import run_suite
from validate_runtime_taskset import validate as validate_taskset
from validate_runtime_trace import load_trace, validate as validate_trace


def norm_path(value: str) -> str:
    value = value.strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return value.strip("/")


def score_answer(answer: object, expected_file: str) -> tuple[bool, float]:
    if not isinstance(answer, str):
        return False, 0.0
    ok = norm_path(answer) == norm_path(expected_file)
    return ok, 1.0 if ok else 0.0


def patch_task_end(trace_path: Path, *, passed: bool, quality_score: float, failure_category: str | None) -> None:
    events = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    if not events or events[-1].get("event_type") != "task_end":
        raise ValueError(f"adapter trace {trace_path} must end with task_end")
    events[-1]["passed"] = passed
    events[-1]["quality_score"] = quality_score
    if failure_category:
        events[-1]["failure_category"] = failure_category
    else:
        events[-1].pop("failure_category", None)
    trace_path.write_text("\n".join(json.dumps(e, separators=(",", ":"), ensure_ascii=False) for e in events) + "\n", encoding="utf-8")
    validate_trace(load_trace(trace_path))


def run_adapter(command: list[str], *, task_path: Path, condition: str, trace_out: Path, result_out: Path, timeout_s: float) -> None:
    cmd = command + [
        "--task", str(task_path),
        "--condition", condition,
        "--trace-out", str(trace_out),
        "--result-out", str(result_out),
    ]
    completed = subprocess.run(cmd, check=False, timeout=timeout_s)
    if completed.returncode != 0:
        raise RuntimeError(f"adapter failed with exit code {completed.returncode}: {cmd!r}")
    if not trace_out.exists() or not result_out.exists():
        raise RuntimeError("adapter must create both --trace-out and --result-out")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("taskset", type=Path)
    parser.add_argument("--adapter", required=True, help="quoted adapter command, e.g. 'python adapters/codex.py'")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--timeout-s", type=float, default=600.0)
    parser.add_argument("--quality-tolerance", type=float, default=0.0)
    parser.add_argument("--material-improvement-pct", type=float, default=1.0)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    taskset_obj = json.loads(args.taskset.read_text(encoding="utf-8"))
    validate_taskset(taskset_obj)
    adapter_cmd = shlex.split(args.adapter)
    if not adapter_cmd:
        raise SystemExit("--adapter command is empty")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    pairs = []
    raw_results = []

    for task in taskset_obj["tasks"]:
        # Do not leak expected_file to the runtime adapter.
        public_task = {
            "schema_version": "0.1",
            "suite_id": taskset_obj["suite_id"],
            "task_id": task["task_id"],
            "task_stratum": taskset_obj.get("task_stratum"),
            "repository": task["repository"],
            "commit_sha": task["commit_sha"],
            "prompt": task["prompt"],
        }
        task_dir = args.out_dir / task["task_id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        task_input = task_dir / "task.json"
        task_input.write_text(json.dumps(public_task, indent=2), encoding="utf-8")

        pair_paths = {}
        for condition in ("OFF", "ON"):
            trace_out = task_dir / f"{condition.lower()}.jsonl"
            result_out = task_dir / f"{condition.lower()}-result.json"
            run_adapter(adapter_cmd, task_path=task_input, condition=condition, trace_out=trace_out, result_out=result_out, timeout_s=args.timeout_s)
            result = json.loads(result_out.read_text(encoding="utf-8"))
            passed, quality = score_answer(result.get("answer"), task["expected_file"])
            patch_task_end(trace_out, passed=passed, quality_score=quality, failure_category=None if passed else "MISS_CONTEXT")

            start = load_trace(trace_out)[0]
            if start.get("condition") != condition:
                raise ValueError(f"{task['task_id']} {condition}: trace condition mismatch")
            if start.get("task_id") != task["task_id"]:
                raise ValueError(f"{task['task_id']} {condition}: trace task_id mismatch")
            pair_paths[condition] = trace_out
            raw_results.append({
                "task_id": task["task_id"],
                "condition": condition,
                "answer": result.get("answer"),
                "expected_file": task["expected_file"],
                "passed": passed,
            })

        pairs.append({
            "off": str(pair_paths["OFF"].relative_to(args.out_dir)),
            "on": str(pair_paths["ON"].relative_to(args.out_dir)),
        })

    manifest = {"suite_id": taskset_obj["suite_id"] + "-results", "pairs": pairs}
    manifest_path = args.out_dir / "paired-results.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    summary = run_suite(manifest_path, args.quality_tolerance, args.material_improvement_pct)
    report = {
        "taskset": taskset_obj["suite_id"],
        "adapter_command": adapter_cmd,
        "raw_scored_results": raw_results,
        "paired_summary": summary,
        "ground_truth_boundary": "expected_file is withheld from adapter task inputs and applied only by the harness after adapter execution.",
    }
    report_path = args.out_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if args.require_pass and not summary["suite_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
