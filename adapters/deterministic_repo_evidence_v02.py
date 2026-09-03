#!/usr/bin/env python3
"""Deterministic real-repository source-evidence adapter.

Development purpose: strengthen the existing path-localization runtime into an
actual source-evidence exposure test. Both arms use the same frozen v0.4.1
localizer and inspect the same selected source file.

OFF exposes a bounded raw search + source window to the worker.
ON keeps raw search/source state controller-side and exposes only an exact typed
certificate containing source lines and provenance.

This is NOT an LLM quality benchmark. Ground-truth path/anchor are withheld by
the harness and never available here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))

import deterministic_repo_localization_v041 as _freeze_ranker  # noqa: F401,E402
import deterministic_repo_localization as base  # noqa: E402
from runtime_trace_writer import TraceWriter, metric  # noqa: E402

MAX_CERT_RECORDS = 6
WINDOW_RADIUS = 10


def line_sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def score_hit(text: str, terms: list[tuple[str, float, bool]]) -> float:
    low = text.lower()
    score = 0.0
    for term, weight, exactish in terms:
        if term.lower() in low:
            score += weight * (2.0 if exactish else 1.0)
    if any(x in low for x in ("def ", "class ", "func ", "function ", " duplicate ", "originat")):
        score += 4.0
    return score


def source_records(repo: Path, selected: str, ranked_row: dict | None, terms: list[tuple[str, float, bool]]) -> tuple[list[dict], list[str], bytes]:
    if not selected:
        return [], [], b""
    path = repo / selected
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()

    hits: list[tuple[int, str]] = []
    if ranked_row:
        for raw_lineno, raw_text in ranked_row.get("hit_lines", []):
            try:
                lineno = int(raw_lineno)
            except (TypeError, ValueError):
                continue
            if 1 <= lineno <= len(lines):
                hits.append((lineno, lines[lineno - 1]))

    if not hits:
        for i, line in enumerate(lines, 1):
            low = line.lower()
            if any(term.lower() in low for term, _, _ in terms):
                hits.append((i, line))

    # Highest-value exact source lines first; deterministic tie-break by line number.
    dedup = {(n, t) for n, t in hits}
    ordered = sorted(dedup, key=lambda x: (-score_hit(x[1], terms), x[0], x[1]))
    chosen = ordered[:MAX_CERT_RECORDS]
    records = [{"line": n, "text": t, "line_sha256": line_sha(t)} for n, t in chosen]

    window_indices: set[int] = set()
    for n, _ in chosen[:3]:
        lo = max(1, n - WINDOW_RADIUS)
        hi = min(len(lines), n + WINDOW_RADIUS)
        window_indices.update(range(lo, hi + 1))
    raw_window = [f"{i}:{lines[i-1]}" for i in sorted(window_indices)]
    return records, raw_window, data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", type=Path, required=True)
    ap.add_argument("--condition", choices=["OFF", "ON"], required=True)
    ap.add_argument("--trace-out", type=Path, required=True)
    ap.add_argument("--result-out", type=Path, required=True)
    args = ap.parse_args()

    task = json.loads(args.task.read_text(encoding="utf-8"))
    repo = base.ensure_repo(task["repository"], task["commit_sha"])
    writer = TraceWriter(
        args.trace_out,
        task_id=task["task_id"],
        condition=args.condition,
        surface="local-git-real-source-evidence",
        model="deterministic-localizer-v041+source-certificate-v02",
        task_stratum=task.get("task_stratum") or "repository-source-evidence",
    )
    started = time.perf_counter()

    terms = base.query_terms(task["prompt"])
    writer.emit("context_action_selected", action_id="grep-rank-source", action_kind="SEARCH", query_terms=[t for t, _, _ in terms])
    writer.tool_call_start("call-grep", "git-grep", action_id="grep-rank-source")
    raw, grep_ms = base.grep_repo(repo, terms)
    writer.tool_call_end("call-grep", True, latency_ms=grep_ms)
    ranked = base.rank_files(base.parse_hits(raw, terms), terms)
    selected = ranked[0]["path"] if ranked else ""
    selected_row = ranked[0] if ranked else None

    writer.tool_call_start("call-source-read", "local-source-read", action_id="grep-rank-source")
    read_start = time.perf_counter()
    records, raw_window, source_bytes = source_records(repo, selected, selected_row, terms)
    read_ms = (time.perf_counter() - read_start) * 1000.0
    writer.tool_call_end("call-source-read", True, latency_ms=read_ms)

    search_payload = base.compact_search_payload(ranked)
    raw_window_payload = "\n".join(raw_window).encode("utf-8")
    raw_worker_payload = search_payload + b"\n" + raw_window_payload
    raw_controller_bytes = len(raw.encode("utf-8", errors="replace")) + len(source_bytes)
    provenance = [f"git:{task['repository']}@{task['commit_sha']}:{selected}"] if selected else [f"git:{task['repository']}@{task['commit_sha']}"]

    exact_value = {
        "repository": task["repository"],
        "revision": task["commit_sha"],
        "selected_path": selected,
        "source_file_sha256": file_sha(source_bytes),
        "records": records,
    }

    if args.condition == "OFF":
        evidence_id = "ev-raw-source-proof"
        writer.evidence_observed(
            evidence_id,
            evidence_kind="semantic",
            certificate_capable=False,
            provenance_refs=provenance,
            metrics={"controller_only_bytes": metric(0)},
        )
        writer.expose_full(evidence_id, bytes_=len(raw_worker_payload), tokens=None)
        worker_evidence = {"representation": "raw", "path": selected, "records": records, "raw_window": raw_window}
        certificate = None
    else:
        writer.emit(
            "controller_context_recorded",
            context_id="raw-search-and-source",
            representation="structured-source-state",
            metrics={"controller_only_bytes": metric(raw_controller_bytes)},
        )
        evidence_id = "ev-certified-source-proof"
        digest = writer.evidence_observed(
            evidence_id,
            evidence_kind="structured",
            certificate_capable=True,
            provenance_refs=provenance,
            exact_value=exact_value,
            metrics={"controller_only_bytes": metric(raw_controller_bytes)},
        )
        certificate = {
            "schema": "ace-s.repo-source-evidence.v0.2",
            "repository": task["repository"],
            "revision": task["commit_sha"],
            "path": selected,
            "source_file_sha256": exact_value["source_file_sha256"],
            "records": records,
            "provenance": provenance,
        }
        cert_payload = json.dumps(certificate, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        writer.certificate_emitted(
            "cert-source-proof",
            evidence_id,
            schema_ref="ace-s.repo-source-evidence.v0.2",
            exact_value_sha256=digest or "sha256:0",
            provenance_refs=provenance,
            metrics={"certificate_bytes": metric(len(cert_payload))},
        )
        writer.expose_certificate("cert-source-proof", bytes_=len(cert_payload), tokens=None)
        worker_evidence = {"representation": "certificate", **certificate}

    elapsed = (time.perf_counter() - started) * 1000.0
    writer.end(passed=False, quality_score=None, wall_clock_ms=elapsed)
    args.result_out.parent.mkdir(parents=True, exist_ok=True)
    args.result_out.write_text(
        json.dumps(
            {
                "answer": selected,
                "worker_evidence": worker_evidence,
                "certificate": certificate,
                "metrics": {
                    "raw_search_bytes": len(raw.encode("utf-8", errors="replace")),
                    "source_file_bytes": len(source_bytes),
                    "off_raw_worker_payload_bytes": len(raw_worker_payload),
                    "on_certificate_bytes": 0 if certificate is None else len(json.dumps(certificate, ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
