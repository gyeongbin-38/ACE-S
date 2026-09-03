#!/usr/bin/env python3
"""Calibrate architecture evaluation freeze/leakage governance semantics."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path

from validate_architecture_eval_bundle import validate


def sha(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def main() -> None:
    contents = {
        "method.txt": "proof-carrying method v1\n",
        "evaluator.txt": "edge-f1 evaluator v1\n",
        "prompt.txt": "generate architecture from visible requirements\n",
        "tasks.json": '{"sealed":["p3","p4"]}\n',
        "model.json": '{"model":"same-model","temperature":0}\n',
        "reference.json": '{"p3":"hidden-reference"}\n',
    }
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for path, data in contents.items():
            (root / path).write_text(data, encoding="utf-8")

        base = {
            "bundle_id": "architecture-sealed-bundle-control",
            "benchmark_version": "0.1",
            "status": "FROZEN_BEFORE_SEALED_EXECUTION",
            "development_project_ids": ["p1", "p2"],
            "sealed_project_ids": ["p3", "p4"],
            "reference_hidden_from_generator": True,
            "allow_post_sealed_method_mutation": False,
            "maximum_claim_before_results": "EXPERIMENTAL",
            "generator_input_groups": ["method_files", "generator_prompt_files", "task_manifest_files", "model_config_files"],
            "files": [
                {"path":"method.txt","role":"GENERATOR_VISIBLE","group":"method_files","sha256":sha(contents["method.txt"])},
                {"path":"evaluator.txt","role":"EVALUATOR_ONLY","group":"evaluator_files","sha256":sha(contents["evaluator.txt"])},
                {"path":"prompt.txt","role":"GENERATOR_VISIBLE","group":"generator_prompt_files","sha256":sha(contents["prompt.txt"])},
                {"path":"tasks.json","role":"GENERATOR_VISIBLE","group":"task_manifest_files","sha256":sha(contents["tasks.json"])},
                {"path":"model.json","role":"PUBLIC_METADATA","group":"model_config_files","sha256":sha(contents["model.json"])},
                {"path":"reference.json","role":"EVALUATOR_ONLY","group":"hidden_reference_files","sha256":sha(contents["reference.json"])},
            ],
        }

        cases = []
        cases.append(("valid-frozen-bundle", copy.deepcopy(base), True, set()))

        b = copy.deepcopy(base)
        b["sealed_project_ids"].append("p2")
        cases.append(("project-overlap", b, False, {"DEV_SEALED_PROJECT_OVERLAP"}))

        b = copy.deepcopy(base)
        for e in b["files"]:
            if e["path"] == "method.txt":
                e["sha256"] = "0" * 64
        cases.append(("method-hash-mismatch", b, False, {"FROZEN_FILE_HASH_MISMATCH"}))

        b = copy.deepcopy(base)
        for e in b["files"]:
            if e["path"] == "reference.json":
                e["role"] = "GENERATOR_VISIBLE"
        b["generator_input_groups"].append("hidden_reference_files")
        cases.append((
            "reference-leakage", b, False,
            {"HIDDEN_REFERENCE_NOT_EVALUATOR_ONLY", "HIDDEN_REFERENCE_IN_GENERATOR_INPUT"},
        ))

        b = copy.deepcopy(base)
        b["status"] = "SEALED_RESULTS_ALREADY_OBSERVED"
        cases.append(("late-freeze", b, False, {"NOT_FROZEN_BEFORE_EXECUTION"}))

        b = copy.deepcopy(base)
        b["maximum_claim_before_results"] = "PUBLIC_BEST_OR_SOTA_CANDIDATE"
        cases.append(("premature-claim", b, False, {"PRE_RESULT_CLAIM_TOO_STRONG"}))

        rows, failed = [], []
        for cid, bundle, expected_pass, expected_codes in cases:
            result = validate(bundle, root)
            actual = {x["code"] for x in result["errors"]}
            ok = result["gate_passed"] == expected_pass and expected_codes.issubset(actual)
            row = {
                "id": cid,
                "passed": ok,
                "gate_passed": result["gate_passed"],
                "expected_error_codes": sorted(expected_codes),
                "actual_error_codes": sorted(actual),
            }
            rows.append(row)
            if not ok:
                failed.append({"row": row, "result": result})

        report = {
            "suite_id": "architecture-eval-freeze-bundle-v0.1",
            "cases": len(rows),
            "passed": sum(1 for x in rows if x["passed"]),
            "failed": len(failed),
            "rows": rows,
            "claim_boundary": "Temporary authored files validate freeze/leakage governance only; no model benchmark or dataset independence claim is implied.",
        }
        print(json.dumps(report, indent=2))
        if failed:
            print(json.dumps({"failures": failed}, indent=2))
            raise SystemExit(1)


if __name__ == "__main__":
    main()
