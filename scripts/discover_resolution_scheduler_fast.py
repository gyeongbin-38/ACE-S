#!/usr/bin/env python3
from __future__ import annotations

import json
import random
from dataclasses import asdict

import discover_resolution_scheduler as d

TRAIN_WORLDS = 18
VALIDATION_WORLDS = 36
TRAIN_SIGMAS = [0.0, 0.75]
VALIDATION_SIGMAS = [0.0, 0.5, 1.0]
NOISE_SEEDS = [711_019]
CANDIDATES = 96
FINALISTS = 10


def objective(summary: dict) -> float:
    return summary["mean"] + 0.3 * max(0.0, summary["p90"] - 1.0)


def main() -> None:
    train = d.make_worlds(d.TRAIN_SEED, TRAIN_WORLDS)
    validation = d.make_worlds(d.VALIDATION_SEED, VALIDATION_WORLDS)
    all_candidates = sorted(d.candidate_space(), key=lambda p: tuple(asdict(p).values()))
    rng = random.Random(600_731)
    anchors = [
        d.Policy(0.35, 1.25, 1.0, 1.5, 0.5, 0.5, 0.0),
        d.Policy(1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    ]
    remaining = [p for p in all_candidates if p not in anchors]
    candidates = anchors + rng.sample(remaining, CANDIDATES - len(anchors))

    stage1 = []
    for p in candidates:
        vals = d.evaluate(p, train, TRAIN_SIGMAS, NOISE_SEEDS)
        s = d.summarize(vals)
        stage1.append((objective(s), p, s))
    stage1.sort(key=lambda row: (row[0], tuple(asdict(row[1]).values())))

    stage2 = []
    for _obj, p, _s in stage1[:FINALISTS]:
        vals = d.evaluate(p, validation, VALIDATION_SIGMAS, NOISE_SEEDS)
        s = d.summarize(vals)
        stage2.append((objective(s), p, s))
    stage2.sort(key=lambda row: (row[0], tuple(asdict(row[1]).values())))

    winner = stage2[0]
    prior = anchors[0]
    value_cost = anchors[1]
    prior_summary = d.summarize(d.evaluate(prior, validation, VALIDATION_SIGMAS, NOISE_SEEDS))
    value_summary = d.summarize(d.evaluate(value_cost, validation, VALIDATION_SIGMAS, NOISE_SEEDS))
    ladder_ratios = [d.expected_cost(world, d.ladder_chooser, jump_allowed=False) / opt for _iid, world, opt in validation]

    result = {
        "experiment": "adaptive-resolution-scheduler-search-v0.1-fast",
        "status": "development_search_only",
        "candidate_count": len(candidates),
        "train_worlds": len(train),
        "validation_worlds": len(validation),
        "selected_policy": asdict(winner[1]),
        "selected_validation": winner[2],
        "zero_shot_frozen_acquisition_policy": prior_summary,
        "plain_value_per_cost_jump": value_summary,
        "fixed_progressive_ladder": d.summarize(ladder_ratios),
        "top_candidates": [
            {"policy": asdict(p), "summary": s, "objective": round(obj, 6)}
            for obj, p, s in stage2[:5]
        ],
        "guardrail": "Bounded development search only. The original acquisition policy is evaluated zero-shot without resolution retuning. Freeze any selected resolution policy before unseen resolution tests.",
        "caveat": "Synthetic finite-decision resolution mechanics, not end-to-end LLM answer quality."
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
