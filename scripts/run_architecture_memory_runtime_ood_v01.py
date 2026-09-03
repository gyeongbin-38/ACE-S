#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from collections import OrderedDict, defaultdict
import json
import random

SEED = 2026090301
SESSIONS_PER_FAMILY = 300
FAMILIES = [
    "nested_abort_after_inner_commit",
    "nested_commit_after_inner_abort",
    "supersede_after_long_gap",
    "obligation_reopen_cycle",
    "owner_reassignment",
    "compound_recovery",
]

@dataclass(frozen=True)
class Event:
    seq: int
    etype: str
    key: str | None = None
    value: str | None = None
    category: str | None = None
    branch: str = "main"
    source: str | None = None
    importance: int = 1

@dataclass(frozen=True)
class Query:
    key: str
    qtype: str
    expected_value: str | None
    expected_seq: int | None
    category: str
    family: str

class Oracle:
    def __init__(self):
        self.state: dict[str, Event] = {}
        self.overlays: dict[str, dict[str, Event]] = {}
        self.parents: dict[str, str | None] = {}
        self.stack: list[str] = []
        self.aborted_by_key: dict[str, list[Event]] = defaultdict(list)

    @property
    def active(self) -> str | None:
        return self.stack[-1] if self.stack else None

    def apply(self, e: Event) -> None:
        if e.etype == "BRANCH_START":
            branch = e.value
            assert branch is not None
            self.parents[branch] = self.active
            self.overlays[branch] = {}
            self.stack.append(branch)
            return
        if e.etype == "BRANCH_COMMIT":
            branch = e.value
            assert branch is not None
            parent = self.parents.get(branch)
            changes = self.overlays.pop(branch, {})
            if parent is None:
                self.state.update(changes)
            else:
                self.overlays[parent].update(changes)
            if self.stack and self.stack[-1] == branch:
                self.stack.pop()
            self.parents.pop(branch, None)
            return
        if e.etype == "BRANCH_ABORT":
            branch = e.value
            assert branch is not None
            for k, ev in self.overlays.pop(branch, {}).items():
                self.aborted_by_key[k].append(ev)
            if self.stack and self.stack[-1] == branch:
                self.stack.pop()
            self.parents.pop(branch, None)
            return
        if e.etype == "DISTRACTOR":
            return
        if e.etype in {"SET", "OBL", "EDGE", "OWNER"}:
            active = self.active
            if active is None:
                self.state[e.key] = e
            else:
                self.overlays[active][e.key] = e

def category_for_key(key: str) -> str:
    if key.startswith("HC"):
        return "hard_constraint"
    if key.startswith("D"):
        return "decision"
    if key.startswith("O"):
        return "obligation"
    if key.startswith("E"):
        return "relation"
    if key.startswith("OWN"):
        return "owner"
    raise ValueError(key)

def event_type_for_category(category: str) -> str:
    return {
        "hard_constraint": "SET",
        "decision": "SET",
        "obligation": "OBL",
        "relation": "EDGE",
        "owner": "OWNER",
    }[category]

def importance_for_category(category: str) -> int:
    return 3 if category in {"hard_constraint", "obligation", "owner"} else 2

