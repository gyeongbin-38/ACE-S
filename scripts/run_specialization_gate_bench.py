#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "adaptive-context-engineering"
FIXTURE = ROOT / "benchmarks" / "specialization-gate-bench-v0.1.json"

KERNEL = "SKILL.md"
INDEX = "manifests/INDEX.md"
GENERIC = "manifests/generic.md"

DOMAIN = {
    "CODE": ("manifests/code.md", "references/coding.md"),
    "DOCUMENT": ("manifests/document.md", "references/long-document.md"),
    "RESEARCH": ("manifests/research.md", "references/research.md"),
    "STATE": ("manifests/state.md", "references/temporal.md"),
}
MODIFIER = {
    "TEMPORAL": ("manifests/temporal.md", "references/temporal.md"),
    "EVIDENCE": ("manifests/evidence.md", "references/evidence-and-provenance.md"),
    "TOOLS": ("manifests/tools.md", "references/tool-discovery.md"),
    "RETENTION": ("manifests/retention.md", "references/plan-aware.md"),
}
RESOLUTION = "references/resolution-ladder.md"


def size(rel: str) -> int:
    return (SKILL / rel).stat().st_size


def uniq(seq: list[str]) -> list[str]:
    out = []
    seen = set()
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def specialized_files(domain: str) -> list[str]:
    return list(DOMAIN[domain])


def modifier_files(modifiers: list[str]) -> list[str]:
    files: list[str] = []
    for modifier in modifiers:
        files.extend(MODIFIER[modifier])
    return files


def required_files(case: dict) -> set[str]:
    if case["required_mode"] == "DIRECT":
        return {KERNEL}
    files = {KERNEL, INDEX}
    if case["required_mode"] == "GENERIC":
        files.add(GENERIC)
    if case["required_domain"]:
        files.update(specialized_files(case["required_domain"]))
    files.update(modifier_files(case["required_modifiers"]))
    if case["late_domain"]:
        files.update(specialized_files(case["late_domain"]))
    return files


def load_full(case: dict) -> list[str]:
    if case["activation"] == "DIRECT":
        return [KERNEL]
    files = [KERNEL, INDEX, GENERIC]
    for pair in DOMAIN.values():
        files.extend(pair)
    for pair in MODIFIER.values():
        files.extend(pair)
    files.append(RESOLUTION)
    return uniq(files)


def load_forced(case: dict) -> list[str]:
    if case["activation"] == "DIRECT":
        return [KERNEL]
    files = [KERNEL, INDEX]
    domain = case["required_domain"] or case["forced_domain"] or case["late_domain"]
    if domain:
        files.extend(specialized_files(domain))
    files.extend(modifier_files(case["required_modifiers"]))
    return uniq(files)


def load_optional(case: dict) -> list[str]:
    if case["activation"] == "DIRECT":
        return [KERNEL]
    files = [KERNEL, INDEX]
    if case["required_mode"] == "SPECIALIZED":
        files.extend(specialized_files(case["required_domain"]))
    else:
        # Wrong-specialist family explicitly measures bounded fallback cost.
        if case["family"] == "wrong-specialist-recovery":
            files.extend(specialized_files(case["forced_domain"]))
        files.append(GENERIC)
        files.extend(modifier_files(case["required_modifiers"]))
        if case["late_domain"]:
            files.extend(specialized_files(case["late_domain"]))
    return uniq(files)


