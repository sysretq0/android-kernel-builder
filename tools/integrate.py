#!/usr/bin/env python3
"""Logic: run enabled module installers in fixed order. cwd=work.

Usage: integrate.py <variant> <branch> [override-json]

Pin triple per module lives in variant defaults, e.g.
  "ksu": {"branch": "dev", "tag": "", "commit": "2482c569..."}
Precedence: commit > tag > branch > basic clone (all empty = no pin).
A branch record may replace the whole triple for proven per-tree
divergence; partial overrides fail closed. A dispatch-time override
(JSON merge-patch, e.g. {"ksu": {"tag": "v3.3.0"}}) wins over both --
that is how a run pins a different branch/tag without editing JSON.
"""
import json
import subprocess
import sys
from pathlib import Path

builder = Path("../builder")  # cwd=work, checkout is a sibling
manifest = json.loads((builder / "modules" / "manifest.json").read_text())
MODULES = manifest["order"]
KEY = manifest["keys"]
SHORT_KEYS = set(KEY.values()) | {"fragments"}

variant, branch = sys.argv[1], sys.argv[2]
override = json.loads(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else {}


def deep_merge(base, patch):
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base


v = json.loads((builder / "variants" / f"{variant}.json").read_text())
rec = next(b for b in v["branches"] if b["branch"] == branch)
defaults = dict(v.get("defaults", {}))
if isinstance(override.get("defaults"), dict):
    deep_merge(defaults, override["defaults"])
for k in SHORT_KEYS:
    if k in override:  # flat shorthand: {"ksu": {"tag": "v3.3.0"}}
        defaults[k] = override[k]
branch_over = override.get("branches", {}).get(branch, {})

for mod in MODULES:
    key = KEY[mod]
    spec = defaults.get(key, False)
    if key in branch_over:
        spec = branch_over[key]
    if spec is False or spec is None:
        print(f"integrate: {mod} off; skipping")
        continue
    if spec is True:
        pin = {}
    elif isinstance(spec, dict):
        pin = spec
    else:
        sys.exit(f"FAIL: {key} must be true/false or a pin triple")
    script = builder / "modules" / mod / "setup.sh"
    if not script.is_file():
        sys.exit(f"FAIL: {mod} enabled but {script} missing")
    ref = pin.get("commit") or pin.get("tag") or pin.get("branch") or ""
    print(f"integrate: {mod} ref={ref or '(basic clone)'}")
    subprocess.run(["bash", str(script), ".", branch, ref], check=True)
print("integrate: done")
