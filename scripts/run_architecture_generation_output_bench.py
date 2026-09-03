#!/usr/bin/env python3
"""Calibrate common architecture benchmark output-contract validation."""
from __future__ import annotations

import copy
import json

from validate_architecture_generation_output import validate


def valid_output():
    return {
        "architecture": {
            "nodes": [
                {"id":"api","kind":"COMPONENT","name":"API","responsibility":"receive checkout commands"},
                {"id":"domain","kind":"COMPONENT","name":"Checkout Domain","responsibility":"enforce checkout invariants"},
                {"id":"store","kind":"DATA_STORE","name":"Order Store","responsibility":"persist authoritative orders"},
            ],
            "edges": [
                {"from":"api","to":"domain","relation":"CALLS","contract":"PlaceOrder command"},
                {"from":"domain","to":"store","relation":"WRITES","contract":"OrderRepository transaction"},
            ],
            "state": [
                {"name":"orders","owner":"store","consistency":"serializable per order","recovery":"restore snapshot and replay idempotent journal"}
            ],
            "boundaries": [
                {"between":["api","domain"],"kind":"MODULE","drivers":["asr-change-isolation"],"enforcement_or_mitigation":"public command contract"}
            ],
        },
        "requirement_traceability": [
            {"requirement_id":"asr-change-isolation","mechanism_node_ids":["api","domain"],"mechanism":"stable command boundary localizes API churn","fitness_check":"architecture dependency test"}
        ],
        "decisions": [
            {"id":"d1","choice":"keep transactional domain/store close","drivers":["asr-correctness"],"alternatives":["split store service"],"accepted_tradeoffs":["single deploy scaling"],"reversal_condition":"independent scale becomes required"}
        ],
        "risks": [
            {"id":"r1","description":"write hotspot may emerge","affected_ids":["store","d1"],"mitigation_or_next_evidence":"measure peak write contention"}
        ],
    }


def main():
    allowed={"asr-change-isolation","asr-correctness"}
    base=valid_output()
    cases=[("valid",base,True,set())]

    x=copy.deepcopy(base)
    x["architecture"]["edges"][0]["to"]="ghost"
    cases.append(("dangling-edge",x,False,{"EDGE_ENDPOINT_UNKNOWN"}))

    x=copy.deepcopy(base)
    x["requirement_traceability"][0]["requirement_id"]="invented-asr"
    cases.append(("invented-requirement",x,False,{"TRACEABILITY_UNKNOWN_REQUIREMENT"}))

    x=copy.deepcopy(base)
    x["architecture"]["state"][0]["owner"]=""
    cases.append(("ownerless-state",x,False,{"STATE_OWNER_REQUIRED"}))

    x=copy.deepcopy(base)
    x["architecture"]["boundaries"][0]["drivers"]=[]
    cases.append(("driverless-boundary",x,False,{"BOUNDARY_DRIVER_REQUIRED"}))

    x=copy.deepcopy(base)
    x["decisions"][0]["reversal_condition"]=""
    cases.append(("decision-no-reversal",x,False,{"DECISION_REVERSAL_REQUIRED"}))

    rows=[]; failed=[]
    for cid,obj,expected_pass,expected_codes in cases:
        r=validate(obj,allowed)
        actual=set(r["error_codes"])
        ok=r["gate_passed"]==expected_pass and expected_codes.issubset(actual)
        row={"id":cid,"passed":ok,"gate_passed":r["gate_passed"],"expected":sorted(expected_codes),"actual":sorted(actual)}
        rows.append(row)
        if not ok: failed.append({"row":row,"result":r})

    report={
        "suite_id":"architecture-generation-output-v0.1",
        "cases":len(rows),"passed":sum(1 for x in rows if x["passed"]),"failed":len(failed),"rows":rows,
        "claim_boundary":"Authored output fixtures validate common schema/referential-integrity semantics only; they do not measure architecture-generation quality."
    }
    print(json.dumps(report,indent=2))
    if failed:
        print(json.dumps({"failures":failed},indent=2)); raise SystemExit(1)


if __name__=="__main__":
    main()
