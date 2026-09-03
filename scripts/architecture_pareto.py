#!/usr/bin/env python3
"""Conservative Pareto-frontier evaluator for architecture candidates.

Unknown material values block dominance rather than being treated as zero/best.
This tool does not choose a winner unless the input itself makes one candidate
strictly non-dominated and all comparison dimensions are known.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def dominates(a: dict[str, Any], b: dict[str, Any], directions: dict[str, str]) -> bool:
    strictly_better = False
    for dim, direction in directions.items():
        av = a.get("dimensions", {}).get(dim)
        bv = b.get("dimensions", {}).get(dim)
        if not is_number(av) or not is_number(bv):
            return False
        if direction == "min":
            if av > bv:
                return False
            if av < bv:
                strictly_better = True
        elif direction == "max":
            if av < bv:
                return False
            if av > bv:
                strictly_better = True
        else:
            raise ValueError(f"invalid direction for {dim}: {direction}")
    return strictly_better


def frontier(obj: dict[str, Any]) -> dict[str, Any]:
    directions = obj.get("directions")
    candidates = obj.get("candidates")
    if not isinstance(directions, dict) or not directions:
        raise ValueError("directions must be non-empty object")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("candidates must be non-empty array")

    feasible = []
    eliminated = []
    for c in candidates:
        if not isinstance(c, dict) or not isinstance(c.get("id"), str):
            raise ValueError("each candidate requires string id")
        violations = c.get("hard_constraint_violations", [])
        if violations:
            eliminated.append({"id": c["id"], "reason": "hard_constraint", "details": violations})
        else:
            feasible.append(c)

    dominated_by: dict[str, list[str]] = {c["id"]: [] for c in feasible}
    for b in feasible:
        for a in feasible:
            if a["id"] == b["id"]:
                continue
            if dominates(a, b, directions):
                dominated_by[b["id"]].append(a["id"])

    pareto = [c["id"] for c in feasible if not dominated_by[c["id"]]]
    for c in feasible:
        if dominated_by[c["id"]]:
            eliminated.append({"id": c["id"], "reason": "dominated", "details": sorted(dominated_by[c["id"]])})

    unknowns = {}
    for c in feasible:
        missing = [d for d in directions if not is_number(c.get("dimensions", {}).get(d))]
        if missing:
            unknowns[c["id"]] = missing

    return {
        "pareto_frontier": pareto,
        "feasible_candidates": [c["id"] for c in feasible],
        "eliminated": eliminated,
        "unknown_material_dimensions": unknowns,
        "winner_selected": len(pareto) == 1 and pareto[0] not in unknowns,
        "winner": pareto[0] if len(pareto) == 1 and pareto[0] not in unknowns else None,
        "claim_boundary": "Pareto filtering only. It does not invent stakeholder utility weights and unknown dimensions block dominance.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    obj = json.loads(args.input.read_text(encoding="utf-8"))
    print(json.dumps(frontier(obj), indent=2))


if __name__ == "__main__":
    main()
