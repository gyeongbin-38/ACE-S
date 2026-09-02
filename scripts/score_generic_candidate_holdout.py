#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "adaptive-context-engineering"
FIXTURE = ROOT / "benchmarks" / "generic-candidate-unseen-v0.1.json"

OLD_SHA = "6e84f524aeb9bd761aa789445c1edb99cdadd9dd"
NEW_SHA = "0e9a0ba03bfda7ffb8997a68f63e46dfcdbad503"

KERNEL = "skills/adaptive-context-engineering/SKILL.md"
INDEX = "skills/adaptive-context-engineering/manifests/INDEX.md"
GENERIC = "skills/adaptive-context-engineering/manifests/generic.md"
DOMAIN = {
    "CODE": (
        "skills/adaptive-context-engineering/manifests/code.md",
        "skills/adaptive-context-engineering/references/coding.md",
    ),
    "DOCUMENT": (
        "skills/adaptive-context-engineering/manifests/document.md",
        "skills/adaptive-context-engineering/references/long-document.md",
    ),
    "RESEARCH": (
        "skills/adaptive-context-engineering/manifests/research.md",
        "skills/adaptive-context-engineering/references/research.md",
    ),
    "STATE": (
        "skills/adaptive-context-engineering/manifests/state.md",
        "skills/adaptive-context-engineering/references/temporal.md",
    ),
}


def git_bytes(sha: str, path: str) -> int:
    data = subprocess.check_output(["git", "show", f"{sha}:{path}"], cwd=ROOT)
    return len(data)


def pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def entry_bytes(sha: str, domain: str | None = None, generic: bool = False) -> int:
    total = git_bytes(sha, KERNEL) + git_bytes(sha, INDEX)
    if generic:
        total += git_bytes(sha, GENERIC)
    if domain:
        m, r = DOMAIN[domain]
        total += git_bytes(sha, m) + git_bytes(sha, r)
    return total


def main() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    hard = [c for c in doc["cases"] if c["gold_strength"] == "hard"]
    ambiguous = [c for c in doc["cases"] if c["gold_strength"] == "ambiguous"]
    hard_spec = [c for c in hard if c["acceptable_modes"] == ["SPECIALIZED"]]
    hard_generic = [c for c in hard if c["acceptable_modes"] == ["GENERIC"]]

    # Old forced-primary controller can represent hard specialist tasks but has
    # no valid generic entry state. For its generic-task byte cost, use the
    # cheapest specialist path as an optimistic lower bound rather than choosing
    # a convenient wrong domain per fixture.
    old_domain_costs = {d: entry_bytes(OLD_SHA, domain=d) for d in DOMAIN}
    old_cheapest_domain = min(old_domain_costs, key=old_domain_costs.get)
    old_cheapest_cost = old_domain_costs[old_cheapest_domain]

    old_costs = []
    new_costs = []
    for case in hard:
        if case in hard_spec:
            domain = case["acceptable_domains"][0]
            old_costs.append(entry_bytes(OLD_SHA, domain=domain))
            new_costs.append(entry_bytes(NEW_SHA, domain=domain))
        else:
            old_costs.append(old_cheapest_cost)
            new_costs.append(entry_bytes(NEW_SHA, generic=True))

    old_fit = len(hard_spec)
    new_fit = len(hard)

    result = {
        "experiment": "generic-candidate-fresh-holdout-structural-v0.1",
        "source_task_count": len(doc["cases"]),
        "hard_task_count": len(hard),
        "ambiguous_task_count": len(ambiguous),
        "hard_specialized_count": len(hard_spec),
        "hard_generic_count": len(hard_generic),
        "old_forced_primary": {
            "policy_commit": OLD_SHA,
            "hard_representational_fit_rate": pct(old_fit, len(hard)),
            "hard_specialist_preservation": 100.0,
            "hard_generic_entry_coverage": 0.0,
            "hard_generic_unnecessary_specialist_rate": 100.0,
            "mean_entry_policy_bytes_optimistic": round(sum(old_costs) / len(old_costs), 1),
            "optimistic_generic_forced_domain": old_cheapest_domain,
            "optimistic_generic_forced_entry_bytes": old_cheapest_cost,
            "note": "Generic-case byte cost uses the cheapest old specialist path, so this is an optimistic lower bound for the forced-primary baseline."
        },
        "new_optional_specialization": {
            "policy_commit": NEW_SHA,
            "hard_representational_fit_rate": pct(new_fit, len(hard)),
            "hard_specialist_preservation": 100.0,
            "hard_generic_entry_coverage": 100.0,
            "hard_generic_unnecessary_specialist_rate": 0.0,
            "mean_entry_policy_bytes_oracle": round(sum(new_costs) / len(new_costs), 1),
            "generic_entry_bytes": entry_bytes(NEW_SHA, generic=True),
            "note": "Uses holdout gold entry mode only to measure architecture mechanics, not model routing accuracy."
        },
        "interpretation": (
            "The structural comparison asks whether the architecture can represent the hard holdout boundary and what entry-policy bytes it would load under oracle entry decisions. "
            "It does not show that a model will choose the correct entry mode. Ambiguous cases are excluded from hard fit scoring."
        )
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
