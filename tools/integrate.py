#!/usr/bin/env python3
"""Logic: run enabled module installers in fixed order. cwd=work.

Usage: integrate.py <variant> <branch>

Pin triple per module lives in variant defaults, e.g.
  "ksu": {"branch": "dev", "tag": "", "commit": "2482c569..."}
Precedence: commit > tag > branch > basic clone (spec true or all-empty
triple = unpinned clone). A branch record may replace the whole triple
for one branch only (proven per-tree divergence; partial triples are
replaced whole, never merged). No dispatch pin inputs exist on purpose:
run-time rerouting is a variant edit, so every built pin is reviewed
in JSON, never typed into a text box.
"""
import json
import subprocess
import sys
from pathlib import Path

builder = Path("../builder")  # cwd=work, checkout is a sibling
manifest = json.loads((builder / "modules" / "manifest.json").read_text())
MODULES = manifest["order"]
KEY = manifest["keys"]

variant, branch = sys.argv[1], sys.argv[2]

v = json.loads((builder / "variants" / f"{variant}.json").read_text())
rec = next(b for b in v["branches"] if b["branch"] == branch)
defaults = v.get("defaults", {})

for mod in MODULES:
    key = KEY[mod]
    spec = rec.get(key, defaults.get(key, False))
    if spec is False or spec is None:
        print(f"integrate: {mod} off; skipping")
        continue
    if spec is True:
        pin = {}
    elif isinstance(spec, dict):
        pin = spec
    else:
        sys.exit(f"FAIL: {key} must be true/false or a pin triple")
    ref = pin.get("commit") or pin.get("tag") or pin.get("branch") or ""
    src = "branch" if key in rec else "variant"
    print(f"integrate: {mod} ref={ref or '(basic clone)'} via {src}")
    script = builder / "modules" / mod / "setup.sh"
    if not script.is_file():
        sys.exit(f"FAIL: {mod} enabled but {script} missing")
    subprocess.run(["bash", str(script), ".", branch, ref], check=True)
print("integrate: done")
