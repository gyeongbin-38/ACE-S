#!/usr/bin/env python3
from pathlib import Path
import json
import re
import sys

root = Path(__file__).resolve().parents[1]
skill = root / "skills" / "adaptive-context-engineering"
skill_path = skill / "SKILL.md"
readme_path = root / "README.md"
eval_path = skill / "evals" / "evals.json"
citation_path = root / "CITATION.cff"
routerbench_path = root / "benchmarks" / "routerbench-v0.1.json"
policy_bench_path = root / "benchmarks" / "policy-load-bench-v0.1.json"

errors = []


def fail(message: str) -> None:
    errors.append(message)


# --- SKILL.md frontmatter -------------------------------------------------
text = skill_path.read_text(encoding="utf-8")
if not text.startswith("---\n"):
    fail("SKILL.md must start with YAML frontmatter")
parts = text.split("---", 2)
front = parts[1] if len(parts) > 2 else ""

name_match = re.search(r"^name:\s*(.+)$", front, re.M)
desc_match = re.search(r"^description:\s*(.+)$", front, re.M)
version_match = re.search(r'^\s*version:\s*["\']?([^"\'\n]+)["\']?\s*$', front, re.M)

if not name_match:
    fail("missing name")
else:
    value = name_match.group(1).strip()
    if value != skill.name:
        fail("name must match skill directory")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        fail("invalid kebab-case name")
if not desc_match or not desc_match.group(1).strip():
    fail("missing description")
skill_version = version_match.group(1).strip() if version_match else None
if not skill_version:
    fail("missing metadata.version")

# --- Progressive policy manifests ----------------------------------------
index_rel = "manifests/INDEX.md"
if f"`{index_rel}`" not in text:
    fail("SKILL.md must route through manifests/INDEX.md")
if not (skill / index_rel).exists():
    fail("missing manifests/INDEX.md")

required_manifests = {
    "manifests/code.md",
    "manifests/document.md",
    "manifests/research.md",
    "manifests/state.md",
    "manifests/temporal.md",
    "manifests/evidence.md",
    "manifests/tools.md",
    "manifests/retention.md",
}
index_text = (skill / index_rel).read_text(encoding="utf-8") if (skill / index_rel).exists() else ""
for manifest in sorted(required_manifests):
    if not (skill / manifest).exists():
        fail(f"missing manifest: {manifest}")
    if f"`{manifest}`" not in index_text:
        fail(f"manifest index does not route to {manifest}")

# Manifests may route to specialist references; validate only what they name.
manifest_reference_paths = set()
for manifest in sorted(required_manifests):
    path = skill / manifest
    if not path.exists():
        continue
    body = path.read_text(encoding="utf-8")
    refs = set(re.findall(r"`(references/[^`]+\.md)`", body))
    if not refs:
        fail(f"{manifest} must name at least one specialist reference")
    for ref in refs:
        manifest_reference_paths.add(ref)
        if not (skill / ref).exists():
            fail(f"{manifest} points to missing reference: {ref}")

if "references/resolution-ladder.md" not in text:
    fail("SKILL.md must keep resolution-ladder as an on-demand utility")
if not (skill / "references/resolution-ladder.md").exists():
    fail("missing references/resolution-ladder.md")

# Guard against regressing to eager specialist loading in the kernel.
direct_specialist_refs = set(re.findall(r"`(references/[^`]+\.md)`", text))
if len(direct_specialist_refs) > 1:
    fail("SKILL.md should not directly enumerate/load specialist references; use manifests")

