#!/usr/bin/env python3
"""Choose the next architecture-changing question by conservative value of information.

Questions provide explicit finite outcomes that fill currently unknown candidate
metrics. The selector does not invent probabilities. Its default ranking uses
worst-case Pareto-frontier reduction per evidence cost; expected reduction is
reported only when probabilities are supplied by the caller.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from architecture_pareto import frontier


def _apply(base: dict[str, Any], assignments: list[dict[str, Any]]) -> dict[str, Any]:
    obj = copy.deepcopy(base)
    by_id = {c["id"]: c for c in obj["candidates"]}
    for a in assignments:
        cid, dim, value = a.get("candidate"), a.get("dimension"), a.get("value")
        if cid not in by_id:
            raise ValueError(f"unknown candidate in assignment: {cid}")
        if dim not in obj["directions"]:
            raise ValueError(f"unknown dimension in assignment: {dim}")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("assignment value must be numeric")
        by_id[cid].setdefault("dimensions", {})[dim] = value
    return obj


def evaluate_questions(obj: dict[str, Any]) -> dict[str, Any]:
    base = {"directions": obj.get("directions"), "candidates": obj.get("candidates")}
    baseline = frontier(base)
    baseline_size = len(baseline["pareto_frontier"])
    questions = obj.get("questions", [])
    if not isinstance(questions, list):
        raise ValueError("questions must be array")

    rows = []
    for q in questions:
        if not isinstance(q, dict) or not isinstance(q.get("id"), str):
            raise ValueError("question requires string id")
        cost = q.get("cost", 1.0)
        if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost <= 0:
            raise ValueError(f"question {q['id']} cost must be >0")
        outcomes = q.get("outcomes", [])
        if not outcomes:
            raise ValueError(f"question {q['id']} requires outcomes")

        outcome_rows = []
        probabilities = []
        for i, outcome in enumerate(outcomes):
            assignments = outcome.get("assignments", [])
            after = frontier(_apply(base, assignments))
            after_size = len(after["pareto_frontier"])
            reduction = baseline_size - after_size
            p = outcome.get("probability")
            if p is not None:
                if not isinstance(p, (int, float)) or isinstance(p, bool) or p < 0 or p > 1:
                    raise ValueError(f"invalid probability in {q['id']} outcome {i}")
                probabilities.append(float(p))
            outcome_rows.append({
                "outcome_index": i,
                "frontier": after["pareto_frontier"],
                "frontier_size": after_size,
                "frontier_reduction": reduction,
                "winner": after.get("winner"),
                "probability": p,
            })

        if probabilities and len(probabilities) != len(outcomes):
            raise ValueError(f"question {q['id']} must provide probabilities for all outcomes or none")
        if probabilities and abs(sum(probabilities) - 1.0) > 1e-9:
            raise ValueError(f"question {q['id']} probabilities must sum to 1")

        reductions = [r["frontier_reduction"] for r in outcome_rows]
        guaranteed = min(reductions)
        mean_unweighted = sum(reductions) / len(reductions)
        expected = None
        if probabilities:
            expected = sum(p * r for p, r in zip(probabilities, reductions))

        rows.append({
            "id": q["id"],
            "cost": float(cost),
            "outcomes": outcome_rows,
            "guaranteed_frontier_reduction": guaranteed,
            "guaranteed_reduction_per_cost": round(guaranteed / cost, 6),
            "unweighted_mean_frontier_reduction": round(mean_unweighted, 6),
            "expected_frontier_reduction": None if expected is None else round(expected, 6),
            "expected_reduction_per_cost": None if expected is None else round(expected / cost, 6),
        })

    ranked = sorted(
        rows,
        key=lambda r: (
            r["guaranteed_reduction_per_cost"],
            r["guaranteed_frontier_reduction"],
            -r["cost"],
            r["id"],
        ),
        reverse=True,
    )
    selected = ranked[0]["id"] if ranked and ranked[0]["guaranteed_frontier_reduction"] > 0 else None

    return {
        "baseline_frontier": baseline["pareto_frontier"],
        "baseline_frontier_size": baseline_size,
        "baseline_unknown_material_dimensions": baseline["unknown_material_dimensions"],
        "questions": rows,
        "selection_mode": "guaranteed_frontier_reduction_per_cost",
        "selected_question": selected,
        "abstained": selected is None,
        "claim_boundary": (
            "Finite-outcome Pareto value-of-information only. The selector does not infer outcome probabilities, "
            "semantic metric values, or whether the supplied outcome set is complete."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    args = p.parse_args()
    obj = json.loads(args.input.read_text(encoding="utf-8"))
    print(json.dumps(evaluate_questions(obj), indent=2))


if __name__ == "__main__":
    main()
