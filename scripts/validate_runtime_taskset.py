#!/usr/bin/env python3
"""Validate frozen ACE-S runtime taskset manifests."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(obj: dict) -> dict:
    if obj.get("schema_version") != "0.1":
        raise ValueError("schema_version must be 0.1")
    if not nonempty(obj.get("suite_id")):
        raise ValueError("suite_id is required")
    if obj.get("status") != "frozen_before_runtime_execution":
        raise ValueError("status must be frozen_before_runtime_execution")
    tasks = obj.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks must be a non-empty array")

    seen = set()
    repos = set()
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError(f"task {i}: must be object")
        task_id = task.get("task_id")
        if not nonempty(task_id) or task_id in seen:
            raise ValueError(f"task {i}: task_id must be unique non-empty string")
        seen.add(task_id)
        repo = task.get("repository")
        if not isinstance(repo, str) or not REPO.fullmatch(repo):
            raise ValueError(f"task {task_id}: repository must be owner/name")
        repos.add(repo)
        sha = task.get("commit_sha")
        if not isinstance(sha, str) or not SHA40.fullmatch(sha):
            raise ValueError(f"task {task_id}: commit_sha must be lowercase 40-hex SHA")
        if not nonempty(task.get("prompt")):
            raise ValueError(f"task {task_id}: prompt is required")
        expected = task.get("expected_file")
        if not nonempty(expected) or str(expected).startswith("/") or ".." in Path(str(expected)).parts:
            raise ValueError(f"task {task_id}: expected_file must be safe repository-relative path")

    if not nonempty(obj.get("freeze_rule")):
        raise ValueError("freeze_rule is required")
    return {"status": "valid", "suite_id": obj["suite_id"], "tasks": len(tasks), "repositories": len(repos)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        obj = json.loads(args.manifest.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("manifest root must be object")
        print(json.dumps(validate(obj), indent=2))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