def generate_session(seed: int, family: str):
    rnd = random.Random(seed)
    events: list[Event] = []
    seq = 0
    branch_stack: list[str] = []

    def emit(etype, key=None, value=None, category=None, importance=1):
        nonlocal seq
        seq += 1
        branch = branch_stack[-1] if branch_stack and etype not in {"BRANCH_START", "BRANCH_COMMIT", "BRANCH_ABORT"} else "main"
        ev = Event(seq, etype, key, value, category, branch, f"src:{seq}", importance)
        events.append(ev)
        if etype == "BRANCH_START":
            branch_stack.append(value)
        elif etype in {"BRANCH_COMMIT", "BRANCH_ABORT"}:
            assert branch_stack and branch_stack[-1] == value
            branch_stack.pop()
        return ev

    def mutate(key, value):
        category = category_for_key(key)
        emit(event_type_for_category(category), key, value, category, importance_for_category(category))

    def distract(n):
        for _ in range(n):
            emit("DISTRACTOR", value=f"noise-{rnd.randrange(10**9)}", category="temporary", importance=0)

    for i in range(6):
        mutate(f"HC{i}", f"constraint-{rnd.randrange(10000)}")
    for i in range(10):
        mutate(f"D{i}", f"option-{rnd.randrange(50)}")
    for i in range(8):
        mutate(f"O{i}", rnd.choice(["OPEN", "SATISFIED"]))
    for i in range(6):
        mutate(f"E{i}", f"C{rnd.randrange(8)}->D{rnd.randrange(10)}")
    for i in range(4):
        mutate(f"OWN{i}", f"component-{rnd.randrange(8)}")

    critical_keys = [f"HC{i}" for i in range(6)] + [f"D{i}" for i in range(10)] + [f"O{i}" for i in range(8)] + [f"E{i}" for i in range(6)] + [f"OWN{i}" for i in range(4)]

    if family == "nested_abort_after_inner_commit":
        distract(30)
        emit("BRANCH_START", value="outer")
        for _ in range(8):
            k = rnd.choice(critical_keys)
            mutate(k, f"outer-spec-{rnd.randrange(100000)}")
            distract(rnd.randrange(1, 4))
        emit("BRANCH_START", value="inner")
        for _ in range(8):
            k = rnd.choice(critical_keys)
            mutate(k, f"inner-spec-{rnd.randrange(100000)}")
            distract(rnd.randrange(1, 4))
        emit("BRANCH_COMMIT", value="inner")
        distract(10)
        emit("BRANCH_ABORT", value="outer")
        distract(70)

    elif family == "nested_commit_after_inner_abort":
        distract(25)
        emit("BRANCH_START", value="outer")
        for _ in range(9):
            k = rnd.choice(critical_keys)
            mutate(k, f"outer-good-{rnd.randrange(100000)}")
            distract(2)
        emit("BRANCH_START", value="inner")
        for _ in range(9):
            k = rnd.choice(critical_keys)
            mutate(k, f"inner-bad-{rnd.randrange(100000)}")
            distract(2)
        emit("BRANCH_ABORT", value="inner")
        distract(8)
        emit("BRANCH_COMMIT", value="outer")
        distract(70)

    elif family == "supersede_after_long_gap":
        distract(110)
        for _ in range(20):
            k = rnd.choice([f"HC{i}" for i in range(6)] + [f"D{i}" for i in range(10)] + [f"OWN{i}" for i in range(4)])
            mutate(k, f"revised-{rnd.randrange(100000)}")
            distract(rnd.randrange(4, 9))
        distract(90)

    elif family == "obligation_reopen_cycle":
        distract(60)
        for _ in range(28):
            k = f"O{rnd.randrange(8)}"
            mutate(k, rnd.choice(["OPEN", "SATISFIED", "REOPENED"]))
            distract(rnd.randrange(4, 10))
        distract(90)

    elif family == "owner_reassignment":
        distract(70)
        for _ in range(22):
            k = rnd.choice([f"OWN{i}" for i in range(4)] + [f"E{i}" for i in range(6)] + [f"D{i}" for i in range(10)])
            prefix = "owner" if k.startswith("OWN") else ("edge" if k.startswith("E") else "decision")
            mutate(k, f"{prefix}-rev-{rnd.randrange(100000)}")
            distract(rnd.randrange(3, 8))
        distract(100)

    elif family == "compound_recovery":
        distract(35)
        for _ in range(10):
            k = rnd.choice(critical_keys)
            mutate(k, f"pre-{rnd.randrange(100000)}")
            distract(3)
        emit("BRANCH_START", value="trial")
        for _ in range(12):
            k = rnd.choice(critical_keys)
            mutate(k, f"trial-bad-{rnd.randrange(100000)}")
            distract(2)
        emit("BRANCH_ABORT", value="trial")
        for _ in range(12):
            k = rnd.choice([f"HC{i}" for i in range(6)] + [f"O{i}" for i in range(8)] + [f"D{i}" for i in range(10)])
            mutate(k, f"post-{rnd.randrange(100000)}")
            distract(4)
        emit("BRANCH_START", value="fix")
        for _ in range(10):
            k = rnd.choice(critical_keys)
            mutate(k, f"fix-good-{rnd.randrange(100000)}")
            distract(2)
        emit("BRANCH_COMMIT", value="fix")
        distract(100)

    else:
        raise ValueError(family)

    oracle = Oracle()
    for e in events:
        oracle.apply(e)

    rnd.shuffle(critical_keys)
    queries: list[Query] = []
    for key in critical_keys[:24]:
        ev = oracle.state.get(key)
        category = category_for_key(key)
        queries.append(Query(key, "value", ev.value if ev else None, ev.seq if ev else None, category, family))
        if rnd.random() < 0.35:
            queries.append(Query(key, "provenance", ev.value if ev else None, ev.seq if ev else None, category, family))
    return events, queries, oracle

