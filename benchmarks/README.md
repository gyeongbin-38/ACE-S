# Benchmark Notes

## v0.1 synthetic mechanism benchmark

This benchmark is a mechanism-level simulator, **not an end-to-end LLM benchmark**.

### Workload
- 3 independent random seeds
- 14 context-task classes
- 3 working-context budgets: 2K / 8K / 32K
- 40 cases per class/budget/seed
- 65,520 strategy evaluations across the full experiment series

Task classes included:
simple recent context, exact fact recovery, conflicting state, long documents,
research synthesis, multi-source verification, local code, code ripple,
multi-step plans, tool selection, noisy chat, aggregation, historical/temporal state,
and no-retrieval controls.

### Main result
The modular skill design (small router + conditional specialist references) produced
the best simulated public-skill result.

Important: the simulator models context selection/recoverability. It does not prove
that a particular frontier model will achieve the same uplift.

### Release gate
Do not advertise synthetic scores as model benchmark scores.

For v0.2, run same-model, same-task A/B tests through real agent harnesses and report:
- pass rate and pass@k
- trigger precision/recall
- token delta
- latency delta
- failure categories
- negative/no-uplift cells
