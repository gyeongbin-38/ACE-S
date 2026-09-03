#!/usr/bin/env python3
"""Deterministic consistency checker for typed architecture propositions.

The semantic layer supplies propositions and explicit constraint rules with
provenance. This engine only performs set/logic consistency checks; it does not
invent architecture rules from names or prose.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VALID_KINDS = {"REQUIRE", "FORBID", "ASSUME", "OBSERVE"}


def _issue(code: str, message: str, refs: list[str] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"code": code, "message": message}
    if refs:
        out["refs"] = sorted(set(refs))
    return out


def validate(obj: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    props = obj.get("propositions", [])
    rules = obj.get("rules", [])
    if not isinstance(props, list):
        return {"gate_passed": False, "issues": [_issue("PROPOSITIONS_INVALID", "propositions must be array")]}
    if not isinstance(rules, list):
        return {"gate_passed": False, "issues": [_issue("RULES_INVALID", "rules must be array")]}

    by_fact: dict[str, dict[str, list[dict[str, Any]]]] = {}
    prop_ids: set[str] = set()
    for i, p in enumerate(props):
        if not isinstance(p, dict):
            issues.append(_issue("PROPOSITION_INVALID", f"propositions[{i}] must be object")); continue
        pid, fact, kind = p.get("id"), p.get("fact"), p.get("kind")
        if not isinstance(pid, str) or not pid:
            issues.append(_issue("PROPOSITION_ID_REQUIRED", f"propositions[{i}] id required")); continue
        if pid in prop_ids:
            issues.append(_issue("DUPLICATE_PROPOSITION_ID", f"duplicate proposition id {pid}", [pid])); continue
        prop_ids.add(pid)
        if not isinstance(fact, str) or not fact:
            issues.append(_issue("PROPOSITION_FACT_REQUIRED", f"proposition {pid} fact required", [pid])); continue
        if kind not in VALID_KINDS:
            issues.append(_issue("PROPOSITION_KIND_INVALID", f"proposition {pid} invalid kind {kind}", [pid])); continue
        status = p.get("evidence_status")
        if status not in {"OBSERVED", "ACCEPTED_INTENT", "INFERRED", "UNRESOLVED"}:
            issues.append(_issue("PROPOSITION_EVIDENCE_STATUS_INVALID", f"proposition {pid} invalid evidence_status", [pid]))
        by_fact.setdefault(fact, {}).setdefault(kind, []).append(p)

    # Direct logical contradiction: the same fact is both required and forbidden.
    for fact, kinds in by_fact.items():
        if kinds.get("REQUIRE") and kinds.get("FORBID"):
            refs = [p["id"] for p in kinds["REQUIRE"] + kinds["FORBID"]]
            issues.append(_issue("REQUIRE_FORBID_CONTRADICTION", f"fact both required and forbidden: {fact}", refs))

    # An OBSERVE fact means it is currently true. A FORBID fact means the target
    # architecture must not permit it. This is a current-state conflict, not
    # necessarily an impossible target; require an explicit migration/mitigation.
    for fact, kinds in by_fact.items():
        if kinds.get("OBSERVE") and kinds.get("FORBID"):
            mitigations = [p for p in props if isinstance(p, dict) and fact in (p.get("mitigates_facts") or [])]
            if not mitigations:
                refs = [p["id"] for p in kinds["OBSERVE"] + kinds["FORBID"]]
                issues.append(_issue("OBSERVED_FORBIDDEN_WITHOUT_MITIGATION", f"observed forbidden fact lacks mitigation: {fact}", refs))

    active = {
        fact for fact, kinds in by_fact.items()
        if kinds.get("REQUIRE") or kinds.get("ASSUME") or kinds.get("OBSERVE")
    }
    forbidden = {fact for fact, kinds in by_fact.items() if kinds.get("FORBID")}

    rule_ids: set[str] = set()
    triggered = []
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            issues.append(_issue("RULE_INVALID", f"rules[{i}] must be object")); continue
        rid = rule.get("id")
        if not isinstance(rid, str) or not rid:
            issues.append(_issue("RULE_ID_REQUIRED", f"rules[{i}] id required")); continue
        if rid in rule_ids:
            issues.append(_issue("DUPLICATE_RULE_ID", f"duplicate rule id {rid}", [rid])); continue
        rule_ids.add(rid)
        source_refs = rule.get("source_refs", [])
        if not isinstance(source_refs, list) or not source_refs:
            issues.append(_issue("RULE_PROVENANCE_REQUIRED", f"rule {rid} requires source_refs", [rid]))

        when_all = set(rule.get("when_all", []) or [])
        when_any = set(rule.get("when_any", []) or [])
        if not when_all and not when_any:
            issues.append(_issue("RULE_TRIGGER_REQUIRED", f"rule {rid} requires when_all or when_any", [rid])); continue
        fires = when_all.issubset(active) and (not when_any or bool(when_any & active))
        if not fires:
            continue
        triggered.append(rid)

        requires_all = set(rule.get("requires_all", []) or [])
        requires_any = set(rule.get("requires_any", []) or [])
        forbids_any = set(rule.get("forbids_any", []) or [])

        missing_all = sorted(x for x in requires_all if x not in active)
        if missing_all:
            issues.append(_issue("TRIGGERED_RULE_MISSING_REQUIRED_FACT", f"rule {rid} missing required facts: {missing_all}", [rid]))
        if requires_any and not (requires_any & active):
            issues.append(_issue("TRIGGERED_RULE_MISSING_REQUIRED_ALTERNATIVE", f"rule {rid} needs one of {sorted(requires_any)}", [rid]))
        conflicts = sorted(forbids_any & active)
        if conflicts:
            issues.append(_issue("TRIGGERED_RULE_FORBIDDEN_COMBINATION", f"rule {rid} conflicts with active facts: {conflicts}", [rid]))

        # A required consequence that is explicitly forbidden is stronger than
        # merely missing: the current proposition set is internally inconsistent.
        required = requires_all | requires_any
        contradictory = sorted(required & forbidden)
        if contradictory:
            issues.append(_issue("RULE_CONSEQUENCE_EXPLICITLY_FORBIDDEN", f"rule {rid} requires facts explicitly forbidden: {contradictory}", [rid]))

    error_codes = [x["code"] for x in issues]
    return {
        "ledger_id": obj.get("ledger_id"),
        "gate_passed": not issues,
        "active_facts": sorted(active),
        "forbidden_facts": sorted(forbidden),
        "triggered_rule_ids": sorted(triggered),
        "issue_count": len(issues),
        "issues": issues,
        "error_codes": sorted(set(error_codes)),
        "claim_boundary": (
            "Deterministic consistency over supplied typed propositions/rules only. "
            "The engine does not prove that the semantic layer extracted the right facts or that the rule set is complete."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("ledger", type=Path)
    p.add_argument("--require-pass", action="store_true")
    args = p.parse_args()
    obj = json.loads(args.ledger.read_text(encoding="utf-8"))
    result = validate(obj)
    print(json.dumps(result, indent=2))
    if args.require_pass and not result["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
