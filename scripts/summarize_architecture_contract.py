#!/usr/bin/env python3
"""Summarize architecture-contract coverage without collapsing quality to one score."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_architecture_contract import DISTANT_LEVELS, DISTRIBUTED_KINDS, nonempty, string_list, validate


def pct(num: int, den: int) -> float | None:
    return None if den == 0 else round(100.0 * num / den, 3)


def summarize(obj: dict[str, Any]) -> dict[str, Any]:
    validation = validate(obj)

    hard = [x for x in obj.get("hard_constraints", []) if isinstance(x, dict)]
    critical_asrs = [x for x in obj.get("asrs", []) if isinstance(x, dict) and x.get("critical") is True]
    mutable = [x for x in obj.get("state", []) if isinstance(x, dict) and x.get("mutable") is True]
    critical_flows = [x for x in obj.get("critical_flows", []) if isinstance(x, dict) and x.get("critical") is True]
    boundaries = [x for x in obj.get("boundaries", []) if isinstance(x, dict)]
    distant = [x for x in boundaries if x.get("kind") in DISTRIBUTED_KINDS or x.get("chosen_distance") in DISTANT_LEVELS]
    cohesion_conflicts = [x for x in distant if string_list(x.get("cohesion_pressure", []))]
    decisions = [x for x in obj.get("decisions", []) if isinstance(x, dict)]
    high_lockin = [x for x in decisions if x.get("reversibility") in {"MIGRATABLE", "IRREVERSIBLE_OR_HIGH_LOCKIN"}]

    def flow_relation_complete(flow: dict[str, Any]) -> bool:
        hops = flow.get("hops")
        return isinstance(hops, list) and bool(hops) and all(
            isinstance(h, dict) and nonempty(h.get("from")) and nonempty(h.get("to")) and nonempty(h.get("interface"))
            for h in hops
        )

    result = {
        "candidate_id": obj.get("candidate_id"),
        "hard_gate_passed": validation["gate_passed"],
        "validator_errors": validation["error_count"],
        "validator_warnings": validation["warning_count"],
        "coverage": {
            "hard_constraints_satisfied_pct": pct(sum(x.get("status") == "satisfied" for x in hard), len(hard)),
            "critical_asr_mechanism_pct": pct(sum(nonempty(x.get("mechanism")) for x in critical_asrs), len(critical_asrs)),
            "critical_asr_traceability_pct": pct(sum(bool(x.get("mechanism_refs")) for x in critical_asrs), len(critical_asrs)),
            "critical_asr_fitness_pct": pct(sum(nonempty(x.get("fitness_check")) for x in critical_asrs), len(critical_asrs)),
            "mutable_state_ownership_or_protocol_pct": pct(sum(nonempty(x.get("owner")) or nonempty(x.get("multi_writer_protocol")) for x in mutable), len(mutable)),
            "mutable_state_recovery_pct": pct(sum(nonempty(x.get("recovery")) for x in mutable), len(mutable)),
            "critical_flow_relation_complete_pct": pct(sum(flow_relation_complete(x) for x in critical_flows), len(critical_flows)),
            "critical_flow_failure_model_pct": pct(sum(nonempty(x.get("failure_behavior")) for x in critical_flows), len(critical_flows)),
            "critical_flow_observability_pct": pct(sum(nonempty(x.get("observability_point")) for x in critical_flows), len(critical_flows)),
            "distant_boundary_separation_pressure_pct": pct(sum(bool(string_list(x.get("separation_pressure", x.get("forces", [])))) for x in distant), len(distant)),
            "distant_boundary_cohesion_mitigation_pct": pct(sum(bool(string_list(x.get("cohesion_mitigation", []))) for x in cohesion_conflicts), len(cohesion_conflicts)),
            "distant_boundary_reversal_pct": pct(sum(nonempty(x.get("merge_condition")) or nonempty(x.get("reversal_condition")) for x in distant), len(distant)),
            "high_lockin_decision_alternatives_pct": pct(sum(bool(x.get("alternatives")) for x in high_lockin), len(high_lockin)),
            "high_lockin_decision_kill_condition_pct": pct(sum(nonempty(x.get("kill_condition")) for x in high_lockin), len(high_lockin)),
        },
        "counts": {
            "components": len([x for x in obj.get("components", []) if isinstance(x, dict)]),
            "boundaries": len(boundaries),
            "distant_boundaries": len(distant),
            "distant_boundaries_with_cohesion_pressure": len(cohesion_conflicts),
            "critical_asrs": len(critical_asrs),
            "mutable_state_categories": len(mutable),
            "critical_flows": len(critical_flows),
            "decisions": len(decisions),
            "high_lockin_decisions": len(high_lockin),
        },
        "claim_boundary": "Coverage report only. Metrics expose missing architecture evidence/relations; they are not a scalar architecture-quality score.",
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    obj = json.loads(args.candidate.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit("candidate root must be object")
    print(json.dumps(summarize(obj), indent=2))


if __name__ == "__main__":
    main()
