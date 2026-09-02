#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ContextAction:
    name: str
    epistemic_value: float
    context_tokens: float
    reacquisition_tokens: float = 0.0
    tool_calls: float = 0.0
    latency_ms: float = 0.0
    mandatory: bool = False


@dataclass(frozen=True)
class CostWeights:
    token: float = 1.0
    reacquisition_token: float = 1.0
    tool_call: float = 0.0
    latency_ms: float = 0.0


def effective_cost(action: ContextAction, weights: CostWeights) -> float:
    cost = (
        weights.token * action.context_tokens
        + weights.reacquisition_token * action.reacquisition_tokens
        + weights.tool_call * action.tool_calls
        + weights.latency_ms * action.latency_ms
    )
    return max(cost, 1e-9)


def value_per_cost(action: ContextAction, weights: CostWeights) -> float:
    return action.epistemic_value / effective_cost(action, weights)


def choose_next(
    actions: Iterable[ContextAction],
    *,
    weights: CostWeights = CostWeights(),
    min_value_per_cost: float = 0.0,
    remaining_context_tokens: float | None = None,
) -> ContextAction | None:
    """Choose one context action, or STOP by returning None.

    `epistemic_value` is deliberately unit-agnostic: exact information gain in bits
    is preferred when a posterior is available; otherwise a calibrated estimate of
    expected decision change may be used. Costs stay explicit rather than being
    hidden inside a model score.
    """
    candidates = list(actions)
    if remaining_context_tokens is not None:
        candidates = [a for a in candidates if a.context_tokens <= remaining_context_tokens or a.mandatory]
    if not candidates:
        return None

    mandatory = [a for a in candidates if a.mandatory]
    pool = mandatory or candidates
    best = max(pool, key=lambda a: (value_per_cost(a, weights), a.epistemic_value, -effective_cost(a, weights)))
    if mandatory:
        return best
    if value_per_cost(best, weights) <= min_value_per_cost:
        return None
    return best
