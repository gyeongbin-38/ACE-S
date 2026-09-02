#!/usr/bin/env python3
from __future__ import annotations

import json

from run_routerbench_experiment import (
    ACTIVATIONS,
    LEGACY,
    PRIMARY,
    ROUTERS,
    STRESS,
    macro_f1,
    modifier_micro_f1,
    safe_div,
    score_legacy_activation,
)


def semantic_exact(pred, expected: dict) -> bool:
    return (
        pred.activation == expected["activation"]
        and pred.primary_domain == expected["primary_domain"]
        and set(pred.modifiers) == set(expected["modifiers"])
        and pred.fidelity == expected["fidelity"]
    )


def score_full(cases: list[dict], router) -> dict:
    predictions = [router(c["prompt"]) for c in cases]
    exp_a = [c["expected"]["activation"] for c in cases]
    pred_a = [p.activation for p in predictions]
    activation_f1 = macro_f1(exp_a, pred_a, ACTIVATIONS)
    domain_acc = sum(p.primary_domain == c["expected"]["primary_domain"] for c, p in zip(cases, predictions)) / len(cases)
    mod_f1 = modifier_micro_f1([set(c["expected"]["modifiers"]) for c in cases], [set(p.modifiers) for p in predictions])
    fidelity_acc = sum(p.fidelity == c["expected"]["fidelity"] for c, p in zip(cases, predictions)) / len(cases)
    exact = sum(semantic_exact(p, c["expected"]) for c, p in zip(cases, predictions)) / len(cases)

    direct_idx = [i for i, c in enumerate(cases) if c["expected"]["activation"] == "DIRECT"]
    active_idx = [i for i, c in enumerate(cases) if c["expected"]["activation"] == "ACTIVE"]
    overtrigger = safe_div(sum(predictions[i].activation != "DIRECT" for i in direct_idx), len(direct_idx))
    undertrigger = safe_div(sum(predictions[i].activation == "DIRECT" for i in active_idx), len(active_idx))

    composite = (
        0.25 * activation_f1
        + 0.20 * domain_acc
        + 0.20 * mod_f1
        + 0.15 * fidelity_acc
        + 0.10 * exact
        + 0.05 * (1 - overtrigger)
        + 0.05 * (1 - undertrigger)
    ) * 100

    bucket = {}
    for name in sorted({c["bucket"] for c in cases}):
        indices = [i for i, c in enumerate(cases) if c["bucket"] == name]
        bucket[name] = {
            "n": len(indices),
            "activation_accuracy": round(100 * sum(predictions[i].activation == cases[i]["expected"]["activation"] for i in indices) / len(indices), 1),
            "full_exact_match": round(100 * sum(semantic_exact(predictions[i], cases[i]["expected"]) for i in indices) / len(indices), 1),
        }

    failures = []
    for case, pred in zip(cases, predictions):
        if not semantic_exact(pred, case["expected"]):
            failures.append({"id": case["id"], "bucket": case["bucket"], "expected": case["expected"], "predicted": pred.as_dict()})

    return {
        "n": len(cases),
        "router_score": round(composite, 1),
        "activation_macro_f1": round(activation_f1 * 100, 1),
        "domain_accuracy": round(domain_acc * 100, 1),
        "modifier_micro_f1": round(mod_f1 * 100, 1),
        "fidelity_accuracy": round(fidelity_acc * 100, 1),
        "full_exact_match": round(exact * 100, 1),
        "overtrigger_rate": round(overtrigger * 100, 1),
        "undertrigger_rate": round(undertrigger * 100, 1),
        "buckets": bucket,
        "failures": failures,
    }


def main() -> None:
    primary = json.loads(PRIMARY.read_text(encoding="utf-8"))["cases"]
    stress = json.loads(STRESS.read_text(encoding="utf-8"))["cases"]
    legacy = json.loads(LEGACY.read_text(encoding="utf-8"))["cases"]

    report = {
        "experiment": "routerbench-three-condition-v0.1.1",
        "score_formula": "25% activation macro-F1 + 20% domain accuracy + 20% modifier micro-F1 + 15% fidelity accuracy + 10% semantic full exact match + 5% (1-overtrigger) + 5% (1-undertrigger)",
        "scoring_fix": "Modifier order is ignored because modifiers are an unordered multi-label set.",
        "important_caveat": "This is a deterministic controller-policy benchmark, not a repeated frontier-model routing benchmark.",
        "conditions": {},
    }
    for name, router in ROUTERS.items():
        report["conditions"][name] = {
            "primary": score_full(primary, router),
            "stress": score_full(stress, router),
            "legacy_activation": score_legacy_activation(legacy, router),
        }

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
