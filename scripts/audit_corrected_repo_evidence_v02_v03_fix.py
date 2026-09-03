#!/usr/bin/env python3
"""Invariant-only decode wrapper for corrected v0.2/v0.3 audit.

Changes only git-grep stdout decoding to UTF-8 with replacement, matching the
previous v0.2 invariant fix. Policies, corrected labels, metrics, and selection
rules are unchanged.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import audit_corrected_repo_evidence_v02_v03 as audit


def decode_safe_grep(repo: Path, terms: list[tuple[str, float, bool]]) -> tuple[str, int]:
    if not terms:
        return "", 0
    cmd = ["git", "grep", "-n", "-I", "-i"]
    for term, _, _ in terms:
        cmd.extend(["-e", term])
    cmd.extend(["--", ":(exclude)*.lock"])
    cp = subprocess.run(cmd, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if cp.returncode not in {0, 1}:
        raise RuntimeError(cp.stderr.decode("utf-8", errors="replace")[-1000:])
    return cp.stdout.decode("utf-8", errors="replace"), len(cp.stdout)


audit.v02.grep = decode_safe_grep

if __name__ == "__main__":
    audit.main()
