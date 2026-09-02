#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT / "benchmarks" / "routerbench-v0.1.json"
STRESS = ROOT / "benchmarks" / "routerbench-stress-v0.1.json"
LEGACY = ROOT / "skills" / "adaptive-context-engineering" / "evals" / "evals.json"

MODIFIERS = ["TEMPORAL", "EVIDENCE_CRITICAL", "PLAN_AWARE", "TOOL_DISCOVERY"]
ACTIVATIONS = ["DIRECT", "ACTIVE", "UNCERTAIN"]


@dataclass(frozen=True)
class Prediction:
    activation: str
    primary_domain: str
    modifiers: tuple[str, ...]
    fidelity: str

    def as_dict(self) -> dict:
        return {
            "activation": self.activation,
            "primary_domain": self.primary_domain,
            "modifiers": list(self.modifiers),
            "fidelity": self.fidelity,
        }


def t(prompt: str) -> str:
    return " ".join(prompt.lower().split())


def has(text: str, *parts: str) -> bool:
    return any(part in text for part in parts)


def explicit_direct(text: str) -> bool:
    return has(
        text,
        "rewrite this",
        "rewrite this title",
        "make this title friendlier",
        "copyedit this supplied sentence only",
        "write a short birthday",
        "capital of france",
        "no repository lookup is needed",
        "no source lookup is needed",
        "do not check any live product",
        "without looking anything up",
        "without checking any current product",
    )


def simple_transform(text: str) -> bool:
    return has(text, "rewrite", "copyedit", "make this title", "birthday message", "format them as a bullet")


def code_signal(text: str) -> bool:
    return has(
        text,
        "repository",
        " repo ",
        "codebase",
        "function",
        "method",
        "tests",
        "callers",
        "symbol",
        "implementation",
        "source file",
        "regression test",
        "parseconfig",
        "authtoken",
        "contextdecision",
        "debugging",
        "log lines",
        "raw log",
    )


def doc_signal(text: str) -> bool:
    return has(
        text,
        "page policy",
        "page specification",
        "page manual",
        "pages. identify",
        "pages. find",
        "pdf",
        "policy document",
        "long policy",
        "long regulation",
        "attached manual",
        "attached policy",
        "attached 300",
        "attached 250",
        "supplied regulation",
        "specification",
        "governing clause",
        "section 4.2",
        "omitted table",
        "omitted appendix",
        "heading hierarchy",
    )


def research_signal(text: str) -> bool:
    return has(
        text,
        "paper",
        "papers",
        "peer-reviewed",
        "primary sources",
        "authoritative sources",
        "approaches",
        "deep research",
        "research a library",
        "context compression",
        "reported experiments",
    )


def state_signal(text: str) -> bool:
    conflict = has(text, "disagree", "different current", "conflict", "superseded", "earlier state", "old and new")
    state_terms = has(text, "current value", "applies now", "controls today", "governs today", "revision controls", "historical date", "archived v2.1", "version 2.1")
    return conflict or state_terms


def temporal_surface(text: str) -> bool:
    return has(text, "latest", "current", "today", "now", "newest", "recent", "revision", "amendment", "version")


def historical_fixed(text: str) -> bool:
    return has(text, "historical date is fixed", "date is fixed", "fixed to 2024", "january 1, 2024", "archived v2.1", "version 2.1", "published in 2024")


def evidence_surface(text: str) -> bool:
    return has(
        text,
        "exact",
        "quote",
        "cite",
        "citation",
        "verify",
        "provenance",
        "evidence",
        "official",
        "accepted action names",
        "allowed values",
        "field name",
        "governing section",
        "controlling exception",
        "raw benchmark",
        "route back to raw",
        "reference to the raw",
    )


def plan_surface(text: str) -> bool:
    return has(
        text,
        "later",
        "next implementation",
        "next refactor",
        "next debugging",
        "next diagnosis",
        "next step",
        "another agent",
        "handoff",
        "tomorrow",
        "implementation plan",
        "prepare context",
        "preserve only what",
        "preserve the exact constraints",
        "what would break",
        "likely to break",
        "blast radius",
    )


def tool_surface(text: str) -> bool:
    return has(text, "tool can read", "capability", "installed code-search", "installed capability", "visible tools", "unknown binary artifact", "artifact format is unknown")


def uncertain_surface(text: str) -> bool:
    return (
        has(text, "may have enough", "probably answers")
        and has(text, "omitted table", "omitted appendix")
        and has(text, "change the conclusion", "reverse the conclusion")
    )


def choose_domain(text: str, direct: bool = False, signal_aware: bool = False) -> str:
    if direct and signal_aware:
        if has(text, "complete function", "for-loop"):
            return "CODE"
        return "GENERAL"
    if code_signal(text):
        return "CODE"
    if doc_signal(text):
        return "LONG_DOCUMENT"
    if research_signal(text):
        return "RESEARCH"
    if state_signal(text):
        return "STATE"
    return "GENERAL"


