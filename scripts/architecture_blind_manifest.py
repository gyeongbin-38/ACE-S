#!/usr/bin/env python3
"""Create evaluator-visible opaque candidate IDs and a private condition mapping.

The public manifest contains task/candidate identifiers but no benchmark
condition/model labels. The private mapping is evaluator-orchestrator metadata
and must not be shown to human reviewers or condition-blind scoring passes.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any


def opaque_id(salt: str, task_id: str, condition: str, replicate: int) -> str:
    msg = f"{task_id}\0{condition}\0{replicate}".encode("utf-8")
    digest = hmac.new(salt.encode("utf-8"), msg, hashlib.sha256).hexdigest()[:16]
    return f"cand-{digest}"


def blind(manifest: dict[str, Any], salt: str) -> tuple[dict[str, Any], dict[str, Any]]:
    conditions = manifest.get("conditions", [])
    tasks = manifest.get("tasks", [])
    replicates = int(manifest.get("replicates", 1))
    if not isinstance(conditions, list) or not conditions:
        raise ValueError("conditions must be a non-empty array")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks must be a non-empty array")
    if replicates < 1:
        raise ValueError("replicates must be >=1")

    public_candidates = []
    private_rows = []
    seen = set()
    for task in tasks:
        if not isinstance(task, dict) or not isinstance(task.get("task_id"), str):
            raise ValueError("each task requires task_id")
        tid = task["task_id"]
        public_task = {k:v for k,v in task.items() if k not in {"hidden_reference","reference_path","condition"}}
        for condition in conditions:
            if not isinstance(condition, dict) or not isinstance(condition.get("id"), str):
                raise ValueError("each condition requires id")
            cid = condition["id"]
            for rep in range(replicates):
                oid = opaque_id(salt, tid, cid, rep)
                if oid in seen:
                    raise ValueError("opaque candidate collision")
                seen.add(oid)
                public_candidates.append({
                    "candidate_id": oid,
                    "task_id": tid,
                    "replicate": rep,
                    "task": public_task,
                })
                private_rows.append({
                    "candidate_id": oid,
                    "task_id": tid,
                    "condition_id": cid,
                    "condition_prompt_path": condition.get("prompt_path"),
                    "replicate": rep,
                })

    public = {
        "schema_version":"0.1",
        "benchmark_id":manifest.get("benchmark_id"),
        "candidates":sorted(public_candidates,key=lambda x:x["candidate_id"]),
        "blinding":"condition/model identity absent from evaluator-visible manifest",
    }
    private = {
        "schema_version":"0.1",
        "benchmark_id":manifest.get("benchmark_id"),
        "mapping":sorted(private_rows,key=lambda x:x["candidate_id"]),
        "sensitive":"EVALUATOR_ORCHESTRATOR_ONLY",
    }
    return public,private


def main():
    p=argparse.ArgumentParser()
    p.add_argument("manifest",type=Path)
    p.add_argument("--salt",required=True)
    p.add_argument("--public-out",type=Path,required=True)
    p.add_argument("--private-out",type=Path,required=True)
    args=p.parse_args()
    obj=json.loads(args.manifest.read_text(encoding="utf-8"))
    public,private=blind(obj,args.salt)
    args.public_out.write_text(json.dumps(public,indent=2)+"\n",encoding="utf-8")
    args.private_out.write_text(json.dumps(private,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"public_candidates":len(public["candidates"]),"private_mappings":len(private["mapping"]),"claim_boundary":"Deterministic pseudonymous blinding only; secrecy depends on keeping the salt/private mapping outside reviewer/model context."},indent=2))


if __name__=="__main__":
    main()
