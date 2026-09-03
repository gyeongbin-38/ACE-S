#!/usr/bin/env python3
"""Validate ACE-S runtime trace JSONL v0.1 using only the Python stdlib."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

SCHEMA_VERSION = "0.1"
METRIC_KEYS = {
    "worker_visible_bytes", "worker_visible_tokens",
    "controller_only_bytes", "controller_only_tokens",
    "certificate_bytes", "certificate_tokens",
    "sample_draws", "wall_clock_ms", "tool_latency_ms", "model_latency_ms",
}
METRIC_STATUS = {"measured", "estimated", "unavailable"}
EVENT_TYPES = {
    "task_start", "context_action_selected", "tool_call_start", "tool_call_end",
    "evidence_observed", "certificate_emitted", "worker_context_exposed",
    "controller_context_recorded", "cache_hit", "cache_miss", "expensive_eval",
    "sample_draw", "model_call", "task_end",
}


class TraceError(ValueError):
    pass


def fail(msg: str) -> None:
    raise TraceError(msg)


def load_trace(path: Path) -> list[dict]:
    events = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"line {lineno}: invalid JSON: {exc}")
        if not isinstance(obj, dict):
            fail(f"line {lineno}: event must be an object")
        obj["__line__"] = lineno
        events.append(obj)
    if not events:
        fail("trace is empty")
    return events


def validate_metric(name: str, spec: object, lineno: int) -> None:
    if name not in METRIC_KEYS:
        fail(f"line {lineno}: unknown metric {name!r}")
    if not isinstance(spec, dict):
        fail(f"line {lineno}: metric {name!r} must be an object")
    status = spec.get("status")
    value = spec.get("value")
    if status not in METRIC_STATUS:
        fail(f"line {lineno}: metric {name!r} has invalid status {status!r}")
    if status == "unavailable":
        if value is not None:
            fail(f"line {lineno}: unavailable metric {name!r} must have null value")
        return
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        fail(f"line {lineno}: metric {name!r} with status {status!r} requires numeric value")
    if not math.isfinite(float(value)) or value < 0:
        fail(f"line {lineno}: metric {name!r} must be finite and non-negative")


def require_nonempty_string(event: dict, key: str) -> str:
    value = event.get(key)
    if not isinstance(value, str) or not value.strip():
        fail(f"line {event['__line__']}: {key} must be a non-empty string")
    return value


def require_refs(event: dict, key: str = "provenance_refs") -> tuple[str, ...]:
    refs = event.get(key)
    if not isinstance(refs, list) or not refs or any(not isinstance(x, str) or not x.strip() for x in refs):
        fail(f"line {event['__line__']}: {key} must be a non-empty string array")
    return tuple(refs)


def validate(events: list[dict]) -> dict:
    if events[0].get("event_type") != "task_start":
        fail("first event must be task_start")
    if events[-1].get("event_type") != "task_end":
        fail("last event must be task_end")

    task_id = None
    seen_ids: set[str] = set()
    last_seq = 0
    open_calls: set[str] = set()
    evidence: dict[str, dict] = {}
    certificates: dict[str, dict] = {}
    ended = False

    for index, event in enumerate(events):
        lineno = event["__line__"]
        if event.get("schema_version") != SCHEMA_VERSION:
            fail(f"line {lineno}: schema_version must be {SCHEMA_VERSION!r}")
        event_task = require_nonempty_string(event, "task_id")
        if task_id is None:
            task_id = event_task
        elif event_task != task_id:
            fail(f"line {lineno}: task_id changed within trace")
        event_id = require_nonempty_string(event, "event_id")
        if event_id in seen_ids:
            fail(f"line {lineno}: duplicate event_id {event_id!r}")
        seen_ids.add(event_id)
        seq = event.get("seq")
        if isinstance(seq, bool) or not isinstance(seq, int) or seq <= last_seq:
            fail(f"line {lineno}: seq must be a strictly increasing positive integer")
        last_seq = seq
        event_type = event.get("event_type")
        if event_type not in EVENT_TYPES:
            fail(f"line {lineno}: unsupported event_type {event_type!r}")
        if ended:
            fail(f"line {lineno}: event appears after task_end")
        metrics = event.get("metrics")
        if not isinstance(metrics, dict):
            fail(f"line {lineno}: metrics must be an object")
        for name, spec in metrics.items():
            validate_metric(name, spec, lineno)

        if event_type == "task_start" and index != 0:
            fail(f"line {lineno}: task_start may appear only once at the beginning")
        elif event_type == "tool_call_start":
            call_id = require_nonempty_string(event, "call_id")
            if call_id in open_calls:
                fail(f"line {lineno}: duplicate open tool call {call_id!r}")
            open_calls.add(call_id)
        elif event_type == "tool_call_end":
            call_id = require_nonempty_string(event, "call_id")
            if call_id not in open_calls:
                fail(f"line {lineno}: tool_call_end has no preceding open start for {call_id!r}")
            open_calls.remove(call_id)
            if not isinstance(event.get("ok"), bool):
                fail(f"line {lineno}: tool_call_end.ok must be boolean")
        elif event_type == "evidence_observed":
            evidence_id = require_nonempty_string(event, "evidence_id")
            if evidence_id in evidence:
                fail(f"line {lineno}: duplicate evidence_id {evidence_id!r}")
            kind = event.get("evidence_kind")
            if kind not in {"structured", "semantic"}:
                fail(f"line {lineno}: evidence_kind must be structured or semantic")
            if not isinstance(event.get("certificate_capable"), bool):
                fail(f"line {lineno}: certificate_capable must be boolean")
            refs = require_refs(event)
            evidence[evidence_id] = {"kind": kind, "certificate_capable": event["certificate_capable"], "refs": refs}
        elif event_type == "certificate_emitted":
            certificate_id = require_nonempty_string(event, "certificate_id")
            if certificate_id in certificates:
                fail(f"line {lineno}: duplicate certificate_id {certificate_id!r}")
            evidence_id = require_nonempty_string(event, "evidence_id")
            if evidence_id not in evidence:
                fail(f"line {lineno}: certificate references unseen evidence {evidence_id!r}")
            observed = evidence[evidence_id]
            if event.get("evidence_kind") != "structured" or observed["kind"] != "structured":
                fail(f"line {lineno}: semantic evidence cannot be certificate-compressed")
            if not observed["certificate_capable"]:
                fail(f"line {lineno}: evidence {evidence_id!r} is not certificate-capable")
            require_nonempty_string(event, "schema_ref")
            require_nonempty_string(event, "exact_value_sha256")
            refs = require_refs(event)
            if not set(observed["refs"]).issubset(set(refs)):
                fail(f"line {lineno}: certificate detached from observed provenance")
            certificates[certificate_id] = {"evidence_id": evidence_id, "refs": refs}
        elif event_type == "worker_context_exposed":
            rep = event.get("representation")
            if rep not in {"full", "certificate"}:
                fail(f"line {lineno}: representation must be full or certificate")
            has_e = isinstance(event.get("evidence_id"), str) and bool(event.get("evidence_id"))
            has_c = isinstance(event.get("certificate_id"), str) and bool(event.get("certificate_id"))
            if has_e == has_c:
                fail(f"line {lineno}: worker_context_exposed requires exactly one of evidence_id/certificate_id")
            if rep == "full" and (not has_e or event["evidence_id"] not in evidence):
                fail(f"line {lineno}: full exposure must reference observed evidence")
            if rep == "certificate" and (not has_c or event["certificate_id"] not in certificates):
                fail(f"line {lineno}: certificate exposure must reference an emitted certificate")
        elif event_type in {"cache_hit", "cache_miss"}:
            require_nonempty_string(event, "cache_key")
        elif event_type == "expensive_eval":
            require_nonempty_string(event, "expensive_eval_id")
        elif event_type == "task_end":
            if index != len(events) - 1:
                fail(f"line {lineno}: task_end must be the final event")
            if not isinstance(event.get("passed"), bool):
                fail(f"line {lineno}: task_end.passed must be boolean")
            qs = event.get("quality_score")
            if qs is not None and (isinstance(qs, bool) or not isinstance(qs, (int, float)) or not math.isfinite(float(qs))):
                fail(f"line {lineno}: quality_score must be finite number or null")
            ended = True

    if open_calls:
        fail(f"unclosed tool calls: {sorted(open_calls)}")
    return {
        "task_id": task_id,
        "events": len(events),
        "evidence": len(evidence),
        "certificates": len(certificates),
        "status": "valid",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    try:
        result = validate(load_trace(args.trace))
    except TraceError as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, indent=2))
        raise SystemExit(1)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
