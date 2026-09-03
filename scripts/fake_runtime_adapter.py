#!/usr/bin/env python3
"""CI-only fake adapter for runtime harness plumbing. Never use for performance claims."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_trace_writer import TraceWriter, metric


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--condition", choices=["OFF", "ON"], required=True)
    parser.add_argument("--trace-out", type=Path, required=True)
    parser.add_argument("--result-out", type=Path, required=True)
    args = parser.parse_args()

    task = json.loads(args.task.read_text(encoding="utf-8"))
    if "expected_file" in task:
        raise SystemExit("ground truth leaked to adapter input")

    w = TraceWriter(
        args.trace_out,
        task["task_id"],
        args.condition,
        "ci-fake-adapter",
        "fixture-model",
        task.get("task_stratum") or "repository-local",
    )
    w.tool_call_start("c1", "fixture.lookup")
    w.tool_call_end("c1", True, 10.0)
    digest = w.evidence_observed(
        "ev1",
        evidence_kind="structured",
        certificate_capable=True,
        provenance_refs=["fixture://lookup/1"],
        exact_value={"path": "src/fixture.py"},
        metrics={"controller_only_bytes": metric(1000 if args.condition == "ON" else 0)},
    )
    if args.condition == "ON":
        assert digest is not None
        w.certificate_emitted(
            "cert1", "ev1",
            schema_ref="schema://fixture/path-v1",
            exact_value_sha256=digest,
            provenance_refs=["fixture://lookup/1"],
            metrics={"certificate_bytes": metric(100)},
        )
        w.expose_certificate("cert1", bytes_=400, tokens=100)
        wall = 90.0
    else:
        w.expose_full("ev1", bytes_=1000, tokens=250)
        wall = 100.0
    # Placeholder quality is intentionally overwritten by the external harness scorer.
    w.end(passed=False, quality_score=0.0, wall_clock_ms=wall)
    args.result_out.parent.mkdir(parents=True, exist_ok=True)
    args.result_out.write_text(json.dumps({"answer": "src/fixture.py"}), encoding="utf-8")


if __name__ == "__main__":
    main()
