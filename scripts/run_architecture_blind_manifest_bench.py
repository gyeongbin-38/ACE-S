#!/usr/bin/env python3
"""Calibrate opaque condition blinding for architecture benchmark candidates."""
from __future__ import annotations

import json

from architecture_blind_manifest import blind


def main():
    manifest={
        "benchmark_id":"blind-control",
        "replicates":2,
        "conditions":[
            {"id":"A_DIRECT","prompt_path":"A.md"},
            {"id":"D_PROOF","prompt_path":"D.md"},
        ],
        "tasks":[
            {"task_id":"p1","requirements":["R1"],"hidden_reference":"must-not-leak"},
            {"task_id":"p2","requirements":["R2"],"reference_path":"secret/ref.json"},
        ],
    }
    public,private=blind(manifest,"unit-test-secret-salt")
    public_text=json.dumps(public,sort_keys=True)
    private_text=json.dumps(private,sort_keys=True)
    ids=[x["candidate_id"] for x in public["candidates"]]
    checks={
        "candidate_count":len(ids)==8,
        "unique_ids":len(ids)==len(set(ids)),
        "opaque_prefix":all(x.startswith("cand-") and len(x)==21 for x in ids),
        "condition_hidden_public":"A_DIRECT" not in public_text and "D_PROOF" not in public_text,
        "prompt_path_hidden_public":"A.md" not in public_text and "D.md" not in public_text,
        "hidden_reference_removed":"must-not-leak" not in public_text and "secret/ref.json" not in public_text,
        "private_mapping_complete":len(private["mapping"])==8 and "A_DIRECT" in private_text and "D_PROOF" in private_text,
        "stable_same_salt":blind(manifest,"unit-test-secret-salt")[0]==public,
        "different_salt_changes_ids":{x["candidate_id"] for x in blind(manifest,"different-salt")[0]["candidates"]}!=set(ids),
    }
    report={
        "suite_id":"architecture-blind-manifest-v0.1",
        "passed":all(checks.values()),
        "checks":checks,
        "claim_boundary":"Authored manifest verifies pseudonymous condition/reference hiding semantics only. Operational blinding still requires salt/private mapping isolation from models and reviewers."
    }
    print(json.dumps(report,indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__=="__main__":
    main()
