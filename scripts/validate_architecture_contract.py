#!/usr/bin/env python3
"""Validate architecture candidates against structural architecture invariants.

This is a deterministic contract checker, not an architecture-quality oracle.
It catches explicit hard failures and relational omissions that should not be
hidden by a prose or LLM-judge score.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

STRONG_SEPARATION_PRESSURES = {
    "state_consistency",
    "trust",
    "failure_isolation",
    "independent_scale",
    "independent_deployment",
    "runtime_requirement",
    "regulatory_isolation",
    "data_location",
}
ALLOWED_SEPARATION_PRESSURES = STRONG_SEPARATION_PRESSURES | {"change_coupling", "ownership"}
ALLOWED_COHESION_PRESSURES = {
    "shared_invariant",
    "transactional_consistency",
    "coordinated_change",
    "shared_domain_model",
    "chatty_latency",
    "lifecycle_recovery",
}
DISTRIBUTED_KINDS = {"process", "service", "network"}
DISTANT_LEVELS = {"PROCESS", "SERVICE", "SYSTEM"}
HIGH_LOCKIN = {"MIGRATABLE", "IRREVERSIBLE_OR_HIGH_LOCKIN"}
CHANGE_LIKELIHOOD = {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [x for x in value if isinstance(x, str) and x]


def issue(code: str, path: str, message: str, severity: str = "error") -> dict[str, str]:
    return {"code": code, "path": path, "message": message, "severity": severity}


def validate(candidate: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []

    if not nonempty(candidate.get("candidate_id")):
        issues.append(issue("CANDIDATE_ID_REQUIRED", "candidate_id", "candidate_id is required"))

    components = candidate.get("components", [])
    if not isinstance(components, list):
        components = []
        issues.append(issue("COMPONENTS_INVALID", "components", "components must be an array"))
    component_ids = {
        c.get("id") for c in components
        if isinstance(c, dict) and nonempty(c.get("id"))
    }

    boundaries = candidate.get("boundaries", [])
    boundary_ids = {
        b.get("id") for b in boundaries
        if isinstance(b, dict) and nonempty(b.get("id"))
    }
    flows = candidate.get("critical_flows", [])
    flow_ids = {
        f.get("id") for f in flows
        if isinstance(f, dict) and nonempty(f.get("id"))
    }
    decisions = candidate.get("decisions", [])
    decision_ids = {
        d.get("id") for d in decisions
        if isinstance(d, dict) and nonempty(d.get("id"))
    }
    traceable_ids = component_ids | boundary_ids | flow_ids | decision_ids

    for i, c in enumerate(candidate.get("hard_constraints", [])):
        if not isinstance(c, dict):
            issues.append(issue("HARD_CONSTRAINT_INVALID", f"hard_constraints[{i}]", "constraint must be object"))
            continue
        status = c.get("status")
        if status == "violated":
            issues.append(issue("HARD_CONSTRAINT_VIOLATION", f"hard_constraints[{i}]", "hard constraint is violated"))
        elif status == "unknown":
            issues.append(issue("HARD_CONSTRAINT_UNRESOLVED", f"hard_constraints[{i}]", "hard constraint remains unknown"))
        elif status != "satisfied":
            issues.append(issue("HARD_CONSTRAINT_STATUS_INVALID", f"hard_constraints[{i}].status", "status must be satisfied, violated, or unknown"))

    for i, a in enumerate(candidate.get("asrs", [])):
        if not isinstance(a, dict):
            issues.append(issue("ASR_INVALID", f"asrs[{i}]", "ASR must be object"))
            continue
        if a.get("critical") is True and not nonempty(a.get("mechanism")):
            issues.append(issue("CRITICAL_ASR_NO_MECHANISM", f"asrs[{i}].mechanism", "critical ASR has no architecture mechanism"))
        if a.get("critical") is True and not nonempty(a.get("fitness_check")):
            issues.append(issue("CRITICAL_ASR_NO_FITNESS_CHECK", f"asrs[{i}].fitness_check", "critical ASR has no executable or inspectable fitness check", "warning"))
        refs = a.get("mechanism_refs")
        if a.get("critical") is True and not refs:
            issues.append(issue("CRITICAL_ASR_NO_TRACEABILITY", f"asrs[{i}].mechanism_refs", "critical ASR has no typed trace to architecture mechanisms", "warning"))
        elif refs is not None:
            if not isinstance(refs, list) or any(not isinstance(x, str) or x not in traceable_ids for x in refs):
                issues.append(issue("ASR_TRACEABILITY_INVALID", f"asrs[{i}].mechanism_refs", "mechanism_refs must reference known component, boundary, flow, or decision ids"))

    for i, b in enumerate(boundaries):
        if not isinstance(b, dict):
            issues.append(issue("BOUNDARY_INVALID", f"boundaries[{i}]", "boundary must be object"))
            continue

        # `forces` is retained as a backwards-compatible alias for separation pressure.
        raw_separation = b.get("separation_pressure", b.get("forces", []))
        separation = {x for x in string_list(raw_separation) if x in ALLOWED_SEPARATION_PRESSURES}
        cohesion = {x for x in string_list(b.get("cohesion_pressure", [])) if x in ALLOWED_COHESION_PRESSURES}
        if not separation:
            issues.append(issue("BOUNDARY_WITHOUT_FORCE", f"boundaries[{i}].separation_pressure", "boundary has no material separation pressure"))

        kind = b.get("kind")
        distance = b.get("chosen_distance")
        is_distant = kind in DISTRIBUTED_KINDS or distance in DISTANT_LEVELS
        if is_distant and not (separation & STRONG_SEPARATION_PRESSURES):
            issues.append(issue("DISTRIBUTED_WEAK_BOUNDARY", f"boundaries[{i}]", "distant boundary lacks a strong isolation/scale/deployment/state driver", "warning"))

        between = b.get("between", [])
        if not isinstance(between, list) or len(between) != 2 or any(x not in component_ids for x in between):
            issues.append(issue("BOUNDARY_ENDPOINT_INVALID", f"boundaries[{i}].between", "boundary endpoints must reference exactly two known components"))

        if kind == "trust" and not nonempty(b.get("enforcement")):
            issues.append(issue("TRUST_BOUNDARY_NO_ENFORCEMENT", f"boundaries[{i}].enforcement", "trust boundary lacks an enforcement point"))

        if is_distant and cohesion and not string_list(b.get("cohesion_mitigation", [])):
            issues.append(issue("BOUNDARY_COHESION_CONFLICT_UNRESOLVED", f"boundaries[{i}].cohesion_mitigation", "distant boundary has material cohesion pressure but no explicit mitigation"))

        change = b.get("change_likelihood")
        if change is not None and change not in CHANGE_LIKELIHOOD:
            issues.append(issue("BOUNDARY_CHANGE_LIKELIHOOD_INVALID", f"boundaries[{i}].change_likelihood", "change_likelihood must be HIGH, MEDIUM, LOW, or UNKNOWN"))
        elif is_distant and cohesion and change == "UNKNOWN":
            issues.append(issue("BOUNDARY_CHANGE_LIKELIHOOD_UNKNOWN", f"boundaries[{i}].change_likelihood", "distant boundary with cohesion pressure has unknown change likelihood", "warning"))

        if is_distant and not (nonempty(b.get("merge_condition")) or nonempty(b.get("reversal_condition"))):
            issues.append(issue("DISTRIBUTED_BOUNDARY_NO_REVERSAL", f"boundaries[{i}]", "distant boundary has no merge/reversal condition", "warning"))

    for i, s in enumerate(candidate.get("state", [])):
        if not isinstance(s, dict):
            issues.append(issue("STATE_INVALID", f"state[{i}]", "state record must be object"))
            continue
        if s.get("mutable") is True:
            owner = s.get("owner")
            protocol = s.get("multi_writer_protocol")
            if not nonempty(owner) and not nonempty(protocol):
                issues.append(issue("MUTABLE_STATE_NO_OWNER", f"state[{i}]", "mutable state needs one authoritative owner or an explicit multi-writer protocol"))
            if nonempty(owner) and owner not in component_ids:
                issues.append(issue("STATE_OWNER_UNKNOWN_COMPONENT", f"state[{i}].owner", "state owner must reference a known component"))
            if not nonempty(s.get("recovery")):
                issues.append(issue("MUTABLE_STATE_NO_RECOVERY", f"state[{i}].recovery", "mutable state has no recovery/rebuild path", "warning"))

    for i, f in enumerate(flows):
        if not isinstance(f, dict):
            issues.append(issue("FLOW_INVALID", f"critical_flows[{i}]", "flow must be object"))
            continue
        hops = f.get("hops", [])
        if not isinstance(hops, list) or not hops:
            issues.append(issue("RELATION_GAP", f"critical_flows[{i}].hops", "critical flow has no explicit relation path"))
        else:
            for j, h in enumerate(hops):
                if not isinstance(h, dict):
                    issues.append(issue("RELATION_GAP", f"critical_flows[{i}].hops[{j}]", "hop must be object"))
                    continue
                if h.get("from") not in component_ids or h.get("to") not in component_ids or not nonempty(h.get("interface")):
                    issues.append(issue("RELATION_GAP", f"critical_flows[{i}].hops[{j}]", "hop must connect known components through an explicit interface"))
        if f.get("critical") is True and not nonempty(f.get("failure_behavior")):
            issues.append(issue("CRITICAL_FLOW_NO_FAILURE_MODEL", f"critical_flows[{i}].failure_behavior", "critical flow lacks failure behavior"))
        if f.get("critical") is True and not nonempty(f.get("observability_point")):
            issues.append(issue("CRITICAL_FLOW_NO_OBSERVABILITY", f"critical_flows[{i}].observability_point", "critical flow lacks an observability point", "warning"))

    for i, d in enumerate(decisions):
        if not isinstance(d, dict):
            issues.append(issue("DECISION_INVALID", f"decisions[{i}]", "decision must be object"))
            continue
        rev = d.get("reversibility")
        if rev in HIGH_LOCKIN:
            if not d.get("alternatives"):
                issues.append(issue("HIGH_LOCKIN_NO_ALTERNATIVES", f"decisions[{i}].alternatives", "high-lock-in decision has no recorded alternatives"))
            if not nonempty(d.get("kill_condition")):
                issues.append(issue("HIGH_LOCKIN_NO_KILL_CONDITION", f"decisions[{i}].kill_condition", "high-lock-in decision has no reversal/kill condition"))
            if not d.get("drivers"):
                issues.append(issue("HIGH_LOCKIN_NO_DRIVERS", f"decisions[{i}].drivers", "high-lock-in decision has no explicit drivers"))

    errors = [x for x in issues if x["severity"] == "error"]
    warnings = [x for x in issues if x["severity"] == "warning"]
    return {
        "candidate_id": candidate.get("candidate_id"),
        "gate_passed": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": issues,
        "claim_boundary": "Deterministic structural contract validation only; passing does not prove that an architecture is optimal or production-ready.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    obj = json.loads(args.candidate.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit("candidate root must be object")
    result = validate(obj)
    print(json.dumps(result, indent=2))
    if args.require_pass and not result["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