# --- Existing skill evals -------------------------------------------------
try:
    eval_data = json.loads(eval_path.read_text(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError) as exc:
    fail(f"invalid or missing evals JSON: {exc}")
    eval_data = {}

cases = eval_data.get("cases", [])
if len(cases) < 10:
    fail("need at least 10 eval cases")
ids = [case.get("id") for case in cases if isinstance(case, dict)]
if len(ids) != len(set(ids)) or any(not case_id for case_id in ids):
    fail("eval case ids must be non-empty and unique")
for case in cases:
    if not isinstance(case, dict):
        fail("every eval case must be an object")
        continue
    for field in ("id", "prompt", "expected", "assertions"):
        if field not in case:
            fail(f"eval {case.get('id', '<unknown>')} missing {field}")
if skill_version and eval_data.get("version") != skill_version:
    fail(f"version mismatch: SKILL.md={skill_version} evals={eval_data.get('version')}")

# --- RouterBench fixture (legacy experimental routing fixture) ------------
try:
    routerbench = json.loads(routerbench_path.read_text(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError) as exc:
    fail(f"invalid or missing RouterBench JSON: {exc}")
    routerbench = {}
rb_cases = routerbench.get("cases", [])
if routerbench.get("version") != "0.1" or len(rb_cases) < 20:
    fail("RouterBench v0.1 needs version 0.1 and at least 20 fixtures")

# --- Selective Policy Load Bench -----------------------------------------
try:
    policy_bench = json.loads(policy_bench_path.read_text(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError) as exc:
    fail(f"invalid or missing policy-load bench JSON: {exc}")
    policy_bench = {}

pb_cases = policy_bench.get("cases", [])
if policy_bench.get("version") != "0.1" or len(pb_cases) < 20:
    fail("policy-load bench v0.1 needs version 0.1 and at least 20 cases")
allowed_domains = {"GENERAL", "CODE", "DOCUMENT", "RESEARCH", "STATE"}
allowed_modifiers = {"TEMPORAL", "EVIDENCE", "TOOLS", "RETENTION"}
allowed_recovery = {"none", "manifest_reject", "specialist_no_progress"}
pb_ids = []
for case in pb_cases:
    if not isinstance(case, dict):
        fail("policy-load case must be an object")
        continue
    required = {"id", "family", "activation", "required_domain", "required_modifiers", "initial_candidates", "recovery_mode", "needs_resolution_policy"}
    missing = required - set(case)
    if missing:
        fail(f"policy-load case {case.get('id', '<unknown>')} missing {sorted(missing)}")
        continue
    pb_ids.append(case["id"])
    if case["required_domain"] not in allowed_domains:
        fail(f"invalid required_domain in {case['id']}")
    if not set(case["required_modifiers"]).issubset(allowed_modifiers):
        fail(f"invalid modifier in {case['id']}")
    if len(case["initial_candidates"]) > 2:
        fail(f"{case['id']} violates one-primary-plus-one-backup limit")
    if not set(case["initial_candidates"]).issubset(allowed_domains):
        fail(f"invalid initial candidate in {case['id']}")
    if case["recovery_mode"] not in allowed_recovery:
        fail(f"invalid recovery_mode in {case['id']}")
if len(pb_ids) != len(set(pb_ids)):
    fail("policy-load case ids must be unique")
required_families = {"direct", "single-domain", "lazy-modifier", "wrong-first-manifest", "wrong-first-specialist", "compositional"}
if not required_families.issubset({case.get("family") for case in pb_cases if isinstance(case, dict)}):
    fail("policy-load bench is missing required case families")

# --- Public repository consistency ---------------------------------------
required_public_files = [
    "AGENTS.md",
    "ROADMAP.md",
    "SECURITY.md",
    "CITATION.cff",
    "docs/QUICKSTART.md",
    "docs/CONTEXT_CONTRACTS.md",
    "benchmarks/AGENT_AB_PROTOCOL.md",
    "benchmarks/ROUTERBENCH.md",
    "benchmarks/policy-load-bench-v0.1.json",
    "scripts/run_policy_load_bench.py",
]
for relative_path in required_public_files:
    if not (root / relative_path).exists():
        fail(f"missing {relative_path}")

if readme_path.exists() and skill_version:
    readme = readme_path.read_text(encoding="utf-8")
    badge_version = skill_version.replace("-", "--")
    if f"version-{badge_version}" not in readme:
        fail(f"README version badge does not match {skill_version}")
if citation_path.exists() and skill_version:
    citation = citation_path.read_text(encoding="utf-8")
    citation_version = re.search(r'^version:\s*["\']?([^"\'\n]+)', citation, re.M)
    if not citation_version or citation_version.group(1).strip() != skill_version:
        fail(f"CITATION.cff version does not match {skill_version}")

if errors:
    print("FAILED")
    for error in errors:
        print("-", error)
    sys.exit(1)

print(
    f"OK: ACE-S {skill_version} progressive policy manifests, evals, "
    "RouterBench fixtures, Selective Policy Load Bench, and metadata are consistent"
)
