#!/usr/bin/env python3
"""Small stdlib-only writer for ACE-S runtime trace JSONL v0.1.

Adapters should emit facts they can actually observe. Missing values should be
recorded as unavailable rather than inferred. This module does not perform any
context optimization itself; it only normalizes instrumentation.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "0.1"


def metric(value: float | int | None, *, status: str = "measured") -> dict[str, Any]:
    if value is None:
        return {"status": "unavailable", "value": None}
    if status not in {"measured", "estimated"}:
        raise ValueError("status must be measured or estimated when value is present")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError("metric value must be a non-negative number")
    return {"status": status, "value": value}


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


@dataclass
class TraceWriter:
    path: Path
    task_id: str
    condition: str
    surface: str
    model: str
    task_stratum: str
    _seq: int = 0
    _events: list[dict[str, Any]] = field(default_factory=list)
    _ended: bool = False

    def __post_init__(self) -> None:
        if self.condition not in {"OFF", "ON"}:
            raise ValueError("condition must be OFF or ON")
        if not self.task_id:
            raise ValueError("task_id is required")
        self.emit(
            "task_start",
            condition=self.condition,
            surface=self.surface,
            model=self.model,
            task_stratum=self.task_stratum,
        )

    def emit(self, event_type: str, *, metrics: dict[str, dict[str, Any]] | None = None, **fields: Any) -> dict[str, Any]:
        if self._ended:
            raise RuntimeError("cannot emit after task_end")
        self._seq += 1
        event = {
            "schema_version": SCHEMA_VERSION,
            "task_id": self.task_id,
            "event_id": f"e{self._seq:04d}",
            "seq": self._seq,
            "event_type": event_type,
            "metrics": metrics or {},
            **fields,
        }
        self._events.append(event)
        if event_type == "task_end":
            self._ended = True
        return event

    def tool_call_start(self, call_id: str, tool_name: str, action_id: str | None = None) -> None:
        fields: dict[str, Any] = {"call_id": call_id, "tool_name": tool_name}
        if action_id is not None:
            fields["action_id"] = action_id
        self.emit("tool_call_start", **fields)

    def tool_call_end(self, call_id: str, ok: bool, latency_ms: float | None = None) -> None:
        self.emit("tool_call_end", call_id=call_id, ok=ok, metrics={"tool_latency_ms": metric(latency_ms)})

    def evidence_observed(
        self,
        evidence_id: str,
        *,
        evidence_kind: str,
        certificate_capable: bool,
        provenance_refs: Iterable[str],
        exact_value: Any | None = None,
        metrics: dict[str, dict[str, Any]] | None = None,
    ) -> str | None:
        refs = list(provenance_refs)
        digest = None if exact_value is None else sha256_json(exact_value)
        fields: dict[str, Any] = {
            "evidence_id": evidence_id,
            "evidence_kind": evidence_kind,
            "certificate_capable": certificate_capable,
            "provenance_refs": refs,
        }
        if digest is not None:
            fields["value_sha256"] = digest
        self.emit("evidence_observed", metrics=metrics, **fields)
        return digest

    def certificate_emitted(
        self,
        certificate_id: str,
        evidence_id: str,
        *,
        schema_ref: str,
        exact_value_sha256: str,
        provenance_refs: Iterable[str],
        metrics: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.emit(
            "certificate_emitted",
            certificate_id=certificate_id,
            evidence_id=evidence_id,
            evidence_kind="structured",
            schema_ref=schema_ref,
            exact_value_sha256=exact_value_sha256,
            provenance_refs=list(provenance_refs),
            metrics=metrics,
        )

    def expose_full(self, evidence_id: str, *, bytes_: float | None = None, tokens: float | None = None) -> None:
        self.emit(
            "worker_context_exposed",
            representation="full",
            evidence_id=evidence_id,
            metrics={
                "worker_visible_bytes": metric(bytes_),
                "worker_visible_tokens": metric(tokens),
            },
        )

    def expose_certificate(self, certificate_id: str, *, bytes_: float | None = None, tokens: float | None = None) -> None:
        self.emit(
            "worker_context_exposed",
            representation="certificate",
            certificate_id=certificate_id,
            metrics={
                "worker_visible_bytes": metric(bytes_),
                "worker_visible_tokens": metric(tokens),
            },
        )

    def end(self, *, passed: bool, quality_score: float | None, wall_clock_ms: float | None = None, failure_category: str | None = None) -> None:
        fields: dict[str, Any] = {"passed": passed, "quality_score": quality_score}
        if failure_category:
            fields["failure_category"] = failure_category
        self.emit("task_end", metrics={"wall_clock_ms": metric(wall_clock_ms)}, **fields)
        self.flush()

    def flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        text = "\n".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")) for e in self._events) + "\n"
        self.path.write_text(text, encoding="utf-8")
