#!/usr/bin/env python3
"""Invariant-only wrapper for discover_repo_frontier_v02.py.

The first run failed before policy evaluation because git-grep output contained a
non-UTF8 byte. This wrapper changes decoding only; candidate policies, tasksets,
metrics, and selection rules are unchanged.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import discover_repo_frontier_v02 as m


def decode_safe_grep(repo: Path, terms: list[tuple[str, float, bool]]) -> tuple[str, int]:
    if not terms:
        return "", 0
    cmd = ["git", "grep", "-n", "-I", "-i"]
    for term, _, _ in terms:
        cmd.extend(["-e", term])
    cmd.extend(["--", ":(exclude)*.lock"])
    cp = subprocess.run(
        cmd,
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if cp.returncode not in {0, 1}:
        raise RuntimeError(cp.stderr.decode("utf-8", errors="replace")[-1000:])
    raw = cp.stdout.decode("utf-8", errors="replace")
    return raw, len(cp.stdout)


m.grep = decode_safe_grep
m.main()