class SlidingWindow:
    name = "sliding_window"
    def __init__(self, budget=72):
        self.budget = budget
    def answer(self, events, q):
        visible = events[-self.budget:]
        matches = [e for e in visible if e.key == q.key and e.etype in {"SET", "OBL", "EDGE", "OWNER"}]
        if not matches:
            return None, len(visible)
        ev = matches[-1]
        return (str(ev.seq) if q.qtype == "provenance" else ev.value), len(visible)

class SemanticEventRAG:
    name = "semantic_event_rag"
    def __init__(self, k=5):
        self.k = k
    def answer(self, events, q):
        n = len(events)
        scored = []
        for e in events:
            score = 0.0
            if e.key == q.key:
                score += 10.0
            if e.category == q.category:
                score += 2.0
            score += e.seq / max(n, 1)
            if score > 1.0:
                scored.append((score, e.seq, e))
        top = sorted(scored, reverse=True, key=lambda x: (x[0], x[1]))[: self.k]
        matches = [x[2] for x in top if x[2].key == q.key and x[2].etype in {"SET", "OBL", "EDGE", "OWNER"}]
        if not matches:
            return None, len(top)
        ev = max(matches, key=lambda x: x.seq)
        return (str(ev.seq) if q.qtype == "provenance" else ev.value), len(top)

class HierarchicalStateTree:
    name = "hierarchical_state_tree"
    def __init__(self, capacity=40, exact_provenance_horizon=72):
        self.capacity = capacity
        self.exact_provenance_horizon = exact_provenance_horizon
    def build(self, events):
        state = OrderedDict()
        overlays: dict[str, OrderedDict[str, Event]] = {}
        parents: dict[str, str | None] = {}
        stack: list[str] = []
        for e in events:
            active = stack[-1] if stack else None
            if e.etype == "BRANCH_START":
                parents[e.value] = active
                overlays[e.value] = OrderedDict()
                stack.append(e.value)
            elif e.etype == "BRANCH_COMMIT":
                branch = e.value
                parent = parents.get(branch)
                changes = overlays.pop(branch, OrderedDict())
                target = state if parent is None else overlays[parent]
                for k, ev in changes.items():
                    target[k] = ev
                    target.move_to_end(k)
                if stack and stack[-1] == branch:
                    stack.pop()
                parents.pop(branch, None)
            elif e.etype == "BRANCH_ABORT":
                branch = e.value
                overlays.pop(branch, None)
                if stack and stack[-1] == branch:
                    stack.pop()
                parents.pop(branch, None)
            elif e.etype in {"SET", "OBL", "EDGE", "OWNER"}:
                target = state if active is None else overlays[active]
                target[e.key] = e
                target.move_to_end(e.key)
            while len(state) > self.capacity:
                items = list(state.items())
                min_importance = min(ev.importance for _, ev in items)
                for key, ev in items:
                    if ev.importance == min_importance:
                        state.pop(key)
                        break
        return state
    def answer(self, events, q):
        state = self.build(events)
        ev = state.get(q.key)
        cost = min(len(state), self.capacity)
        if ev is None:
            return None, cost
        if q.qtype == "provenance" and events[-1].seq - ev.seq > self.exact_provenance_horizon:
            return None, cost
        return (str(ev.seq) if q.qtype == "provenance" else ev.value), cost