def evaluate(name: str, cases: list[dict], loader) -> dict:
    rows = []
    family = defaultdict(lambda: {"n": 0, "success": 0, "bytes": 0})
    clear_spec_n = clear_spec_ok = 0
    pure_generic_n = pure_generic_clean = 0
    recovery_n = recovery_ok = 0

    for case in cases:
        loaded = loader(case)
        req = required_files(case)
        loaded_set = set(loaded)
        success = req.issubset(loaded_set)
        loaded_bytes = sum(size(p) for p in loaded)
        irrelevant = loaded_set - req
        irrelevant_bytes = sum(size(p) for p in irrelevant)

        if case["family"] == "clear-specialized":
            clear_spec_n += 1
            clear_spec_ok += int(success)
        if case["family"] in {"generic-artifact", "generic-history"}:
            pure_generic_n += 1
            has_specialist = any(ref in loaded_set for _, ref in DOMAIN.values())
            pure_generic_clean += int(success and not has_specialist)
        if case["family"] == "wrong-specialist-recovery":
            recovery_n += 1
            recovery_ok += int(success and GENERIC in loaded_set)

        fs = family[case["family"]]
        fs["n"] += 1
        fs["success"] += int(success)
        fs["bytes"] += loaded_bytes
        rows.append({
            "id": case["id"],
            "success": success,
            "loaded_files": loaded,
            "loaded_bytes": loaded_bytes,
            "irrelevant_bytes": irrelevant_bytes,
            "missing": sorted(req - loaded_set),
        })

    n = len(rows)
    success_rate = sum(r["success"] for r in rows) / n
    mean_bytes = sum(r["loaded_bytes"] for r in rows) / n
    total_bytes = sum(r["loaded_bytes"] for r in rows)
    irrelevant_rate = sum(r["irrelevant_bytes"] for r in rows) / total_bytes if total_bytes else 0.0

    return {
        "name": name,
        "n": n,
        "success_rate": success_rate,
        "clear_specialist_preservation": clear_spec_ok / clear_spec_n if clear_spec_n else 0.0,
        "pure_generic_no_specialist_rate": pure_generic_clean / pure_generic_n if pure_generic_n else 0.0,
        "wrong_specialist_to_generic_recovery": recovery_ok / recovery_n if recovery_n else 0.0,
        "mean_policy_bytes": mean_bytes,
        "mean_loaded_files": sum(len(r["loaded_files"]) for r in rows) / n,
        "irrelevant_policy_byte_rate": irrelevant_rate,
        "families": {
            k: {
                "n": v["n"],
                "success_rate": v["success"] / v["n"],
                "mean_policy_bytes": v["bytes"] / v["n"],
            }
            for k, v in sorted(family.items())
        },
        "failures": [r for r in rows if not r["success"]],
    }


def r1(x: float) -> float:
    return round(100.0 * x, 1)


def main() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = doc["cases"]
    results = {
        "A_full_load": evaluate("A_full_load", cases, load_full),
        "D_forced_specialized": evaluate("D_forced_specialized", cases, load_forced),
        "E_optional_specialization": evaluate("E_optional_specialization", cases, load_optional),
    }
    full_mean = results["A_full_load"]["mean_policy_bytes"]

    for result in results.values():
        success = result["success_rate"]
        byte_saving = max(0.0, 1.0 - result["mean_policy_bytes"] / full_mean)
        quality_adjusted_eff = success * byte_saving
        score = (
            0.45 * success
            + 0.20 * result["clear_specialist_preservation"]
            + 0.15 * result["pure_generic_no_specialist_rate"]
            + 0.10 * result["wrong_specialist_to_generic_recovery"]
            + 0.10 * quality_adjusted_eff
        )
        result["specialization_gate_score"] = round(100 * score, 1)
        result["success_rate"] = r1(result["success_rate"])
        result["clear_specialist_preservation"] = r1(result["clear_specialist_preservation"])
        result["pure_generic_no_specialist_rate"] = r1(result["pure_generic_no_specialist_rate"])
        result["wrong_specialist_to_generic_recovery"] = r1(result["wrong_specialist_to_generic_recovery"])
        result["quality_adjusted_policy_efficiency"] = r1(quality_adjusted_eff)
        result["irrelevant_policy_byte_rate"] = r1(result["irrelevant_policy_byte_rate"])
        result["mean_policy_bytes"] = round(result["mean_policy_bytes"], 1)
        result["mean_loaded_files"] = round(result["mean_loaded_files"], 2)
        for fam in result["families"].values():
            fam["success_rate"] = r1(fam["success_rate"])
            fam["mean_policy_bytes"] = round(fam["mean_policy_bytes"], 1)

    output = {
        "experiment": "specialization-gate-bench-v0.1",
        "fixture_count": len(cases),
        "important_caveat": (
            "Development-time controller-mechanics screening. Fixtures were authored to exercise the candidate architecture; "
            "this is not an unseen natural-language or end-to-end quality benchmark."
        ),
        "score_formula": (
            "45% mechanical policy coverage + 20% clear-specialist preservation + "
            "15% pure-generic no-specialist rate + 10% wrong-specialist-to-generic recovery + "
            "10% quality-adjusted policy-byte efficiency"
        ),
        "conditions": results,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
