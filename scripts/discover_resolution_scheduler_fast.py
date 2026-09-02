#!/usr/bin/env python3
from __future__ import annotations

import functools
import json
import math
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


def sequential_ladder_cost(world: d.World) -> float:
    """Strong sequential baseline: look ahead to pick a source, but only advance one fidelity level at a time."""
    initial_active = tuple(range(len(world.decisions)))
    initial_levels = tuple(0 for _ in world.sources)

    @functools.lru_cache(maxsize=None)
    def rec(active: tuple[int, ...], levels: tuple[int, ...]) -> float:
        if d.solved(world, active):
            return 0.0
        candidates = []
        for sid in range(len(world.sources)):
            current = levels[sid]
            if current >= 4:
                continue
            nxt = current + 1
            reachable = []
            for target in range(nxt, 5):
                ig = d.info_gain(world, active, sid, target)
                if ig > 1e-12:
                    total_upgrade_cost = d.incremental_cost(world, levels, sid, target)
                    reachable.append((ig / total_upgrade_cost, ig, -total_upgrade_cost, target))
            if reachable:
                best_reachable = max(reachable)
                next_cost = d.incremental_cost(world, levels, sid, nxt)
                next_ig = d.info_gain(world, active, sid, nxt)
                candidates.append((best_reachable, next_ig / next_cost if next_cost > 0 else 0.0, -next_cost, -sid, sid, nxt))
        if not candidates:
            return math.inf
        *_rank, sid, target = max(candidates)
        nl = list(levels)
        nl[sid] = target
        next_levels = tuple(nl)
        return d.incremental_cost(world, levels, sid, target) + sum(
            p * rec(st, next_levels) for p, st in d.partitions(world, active, sid, target)
        )

    return rec(initial_active, initial_levels)


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
    ladder_ratios = [sequential_ladder_cost(world) / opt for _iid, world, opt in validation]

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
        "strong_sequential_ladder": d.summarize(ladder_ratios),
        "top_candidates": [
            {"policy": asdict(p), "summary": s, "objective": round(obj, 6)}
            for obj, p, s in stage2[:5]
        ],
        "guardrail": "Bounded development search only. The original acquisition policy is evaluated zero-shot without resolution retuning. Freeze any selected resolution policy before unseen resolution tests.",
        "caveat": "Synthetic finite-decision resolution mechanics, not end-to-end LLM answer quality. The ladder baseline may look ahead when choosing a source, but must pay every intermediate fidelity level."
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
