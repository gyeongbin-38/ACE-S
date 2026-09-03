#!/usr/bin/env python3
"""Calibrate deterministic architecture constraint-ledger semantics."""
from __future__ import annotations

import copy
import json

from architecture_constraint_ledger import validate


def prop(pid, fact, kind="REQUIRE", status="ACCEPTED_INTENT", **extra):
    return {"id":pid,"fact":fact,"kind":kind,"evidence_status":status,**extra}


def main():
    rule = {
        "id":"independent-deploy-needs-remote-contract",
        "source_refs":["asr-independent-deployment"],
        "when_all":["independent_deployment"],
        "requires_any":["remote_contract","async_contract"],
        "forbids_any":["shared_in_process_atomic_transaction"],
    }
    base = {
        "ledger_id":"valid",
        "propositions":[
            prop("p1","independent_deployment"),
            prop("p2","remote_contract"),
        ],
        "rules":[rule],
    }
    cases = [("valid-remote-contract", base, True, set())]

    x = copy.deepcopy(base)
    x["ledger_id"] = "missing-contract"
    x["propositions"] = [prop("p1","independent_deployment")]
    cases.append(("missing-required-alternative", x, False, {"TRIGGERED_RULE_MISSING_REQUIRED_ALTERNATIVE"}))

    x = copy.deepcopy(base)
    x["ledger_id"] = "distributed-transaction-conflict"
    x["propositions"].append(prop("p3","shared_in_process_atomic_transaction"))
    cases.append(("forbidden-combination", x, False, {"TRIGGERED_RULE_FORBIDDEN_COMBINATION"}))

    x = copy.deepcopy(base)
    x["ledger_id"] = "direct-contradiction"
    x["propositions"].append(prop("p4","remote_contract",kind="FORBID"))
    cases.append(("require-forbid", x, False, {"REQUIRE_FORBID_CONTRADICTION"}))

    # Existing-system redesign: an observed current-state violation may be
    # accepted only if there is an explicit migration/mitigation proposition.
    x = {
        "ledger_id":"observed-forbidden-no-migration",
        "propositions":[
            prop("o1","shared_database",kind="OBSERVE",status="OBSERVED"),
            prop("f1","shared_database",kind="FORBID"),
        ],
        "rules":[],
    }
    cases.append(("observed-forbidden-no-mitigation", x, False, {"OBSERVED_FORBIDDEN_WITHOUT_MITIGATION"}))

    x2 = copy.deepcopy(x)
    x2["ledger_id"] = "observed-forbidden-with-migration"
    x2["propositions"].append(prop("m1","split_database_migration",kind="REQUIRE",mitigates_facts=["shared_database"]))
    # The OBSERVE+FORBID pair is intentionally not treated as logical impossibility;
    # it represents current-state drift plus a target constraint when migration exists.
    cases.append(("observed-forbidden-with-mitigation", x2, True, set()))

    rows, failed = [], []
    for cid, ledger, expected_pass, expected_codes in cases:
        result = validate(ledger)
        actual = set(result.get("error_codes", []))
        ok = result.get("gate_passed") == expected_pass and expected_codes.issubset(actual)
        row = {"id":cid,"passed":ok,"gate_passed":result.get("gate_passed"),"expected":sorted(expected_codes),"actual":sorted(actual)}
        rows.append(row)
        if not ok:
            failed.append({"row":row,"result":result})

    report = {
        "suite_id":"architecture-constraint-ledger-v0.1",
        "cases":len(rows),
        "passed":sum(1 for x in rows if x["passed"]),
        "failed":len(failed),
        "rows":rows,
        "claim_boundary":"Authored typed proposition/rule fixtures validate deterministic consistency semantics only; they do not validate semantic extraction or rule completeness.",
    }
    print(json.dumps(report,indent=2))
    if failed:
        print(json.dumps({"failures":failed},indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
