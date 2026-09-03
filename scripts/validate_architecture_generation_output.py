#!/usr/bin/env python3
"""Validate the common final artifact emitted by all architecture benchmark conditions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

NODE_KINDS = {"COMPONENT", "DATA_STORE", "EXTERNAL_SYSTEM", "ACTOR"}
EDGE_RELATIONS = {"CALLS", "READS", "WRITES", "PUBLISHES", "SUBSCRIBES", "AUTHENTICATES", "AUTHORIZES", "ROUTES", "REPLICATES", "OTHER"}
BOUNDARY_KINDS = {"MODULE", "PROCESS", "SERVICE", "SYSTEM", "TRUST", "DATA"}


def issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code":code,"path":path,"message":message}


def nonempty(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def validate(obj: dict[str, Any], allowed_requirement_ids: set[str] | None = None) -> dict[str, Any]:
    issues = []
    arch = obj.get("architecture")
    if not isinstance(arch, dict):
        return {"gate_passed":False,"issues":[issue("ARCHITECTURE_REQUIRED","architecture","architecture object required")]}

    nodes = arch.get("nodes", [])
    if not isinstance(nodes, list) or not nodes:
        issues.append(issue("NODES_REQUIRED","architecture.nodes","non-empty nodes array required")); nodes=[]
    ids = set()
    node_by_id = {}
    for i,n in enumerate(nodes):
        if not isinstance(n,dict):
            issues.append(issue("NODE_INVALID",f"architecture.nodes[{i}]","node must be object")); continue
        nid=n.get("id")
        if not nonempty(nid):
            issues.append(issue("NODE_ID_REQUIRED",f"architecture.nodes[{i}].id","node id required")); continue
        if nid in ids:
            issues.append(issue("DUPLICATE_NODE_ID",f"architecture.nodes[{i}].id",f"duplicate node id {nid}")); continue
        ids.add(nid); node_by_id[nid]=n
        if n.get("kind") not in NODE_KINDS:
            issues.append(issue("NODE_KIND_INVALID",f"architecture.nodes[{i}].kind","invalid node kind"))
        if not nonempty(n.get("name")) or not nonempty(n.get("responsibility")):
            issues.append(issue("NODE_DESCRIPTION_REQUIRED",f"architecture.nodes[{i}]","node name/responsibility required"))

    edges = arch.get("edges", [])
    if not isinstance(edges,list):
        issues.append(issue("EDGES_INVALID","architecture.edges","edges must be array")); edges=[]
    edge_keys=set()
    for i,e in enumerate(edges):
        if not isinstance(e,dict):
            issues.append(issue("EDGE_INVALID",f"architecture.edges[{i}]","edge must be object")); continue
        src,dst,rel=e.get("from"),e.get("to"),e.get("relation")
        if src not in ids or dst not in ids:
            issues.append(issue("EDGE_ENDPOINT_UNKNOWN",f"architecture.edges[{i}]","edge endpoints must reference emitted nodes"))
        if rel not in EDGE_RELATIONS:
            issues.append(issue("EDGE_RELATION_INVALID",f"architecture.edges[{i}].relation","invalid edge relation"))
        key=(src,rel,dst)
        if key in edge_keys:
            issues.append(issue("DUPLICATE_EDGE",f"architecture.edges[{i}]",f"duplicate edge {key}"))
        edge_keys.add(key)
        if not nonempty(e.get("contract")):
            issues.append(issue("EDGE_CONTRACT_REQUIRED",f"architecture.edges[{i}].contract","interaction contract required"))

    states = arch.get("state", [])
    if not isinstance(states,list):
        issues.append(issue("STATE_INVALID","architecture.state","state must be array")); states=[]
    for i,s in enumerate(states):
        if not isinstance(s,dict):
            issues.append(issue("STATE_RECORD_INVALID",f"architecture.state[{i}]","state must be object")); continue
        owner=s.get("owner")
        if not nonempty(s.get("name")):
            issues.append(issue("STATE_NAME_REQUIRED",f"architecture.state[{i}].name","state name required"))
        if not nonempty(owner):
            issues.append(issue("STATE_OWNER_REQUIRED",f"architecture.state[{i}].owner","state owner or explicit multi-writer protocol required"))
        elif owner not in ids and not any(k in owner.lower() for k in ("multi-writer","multiwriter","protocol","crdt","consensus")):
            issues.append(issue("STATE_OWNER_UNKNOWN",f"architecture.state[{i}].owner","owner must be node id or explicit multi-writer protocol"))
        if not nonempty(s.get("consistency")):
            issues.append(issue("STATE_CONSISTENCY_REQUIRED",f"architecture.state[{i}].consistency","consistency semantics required"))
        if not nonempty(s.get("recovery")):
            issues.append(issue("STATE_RECOVERY_REQUIRED",f"architecture.state[{i}].recovery","recovery mechanism required"))

    boundaries=arch.get("boundaries",[])
    if not isinstance(boundaries,list):
        issues.append(issue("BOUNDARIES_INVALID","architecture.boundaries","boundaries must be array")); boundaries=[]
    for i,b in enumerate(boundaries):
        if not isinstance(b,dict):
            issues.append(issue("BOUNDARY_INVALID",f"architecture.boundaries[{i}]","boundary must be object")); continue
        between=b.get("between")
        if not isinstance(between,list) or len(between)!=2 or any(x not in ids for x in between):
            issues.append(issue("BOUNDARY_ENDPOINT_INVALID",f"architecture.boundaries[{i}].between","boundary must connect two emitted nodes"))
        if b.get("kind") not in BOUNDARY_KINDS:
            issues.append(issue("BOUNDARY_KIND_INVALID",f"architecture.boundaries[{i}].kind","invalid boundary kind"))
        if not isinstance(b.get("drivers"),list) or not b.get("drivers"):
            issues.append(issue("BOUNDARY_DRIVER_REQUIRED",f"architecture.boundaries[{i}].drivers","boundary requires at least one driver"))

    trace=obj.get("requirement_traceability",[])
    if not isinstance(trace,list):
        issues.append(issue("TRACEABILITY_INVALID","requirement_traceability","must be array")); trace=[]
    seen_req=set()
    for i,t in enumerate(trace):
        if not isinstance(t,dict):
            issues.append(issue("TRACEABILITY_RECORD_INVALID",f"requirement_traceability[{i}]","record must be object")); continue
        rid=t.get("requirement_id")
        if not nonempty(rid):
            issues.append(issue("TRACEABILITY_REQUIREMENT_ID_REQUIRED",f"requirement_traceability[{i}].requirement_id","requirement id required"))
        elif allowed_requirement_ids is not None and rid not in allowed_requirement_ids:
            issues.append(issue("TRACEABILITY_UNKNOWN_REQUIREMENT",f"requirement_traceability[{i}].requirement_id",f"unknown input requirement id {rid}"))
        if rid in seen_req:
            issues.append(issue("DUPLICATE_REQUIREMENT_TRACE",f"requirement_traceability[{i}]",f"duplicate requirement trace {rid}"))
        seen_req.add(rid)
        mids=t.get("mechanism_node_ids",[])
        if not isinstance(mids,list) or not mids or any(x not in ids for x in mids):
            issues.append(issue("TRACEABILITY_MECHANISM_INVALID",f"requirement_traceability[{i}].mechanism_node_ids","mechanism ids must be non-empty emitted node ids"))
        if not nonempty(t.get("mechanism")) or not nonempty(t.get("fitness_check")):
            issues.append(issue("TRACEABILITY_MECHANISM_CHECK_REQUIRED",f"requirement_traceability[{i}]","mechanism and fitness_check required"))

    decisions=obj.get("decisions",[])
    if not isinstance(decisions,list):
        issues.append(issue("DECISIONS_INVALID","decisions","decisions must be array")); decisions=[]
    decision_ids=set()
    for i,d in enumerate(decisions):
        if not isinstance(d,dict):
            issues.append(issue("DECISION_INVALID",f"decisions[{i}]","decision must be object")); continue
        did=d.get("id")
        if not nonempty(did) or did in decision_ids:
            issues.append(issue("DECISION_ID_INVALID",f"decisions[{i}].id","unique decision id required"))
        else: decision_ids.add(did)
        if not nonempty(d.get("choice")) or not isinstance(d.get("drivers"),list) or not d.get("drivers"):
            issues.append(issue("DECISION_DRIVER_REQUIRED",f"decisions[{i}]","choice and drivers required"))
        if not nonempty(d.get("reversal_condition")):
            issues.append(issue("DECISION_REVERSAL_REQUIRED",f"decisions[{i}].reversal_condition","reversal condition required"))

    risks=obj.get("risks",[])
    if not isinstance(risks,list):
        issues.append(issue("RISKS_INVALID","risks","risks must be array")); risks=[]
    for i,r in enumerate(risks):
        if not isinstance(r,dict):
            issues.append(issue("RISK_INVALID",f"risks[{i}]","risk must be object")); continue
        affected=r.get("affected_ids",[])
        allowed=ids|decision_ids
        if not nonempty(r.get("id")) or not nonempty(r.get("description")):
            issues.append(issue("RISK_FIELDS_REQUIRED",f"risks[{i}]","risk id/description required"))
        if not isinstance(affected,list) or any(x not in allowed for x in affected):
            issues.append(issue("RISK_AFFECTED_IDS_INVALID",f"risks[{i}].affected_ids","risk affected ids must reference node/decision ids"))
        if not nonempty(r.get("mitigation_or_next_evidence")):
            issues.append(issue("RISK_MITIGATION_REQUIRED",f"risks[{i}].mitigation_or_next_evidence","bounded mitigation/next evidence required"))

    return {
        "gate_passed":not issues,
        "node_count":len(ids),
        "edge_count":len(edge_keys),
        "trace_count":len(trace),
        "decision_count":len(decision_ids),
        "issue_count":len(issues),
        "error_codes":sorted({x["code"] for x in issues}),
        "issues":issues,
        "claim_boundary":"Common artifact schema/referential-integrity validation only; passing does not prove architecture quality or requirement completeness.",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("output",type=Path)
    p.add_argument("--requirements",type=Path,help="JSON array/object containing allowed requirement ids")
    p.add_argument("--require-pass",action="store_true")
    args=p.parse_args()
    obj=json.loads(args.output.read_text(encoding="utf-8"))
    allowed=None
    if args.requirements:
        r=json.loads(args.requirements.read_text(encoding="utf-8"))
        values=r if isinstance(r,list) else r.get("requirements",[])
        allowed={x["id"] if isinstance(x,dict) else x for x in values}
    result=validate(obj,allowed)
    print(json.dumps(result,indent=2))
    if args.require_pass and not result["gate_passed"]:
        raise SystemExit(1)


if __name__=="__main__":
    main()
