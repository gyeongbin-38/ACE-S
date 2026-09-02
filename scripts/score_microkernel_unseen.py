#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "adaptive-context-engineering"
RUNTIME = SKILL / "runtime"
FIXTURE = ROOT / "benchmarks" / "microkernel-unseen-v0.1.json"

spec = importlib.util.spec_from_file_location("ace_context_controller_unseen", RUNTIME / "context_controller.py")
controller = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = controller
spec.loader.exec_module(controller)

KERNEL = "SKILL.md"
INDEX = "manifests/INDEX.md"
GENERIC = "manifests/generic.md"
MICRO = "runtime/MICROKERNEL.md"
DOMAIN = {
    "CODE": ("manifests/code.md", "references/coding.md"),
    "DOCUMENT": ("manifests/document.md", "references/long-document.md"),
    "RESEARCH": ("manifests/research.md", "references/research.md"),
    "STATE": ("manifests/state.md", "references/temporal.md"),
}
SRC_CODE = {"CODE": "C", "DOCUMENT": "D", "RESEARCH": "R", "STATE": "T", "GENERIC": "G"}


def size(rel: str) -> int:
    return (SKILL / rel).stat().st_size


def current_files(case: dict) -> list[str]:
    files = [KERNEL, INDEX]
    if case["entry_mode"] == "GENERIC":
        files.append(GENERIC)
    else:
        files.extend(DOMAIN[case["source"]])
    return files


def signal(case: dict) -> dict:
    return {"N": "1", "S": SRC_CODE[case["source"]], "Q": [], "V": "A", "P": "?", "B": "-"}


def sig_bytes(raw: dict) -> int:
    return len(json.dumps(raw, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def main() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = []
    for case in doc["cases"]:
        raw = signal(case)
        decision = controller.decide(controller.SignalVector.from_dict(raw))
        fit = decision["entry_mode"] == case["entry_mode"] and decision["source"] == case["source"]
        current = sum(size(p) for p in current_files(case))
        capsule = controller.worker_capsule(decision)
        opcode = controller.compact_directive(decision)
        inline = size(MICRO) + sig_bytes(raw) + len(capsule.encode("utf-8"))
        rows.append(
            {
                "task_id": case["task_id"],
                "source_line": case["source_line"],
                "gold_entry_mode": case["entry_mode"],
                "gold_source": case["source"],
                "representable": fit,
                "current_optional_text_bytes": current,
                "microkernel_inline_bytes": inline,
                "compiled_capsule_worker_bytes": len(capsule.encode("utf-8")),
                "compiled_opcode_worker_bytes": len(opcode.encode("utf-8")),
            }
        )

    base_mean = sum(r["current_optional_text_bytes"] for r in rows) / len(rows)

    def summary(field: str) -> dict:
        vals = [r[field] for r in rows]
        mean = sum(vals) / len(vals)
        return {
            "mean_bytes": round(mean, 1),
            "median_bytes": sorted(vals)[len(vals) // 2],
            "max_bytes": max(vals),
            "reduction_vs_current_pct": round(100 * (1 - mean / base_mean), 1),
        }

    generic = [r for r in rows if r["gold_entry_mode"] == "GENERIC"]
    specialized = [r for r in rows if r["gold_entry_mode"] == "SPECIALIZED"]
    result = {
        "experiment": doc["name"],
        "source": doc["source"],
        "policy_commit": doc["policy_commit"],
        "task_count": len(rows),
        "hard_generic_count": len(generic),
        "hard_specialized_count": len(specialized),
        "deterministic_representational_fit_pct": round(100 * sum(r["representable"] for r in rows) / len(rows), 1),
        "current_optional_text": summary("current_optional_text_bytes"),
        "microkernel_inline": summary("microkernel_inline_bytes"),
        "compiled_capsule_worker": summary("compiled_capsule_worker_bytes"),
        "compiled_opcode_worker": summary("compiled_opcode_worker_bytes"),
        "total_worker_control_bytes": {
            "current_optional_text": sum(r["current_optional_text_bytes"] for r in rows),
            "microkernel_inline": sum(r["microkernel_inline_bytes"] for r in rows),
            "compiled_capsule_worker": sum(r["compiled_capsule_worker_bytes"] for r in rows),
            "compiled_opcode_worker": sum(r["compiled_opcode_worker_bytes"] for r in rows),
        },
        "important_caveat": (
            "Sealed external-task structural test with oracle hard labels. The source range was inspected only after the protected policy files were fixed. "
            "This tests whether the frozen controller can represent the labels and how much control-policy text reaches the worker under those labels. "
            "It does not measure a model's ability to infer SignalVector fields from natural language and does not prove end-to-end answer quality."
        ),
        "rows": rows,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
