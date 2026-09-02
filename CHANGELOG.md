# Changelog

## 0.3.0-alpha - 2026-09-02

- Added a dedicated `long-document` specialist route for large PDFs, policies, specifications, books, transcripts, and scanned/visual pages.
- Expanded the research route into claim-centered retrieval with source hierarchy, contradiction handling, freshness checks, a compact claim ledger, and an explicit sufficiency stop.
- Expanded plan-aware context management with future-utility buckets, semantic-boundary compaction, reconstruction-cost checks, and a reusable `HandoffState` shape.
- Expanded evidence/provenance handling with `EXACT / EXTRACTIVE / LOSSY` fidelity classes, `EvidencePacket`, source-state tracking, transformation provenance, corroboration policy, and abstention conditions.
- Expanded the eval suite with long-document cross-reference, redundant-research stop, handoff retention, provenance-transform, and additional no-trigger cases.
- Published `docs/QUICKSTART.md` and practical before/after examples.
- Published a conservative end-to-end agent OFF vs ON benchmark protocol with task strata, failure taxonomy, anti-gaming rules, and stable-release evidence gates.
- Added an evidence-gated `ROADMAP.md`, `SECURITY.md`, `CITATION.cff`, pull-request template, and structured bug/feature/benchmark issue templates.
- Strengthened CI validation to check required specialist routes, eval integrity, version consistency, citation metadata, and public project files.
- Refreshed the Archify repository evidence to the v0.3 source state and included the long-document/plan-aware specialist routes.

## 0.2.0-alpha - 2026-09-02

- Rebranded the public project as **ACE-S — Adaptive Context Engineering Skill**.
- Reworked README around a 30-second visual/ASCII mental model.
- Added the 21-task Popular Repo Replay across Requests, Django, Zod, Actix Web, Gson, Gin, and Kubernetes.
- Added transparent `RepoReplay Score` methodology: ACE-S 90.2/100 vs single-pass 72.9/100 in the live replay.
- Added raw replay CSV and per-repository results.
- Added competitor/related-work matrix covering context-router, Ratel, Acontext, memahead, xMemory, and Agent Skills for Context Engineering.
- Refined the coding route with query reduction and test → symbol → implementation structural follow-ups observed in the replay.
- Expanded eval cases for over-constrained repository search and test-to-source routing.
- Preserved the release rule that end-to-end same-model A/B evaluation is required before stable general performance claims.

## 0.1.0-alpha - 2026-09-02

- Initial public alpha.
- Added trigger-gated context routing.
- Added adaptive resolution ladder.
- Added specialist routes for coding, temporal state, research, planning, and evidence provenance.
- Added synthetic mechanism benchmark and reproducible validation script.
- Real-agent A/B benchmark remains a release gate before stable performance claims.
