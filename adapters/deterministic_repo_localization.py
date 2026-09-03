#!/usr/bin/env python3
"""Deterministic real-repository localization adapter for the ACE-S runtime A/B harness.

This adapter is deliberately NOT an LLM benchmark. It validates the real-runtime
measurement boundary on actual Git repositories at frozen commits:

OFF: the localization ranker directly consumes raw semantic grep output.
ON:  the controller consumes that same raw output, then the worker receives only
     an exact typed selected-path certificate with provenance.

Repository checkout is fixture preparation and is intentionally completed before
trace timing starts. Ground truth is never available to this adapter.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from runtime_trace_writer import TraceWriter, metric  # noqa: E402

STOPWORDS = {
    "locate", "production", "source", "file", "responsible", "return", "most",
    "relevant", "path", "implementing", "implementation", "behavior", "used",
    "when", "where", "that", "this", "with", "from", "into", "including",
    "containing", "contains", "involved", "handling", "changes", "configuration",
    "determines", "may", "different", "values", "data", "missing", "none",
}
NONPROD_PARTS = {
    "test", "tests", "testing", "docs", "doc", "examples", "example", "vendor",
    "third_party", "node_modules", "benchmarks", "benchmark", "fixtures", "fixture",
    "generated", "dist", "build", "changelog", ".github",
}
CODE_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".kt", ".kts", ".rs",
    ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift", ".scala",
    ".sh", ".bash", ".zsh", ".toml", ".yaml", ".yml", ".json", ".xml",
}


def run(cmd: list[str], *, cwd: Path | None = None, timeout: float = 300.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, timeout=timeout,
    )


def cache_key(repository: str, sha: str) -> str:
    return repository.replace("/", "__") + "__" + sha[:16]


def ensure_repo(repository: str, sha: str) -> Path:
    root = Path(os.environ.get("ACE_S_REPO_CACHE", Path(tempfile.gettempdir()) / "ace-s-repo-cache"))
    root.mkdir(parents=True, exist_ok=True)
    target = root / cache_key(repository, sha)
    marker = target / ".ace-s-ready"
    if marker.exists():
        return target
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    steps = [
        ["git", "init", "-q"],
        ["git", "remote", "add", "origin", f"https://github.com/{repository}.git"],
        ["git", "fetch", "-q", "--depth=1", "origin", sha],
        ["git", "checkout", "-q", "--detach", "FETCH_HEAD"],
    ]
    for cmd in steps:
        cp = run(cmd, cwd=target, timeout=600.0)
        if cp.returncode != 0:
            raise RuntimeError(f"repo preparation failed: {cmd!r}: {cp.stderr[-1000:]}")
    marker.write_text(sha + "\n", encoding="utf-8")
    return target


def split_camel(value: str) -> list[str]:
    return [x for x in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", value) if len(x) >= 3]


def variants(token: str) -> set[str]:
    out = {token}
    if "-" in token or "_" in token:
        parts = [p for p in re.split(r"[-_]", token) if p]
        if parts:
            out.add("_".join(parts))
            out.add("-".join(parts))
            out.add("".join(parts))
            out.add(parts[0].lower() + "".join(p[:1].upper() + p[1:] for p in parts[1:]))
            out.add("".join(p[:1].upper() + p[1:] for p in parts))
    elif any(c.isupper() for c in token[1:]):
        parts = split_camel(token)
        if len(parts) > 1:
            out.add("_".join(p.lower() for p in parts))
            out.add("-".join(p.lower() for p in parts))
    return {x for x in out if len(x) >= 4}


def query_terms(prompt: str) -> list[tuple[str, float, bool]]:
    raw = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", prompt)
    merged: dict[str, tuple[float, bool]] = {}
    for tok in raw:
        low = tok.lower()
        if low in STOPWORDS:
            continue
        code_like = "_" in tok or "-" in tok or any(c.isupper() for c in tok[1:])
        base_weight = 8.0 if code_like else (6.0 if len(tok) >= 8 else 3.0)
        for v in variants(tok):
            k = v.lower()
            prev = merged.get(k)
            weight = base_weight if v == tok else base_weight * 0.82
            is_exactish = code_like or tok.lower() in {"netrc", "kubeconfig", "duplicate"}
            if prev is None or weight > prev[0]:
                merged[k] = (weight, is_exactish)
    # Keep the search compact and deterministic.
    ranked = sorted(((k, w, e) for k, (w, e) in merged.items()), key=lambda x: (-x[1], -len(x[0]), x[0]))
    return ranked[:18]


def is_prod_path(path: str) -> bool:
    p = Path(path)
    parts = {part.lower() for part in p.parts}
    if parts & NONPROD_PARTS:
        return False
    if p.suffix.lower() not in CODE_EXTS:
        return False
    name = p.name.lower()
    if name.startswith("test_") or name.endswith("_test.go") or name.endswith("test.java") or name.endswith("tests.py"):
        return False
    return True


def grep_repo(repo: Path, terms: list[tuple[str, float, bool]]) -> tuple[str, float]:
    if not terms:
        return "", 0.0
    cmd = ["git", "grep", "-n", "-I", "-i"]
    for term, _, _ in terms:
        cmd.extend(["-e", term])
    cmd.extend(["--", ":(exclude)*.lock"])
    start = time.perf_counter()
    cp = run(cmd, cwd=repo, timeout=180.0)
    elapsed = (time.perf_counter() - start) * 1000.0
    # git grep uses 1 for no matches.
    if cp.returncode not in {0, 1}:
        raise RuntimeError(f"git grep failed: {cp.stderr[-1000:]}")
    return cp.stdout, elapsed


def parse_hits(output: str, terms: list[tuple[str, float, bool]]) -> dict[str, dict]:
    term_meta = {t.lower(): (w, exactish) for t, w, exactish in terms}
    by_file: dict[str, dict] = defaultdict(lambda: {"lines": [], "tf": Counter(), "bytes": 0})
    for line in output.splitlines():
        try:
            path, lineno, text = line.split(":", 2)
        except ValueError:
            continue
        if not is_prod_path(path):
            continue
        low = text.lower()
        rec = by_file[path]
        rec["lines"].append((lineno, text))
        rec["bytes"] += len((line + "\n").encode("utf-8", errors="replace"))
        for term in term_meta:
            count = low.count(term)
            if count:
                rec["tf"][term] += count
    return by_file


def rank_files(by_file: dict[str, dict], terms: list[tuple[str, float, bool]]) -> list[dict]:
    if not by_file:
        return []
    n = len(by_file)
    df = Counter()
    for rec in by_file.values():
        for term in rec["tf"]:
            df[term] += 1
    meta = {t.lower(): (w, exactish) for t, w, exactish in terms}
    rows = []
    for path, rec in by_file.items():
        score = 0.0
        exact_hits = 0
        matched = []
        path_low = path.lower()
        for term, tf in rec["tf"].items():
            w, exactish = meta[term]
            idf = math.log((n + 1.0) / (df[term] + 1.0)) + 1.0
            contribution = w * idf * (1.0 + math.log1p(tf))
            if exactish:
                contribution *= 2.75
                exact_hits += 1
            if term in path_low:
                contribution *= 1.35
            score += contribution
            matched.append(term)
        # Prefer focused implementation files over giant aggregator files on ties.
        score -= 0.0008 * rec["bytes"]
        rows.append({
            "path": path,
            "score": score,
            "exact_hits": exact_hits,
            "matched_terms": sorted(matched),
            "hit_bytes": rec["bytes"],
            "hit_lines": rec["lines"],
        })
    rows.sort(key=lambda r: (-r["exact_hits"], -r["score"], r["hit_bytes"], r["path"]))
    return rows


def compact_search_payload(ranked: list[dict], limit_files: int = 12, limit_lines_per_file: int = 8) -> bytes:
    payload = []
    for row in ranked[:limit_files]:
        payload.append({
            "path": row["path"],
            "score": round(row["score"], 6),
            "matched_terms": row["matched_terms"],
            "lines": row["hit_lines"][:limit_lines_per_file],
        })
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", type=Path, required=True)
    ap.add_argument("--condition", choices=["OFF", "ON"], required=True)
    ap.add_argument("--trace-out", type=Path, required=True)
    ap.add_argument("--result-out", type=Path, required=True)
    args = ap.parse_args()

    task = json.loads(args.task.read_text(encoding="utf-8"))
    repo = ensure_repo(task["repository"], task["commit_sha"])

    writer = TraceWriter(
        args.trace_out,
        task_id=task["task_id"],
        condition=args.condition,
        surface="local-git-real-repository",
        model="deterministic-localization-ranker-v0.1",
        task_stratum=task.get("task_stratum") or "repository-local",
    )
    started = time.perf_counter()
    terms = query_terms(task["prompt"])
    writer.emit("context_action_selected", action_id="grep-rank", action_kind="SEARCH", query_terms=[t for t, _, _ in terms])
    writer.tool_call_start("call-grep", "git-grep", action_id="grep-rank")
    raw, grep_ms = grep_repo(repo, terms)
    writer.tool_call_end("call-grep", True, latency_ms=grep_ms)

    ranked = rank_files(parse_hits(raw, terms), terms)
    if ranked:
        selected = ranked[0]["path"]
    else:
        selected = ""

    raw_bytes = len(raw.encode("utf-8", errors="replace"))
    payload = compact_search_payload(ranked)
    payload_bytes = len(payload)

    if args.condition == "OFF":
        # Baseline: the ranker/worker consumes the semantic search payload directly.
        evidence_id = "ev-search-semantic"
        refs = [f"git:{task['repository']}@{task['commit_sha']}:{r['path']}" for r in ranked[:12]] or [f"git:{task['repository']}@{task['commit_sha']}"]
        writer.evidence_observed(
            evidence_id,
            evidence_kind="semantic",
            certificate_capable=False,
            provenance_refs=refs,
            metrics={"controller_only_bytes": metric(0)},
        )
        writer.expose_full(evidence_id, bytes_=payload_bytes, tokens=None)
    else:
        # BCS-style split: exact deterministic search output stays controller-only.
        writer.emit(
            "controller_context_recorded",
            context_id="grep-output",
            representation="structured-search-state",
            metrics={"controller_only_bytes": metric(raw_bytes)},
        )
        exact_value = {
            "selected_path": selected,
            "matched_terms": ranked[0]["matched_terms"] if ranked else [],
            "ranker": "deterministic-localization-ranker-v0.1",
        }
        evidence_id = "ev-selected-path"
        provenance = [f"git:{task['repository']}@{task['commit_sha']}:{selected}"] if selected else [f"git:{task['repository']}@{task['commit_sha']}"]
        digest = writer.evidence_observed(
            evidence_id,
            evidence_kind="structured",
            certificate_capable=True,
            provenance_refs=provenance,
            exact_value=exact_value,
            metrics={"controller_only_bytes": metric(raw_bytes)},
        )
        certificate = {
            "schema": "ace-s.repo-localization.selected-path.v0.1",
            "outcome": exact_value,
            "source_ref": provenance[0],
        }
        cert_bytes = len(json.dumps(certificate, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        writer.certificate_emitted(
            "cert-selected-path",
            evidence_id,
            schema_ref="ace-s.repo-localization.selected-path.v0.1",
            exact_value_sha256=digest or "sha256:0",
            provenance_refs=provenance,
            metrics={"certificate_bytes": metric(cert_bytes)},
        )
        writer.expose_certificate("cert-selected-path", bytes_=cert_bytes, tokens=None)

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    writer.end(passed=False, quality_score=None, wall_clock_ms=elapsed_ms)
    args.result_out.parent.mkdir(parents=True, exist_ok=True)
    args.result_out.write_text(json.dumps({"answer": selected}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
