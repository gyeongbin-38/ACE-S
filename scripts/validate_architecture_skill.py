#!/usr/bin/env python3
"""Validate architecture-engineering progressive policy structure.

This checks file-level governance only. Byte reductions are policy-loading
accounting, not architecture-quality or model-token claims.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "architecture-engineering"
CORE = SKILL / "SKILL.md"
MANIFESTS = SKILL / "manifests"
INDEX = MANIFESTS / "INDEX.md"
REFERENCES = SKILL / "references"

EXPECTED_MANIFESTS = {
    "boundary.md",
    "state.md",
    "trust.md",
    "failure.md",
    "performance.md",
    "evolution.md",
    "generic.md",
}
MAX_CORE_BYTES = 9_000
MAX_MANIFEST_BYTES = 1_500
REF_PATTERN = re.compile(r"`\.\./references/([^`]+\.md)`")


def main() -> None:
    errors = []
    if not CORE.is_file():
        errors.append("missing architecture-engineering/SKILL.md")
    if not INDEX.is_file():
        errors.append("missing manifests/INDEX.md")

    manifest_paths = {p.name for p in MANIFESTS.glob("*.md") if p.name != "INDEX.md"}
    if manifest_paths != EXPECTED_MANIFESTS:
        errors.append(f"manifest set mismatch expected={sorted(EXPECTED_MANIFESTS)} actual={sorted(manifest_paths)}")

    core_bytes = CORE.stat().st_size if CORE.exists() else 0
    if core_bytes > MAX_CORE_BYTES:
        errors.append(f"core too large: {core_bytes} > {MAX_CORE_BYTES}")

    index_bytes = INDEX.stat().st_size if INDEX.exists() else 0
    manifest_rows = []
    referenced = set()
    max_entry_load = core_bytes + index_bytes

    for path in sorted(MANIFESTS.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        size = path.stat().st_size
        if size > MAX_MANIFEST_BYTES:
            errors.append(f"manifest too large: {path.relative_to(ROOT)} {size} > {MAX_MANIFEST_BYTES}")
        text = path.read_text(encoding="utf-8")
        refs = REF_PATTERN.findall(text)
        if len(refs) > 1:
            errors.append(f"manifest loads more than one specialist reference: {path.name}: {refs}")
        ref_bytes = 0
        for ref in refs:
            ref_path = REFERENCES / ref
            if not ref_path.is_file():
                errors.append(f"manifest {path.name} references missing file: {ref}")
                continue
            referenced.add(ref)
            ref_bytes += ref_path.stat().st_size
        entry_load = core_bytes + index_bytes + size + ref_bytes
        max_entry_load = max(max_entry_load, entry_load)
        manifest_rows.append({
            "manifest": path.name,
            "bytes": size,
            "references": refs,
            "one_hotspot_policy_bytes": entry_load,
        })

    all_policy_files = [CORE, INDEX]
    all_policy_files += sorted(p for p in MANIFESTS.glob("*.md") if p.name != "INDEX.md")
    all_policy_files += sorted(REFERENCES.glob("*.md"))
    full_preload_bytes = sum(p.stat().st_size for p in all_policy_files if p.is_file())
    reduction = None if full_preload_bytes == 0 else round(100.0 * (1.0 - max_entry_load / full_preload_bytes), 3)

    report = {
        "status": "invalid" if errors else "valid",
        "core_bytes": core_bytes,
        "manifest_index_bytes": index_bytes,
        "manifests": manifest_rows,
        "referenced_specialist_files": sorted(referenced),
        "full_policy_preload_bytes": full_preload_bytes,
        "max_one_hotspot_initial_policy_bytes": max_entry_load,
        "one_hotspot_vs_full_preload_byte_reduction_pct": reduction,
        "errors": errors,
        "claim_boundary": "Static policy-file accounting only. It does not measure model tokens, end-to-end context, or architecture quality.",
    }
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
