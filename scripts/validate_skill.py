#!/usr/bin/env python3
from pathlib import Path
import re, json, sys

root = Path(__file__).resolve().parents[1]
skill = root / "skills" / "adaptive-context-engineering"
path = skill / "SKILL.md"
text = path.read_text(encoding="utf-8")

errors = []
if not text.startswith("---\n"):
    errors.append("SKILL.md must start with YAML frontmatter")
parts = text.split("---", 2)
front = parts[1] if len(parts) > 2 else ""

name = re.search(r"^name:\s*(.+)$", front, re.M)
desc = re.search(r"^description:\s*(.+)$", front, re.M)
if not name:
    errors.append("missing name")
else:
    value = name.group(1).strip()
    if value != skill.name:
        errors.append("name must match skill directory")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        errors.append("invalid kebab-case name")
if not desc or not desc.group(1).strip():
    errors.append("missing description")

for ref in re.findall(r"`(references/[^`]+\.md)`", text):
    if not (skill / ref).exists():
        errors.append(f"missing reference: {ref}")

eval_path = skill / "evals" / "evals.json"
if not eval_path.exists():
    errors.append("missing evals/evals.json")
else:
    data = json.loads(eval_path.read_text(encoding="utf-8"))
    if len(data.get("cases", [])) < 5:
        errors.append("need at least 5 eval cases")

if errors:
    print("FAILED")
    for e in errors:
        print("-", e)
    sys.exit(1)
print("OK: skill structure and local references validated")