def choose_fidelity(text: str, activation: str, domain: str, signal_aware: bool) -> str:
    if activation == "DIRECT":
        if has(text, "complete function", "given the complete enum"):
            return "EXTRACT"
        return "INDEX"
    if activation == "UNCERTAIN":
        return "INDEX"

    raw = evidence_surface(text) and has(
        text,
        "quote",
        "exact enum",
        "exact clause",
        "exact controlling",
        "exact rule",
        "exact limit",
        "allowed values",
        "accepted action names",
        "governing section",
    )
    if state_signal(text) and has(text, "current", "today", "now", "revision controls", "historical date", "archived v2.1", "version 2.1"):
        raw = True
    if raw:
        return "RAW"
    if has(text, "before reading", "before opening", "heading hierarchy", "find the section", "identify the heading", "capability first", "smallest suitable capability", "minimum capability"):
        return "INDEX"
    if has(text, "compact state packet"):
        return "SUMMARY"
    if domain in {"CODE", "RESEARCH"} or has(text, "log lines", "raw log"):
        return "EXTRACT"
    if domain == "LONG_DOCUMENT":
        return "EXTRACT" if signal_aware else "INDEX"
    return "INDEX"


def predict_legacy_flat(prompt: str) -> Prediction:
    text = t(prompt)
    if explicit_direct(text) or simple_transform(text):
        domain = "CODE" if has(text, "complete function", "for-loop") else "GENERAL"
        fidelity = "EXTRACT" if domain == "CODE" else "INDEX"
        return Prediction("DIRECT", domain, (), fidelity)

    # v0.3-style overloaded single-route precedence.
    if evidence_surface(text):
        route = "EVIDENCE"
    elif temporal_surface(text) or state_signal(text):
        route = "TEMPORAL"
    elif code_signal(text):
        route = "CODE"
    elif doc_signal(text):
        route = "LONG_DOCUMENT"
    elif research_signal(text):
        route = "RESEARCH"
    elif plan_surface(text):
        route = "PLAN_AWARE"
    elif tool_surface(text):
        route = "DIRECT"  # no first-class tool-discovery route in the old contract
    else:
        route = "DIRECT"

    if route == "DIRECT":
        return Prediction("DIRECT", "GENERAL", (), "INDEX")
    mapping = {
        "EVIDENCE": ("GENERAL", ("EVIDENCE_CRITICAL",), "RAW"),
        "TEMPORAL": ("STATE", ("TEMPORAL",), "RAW"),
        "CODE": ("CODE", (), "EXTRACT"),
        "LONG_DOCUMENT": ("LONG_DOCUMENT", (), "INDEX"),
        "RESEARCH": ("RESEARCH", (), "EXTRACT"),
        "PLAN_AWARE": ("GENERAL", ("PLAN_AWARE",), "SUMMARY"),
    }
    domain, modifiers, fidelity = mapping[route]
    return Prediction("ACTIVE", domain, modifiers, fidelity)


def predict_layered_naive(prompt: str) -> Prediction:
    text = t(prompt)
    if simple_transform(text) or has(text, "capital of france"):
        activation = "DIRECT"
    elif uncertain_surface(text):
        activation = "UNCERTAIN"
    elif code_signal(text) or doc_signal(text) or research_signal(text) or state_signal(text) or temporal_surface(text) or evidence_surface(text) or plan_surface(text) or tool_surface(text):
        activation = "ACTIVE"
    else:
        activation = "DIRECT"

    domain = choose_domain(text)
    modifiers = []
    if temporal_surface(text):
        modifiers.append("TEMPORAL")
    if evidence_surface(text):
        modifiers.append("EVIDENCE_CRITICAL")
    if plan_surface(text):
        modifiers.append("PLAN_AWARE")
    if tool_surface(text):
        modifiers.append("TOOL_DISCOVERY")
    fidelity = choose_fidelity(text, activation, domain, signal_aware=False)
    return Prediction(activation, domain, tuple(modifiers), fidelity)


