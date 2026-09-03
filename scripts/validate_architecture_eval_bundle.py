#!/usr/bin/env python3
"""Validate a sealed architecture-synthesis evaluation freeze bundle.

The bundle separates generator-visible task inputs from evaluator-only hidden
references and freezes method/evaluator/config/task membership before execution.
This validates governance metadata; it does not execute models or score quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ALLOWED_ROLES = {"GENERATOR_VISIBLE", "EVALUATOR_ONLY", "PUBLIC_METADATA"}
REQUIRED_GROUPS = {
    "method_files",
    "evaluator_files",
    "generator_prompt_files",
    "task_manifest_files",
    "model_config_files",
}


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def issue(code: str, message: str, path: str | None = None) -> dict[str, Any]:
    out = {"code": code, "message": message}
    if path is not None:
        out["path"] = path
    return out


def validate(bundle: dict[str, Any], root: Path) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if bundle.get("status") != "FROZEN_BEFORE_SEALED_EXECUTION":
        errors.append(issue("NOT_FROZEN_BEFORE_EXECUTION", "status must be FROZEN_BEFORE_SEALED_EXECUTION"))
    if not bundle.get("bundle_id"):
        errors.append(issue("BUNDLE_ID_REQUIRED", "bundle_id is required"))
    if not bundle.get("benchmark_version"):
        errors.append(issue("BENCHMARK_VERSION_REQUIRED", "benchmark_version is required"))
    if bundle.get("development_project_ids") is None or bundle.get("sealed_project_ids") is None:
        errors.append(issue("PROJECT_SPLITS_REQUIRED", "development_project_ids and sealed_project_ids are required"))
    else:
        dev = set(bundle.get("development_project_ids", []))
        sealed = set(bundle.get("sealed_project_ids", []))
        overlap = sorted(dev & sealed)
        if overlap:
            errors.append(issue("DEV_SEALED_PROJECT_OVERLAP", f"development/sealed overlap: {overlap}"))
        if not sealed:
            errors.append(issue("SEALED_PROJECT_SET_EMPTY", "sealed project set must be non-empty"))

    files = bundle.get("files", [])
    if not isinstance(files, list) or not files:
        errors.append(issue("FILES_REQUIRED", "files must be a non-empty array"))
        files = []

    seen_paths: set[str] = set()
    groups_seen: set[str] = set()
    visible_paths: set[str] = set()
    hidden_paths: set[str] = set()
    rows = []

    for i, entry in enumerate(files):
        if not isinstance(entry, dict):
            errors.append(issue("FILE_ENTRY_INVALID", f"files[{i}] must be object"))
            continue
        rel = entry.get("path")
        role = entry.get("role")
        group = entry.get("group")
        expected = entry.get("sha256")
        if not isinstance(rel, str) or not rel:
            errors.append(issue("FILE_PATH_REQUIRED", f"files[{i}] path required"))
            continue
        if rel in seen_paths:
            errors.append(issue("DUPLICATE_FROZEN_PATH", f"duplicate frozen path {rel}", rel))
        seen_paths.add(rel)
        if role not in ALLOWED_ROLES:
            errors.append(issue("FILE_ROLE_INVALID", f"invalid role {role}", rel))
        if isinstance(group, str):
            groups_seen.add(group)
        else:
            errors.append(issue("FILE_GROUP_REQUIRED", "group is required", rel))
        if not isinstance(expected, str) or len(expected) != 64:
            errors.append(issue("FILE_SHA256_REQUIRED", "64-char sha256 required", rel))
            expected = None

        path = root / rel
        if not path.is_file():
            errors.append(issue("FROZEN_FILE_MISSING", "frozen file missing", rel))
            actual = None
        else:
            actual = sha256_path(path)
            if expected is not None and actual != expected:
                errors.append(issue("FROZEN_FILE_HASH_MISMATCH", f"expected {expected}, actual {actual}", rel))

        if role == "GENERATOR_VISIBLE":
            visible_paths.add(rel)
        elif role == "EVALUATOR_ONLY":
            hidden_paths.add(rel)

        rows.append({"path": rel, "role": role, "group": group, "sha256_matches": actual == expected if actual and expected else False})

    missing_groups = sorted(REQUIRED_GROUPS - groups_seen)
    if missing_groups:
        errors.append(issue("REQUIRED_FREEZE_GROUP_MISSING", f"missing groups: {missing_groups}"))

    leakage = sorted(visible_paths & hidden_paths)
    if leakage:
        errors.append(issue("REFERENCE_VISIBILITY_LEAK", f"paths assigned both generator-visible and evaluator-only: {leakage}"))

    hidden_reference_paths = {
        e.get("path") for e in files
        if isinstance(e, dict) and e.get("group") == "hidden_reference_files"
    }
    for p in sorted(x for x in hidden_reference_paths if isinstance(x, str)):
        role = next((e.get("role") for e in files if isinstance(e, dict) and e.get("path") == p), None)
        if role != "EVALUATOR_ONLY":
            errors.append(issue("HIDDEN_REFERENCE_NOT_EVALUATOR_ONLY", "hidden reference must be evaluator-only", p))

    generator_inputs = bundle.get("generator_input_groups", [])
    if not isinstance(generator_inputs, list):
        errors.append(issue("GENERATOR_INPUT_GROUPS_INVALID", "generator_input_groups must be an array"))
        generator_inputs = []
    if "hidden_reference_files" in generator_inputs:
        errors.append(issue("HIDDEN_REFERENCE_IN_GENERATOR_INPUT", "hidden references cannot be generator inputs"))

    if bundle.get("reference_hidden_from_generator") is not True:
        errors.append(issue("REFERENCE_HIDING_NOT_ASSERTED", "reference_hidden_from_generator must be true"))
    if bundle.get("allow_post_sealed_method_mutation") is not False:
        errors.append(issue("POST_SEALED_MUTATION_MUST_BE_FALSE", "allow_post_sealed_method_mutation must be false"))

    claim_level = bundle.get("maximum_claim_before_results")
    if claim_level not in {"EXPERIMENTAL", "NONE"}:
        errors.append(issue("PRE_RESULT_CLAIM_TOO_STRONG", "maximum_claim_before_results must be EXPERIMENTAL or NONE"))

    return {
        "bundle_id": bundle.get("bundle_id"),
        "gate_passed": not errors,
        "frozen_files": len(rows),
        "development_projects": len(bundle.get("development_project_ids", []) or []),
        "sealed_projects": len(bundle.get("sealed_project_ids", []) or []),
        "rows": rows,
        "errors": errors,
        "warnings": warnings,
        "claim_boundary": (
            "Freeze/leakage governance only. Passing proves that declared local inputs match their hashes and "
            "that the bundle separates generator-visible from evaluator-only files; it does not prove benchmark "
            "independence outside the declared files or architecture quality."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("bundle", type=Path)
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--require-pass", action="store_true")
    args = p.parse_args()
    obj = json.loads(args.bundle.read_text(encoding="utf-8"))
    result = validate(obj, args.root)
    print(json.dumps(result, indent=2))
    if args.require_pass and not result["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
