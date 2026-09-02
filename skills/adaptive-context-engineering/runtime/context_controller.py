#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
IR = json.loads((HERE / "policy-ir.json").read_text(encoding="utf-8"))

SOURCE = IR["codes"]["source"]
REQ = IR["codes"]["requirement"]
FIDELITY = IR["codes"]["fidelity"]


@dataclass(frozen=True)
class SignalVector:
    N: str
    S: str
    Q: tuple[str, ...] = ()
    V: str = "A"
    P: str = "?"
    B: str = "-"

    @classmethod
    def from_dict(cls, value: dict) -> "SignalVector":
        return cls(
            N=value["N"],
            S=value["S"],
            Q=tuple(sorted(value.get("Q", []))),
            V=value.get("V", "A"),
            P=value.get("P", "?"),
            B=value.get("B", "-"),
        )


def _requirements(codes: Iterable[str]) -> list[str]:
    return [REQ[c] for c in codes]


def _requirement_ops(codes: Iterable[str]) -> list[str]:
    out: list[str] = []
    for code in codes:
        out.extend(IR["requirement_ops"][code])
    return list(dict.fromkeys(out))


def decide(sig: SignalVector) -> dict:
    if sig.N == "0":
        return {
            "action": "STOP",
            "entry_mode": "DIRECT",
            "source": None,
            "requirements": [],
            "fidelity": None,
            "ops": [],
            "reason": "CURRENT_CONTEXT_SUFFICIENT",
        }

    if sig.N == "?":
        return {
            "action": "PROBE",
            "entry_mode": "UNCERTAIN",
            "source": None,
            "requirements": _requirements(sig.Q),
            "fidelity": FIDELITY[sig.V],
            "ops": ["SUFFICIENCY"],
            "reason": "ACTIVATION_UNCERTAIN",
        }

    if sig.P == "0":
        if sig.B != "-":
            return {
                "action": "SWITCH",
                "entry_mode": "SPECIALIZED" if sig.B != "G" else "GENERIC",
                "source": SOURCE[sig.B],
                "requirements": _requirements(sig.Q),
                "fidelity": FIDELITY[sig.V],
                "ops": [],
                "reason": "NO_PROGRESS_USE_BACKUP",
            }
        if sig.S != "G":
            return {
                "action": "SWITCH",
                "entry_mode": "GENERIC",
                "source": "GENERIC",
                "requirements": _requirements(sig.Q),
                "fidelity": FIDELITY[sig.V],
                "ops": IR["source_ops"]["G"] + _requirement_ops(sig.Q),
                "reason": "NO_PROGRESS_FALLBACK_GENERIC",
            }

    if sig.S == "?":
        return {
            "action": "PROBE",
            "entry_mode": "GENERIC",
            "source": None,
            "requirements": _requirements(sig.Q),
            "fidelity": FIDELITY[sig.V],
            "ops": ["SOURCE"],
            "reason": "SOURCE_UNCERTAIN",
        }

    source = SOURCE[sig.S]
    generic = sig.S == "G"
    return {
        "action": "OPEN" if generic else "SPECIALIZE",
        "entry_mode": "GENERIC" if generic else "SPECIALIZED",
        "source": source,
        "requirements": _requirements(sig.Q),
        "fidelity": FIDELITY[sig.V],
        "ops": IR["source_ops"][sig.S] + _requirement_ops(sig.Q),
        "reason": "LOW_COMMITMENT_ENTRY" if generic else "DOMINANT_SOURCE_EARNED",
    }


def compact_directive(decision: dict) -> str:
    action = decision["action"]
    source = decision["source"] or "-"
    req = "+".join(decision["requirements"]) or "-"
    fidelity = decision["fidelity"] or "-"
    ops = ",".join(decision["ops"])
    return f"A={action};S={source};Q={req};V={fidelity};OPS={ops}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("signal_json", help="JSON object with N,S,Q,V,P,B")
    args = parser.parse_args()
    signal = SignalVector.from_dict(json.loads(args.signal_json))
    result = decide(signal)
    print(json.dumps({"decision": result, "directive": compact_directive(result)}, indent=2))
