#!/usr/bin/env python3
"""Score blind external semantic-judge responses for repo-frontier unseen v0.1.

Input JSONL rows must contain task_id plus the judge JSON fields. The scorer is
the only component that joins blind candidate IDs to hidden expected paths.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKSET = ROOT / "benchmarks/runtime-traces/sealed/repo-frontier-unseen-v0.1.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("responses", type=Path)
    ap.add_argument("packets", type=Path)
    args = ap.parse_args()

    expected = {t["task_id"]: t["expected_file"] for t in json.loads(TASKSET.read_text())["tasks"]}
    packets = {p["task_id"]: p for p in json.loads(args.packets.read_text())["packets"]}
    responses = {}
    for line in args.responses.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        responses[row["task_id"]] = row

    rows = []
    judged = correct = abstain = invalid = 0
    for task_id, packet in packets.items():
        by_id = {c["candidate_id"]: c["path"] for c in packet["candidates"]}
        reachable = expected[task_id] in set(by_id.values())
        r = responses.get(task_id)
        if r is None:
            rows.append({"task_id": task_id, "reachable": reachable, "status": "MISSING_RESPONSE"})
            continue
        decision = r.get("decision")
        cid = r.get("candidate_id")
        if decision == "ABSTAIN":
            abstain += 1; judged += 1
            status = "ABSTAIN"
            selected_path = None
        elif decision == "SELECT" and cid in by_id:
            judged += 1
            selected_path = by_id[cid]
            ok = selected_path == expected[task_id]
            correct += int(ok)
            status = "CORRECT" if ok else "WRONG"
        else:
            invalid += 1
            selected_path = None
            status = "INVALID"
        rows.append({
            "task_id": task_id,
            "reachable": reachable,
            "status": status,
            "selected_path": selected_path,
            "expected_path": expected[task_id],
            "confidence": r.get("confidence"),
            "evidence_refs": r.get("evidence_refs", []),
        })

    reachable_ids = {r["task_id"] for r in rows if r.get("reachable")}
    conditional_rows = [r for r in rows if r.get("reachable") and r["status"] in {"CORRECT", "WRONG", "ABSTAIN"}]
    conditional_correct = sum(r["status"] == "CORRECT" for r in conditional_rows)
    total_tasks = len(expected)
    end_to_end_correct = sum(r.get("status") == "CORRECT" for r in rows)
    result = {
        "experiment": "luna-blind-semantic-judge-score-v0.1",
        "total_tasks": total_tasks,
        "retrieval_reachable_tasks": len(reachable_ids),
        "retrieval_frontier_recall_pct": round(100 * len(reachable_ids) / total_tasks, 3),
        "judge_responses_scored": judged,
        "judge_abstain_count": abstain,
        "invalid_response_count": invalid,
        "conditional_judge_accuracy_pct": round(100 * conditional_correct / len(conditional_rows), 3) if conditional_rows else None,
        "end_to_end_accuracy_pct": round(100 * end_to_end_correct / total_tasks, 3),
        "rows": rows,
        "claim_boundary": "Conditional judge accuracy is meaningful only for tasks whose hidden expected file was present in the frozen frontier. Retrieval misses remain end-to-end failures regardless of judge output."
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