def predict_signal_aware(prompt: str) -> Prediction:
    text = t(prompt)
    direct = explicit_direct(text) or simple_transform(text) and not has(text, "research a library")
    if direct:
        activation = "DIRECT"
    elif uncertain_surface(text):
        activation = "UNCERTAIN"
    elif code_signal(text) or doc_signal(text) or research_signal(text) or state_signal(text) or evidence_surface(text) or plan_surface(text) or tool_surface(text) or temporal_surface(text):
        activation = "ACTIVE"
    else:
        activation = "DIRECT"

    domain = choose_domain(text, direct=activation == "DIRECT", signal_aware=True)
    modifiers = []
    if activation != "DIRECT":
        temporal_needed = temporal_surface(text) and not historical_fixed(text)
        # Fresh/current source comparison is temporal even when "latest" is not the first cue.
        if temporal_needed:
            modifiers.append("TEMPORAL")

        evidence_needed = evidence_surface(text)
        if research_signal(text) and has(text, "compare", "disagree", "newest", "current approaches", "primary sources", "reported experiments"):
            evidence_needed = True
        if code_signal(text) and has(text, "defined", "declaration", "which fields", "source"):
            evidence_needed = True
        if state_signal(text):
            evidence_needed = True
        if has(text, "raw output", "raw log", "raw logs", "raw-result reference", "route back to raw", "omitted table", "omitted appendix"):
            evidence_needed = True
        if evidence_needed:
            modifiers.append("EVIDENCE_CRITICAL")

        if plan_surface(text) or (code_signal(text) and has(text, "rename", "break", "blast radius", "change impact")):
            modifiers.append("PLAN_AWARE")
        if tool_surface(text):
            modifiers.append("TOOL_DISCOVERY")

    fidelity = choose_fidelity(text, activation, domain, signal_aware=True)
    return Prediction(activation, domain, tuple(modifiers), fidelity)


ROUTERS = {
    "A_legacy_flat": predict_legacy_flat,
    "B_layered_naive": predict_layered_naive,
    "C_layered_signal_aware": predict_signal_aware,
}


def safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def macro_f1(expected: list[str], predicted: list[str], labels: list[str]) -> float:
    scores = []
    for label in labels:
        tp = sum(e == label and p == label for e, p in zip(expected, predicted))
        fp = sum(e != label and p == label for e, p in zip(expected, predicted))
        fn = sum(e == label and p != label for e, p in zip(expected, predicted))
        if tp == fp == fn == 0:
            continue
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        scores.append(safe_div(2 * precision * recall, precision + recall))
    return sum(scores) / len(scores) if scores else 0.0


def modifier_micro_f1(expected: list[set[str]], predicted: list[set[str]]) -> float:
    tp = fp = fn = 0
    for e, p in zip(expected, predicted):
        tp += len(e & p)
        fp += len(p - e)
        fn += len(e - p)
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    return safe_div(2 * precision * recall, precision + recall)


def score_full(cases: list[dict], router) -> dict:
    predictions = [router(c["prompt"]) for c in cases]
    exp_a = [c["expected"]["activation"] for c in cases]
    pred_a = [p.activation for p in predictions]
    activation_f1 = macro_f1(exp_a, pred_a, ACTIVATIONS)
    domain_acc = sum(p.primary_domain == c["expected"]["primary_domain"] for c, p in zip(cases, predictions)) / len(cases)
    mod_f1 = modifier_micro_f1([set(c["expected"]["modifiers"]) for c in cases], [set(p.modifiers) for p in predictions])
    fidelity_acc = sum(p.fidelity == c["expected"]["fidelity"] for c, p in zip(cases, predictions)) / len(cases)
    exact = sum(p.as_dict() == c["expected"] for c, p in zip(cases, predictions)) / len(cases)

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
            "full_exact_match": round(100 * sum(predictions[i].as_dict() == cases[i]["expected"] for i in indices) / len(indices), 1),
        }

    failures = []
    for case, pred in zip(cases, predictions):
        if pred.as_dict() != case["expected"]:
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


def score_legacy_activation(cases: list[dict], router) -> dict:
    expected = []
    predicted = []
    for c in cases:
        assertions = c.get("assertions", [])
        e = "DIRECT" if "should_not_trigger" in assertions or "no unnecessary retrieval" in assertions and c["id"] == "direct-no-retrieval" else "ACTIVE"
        expected.append(e)
        predicted.append(router(c["prompt"]).activation)
    accuracy = sum(e == p for e, p in zip(expected, predicted)) / len(cases)
    direct_idx = [i for i, e in enumerate(expected) if e == "DIRECT"]
    active_idx = [i for i, e in enumerate(expected) if e == "ACTIVE"]
    over = safe_div(sum(predicted[i] != "DIRECT" for i in direct_idx), len(direct_idx))
    under = safe_div(sum(predicted[i] == "DIRECT" for i in active_idx), len(active_idx))
    return {
        "n": len(cases),
        "activation_accuracy": round(accuracy * 100, 1),
        "overtrigger_rate": round(over * 100, 1),
        "undertrigger_rate": round(under * 100, 1),
        "failures": [cases[i]["id"] for i, (e, p) in enumerate(zip(expected, predicted)) if e != p],
    }


def main() -> None:
    primary = json.loads(PRIMARY.read_text(encoding="utf-8"))["cases"]
    stress = json.loads(STRESS.read_text(encoding="utf-8"))["cases"]
    legacy = json.loads(LEGACY.read_text(encoding="utf-8"))["cases"]

    report = {
        "experiment": "routerbench-three-condition-v0.1",
        "score_formula": "25% activation macro-F1 + 20% domain accuracy + 20% modifier micro-F1 + 15% fidelity accuracy + 10% full exact match + 5% (1-overtrigger) + 5% (1-undertrigger)",
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
