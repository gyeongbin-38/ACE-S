#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "benchmarks" / "unseen-routing-v0.1.json"


def pct(num: int, den: int) -> float:
    return round(100.0 * num / den, 1) if den else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()

    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    pred_doc = json.loads(args.predictions.read_text(encoding="utf-8"))

    cases = {c["id"]: c for c in fixture["cases"]}
    preds = {p["id"]: p for p in pred_doc["predictions"]}

    missing = sorted(set(cases) - set(preds))
    extra = sorted(set(preds) - set(cases))
    if missing or extra:
        raise SystemExit(f"prediction ids mismatch: missing={missing} extra={extra}")

    all_cases = list(cases.values())
    active = [c for c in all_cases if c["expected_activation"] == "ACTIVE"]
    direct = [c for c in all_cases if c["expected_activation"] == "DIRECT"]
    covered = [c for c in active if not c.get("architecture_gap")]
    gaps = [c for c in active if c.get("architecture_gap")]

    activation_ok = 0
    direct_clean = 0
    top1_ok = 0
    top2_ok = 0
    gap_detect_ok = 0
    budget_ok = 0
    final_ok = 0
    family_stats = defaultdict(lambda: {"n": 0, "final_ok": 0})
    failures = []

    for case in all_cases:
        pred = preds[case["id"]]
        activation_match = pred.get("activation") == case["expected_activation"]
        activation_ok += int(activation_match)

        primary = pred.get("primary")
        backup = pred.get("backup")
        gap_detected = pred.get("gap_detected")
        budget_ok += int(not isinstance(backup, list))

        if case["expected_activation"] == "DIRECT":
            ok = activation_match and primary is None and backup is None
            direct_clean += int(ok)
        elif case.get("architecture_gap"):
            ok = activation_match and gap_detected == case["architecture_gap"]
            gap_detect_ok += int(gap_detected == case["architecture_gap"])
        else:
            acceptable = set(case["acceptable_primary"])
            t1 = primary in acceptable
            t2 = t1 or backup in acceptable
            top1_ok += int(t1)
            top2_ok += int(t2)
            ok = activation_match and t2

        final_ok += int(ok)
        fs = family_stats[case["family"]]
        fs["n"] += 1
        fs["final_ok"] += int(ok)

        if not ok:
            failures.append({
                "id": case["id"],
                "family": case["family"],
                "expected_activation": case["expected_activation"],
                "acceptable_primary": case["acceptable_primary"],
                "architecture_gap": case.get("architecture_gap"),
                "predicted": pred,
            })

    gap_counter = Counter(c["architecture_gap"] for c in gaps)
    out = {
        "experiment": "unseen-routing-v0.1",
        "controller_commit": fixture["controller_commit"],
        "prediction_metadata": {k: v for k, v in pred_doc.items() if k != "predictions"},
        "n": len(all_cases),
        "active_n": len(active),
        "direct_n": len(direct),
        "taxonomy_covered_active_n": len(covered),
        "taxonomy_gap_active_n": len(gaps),
        "taxonomy_coverage_rate_active": pct(len(covered), len(active)),
        "gap_mix": dict(gap_counter),
        "activation_accuracy": pct(activation_ok, len(all_cases)),
        "direct_no_policy_load_rate": pct(direct_clean, len(direct)),
        "primary_top1_accuracy_covered": pct(top1_ok, len(covered)),
        "candidate_top2_coverage_covered": pct(top2_ok, len(covered)),
        "gap_detection_rate": pct(gap_detect_ok, len(gaps)),
        "candidate_budget_compliance": pct(budget_ok, len(all_cases)),
        "final_route_or_gap_resolution_rate": pct(final_ok, len(all_cases)),
        "families": {
            name: {
                "n": stat["n"],
                "final_resolution_rate": pct(stat["final_ok"], stat["n"]),
            }
            for name, stat in sorted(family_stats.items())
        },
        "failures": failures,
        "interpretation_warning": (
            "A high final resolution rate cannot erase taxonomy gaps. The taxonomy coverage rate is a structural metric. "
            "Prediction files may also have their own independence limitations; inspect prediction_metadata before making claims."
        ),
    }

    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
