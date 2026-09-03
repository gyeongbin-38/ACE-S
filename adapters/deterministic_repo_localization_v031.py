#!/usr/bin/env python3
"""Development variant: remove lexicographic exact-hit priority.

Exact-token matches remain strongly represented inside v0.3's score, but do not
form a hard ordering key ahead of definition/path/structural evidence.
"""
from __future__ import annotations

import deterministic_repo_localization_v03 as prev
import deterministic_repo_localization as base


def composite_rank(by_file, terms):
    rows = prev.smart_rank_files(by_file, terms)
    rows.sort(key=lambda r: (-r["score"], -r["exact_hits"], r["hit_bytes"], r["path"]))
    return rows


base.rank_files = composite_rank

if __name__ == "__main__":
    base.main()
