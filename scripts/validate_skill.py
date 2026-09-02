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

# --- Specialist references -----------------------------------------------
referenced = set(re.findall(r"`(references/[^`]+\.md)`", text))
for ref in sorted(referenced):
    if not (skill / ref).exists():
        fail(f"missing reference: {ref}")

required_refs = {
    "references/coding.md",
    "references/long-document.md",
    "references/temporal.md",
    "references/research.md",
    "references/plan-aware.md",
    "references/evidence-and-provenance.md",
    "references/resolution-ladder.md",
}
for ref in sorted(required_refs - referenced):
    fail(f"SKILL.md does not route to required specialist reference: {ref}")

# --- Evals ---------------------------------------------------------------
if not eval_path.exists():
    fail("missing evals/evals.json")
    eval_data = {}
else:
    try:
        eval_data = json.loads(eval_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid evals JSON: {exc}")
        eval_data = {}

cases = eval_data.get("cases", [])
if len(cases) < 10:
    fail("need at least 10 eval cases")

ids = [case.get("id") for case in cases if isinstance(case, dict)]
if any(not case_id for case_id in ids):
    fail("every eval case needs a non-empty id")
if len(ids) != len(set(ids)):
    fail("eval case ids must be unique")

for case in cases:
    if not isinstance(case, dict):
        fail("every eval case must be an object")
        continue
    for field in ("id", "prompt", "expected", "assertions"):
        if field not in case:
            fail(f"eval {case.get('id', '<unknown>')} missing {field}")
    if not isinstance(case.get("assertions", []), list) or not case.get("assertions"):
        fail(f"eval {case.get('id', '<unknown>')} needs assertions")

if skill_version and eval_data.get("version") != skill_version:
    fail(
        f"version mismatch: SKILL.md={skill_version} "
        f"evals={eval_data.get('version')}"
    )

# --- Public repository consistency ---------------------------------------
if not (root / "docs" / "QUICKSTART.md").exists():
    fail("missing docs/QUICKSTART.md")
if not (root / "ROADMAP.md").exists():
    fail("missing ROADMAP.md")
if not (root / "SECURITY.md").exists():
    fail("missing SECURITY.md")
if not citation_path.exists():
    fail("missing CITATION.cff")

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
    f"OK: ACE-S {skill_version} structure, specialist routes, evals, "
    "and public metadata are consistent"
)
