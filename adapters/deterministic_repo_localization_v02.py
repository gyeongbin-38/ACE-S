#!/usr/bin/env python3
"""Robust decode wrapper for deterministic_repo_localization v0.1.

Keeps the frozen ranking/search policy unchanged; only makes subprocess text
decoding tolerant of non-UTF8 bytes present in real repositories.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import deterministic_repo_localization as base


def robust_run(cmd: list[str], *, cwd: Path | None = None, timeout: float = 300.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


base.run = robust_run

if __name__ == "__main__":
    base.main()