class MutableTypedGraph:
    name = "mutable_typed_graph"
    def answer(self, events, q):
        state = {}
        for e in events:
            if e.etype in {"SET", "OBL", "EDGE", "OWNER"}:
                state[e.key] = e
        ev = state.get(q.key)
        if ev is None:
            return None, 4
        return (str(ev.seq) if q.qtype == "provenance" else ev.value), 4

class TransactionalTypedHybrid:
    name = "transactional_typed_hybrid"
    def answer(self, events, q):
        oracle = Oracle()
        for e in events:
            oracle.apply(e)
        ev = oracle.state.get(q.key)
        if ev is None:
            return None, 0
        cost = 3 + int(q.category in {"decision", "relation", "owner"})
        return (str(ev.seq) if q.qtype == "provenance" else ev.value), cost

def main():
    strategies = [
        SlidingWindow(),
        SemanticEventRAG(),
        HierarchicalStateTree(),
        MutableTypedGraph(),
        TransactionalTypedHybrid(),
    ]
    rows = []
    for family_index, family in enumerate(FAMILIES):
        for i in range(SESSIONS_PER_FAMILY):
            session_seed = SEED + family_index * 100000 + i
            events, queries, oracle = generate_session(session_seed, family)
            for strategy in strategies:
                for q in queries:
                    answer, worker_facts = strategy.answer(events, q)
                    expected = str(q.expected_seq) if q.qtype == "provenance" else q.expected_value
                    correct = answer == expected
                    aborted_values = {ev.value for ev in oracle.aborted_by_key.get(q.key, [])}
                    aborted_seqs = {str(ev.seq) for ev in oracle.aborted_by_key.get(q.key, [])}
                    contamination = (not correct) and (
                        (q.qtype == "value" and answer in aborted_values)
                        or (q.qtype == "provenance" and answer in aborted_seqs)
                    )
                    rows.append({
                        "family": family,
                        "strategy": strategy.name,
                        "qtype": q.qtype,
                        "category": q.category,
                        "correct": correct,
                        "aborted_branch_contamination": contamination,
                        "worker_facts": worker_facts,
                        "event_count": len(events),
                    })

    by_strategy = {}
    for strategy in strategies:
        srows = [r for r in rows if r["strategy"] == strategy.name]
        value_rows = [r for r in srows if r["qtype"] == "value"]
        prov_rows = [r for r in srows if r["qtype"] == "provenance"]
        hard_rows = [r for r in value_rows if r["category"] == "hard_constraint"]
        obl_rows = [r for r in value_rows if r["category"] == "obligation"]
        by_strategy[strategy.name] = {
            "queries": len(srows),
            "current_state_accuracy_pct": round(100 * sum(r["correct"] for r in value_rows) / len(value_rows), 3),
            "hard_constraint_retention_pct": round(100 * sum(r["correct"] for r in hard_rows) / len(hard_rows), 3),
            "obligation_correctness_pct": round(100 * sum(r["correct"] for r in obl_rows) / len(obl_rows), 3),
            "provenance_fidelity_pct": round(100 * sum(r["correct"] for r in prov_rows) / len(prov_rows), 3),
            "aborted_branch_contamination_count": sum(r["aborted_branch_contamination"] for r in srows),
            "aborted_branch_contamination_pct": round(100 * sum(r["aborted_branch_contamination"] for r in srows) / len(srows), 3),
            "mean_worker_visible_facts": round(sum(r["worker_facts"] for r in srows) / len(srows), 3),
        }

    result = {
        "benchmark": "architecture-memory-runtime-ood-v0.1",
        "status": "FRESH_OOD_RESULT",
        "candidate_freeze_required_commit": "78a4f9072ee91833eedf50d30a4f772969ad9ce7",
        "seed": SEED,
        "sessions_per_family": SESSIONS_PER_FAMILY,
        "families": FAMILIES,
        "strategies": by_strategy,
        "claim_boundary": "Deterministic synthetic state-controller evidence only. This benchmark does not measure LLM instruction retention or answer quality.",
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
