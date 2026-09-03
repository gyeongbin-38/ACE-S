#!/usr/bin/env python3
"""Exercise counterfactual architecture-delta locality and revalidation semantics."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from architecture_delta import evaluate_delta
from architecture_impact import impact

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks" / "architecture-state-graph-valid-v0.1.json"


def complete_record(base: dict, changed_ids: list[str]) -> dict:
    result = impact(base, changed_ids)
    assert result["status"] == "ok", result
    return {
        "rerun_fitness_checks": result["rerun_fitness_checks"],
        "rerun_scenarios": result["rerun_scenarios"],
        "reprove_obligations": result["reprove_obligations"],
    }


def errors(result: dict) -> set[str]:
    return {x["code"] for x in result.get("issues", [])}


def main() -> None:
    base = json.loads(BASE.read_text(encoding="utf-8"))
    changed_ids = ["asr-tenant-isolation"]
    record = complete_record(base, changed_ids)
    cases = []

    # 1. A requirement/ASR wording change with unchanged mechanisms is legal, but
    # the governed checks must be explicitly reopened.
    g = copy.deepcopy(base)
    g["graph_id"] = "delta-local-intent-only"
    g["asrs"][0]["text"] = "no cross-tenant read or write under delegated access"
    cases.append(("localized-intent-revision", g, record, True, set()))

    # 2. A new architecture node is allowed when traceably anchored to a decision
    # already reopened by the changed ASR.
    g = copy.deepcopy(base)
    g["graph_id"] = "delta-anchored-new-boundary"
    g["asrs"][0]["text"] = "tenant isolation must survive privileged worker compromise"
    g["boundaries"].append({
        "id": "worker-isolation-boundary",
        "type": "BOUNDARY",
        "trust_boundary": False,
        "evidence_status": "ACCEPTED_INTENT",
    })
    g["traceability_edges"].append({
        "from": "dec-store", "relation": "AFFECTS", "to": "worker-isolation-boundary"
    })
    cases.append(("anchored-new-architecture", g, record, True, set()))

    # 3. Rewriting an unrelated existing component is collateral architectural
    # churn even when the changed ASR itself is handled correctly.
    g = copy.deepcopy(base)
    g["graph_id"] = "delta-collateral-rewrite"
    g["asrs"][0]["text"] = "no cross-tenant access including batch exports"
    g["components"][0]["note"] = "rewritten for unrelated API modernization"
    cases.append((
        "collateral-existing-rewrite", g, record, False,
        {"COLLATERAL_EXISTING_NODE_CHANGE"},
    ))

    # 4. A new component that has no traceability path to the reopened decision
    # neighborhood is architectural invention, not a causal response.
    g = copy.deepcopy(base)
    g["graph_id"] = "delta-unanchored-component"
    g["asrs"][0]["text"] = "no cross-tenant access from admin workflows"
    g["components"].append({
        "id": "analytics", "type": "COMPONENT", "evidence_status": "ACCEPTED_INTENT"
    })
    cases.append((
        "unanchored-new-component", g, record, False,
        {"UNANCHORED_NEW_ARCHITECTURE"},
    ))

    # 5. A local graph edit without re-running the checks opened by the impact
    # closure is incomplete governance even if the topology itself is unchanged.
    g = copy.deepcopy(base)
    g["graph_id"] = "delta-missing-revalidation"
    g["asrs"][0]["text"] = "tenant isolation applies to support impersonation"
    cases.append((
        "missing-revalidation", g, {}, False,
        {"MISSING_FITNESS_REVALIDATION", "MISSING_SCENARIO_RERUN"},
    ))

    rows = []
    failed = []
    for cid, changed, change_record, expected_pass, expected_codes in cases:
        result = evaluate_delta(base, changed, changed_ids, change_record)
        actual_codes = errors(result)
        ok = (
            result.get("status") == "ok"
            and result.get("gate_passed") == expected_pass
            and expected_codes.issubset(actual_codes)
        )
        row = {
            "id": cid,
            "passed": ok,
            "gate_passed": result.get("gate_passed"),
            "expected_error_codes": sorted(expected_codes),
            "actual_error_codes": sorted(actual_codes),
            "collateral_change_ratio": result.get("collateral_change_ratio"),
            "actual_touched_count": result.get("actual_touched_count"),
        }
        rows.append(row)
        if not ok:
            failed.append({"row": row, "result": result})

    report = {
        "suite_id": "architecture-counterfactual-delta-v0.1",
        "cases": len(rows),
        "passed": sum(1 for x in rows if x["passed"]),
        "failed": len(failed),
        "rows": rows,
        "claim_boundary": (
            "Authored mutation fixtures validate causal-locality and revalidation accounting only. "
            "They do not show that an LLM will generate the correct counterfactual architecture."
        ),
    }
    print(json.dumps(report, indent=2))
    if failed:
        print(json.dumps({"failures": failed}, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
