#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "adaptive-context-engineering"
RUNTIME = SKILL / "runtime"
FIXTURE = ROOT / "benchmarks" / "specialization-gate-bench-v0.1.json"

spec = importlib.util.spec_from_file_location("ace_context_controller", RUNTIME / "context_controller.py")
controller = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = controller
spec.loader.exec_module(controller)

KERNEL = "SKILL.md"
INDEX = "manifests/INDEX.md"
GENERIC = "manifests/generic.md"
MICROKERNEL = "runtime/MICROKERNEL.md"

DOMAIN = {
    "CODE": ("manifests/code.md", "references/coding.md"),
    "DOCUMENT": ("manifests/document.md", "references/long-document.md"),
    "RESEARCH": ("manifests/research.md", "references/research.md"),
    "STATE": ("manifests/state.md", "references/temporal.md"),
}
MODIFIER = {
    "TEMPORAL": ("manifests/temporal.md", "references/temporal.md"),
    "EVIDENCE": ("manifests/evidence.md", "references/evidence-and-provenance.md"),
    "TOOLS": ("manifests/tools.md", "references/tool-discovery.md"),
    "RETENTION": ("manifests/retention.md", "references/plan-aware.md"),
}
SRC_CODE = {"CODE": "C", "DOCUMENT": "D", "RESEARCH": "R", "STATE": "T", "GENERIC": "G"}
REQ_CODE = {"EVIDENCE": "E", "TEMPORAL": "F", "TOOLS": "U", "RETENTION": "H"}


def fsize(rel: str) -> int:
    return (SKILL / rel).stat().st_size


def uniq(seq: list[str]) -> list[str]:
    return list(dict.fromkeys(seq))


def current_optional_files(case: dict) -> list[str]:
    if case["activation"] == "DIRECT":
        return [KERNEL]
    files = [KERNEL, INDEX]
    if case["required_mode"] == "SPECIALIZED":
        files.extend(DOMAIN[case["required_domain"]])
    else:
        if case["family"] == "wrong-specialist-recovery":
            files.extend(DOMAIN[case["forced_domain"]])
        files.append(GENERIC)
        if case["late_domain"]:
            files.extend(DOMAIN[case["late_domain"]])
    for modifier in case["required_modifiers"]:
        files.extend(MODIFIER[modifier])
    return uniq(files)


def signal_bytes(sig: dict) -> int:
    return len(json.dumps(sig, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def make_signal(case: dict, source: str, *, progress: str = "?", backup: str = "-") -> dict:
    return {
        "N": "0" if case["activation"] == "DIRECT" else "1",
        "S": source,
        "Q": sorted(REQ_CODE[m] for m in case["required_modifiers"]),
        "V": "A",
        "P": progress,
        "B": backup,
    }


def controller_trace(case: dict) -> list[dict]:
    if case["activation"] == "DIRECT":
        sig = make_signal(case, "G")
        return [{"signal": sig, "decision": controller.decide(controller.SignalVector.from_dict(sig))}]

    if case["family"] == "wrong-specialist-recovery":
        wrong = SRC_CODE[case["forced_domain"]]
        first = make_signal(case, wrong)
        second = make_signal(case, wrong, progress="0")
        return [
            {"signal": first, "decision": controller.decide(controller.SignalVector.from_dict(first))},
            {"signal": second, "decision": controller.decide(controller.SignalVector.from_dict(second))},
        ]

    if case["late_domain"]:
        first = make_signal(case, "G")
        second = make_signal(case, SRC_CODE[case["late_domain"]], progress="1")
        return [
            {"signal": first, "decision": controller.decide(controller.SignalVector.from_dict(first))},
            {"signal": second, "decision": controller.decide(controller.SignalVector.from_dict(second))},
        ]

    source = "G" if case["required_mode"] == "GENERIC" else SRC_CODE[case["required_domain"]]
    sig = make_signal(case, source)
    return [{"signal": sig, "decision": controller.decide(controller.SignalVector.from_dict(sig))}]


def trace_covers(case: dict, trace: list[dict]) -> bool:
    decisions = [step["decision"] for step in trace]
    requirements = set(case["required_modifiers"])
    seen_requirements = {r for d in decisions for r in d.get("requirements", [])}
    if not requirements.issubset(seen_requirements):
        return False

    if case["activation"] == "DIRECT":
        return decisions[-1]["entry_mode"] == "DIRECT" and decisions[-1]["action"] == "STOP"

    if case["required_mode"] == "SPECIALIZED":
        return decisions[-1].get("source") == case["required_domain"] and decisions[-1]["entry_mode"] == "SPECIALIZED"

    if not any(d["entry_mode"] == "GENERIC" for d in decisions):
        return False
    if case["late_domain"] and decisions[-1].get("source") != case["late_domain"]:
        return False
    if case["family"] == "wrong-specialist-recovery" and decisions[-1].get("source") != "GENERIC":
        return False
    return True


def capsule_bytes(trace: list[dict]) -> int:
    return sum(len(controller.worker_capsule(step["decision"]).encode("utf-8")) for step in trace)


def opcode_bytes(trace: list[dict]) -> int:
    return sum(len(controller.compact_directive(step["decision"]).encode("utf-8")) for step in trace)


def evaluate(cases: list[dict]) -> dict:
    rows = []
    for case in cases:
        trace = controller_trace(case)
        current_bytes = sum(fsize(p) for p in current_optional_files(case))
        microkernel_inline = fsize(MICROKERNEL) + sum(signal_bytes(s["signal"]) for s in trace) + capsule_bytes(trace)
        compiled_capsule = capsule_bytes(trace)
        compiled_opcode = opcode_bytes(trace)
        rows.append(
            {
                "id": case["id"],
                "family": case["family"],
                "coverage": trace_covers(case, trace),
                "current_text_bytes": current_bytes,
                "microkernel_inline_bytes": microkernel_inline,
                "compiled_capsule_worker_bytes": compiled_capsule,
                "compiled_opcode_worker_bytes": compiled_opcode,
                "trace_steps": len(trace),
            }
        )

    def summarize(field: str) -> dict:
        values = [r[field] for r in rows]
        base = sum(r["current_text_bytes"] for r in rows) / len(rows)
        mean = sum(values) / len(values)
        return {
            "mean_bytes": round(mean, 1),
            "max_bytes": max(values),
            "mean_reduction_vs_current_pct": round(100 * (1 - mean / base), 1),
        }

    return {
        "experiment": "microkernel-control-exposure-v0.1",
        "fixture_count": len(rows),
        "mechanical_plan_coverage_pct": round(100 * sum(r["coverage"] for r in rows) / len(rows), 1),
        "current_optional_text": summarize("current_text_bytes"),
        "microkernel_inline": summarize("microkernel_inline_bytes"),
        "compiled_capsule_worker": summarize("compiled_capsule_worker_bytes"),
        "compiled_opcode_worker": summarize("compiled_opcode_worker_bytes"),
        "microkernel_file_bytes": fsize(MICROKERNEL),
        "policy_store_bytes_not_worker_context": sum(
            (RUNTIME / name).stat().st_size
            for name in ["policy-ir.json", "policy-capsules.json", "signal-vector.schema.json"]
        ),
        "important_caveat": (
            "This benchmark measures control-plane exposure and deterministic plan representability on controller-mechanics fixtures. "
            "It does not establish natural-language signal-extraction accuracy or end-to-end answer quality. "
            "Compiled modes assume policy execution/selection occurs outside the task worker context."
        ),
        "rows": rows,
    }


def main() -> None:
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
    print(json.dumps(evaluate(cases), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
