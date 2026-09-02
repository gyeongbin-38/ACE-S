# Contributing

Contributions are welcome. Prefer changes that improve task quality, recoverability, or context efficiency without increasing default context unnecessarily.

## Before opening a PR

1. Keep `SKILL.md` compact; place specialist guidance in `references/`.
2. Add or update an eval case for behavior changes.
3. Run `python scripts/validate_skill.py`.
4. Separate synthetic/mechanism results from real-agent benchmark claims.
5. Document regressions and no-uplift cases, not only wins.
