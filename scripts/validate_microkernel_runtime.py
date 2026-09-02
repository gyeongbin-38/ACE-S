#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "skills" / "adaptive-context-engineering" / "runtime"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


controller = load("ace_context_controller_validate", RUNTIME / "context_controller.py")
selector = load("ace_value_selector_validate", RUNTIME / "value_selector.py")


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"microkernel validation failed: {msg}")


def main() -> None:
    micro_bytes = (RUNTIME / "MICROKERNEL.md").stat().st_size
    check(micro_bytes <= 2000, f"MICROKERNEL.md is {micro_bytes} bytes; budget is 2000")

    ir = json.loads((RUNTIME / "policy-ir.json").read_text(encoding="utf-8"))
    capsules = json.loads((RUNTIME / "policy-capsules.json").read_text(encoding="utf-8"))
    schema = json.loads((RUNTIME / "signal-vector.schema.json").read_text(encoding="utf-8"))

    check(set(ir["codes"]["source"]) == {"C", "D", "R", "T", "G"}, "source codes drifted")
    check(set(ir["codes"]["requirement"]) == {"E", "F", "U", "H"}, "requirement codes drifted")
    check(set(capsules["source"]) == {"CODE", "DOCUMENT", "RESEARCH", "STATE", "GENERIC"}, "source capsules incomplete")
    check(set(capsules["requirement"]) == {"EVIDENCE", "TEMPORAL", "TOOLS", "RETENTION"}, "requirement capsules incomplete")
    check(schema["additionalProperties"] is False, "SignalVector must stay closed")

    cases = [
        ({"N": "0", "S": "G", "Q": [], "V": "A", "P": "?", "B": "-"}, "STOP", "DIRECT", None),
        ({"N": "1", "S": "C", "Q": ["E"], "V": "X", "P": "?", "B": "-"}, "SPECIALIZE", "SPECIALIZED", "CODE"),
        ({"N": "1", "S": "G", "Q": ["U"], "V": "I", "P": "?", "B": "-"}, "OPEN", "GENERIC", "GENERIC"),
        ({"N": "1", "S": "C", "Q": [], "V": "A", "P": "0", "B": "R"}, "SWITCH", "SPECIALIZED", "RESEARCH"),
        ({"N": "1", "S": "D", "Q": ["H"], "V": "A", "P": "0", "B": "-"}, "SWITCH", "GENERIC", "GENERIC"),
    ]
    for raw, action, mode, source in cases:
        decision = controller.decide(controller.SignalVector.from_dict(raw))
        check(decision["action"] == action, f"wrong action for {raw}")
        check(decision["entry_mode"] == mode, f"wrong mode for {raw}")
        check(decision["source"] == source, f"wrong source for {raw}")
        directive = controller.compact_directive(decision)
        check(len(directive.encode("utf-8")) <= 512, "directive exceeded 512-byte hard budget")
        capsule = controller.worker_capsule(decision)
        check(len(capsule.encode("utf-8")) <= 3000, "single-step worker capsule exceeded 3000-byte hard budget")

    actions = [
        selector.ContextAction("cheap-high-value", epistemic_value=8, context_tokens=100),
        selector.ContextAction("large-low-value", epistemic_value=9, context_tokens=1000),
    ]
    chosen = selector.choose_next(actions)
    check(chosen is not None and chosen.name == "cheap-high-value", "value-per-cost selector ordering failed")
    stopped = selector.choose_next(actions, min_value_per_cost=1.0)
    check(stopped is None, "selector threshold STOP failed")
    mandatory = selector.ContextAction("mandatory", epistemic_value=0.1, context_tokens=5000, mandatory=True)
    check(selector.choose_next(actions + [mandatory]).name == "mandatory", "mandatory evidence gate failed")
    budgeted = selector.choose_next(actions, remaining_context_tokens=200)
    check(budgeted is not None and budgeted.name == "cheap-high-value", "context budget filter failed")

    print(
        "OK: ACE-S microkernel runtime validated; "
        f"kernel={micro_bytes}B, sources=5, requirements=4, controller/recovery/value gates pass"
    )


if __name__ == "__main__":
    main()
