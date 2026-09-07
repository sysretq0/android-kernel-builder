#!/usr/bin/env python3
"""Logic: variant JSON -> build matrix. Control stays in the workflow."""
import json
import os
import sys

variant = sys.argv[1]
want = sys.argv[2] if len(sys.argv) > 2 else "all"

with open(f"variants/{variant}.json") as f:
    v = json.load(f)

rows = [{"branch": b["branch"], "manifest": b["manifest"], "kind": b["kind"]}
        for b in v["branches"]]
if want != "all":
    rows = [r for r in rows if r["branch"] == want]
    if not rows:
        sys.exit(f"unknown branch: {want}")

matrix = json.dumps({"include": rows})
with open(os.environ["GITHUB_OUTPUT"], "a") as f:
    f.write(f"matrix={matrix}\n")
print(matrix)
